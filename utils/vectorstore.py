"""
Módulo para la configuración de embeddings y vectorstore.

Este módulo proporciona funciones para configurar embeddings y crear/cargar
una base de datos vectorial (vectorstore) para la recuperación de información.
"""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from typing import List, Optional
from langagent.config.config import VECTORSTORE_CONFIG
from chromadb.utils.embedding_functions import chroma_langchain_embedding_function
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings
from chromadb.api.types import EmbeddingFunction
import logging
import time

logger = logging.getLogger(__name__)

def create_embeddings(model_name: str = "intfloat/multilingual-e5-large-instruct"):
    """
    Crea un modelo de embeddings.
    
    Args:
        model_name (str): Nombre del modelo de embeddings a utilizar.
        inference_mode (str): Modo de inferencia ('local' o 'remote').
        
    Returns:
        NomicEmbeddings: Modelo de embeddings configurado.
    """
    embeddings = HuggingFaceEmbeddings(model_name=model_name, model_kwargs={"device": "cuda"})
    return embeddings

def create_vectorstore(documents: List[Document], embeddings, persist_directory: str):
    """
    Crea una base de datos vectorial a partir de documentos y la guarda en disco.
    
    Args:o
        documents (List[Document]): Lista de documentos a indexar.
        embeddings: Modelo de embeddings a utilizar.
        persist_directory (str): Directorio donde persistir la base de datos.
        
    Returns:
        Chroma: Base de datos vectorial creada.
    """
    return Chroma.from_documents(
        documents=documents, 
        embedding=embeddings, 
        persist_directory=persist_directory
    )

def load_vectorstore(persist_directory: str, embeddings):
    """
    Carga una base de datos vectorial desde disco.
    
    Args:
        persist_directory (str): Directorio donde está persistida la base de datos.
        embeddings: Modelo de embeddings a utilizar.
        
    Returns:
        Chroma: Base de datos vectorial cargada.
    """
    return Chroma(persist_directory=persist_directory, embedding_function=embeddings)

def create_retriever(vectorstore, k=None, similarity_threshold=0.7):
    """Crea un retriever a partir de un vectorstore."""
    if k is None:
        k = VECTORSTORE_CONFIG["k_retrieval"]
    
    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": k,
            "score_threshold": similarity_threshold
        }
    )
    
    # Añadir logging para seguimiento
    logger.info(f"Retriever creado con k={k} y umbral de similitud={similarity_threshold}")
    
    return retriever

def retrieve_documents(retriever, query, max_retries=3):
    """Recupera documentos con manejo de errores y reintentos."""
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
