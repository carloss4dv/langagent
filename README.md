# SEGEDA: Sistema RAG Adaptativo con LangGraph y Estrategias Mix-of-Granularity

<div align="center">
  <img src="NEAT-AMBIENCE-logo.png" alt="Sistema RAG SEGEDA" width="800"/>
  <br>
  <em>Sistema inteligente de respuesta a preguntas con enrutamiento adaptativo y estrategias avanzadas de granularidad</em>
</div>

## Descripción

RAGDWAREuz es un sistema avanzado de Retrieval-Augmented Generation (RAG) que implementa un agente inteligente utilizando LangGraph, múltiples modelos LLM y bases de datos vectoriales. El sistema organiza la información académica en una estructura jerárquica de "cubos" temáticos dentro de diferentes "ámbitos", incorporando estrategias adaptativas de granularidad Mix-of-Granularity (MoG) para optimizar la recuperación de información según la complejidad de las consultas.

**Financiamiento**: Este TFG se encuadra dentro del proyecto de I+D+i PID2020-113037RB-I00, financiado por MICIU/AEI/10.13039/501100011033 (proyecto NEAT-AMBIENCE) y liderado por la Universidad de Zaragoza.

## Características principales

- **Arquitectura Multi-Agente**: Sistema basado en LangGraph con agente principal y agente de ámbito especializado
- **Estrategias Mix-of-Granularity (MoG)**: Adaptación automática del tamaño de chunks (167-1094 tokens) según complejidad de consultas
- **Enrutamiento Inteligente de Ámbitos**: Identificación automática de ámbitos relevantes (académico, admisión, docencia, I+D+i, etc.)
- **Retrievers Adaptativos**: Múltiples colecciones optimizadas para diferentes granularidades de información
- **Evaluación Granular**: Sistema de evaluación multi-nivel con modelos especializados
- **Generación Contextual**: Enriquecimiento automático de chunks con contexto de documentos fuente
- **Búsqueda Híbrida**: Combinación de búsqueda vectorial y BM25 para máxima precisión
- **Patrón Factory**: Gestión transparente de múltiples tipos de vectorstore (Milvus/Chroma)
- **Document Uploader**: Sistema inteligente de carga incremental con detección de cambios
- **Métricas de Rendimiento**: Recolección detallada de métricas por estrategia y componente
- **Frontend Chainlit**: Interfaz conversacional moderna con soporte para visualizaciones
- **API SQL Integrada**: Capacidad de ejecutar consultas SQL para datos estructurados
- **Sistema de Autenticación**: Tokens JWT para acceso controlado a la API

## Arquitectura del Sistema

<div align="center">
  <img src="Sistema RAGDWAREuz.svg" alt="Arquitectura del Sistema" width="1000"/>
  <br>
  <em>Arquitectura completa del sistema SEGEDA con flujos de trabajo adaptativos</em>
</div>

El sistema implementa una arquitectura multi-agente sofisticada:

### Componentes Principales

1. **Agente Principal (LangChainAgent)**:
   - Orchestador central del flujo de trabajo
   - Gestión de múltiples retrievers adaptativos
   - Coordinación de estrategias Mix-of-Granularity

2. **Agente de Ámbito (AmbitoAgent)**:
   - Identificación automática de ámbitos relevantes
   - Análisis semántico de consultas con LangGraph
   - Generación de preguntas de clarificación cuando es necesario

3. **Workflow LangGraph**:
   - **identify_ambito**: Determina ámbitos y cubos relevantes
   - **retrieve_context**: Recuperación adaptativa de documentos
   - **rewrite_query**: Reformulación inteligente de consultas
   - **grade_relevance**: Evaluación de relevancia de documentos
   - **generate**: Generación RAG/SQL unificada
   - **evaluate_response_granular**: Evaluación multi-dimensional

### Estrategias Mix-of-Granularity (MoG)

- **Fine-grained (167-369 tokens)**: Consultas específicas y técnicas
- **Medium-grained (646 tokens)**: Consultas estándar y comparativas  
- **Coarse-grained (1094 tokens)**: Consultas conceptuales y de síntesis

## Estructura del proyecto

