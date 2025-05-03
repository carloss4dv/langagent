"""
Módulo para la configuración de embeddings.

Este módulo proporciona funciones para configurar diferentes modelos de embeddings
que serán utilizados por las vectorstores.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_milvus.utils.sparse import BM25SparseEmbedding

logger = logging.getLogger(__name__)

def create_embeddings(model_name: str = "intfloat/multilingual-e5-large-instruct",
                     device: str = "cpu",
                     **kwargs) -> Tuple[Embeddings, BM25SparseEmbedding]:
    """
    Crea los modelos de embeddings denso y disperso.
    
    Args:
        model_name: Nombre del modelo de HuggingFace a utilizar
        device: Dispositivo donde ejecutar el modelo ('cpu' o 'cuda')
        **kwargs: Argumentos adicionales para la configuración
        
    Returns:
        Tuple[Embeddings, BM25SparseEmbedding]: Tupla con los modelos de embeddings densos y dispersos
    """
    try:
        # Crear embeddings densos
        dense_embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            **kwargs
        )
        
        # Crear embeddings dispersos con un corpus vacío inicialmente
        # El corpus se actualizará cuando se añadan documentos
        sparse_embeddings = BM25SparseEmbedding(corpus=[],language="es")
        
        logger.info(f"Modelos de embeddings creados: {model_name}")
        return dense_embeddings, sparse_embeddings
    except Exception as e:
        # Si falla con cuda, intentar con CPU
        if device == "cuda":
            logger.warning(f"Error al crear embeddings con CUDA: {str(e)}. Intentando con CPU...")
            return create_embeddings(model_name=model_name, device="cpu", **kwargs)
        else:
            logger.error(f"Error al crear embeddings: {str(e)}")
            raise 