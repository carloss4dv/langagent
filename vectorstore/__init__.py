"""
Paquete vectorstore para la gestión de bases de datos vectoriales.

Este paquete proporciona interfaces e implementaciones para diferentes
bases de datos vectoriales, manteniendo una API común para su uso en la aplicación.
"""

from langagent.vectorstore.base import VectorStoreBase, VectorStoreFactory
from langagent.vectorstore.chroma import ChromaVectorStore
from langagent.vectorstore.milvus import MilvusVectorStore, MilvusFilterRetriever
from langagent.vectorstore.embeddings import create_embeddings

__all__ = [
    'VectorStoreBase',
    'VectorStoreFactory',
    'ChromaVectorStore',
    'MilvusVectorStore',
    'MilvusFilterRetriever',
    'create_embeddings'
] 