```
langagent/
├── api/                  # API FastAPI para servicios web
│   ├── fastapi_app.py    # Implementación principal de la API REST
│   └── run_api.py        # Script de ejecución del servidor API
├── auth/                 # Sistema de autenticación JWT
│   └── authentication.py # Funciones de autenticación y tokens
├── config/               # Configuración centralizada
│   ├── config.py         # Configuraciones del sistema (LLM, vectorstore, SQL)
│   └── logging_config.py # Sistema de logging centralizado
├── core/                 # Núcleo del sistema
│   ├── lang_chain_agent.py # Agente principal con orchestación LangGraph
│   └── ambito_agent.py    # Agente especializado en identificación de ámbitos
├── evaluation/           # Sistema de evaluación y métricas
│   ├── evaluate.py       # Evaluador con deepeval y métricas personalizadas
│   ├── run_evaluation.py # Scripts de evaluación automatizada
│   └── batch_evaluate.py # Evaluación en lotes para benchmarking
├── frontend/             # Interfaces de usuario
│   ├── chainlit_app.py   # Aplicación Chainlit principal
│   ├── run_chainlit.py   # Launcher de la interfaz conversacional
│   └── chainlit.md       # Configuración y documentación del frontend
├── models/               # Modelos y workflows
│   ├── llm.py           # Configuración de LLMs (Ollama, múltiples modelos)
│   ├── workflow.py      # Implementación del workflow LangGraph principal
│   ├── workflow_utils.py # Utilidades determinísticas para workflows
│   ├── query_analysis.py # Análisis de complejidad de consultas MoG
│   ├── metrics_collector.py # Recolección de métricas por estrategia
│   └── constants.py     # Definición de ámbitos, cubos y keywords
├── prompts/             # Sistema de prompts modularizado
│   ├── __init__.py      # Factory de prompts por modelo
│   ├── llama_prompts.py # Prompts optimizados para LLaMA
│   ├── mistral_prompts.py # Prompts optimizados para Mistral
│   └── qwen_prompts.py  # Prompts optimizados para Qwen
├── tools/               # Herramientas especializadas
│   └── sql_integration.py # Integración con Oracle SQL para datos estructurados
├── utils/               # Utilidades del sistema
│   ├── document_loader.py # Carga de documentos markdown y consultas
│   └── terminal_visualization.py # Visualización en terminal
├── vectorstore/         # Gestión de bases de datos vectoriales
│   ├── base.py          # Interfaz abstracta y patrón Factory
│   ├── milvus.py        # Implementación Milvus con búsqueda híbrida
│   ├── chroma.py        # Implementación Chroma para desarrollo
│   ├── embeddings.py    # Gestión de modelos de embeddings
│   └── document_uploader.py # Sistema inteligente de carga incremental
├── chunk_analisys/      # Análisis de estrategias de chunking
├── diagrams/            # Diagramas PlantUML de arquitectura
├── scripts/             # Scripts de automatización y mantenimiento
└── __main__.py          # Punto de entrada principal del módulo
```

## Stack Tecnológico

### Modelos de Lenguaje
- **Modelo Principal**: Mistral Small 3.1 (24B) - Generación RAG/SQL principal
- **Modelo Secundario**: Qwen 2.5 (1.5B) - Evaluación de relevancia y enrutamiento
- **Modelo Terciario**: LLaMA 3.2 (3B) - Reescritura de consultas y evaluación granular
- **Orquestación**: Ollama para gestión local de modelos

### Embeddings y Vectorstores
- **Embeddings**: HuggingFace `intfloat/multilingual-e5-large-instruct`
- **Vectorstore Principal**: Milvus/Zilliz Cloud con búsqueda híbrida
- **Vectorstore Desarrollo**: ChromaDB para prototipado local
- **Patrón Factory**: `VectorStoreFactory` para abstracción transparente
- **Reranker**: BGE Reranker v2-m3 para compresión contextual

### Framework y Orchestación
- **Workflow**: LangGraph para flujos complejos multi-agente
- **Chains**: LangChain para cadenas RAG/SQL integradas
- **Splitting**: RecursiveCharacterTextSplitter con estrategias adaptativas
- **Búsqueda**: Híbrida (vectorial + BM25) con `WeightedRanker`

### Interfaces y APIs
- **Frontend Principal**: Chainlit para interfaz conversacional
- **API**: FastAPI con documentación automática (OpenAPI/Swagger)
- **Base de Datos**: Oracle con SQLAlchemy para consultas estructuradas
- **Autenticación**: JWT con AuthLib

### Desarrollo y Evaluación
- **Evaluación**: DeepEval con métricas customizadas
- **Logging**: Sistema centralizado con ColorLog
- **Métricas**: Recolección detallada por estrategia y componente
- **Testing**: Evaluación batch con casos predefinidos

