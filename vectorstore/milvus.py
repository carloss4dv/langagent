"""
Implementación de VectorStoreBase para Milvus/Zilliz.

Este módulo proporciona una implementación concreta de la interfaz VectorStoreBase
para la base de datos vectorial Milvus/Zilliz, aprovechando sus capacidades avanzadas
como particionamiento y búsqueda híbrida.
"""

import os
import time
import logging
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
        import re
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
            
        Returns:
            Milvus: Instancia de la vectorstore creada
        """
        connection_args = self._get_connection_args()
        logger.info(f"Creando vectorstore Milvus con colección {collection_name}")
        
        try:
            # Primero, crear la colección base con drop_old=True para asegurar una colección limpia
            milvus_db = Milvus.from_documents(
                documents=documents if not self.use_partitioning else documents[:1],  # Solo un documento para inicializar
                embedding=embeddings,
                collection_name=collection_name,
                connection_args=connection_args,
                drop_old=True,  # Forzar recreación
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
            # Proporcionar información detallada sobre el problema de conexión
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
        Crea un retriever a partir de una vectorstore Milvus.
        
        Args:
            vectorstore: Instancia de Milvus
            k: Número de documentos a recuperar
            similarity_threshold: Umbral de similitud para la recuperación
            
        Returns:
            BaseRetriever: Retriever configurado
        """
        if k is None:
            k = VECTORSTORE_CONFIG.get("k_retrieval", 6)
        
        if similarity_threshold is None:
            similarity_threshold = VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
        
        logger.info(f"Creando retriever Milvus con k={k} y umbral={similarity_threshold}")
        
        # Guardar las opciones como atributos del retriever para usarlas luego
        retriever = vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": k,
                "score_threshold": similarity_threshold
            }
        )
        
        # Añadir atributos adicionales al retriever
        retriever.vectorstore = vectorstore
        retriever.collection_name = vectorstore.col.name
        retriever.partition_names = self.collection_mapping.get(vectorstore.col.name, [])
        
        return retriever
    
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
        if not self.use_partitioning or not hasattr(retriever, 'vectorstore'):
            # Usar el método estándar si no hay particionamiento
            return self._standard_retrieve(retriever, query, max_retries)
        
        # Si usamos particionamiento, intentamos identificar las particiones relevantes
        ambito = self._get_ambito_from_query(query)
        vectorstore = retriever.vectorstore
        search_params = retriever.search_kwargs.copy()
        
        # Si tenemos un ámbito identificado y tenemos particiones, hacer búsqueda específica
        if ambito and hasattr(retriever, 'partition_names') and retriever.partition_names:
            partition_name = self._normalize_partition_name(ambito)
            
            # Si la partición existe en esta colección
            if partition_name in retriever.partition_names:
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