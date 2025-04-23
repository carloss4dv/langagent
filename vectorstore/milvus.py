"""
Implementación de VectorStoreBase para Milvus/Zilliz.

Este módulo proporciona una implementación concreta de la interfaz VectorStoreBase
para la base de datos vectorial Milvus/Zilliz, aprovechando sus capacidades avanzadas
como particionamiento y búsqueda híbrida.
"""

import os
import time
import logging
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore
from langchain_milvus import Milvus
from langagent.vectorstore.base import VectorStoreBase
from langagent.config.config import VECTORSTORE_CONFIG
from langagent.models.constants import CUBO_TO_AMBITO, AMBITOS_CUBOS

logger = logging.getLogger(__name__)

class MilvusFilterRetriever(BaseRetriever):
    """Retriever personalizado para Milvus que soporta filtrado por metadatos."""
    
    def __init__(self, vectorstore, search_kwargs=None, filter_threshold=0.7):
        """Inicializa el retriever personalizado."""
        # Inicializar los atributos ANTES de llamar a super.__init__
        self._vectorstore = vectorstore  # Usar _vectorstore en lugar de vectorstore
        self.search_kwargs = search_kwargs or {}  # Inicializar como diccionario vacío si es None
        self.filter_threshold = filter_threshold
        # Llamar a super().__init__ después de inicializar los atributos
        super().__init__()
        
    def _get_relevant_documents(self, query: str, *, run_manager=None):
        """Recupera documentos sin filtrado de metadatos."""
        try:
            return self._vectorstore.similarity_search(query, **self.search_kwargs)
        except Exception as e:
            logger.error(f"Error en búsqueda de documentos: {e}")
            # Si falla con los parámetros proporcionados, intentar con parámetros mínimos
            fallback_kwargs = {"k": self.search_kwargs.get("k", 6)}
            return self._vectorstore.similarity_search(query, **fallback_kwargs)
    
    def search_documents(self, query: str, metadata_filters=None):
        """
        Realiza búsqueda con filtrado por metadatos.
        
        Args:
            query: Consulta de texto
            metadata_filters: Diccionario con filtros de metadatos
            
        Returns:
            List[Document]: Documentos filtrados por metadatos
        """
        if not metadata_filters:
            return self._get_relevant_documents(query)
        
        # Preparar consulta con filtros
        filter_expr = None
        
        # Convertir filtros de metadatos a expresión de filtro de Milvus
        try:
            expressions = []
            for key, value in metadata_filters.items():
                # Convertir a string para asegurar compatibilidad
                if isinstance(value, bool):
                    # Los booleanos se manejan de forma especial
                    value_str = str(value).lower()
                    expressions.append(f'{key} == "{value_str}"')
                else:
                    # Otros tipos se convierten a string
                    value_str = str(value)
                    expressions.append(f'{key} == "{value_str}"')
            
            if expressions:
                filter_expr = " && ".join(expressions)
        except Exception as e:
            logger.error(f"Error al crear expresión de filtro: {e}")
        
        # Configurar parámetros de búsqueda
        search_params = dict(self.search_kwargs)
        if filter_expr:
            search_params["filter"] = filter_expr  # Usar filter en lugar de expr
        
        # Realizar búsqueda con filtros
        try:
            return self._vectorstore.similarity_search(query, **search_params)
        except Exception as e:
            logger.error(f"Error en búsqueda con filtros: {e}")
            # Si falla la búsqueda con filtros, intentar sin filtros
            return self._get_relevant_documents(query)

