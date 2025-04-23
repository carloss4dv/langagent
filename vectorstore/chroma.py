"""
Implementación de VectorStoreBase para ChromaDB.

Este módulo proporciona una implementación concreta de la interfaz VectorStoreBase
para la base de datos vectorial ChromaDB.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore
from langchain_chroma import Chroma
from langagent.vectorstore.base import VectorStoreBase
from langagent.config.config import VECTORSTORE_CONFIG

logger = logging.getLogger(__name__)

class ChromaVectorStore(VectorStoreBase):
    """Implementación de VectorStoreBase para ChromaDB."""
    
    def create_vectorstore(self, documents: List[Document], embeddings: Embeddings, 
                         collection_name: str, **kwargs) -> Chroma:
        """
        Crea una nueva vectorstore Chroma con los documentos proporcionados.
        
        Args:
            documents: Lista de documentos a indexar
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección (usado como directorio)
            
        Returns:
            Chroma: Instancia de la vectorstore creada
        """
        # En Chroma, el collection_name se usa como parte del directorio
        persist_directory = kwargs.get('persist_directory', None)
        
        # Si no se proporciona un directorio, usar el predeterminado
        if not persist_directory:
            base_dir = VECTORSTORE_CONFIG.get("default_chroma_dir", "./chroma")
            persist_directory = os.path.join(base_dir, collection_name)
        
        logger.info(f"Creando vectorstore Chroma en {persist_directory}")
        
        return Chroma.from_documents(
            documents=documents, 
            embedding=embeddings, 
            persist_directory=persist_directory
        )
    
    def load_vectorstore(self, embeddings: Embeddings, collection_name: str, 
                       **kwargs) -> Chroma:
        """
        Carga una vectorstore Chroma existente.
        
        Args:
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección (usado como directorio)
            
        Returns:
            Chroma: Instancia de la vectorstore cargada
        """
        # En Chroma, el collection_name se usa como parte del directorio
        persist_directory = kwargs.get('persist_directory', None)
        
        # Si no se proporciona un directorio, usar el predeterminado
        if not persist_directory:
            base_dir = VECTORSTORE_CONFIG.get("default_chroma_dir", "./chroma")
            persist_directory = os.path.join(base_dir, collection_name)
        
        logger.info(f"Cargando vectorstore Chroma desde {persist_directory}")
        
        return Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
    
    def create_retriever(self, vectorstore: Chroma, k: Optional[int] = None, 
                      similarity_threshold: float = 0.7, **kwargs) -> BaseRetriever:
        """
        Crea un retriever a partir de una vectorstore Chroma.
        
        Args:
            vectorstore: Instancia de Chroma
            k: Número de documentos a recuperar
            similarity_threshold: Umbral de similitud para la recuperación
            
        Returns:
            BaseRetriever: Retriever configurado
        """
        if k is None:
            k = VECTORSTORE_CONFIG.get("k_retrieval", 6)
        
        if similarity_threshold is None:
            similarity_threshold = VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
        
        logger.info(f"Creando retriever con k={k} y umbral={similarity_threshold}")
        
        return vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": k,
                "score_threshold": similarity_threshold
            }
        )
    
    def retrieve_documents(self, retriever: BaseRetriever, query: str, 
                         max_retries: int = 3) -> List[Document]:
        """
        Recupera documentos de un retriever con manejo de errores y reintentos.
        
        Args:
            retriever: Retriever a utilizar
            query: Consulta para la búsqueda
            max_retries: Número máximo de reintentos en caso de error
            
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