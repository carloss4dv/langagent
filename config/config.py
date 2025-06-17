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
    "max_tokens": 2048,        # Límite de tokens para las respuestas generadas
    "model_format": "json",    # Formato de salida (json, text, etc.)
    "default_model": "mistral-small-3.1:24b",  # Modelo predeterminado para el LLM principal
    "default_model2": "qwen2.5:1.5b", # Modelo predeterminado para el LLM secundario (routing)
    "default_model3": "llama3.2:3bm" # Modelo predeterminado para el LLM tercero (eavluation)
}

# Configuración de Vector Store
VECTORSTORE_CONFIG = {
    "chunk_size": 167,         # Tamaño de los fragmentos de texto para indexación
    "chunk_overlap": 37,        # Superposición entre fragmentos
    "k_retrieval": 12,          # Número de documentos a recuperar
    "similarity_threshold": 0.7,  # Umbral mínimo de similitud para considerar un documento relevante
    "max_docs_total": 15,       # Aumentar el límite total de documentos
    "vector_db_type": "milvus", # Tipo de base de datos vectorial (chroma o milvus)
    
    # Configuración para Milvus/Zilliz Cloud
    "milvus_uri": os.getenv("ZILLIZ_CLOUD_URI", "http://localhost:19537"),
    "milvus_token": os.getenv("ZILLIZ_CLOUD_TOKEN", ""),
    "milvus_secure": os.getenv("ZILLIZ_CLOUD_SECURE", "True").lower() in ("true", "1", "t"),     # Usar conexión segura (para Zilliz Cloud)
    
    # Configuración de particionamiento para Milvus
    "use_partitioning": False,  # Desactivar particiones, usar filtrado en su lugar
    "partition_key_field": "ambito",  # Campo para particionamiento (si se activa)
    
    # Configuración para enfoque de colección única
    "use_single_collection": True,  # Usar una sola colección para todos los documentos
    "collection_name": "default_collection_646",  # Nombre de la colección unificada
    "always_update_collection": False,  # Si se deben actualizar documentos en colección existente
    "filter_by_metadata": True,  # Habilitar filtrado por metadatos en consultas
    
    # Configuración de búsqueda híbrida
    "use_hybrid_search": True,  # Activar búsqueda híbrida (vectorial + texto completo)
    
    # Configuración de generación de contexto
    "use_context_generation": False,  # Activar generación de contexto para chunks
    "log_context_generation": True,  # Mostrar logs detallados de la generación de contexto
    "context_batch_size": 20,        # Chunks por lote
    "context_max_workers": 3,        # Hilos concurrentes (no más de 5 para evitar rate limits)
    "skip_existing_context": True,   # Saltar chunks con contexto existente
    "persist_directory": "./vectordb",  # Directorio para persistir la vectorstore Chroma
    
    # Configuración de Recuperación Adaptativa - Múltiples Colecciones
    "adaptive_collections": {
        "369": "default_collection_369",
        "646": "default_collection_646", 
        "1094": "default_collection_1094",
    },
    "use_adaptive_retrieval": True,  # Activar recuperación adaptativa
    
    # Configuración de compresión contextual con BGE
    "use_contextual_compression": False,
    "bge_reranker_model": "BAAI/bge-reranker-v2-m3",
    "compression_top_k_multiplier": 3,  # Recuperar 36 docs si k=12, luego rerank a 12
    "bge_device": "auto",  # Detectar automáticamente CPU/GPU
    "bge_max_length": 755,
}

# Configuración de SQL
SQL_CONFIG = {
    "db_uri": "oracle+cx_oracle://C##DM_ACADEMICO:YourPassword123@127.0.0.1:15210/?service_name=XEPDB1",  # URI de conexión a la base de datos
    "dialect": "oracle",                           # Dialecto SQL (sqlite, postgres, etc.)
    "enable_sql_queries": True,                    # Habilitar consultas SQL
    "max_results": 20,                             # Número máximo de resultados por consulta
    "default_table": "pdi_docencia"                # Tabla por defecto para consultas
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

# Configuración de Chunk Strategies y Recuperación Adaptativa
CHUNK_STRATEGY_CONFIG = {
    "available_strategies": ["369", "646", "1094"],  # Estrategias disponibles
    "default_strategy": "646",     # Estrategia por defecto
    "max_retries": 2,             # Total 3 intentos (inicial + 2 reintentos)
    
    # Umbrales de evaluación granular
    "evaluation_thresholds": {
        "faithfulness": 0.8,
        "context_precision": 0.8,
        "context_recall": 0.7,
        "answer_relevance": 0.7
    },
    
    # Configuración de colecciones por estrategia
    "collection_config": {
        "167": {
            "collection_name": "segeda_collection_167",
            "chunk_size": 167,
            "chunk_overlap": 17
        },
        "307": {
            "collection_name": "segeda_collection_307",
            "chunk_size": 307,
            "chunk_overlap": 31
        },
        "755": {
            "collection_name": "segeda_collection_755",
            "chunk_size": 755,
            "chunk_overlap": 76
        }
    }
}

# Rutas y Directorios
PATHS_CONFIG = {
    "default_data_dir": "./output_md",        # Directorio predeterminado para datos
    "default_vectorstore_dir": "./vectordb",  # Directorio base para vectorstores
    "default_chroma_dir": "./vectordb",       # Directorio específico para Chroma
    "log_dir": "./logs",                      # Directorio para archivos de registro
}

# Configuración de Logging
LOGGING_CONFIG = {
    "level": "INFO",                         # Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    "log_to_file": True,                      # Guardar logs en archivo
    "log_to_console": True,                   # Mostrar logs en consola
    "file_max_bytes": 10 * 1024 * 1024,      # Tamaño máximo del archivo de log (10MB)
    "file_backup_count": 5,                   # Número de archivos de backup
    "console_colors": True,                   # Usar colores en la consola
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
}

# Configuración de Seguridad
SECURITY_CONFIG = {
    "secret_key": "1356up7hsdjf4",  # Clave secreta para tokens JWT (cambiar en producción)
    "algorithm": "HS256",           # Algoritmo para tokens JWT
}
