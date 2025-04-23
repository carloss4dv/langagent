"""
Módulo de configuración para el agente.

Este módulo contiene parámetros de configuración para los diferentes
componentes del sistema, permitiendo ajustar su comportamiento sin
modificar el código principal.
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de LLM
LLM_CONFIG = {
    "model_temperature": 0.15,  # Controla la aleatoriedad de las respuestas (0-1)
    "max_tokens": 1024,        # Límite de tokens para las respuestas generadas
    "model_format": "json",    # Formato de salida (json, text, etc.)
    "default_model": "hf.co/unsloth/Mistral-Small-3.1-24B-Instruct-2503-GGUF",  # Modelo predeterminado para el LLM principal
    "default_model2": "qwen2.5:3b", # Modelo predeterminado para el LLM secundario (routing)
    "default_model3": "qwen2.5:1.5b" # Modelo predeterminado para el LLM tercero (eavluation)
}

# Configuración de Vector Store
VECTORSTORE_CONFIG = {
    "chunk_size": 256,         # Tamaño de los fragmentos de texto para indexación
    "chunk_overlap": 50,        # Superposición entre fragmentos
    "k_retrieval": 6,          # Número de documentos a recuperar
    "similarity_threshold": 0.7,  # Umbral mínimo de similitud para considerar un documento relevante
    "max_docs_total": 15,       # Aumentar el límite total de documentos
    "vector_db_type": "milvus", # Tipo de base de datos vectorial (chroma o milvus)
    
    # Configuración para Milvus/Zilliz Cloud
    "milvus_uri": os.getenv("ZILLIZ_CLOUD_URI", "http://localhost:19530"),
    "milvus_token": os.getenv("ZILLIZ_CLOUD_TOKEN", ""),
    "milvus_secure": os.getenv("ZILLIZ_CLOUD_SECURE", "True").lower() in ("true", "1", "t"),     # Usar conexión segura (para Zilliz Cloud)
    
    # Configuración de particionamiento para Milvus
    "use_partitioning": False,  # Desactivar particiones, usar filtrado en su lugar
    "partition_key_field": "ambito",  # Campo para particionamiento (si se activa)
    
    # Configuración para enfoque de colección única
    "use_single_collection": True,  # Usar una sola colección para todos los documentos
    "unified_collection_name": "UnifiedKnowledgeBase",  # Nombre de la colección unificada
    "always_update_collection": True,  # Si se deben actualizar documentos en colección existente
    "filter_by_metadata": True,  # Habilitar filtrado por metadatos en consultas
    
    # Configuración de búsqueda híbrida
    "use_hybrid_search": True,  # Activar búsqueda híbrida (vectorial + texto completo)
}

# Configuración de API
API_CONFIG = {
    "token_expiration_minutes": 15,  # Tiempo de expiración de tokens JWT
    "rate_limit": 100,              # Límite de solicitudes por usuario
    "max_request_size": 10240,      # Tamaño máximo de solicitud en bytes
    "default_port": 5001,           # Puerto predeterminado para la API
}

# Configuración del Workflow
WORKFLOW_CONFIG = {
    "max_retries": 3,              # Número máximo de reintentos
    "relevance_threshold": 0.8,    # Umbral para considerar una respuesta relevante
}

# Rutas y Directorios
PATHS_CONFIG = {
    "default_data_dir": "./output_md",        # Directorio predeterminado para datos
    "default_vectorstore_dir": "./vectordb",  # Directorio base para vectorstores
    "default_chroma_dir": "./chroma",         # Directorio específico para Chroma
    "log_dir": "./logs",                      # Directorio para archivos de registro
}

# Configuración de Seguridad
SECURITY_CONFIG = {
    "secret_key": "1356up7hsdjf4",  # Clave secreta para tokens JWT (cambiar en producción)
    "algorithm": "HS256",           # Algoritmo para tokens JWT
}
