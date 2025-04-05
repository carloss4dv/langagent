# Agente Local con LangGraph, LLaMA3 y Chroma Vector Store

Este proyecto es una refactorización del notebook original en scripts de Python separados, adaptados para su uso en entornos de terminal. El sistema implementa un agente local de respuesta a preguntas utilizando LangGraph, LLaMA3 y Chroma vector store.

## Características

- **RAG Adaptativo**: Enruta preguntas al vector store basado en el contenido
- **RAG Correctivo**: Implementa un mecanismo de reintento (hasta 3 veces) cuando las respuestas no son satisfactorias
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
│   └── vectorstore.py           # Configuración de vectorstore
├── __init__.py
├── main.py               # Script principal
└── requirements.txt      # Dependencias del proyecto
```

## Requisitos

Ver el archivo `requirements.txt` para la lista completa de dependencias. Las principales son:

- langchain y langgraph
- chromadb
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

### Modo Interactivo

Para iniciar el agente en modo interactivo:

```
python -m langagent.main --data_dir ./data --chroma_dir ./chroma --local_llm llama3
```

### Responder a una Pregunta Específica

Para responder a una pregunta específica:

```
python -m langagent.main --data_dir ./data --chroma_dir ./chroma --local_llm llama3 --question "¿Qué son los alumnos matriculados?"
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
