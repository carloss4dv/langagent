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
                     device: str = "cuda", **kwargs) -> Tuple[Embeddings, BM25SparseEmbedding]:
    """
    Crea los modelos de embeddings denso y disperso.
    
    Args:
        model_name (str): Nombre del modelo de embeddings denso a utilizar.
        device (str): Dispositivo donde ejecutar el modelo ("cuda" o "cpu").
        **kwargs: Argumentos adicionales para el modelo.
        
    Returns:
        Tuple[Embeddings, BM25SparseEmbedding]: Tupla con el modelo de embeddings denso y el modelo BM25.
    """
    try:
        model_kwargs = {"device": device}
        
        # Añadir argumentos adicionales si se proporcionan
        if kwargs:
            model_kwargs.update(kwargs)
        
        logger.info(f"Creando modelo de embeddings denso {model_name} en dispositivo {device}")
        dense_embeddings = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs)
        
        logger.info("Creando modelo de embeddings disperso BM25")
        sparse_embeddings = BM25SparseEmbedding()
        
        return dense_embeddings, sparse_embeddings
    except Exception as e:
        # Si falla con cuda, intentar con CPU
        if device == "cuda":
            logger.warning(f"Error al crear embeddings con CUDA: {str(e)}. Intentando con CPU...")
            return create_embeddings(model_name=model_name, device="cpu", **kwargs)
        else:
            logger.error(f"Error al crear embeddings: {str(e)}")
            raise 