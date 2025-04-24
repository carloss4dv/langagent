"""
Módulo de compatibilidad para la funcionalidad de vectorstore.

Este módulo proporciona versiones compatibles de las antiguas funciones
que redirigen a la nueva implementación basada en VectorStoreBase.
"""

from langchain_core.documents import Document
from typing import List, Optional
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_core.retrievers import BaseRetriever
import logging
import os

from langagent.vectorstore import (
    VectorStoreFactory,
    create_embeddings as create_embeddings_new
)
from langagent.config.config import VECTORSTORE_CONFIG

logger = logging.getLogger(__name__)

# Función de compatibilidad para crear embeddings
def create_embeddings(model_name: str = "intfloat/multilingual-e5-large-instruct"):
    """
    Función de compatibilidad para crear un modelo de embedding.
    
    Args:
        model_name (str): Nombre del modelo de embeddings a utilizar.
        
    Returns:
        Embeddings: Modelo de embeddings configurado.
    """
    return create_embeddings_new(model_name=model_name)

# Función de compatibilidad para crear vectorstore
def create_vectorstore(documents: List[Document], embeddings: Embeddings, persist_directory: str) -> VectorStore:
    """
    Función de compatibilidad para crear una base de datos vectorial.
    
    Args:
        documents (List[Document]): Lista de documentos a indexar.
        embeddings: Modelo de embeddings a utilizar.
        persist_directory (str): Directorio donde persistir la base de datos.
        
    Returns:
        VectorStore: Base de datos vectorial creada.
    """
    # Extraer el nombre de colección del directorio
    collection_name = os.path.basename(persist_directory)
    
    # Obtener la instancia de vectorstore
    vectorstore_handler = VectorStoreFactory.get_vectorstore_instance()
    
    return vectorstore_handler.create_vectorstore(
        documents=documents,
        embeddings=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory
    )

# Función de compatibilidad para cargar vectorstore
def load_vectorstore(persist_directory: str, embeddings: Embeddings) -> VectorStore:
    """
    Función de compatibilidad para cargar una base de datos vectorial.
    Si la base de datos no existe, se crea automáticamente.
    
    Args:
        persist_directory (str): Directorio donde está persistida la base de datos.
        embeddings: Modelo de embeddings a utilizar.
        
    Returns:
        VectorStore: Base de datos vectorial cargada.
    """
    # Extraer el nombre de colección del directorio
    collection_name = os.path.basename(persist_directory)
    
    # Obtener la instancia de vectorstore
    vectorstore_handler = VectorStoreFactory.get_vectorstore_instance()
    
    return vectorstore_handler.load_vectorstore(
        embeddings=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory,
        check_collection_exists=True,  # Verificar si la colección existe antes de crear
        always_drop_old=False          # No recrear si ya existe
    )

# Función de compatibilidad para crear retriever
def create_retriever(vectorstore: VectorStore, k: Optional[int] = None, similarity_threshold: float = 0.7) -> BaseRetriever:
    """
    Función de compatibilidad para crear un retriever.
    
    Args:
        vectorstore: Instancia del vectorstore
        k: Número de documentos a recuperar
        similarity_threshold: Umbral de similitud para la recuperación
        
    Returns:
        BaseRetriever: Retriever configurado
    """
    # Obtener la instancia de vectorstore
    vectorstore_handler = VectorStoreFactory.get_vectorstore_instance()
    
    return vectorstore_handler.create_retriever(
        vectorstore=vectorstore,
        k=k,
        similarity_threshold=similarity_threshold
    )

# Función de compatibilidad para recuperar documentos
def retrieve_documents(retriever: BaseRetriever, query: str, max_retries: int = 3) -> List[Document]:
    """
    Función de compatibilidad para recuperar documentos.
    
    Args:
        retriever: Retriever a utilizar
        query: Consulta para la búsqueda
        max_retries: Número máximo de reintentos en caso de error
        
    Returns:
        List[Document]: Lista de documentos recuperados
    """
    # Obtener la instancia de vectorstore
    vectorstore_handler = VectorStoreFactory.get_vectorstore_instance()
    
    return vectorstore_handler.retrieve_documents(
        retriever=retriever,
        query=query,
        max_retries=max_retries
    )
