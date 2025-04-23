"""
Implementación de VectorStoreBase para Milvus/Zilliz.

Este módulo proporciona una implementación concreta de la interfaz VectorStoreBase
para la base de datos vectorial Milvus/Zilliz, aprovechando sus capacidades avanzadas
como filtrado por metadatos y búsqueda híbrida.
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
from langchain_milvus import Milvus, BM25BuiltInFunction
from langagent.vectorstore.base import VectorStoreBase
from langagent.config.config import VECTORSTORE_CONFIG
from langagent.models.constants import CUBO_TO_AMBITO, AMBITOS_CUBOS

logger = logging.getLogger(__name__)

class MilvusVectorStore(VectorStoreBase):
    """Implementación de VectorStoreBase para Milvus/Zilliz con soporte para búsqueda híbrida."""
    
    def __init__(self):
        """Inicializa la implementación de Milvus Vector Store."""
        self.use_hybrid_search = VECTORSTORE_CONFIG.get("use_hybrid_search", False)
        self.collection_name = VECTORSTORE_CONFIG.get("collection_name", "unified")
        self.partition_key_field = VECTORSTORE_CONFIG.get("partition_key_field", "ambito")
    
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
    
    def create_vectorstore(self, documents: List[Document], embeddings: Embeddings, 
                         collection_name: str, **kwargs) -> Milvus:
        """
        Crea una nueva vectorstore Milvus con los documentos proporcionados.
        Configura particiones basadas en un campo clave en los metadatos.
        
        Args:
            documents: Lista de documentos a indexar
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección en Milvus
            
        Returns:
            Milvus: Instancia de la vectorstore creada
        """
        if not documents:
            logger.error("No se pueden crear vectorstores sin documentos.")
            return None
        
        # Recuperar los argumentos de conexión
        connection_args = self._get_connection_args()
        
        # Obtener opciones para la vectorstore
        drop_old = kwargs.get("drop_old", True)
        consistency_level = kwargs.get("consistency_level", "Strong")
        
        # Determinar si queremos usar búsqueda híbrida
        use_hybrid_search = kwargs.get("use_hybrid_search", self.use_hybrid_search)
        partition_key_field = kwargs.get("partition_key_field", self.partition_key_field)
        
        try:
            logger.info(f"Creando vectorstore para colección {collection_name}")
            
            # Preparar argumentos base
            vs_kwargs = {
                "connection_args": connection_args,
                "collection_name": collection_name,
                "embedding": embeddings,
                "drop_old": drop_old,
                "consistency_level": consistency_level
            }
            
            # Si queremos usar particionamiento por ámbito o cubo
            if partition_key_field:
                logger.info(f"Configurando particionamiento por campo: {partition_key_field}")
                vs_kwargs["partition_key_field"] = partition_key_field
            
            # Si queremos usar búsqueda híbrida (denso + sparse)
            if use_hybrid_search:
                logger.info("Configurando búsqueda híbrida con BM25")
                vs_kwargs["builtin_function"] = BM25BuiltInFunction()
                vs_kwargs["vector_field"] = ["dense", "sparse"]  # 'dense' para embeddings, 'sparse' para BM25
            
            # Crear la vectorstore
            vectorstore = Milvus.from_documents(
                documents=documents,
                **vs_kwargs
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
        
        # Determinar si queremos usar búsqueda híbrida
        use_hybrid_search = kwargs.get("use_hybrid_search", self.use_hybrid_search)
        
        try:
            # Preparar argumentos para cargar la vectorstore
            vs_kwargs = {
                "embedding_function": embeddings,
                "collection_name": collection_name,
                "connection_args": connection_args
            }
            
            # Si queremos usar búsqueda híbrida
            if use_hybrid_search:
                logger.info("Configurando función BM25 para búsqueda híbrida")
                vs_kwargs["builtin_function"] = BM25BuiltInFunction()
                vs_kwargs["vector_field"] = ["dense", "sparse"]  # 'dense' para embeddings, 'sparse' para BM25
            
            # Cargar la vectorstore
            milvus_db = Milvus(**vs_kwargs)
            
            # Verificar que la colección existe realmente
            if not hasattr(milvus_db, 'col') or milvus_db.col is None:
                logger.warning(f"La colección {collection_name} no existe o no se pudo cargar correctamente")
                
                # Crear una colección nueva con un documento de ejemplo para inicializar
                logger.info(f"Creando nueva colección {collection_name}")
                empty_doc = Document(page_content="Documento de inicialización", metadata={"source": "init"})
                
                # Usar los mismos argumentos pero con from_documents
                return Milvus.from_documents(
                    documents=[empty_doc],
                    embedding=embeddings,
                    collection_name=collection_name,
                    connection_args=connection_args,
                    drop_old=False,
                    builtin_function=BM25BuiltInFunction() if use_hybrid_search else None,
                    vector_field=["dense", "sparse"] if use_hybrid_search else None
                )
            
            return milvus_db
            
        except Exception as e:
            logger.error(f"Error al cargar colección {collection_name}: {str(e)}")
            
            # Crear una colección nueva con un documento de ejemplo para inicializar
            try:
                logger.info(f"Intentando crear nueva colección {collection_name}")
                empty_doc = Document(page_content="Documento de inicialización", metadata={"source": "init"})
                
                return Milvus.from_documents(
                    documents=[empty_doc],
                    embedding=embeddings,
                    collection_name=collection_name,
                    connection_args=connection_args,
                    drop_old=False,
                    builtin_function=BM25BuiltInFunction() if use_hybrid_search else None,
                    vector_field=["dense", "sparse"] if use_hybrid_search else None
                )
                
            except Exception as create_error:
                # Si falla la creación, registrar el error y proporcionar información detallada
                logger.error(f"Error al crear colección {collection_name}: {str(create_error)}")
                if "connection" in str(e).lower():
                    logger.error(f"Problema de conexión a Milvus. Verifique que el servidor esté en ejecución en {connection_args['uri']} " +
                                f"y que las credenciales sean correctas.")
                    logger.error("Asegúrese de configurar las variables de entorno ZILLIZ_CLOUD_URI y ZILLIZ_CLOUD_TOKEN correctamente.")
                raise e
    
    def create_retriever(self, vectorstore: Milvus, k: Optional[int] = None, 
                       similarity_threshold: float = 0.7, **kwargs) -> BaseRetriever:
        """
        Crea un retriever para una vectorstore Milvus.
        Configura el retriever para usar búsqueda con filtrado y/o híbrida.
        
        Args:
            vectorstore: Instancia de Milvus vectorstore
            k: Número de documentos a recuperar
            similarity_threshold: Umbral mínimo de similitud
            
        Returns:
            BaseRetriever: Retriever configurado para Milvus
        """
        # Obtener parámetros de búsqueda desde la configuración o parámetros
        k = k or VECTORSTORE_CONFIG.get("k_retrieval", 4)
        
        # Determinar el tipo de búsqueda a utilizar
        search_type = kwargs.get("search_type", "similarity")
        if self.use_hybrid_search and search_type == "similarity":
            search_type = "mmr"  # Usar MMR para búsqueda híbrida
            logger.info("Usando búsqueda MMR para soporte híbrido")
        
        # Configuración para MMR (Maximum Marginal Relevance)
        mmr_lambda = kwargs.get("mmr_lambda", 0.5)  # 0.5 balance entre relevancia y diversidad
        
        # Crear los parámetros de búsqueda
        search_kwargs = {
            "k": k,
            "score_threshold": similarity_threshold
        }
        
        # Configuración específica para MMR
        if search_type == "mmr":
            search_kwargs["fetch_k"] = k * 2  # Recuperar más documentos para luego reordenarlos
            search_kwargs["lambda_mult"] = mmr_lambda
        
        # Si usamos búsqueda híbrida, configurar el reranker
        if self.use_hybrid_search:
            search_kwargs["ranker_type"] = "weighted"
            search_kwargs["ranker_params"] = {"weights": [0.7, 0.3]}  # 70% dense, 30% sparse
        
        try:
            logger.info(f"Creando retriever con tipo de búsqueda: {search_type}")
            retriever = vectorstore.as_retriever(
                search_type=search_type,
                search_kwargs=search_kwargs
            )
            return retriever
        except Exception as e:
            logger.error(f"Error al crear retriever: {e}")
            # Fallback simple
            return vectorstore.as_retriever()
    
    def retrieve_documents(self, retriever: BaseRetriever, query: str, 
                         metadata_filters: Optional[Dict[str, Any]] = None,
                         max_retries: int = 3) -> List[Document]:
        """
        Recupera documentos de un retriever con filtrado por metadatos.
        
        Args:
            retriever: Retriever a utilizar
            query: Consulta para la búsqueda
            metadata_filters: Filtros de metadatos a aplicar (ej: {"ambito": "seguridad"})
            max_retries: Número máximo de reintentos en caso de error
            
        Returns:
            List[Document]: Lista de documentos recuperados
        """
        logger.info(f"Recuperando documentos para query: {query}")
        
        if metadata_filters:
            logger.info(f"Aplicando filtros de metadatos: {metadata_filters}")
            
            # Construir expresión de filtrado para Milvus
            filter_expr = self._build_filter_expression(metadata_filters)
            logger.info(f"Expresión de filtro: {filter_expr}")
            
            # Intentar recuperar con filtros
            for attempt in range(max_retries):
                try:
                    # Usar invoke() con parámetro filter
                    docs = retriever.invoke(query, filter=metadata_filters)
                    
                    if not docs:
                        logger.warning(f"No se encontraron documentos con filtros: {metadata_filters}")
                        if attempt == max_retries - 1:
                            # En el último intento, probar sin filtros
                            logger.info("Intentando recuperar sin filtros como último recurso")
                            return retriever.invoke(query)
                    else:
                        return docs
                    
                except Exception as e:
                    logger.error(f"Error en intento {attempt + 1} con filtros: {str(e)}")
                    if attempt == max_retries - 1:
                        logger.info("Intentando recuperar sin filtros como último recurso")
                        try:
                            return retriever.invoke(query)
                        except Exception as e2:
                            logger.error(f"Error final sin filtros: {str(e2)}")
                            return []
                    time.sleep(1)  # Esperar antes de reintentar
        else:
            # Sin filtros, usar método estándar
            for attempt in range(max_retries):
                try:
                    docs = retriever.invoke(query)
                    
                    if not docs:
                        logger.warning(f"No se encontraron documentos relevantes para: {query}")
                        return []
                    
                    return docs
                    
                except Exception as e:
                    logger.error(f"Error en intento {attempt + 1}: {str(e)}")
                    if attempt == max_retries - 1:
                        logger.error("Se agotaron los reintentos")
                        return []
                    time.sleep(1)  # Esperar antes de reintentar
    
    def _build_filter_expression(self, metadata_filters: Dict[str, Any]) -> str:
        """
        Construye una expresión de filtro para Milvus a partir de un diccionario de filtros.
        
        Args:
            metadata_filters: Diccionario con filtros de metadatos
            
        Returns:
            str: Expresión de filtro para Milvus
        """
        expressions = []
        
        for key, value in metadata_filters.items():
            if value is None:
                continue
                
            # Manejar diferentes tipos de datos
            if isinstance(value, bool):
                value_str = str(value).lower()
                expressions.append(f'{key} == "{value_str}"')
            elif isinstance(value, (int, float)):
                expressions.append(f'{key} == {value}')
            elif isinstance(value, list):
                if not value:
                    continue
                value_items = [f'"{item}"' if isinstance(item, str) else str(item) for item in value]
                expressions.append(f'{key} in [{", ".join(value_items)}]')
            else:
                value_str = str(value)
                expressions.append(f'{key} == "{value_str}"')
        
        if not expressions:
            return ""
            
        return " && ".join(expressions)
    
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