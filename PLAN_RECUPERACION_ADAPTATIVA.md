# Plan de Implementación: Recuperación Adaptativa con Evaluación Granular

## Objetivo
Implementar un sistema de recuperación adaptativa que utilice tres colecciones de fragmentos (256, 512, 1024 tokens) y un mecanismo de reintento inteligente basado en evaluación granular del LLM3 (evaluador).

## Arquitectura Propuesta

### 1. Modificaciones al Estado del Workflow

**Archivo:** `models/workflow.py`

#### Nuevos Campos en el Estado:
```python
# Añadir al StateGraph existente
chunk_strategy: str = "512"  # Valores: "256", "512", "1024"
retry_count: int = 0
evaluation_metrics: dict = {}  # Métricas granulares del evaluador
# max_retries = 2 (total 3 intentos) definido en constants.py
```

### 2. Sistema de Retrievers Múltiples

**Archivo:** `models/workflow.py` (función retrieve_documents)

#### Cambios Mínimos:
- Mantener la función `retrieve_documents` actual
- Añadir lógica de selección basada en `state.chunk_strategy`
- Crear un diccionario de retrievers inicializados para cada colección
- Modificar solo el retriever que se utiliza según el estado

#### Estructura:
```python
# En la inicialización del workflow
retrievers = {
    "256": create_retriever(collection_256),
    "512": create_retriever(collection_512), 
    "1024": create_retriever(collection_1024)
}

# En retrieve_documents
current_retriever = retrievers[state.chunk_strategy]
```

### 3. Evaluador Granular (LLM3)

**Archivo:** `prompts.py`

#### Nuevos Prompts para Evaluación Granular:

##### Para cada modelo (llama, mistral, qwen):
1. **`granular_evaluator`**: Prompt que evalúa múltiples métricas
   - Fidelidad (Faithfulness)
   - Precisión del Contexto (Context Precision) 
   - Exhaustividad del Contexto (Context Recall)
   - Formato de salida JSON estructurado

**Archivo:** `models/workflow.py`

#### Nueva Función de Evaluación:
- `evaluate_response_granular()`: Reemplaza o complementa `grade_generation_grounded_in_documents_and_question`
- Utiliza el nuevo prompt `granular_evaluator`
- Devuelve métricas estructuradas en lugar de solo "yes/no"

### 4. Enrutador Inteligente (Lógica Determinística)

**Archivo:** `models/workflow.py`

#### Nueva Función:
- `route_next_strategy()`: Decide la próxima estrategia basada en comparación simple de métricas
- **NO utiliza LLM** - solo comparaciones if/else con umbrales
- Actualiza `state.chunk_strategy` para el siguiente intento

#### Lógica de Enrutamiento (Determinística y Simple):
```python
def route_next_strategy(state):
    # Si ya hicimos 3 intentos (retry_count = 2), terminar siempre
    if state.retry_count >= 2:
        return "END"
    
    metrics = state.evaluation_metrics
    
    # Si las métricas están por encima de los umbrales, terminar
    if (metrics["faithfulness"] >= THRESHOLDS["faithfulness"] and
        metrics["context_precision"] >= THRESHOLDS["context_precision"] and
        metrics["context_recall"] >= THRESHOLDS["context_recall"]):
        return "END"
    
    # Incrementar contador de reintentos
    state.retry_count += 1
    
    # Context Recall bajo → necesitamos más contexto
    if metrics["context_recall"] < THRESHOLDS["context_recall"]:
        state.chunk_strategy = "1024"
        return "RETRY"
    
    # Context Precision bajo O Faithfulness bajo → necesitamos más precisión
    if (metrics["context_precision"] < THRESHOLDS["context_precision"] or
        metrics["faithfulness"] < THRESHOLDS["faithfulness"]):
        state.chunk_strategy = "256"
        return "RETRY"
    
    return "END"
```

### 5. Modificaciones en las Chains

**Archivo:** `models/workflow.py` (función que define el grafo)

