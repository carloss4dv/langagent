# LangAgent: Agente con LangGraph, LLaMA3 y Chroma Vector Store

<div align="center">
  <!-- Nota: Puedes añadir un logo personalizado en esta ubicación -->
  <br>
  <em>Un sistema RAG con enrutamiento inteligente y mecanismos de reintento</em>
</div>

## 🌟 Descripción

LangAgent es un sistema de respuesta a preguntas (Question Answering) que implementa un agente local utilizando LangGraph, LLaMA3 y Chroma Vector Store. El sistema organiza el conocimiento en "cubos" temáticos dentro de diferentes "ámbitos", permitiendo un enrutamiento inteligente de preguntas y mecanismos de reintento para garantizar respuestas de alta calidad.

## 🔍 Características Principales

- **Organización Jerárquica del Conocimiento**: Estructura de "cubos" y "ámbitos" para organizar documentos
- **RAG Adaptativo**: Enrutamiento inteligente de preguntas al vector store basado en el contenido
- **RAG Correctivo**: Mecanismo de reintento (hasta 3 intentos) cuando las respuestas no son satisfactorias
- **Evaluación Múltiple**: Evalúa tanto la relevancia de los documentos como la calidad de las respuestas
- **Autenticación Segura**: Sistema de autenticación basado en tokens JWT para la API
- **Optimizado para Terminal**: Adaptado para entornos sin interfaz gráfica

## 🔄 Workflow del Sistema

El sistema implementa un flujo de trabajo sofisticado basado en LangGraph:

<!-- Puedes incluir aquí el diagrama del workflow generado -->

El workflow consta de tres nodos principales:
1. **Route Question**: Determina qué cubos son relevantes para la pregunta
2. **Retrieve**: Recupera documentos relevantes de los cubos seleccionados
3. **Generate**: Genera una respuesta basada en los documentos recuperados

## 📁 Estructura del Proyecto

```
langagent/
├── api/                  # Módulos para la API FastAPI
│   ├── __init__.py
│   └── fastapi_app.py    # Implementación de la API
├── auth/                 # Módulos para autenticación
│   ├── __init__.py
│   └── authentication.py # Funciones de autenticación JWT
├── config/               # Configuraciones
│   ├── __init__.py
│   └── config.py         # Configuraciones del sistema
├── data/                 # Directorio para datos
│   └── __init__.py
├── models/               # Modelos y flujo de trabajo
│   ├── __init__.py
│   ├── constants.py      # Constantes del sistema
│   ├── llm.py            # Configuración de modelos de lenguaje
│   └── workflow.py       # Implementación del flujo con LangGraph
├── utils/                # Utilidades
│   ├── __init__.py
│   ├── document_loader.py       # Carga de documentos markdown
│   ├── terminal_visualization.py # Visualización en terminal
│   └── vectorstore.py           # Configuración de vectorstore
├── __init__.py
├── main.py               # Script principal
└── requirements.txt      # Dependencias del proyecto
```

## 🛠️ Componentes Técnicos

- **Modelos LLM**: Utiliza modelos de Ollama (LLaMA3) para diferentes tareas
- **Embeddings**: HuggingFace Embeddings (multilingual-e5-large-instruct)
- **Vector Store**: Chroma DB para almacenamiento y recuperación eficiente
- **Framework de Flujo**: LangGraph para orquestar el flujo de trabajo
- **API**: FastAPI para exponer la funcionalidad como servicio web

## 📋 Requisitos

Las principales dependencias son:

- Python 3.10+
- langchain y langgraph
- chromadb
- huggingface_hub
- unstructured[md]
- fastapi y uvicorn
- authlib
- ollama (instalado localmente)

Ver el archivo `requirements.txt` para la lista completa de dependencias.

## 🚀 Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/carloss4dv/langagent.git
   cd langagent
   ```

2. Crea un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Asegúrate de tener Ollama instalado con los modelos LLaMA3 disponibles localmente:
   ```bash
   ollama pull llama3
   ```

## 💻 Uso

### Modo Interactivo

Para iniciar el agente en modo interactivo:

```bash
python -m langagent.main --data_dir ./data --chroma_dir ./chroma --local_llm llama3
```

### Responder a una Pregunta Específica

Para responder a una pregunta específica:

```bash
python -m langagent.main --data_dir ./data --chroma_dir ./chroma --local_llm llama3 --question "¿Qué son los alumnos matriculados?"
```

### Iniciar la API

Para iniciar la API FastAPI:

```bash
uvicorn langagent.api.fastapi_app:app --host 0.0.0.0 --port 5001
```

## 🔄 Mecanismo de Reintento y Evaluación

El sistema implementa un sofisticado mecanismo de evaluación y reintento:

1. **Evaluación de Documentos**: Determina si los documentos recuperados son relevantes para la pregunta
2. **Evaluación de Alucinaciones**: Verifica si la respuesta generada contiene información no respaldada por los documentos
3. **Evaluación de Respuesta**: Comprueba si la respuesta aborda adecuadamente la pregunta original
4. **Reintento Adaptativo**: Si alguna evaluación falla, el sistema reintenta con ajustes (hasta 3 veces)
5. **Estrategia de Último Recurso**: En el último intento, utiliza todos los cubos disponibles

## 🧠 Organización del Conocimiento

El sistema organiza los documentos en:

- **Ámbitos**: Categorías amplias de conocimiento (ej. académico, admisión, docencia)
- **Cubos**: Subconjuntos temáticos dentro de cada ámbito

Esta estructura jerárquica permite un enrutamiento más preciso de las preguntas y una recuperación más eficiente de la información relevante.

## 📊 Visualización en Terminal

Todas las visualizaciones han sido adaptadas para entornos de terminal, utilizando formato de texto en lugar de gráficos. El módulo `terminal_visualization.py` proporciona funciones para mostrar:

- Progreso del procesamiento
- Documentos recuperados con puntuaciones de relevancia
- Evaluaciones de calidad de respuesta
- Estadísticas de rendimiento

## 🔒 Seguridad

El sistema implementa autenticación JWT para la API, permitiendo:

- Generación segura de tokens
- Verificación de autenticidad
- Control de acceso a endpoints
- Expiración configurable de tokens


## 📝 Notas Importantes

- El sistema está configurado para trabajar con archivos markdown (.md)
- La base de datos vectorial (Chroma) se guarda en el directorio especificado para su reutilización
- Para un rendimiento óptimo, se recomienda usar GPU para los modelos de embeddings


<div align="center">
  <p>Desarrollado con ❤️ por el equipo de LangAgent</p>
</div>
