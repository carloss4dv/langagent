# Migración de Chroma a Milvus en LangAgent

## Introducción

Este documento describe el proceso para migrar de ChromaDB a Milvus como base de datos vectorial en el proyecto LangAgent. Milvus es una base de datos vectorial de código abierto diseñada específicamente para aplicaciones de IA que requieren almacenamiento, indexación y consulta eficiente de vectores de embeddings.

## Ventajas de Milvus frente a Chroma

### Escalabilidad
- **Arquitectura distribuida**: Milvus ofrece una arquitectura con separación de componentes de cómputo y almacenamiento, permitiendo escalabilidad horizontal hasta miles de millones de vectores.
- **Asignación dinámica de nodos**: Milvus puede asignar nodos dinámicamente a grupos de acciones, lo que mejora la velocidad y la gestión de recursos.
- **Sin límites prácticos**: A diferencia de Chroma que tiene un límite práctico de aproximadamente un millón de vectores, Milvus puede escalar hasta billones de vectores.

### Funcionalidad
- **Control de acceso basado en roles (RBAC)**: Milvus ofrece sólido soporte para RBAC, ideal para aplicaciones empresariales.
- **Múltiples tipos de índices**: Soporta 14 tipos de índices diferentes, incluyendo FLAT, IVF_FLAT, HNSW, entre otros.
- **Particionamiento a nivel de tabla**: Mejora el rendimiento en consultas en tiempo real.
- **Índices en disco**: Proporciona flexibilidad para aplicaciones con limitaciones de costos.
- **Búsqueda híbrida**: Permite realizar búsquedas vectoriales con filtrado de metadatos antes y después de la operación.

### Rendimiento
- **Optimizado para alto rendimiento**: Arquitectura diseñada para aplicaciones que requieren baja latencia y alto rendimiento.
- **Consultas de alta velocidad**: Ideal para entornos de producción con grandes volúmenes de datos y necesidades de búsqueda en tiempo real.

## Requisitos previos

- Docker (para ejecutar Milvus localmente o en entorno de desarrollo)
- Python 3.8+
- Tarjeta gráfica NVIDIA con CUDA (opcional, para mejor rendimiento)

## Instalación de Milvus

### Opción 1: Usando Docker Compose (recomendado para desarrollo)

1. Crea un archivo `docker-compose.yml` con la siguiente configuración:

```yaml
version: '3.5'

services:
  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/etcd:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/minio:/minio_data
    command: minio server /minio_data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.3.5
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/milvus:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - "etcd"
      - "minio"

networks:
  default:
    name: milvus
```

2. Inicia los servicios:

```bash
docker-compose up -d
```

### Opción 2: Usando Milvus Cloud (recomendado para producción)