## Requisitos del Sistema

### Dependencias Principales

```bash
# Framework principal
langchain
langchain-core
langchain-community
langgraph
langchain-text-splitters

# Modelos y LLMs
ollama
langchain-ollama  
langchain-huggingface
sentence-transformers

# Vectorstores
langchain-milvus
pymilvus
chromadb
langchain-chroma

# Frontend y API
chainlit
fastapi
uvicorn
pydantic

# Base de datos y herramientas
cx-Oracle
sqlalchemy
pandas
tqdm

# Evaluación
deepeval
```

### Requisitos de Hardware
- **RAM**: Mínimo 16GB (recomendado 32GB para modelos grandes)
- **GPU**: CUDA compatible para embeddings (opcional, funciona en CPU)
- **Almacenamiento**: 50GB para modelos locales
- **Procesador**: Multi-core recomendado para paralelización

## Instalación y Configuración

### 1. Configuración del Entorno

```bash
# Clonar el repositorio
git clone https://github.com/carloss4dv/langagent.git
cd langagent

# Crear entorno virtual
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración de Ollama

```bash
# Instalar Ollama (https://ollama.ai)
# Descargar modelos necesarios
ollama pull mistral-small-3.1:24b
ollama pull qwen2.5:1.5b  
ollama pull llama3.2:3b
```

### 3. Configuración de Variables de Entorno

Crear archivo `.env` en el directorio raíz:

```bash
# Configuración Milvus/Zilliz Cloud (opcional)
ZILLIZ_CLOUD_URI=https://your-cluster.gcp-us-west1.vectordb.zilliz.cloud
ZILLIZ_CLOUD_TOKEN=your_token_here
ZILLIZ_CLOUD_SECURE=True

# Configuración Oracle (opcional)
ORACLE_URI=oracle+cx_oracle://user:pass@host:port/?service_name=XEPDB1
```

## Uso del Sistema

### 1. Interfaz Conversacional (Chainlit)

La interfaz principal es Chainlit, que proporciona una experiencia conversacional moderna:

```bash
# Iniciar la aplicación Chainlit
python frontend/run_chainlit.py
```

La interfaz estará disponible en `http://localhost:8000` con características:
- Chat conversacional en tiempo real
- Visualización de métricas y contexto
- Soporte para tablas y gráficos
- Modo consulta para búsquedas guardadas
- Indicadores de progreso y estado

### 2. Línea de Comandos

Ejecución directa del agente:

```bash
# Ejecutar con configuración básica
python -m langagent run --question "¿Cuántos estudiantes se matricularon el año pasado?"

# Configuración avanzada
python -m langagent run \
  --data_dir ./data \
  --vectorstore_dir ./vectorstores \
  --vector_db_type milvus \
  --local_llm mistral-small-3.1:24b \
  --question "Analiza el rendimiento académico por ámbito"
```

### 3. API REST

Servidor API para integración con otros sistemas:

```bash
# Iniciar servidor API
python api/run_api.py

# La API estará disponible en http://localhost:5001
# Documentación interactiva: http://localhost:5001/docs
```

### 4. Evaluación y Benchmarking

```bash
# Evaluación completa con métricas
python -m langagent evaluate \
  --modelo mistral-small-3.1:24b \
  --modelo2 qwen2.5:1.5b \
  --modelo3 llama3.2:3b \
  --vector_db_type milvus

# Evaluación en batch para benchmarking
python -m langagent evaluate --batch \
  --casos preguntas_eval.json \
  --output_dir batch_results
```

## Sistema de Evaluación y Métricas

### Evaluación Multi-Dimensional

El sistema incorpora un evaluador granular con múltiples dimensiones:

```python
# Métricas implementadas
- Relevancia de respuesta (AnswerRelevancy)
- Fidelidad a fuentes (Faithfulness) 
- Relevancia contextual (ContextualRelevancy)
- Precisión contextual (ContextualPrecision)
- Recall contextual (ContextualRecall)
```

### Estrategias Mix-of-Granularity (MoG)

El sistema adapta automáticamente la granularidad según la complejidad:

1. **Análisis de Consulta**: Detección de indicadores semánticos
2. **Selección de Estrategia**: Asignación automática de granularidad
3. **Evaluación Adaptativa**: Cambio dinámico si la respuesta es insuficiente
4. **Histórico de Granularidad**: Prevención de bucles infinitos

### Métricas de Rendimiento