#### Cambios en el Flujo:
1. **Después de `generate`**: Llamar a `evaluate_response_granular` (usa LLM3)
2. **Nuevo nodo `route_strategy`**: Lógica determinística simple (NO usa LLM)
3. **Modificar edges condicionales**: 
   - Si route_strategy() == "END" → END
   - Si route_strategy() == "RETRY" → `retrieve_documents` (con nueva estrategia)
   - Límite automático de 3 intentos total

#### Estructura del Grafo Modificada:
```
retrieve_documents → generate → evaluate_response_granular → route_strategy
                     ↑                                              ↓
                     └─────────── (if "RETRY") ────────────────────┘
```

### 6. Configuración de Retrievers

**Archivo:** `models/constants.py`

#### Nuevas Constantes:
```python
# Configuración de colecciones
COLLECTION_PATHS = {
    "256": "path/to/collection_256",
    "512": "path/to/collection_512", 
    "1024": "path/to/collection_1024"
}

# Umbrales de evaluación
EVALUATION_THRESHOLDS = {
    "faithfulness": 0.7,
    "context_precision": 0.6,
    "context_recall": 0.6
}

# Configuración de reintento
DEFAULT_CHUNK_STRATEGY = "512"
MAX_RETRIES = 2  # Total 3 intentos (inicial + 2 reintentos)
```

### 7. Inicialización del Sistema

**Archivo:** `core/lang_chain_agent.py` o `core/ambito_agent.py`

#### Modificaciones Mínimas:
- Inicializar los tres retrievers al inicio
- Pasar el diccionario de retrievers al workflow
- Mantener la interfaz existente intacta

## Puntos Críticos de Implementación

### 1. Compatibilidad Retroactiva
- Mantener el comportamiento por defecto (chunks 512) si no se especifica
- No romper funcionalidad existente
- Hacer que la recuperación adaptativa sea opcional

### 2. Gestión de Estado
- El estado debe persistir entre reintentos
- Limpiar estado al final de cada consulta completa
- Límite fijo de 3 intentos elimina riesgo de bucles infinitos

### 3. Manejo de Errores
- Si falla la evaluación granular, volver al sistema original
- Si falla el enrutador, usar estrategia por defecto
- Timeout en reintentos para evitar bucles largos

### 4. Optimización de Rendimiento
- Cachear retrievers inicializados
- Evitar re-inicialización innecesaria
- Mantener conexiones de BD abiertas

## Archivos a Modificar (Orden de Implementación)

1. **`models/constants.py`**: Añadir nuevas constantes
2. **`prompts.py`**: Añadir nuevos prompts para evaluación granular
3. **`models/workflow.py`**: Modificar estado y añadir nuevos nodos
4. **`core/lang_chain_agent.py`**: Inicializar múltiples retrievers
5. **`models/llm.py`**: Si es necesario añadir funciones de evaluación específicas

## Ventajas del Enfoque Propuesto

1. **Cambios Mínimos**: Solo se añaden parámetros al estado existente
2. **No Destructivo**: El comportamiento por defecto se mantiene
3. **Modular**: Cada componente es independiente
4. **Escalable**: Fácil añadir más estrategias en el futuro
5. **Testeable**: Cada componente puede probarse por separado
6. **Eficiente**: Solo el evaluador usa LLM, el enrutador es lógica simple
7. **Rápido**: Decisiones de estrategia instantáneas sin latencia de LLM
8. **Simple**: Límite fijo de 3 intentos, sin gestión compleja de historial

## Consideraciones Técnicas

### Gestión de Memoria
- Tres retrievers cargados simultáneamente
- Posible impacto en uso de memoria
- Considerar lazy loading si es necesario

### Latencia
- Evaluación granular añade tiempo de procesamiento (solo una llamada LLM extra)
- Decisión de estrategia es instantánea (sin LLM)
- Reintentos aumentan tiempo total, pero con decisiones inteligentes
- Optimizar prompts de evaluación para ser concisos

### Métricas y Monitoring
- Trackear qué estrategias se usan más frecuentemente
- Medir efectividad de cada tamaño de chunk
- Monitorear tasas de reintento por tipo de consulta

Esta implementación mantiene la arquitectura existente mientras añade la funcionalidad de recuperación adaptativa de manera no invasiva. 