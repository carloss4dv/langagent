"""
Módulo de configuración para el agente.

Este módulo contiene parámetros de configuración para los diferentes
componentes del sistema, permitiendo ajustar su comportamiento sin
modificar el código principal.
"""

# Configuración de LLM
LLM_CONFIG = {
    "model_temperature": 0.15,  # Controla la aleatoriedad de las respuestas (0-1)
    "max_tokens": 1024,        # Límite de tokens para las respuestas generadas
    "model_format": "json",    # Formato de salida (json, text, etc.)
    "default_model": "hf.co/unsloth/Mistral-Small-3.1-24B-Instruct-2503-GGUF",  # Modelo predeterminado para el LLM principal
    "default_model2": "qwen2.5:7b" # Modelo predeterminado para el LLM secundario (evaluación)
}

# Configuración de Vector Store
VECTORSTORE_CONFIG = {
    "chunk_size": 500,         # Tamaño de los fragmentos de texto para indexación
    "chunk_overlap": 50,        # Superposición entre fragmentos
    "k_retrieval": 6,          # Número de documentos a recuperar
    "similarity_threshold": 0.7,  # Umbral mínimo de similitud para considerar un documento relevante
    "max_docs_total": 15       # Aumentar el límite total de documentos
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
    "default_data_dir": "./data",           # Directorio predeterminado para datos
    "default_chroma_dir": "./chroma",       # Directorio predeterminado para la base de datos vectorial
    "log_dir": "./logs",                    # Directorio para archivos de registro
}

# Configuración de Seguridad
SECURITY_CONFIG = {
    "secret_key": "1356up7hsdjf4",  # Clave secreta para tokens JWT (cambiar en producción)
    "algorithm": "HS256",           # Algoritmo para tokens JWT
}
