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
        """Inicializa el retriever personalizado.
        
        Args:
            vectorstore: Instancia de Milvus vectorstore
            search_kwargs: Parámetros de búsqueda
            filter_threshold: Umbral de similitud para filtrado
        """
        self.vectorstore = vectorstore  # Usar self.vectorstore en lugar de self._vectorstore
        self.search_kwargs = search_kwargs or {}  # Usar self.search_kwargs en lugar de self._search_kwargs
        self.filter_threshold = filter_threshold
        logger.info(f"MilvusFilterRetriever inicializado con: vectorstore={type(vectorstore).__name__}, "
                   f"search_kwargs={self.search_kwargs}")
        super().__init__()
    
    def _get_relevant_documents(self, query: str, *, run_manager=None):
        """Recupera documentos sin filtrado de metadatos.
        
        Args:
            query: Consulta de texto
            run_manager: Gestor de ejecución (opcional)
            
        Returns:
            List[Document]: Documentos recuperados
        """
        try:
            logger.info(f"Buscando documentos relevantes para: {query}")
            return self.vectorstore.similarity_search(query, **self.search_kwargs)
        except Exception as e:
            logger.error(f"Error en búsqueda estándar: {e}")
            # Si falla con los parámetros proporcionados, intentar con parámetros mínimos
            fallback_kwargs = {"k": self.search_kwargs.get("k", 6)}
            logger.info(f"Reintentando con parámetros básicos: {fallback_kwargs}")
            try:
                return self.vectorstore.similarity_search(query, **fallback_kwargs)
            except Exception as e2:
                logger.error(f"Error en búsqueda con parámetros básicos: {e2}")
                # Último intento completamente básico
                logger.info("Último intento de búsqueda sin parámetros")
                return self.vectorstore.similarity_search(query)
    
    def search_documents(self, query: str, metadata_filters=None):
        """Realiza búsqueda con filtrado por metadatos.
        
        Args:
            query: Consulta de texto
            metadata_filters: Diccionario con filtros de metadatos
            
        Returns:
            List[Document]: Documentos filtrados por metadatos
        """
        logger.info(f"Búsqueda con filtros de metadatos: {metadata_filters}")
        
        if not metadata_filters:
            logger.info("No hay filtros de metadatos, usando búsqueda estándar")
            return self._get_relevant_documents(query)
        
        # Preparar expresión de filtro
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
                logger.info(f"Expresión de filtro generada: {filter_expr}")
        except Exception as e:
            logger.error(f"Error al crear expresión de filtro: {e}")
        
        # Varios intentos de búsqueda con diferentes configuraciones
        # Intento 1: Usar los parámetros configurados + filtro
        try:
            if not hasattr(self, 'vectorstore') or self.vectorstore is None:
                raise AttributeError("Vectorstore no está configurada correctamente")
                
            search_params = self.search_kwargs.copy()
            if filter_expr:
                search_params["filter"] = filter_expr
                
            logger.info(f"Intento 1: Búsqueda con parámetros completos: {search_params}")
            return self.vectorstore.similarity_search(query, **search_params)
        except Exception as e:
            logger.error(f"Error en intento 1: {e}")
        
        # Intento 2: Usar solo filtro con parámetros básicos
        try:
            basic_params = {"k": 6}
            if filter_expr:
                basic_params["filter"] = filter_expr
                
            logger.info(f"Intento 2: Búsqueda con parámetros básicos + filtro: {basic_params}")
            return self.vectorstore.similarity_search(query, **basic_params)
        except Exception as e:
            logger.error(f"Error en intento 2: {e}")
        
        # Intento 3: Usar solo parámetros básicos sin filtro
        try:
            logger.info("Intento 3: Búsqueda con parámetros básicos sin filtro")
            return self.vectorstore.similarity_search(query, k=6)
        except Exception as e:
            logger.error(f"Error en intento 3: {e}")
            
        # Intento 4: Búsqueda sin parámetros
        try:
            logger.info("Intento 4: Búsqueda sin parámetros")
            return self.vectorstore.similarity_search(query)
        except Exception as e:
            logger.error(f"Error en intento 4: {e}")
            logger.error("Todos los intentos de búsqueda fallaron")
            # Devolver lista vacía si todo falla
            return []

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
            "secure": milvus_secure,
            "timeout": 60  # Aumentar el timeout para operaciones largas
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
        from langchain.vectorstores import Milvus
        
        if not documents:
            logger.error("No se pueden crear vectorstores sin documentos.")
            return None
        
        # Recuperar los argumentos de conexión
        connection_args = self._get_connection_args()
        
        # Obtener opciones para la vectorstore
        drop_old = kwargs.get("drop_old", True)
        consistency_level = kwargs.get("consistency_level", "Session")
        search_params = kwargs.get("search_params", {"metric_type": "COSINE"})
        
        # Usar auto_id=True para que Milvus genere IDs automáticamente
        auto_id = kwargs.get("auto_id", True)
        
        # Si estamos utilizando particionamiento, procesar los documentos por partición
        if self.use_partitioning:
            # Agrupar documentos por partición
            partitioned_docs = self._prepare_documents_for_partitioning(documents)
            logger.info(f"Documentos agrupados en {len(partitioned_docs)} particiones")
            
            # Crear la colección principal (si no existe)
            try:
                # Primero crear la colección principal para todas las particiones
                logger.info(f"Creando vectorstore principal para colección {collection_name}")
                
                # Usar un subconjunto de documentos para la colección principal
                # Esto es necesario para establecer la estructura de la colección
                sample_docs = []
                if partitioned_docs:
                    # Tomar una muestra de cada partición
                    for partition, docs in partitioned_docs.items():
                        if docs:
                            sample_docs.append(docs[0])
                else:
                    # Si no hay particiones, usar el primer documento
                    sample_docs = [documents[0]]
                
                vectorstore = Milvus.from_documents(
                    documents=sample_docs,
                    embedding=embeddings,
                    collection_name=collection_name,
                    drop_old=drop_old,
                    connection_args=connection_args,
                    consistency_level=consistency_level,
                    search_params=search_params,
                    auto_id=auto_id  # Añadir auto_id=True aquí
                )
                
                logger.info(f"Vectorstore principal creada con {len(sample_docs)} documentos de muestra")
                
                # Crear particiones y añadir documentos a cada una
                for partition_key, partition_docs in partitioned_docs.items():
                    if not partition_docs:
                        logger.warning(f"No hay documentos para la partición {partition_key}, omitiendo")
                        continue
                        
                    try:
                        # Crear la partición si no existe
                        logger.info(f"Procesando partición {partition_key} con {len(partition_docs)} documentos")
                        
                        # Verificar si la partición ya existe
                        has_partition = False
                        if hasattr(vectorstore, "col") and vectorstore.col is not None:
                            try:
                                partitions = vectorstore.col.partitions
                                has_partition = partition_key in [p.name for p in partitions]
                            except Exception as e:
                                logger.error(f"Error al verificar particiones existentes: {e}")
                        
                        # Crear la partición si no existe
                        if not has_partition:
                            logger.info(f"Creando partición: {partition_key}")
                            try:
                                if hasattr(vectorstore, "col") and vectorstore.col is not None:
                                    vectorstore.col.create_partition(partition_key)
                                    logger.info(f"Partición {partition_key} creada correctamente")
                            except Exception as e:
                                logger.error(f"Error al crear partición {partition_key}: {e}")
                        
                        # Añadir documentos a la partición
                        logger.info(f"Añadiendo {len(partition_docs)} documentos a la partición {partition_key}")
                        
                        # Usar el método add_texts de la vectorstore para añadir documentos a la partición
                        try:
                            texts = [doc.page_content for doc in partition_docs]
                            metadatas = [doc.metadata for doc in partition_docs]
                            
                            vectorstore.add_texts(
                                texts=texts,
                                metadatas=metadatas,
                                partition_name=partition_key,
                                auto_id=auto_id  # Añadir auto_id=True aquí también
                            )
                            
                            logger.info(f"Documentos añadidos correctamente a la partición {partition_key}")
                        except Exception as e:
                            logger.error(f"Error al procesar partición {partition_key}: {e}")
                    except Exception as e:
                        logger.error(f"Error al procesar partición {partition_key}: {e}")
                
                # Registrar las particiones que hemos creado
                try:
                    if hasattr(vectorstore, "col") and vectorstore.col is not None:
                        partitions = vectorstore.col.partitions
                        partition_names = [p.name for p in partitions]
                        self.collection_mapping[collection_name] = partition_names
                        logger.info(f"Particiones registradas para {collection_name}: {partition_names}")
                except Exception as e:
                    logger.error(f"Error al registrar particiones: {e}")
                
                return vectorstore
                
            except Exception as e:
                logger.error(f"Error al crear la vectorstore principal: {e}")
                return None
                
        else:
            # Enfoque sin particionamiento
            logger.info(f"Creando vectorstore sin particionamiento para colección {collection_name}")
            try:
                vectorstore = Milvus.from_documents(
                    documents=documents,
                    embedding=embeddings,
                    collection_name=collection_name,
                    drop_old=drop_old,
                    connection_args=connection_args,
                    consistency_level=consistency_level,
                    search_params=search_params,
                    auto_id=auto_id  # Añadir auto_id=True aquí
                )
                
                logger.info(f"Vectorstore creada correctamente con {len(documents)} documentos")
                return vectorstore
                
            except Exception as e:
                logger.error(f"Error al crear la vectorstore: {e}")
                return None
    
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
                retriever = MilvusFilterRetriever(vectorstore=vectorstore, search_kwargs=search_kwargs)
                logger.info("Retriever personalizado creado correctamente")
                return retriever
            except Exception as e:
                logger.error(f"Error al crear MilvusFilterRetriever: {str(e)}")
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
        
        # Obtener search_kwargs de manera segura dependiendo del tipo de retriever
        search_params = {}
        if isinstance(retriever, MilvusFilterRetriever):
            # Usar el método getter para obtener search_kwargs
            search_params = retriever.search_kwargs.copy()
        elif hasattr(retriever, 'search_kwargs') and retriever.search_kwargs is not None:
            search_params = retriever.search_kwargs.copy()
        
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