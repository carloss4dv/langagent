"""
Langagent: Agente de respuesta a preguntas con LangGraph.

Este módulo expone las clases y funciones principales del
agente de respuesta a preguntas basado en vectorstores y LangGraph.
"""

# Versión del paquete
__version__ = "1.0.0"

# Imports principales para el usuario
from .core.lang_chain_agent import LangChainAgent
from .models.workflow import create_workflow
from .utils.document_loader import load_documents_from_directory
from .vectorstore import (
    create_embeddings,
    VectorStoreFactory,
    VectorStoreBase,
    ChromaVectorStore,
    MilvusVectorStore
)

# Exportar solo los elementos que queremos exponer en el API público
__all__ = [
    'LangChainAgent',
    'create_workflow',
    'load_documents_from_directory',
    'create_embeddings',
    'VectorStoreFactory',
    'VectorStoreBase',
    'ChromaVectorStore',
    'MilvusVectorStore'
]
