# LangAgent: Agente con LangGraph, LLaMA3 y bases de datos vectoriales

<div align="center">
  <img src="logos/NEAT-AMBIENCE-logo.png" alt="NEAT-AMBIENCE Logo" width="400"/>
  <br>
  <em>Sistema de respuesta a preguntas con enrutamiento inteligente y mecanismos de reintento</em>
</div>

## Descripción

LangAgent es un sistema de respuesta a preguntas que implementa un agente utilizando LangGraph, LLaMA3 y bases de datos vectoriales. El sistema organiza la información en "cubos" temáticos dentro de diferentes "ámbitos", permitiendo dirigir las preguntas de manera adecuada y reintentar cuando las respuestas no son satisfactorias.

## Características principales

- **Organización jerárquica del conocimiento**: Estructura de "cubos" y "ámbitos" para organizar documentos
- **Enrutamiento adaptativo**: Selección inteligente de la base de conocimiento según el contenido de la pregunta
- **Mecanismo de reintento**: Hasta 3 intentos cuando las respuestas no son satisfactorias
- **Evaluación de calidad**: Verifica la relevancia de los documentos y la calidad de las respuestas
- **Autenticación**: Sistema basado en tokens JWT para la API
- **Múltiples interfaces**: API REST, terminal y frontend Streamlit
- **Soporte para distintas bases de datos vectoriales**: Compatible con Chroma DB y Milvus

## Workflow del sistema

El sistema implementa un flujo de trabajo basado en LangGraph con tres nodos principales:
1. **Route Question**: Determina qué cubos son relevantes para la pregunta
2. **Retrieve**: Recupera documentos relevantes de los cubos seleccionados
3. **Generate**: Genera una respuesta basada en los documentos recuperados

## Estructura del proyecto

```
langagent/
├── api/                  # Módulos para la API FastAPI
│   ├── __init__.py
│   ├── fastapi_app.py    # Implementación de la API
│   └── run_api.py        # Script para ejecutar la API
├── auth/                 # Módulos para autenticación
│   ├── __init__.py
│   └── authentication.py # Funciones de autenticación JWT
├── config/               # Configuraciones
│   ├── __init__.py
│   └── config.py         # Configuraciones del sistema
├── core/                 # Núcleo del sistema
│   ├── __init__.py
│   └── lang_chain_agent.py # Clase principal del agente
├── data/                 # Directorio para datos
│   └── __init__.py
├── frontend/             # Interfaces de usuario
│   ├── __init__.py
│   └── streamlit/        # Frontend con Streamlit
│       ├── app.py        # Aplicación Streamlit
│       ├── run_streamlit.py # Script para ejecutar Streamlit
│       └── README.md     # Documentación del frontend
├── logos/                # Logos e imágenes del proyecto
├── models/               # Modelos y flujo de trabajo
│   ├── __init__.py
│   ├── constants.py      # Constantes del sistema
│   ├── llm.py            # Configuración de modelos de lenguaje
│   └── workflow.py       # Implementación del flujo con LangGraph
├── utils/                # Utilidades
│   ├── __init__.py
│   ├── document_loader.py       # Carga de documentos markdown
│   ├── terminal_visualization.py # Visualización en terminal
│   └── llamaindex_integration.py # Integración con llama-index
├── vectorstore/          # Gestión de bases de datos vectoriales
│   ├── __init__.py
│   ├── base.py           # Interfaz base para vectorstores
│   ├── chroma.py         # Implementación para Chroma DB
│   ├── milvus.py         # Implementación para Milvus
│   └── embeddings.py     # Gestión de embeddings
├── __init__.py
├── main.py               # Script principal
├── main_llamaindex.py    # Script principal con integración llama-index
└── requirements.txt      # Dependencias del proyecto
```

## Componentes técnicos

- **Modelos LLM**: Modelos de Ollama (LLaMA3) para diferentes tareas
- **Embeddings**: HuggingFace Embeddings (multilingual-e5-large-instruct)
- **Bases de datos vectoriales**: 
  - **Chroma DB**: Para desarrollo local y conjuntos de datos pequeños-medianos
  - **Milvus**: Para producción, con soporte para búsquedas vectoriales avanzadas
- **Framework de flujo**: LangGraph para orquestar el flujo de trabajo
- **API**: FastAPI para exponer la funcionalidad como servicio web
- **Frontend**: Streamlit para interfaz gráfica de usuario

