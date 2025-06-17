# ============================================================================
# CONFIGURACIONES ADAPTATIVAS GENERADAS POR CHUNK_ANALYZER V2.0
# Basadas en análisis semántico del corpus UZ y métricas de evaluación reales
# ============================================================================

CHUNK_STRATEGIES_ADAPTIVE_TRIPLETS = {
    # Percentiles Robustos: Basado en percentiles P25, P50, P75 para manejar variabilidad
    "145_small": {
        "collection_name": "adaptive_collection_145_s",
        "chunk_size": 145,
        "chunk_overlap": 48,
        "semantic_basis": "robust_percentiles",
        "triplet_id": 1
    },
    "210_medium": {
        "collection_name": "adaptive_collection_210_m",
        "chunk_size": 210,
        "chunk_overlap": 70,
        "semantic_basis": "robust_percentiles",
        "triplet_id": 1
    },
    "368_large": {
        "collection_name": "adaptive_collection_368_l",
        "chunk_size": 368,
        "chunk_overlap": 122,
        "semantic_basis": "robust_percentiles",
        "triplet_id": 1
    },
    
    # Rangos Adaptativos: P10 con mínimo 150, mediana, P90 con máximo 1200
    "150_small": {
        "collection_name": "adaptive_collection_150_s",
        "chunk_size": 150,
        "chunk_overlap": 50,
        "semantic_basis": "adaptive_ranges",
        "triplet_id": 2
    },
    "210_medium": {
        "collection_name": "adaptive_collection_210_m",
        "chunk_size": 210,
        "chunk_overlap": 70,
        "semantic_basis": "adaptive_ranges",
        "triplet_id": 2
    },
    "735_large": {
        "collection_name": "adaptive_collection_735_l",
        "chunk_size": 735,
        "chunk_overlap": 245,
        "semantic_basis": "adaptive_ranges",
        "triplet_id": 2
    },
    
    # Tipo de Contenido: Atributos (1.5x mediana) → Dim P60 → Dim P85
    "351_small": {
        "collection_name": "adaptive_collection_351_s",
        "chunk_size": 351,
        "chunk_overlap": 117,
        "semantic_basis": "content_type_aware",
        "triplet_id": 3
    },
    "273_medium": {
        "collection_name": "adaptive_collection_273_m",
        "chunk_size": 273,
        "chunk_overlap": 91,
        "semantic_basis": "content_type_aware",
        "triplet_id": 3
    },
    "575_large": {
        "collection_name": "adaptive_collection_575_l",
        "chunk_size": 575,
        "chunk_overlap": 191,
        "semantic_basis": "content_type_aware",
        "triplet_id": 3
    },
    
    # Métricas + Variabilidad: Basado en mejor actual (755) con ajuste por variabilidad
    "453_small": {
        "collection_name": "adaptive_collection_453_s",
        "chunk_size": 453,
        "chunk_overlap": 151,
        "semantic_basis": "performance_variability_optimized",
        "triplet_id": 4
    },
    "755_medium": {
        "collection_name": "adaptive_collection_755_m",
        "chunk_size": 755,
        "chunk_overlap": 251,
        "semantic_basis": "performance_variability_optimized",
        "triplet_id": 4
    },
    "1359_large": {
        "collection_name": "adaptive_collection_1359_l",
        "chunk_size": 1359,
        "chunk_overlap": 425,
        "semantic_basis": "performance_variability_optimized",
        "triplet_id": 4
    },
    
    # Cobertura Completa: P20 (min 120), P55, P88 (max 1500) - cubre todo el espectro
    "141_small": {
        "collection_name": "adaptive_collection_141_s",
        "chunk_size": 141,
        "chunk_overlap": 47,
        "semantic_basis": "full_coverage",
        "triplet_id": 5
    },
    "272_medium": {
        "collection_name": "adaptive_collection_272_m",
        "chunk_size": 272,
        "chunk_overlap": 90,
        "semantic_basis": "full_coverage",
        "triplet_id": 5
    },
    "768_large": {
        "collection_name": "adaptive_collection_768_l",
        "chunk_size": 768,
        "chunk_overlap": 256,
        "semantic_basis": "full_coverage",
        "triplet_id": 5
    },
    
    # Granularidad Múltiple: Multi-atributo (2.5x) → Dim P40 → Dim P80
    "709_small": {
        "collection_name": "adaptive_collection_709_s",
        "chunk_size": 709,
        "chunk_overlap": 226,
        "semantic_basis": "multi_granular",
        "triplet_id": 6
    },
    "196_medium": {
        "collection_name": "adaptive_collection_196_m",
        "chunk_size": 196,
        "chunk_overlap": 65,
        "semantic_basis": "multi_granular",
        "triplet_id": 6
    },
    "469_large": {
        "collection_name": "adaptive_collection_469_l",
        "chunk_size": 469,
        "chunk_overlap": 156,
        "semantic_basis": "multi_granular",
        "triplet_id": 6
    },
    
}

# Configuración para usar en CHUNK_STRATEGY_CONFIG
ADAPTIVE_TRIPLET_STRATEGIES = {
    "triplet_1": {
        "small": "145_small",
        "medium": "210_medium", 
        "large": "368_large",
        "description": "Percentiles Robustos"
    },
    "triplet_2": {
        "small": "150_small",
        "medium": "210_medium", 
        "large": "735_large",
        "description": "Rangos Adaptativos"
    },
    "triplet_3": {
        "small": "351_small",
        "medium": "273_medium", 
        "large": "575_large",
        "description": "Tipo de Contenido"
    },
    "triplet_4": {
        "small": "453_small",
        "medium": "755_medium", 
        "large": "1359_large",
        "description": "Métricas + Variabilidad"
    },
    "triplet_5": {
        "small": "141_small",
        "medium": "272_medium", 
        "large": "768_large",
        "description": "Cobertura Completa"
    },
    "triplet_6": {
        "small": "709_small",
        "medium": "196_medium", 
        "large": "469_large",
        "description": "Granularidad Múltiple"
    },
}
