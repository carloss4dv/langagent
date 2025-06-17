
# Configuración optimizada basada en análisis NLTK y métricas reales
CHUNK_STRATEGY_CONFIG = {
    "available_strategies": ["small", "medium", "large"],
    "default_strategy": "medium",
    "max_retries": 2,
    
    # Umbrales de evaluación basados en métricas reales observadas
    "evaluation_thresholds": {
        "faithfulness": 0.82,        # Promedio de mejores configuraciones
        "context_precision": 0.65,   # Promedio de mejores configuraciones
        "context_recall": 0.70,      # Promedio de mejores configuraciones
        "answer_relevance": 0.78     # Promedio de mejores configuraciones
    },
    
    # Configuración de colecciones por estrategia (basadas en análisis NLTK)
    "collection_config": {
        "small": {
            "collection_name": "adaptive_collection_178_118_167",
            "chunk_sizes": [178, 118, 167],
            "chunk_overlaps": [26, 17, 25],
            "description": "Oración Grande → Párrafo Mediano → Sección Pequeña",
            "semantic_strategy": "adaptive_nltk"
        },
        "medium": {
            "collection_name": "adaptive_collection_81_118_170",
            "chunk_sizes": [81, 118, 170],
            "chunk_overlaps": [15, 17, 25],
            "description": "Párrafo Pequeño → Mediano → Grande",
            "semantic_strategy": "adaptive_nltk"
        },
        "large": {
            "collection_name": "adaptive_collection_453_141_116",
            "chunk_sizes": [453, 141, 116],
            "chunk_overlaps": [67, 21, 17],
            "description": "3 Oraciones → Párrafo Promedio → Frac. Sección",
            "semantic_strategy": "adaptive_nltk"
        },
    }
}

# Configuración de Vector Store optimizada
VECTORSTORE_CONFIG = {
    # Configuración adaptativa basada en análisis NLTK
    "use_adaptive_chunking": True,
    "adaptive_chunk_sizes": [167, 307, 755],  # Basado en métricas reales NLTK
    "adaptive_overlaps": [25, 46, 113],       # 15% de cada chunk size
    
    # Configuración de recuperación mejorada
    "k_retrieval": 15,                        # Incrementado basado en análisis
    "similarity_threshold": 0.65,             # Ajustado para mejor recall
    "max_docs_total": 20,                     # Incrementado para mejor contexto
    
    # Configuración de reranking optimizada
    "use_contextual_compression": True,
    "compression_top_k_multiplier": 2.5,     # Ajustado para balance precisión-recall
    "bge_max_length": 755,                    # Basado en mejor configuración NLTK
}