```python
# Métricas recolectadas por componente
- Tiempo de ejecución por nodo LangGraph
- Llamadas a LLM con tiempo y modelo utilizado
- Uso de memoria durante el procesamiento
- Estrategias de chunking utilizadas
- Éxito/fallo por tipo de consulta
```

## Arquitectura de Bases de Datos Vectoriales

### Patrón Factory

El sistema utiliza el patrón Factory para gestión transparente de vectorstores:

```python
# VectorStoreFactory permite cambio transparente
vectorstore = VectorStoreFactory.get_vectorstore_instance("milvus")
# o
vectorstore = VectorStoreFactory.get_vectorstore_instance("chroma")
```

### Document Uploader Inteligente

Sistema avanzado de carga de documentos:

- **Detección de Cambios**: Verificación de versiones por MD5
- **Carga Incremental**: Solo actualiza documentos modificados
- **Gestión de Metadatos**: Enriquecimiento automático con ámbito/cubo
- **Generación de Contexto**: Añade contexto de documento fuente a chunks
- **Filtrado Inteligente**: Eliminación de documentos obsoletos

### Configuraciones de Vectorstore

```python
# Milvus (Producción)
- Búsqueda híbrida (vectorial + BM25)
- Filtrado por metadatos avanzado
- Soporte para Zilliz Cloud
- Colecciones adaptativas por granularidad
- Compresión contextual con reranker

# Chroma (Desarrollo)
- Almacenamiento local simple
- Filtrado básico por metadatos
- Ideal para prototipado
```

## Organización del Conocimiento Académico

### Estructura Jerárquica: Ámbitos y Cubos

El sistema organiza la información académica en una estructura de dos niveles:

```python
ÁMBITOS_ACADÉMICOS = {
    "admision": {
        "cubos": ["admision", "ofertaplazas"],
        "descripcion": "Procesos de admisión y oferta de plazas"
    },
    "academico": {
        "cubos": ["cohorte", "egresados", "matricula", "rendimiento"],
        "descripcion": "Información académica general y rendimiento"
    },
    "docencia": {
        "cubos": ["docenciaAsignatura", "docenciaPDI"],
        "descripcion": "Docencia, asignaturas y personal docente"
    },
    "idi": {
        "cubos": ["grupos", "produccionCientifica", "proyectos", "movilidad_idi"],
        "descripcion": "Investigación, desarrollo e innovación"
    },
    "movilidad": {
        "cubos": ["estudiantesIN", "estudiantesOUT", "acuerdos_bilaterales"],
        "descripcion": "Movilidad internacional y programas de intercambio"
    },
    "rrhh": {
        "cubos": ["PDI", "PTGAS", "cargo", "puesto"],
        "descripcion": "Gestión de recursos humanos y personal"
    }
}
```

### Enrutamiento Inteligente

- **Análisis Semántico**: Identificación automática de keywords por ámbito
- **Agente Especializado**: `AmbitoAgent` con LangGraph para decisiones complejas
- **Clarificación Automática**: Generación de preguntas cuando el ámbito es ambiguo
- **Fallback Inteligente**: Búsqueda en múltiples ámbitos si es necesario

## Integración SQL y Datos Estructurados

### Capacidades SQL Avanzadas

```python
# Generación automática de consultas SQL
- Interpretación de lenguaje natural a SQL
- Ejecución segura con Oracle Database
- Integración en workflow RAG principal
- Formato de resultados para presentación
```

### Flujo RAG-SQL Híbrido

1. **Detección de Consulta**: Identificación automática de necesidad SQL
2. **Generación SQL**: LLM especializado genera consulta estructurada
3. **Ejecución Segura**: Validación y ejecución controlada
4. **Interpretación**: Análisis de resultados en lenguaje natural
5. **Presentación**: Formato tabular y visualización

## Características Avanzadas

### Sistema de Prompts Modularizado

```python
# Prompts especializados por modelo LLM
prompts/
├── llama_prompts.py      # Optimizados para LLaMA 3.2
├── mistral_prompts.py    # Optimizados para Mistral Small
└── qwen_prompts.py       # Optimizados para Qwen 2.5
```

### Análisis de Chunks Adaptativos

- **Análisis Estadístico**: Distribución de longitudes y características
- **Configuraciones Óptimas**: Determinación automática de parámetros
- **Visualizaciones**: Gráficos de rendimiento por estrategia
- **Métricas de Calidad**: Evaluación de coherencia semántica