class MilvusVectorStore(VectorStoreBase):
    """Implementación de VectorStoreBase para Milvus/Zilliz."""
    
    def __init__(self):
        """Inicializa la implementación de Milvus Vector Store."""
        self.use_partitioning = VECTORSTORE_CONFIG.get("use_partitioning", True)
        self.partition_by = VECTORSTORE_CONFIG.get("partition_by", "ambito")
        self.collection_mapping = {}  # Mapeo entre colecciones y sus particiones
    
    def _get_connection_args(self) -> Dict[str, Any]:
        """
        Obtiene los argumentos de conexión para Milvus.
        
        Returns:
            Dict[str, Any]: Argumentos de conexión
        """
        # Obtener parámetros de la configuración
        milvus_uri = VECTORSTORE_CONFIG.get("milvus_uri", "http://localhost:19530")
        milvus_token = VECTORSTORE_CONFIG.get("milvus_token", "")
        milvus_secure = VECTORSTORE_CONFIG.get("milvus_secure", True)
        
        # Verificar si hay variables de entorno disponibles (tienen prioridad)
        env_uri = os.getenv("ZILLIZ_CLOUD_URI")
        env_token = os.getenv("ZILLIZ_CLOUD_TOKEN")
        
        if env_uri:
            milvus_uri = env_uri
            logger.info(f"Usando URI de Milvus desde variable de entorno: {milvus_uri}")
        else:
            logger.info(f"Usando URI de Milvus desde configuración: {milvus_uri}")
            
        if env_token:
            milvus_token = env_token
            logger.info("Usando token de autenticación desde variable de entorno")
        elif milvus_token:
            logger.info("Usando token de autenticación desde configuración")
        
        # Construir argumentos de conexión
        connection_args = {
            "uri": milvus_uri,
            "secure": milvus_secure
        }
        
        # Añadir token solo si está presente
        if milvus_token:
            connection_args["token"] = milvus_token
        
        logger.info(f"Conectando a Milvus en: {milvus_uri} (Secure: {milvus_secure})")
        
        return connection_args
    
    def _prepare_documents_for_partitioning(self, documents: List[Document]) -> Dict[str, List[Document]]:
        """
        Prepara los documentos para ser insertados en particiones.
        Agrupa los documentos por el criterio de particionamiento.
        
        Args:
            documents: Lista de documentos a procesar
            
        Returns:
            Dict[str, List[Document]]: Documentos agrupados por partición
        """
        partitioned_docs = {}
        
        for doc in documents:
            # Determinar la partición según el criterio configurado
            if self.partition_by == "ambito":
                # Usar el ámbito como criterio de partición
                partition_key = doc.metadata.get("ambito", "general")
            else:
                # Usar el cubo como criterio de partición
                partition_key = doc.metadata.get("cubo_source", "general")
            
            # Normalizar el nombre de la partición
            partition_key = self._normalize_partition_name(partition_key)
            
            # Agrupar el documento en su partición
            if partition_key not in partitioned_docs:
                partitioned_docs[partition_key] = []
            
            partitioned_docs[partition_key].append(doc)
        
        return partitioned_docs
    
    def _normalize_partition_name(self, name: str) -> str:
        """
        Normaliza el nombre de una partición para que sea válido en Milvus.
        
        Args:
            name: Nombre original
            
        Returns:
            str: Nombre normalizado
        """
        # Milvus tiene algunas restricciones en los nombres de particiones
        # Eliminar caracteres no alfanuméricos y convertir a minúsculas
        normalized = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
        
        # Asegurarse de que no comienza con un número
        if normalized and normalized[0].isdigit():
            normalized = "p_" + normalized
            
        return normalized
    
    def create_vectorstore(self, documents: List[Document], embeddings: Embeddings, 
                         collection_name: str, **kwargs) -> Milvus:
        """
        Crea una nueva vectorstore Milvus con los documentos proporcionados.
        Si está habilitado el particionamiento, crea las particiones necesarias.
        
        Args:
            documents: Lista de documentos a indexar
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección en Milvus
            drop_old: Si True, elimina la colección existente antes de crearla
            
        Returns:
            Milvus: Instancia de la vectorstore creada
        """
        connection_args = self._get_connection_args()
        logger.info(f"Creando vectorstore Milvus con colección {collection_name}")
        
        # Verificar si debemos eliminar la colección existente
        drop_old = kwargs.get('drop_old', True)
        
        # Para modo de colección única, asegurarnos de usar todos los documentos
        use_single_collection = VECTORSTORE_CONFIG.get("use_single_collection", True)
        
        # Intentar eliminar la colección si drop_old es True
        if drop_old and use_single_collection:
            try:
                from pymilvus import connections, utility
                
                # Conectar a Milvus
                connections.connect(**connection_args)
                
                # Verificar si la colección existe y eliminarla
                if utility.has_collection(collection_name):
                    logger.info(f"Eliminando colección existente {collection_name}")
                    utility.drop_collection(collection_name)
                    logger.info(f"Colección {collection_name} eliminada correctamente")
            except Exception as e:
                logger.error(f"Error al eliminar colección: {e}")
                # Continuar de todos modos
        
        # Comprobar que los documentos tienen metadatos necesarios
        for doc in documents:
            if 'source' in doc.metadata:
                file_path = doc.metadata.get('source', '')
                file_name = os.path.basename(file_path)
                
                # Comprobar si falta el cubo_source
                if 'cubo_source' not in doc.metadata:
                    # Extraer cubo del nombre del archivo
                    match = re.search(r'info_cubo_([^_]+)', file_name)
                    if match:
                        cubo_name = match.group(1)
                        doc.metadata['cubo_source'] = cubo_name
                        
                        # También agregar ámbito si se conoce
                        if cubo_name in CUBO_TO_AMBITO and 'ambito' not in doc.metadata:
                            doc.metadata['ambito'] = CUBO_TO_AMBITO[cubo_name]
        
        try:
            if use_single_collection:
                # Verificar que todos los documentos tengan los metadatos necesarios
                logger.info("Verificando metadatos de los documentos...")
                docs_with_complete_metadata = []
                
                for idx, doc in enumerate(documents):
                    # Asegurarse de que exista el campo metadata
                    if not hasattr(doc, 'metadata') or doc.metadata is None:
                        doc.metadata = {}
                    
                    # Extraer información de la fuente si existe
                    if 'source' in doc.metadata:
                        source = doc.metadata['source']
                        # Extraer cubo_source si no existe
                        if 'cubo_source' not in doc.metadata:
                            match = re.search(r'info_cubo_([^_]+)', os.path.basename(source))
                            if match:
                                doc.metadata['cubo_source'] = match.group(1)
                            else:
                                doc.metadata['cubo_source'] = 'general'
                        
                        # Asignar ámbito basado en cubo_source si no existe
                        if 'ambito' not in doc.metadata and 'cubo_source' in doc.metadata:
                            cubo = doc.metadata['cubo_source']
                            if cubo in CUBO_TO_AMBITO:
                                doc.metadata['ambito'] = CUBO_TO_AMBITO[cubo]
                            else:
                                doc.metadata['ambito'] = 'general'
                    
                    # Si falta ambito y cubo_source, asignar valores predeterminados
                    if 'cubo_source' not in doc.metadata:
                        doc.metadata['cubo_source'] = 'general'
                    if 'ambito' not in doc.metadata:
                        doc.metadata['ambito'] = 'general'
                    
                    docs_with_complete_metadata.append(doc)
                
                # Usar los documentos con metadatos completos
                logger.info(f"Creando colección unificada con {len(docs_with_complete_metadata)} documentos")
                
                # Para Milvus/Zilliz Cloud, necesitamos usar su API de bajo nivel para definir esquema
                try:
                    from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
                    from pymilvus import utility
                    
                    # Conectar a Milvus
                    connections.connect(**connection_args)
                    
                    # Si la colección ya existe, eliminarla si drop_old es True
                    if utility.has_collection(collection_name):
                        if drop_old:
                            utility.drop_collection(collection_name)
                            logger.info(f"Colección {collection_name} eliminada para recreación")
                        else:
                            logger.info(f"La colección {collection_name} ya existe, se usará la existente")
                            
                            # Crear una instancia de Milvus con la colección existente
                            return Milvus(
                                embedding_function=embeddings,
                                collection_name=collection_name,
                                connection_args=connection_args
                            )
                    
                    # Definir el esquema con campos para metadatos
                    fields = [
                        FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
                        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
                        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=65535),
                        FieldSchema(name="cubo_source", dtype=DataType.VARCHAR, max_length=255),
                        FieldSchema(name="ambito", dtype=DataType.VARCHAR, max_length=255),
                        FieldSchema(name="is_consulta", dtype=DataType.BOOL)
                    ]
                    
                    # Crear el esquema y la colección
                    schema = CollectionSchema(fields)
                    collection = Collection(name=collection_name, schema=schema)
                    
                    logger.info(f"Colección {collection_name} creada con esquema personalizado")
                    
                    # Crear un índice para el campo vector
                    logger.info("Creando índice para el campo vector...")
                    index_params = {
                        "metric_type": "COSINE",
                        "index_type": "HNSW",
                        "params": {
                            "M": 16,
                            "efConstruction": 200
                        }
                    }
                    collection.create_index(field_name="vector", index_params=index_params)
                    
                    # Cargar la colección en memoria para insertar datos
                    collection.load()
                    
                    # Procesar los documentos y prepararlos para inserción
                    logger.info("Preparando datos para inserción...")
                    texts = []
                    metadatas = []
                    for doc in docs_with_complete_metadata:
                        texts.append(doc.page_content)
                        meta = doc.metadata.copy()
                        
                        # Asegurar que los metadatos tienen los campos necesarios
                        if "cubo_source" not in meta:
                            meta["cubo_source"] = "general"
                        if "ambito" not in meta:
                            meta["ambito"] = "general"
                        if "is_consulta" not in meta:
                            meta["is_consulta"] = False
                        
                        metadatas.append(meta)
                    
                    # Generar embeddings para todos los textos
                    logger.info("Generando embeddings...")
                    embeddings_vectors = embeddings.embed_documents(texts)
                    
                    # Preparar datos para inserción en Milvus
                    entities = []
                    entities.append({"field": "vector", "type": DataType.FLOAT_VECTOR, "values": embeddings_vectors})
                    entities.append({"field": "text", "type": DataType.VARCHAR, "values": texts})
                    
                    sources = [meta.get("source", "") for meta in metadatas]
                    entities.append({"field": "source", "type": DataType.VARCHAR, "values": sources})
                    
                    cubo_sources = [meta.get("cubo_source", "general") for meta in metadatas]
                    entities.append({"field": "cubo_source", "type": DataType.VARCHAR, "values": cubo_sources})
                    
                    ambitos = [meta.get("ambito", "general") for meta in metadatas]
                    entities.append({"field": "ambito", "type": DataType.VARCHAR, "values": ambitos})
                    
                    is_consultas = [meta.get("is_consulta", False) for meta in metadatas]
                    entities.append({"field": "is_consulta", "type": DataType.BOOL, "values": is_consultas})
                    
                    # Insertar los datos en la colección
                    logger.info(f"Insertando {len(texts)} documentos en la colección...")
                    insert_result = collection.insert(entities)
                    logger.info(f"Inserción completada: {insert_result}")
                    
                    # Esperar a que los datos se persistan
                    collection.flush()
                    
                    # Crear una instancia de Milvus vectorstore con la colección
                    milvus_db = Milvus(
                        embedding_function=embeddings,
                        collection_name=collection_name,
                        connection_args=connection_args
                    )
                    
                    logger.info(f"Vectorstore Milvus creada correctamente como colección única: {collection_name}")
                    return milvus_db
                    
                except ImportError:
                    logger.warning("No se pudo importar pymilvus. Usando la API de alto nivel.")
                except Exception as e:
                    logger.error(f"Error al crear colección con esquema personalizado: {e}")
                    logger.warning("Continuando con la API de alto nivel...")
                
                # Fallback: Usar la API de alto nivel (que puede no preservar todos los metadatos)
                logger.info("Usando API de alto nivel para crear la colección")
                milvus_db = Milvus.from_documents(
                    documents=docs_with_complete_metadata,
                    embedding=embeddings,
                    collection_name=collection_name,
                    connection_args=connection_args,
                    drop_old=drop_old  # Usar el valor proporcionado
                )
                
                # Crear índice HNSW para mejorar el rendimiento
                try:
                    logger.info("Creando índice HNSW para mejorar el rendimiento")
                    index_params = {
                        "metric_type": "COSINE",
                        "index_type": "HNSW",
                        "params": {
                            "M": 16,
                            "efConstruction": 200
                        }
                    }
                    
                    # Crear el índice en el campo de embeddings
                    if hasattr(milvus_db, 'col') and milvus_db.col is not None:
                        # Verificar si el campo existe
                        field_names = [field.name for field in milvus_db.col.schema.fields]
                        
                        if "vector" in field_names:
                            milvus_db.col.create_index(
                                field_name="vector", 
                                index_params=index_params
                            )
                            
                            # Cargar la colección en memoria para mejor rendimiento
                            milvus_db.col.load()
                            
                            logger.info(f"Índice creado correctamente para colección {collection_name}")
                        else:
                            # Buscar campo de embeddings alternativo
                            embedding_field = None
                            for field in field_names:
                                if "embedding" in field.lower() or "vector" in field.lower():
                                    embedding_field = field
                                    break
                            
                            if embedding_field:
                                logger.info(f"Usando campo alternativo para embeddings: {embedding_field}")
                                milvus_db.col.create_index(
                                    field_name=embedding_field, 
                                    index_params=index_params
                                )
                                
                                # Cargar la colección en memoria para mejor rendimiento
                                milvus_db.col.load()
                                
                                logger.info(f"Índice creado correctamente para colección {collection_name}")
                            else:
                                logger.error("No se encontró un campo válido para embeddings")
                except Exception as e:
                    logger.error(f"Error al crear índice en colección {collection_name}: {str(e)}")
                
                logger.info(f"Vectorstore Milvus creada correctamente como colección única: {collection_name}")
                return milvus_db
                
            # Para modo de múltiples colecciones con particionamiento
            else:
                # Primero, crear la colección base
                milvus_db = Milvus.from_documents(
                    documents=documents if not self.use_partitioning else documents[:1],  # Solo un documento para inicializar
                    embedding=embeddings,
                    collection_name=collection_name,
                    connection_args=connection_args,
                    drop_old=drop_old,  # Usar el valor proporcionado
                )
                
                # Si no usamos particionamiento, devolver la vectorstore
                if not self.use_partitioning:
                    logger.info(f"Vectorstore Milvus creada correctamente para colección {collection_name} sin particionamiento")
                    return milvus_db
                
                # Preparar documentos por partición
                partitioned_docs = self._prepare_documents_for_partitioning(documents)
                
                # Crear particiones y añadir documentos
                for partition_name, partition_docs in partitioned_docs.items():
                    if not partition_docs:
                        continue
                        
                    logger.info(f"Creando partición '{partition_name}' en colección '{collection_name}'")
                    
                    try:
                        # Intentar crear la partición
                        partition_name = self._normalize_partition_name(partition_name)
                        milvus_db.col.create_partition(partition_name=partition_name)
                        
                        # Añadir documentos a la partición
                        milvus_db.add_documents(documents=partition_docs, partition_name=partition_name)
                        
                        # Guardar el mapeo de particiones
                        if collection_name not in self.collection_mapping:
                            self.collection_mapping[collection_name] = []
                        
                        self.collection_mapping[collection_name].append(partition_name)
                        
                    except Exception as e:
                        logger.error(f"Error al crear partición {partition_name}: {str(e)}")
                
                # Crear índice HNSW para mejorar el rendimiento
                try:
                    index_params = {
                        "metric_type": "COSINE",
                        "index_type": "HNSW",
                        "params": {
                            "M": 16,
                            "efConstruction": 200
                        }
                    }
                    
                    # Crear el índice en el campo de embeddings
                    if hasattr(milvus_db, 'col') and milvus_db.col is not None:
                        milvus_db.col.create_index(
                            field_name="text_embedding", 
                            index_params=index_params
                        )
                        
                        # Cargar la colección en memoria para mejor rendimiento
                        milvus_db.col.load()
                        
                        logger.info(f"Índice creado correctamente para colección {collection_name}")
                except Exception as e:
                    logger.error(f"Error al crear índice en colección {collection_name}: {str(e)}")
                
                logger.info(f"Vectorstore Milvus creada correctamente para colección {collection_name}")
                return milvus_db
            
        except Exception as e:
            logger.error(f"Error al crear vectorstore Milvus para colección {collection_name}: {str(e)}")
            # Proporcionar información detallada sobre el problema de conexión
            if "connection" in str(e).lower():
                logger.error(f"Problema de conexión a Milvus. Verifique que el servidor esté en ejecución en {connection_args['uri']} " +
                             f"y que las credenciales sean correctas.")
                logger.error("Asegúrese de configurar las variables de entorno ZILLIZ_CLOUD_URI y ZILLIZ_CLOUD_TOKEN correctamente.")
            raise e
    
    def load_vectorstore(self, embeddings: Embeddings, collection_name: str, 
                       **kwargs) -> Milvus:
        """
        Carga una vectorstore Milvus existente.
        
        Args:
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección en Milvus
            
        Returns:
            Milvus: Instancia de la vectorstore cargada
        """
        connection_args = self._get_connection_args()
        logger.info(f"Cargando vectorstore Milvus existente: {collection_name}")
        
        try:
            milvus_db = Milvus(
                embedding_function=embeddings,
                collection_name=collection_name,
                connection_args=connection_args
            )
            
            # Verificar que la colección existe realmente
            if not hasattr(milvus_db, 'col') or milvus_db.col is None:
                logger.warning(f"La colección {collection_name} no existe o no se pudo cargar correctamente")
                # Crear una colección nueva con un documento de ejemplo para inicializar
                logger.info(f"Creando nueva colección {collection_name}")
                empty_doc = Document(page_content="Documento de inicialización", metadata={"source": "init"})
                milvus_db = Milvus.from_documents(
                    documents=[empty_doc],
                    embedding=embeddings,
                    collection_name=collection_name,
                    connection_args=connection_args,
                    drop_old=False
                )
                return milvus_db
            
            # Cargar metadatos de particiones si existen
            try:
                partitions = milvus_db.col.partitions
                partition_names = [p.name for p in partitions]
                
                # Guardar en el mapeo de colecciones
                self.collection_mapping[collection_name] = partition_names
                
                logger.info(f"Colección {collection_name} cargada con {len(partition_names)} particiones: {partition_names}")
            except Exception as e:
                logger.warning(f"No se pudieron obtener particiones para {collection_name}: {str(e)}")
            
            return milvus_db
        except Exception as e:
            logger.error(f"Error al cargar colección {collection_name}: {str(e)}")
            # Crear una colección nueva con un documento de ejemplo para inicializar
            try:
                logger.info(f"Intentando crear nueva colección {collection_name}")
                empty_doc = Document(page_content="Documento de inicialización", metadata={"source": "init"})
                milvus_db = Milvus.from_documents(
                    documents=[empty_doc],
                    embedding=embeddings,
                    collection_name=collection_name,
                    connection_args=connection_args,
                    drop_old=False
                )
                return milvus_db
            except Exception as create_error:
                # Si falla la creación, registrar el error y proporcionar información detallada
                logger.error(f"Error al crear colección {collection_name}: {str(create_error)}")
                if "connection" in str(e).lower():
                    logger.error(f"Problema de conexión a Milvus. Verifique que el servidor esté en ejecución en {connection_args['uri']} " +
                                f"y que las credenciales sean correctas.")
                    logger.error("Asegúrese de configurar las variables de entorno ZILLIZ_CLOUD_URI y ZILLIZ_CLOUD_TOKEN correctamente.")
                raise e
    
    def _get_ambito_from_query(self, query: str) -> Optional[str]:
        """
        Intenta determinar el ámbito de una consulta basado en keywords.
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Optional[str]: Ámbito identificado o None
        """
        import re
        query_lower = query.lower()
        
        # Buscar referencias explícitas a ámbitos
        explicit_ambito_pattern = r"(?:ámbito|ambito)\s+(\w+)"
        ambito_matches = re.findall(explicit_ambito_pattern, query_lower)
        
        # Verificar ámbitos explícitos
        for match in ambito_matches:
            ambito_key = match.lower().replace(" ", "_")
            if ambito_key in AMBITOS_CUBOS:
                return ambito_key
        
        # Buscar referencias explícitas a cubos
        explicit_cubo_pattern = r"(?:del|en el|del cubo|en el cubo)\s+(\w+)"
        cubo_matches = re.findall(explicit_cubo_pattern, query_lower)
        
        for match in cubo_matches:
            if match in CUBO_TO_AMBITO:
                return CUBO_TO_AMBITO[match]
        
        return None
    
    def create_retriever(self, vectorstore: Milvus, k: Optional[int] = None, 
                      similarity_threshold: float = 0.7, **kwargs) -> BaseRetriever:
        """
        Crea un retriever para una vectorstore Milvus.
        Configura el retriever para permitir búsquedas filtradas por metadatos.
        
        Args:
            vectorstore: Instancia de Milvus vectorstore
            k: Número de documentos a recuperar
            similarity_threshold: Umbral mínimo de similitud
            
        Returns:
            BaseRetriever: Retriever configurado para Milvus
        """
        # Obtener parámetros de búsqueda desde la configuración o parámetros
        k = k or VECTORSTORE_CONFIG.get("k_retrieval", 4)
        search_params = {
            "params": {
                "metric_type": "COSINE",
                "offset": 0,
                "ignore_growing": False,  # Considerar también documentos en cola
                "params": {"nprobe": 10}  # Cantidad de clusters a consultar
            }
        }
        
        # Determinar si usamos una colección única con filtrado por metadatos
        use_single_collection = VECTORSTORE_CONFIG.get("use_single_collection", True)
        filter_by_metadata = VECTORSTORE_CONFIG.get("filter_by_metadata", True)
        
        # Crear un wrapper personalizado para el retriever de Milvus si es necesario
        if use_single_collection and filter_by_metadata:
            # Crear retriever con soporte para filtrado por metadatos
            logger.info(f"Creando retriever personalizado con filtrado para Milvus")
            
            from langagent.vectorstore.milvus import MilvusFilterRetriever
            
            # Crear los search_kwargs que funcionarán con la colección
            # Intentar recuperar el nombre del campo de vectores
            embedding_field = "vector"
            if hasattr(vectorstore, 'col') and vectorstore.col is not None:
                try:
                    field_names = [field.name for field in vectorstore.col.schema.fields]
                    # Buscar el campo de embedding por nombre
                    for field in field_names:
                        if "embedding" in field.lower():
                            embedding_field = field
                            break
                    logger.info(f"Campo de embeddings detectado: {embedding_field}")
                except Exception as e:
                    logger.error(f"Error al detectar campo de embeddings: {e}")
            
            # Configurar parámetros de búsqueda que funcionarán
            search_kwargs = {
                "k": k, 
                "score_threshold": similarity_threshold
            }
            
            # Solo añadir search_params si estamos seguros de que la colección los soporta
            try:
                if hasattr(vectorstore, 'col') and vectorstore.col is not None:
                    schema = vectorstore.col.schema
                    search_kwargs["search_params"] = search_params
            except Exception as e:
                logger.warning(f"No se pudieron verificar los parámetros de búsqueda: {e}")
            
            try:
                # Crear y devolver el retriever personalizado
                return MilvusFilterRetriever(vectorstore=vectorstore, search_kwargs=search_kwargs)
            except Exception as e:
                logger.error(f"Error al crear MilvusFilterRetriever: {e}")
                logger.info("Creando retriever estándar como fallback")
                
                # Si falla, usar el método estándar
                return vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": k, "score_threshold": similarity_threshold}
                )
        else:
            # Enfoque estándar: crear un retriever normal
            logger.info(f"Creando retriever estándar para Milvus")
            
            # Si es una vectorstore de Milvus, crear un retriever específico
            try:
                retriever = vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={
                        "k": k,
                        "score_threshold": similarity_threshold
                    }
                )
                return retriever
            except Exception as e:
                logger.error(f"Error al crear retriever estándar: {e}")
                # Fallback simple
                return vectorstore.as_retriever()
    
    def retrieve_documents(self, retriever: BaseRetriever, query: str, 
                         max_retries: int = 3) -> List[Document]:
        """
        Recupera documentos de un retriever con manejo de errores y reintentos.
        Si se usa particionamiento, intenta identificar las particiones relevantes.
        
        Args:
            retriever: Retriever a utilizar
            query: Consulta para la búsqueda
            max_retries: Número máximo de reintentos en caso de error
            
        Returns:
            List[Document]: Lista de documentos recuperados
        """
        # Verificar si tenemos metadatos para este retriever
        retriever_id = id(retriever)
        retriever_metadata = getattr(self, '_retriever_metadata', {}).get(retriever_id, {})
        
        # Si no tenemos metadatos o no estamos usando particionamiento, usar el método estándar
        if not retriever_metadata or not self.use_partitioning:
            return self._standard_retrieve(retriever, query, max_retries)
        
        # Obtener la vectorstore y otro metadatos desde el diccionario
        vectorstore = retriever_metadata.get('vectorstore')
        collection_name = retriever_metadata.get('collection_name')
        partition_names = retriever_metadata.get('partition_names', [])
        
        # Si no tenemos vectorstore válida, usar el método estándar
        if not vectorstore or not collection_name or collection_name == 'unknown':
            return self._standard_retrieve(retriever, query, max_retries)
        
        # Si usamos particionamiento, intentamos identificar las particiones relevantes
        ambito = self._get_ambito_from_query(query)
        search_params = retriever.search_kwargs.copy() if hasattr(retriever, 'search_kwargs') else {}
        
        # Si tenemos un ámbito identificado y tenemos particiones, hacer búsqueda específica
        if ambito and partition_names:
            partition_name = self._normalize_partition_name(ambito)
            
            # Si la partición existe en esta colección
            if partition_name in partition_names:
                logger.info(f"Búsqueda en partición específica: {partition_name}")
                search_params['partition_names'] = [partition_name]
                
                try:
                    # Búsqueda directa en la partición específica
                    docs = vectorstore.similarity_search_with_score(
                        query=query,
                        **search_params
                    )
                    
                    # Convertir el resultado a formato estándar de documentos
                    return self._process_similarity_results(docs)
                    
                except Exception as e:
                    logger.error(f"Error en búsqueda por partición: {str(e)}")
                    # Caer al método estándar en caso de error
        
        # Si no pudimos hacer búsqueda por partición, usar método estándar
        return self._standard_retrieve(retriever, query, max_retries)
    
    def _standard_retrieve(self, retriever: BaseRetriever, query: str, 
                          max_retries: int = 3) -> List[Document]:
        """
        Método estándar de recuperación cuando no se usa particionamiento.
        
        Args:
            retriever: Retriever a utilizar
            query: Consulta para la búsqueda
            max_retries: Número máximo de reintentos
            
        Returns:
            List[Document]: Lista de documentos recuperados
        """
        for attempt in range(max_retries):
            try:
                docs = retriever.get_relevant_documents(query)
                
                if not docs:
                    logger.warning(f"No se encontraron documentos relevantes para la consulta: {query}")
                    return []
                
                # Logging detallado de los documentos recuperados
                for i, doc in enumerate(docs):
                    logger.debug(f"Documento {i+1}: Score={doc.metadata.get('score', 'N/A')}, "
                               f"Fuente={doc.metadata.get('source', 'N/A')}")
                
                return docs
                
            except Exception as e:
                logger.error(f"Error en intento {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error("Se agotaron los reintentos")
                    return []
                time.sleep(1)  # Esperar antes de reintentar
    
    def _process_similarity_results(self, results: List[Tuple[Document, float]]) -> List[Document]:
        """
        Procesa los resultados de similarity_search_with_score para convertirlos al formato estándar.
        
        Args:
            results: Lista de tuplas (documento, score)
            
        Returns:
            List[Document]: Lista de documentos con el score como metadato
        """
        processed_docs = []
        
        for doc, score in results:
            # Añadir el score a los metadatos
            if 'metadata' not in doc.__dict__:
                doc.metadata = {}
            
            doc.metadata['score'] = score
            processed_docs.append(doc)
        
        return processed_docs
    
    def add_documents_to_collection(self, vectorstore: Milvus, documents: List[Document]) -> bool:
        """
        Añade documentos a una vectorstore Milvus existente.
        
        Args:
            vectorstore: Instancia de Milvus vectorstore
            documents: Lista de documentos a añadir
            
        Returns:
            bool: True si los documentos se añadieron correctamente
        """
        if not documents:
            logger.warning("No hay documentos para añadir a la colección")
            return False
            
        if not hasattr(vectorstore, 'add_documents') or not callable(getattr(vectorstore, 'add_documents')):
            logger.error("El vectorstore no soporta el método add_documents")
            return False
            
        try:
            # Para colecciones grandes, dividir en lotes
            batch_size = 1000
            total_docs = len(documents)
            
            if total_docs <= batch_size:
                # Si son pocos documentos, añadirlos directamente
                logger.info(f"Añadiendo {total_docs} documentos a la colección")
                vectorstore.add_documents(documents)
            else:
                # Para muchos documentos, procesarlos en lotes
                logger.info(f"Añadiendo {total_docs} documentos en lotes de {batch_size}")
                for i in range(0, total_docs, batch_size):
                    end_idx = min(i + batch_size, total_docs)
                    batch = documents[i:end_idx]
                    logger.info(f"Añadiendo lote {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}: {len(batch)} documentos")
                    vectorstore.add_documents(batch)
                    
            logger.info(f"Se han añadido {total_docs} documentos correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al añadir documentos a la colección: {str(e)}")
            return False 