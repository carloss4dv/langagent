# Agente Local con LangGraph, LLaMA3, Chroma Vector Store y llama-index

Este proyecto implementa un agente local de respuesta a preguntas utilizando LangGraph, LLaMA3, Chroma vector store y capacidades avanzadas de RAG proporcionadas por llama-index.

## Características

- **RAG Adaptativo**: Enruta preguntas al vector store basado en el contenido
- **RAG Correctivo**: Implementa un mecanismo de reintento (hasta 3 veces) cuando las respuestas no son satisfactorias
- **Técnicas Avanzadas de RAG**:
  - `dual_chunks`: Divide documentos en chunks pequeños para recuperación precisa y chunks grandes para síntesis
  - `document_summary`: Crea resúmenes de documentos para preguntas que requieren visión general
  - `router`: Selecciona dinámicamente la mejor estrategia de recuperación según la pregunta
  - `optimize_embeddings`: Optimiza la representación vectorial de los documentos
- **Autenticación**: Sistema de autenticación basado en tokens JWT para la API
- **Visualización en Terminal**: Adaptado para entornos sin interfaz gráfica

## Estructura del Proyecto

```
langagent/
├── api/                  # Módulos para la API FastAPI
│   ├── __init__.py
│   └── fastapi_app.py    # Implementación de la API
├── auth/                 # Módulos para autenticación
│   ├── __init__.py
│   └── authentication.py # Funciones de autenticación JWT
├── config/               # Configuraciones
│   └── __init__.py
├── data/                 # Directorio para datos
│   └── __init__.py
├── models/               # Modelos y flujo de trabajo
│   ├── __init__.py
│   ├── llm.py            # Configuración de modelos de lenguaje
│   └── workflow.py       # Implementación del flujo de trabajo con LangGraph
├── utils/                # Utilidades
│   ├── __init__.py
│   ├── document_loader.py       # Carga de documentos markdown
│   ├── terminal_visualization.py # Visualización en terminal
│   ├── vectorstore.py           # Configuración de vectorstore
│   └── llamaindex_integration.py # Integración con llama-index
├── __init__.py
├── main.py               # Script principal
├── main_llamaindex.py    # Script principal con integración llama-index
└── requirements.txt      # Dependencias del proyecto
```

## Requisitos

Ver el archivo `requirements.txt` para la lista completa de dependencias. Las principales son:

- langchain y langgraph
- chromadb
- llama-index
- unstructured[md]
- fastapi y uvicorn
- authlib

## Instalación

1. Crea un entorno virtual (recomendado):
   ```
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

2. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```

## Uso

### Modo Interactivo con llama-index

Para iniciar el agente en modo interactivo con las capacidades avanzadas de llama-index:

```
python -m langagent.main_llamaindex --data_dir ./data --chroma_dir ./chroma --local_llm llama3 --use_advanced_rag
```

### Técnicas Avanzadas de RAG

Puedes especificar qué técnicas avanzadas de RAG utilizar:

```
python -m langagent.main_llamaindex --data_dir ./data --chroma_dir ./chroma --local_llm llama3 --use_advanced_rag --advanced_techniques dual_chunks document_summary
```

Las técnicas disponibles son:
- `dual_chunks`: Para recuperación precisa y síntesis contextual
- `document_summary`: Para preguntas que requieren resúmenes
- `router`: Para selección dinámica de estrategias de recuperación
- `optimize_embeddings`: Para optimización de embeddings

### Responder a una Pregunta Específica

Para responder a una pregunta específica con técnicas avanzadas:

```
python -m langagent.main_llamaindex --data_dir ./data --chroma_dir ./chroma --local_llm llama3 --use_advanced_rag --question "¿Qué son los alumnos matriculados?"
```

### Iniciar la API

Para iniciar la API FastAPI:

```
uvicorn langagent.api.fastapi_app:app --host 0.0.0.0 --port 5001
```

## Mecanismo de Reintento

El sistema implementa un mecanismo de reintento que:

1. Evalúa si la respuesta generada es relevante y no contiene alucinaciones
2. Si la respuesta no es satisfactoria, realiza hasta 3 intentos
3. Si después de 3 intentos no se obtiene una respuesta satisfactoria, devuelve la pregunta original

## Adaptación para Terminal

Todas las visualizaciones han sido adaptadas para entornos de terminal, utilizando formato de texto en lugar de gráficos. El módulo `terminal_visualization.py` proporciona funciones para mostrar información de manera clara en la terminal.

## Notas Importantes

- El sistema está configurado para trabajar con archivos markdown (.md) utilizando la librería unstructured[md]
- Se requiere tener instalado Ollama con los modelos LLaMA3 disponibles localmente
- La base de datos vectorial (Chroma) se guarda en el directorio especificado para su reutilización
- Las técnicas avanzadas de RAG requieren más recursos computacionales pero proporcionan mejores resultados
- El router de llama-index puede mejorar significativamente la precisión de las respuestas al seleccionar la mejor estrategia de recuperación