### Workflow Adaptativo

```python
# Nodos especializados del workflow LangGraph
- identify_ambito: Identificación inteligente de ámbito
- retrieve_context: Recuperación adaptativa multi-estrategia  
- rewrite_query: Reformulación automática de consultas
- grade_relevance: Evaluación de calidad de documentos
- generate: Generación RAG/SQL unificada
- evaluate_response_granular: Evaluación multi-dimensional
```

### Logging y Observabilidad

- **Logging Centralizado**: Sistema unificado con niveles configurables
- **Métricas en Tiempo Real**: Recolección durante ejecución
- **Trazabilidad**: Seguimiento completo de decisiones del workflow
- **Análisis de Rendimiento**: Identificación de cuellos de botella

## Casos de Uso Típicos

### 1. Consultas Académicas Específicas
```
"¿Cuántos estudiantes de Ingeniería Informática se graduaron en 2023?"
→ Estrategia: Fine-grained + SQL
→ Ámbito: académico (egresados)
```

### 2. Análisis Comparativos
```
"Compara el rendimiento académico entre diferentes titulaciones"
→ Estrategia: Medium-grained + Multi-ámbito
→ Ámbitos: académico + docencia
```

### 3. Consultas Conceptuales
```
"Explica el proceso completo de admisión universitaria"
→ Estrategia: Coarse-grained + Síntesis
→ Ámbito: admision (proceso completo)
```

### 4. Investigación y Proyectos
```
"¿Qué grupos de investigación trabajaron en IA en los últimos 3 años?"
→ Estrategia: Híbrida RAG+SQL
→ Ámbito: idi (grupos + proyectos)
```

## Seguridad y Autenticación

### Sistema JWT
- **Tokens Seguros**: Generación y verificación con AuthLib
- **Expiración Configurable**: Control temporal de acceso
- **Middleware FastAPI**: Protección automática de endpoints
- **Gestión de Sesiones**: Control de acceso por usuario

### Validación de Entrada
- **Sanitización SQL**: Prevención de inyección SQL
- **Validación de Prompts**: Control de contenido malicioso
- **Límites de Rate**: Protección contra abuso de API
- **Logging de Seguridad**: Registro de intentos de acceso

## Configuración Avanzada

### Variables de Entorno Principales

```bash
# Modelos LLM
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=mistral-small-3.1:24b
MODEL_TEMPERATURE=0.15

# Vectorstore
VECTOR_DB_TYPE=milvus
CHUNK_SIZE=646
CHUNK_OVERLAP=50
K_RETRIEVAL=12

# API y Seguridad
API_PORT=5001
JWT_SECRET_KEY=your_secret_key
TOKEN_EXPIRATION_MINUTES=60

# Base de Datos
ORACLE_URI=oracle+cx_oracle://user:pass@host:port/?service_name=XEPDB1
```

### Optimización de Rendimiento

```python
# Configuraciones recomendadas por entorno

# Desarrollo Local
VECTOR_DB_TYPE=chroma
CHUNK_SIZE=512
USE_GPU=false

# Producción
VECTOR_DB_TYPE=milvus
USE_HYBRID_SEARCH=true
USE_CONTEXT_GENERATION=true
BGE_DEVICE=cuda
CONTEXT_BATCH_SIZE=10
```

## Contribución y Desarrollo

### Estructura de Desarrollo
- **Patrón Factory**: Fácil extensión de nuevos vectorstores
- **Interfaces Abstractas**: Componentes intercambiables
- **Sistema de Plugins**: Extensión modular de funcionalidades
- **Testing Automatizado**: Suite de pruebas con casos reales

### Roadmap Futuro
- [ ] Soporte para modelos de embeddings adicionales
- [ ] Integración con más bases de datos vectoriales
- [ ] Sistema de caché inteligente
- [ ] Análisis de sentimientos en consultas
- [ ] Soporte multiidioma mejorado
- [ ] Integración con sistemas LMS

<div align="center">
  <div style="display: flex; justify-content: center; align-items: center; gap: 30px;">
    <img src="logos/cosmos-logo.png" alt="Cosmos Logo" width="300"/>
    <img src="logos/NEAT-AMBIENCE-logoAcks.jpg" alt="NEAT-AMBIENCE ACKS Logo" width="300"/>
  </div>
  <p>Desarrollado por Carlos de Vera Sanz</p>
  <p>Universidad de Zaragoza - COSMOS</p>
</div>
