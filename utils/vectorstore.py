"""
Módulo para la configuración de embeddings y vectorstore.

Este módulo proporciona funciones para configurar embeddings y crear/cargar
una base de datos vectorial (vectorstore) para la recuperación de información.
"""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from typing import List, Optional
from langagent.config.config import VECTORSTORE_CONFIG
from chromadb.utils.embedding_functions import create_langchain_embedding
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings
from chromadb.api.types import EmbeddingFunction



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

def create_retriever(vectorstore, k: int = None):
    """
    Crea un recuperador (retriever) a partir de una base de datos vectorial.
    
    Args:
        vectorstore: Base de datos vectorial.
        k (int, optional): Número de documentos a recuperar.
        
    Returns:
        Retriever: Recuperador configurado.
    """
    # Usar valor de configuración si no se proporciona k
    k = k if k is not None else VECTORSTORE_CONFIG["k_retrieval"]
    
    res = vectorstore.as_retriever(k=k)
    return res