## Requisitos

Las principales dependencias son:

- Python 3.10+
- langchain y langgraph
- chromadb y pymilvus
- huggingface_hub
- unstructured[md]
- fastapi y uvicorn
- streamlit
- authlib
- ollama (instalado localmente)

Ver el archivo `requirements.txt` para la lista completa de dependencias.

## Instalación

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

## Uso

### Modo interactivo con terminal

Para iniciar el agente en modo interactivo:

```bash
python -m langagent.main --data_dir ./data --vectorstore_dir ./vectorstores --local_llm llama3
```

### API REST con FastAPI

Para iniciar la API REST:

```bash
python api/run_api.py
```

La API estará disponible en http://localhost:8000 con documentación interactiva en http://localhost:8000/docs

### Interfaz gráfica con Streamlit

Para iniciar el frontend Streamlit (asegúrate de que la API esté en ejecución):

```bash
python frontend/streamlit/run_streamlit.py
```

La interfaz estará disponible en http://localhost:8501

### Técnicas avanzadas de RAG

Puedes especificar qué técnicas avanzadas de RAG utilizar:

```bash
python -m langagent.main_llamaindex --data_dir ./data --vectorstore_dir ./vectorstores --local_llm llama3 --use_advanced_rag --advanced_techniques dual_chunks document_summary
```

Las técnicas disponibles son:
- `dual_chunks`: Para recuperación precisa y síntesis contextual
- `document_summary`: Para preguntas que requieren resúmenes
- `router`: Para selección dinámica de estrategias de recuperación
- `optimize_embeddings`: Para optimización de embeddings

## Mecanismo de reintento y evaluación

El sistema implementa un mecanismo de evaluación y reintento:

1. **Evaluación de documentos**: Verifica si los documentos recuperados son relevantes para la pregunta
2. **Evaluación de alucinaciones**: Comprueba si la respuesta contiene información no respaldada por los documentos
3. **Evaluación de respuesta**: Verifica si la respuesta aborda adecuadamente la pregunta original
4. **Reintento adaptativo**: Si alguna evaluación falla, el sistema reintenta con ajustes (hasta 3 veces)
5. **Estrategia de último recurso**: En el último intento, utiliza todos los cubos disponibles

## Organización del conocimiento

El sistema organiza los documentos en:

- **Ámbitos**: Categorías amplias de conocimiento (ej. académico, admisión, docencia)
- **Cubos**: Subconjuntos temáticos dentro de cada ámbito

Esta estructura permite una recuperación más precisa de la información relevante.

## Bases de datos vectoriales

El sistema soporta dos tipos de bases de datos vectoriales:

### Chroma DB
- **Entorno**: Desarrollo local y pruebas
- **Almacenamiento**: Local en sistema de archivos
- **Ventajas**: 
  - Configuración sencilla
  - Sin dependencias externas
  - Adecuado para prototipado

### Milvus
- **Entorno**: Producción y escalabilidad
- **Principal diferencia**: Soporte para búsquedas vectoriales avanzadas
- **Otras ventajas**:
  - Mejor rendimiento con grandes volúmenes de datos
  - Escalabilidad horizontal
  - Búsquedas por similitud más sofisticadas
  - Soporte para colecciones unificadas

El sistema usa una interfaz común para ambas bases de datos, lo que permite cambiar entre ellas según las necesidades.

## Visualización

El sistema ofrece varias formas de visualización:

- **Terminal**: Visualización en texto para entornos sin interfaz gráfica
- **API REST**: Respuestas JSON para integración con otros sistemas
- **Streamlit**: Interfaz gráfica para usuarios finales

## Seguridad

El sistema implementa autenticación JWT para la API con:

- Generación de tokens
- Verificación de autenticidad
- Control de acceso a endpoints
- Expiración configurable de tokens

## Notas importantes

- El sistema trabaja con archivos markdown (.md)
- La base de datos vectorial se guarda en el directorio especificado
- Para un mejor rendimiento, se recomienda usar GPU para los modelos de embeddings
- El cambio entre Chroma y Milvus se configura en config.py

<div align="center">
  <img src="logos/cosmos-logo.png" alt="Cosmos Logo" width="100"/>
  <p>Desarrollado por Carlos de Vera Sanz</p>
  <p>Universidad de Zaragoza - COSMOS</p>
</div>