Para entornos de producción, considera utilizar [Zilliz Cloud](https://zilliz.com/cloud), que es el servicio gestionado oficial de Milvus.

## Instalación de dependencias en Python

Instala las bibliotecas necesarias:

```bash
pip install pymilvus langchain-milvus
```

## Modificaciones al código

### 1. Actualización del archivo de configuración

Modifica el archivo `config/config.py` para añadir la configuración de Milvus:

```python
# Configuración de Vector Store
VECTORSTORE_CONFIG = {
    "chunk_size": 256,         # Tamaño de los fragmentos de texto para indexación
    "chunk_overlap": 50,       # Superposición entre fragmentos
    "k_retrieval": 6,          # Número de documentos a recuperar
    "similarity_threshold": 0.7,  # Umbral mínimo de similitud para considerar un documento relevante
    "max_docs_total": 15,      # Aumentar el límite total de documentos
    "vector_db_type": "milvus", # Tipo de base de datos vectorial (chroma o milvus)
    "milvus_uri": "http://localhost:19530", # URI de Milvus (local o en la nube)
    "milvus_username": "",     # Usuario para Milvus Cloud (déjalo vacío para la versión local)
    "milvus_password": ""      # Contraseña para Milvus Cloud (déjalo vacío para la versión local)
}
```

### 2. Creación del módulo para Milvus

Crea un nuevo archivo `utils/milvus_vectorstore.py`:

```python
"""
Módulo para la configuración de embeddings y vectorstore utilizando Milvus.

Este módulo proporciona funciones para configurar embeddings y crear/cargar
una base de datos vectorial Milvus para la recuperación de información.
"""

from langchain_milvus import Milvus
from langchain_core.documents import Document
from typing import List, Optional, Dict, Any
from langagent.config.config import VECTORSTORE_CONFIG
from langchain_core.embeddings import Embeddings
import logging
import time
import os

logger = logging.getLogger(__name__)

def create_vectorstore(documents: List[Document], embeddings: Embeddings, collection_name: str) -> Milvus:
    """
    Crea una base de datos vectorial Milvus a partir de documentos.
    
    Args:
        documents (List[Document]): Lista de documentos a indexar.
        embeddings: Modelo de embeddings a utilizar.
        collection_name (str): Nombre de la colección en Milvus.
        
    Returns:
        Milvus: Base de datos vectorial creada.
    """
    connection_args = {
        "uri": VECTORSTORE_CONFIG.get("milvus_uri", "http://localhost:19530"),
    }
    
    # Agregar credenciales si se proporcionan (para Milvus Cloud)
    if VECTORSTORE_CONFIG.get("milvus_username") and VECTORSTORE_CONFIG.get("milvus_password"):
        connection_args["username"] = VECTORSTORE_CONFIG.get("milvus_username")
        connection_args["password"] = VECTORSTORE_CONFIG.get("milvus_password")
    
    return Milvus.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        connection_args=connection_args,
        drop_old=True  # Establece en False para no eliminar la colección existente
    )

def load_vectorstore(embeddings: Embeddings, collection_name: str) -> Milvus:
    """
    Carga una base de datos vectorial Milvus existente.
    
    Args:
        embeddings: Modelo de embeddings a utilizar.
        collection_name (str): Nombre de la colección en Milvus.
        
    Returns:
        Milvus: Base de datos vectorial cargada.
    """
    connection_args = {
        "uri": VECTORSTORE_CONFIG.get("milvus_uri", "http://localhost:19530"),
    }
    
    # Agregar credenciales si se proporcionan (para Milvus Cloud)
    if VECTORSTORE_CONFIG.get("milvus_username") and VECTORSTORE_CONFIG.get("milvus_password"):
        connection_args["username"] = VECTORSTORE_CONFIG.get("milvus_username")
        connection_args["password"] = VECTORSTORE_CONFIG.get("milvus_password")
    
    return Milvus.from_existing_collection(
        embedding=embeddings,
        collection_name=collection_name,
        connection_args=connection_args,
    )

def create_retriever(vectorstore, k=None, similarity_threshold=0.7):
    """
    Crea un retriever a partir de un vectorstore Milvus.
    
    Args:
        vectorstore: Vector store Milvus.
        k (int, optional): Número de documentos a recuperar. Si es None, se usa el valor de configuración.
        similarity_threshold (float): Umbral mínimo de similitud.
        
    Returns:
        Retriever: Retriever configurado.
    """
    if k is None:
        k = VECTORSTORE_CONFIG["k_retrieval"]
    
    # Configurar el retriever de Milvus
    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": k,
            "score_threshold": similarity_threshold
        }
    )
    
    logger.info(f"Retriever Milvus creado con k={k} y umbral de similitud={similarity_threshold}")
    
    return retriever

def retrieve_documents(retriever, query, max_retries=3):
    """
    Recupera documentos con manejo de errores y reintentos.
    
    Args:
        retriever: Retriever configurado.
        query (str): Consulta para la búsqueda.
        max_retries (int): Número máximo de reintentos en caso de error.
        
    Returns:
        List[Document]: Lista de documentos recuperados.
    """
    for attempt in range(max_retries):
        try:
            docs = retriever.get_relevant_documents(query)
            if not docs:
                logger.warning(f"No se encontraron documentos relevantes para la consulta: {query}")
                return []
            
            # Logging detallado de los documentos recuperados
            for i, doc in enumerate(docs):
                logger.debug(f"Documento {i+1}: Score={doc.metadata.get('score', 'N/A')}, "
                           f"Fuente={doc.metadata.get('source', 'N/A')}")
            
            return docs
            
        except Exception as e:
            logger.error(f"Error en intento {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error("Se agotaron los reintentos")
                return []
            time.sleep(1)  # Esperar antes de reintentar
```

### 3. Modificar el archivo principal de LangChainAgent

Actualiza el archivo `core/lang_chain_agent.py` para soportar ambas opciones de vectorstore (Chroma y Milvus):

```python
# ... código existente ...
from langagent.utils.vectorstore import (
    create_embeddings, 
    create_vectorstore as create_chroma_vectorstore, 
    load_vectorstore as load_chroma_vectorstore, 
    create_retriever
)
from langagent.utils.milvus_vectorstore import (
    create_vectorstore as create_milvus_vectorstore,
    load_vectorstore as load_milvus_vectorstore
)
from langagent.config.config import (
    LLM_CONFIG,
    VECTORSTORE_CONFIG,
    PATHS_CONFIG
)

# ... más código existente ...

class LangChainAgent:
    def __init__(self, data_dir=None, vectorstore_base_dir=None, local_llm=None, local_llm2=None, local_llm3=None, consultas_dir=None):
        """
        Inicializa el agente con todos sus componentes, creando una vectorstore separada
        para cada cubo identificado en los documentos.
        
        Args:
            data_dir (str, optional): Directorio con los documentos markdown.
            vectorstore_base_dir (str, optional): Directorio base para las bases de datos vectoriales.
            local_llm (str, optional): Nombre del modelo LLM principal.
            local_llm2 (str, optional): Nombre del segundo modelo LLM.
            local_llm3 (str, optional): Nombre del tercer modelo LLM.
            consultas_dir (str, optional): Directorio con las consultas guardadas.
        """
        self.data_dir = data_dir or PATHS_CONFIG["default_data_dir"]
        self.vectorstore_base_dir = vectorstore_base_dir or PATHS_CONFIG["default_chroma_dir"]
        self.local_llm = local_llm or LLM_CONFIG["default_model"]
        self.local_llm2 = local_llm2 or LLM_CONFIG["default_model2"]
        self.local_llm3 = local_llm3 or LLM_CONFIG["default_model3"]
        self.consultas_dir = consultas_dir or os.path.join(os.path.dirname(self.data_dir), "consultas_guardadas")
        
        self.embeddings = None
        self.retrievers = {}
        self.vectorstores = {}
        self.consultas_vectorstores = {}
        self.llm = None
        self.llm2 = None
        self.rag_chain = None
        self.retrieval_grader = None
        self.hallucination_grader = None
        self.answer_grader = None
        self.question_router = None
        self.workflow = None
        self.app = None
        
        # Determinar el tipo de vectorstore a utilizar
        self.vector_db_type = VECTORSTORE_CONFIG.get("vector_db_type", "chroma")
        
        self.setup_agent()

    def setup_agent(self):
        """
        Configura el agente con todos sus componentes.
        """
        print_title("Configurando el agente")
        
        # Crear embeddings (compartidos por todas las vectorstores)
        print("Creando embeddings...")
        self.embeddings = create_embeddings()
        
        # Cargar documentos y agruparlos por cubo
        print("Cargando documentos y agrupándolos por cubo...")
        all_documents = load_documents_from_directory(self.data_dir)
        
        # Cargar consultas guardadas
        print("Cargando consultas guardadas...")
        consultas_por_ambito = load_consultas_guardadas(self.consultas_dir)
        
        # Dividir documentos en chunks más pequeños
        print("Dividiendo documentos...")
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=VECTORSTORE_CONFIG["chunk_size"], 
            chunk_overlap=VECTORSTORE_CONFIG["chunk_overlap"]
        )
        
        # Diccionario para agrupar los documentos por cubo
        cubo_documents = {}
        
        # Extraer y agrupar por nombre de cubo
        for doc in all_documents:
            # ... código existente para agrupar por cubo ...
        
        # Procesar cada cubo y crear su vectorstore
        for cubo_name, docs in cubo_documents.items():
            print(f"Procesando documentos para el cubo: {cubo_name}")
            
            # Dividir documentos en chunks
            doc_splits = text_splitter.split_documents(docs)
            
            if self.vector_db_type == "chroma":
                # Usar Chroma como vectorstore
                cubo_chroma_dir = os.path.join(self.vectorstore_base_dir, f"Cubo{cubo_name}")
                
                # Crear o cargar vectorstore para este cubo
                if not os.path.exists(cubo_chroma_dir):
                    print(f"Creando nueva base de datos vectorial Chroma para {cubo_name}...")
                    db = create_chroma_vectorstore(doc_splits, self.embeddings, cubo_chroma_dir)
                else:
                    print(f"Cargando base de datos vectorial Chroma existente para {cubo_name}...")
                    db = load_chroma_vectorstore(cubo_chroma_dir, self.embeddings)
            else:
                # Usar Milvus como vectorstore
                collection_name = f"Cubo{cubo_name}"
                
                try:
                    # Intentar cargar una colección existente
                    print(f"Intentando cargar colección Milvus existente para {cubo_name}...")
                    db = load_milvus_vectorstore(self.embeddings, collection_name)
                    print(f"Colección Milvus existente cargada para {cubo_name}")
                except Exception as e:
                    # Si no existe, crear una nueva
                    print(f"Creando nueva colección Milvus para {cubo_name}...")
                    db = create_milvus_vectorstore(doc_splits, self.embeddings, collection_name)
                    print(f"Nueva colección Milvus creada para {cubo_name}")
            
            # Guardar la vectorstore
            self.vectorstores[cubo_name] = db
            
            # Crear retriever para este cubo
            self.retrievers[cubo_name] = create_retriever(db, k=VECTORSTORE_CONFIG["k_retrieval"])
        
        # Procesar consultas guardadas por ámbito
        for ambito, consultas in consultas_por_ambito.items():
            print(f"Procesando consultas guardadas para el ámbito: {ambito}")
            
            # Dividir consultas en chunks
            consulta_splits = text_splitter.split_documents(consultas)
            
            if self.vector_db_type == "chroma":
                # Usar Chroma para consultas
                consultas_chroma_dir = os.path.join(self.vectorstore_base_dir, f"Consultas_{ambito}")
                
                # Crear o cargar vectorstore para las consultas de este ámbito
                if not os.path.exists(consultas_chroma_dir):
                    print(f"Creando nueva base de datos vectorial Chroma para consultas de {ambito}...")
                    db = create_chroma_vectorstore(consulta_splits, self.embeddings, consultas_chroma_dir)
                else:
                    print(f"Cargando base de datos vectorial Chroma existente para consultas de {ambito}...")
                    db = load_chroma_vectorstore(consultas_chroma_dir, self.embeddings)
            else:
                # Usar Milvus para consultas
                collection_name = f"Consultas_{ambito}"
                
                try:
                    # Intentar cargar una colección existente
                    print(f"Intentando cargar colección Milvus existente para consultas de {ambito}...")
                    db = load_milvus_vectorstore(self.embeddings, collection_name)
                    print(f"Colección Milvus existente cargada para consultas de {ambito}")
                except Exception as e:
                    # Si no existe, crear una nueva
                    print(f"Creando nueva colección Milvus para consultas de {ambito}...")
                    db = create_milvus_vectorstore(consulta_splits, self.embeddings, collection_name)
                    print(f"Nueva colección Milvus creada para consultas de {ambito}")
            
            # Guardar la vectorstore de consultas
            self.consultas_vectorstores[ambito] = db
            
            # Crear retriever para las consultas de este ámbito y agregarlo a los retrievers
            retriever_key = f"consultas_{ambito}"
            self.retrievers[retriever_key] = create_retriever(db, k=VECTORSTORE_CONFIG["k_retrieval"])
        
        # ... resto del código para configurar LLMs, cadenas, etc. ...
```

## Técnicas avanzadas de recuperación con Milvus

### 1. Búsqueda híbrida (vectorial y filtrado por metadatos)

Milvus permite realizar búsquedas híbridas, combinando la búsqueda por similitud vectorial con filtrado por atributos de metadatos:

```python
# Ejemplo de búsqueda con filtrado
query = "¿Cuáles son los efectos secundarios de este medicamento?"
expr = "category == 'medicamento' && year >= 2020"

results = vectorstore.similarity_search(
    query, 
    k=5,
    expr=expr  # Expresión de filtrado
)
```

### 2. Búsqueda por particiones

Milvus permite crear particiones para mejorar el rendimiento de las búsquedas:

```python
from pymilvus import Collection, FieldSchema, CollectionSchema, DataType, utility

# Definir esquema con partición
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=255),
]
schema = CollectionSchema(fields=fields, description="Documentos médicos")

# Crear colección
collection = Collection(name="documentos_medicos", schema=schema)

# Crear particiones
collection.create_partition("medicamentos")
collection.create_partition("procedimientos")
collection.create_partition("diagnósticos")

# Buscar sólo en particiones específicas
results = collection.search(
    data=[vector_query],
    anns_field="embedding",
    param={"metric_type": "COSINE", "params": {"nprobe": 10}},
    limit=10,
    expr="category == 'medicamento'",
    partition_names=["medicamentos"]
)
```

### 3. Uso de índices HNSW para alto rendimiento

HNSW (Hierarchical Navigable Small World) es un algoritmo de indexación que ofrece excelente rendimiento para la búsqueda aproximada de vecinos más cercanos:

```python
# Crear índice HNSW
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {
        "M": 16,
        "efConstruction": 200
    }
}

collection.create_index(
    field_name="embedding", 
    index_params=index_params
)
```

## Migración de datos existentes de Chroma a Milvus

Si ya tienes datos en Chroma y quieres migrarlos a Milvus, puedes usar el siguiente script:

```python
import os
from langchain_chroma import Chroma
from langchain_milvus import Milvus
from langchain_huggingface import HuggingFaceEmbeddings

def migrate_chroma_to_milvus(chroma_dir, milvus_collection_name, embeddings_model="intfloat/multilingual-e5-large-instruct"):
    """
    Migra datos de Chroma a Milvus.
    
    Args:
        chroma_dir (str): Directorio donde se encuentra la base de datos Chroma.
        milvus_collection_name (str): Nombre de la colección en Milvus.
        embeddings_model (str): Modelo de embeddings a utilizar.
    """
    # Crear modelo de embeddings
    embeddings = HuggingFaceEmbeddings(model_name=embeddings_model, model_kwargs={"device": "cuda"})
    
    # Cargar Chroma existente
    chroma_db = Chroma(persist_directory=chroma_dir, embedding_function=embeddings)
    
    # Obtener todos los documentos de Chroma
    documents = chroma_db.get()
    
    # Crear documentos para Milvus
    from langchain_core.documents import Document
    docs = []
    for i, (text, metadata) in enumerate(zip(documents["documents"], documents["metadatas"])):
        docs.append(Document(page_content=text, metadata=metadata))
    
    # Crear vectorstore Milvus
    connection_args = {"uri": "http://localhost:19530"}
    milvus_db = Milvus.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=milvus_collection_name,
        connection_args=connection_args,
        drop_old=True
    )
    
    print(f"Migrados {len(docs)} documentos de Chroma a Milvus (colección: {milvus_collection_name})")
    return milvus_db

# Uso:
# migrate_chroma_to_milvus("./chroma/CuboSalud", "CuboSalud")
```

## Consideraciones finales

### Recomendaciones para entornos de producción

1. **Usa Milvus Cloud (Zilliz)** para entornos de producción, ya que ofrece alta disponibilidad, escalabilidad automática y copia de seguridad.

2. **Implementa métodos de monitoreo** para supervisar el rendimiento y uso del sistema.

3. **Define una estrategia de particionamiento** adecuada para tu caso de uso, basada en cómo se consultarán los datos.

4. **Utiliza índices adecuados** para tu caso de uso. HNSW es bueno para la mayoría de los casos, pero hay otros que pueden funcionar mejor según tus datos.

### Limitaciones y consideraciones

1. **Mayor complejidad operativa**: Milvus requiere más componentes para funcionar (como etcd y MinIO) en comparación con Chroma.

2. **Curva de aprendizaje**: La API de Milvus es más compleja y podría requerir un tiempo de adaptación para los desarrolladores.

3. **Requisitos de recursos**: Milvus puede requerir más recursos de hardware, especialmente para colecciones grandes de vectores.

## Conclusión

La migración de Chroma a Milvus ofrece importantes beneficios en términos de escalabilidad, rendimiento y funcionalidades avanzadas, especialmente en entornos de producción o aplicaciones con grandes volúmenes de datos. Aunque implica algunos cambios en el código y un aumento en la complejidad operativa, las ventajas que proporciona Milvus en aplicaciones de IA generativa hacen que valga la pena esta migración. 