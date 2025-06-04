"""
Módulo para la configuración de embeddings.

Este módulo proporciona funciones para configurar diferentes modelos de embeddings
que serán utilizados por las vectorstores.
"""

from typing import Optional, Dict, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

def create_embeddings(model_name: str = "intfloat/multilingual-e5-large-instruct", 
                     device: str = "cuda", **kwargs) -> Embeddings:
    """
    Crea un modelo de embeddings.
    
    Args:
        model_name (str): Nombre del modelo de embeddings a utilizar.
        device (str): Dispositivo donde ejecutar el modelo ("cuda" o "cpu").
        **kwargs: Argumentos adicionales para el modelo.
        
    Returns:
        Embeddings: Modelo de embeddings configurado.
    """
    try:
        model_kwargs = {"device": device}
        
        # Añadir argumentos adicionales si se proporcionan
        if kwargs:
            model_kwargs.update(kwargs)
        
        logger.info(f"Creando modelo de embeddings {model_name} en dispositivo {device}")
        embeddings = HuggingFaceEmbeddings(model_name=model_name, model_kwargs=model_kwargs)
        
        return embeddings
    except Exception as e:
        # Si falla con cuda, intentar con CPU
        if device == "cuda":
            logger.warning(f"Error al crear embeddings con CUDA: {str(e)}. Intentando con CPU...")
            return create_embeddings(model_name=model_name, device="cpu", **kwargs)
        else:
            logger.error(f"Error al crear embeddings: {str(e)}")
            raise 