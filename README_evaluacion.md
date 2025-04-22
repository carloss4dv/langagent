# Evaluación de Agente RAG con DeepEval

Este módulo proporciona herramientas para evaluar el rendimiento del agente LangChain utilizando la biblioteca DeepEval. Las evaluaciones se centran en métricas específicas para sistemas RAG (Retrieval-Augmented Generation) e incluyen datos de costo y rendimiento.

## Requisitos previos

Antes de utilizar estos scripts de evaluación, asegúrese de tener instaladas las siguientes dependencias:

```bash
pip install deepeval langchain langchain_core matplotlib numpy
```

## Descripción de archivos

- **evaluate.py**: Contiene la clase `AgentEvaluator` que permite evaluar las respuestas del agente LangChain utilizando diversas métricas de DeepEval. También captura metadatos como tiempo de ejecución y costos de tokens.
  
- **run_evaluation.py**: Script que ejecuta una evaluación completa con casos de prueba predefinidos o personalizados y genera un informe JSON detallado con los resultados.

## Métricas de evaluación utilizadas

Las métricas implementadas en este módulo son:

1. **Answer Relevancy**: Evalúa qué tan relevante es la respuesta generada respecto a la pregunta.

2. **Faithfulness**: Evalúa si la respuesta generada es fiel a la información proporcionada en el contexto de recuperación, detectando alucinaciones.

3. **Contextual Relevancy**: Evalúa si el contexto recuperado es relevante para responder la pregunta.

4. **Contextual Recall**: Evalúa si toda la información necesaria para responder la pregunta está presente en el contexto recuperado.

5. **Contextual Precision**: Evalúa si el contexto recuperado contiene información precisa y útil para responder la pregunta.

Además, se capturan las siguientes métricas de rendimiento y costo:

1. **Completion Time**: Tiempo que tarda el modelo en generar una respuesta.

2. **Token Cost**: Costo estimado de la generación basado en los tokens de entrada y salida.

3. **Token Usage**: Número de tokens utilizados en la entrada, salida y total.

## Ejemplos de uso

### Evaluar una pregunta específica

```python
from evaluate import AgentEvaluator

# Crear el evaluador
evaluador = AgentEvaluator()

# Evaluar una pregunta individual
resultados = evaluador.evaluar_pregunta("¿Qué es un cubo BIC?")

# Mostrar resultados
print(resultados)
```

### Ejecutar la evaluación completa desde línea de comandos

Para ejecutar la evaluación con los casos de prueba predefinidos:

```bash
python run_evaluation.py --data_dir "/ruta/a/documentos" --chroma_dir "/ruta/a/base/chroma" --modelo "nombre_modelo" --verbose
```

Opciones disponibles:

- `--data_dir`: Directorio con los documentos de conocimiento.
- `--chroma_dir`: Directorio base para las bases de datos vectoriales.
- `--modelo`: Nombre del modelo LLM principal a utilizar.
- `--modelo2`: Nombre del segundo modelo LLM a utilizar.
- `--salida`: Ruta para guardar el archivo de resultados JSON.
- `--verbose`: Mostrar información detallada, incluyendo costos y tiempos.
- `--casos`: Ruta a un archivo JSON con casos de prueba personalizados.

### Evaluar una lista personalizada de preguntas

```python
from evaluate import AgentEvaluator

# Crear el evaluador
evaluador = AgentEvaluator()

# Lista de preguntas a evaluar
preguntas = [
    "¿Qué es un cubo BIC?",
    "¿Cómo puedo consultar ventas por región?",
    "¿Cuáles son los cubos disponibles?"
]

# Ejecutar evaluación
resultados = evaluador.evaluar(preguntas)

# Procesar los resultados
for i, test_case in enumerate(evaluador.test_cases):
    print(f"\nPregunta: {test_case.input}")
    print(f"Respuesta: {test_case.actual_output}")
    
    # Acceder a los metadatos de rendimiento
    if hasattr(test_case, "metadata"):
        metadata = test_case.metadata
        print(f"Tiempo de completado: {metadata.get('completion_time', 0):.4f} segundos")
        
        token_info = metadata.get("token_info", {})
        if token_info:
            print(f"Tokens totales: {token_info.get('total_tokens', 0)}")
            if "cost_estimate" in token_info:
                print(f"Costo estimado: ${token_info['cost_estimate'].get('total_cost', 0):.6f}")
```

### Crear un archivo JSON de casos de prueba personalizados

Puedes crear un archivo JSON con casos de prueba personalizados para usarlos con el script de evaluación:

```json
[
  {
    "pregunta": "¿Qué es un cubo BIC?",
    "respuesta_esperada": "Un cubo BIC es un conjunto de datos estructurados que incluye información sobre..."
  },
  {
    "pregunta": "¿Cómo puedo filtrar por región?",
    "respuesta_esperada": null
  }
]
```

Y luego usarlo con:

```bash
python run_evaluation.py --casos "ruta/a/mis_casos.json" --verbose
```

## Resultados de evaluación

Los resultados de la evaluación se guardan en formato JSON en el directorio `resultados_evaluacion` con la siguiente estructura mejorada:

```json
{
  "timestamp": "2025-04-19T15:30:45.123456",
  "metricas_evaluadas": ["AnswerRelevancy", "Faithfulness", "ContextualRelevancy"],
  "casos_evaluados": [
    {
      "pregunta": "¿Qué es un cubo BIC?",
      "respuesta_generada": "Un cubo BIC es...",
      "respuesta_esperada": "",
      "contexto_recuperado": ["Texto del primer documento recuperado", "Texto del segundo documento..."],
      "scores": {
        "AnswerRelevancy": 0.85,
        "Faithfulness": 0.92,
        "ContextualRelevancy": 0.78
      },
      "metadata": {
        "completion_time": 1.2345,
        "token_info": {
          "input_tokens": 320,
          "output_tokens": 150,
          "total_tokens": 470,
          "cost_estimate": {
            "input_cost": 0.00016,
            "output_cost": 0.000225,
            "total_cost": 0.000385
          }
        },
        "model_info": "nombre_del_modelo",
        "hallucination_score": 0.12,
        "answer_score": 0.89,
        "relevant_cubos": ["BIC", "VENTAS"],
        "ambito": "finanzas",
        "is_consulta": false
      },
      "raw_output": {
        "pregunta": "¿Qué es un cubo BIC?",
        "resultado_completo": {
          "generation": "Un cubo BIC es...",
          "documents": [...],
          "relevant_cubos": [...],
          "response_metadata": {...}
        },
        "tiempo_completado": 1.2345
      }
    },
    // más resultados...
  ]
}
```

## Personalización

### Personalizar casos de prueba

Para personalizar los casos de prueba, puedes:

1. Modificar la lista `CASOS_PRUEBA` en el archivo `run_evaluation.py`.
2. Crear un archivo JSON con tus casos de prueba y usarlo con la opción `--casos`.

Cada caso debe incluir una "pregunta" y opcionalmente una "respuesta_esperada".

### Personalizar métricas y umbrales

Para modificar qué métricas se evalúan o ajustar sus umbrales, modifica el diccionario `self.metrics` en el constructor de la clase `AgentEvaluator` en el archivo `evaluate.py`:

```python
self.metrics = {
    "answer_relevancy": AnswerRelevancyMetric(threshold=0.7),  # Cambia el umbral según tus necesidades
    "faithfulness": FaithfulnessMetric(threshold=0.7),
    # Agrega o quita métricas según sea necesario
}
``` 