"""
OBSOLETO: Este módulo está obsoleto y se mantiene solo por compatibilidad.

Por favor, utiliza el módulo 'langagent.vectorstore' en su lugar que ofrece
una implementación más flexible y con soporte para múltiples bases de datos vectoriales.

Ejemplo:
    from langagent.vectorstore import create_embeddings, VectorStoreFactory
    
    # Crear embeddings
    embeddings = create_embeddings()
    
    # Crear vectorstore
    vectorstore_handler = VectorStoreFactory.get_vectorstore_instance('chroma')
    db = vectorstore_handler.create_vectorstore(...)
"""

# Importar del nuevo módulo para mantener compatibilidad
from langagent.vectorstore import create_embeddings
from langagent.vectorstore import VectorStoreFactory

# También importamos los módulos antiguos para compatibilidad
from langchain_chroma import Chroma
from langchain_core.documents import Document
from typing import List, Optional
from langagent.config.config import VECTORSTORE_CONFIG
import logging
import time

logger = logging.getLogger(__name__)

def create_embeddings(model_name: str = "intfloat/multilingual-e5-large-instruct"):
    """
    Crea un modelo de embedding.
    
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
    OBSOLETO: Usa vectorstore.ChromaVectorStore.create_vectorstore() en su lugar.
    
    Crea una base de datos vectorial a partir de documentos y la guarda en disco.
    """
    logger.warning("Función obsoleta: create_vectorstore. Usa el nuevo módulo vectorstore en su lugar.")
    handler = VectorStoreFactory.get_vectorstore_instance("chroma")
    collection_name = persist_directory.split("/")[-1] if "/" in persist_directory else persist_directory
    return handler.create_vectorstore(
        documents=documents,
        embeddings=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory
    )

def load_vectorstore(persist_directory: str, embeddings):
    """
    OBSOLETO: Usa vectorstore.ChromaVectorStore.load_vectorstore() en su lugar.
    
    Carga una base de datos vectorial desde disco.
    """
    logger.warning("Función obsoleta: load_vectorstore. Usa el nuevo módulo vectorstore en su lugar.")
    handler = VectorStoreFactory.get_vectorstore_instance("chroma")
    collection_name = persist_directory.split("/")[-1] if "/" in persist_directory else persist_directory
    return handler.load_vectorstore(
        embeddings=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory
    )

def create_retriever(vectorstore, k=None, similarity_threshold=0.7):
    """
    OBSOLETO: Usa vectorstore.ChromaVectorStore.create_retriever() en su lugar.
    
    Crea un retriever a partir de un vectorstore.
    """
    logger.warning("Función obsoleta: create_retriever. Usa el nuevo módulo vectorstore en su lugar.")
    handler = VectorStoreFactory.get_vectorstore_instance("chroma")
    return handler.create_retriever(
        vectorstore=vectorstore,
        k=k,
        similarity_threshold=similarity_threshold
    )

def retrieve_documents(retriever, query, max_retries=3):
    """
    OBSOLETO: Usa vectorstore.ChromaVectorStore.retrieve_documents() en su lugar.
    
    Recupera documentos con manejo de errores y reintentos.
    """
    logger.warning("Función obsoleta: retrieve_documents. Usa el nuevo módulo vectorstore en su lugar.")
    handler = VectorStoreFactory.get_vectorstore_instance("chroma")
    return handler.retrieve_documents(
        retriever=retriever,
        query=query,
        max_retries=max_retries
    )
