"""
Implementación de VectorStoreBase para Milvus/Zilliz.

Este módulo proporciona una implementación concreta de la interfaz VectorStoreBase
para la base de datos vectorial Milvus/Zilliz, aprovechando sus capacidades avanzadas
como filtrado por metadatos y búsqueda híbrida.
"""

import os
import time
import logging
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore
from langchain_milvus import Milvus, BM25BuiltInFunction
from langchain_milvus.retrievers import MilvusCollectionHybridSearchRetriever
from pymilvus import WeightedRanker
from langagent.vectorstore.base import VectorStoreBase
from langagent.config.config import VECTORSTORE_CONFIG
from langagent.models.constants import CUBO_TO_AMBITO, AMBITOS_CUBOS
from langagent.models.llm import create_context_generator
from tqdm import tqdm  # Añadir importación de tqdm para barra de progreso

logger = logging.getLogger(__name__)

class MilvusVectorStore(VectorStoreBase):
    """Implementación de VectorStoreBase para Milvus/Zilliz con soporte para búsqueda híbrida."""
    
    def __init__(self):
        """Inicializa la implementación de Milvus Vector Store."""
        self.use_hybrid_search = VECTORSTORE_CONFIG.get("use_hybrid_search", False)
        self.collection_name = VECTORSTORE_CONFIG.get("collection_name", "unified")
        self.partition_key_field = VECTORSTORE_CONFIG.get("partition_key_field", "ambito")
        self.use_context_generation = VECTORSTORE_CONFIG.get("use_context_generation", False)
        self.context_generator = None
    
    def set_context_generator(self, context_generator):
        """
        Establece el generador de contexto para enriquecer los chunks.
        
        Args:
            context_generator: Generador de contexto preconfigurado
        """
        if not self.use_context_generation:
            logger.warning("La generación de contexto está desactivada en la configuración. No se configurará el generador.")
            logger.warning("Establece VECTORSTORE_CONFIG['use_context_generation'] = True para activarla.")
            return
            
        if context_generator is None:
            logger.error("Error: Se proporcionó un generador de contexto nulo")
            return
            
        try:
            logger.info("Configurando generador de contexto para chunks...")
            self.context_generator = context_generator
            
            # Verificar el tipo de context_generator
            logger.info(f"Tipo de context_generator: {type(context_generator)}")
            
            # Realizar una pequeña prueba para verificar que funciona
            logger.info("Iniciando prueba del generador de contexto...")
            test_input = {
                "document": "Este es un documento de prueba para verificar que el generador funciona.",
                "chunk": "Este es un chunk de prueba."
            }
            logger.info(f"Enviando entrada de prueba: {test_input}")
            
            test_result = None
            try:
                test_result = self.context_generator.invoke(test_input)
                logger.info(f"Tipo de resultado: {type(test_result)}")
                logger.info(f"Resultado completo: {test_result}")
            except Exception as invoke_err:
                logger.error(f"Error al invocar el generador de contexto: {str(invoke_err)}")
                # Intentar con un formato alternativo
                try:
                    logger.info("Intentando formato alternativo...")
                    test_result = self.context_generator(test_input)
                    logger.info(f"Resultado con formato alternativo: {test_result}")
                except Exception as alt_err:
                    logger.error(f"Error al usar formato alternativo: {str(alt_err)}")
            
            # Verificar que el resultado tenga un formato válido (dict con key 'context' o string)
            if isinstance(test_result, dict) and 'context' in test_result:
                logger.info("Generador de contexto configurado y probado correctamente.")
                ejemplo = test_result['context']
                logger.info(f"Ejemplo de generación (JSON): '{ejemplo}'")
            elif isinstance(test_result, str) and len(test_result.strip()) > 0:
                logger.info("Generador de contexto configurado y probado correctamente.")
                logger.info(f"Ejemplo de generación (string): '{test_result.strip()}'")
            else:
                logger.warning("El generador de contexto se configuró pero la prueba no generó texto o el resultado no tiene el formato esperado.")
                logger.warning(f"Resultado obtenido: {test_result}")
                logger.warning("Comprueba que el modelo LLM está funcionando correctamente y que el prompt es adecuado.")
                
                # Intentar continuar a pesar del error
                logger.info("Se intentará continuar con el generador de contexto a pesar del error.")
                
            # En todos los casos, configuramos el generador si obtuvimos algún resultado
            if test_result is not None:
                logger.info("Generador de contexto configurado correctamente")
                
        except Exception as e:
            logger.error(f"Error al configurar el generador de contexto: {str(e)}")
            import traceback
            logger.error(f"Traza completa: {traceback.format_exc()}")
            self.context_generator = None
    
    def _get_connection_args(self) -> Dict[str, Any]:
        """
        Obtiene los argumentos de conexión para Milvus.
        Configurado para usar túnel SSH sin SSL.
        
        Returns:
            Dict[str, Any]: Argumentos de conexión
        """
        # Obtener parámetros de la configuración
        milvus_uri = VECTORSTORE_CONFIG.get("milvus_uri", "http://localhost:19530")
        milvus_token = VECTORSTORE_CONFIG.get("milvus_token", "root:Milvus")
        
        # Verificar si hay variables de entorno disponibles (tienen prioridad)
        env_uri = os.getenv("ZILLIZ_CLOUD_URI")
        env_token = os.getenv("ZILLIZ_CLOUD_TOKEN")
        
        if env_uri:
            milvus_uri = env_uri
            logger.info(f"Usando URI de Milvus desde variable de entorno: {milvus_uri}")
        else:
            logger.info(f"Usando URI de Milvus desde configuración: {milvus_uri}")
            
        if env_token:
            milvus_token = env_token
            logger.info("Usando token de autenticación desde variable de entorno")
        elif milvus_token:
            logger.info("Usando token de autenticación desde configuración")
        
        # Construir argumentos de conexión
        connection_args = {
            "uri": milvus_uri,
            "secure": False,  # Deshabilitar SSL ya que usamos túnel SSH
            "timeout": 60,  # Aumentar el timeout para operaciones largas
            "use_grpc": True,  # Usar gRPC para mejor rendimiento
            "grpc_secure": False  # Deshabilitar SSL en gRPC también
        }
        
        # Añadir token solo si está presente
        if milvus_token:
            connection_args["token"] = milvus_token
        
        logger.info(f"Conectando a Milvus a través de túnel SSH en: {milvus_uri} (gRPC: True, SSL: False)")
        
        return connection_args
    
    def create_vectorstore(self, documents: List[Document], embeddings: Embeddings, 
                         collection_name: str, **kwargs) -> Milvus:
        """
        Crea una nueva vectorstore Milvus con los documentos proporcionados.
        Configura particiones basadas en un campo clave en los metadatos.
        Muestra una barra de progreso durante el procesamiento.
        
        Args:
            documents: Lista de documentos a indexar
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección en Milvus
            
        Returns:
            Milvus: Instancia de la vectorstore creada
        """
        if not documents:
            logger.error("No se pueden crear vectorstores sin documentos.")
            return None
        
        # Mostrar el número de documentos a procesar
        logger.info(f"Preparando {len(documents)} documentos para vectorstore {collection_name}")
        
        # Verificar y asegurar que los documentos tienen los metadatos requeridos
        # Usar tqdm para mostrar el progreso
        logger.info("Verificando metadatos de los documentos...")
        with tqdm(total=len(documents), desc="Verificando metadatos", unit="doc") as progress_bar:
            updated_documents = []
            for doc in documents:
                # Verificar que el documento tiene un objeto de metadatos
                if 'metadata' not in doc.__dict__ or doc.metadata is None:
                    doc.metadata = {}
                
                # Asegurar que tiene el campo ambito
                if 'ambito' not in doc.metadata or not doc.metadata['ambito']:
                    # Intentar obtener el ámbito a partir del cubo_source
                    if 'cubo_source' in doc.metadata and doc.metadata['cubo_source'] in CUBO_TO_AMBITO:
                        doc.metadata['ambito'] = CUBO_TO_AMBITO[doc.metadata['cubo_source']]
                    else:
                        # Si no se puede determinar, usar un valor predeterminado
                        doc.metadata['ambito'] = "general"
                
                # Asegurar que tiene el campo cubo_source
                if 'cubo_source' not in doc.metadata or not doc.metadata['cubo_source']:
                    doc.metadata['cubo_source'] = "general"
                    
                # Inicializar el campo context_generation si no existe
                if 'context_generation' not in doc.metadata:
                    doc.metadata['context_generation'] = ""
                    
                # Convertir valores booleanos a string para evitar problemas con Milvus
                if 'is_consulta' in doc.metadata and isinstance(doc.metadata['is_consulta'], bool):
                    doc.metadata['is_consulta'] = str(doc.metadata['is_consulta']).lower()
                
                updated_documents.append(doc)
                progress_bar.update(1)
        
        # Reemplazar los documentos originales con los actualizados
        documents = updated_documents
        
        # Recuperar los argumentos de conexión
        connection_args = self._get_connection_args()
        
        # Obtener opciones para la vectorstore
        drop_old = kwargs.get("drop_old", True)
        check_collection_exists = kwargs.get("check_collection_exists", False)
        consistency_level = kwargs.get("consistency_level", "Strong")
        
        # Determinar si queremos usar búsqueda híbrida
        use_hybrid_search = kwargs.get("use_hybrid_search", self.use_hybrid_search)
        use_partition_key = VECTORSTORE_CONFIG.get("use_partitioning", False)
        partition_key_field = kwargs.get("partition_key_field", self.partition_key_field) if use_partition_key else None
        
        # Si se solicita verificar si la colección existe antes de crearla
        if check_collection_exists:
            try:
                # Intentar cargar la colección existente sin crear una nueva
                logger.info(f"Verificando si la colección {collection_name} ya existe...")
                
                # Preparar argumentos para verificar
                check_kwargs = {
                    "embedding_function": embeddings,
                    "collection_name": collection_name,
                    "connection_args": connection_args
                }
                
                # Configurar búsqueda híbrida si es necesario
                if use_hybrid_search:
                    check_kwargs["builtin_function"] = BM25BuiltInFunction()
                    check_kwargs["vector_field"] = ["dense", "sparse"]
                
                # Intentar cargar la colección
                existing_db = Milvus(**check_kwargs)
                
                # Verificar si la colección se cargó correctamente
                if hasattr(existing_db, 'col') and existing_db.col is not None:
                    logger.info(f"La colección {collection_name} ya existe. No se creará una nueva.")
                    
                    # Si no queremos recrearla, devolver la existente
                    if not drop_old:
                        logger.info(f"Usando colección existente {collection_name}")
                        return existing_db
                    else:
                        logger.info(f"La colección {collection_name} existe pero se recreará (drop_old=True)")
            except Exception as check_error:
                # Si hay un error al verificar, asumir que no existe
                logger.info(f"Error al verificar colección existente: {str(check_error)}")
                logger.info("Continuando con la creación de una nueva colección")
        
        try:
            logger.info(f"Creando vectorstore para colección {collection_name}")
            
            # Preparar argumentos base
            vs_kwargs = {
                "connection_args": connection_args,
                "collection_name": collection_name,
                "embedding": embeddings,
                "drop_old": drop_old,
                "consistency_level": consistency_level
            }
            
            # Si queremos usar particionamiento por ámbito o cubo
            if partition_key_field and use_partition_key:
                logger.info(f"Configurando particionamiento por campo: {partition_key_field}")
                vs_kwargs["partition_key_field"] = partition_key_field
            
            # Si queremos usar búsqueda híbrida (denso + sparse)
            if use_hybrid_search:
                logger.info("Configurando búsqueda híbrida con BM25")
                vs_kwargs["builtin_function"] = BM25BuiltInFunction()
                vs_kwargs["vector_field"] = ["dense", "sparse"]  # 'dense' para embeddings, 'sparse' para BM25
            
            # Crear la vectorstore
            vectorstore = Milvus.from_documents(
                documents=documents,
                **vs_kwargs
            )
            
            logger.info(f"Vectorstore creada correctamente con {len(documents)} documentos")
            return vectorstore
        except Exception as e:
            logger.error(f"Error al crear la vectorstore: {e}")

        # Intentar sin partition_key_field si el error es sobre ese campo
        if "PartitionKeyException" in str(e) and "partition key field" in str(e) and partition_key_field:
            logger.warning("Error con campo de partición. Intentando sin particionamiento...")
            # Eliminar partition_key_field y reintentar
            if "partition_key_field" in vs_kwargs:
                del vs_kwargs["partition_key_field"]
            
            try:
                vectorstore = Milvus.from_documents(
                    documents=documents,
                    **vs_kwargs
                )
                logger.info(f"Vectorstore creada correctamente sin particionamiento con {len(documents)} documentos")
                return vectorstore
            except Exception as e2:
                logger.error(f"Error en segundo intento sin particionamiento: {e2}")

        # Si el error es sobre un campo faltante, verificar y asegurar que todos los documentos lo tienen
        if "Insert missed an field" in str(e):
            field_match = re.search(r"Insert missed an field `([^`]+)`", str(e))
            if field_match:
                missing_field = field_match.group(1)
                logger.warning(f"Error por campo faltante: {missing_field}. Asegurando que todos los documentos lo tienen.")
                
                # Asegurar que todos los documentos tienen el campo requerido
                for doc in documents:
                    if missing_field not in doc.metadata:
                        doc.metadata[missing_field] = "general"  # Valor predeterminado
                
                # Reintentar con los documentos corregidos
                try:
                    vectorstore = Milvus.from_documents(
                        documents=documents,
                        **vs_kwargs
                    )
                    logger.info(f"Vectorstore creada correctamente después de corregir campos faltantes: {len(documents)} documentos")
                    return vectorstore
                except Exception as e3:
                    logger.error(f"Error en tercer intento después de corregir campos: {e3}")

        return None
    
    def load_vectorstore(self, embeddings: Embeddings, collection_name: str, 
                       **kwargs) -> Milvus:
        """
        Carga una vectorstore Milvus existente.
        Si la colección no existe, la crea con un documento de inicialización.
        
        Args:
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección en Milvus
            
        Returns:
            Milvus: Instancia de la vectorstore cargada
        """
        connection_args = self._get_connection_args()
        logger.info(f"Cargando vectorstore Milvus existente: {collection_name}")
        
        # Determinar si queremos usar búsqueda híbrida
        use_hybrid_search = kwargs.get("use_hybrid_search", self.use_hybrid_search)
        always_drop_old = kwargs.get("always_drop_old", False)
        
        try:
            # Preparar argumentos para cargar la vectorstore
            vs_kwargs = {
                "embedding_function": embeddings,
                "collection_name": collection_name,
                "connection_args": connection_args
            }
            
            # Si queremos usar búsqueda híbrida
            if use_hybrid_search:
                logger.info("Configurando función BM25 para búsqueda híbrida")
                vs_kwargs["builtin_function"] = BM25BuiltInFunction()
                vs_kwargs["vector_field"] = ["dense", "sparse"]  # 'dense' para embeddings, 'sparse' para BM25
            
            # Intentar cargar la vectorstore
            milvus_db = None
            collection_exists = False
            
            try:
                # Intentar cargar directamente
                milvus_db = Milvus(**vs_kwargs)
                
                # Verificar si la colección existe realmente
                if hasattr(milvus_db, 'col') and milvus_db.col is not None:
                    logger.info(f"Colección {collection_name} cargada correctamente")
                    collection_exists = True
                    # Si siempre queremos recrear, no devolvemos aquí
                    if not always_drop_old:
                        return milvus_db
                    else:
                        logger.info(f"La colección {collection_name} existe pero se recreará (always_drop_old=True)")
            except Exception as load_error:
                logger.warning(f"Error al cargar colección: {str(load_error)}")
                collection_exists = False
            
            # Si la colección no existe o siempre queremos recrearla, la creamos
            if not collection_exists or always_drop_old:
                # Crear una colección nueva con un documento de ejemplo para inicializar
                logger.info(f"{'Recreando' if collection_exists else 'Creando nueva'} colección {collection_name}")
                empty_doc = Document(
                    page_content="Documento de inicialización", 
                    metadata={"source": "init", "ambito": "general", "cubo_source": "general"}
                )
                
                # Crear la vectorstore con el documento de inicialización
                return self.create_vectorstore(
                    documents=[empty_doc],
                    embeddings=embeddings,
                    collection_name=collection_name,
                    drop_old=always_drop_old,  # Solo forzar drop_old si se solicitó
                    **kwargs
                )
            
            # Si llegamos aquí, la colección existe pero no pudimos cargarla correctamente
            logger.error(f"La colección {collection_name} existe pero no se pudo cargar correctamente")
            return None
            
        except Exception as e:
            logger.error(f"Error grave al cargar/crear colección {collection_name}: {str(e)}")
            
            # Último intento: crear una colección nueva
            try:
                logger.info(f"Último intento: creando nueva colección {collection_name}")
                empty_doc = Document(
                    page_content="Documento de inicialización (último intento)", 
                    metadata={"source": "init", "ambito": "general", "cubo_source": "general"}
                )
                
                return self.create_vectorstore(
                    documents=[empty_doc],
                    embeddings=embeddings,
                    collection_name=collection_name,
                    drop_old=False,  # No forzar drop_old en el último intento
                    **kwargs
                )
                
            except Exception as create_error:
                # Si falla la creación, registrar el error y proporcionar información detallada
                logger.error(f"Error final al crear colección {collection_name}: {str(create_error)}")
                if "connection" in str(e).lower():
                    logger.error(f"Problema de conexión a Milvus. Verifique que el servidor esté en ejecución en {connection_args['uri']} " +
                                f"y que las credenciales sean correctas.")
                    logger.error("Asegúrese de configurar las variables de entorno ZILLIZ_CLOUD_URI y ZILLIZ_CLOUD_TOKEN correctamente.")
                raise e
    
    def create_retriever(self, vectorstore: Milvus, k: Optional[int] = None, 
                      similarity_threshold: float = 0.7, **kwargs) -> BaseRetriever:
        """
        Crea un retriever para una vectorstore Milvus usando búsqueda híbrida.
        
        Args:
            vectorstore: Instancia de Milvus vectorstore
            k: Número de documentos a recuperar
            similarity_threshold: Umbral mínimo de similitud
            
        Returns:
            BaseRetriever: Retriever configurado para Milvus con búsqueda híbrida
        """
        # Verificar que la vectorstore no es None
        if vectorstore is None:
            logger.error("No se puede crear un retriever con una vectorstore None")
            return None
            
        # Obtener parámetros de búsqueda desde la configuración o parámetros
        k = k or VECTORSTORE_CONFIG.get("k_retrieval", 4)
        
        try:
            logger.info("Creando retriever con búsqueda híbrida")
            
            # Configurar parámetros de búsqueda para campos dense y sparse
            dense_search_params = {
                "metric_type": "L2",
                "params": {}
            }
            
            sparse_search_params = {
                "metric_type": "BM25"
            }
            
            # Crear el retriever híbrido
            retriever = MilvusCollectionHybridSearchRetriever(
                collection=vectorstore.col,
                rerank=WeightedRanker(0.7, 0.3),  # 70% dense, 30% sparse
                anns_fields=["dense", "sparse"],
                field_embeddings=[vectorstore.embedding_function, BM25BuiltInFunction()],
                field_search_params=[dense_search_params, sparse_search_params],
                top_k=k,
                text_field="text"
            )
            
            logger.info("Retriever híbrido creado correctamente")
            return retriever
            
        except Exception as e:
            logger.error(f"Error al crear retriever híbrido: {e}")
            # Intentar con parámetros mínimos como fallback
            try:
                logger.info("Intentando crear retriever con parámetros mínimos")
                return vectorstore.as_retriever()
            except Exception as e2:
                logger.error(f"Error al crear retriever con parámetros mínimos: {e2}")
                return None
    
    def retrieve_documents(self, retriever: BaseRetriever, query: str, 
                         metadata_filters: Optional[Dict[str, Any]] = None,
                         max_retries: int = 3) -> List[Document]:
        """
        Recupera documentos de un retriever con filtrado por metadatos.
        
        Args:
            retriever: Retriever a utilizar
            query: Consulta para la búsqueda
            metadata_filters: Filtros de metadatos a aplicar (ej: {"ambito": "seguridad"})
            max_retries: Número máximo de reintentos en caso de error
            
        Returns:
            List[Document]: Lista de documentos recuperados
        """
        logger.info(f"Recuperando documentos para query: {query}")
        
        # Verificar que el retriever no es None
        if retriever is None:
            logger.error("No se puede recuperar documentos con un retriever None")
            return []
        
        # Verificar si este retriever debe usar búsqueda híbrida
        use_hybrid = hasattr(retriever, '_use_hybrid_search') and retriever._use_hybrid_search
        
        if use_hybrid and hasattr(retriever, '_vectorstore'):
            logger.info("Usando búsqueda híbrida directamente desde retrieve_documents")
            try:
                # Preparar la expresión de filtro si hay filtros de metadatos
                filter_expr = ""
                if metadata_filters:
                    # Convertir valores booleanos a string para Milvus
                    for key, value in metadata_filters.items():
                        if isinstance(value, bool):
                            metadata_filters[key] = str(value).lower()
                    
                    filter_expr = self._build_filter_expression(metadata_filters)
                
                # Usar hybrid_search directamente en el vectorstore
                search_results = retriever._vectorstore.hybrid_search(
                    query=query,
                    k=VECTORSTORE_CONFIG.get("k_retrieval", 4),
                    expr=filter_expr if filter_expr else None,
                    fusion_coefficient=[0.7, 0.3]  # 70% dense, 30% sparse
                )
                
                # Convertir resultados a formato Document
                if search_results:
                    # El formato de hybrid_search devuelve tuplas (Document, score)
                    return [doc[0] for doc in search_results]
                return []
                
            except Exception as e:
                logger.error(f"Error al usar hybrid_search: {e}")
                # Intentar con método estándar como fallback
                logger.info("Fallback: usando método estándar del retriever")
        
        # Código existente para retriever estándar con filtros
        if metadata_filters:
            logger.info(f"Aplicando filtros de metadatos: {metadata_filters}")
            
            # Convertir valores booleanos a string para evitar problemas con Milvus
            for key, value in metadata_filters.items():
                if isinstance(value, bool):
                    metadata_filters[key] = str(value).lower()
            
            # Intentar recuperar con filtros
            for attempt in range(max_retries):
                try:
                    # Usar invoke() con parámetro filter
                    docs = retriever.invoke(query, filter=metadata_filters)
                    
                    if not docs:
                        logger.warning(f"No se encontraron documentos con filtros: {metadata_filters}")
                        if attempt == max_retries - 1:
                            # En el último intento, probar sin filtros
                            logger.info("Intentando recuperar sin filtros como último recurso")
                            return retriever.invoke(query)
                    else:
                        return docs
                    
                except Exception as e:
                    logger.error(f"Error en intento {attempt + 1} con filtros: {str(e)}")
                    
                    # Detectar error específico de multi-vector search
                    if "_collection_search does not support multi-vector search" in str(e) and use_hybrid:
                        # Reintentar con búsqueda híbrida manual
                        try:
                            logger.info("Detectado error de multi-vector. Reintentando con método manual.")
                            # Construir expresión de filtro para Milvus
                            filter_expr = self._build_filter_expression(metadata_filters)
                            
                            # Usar hybrid_search directamente
                            search_results = retriever._vectorstore.hybrid_search(
                                query=query,
                                k=VECTORSTORE_CONFIG.get("k_retrieval", 4),
                                expr=filter_expr if filter_expr else None,
                                fusion_coefficient=[0.7, 0.3]  # 70% dense, 30% sparse
                            )
                            
                            # Convertir resultados a formato Document
                            if search_results:
                                return [doc[0] for doc in search_results]
                            return []
                            
                        except Exception as hybrid_error:
                            logger.error(f"Error al usar hybrid_search manual: {hybrid_error}")
                    
                    if attempt == max_retries - 1:
                        logger.info("Intentando recuperar sin filtros como último recurso")
                        try:
                            return retriever.invoke(query)
                        except Exception as e2:
                            logger.error(f"Error final sin filtros: {str(e2)}")
                            return []
                    time.sleep(1)  # Esperar antes de reintentar
        else:
            # Sin filtros, usar método estándar
            for attempt in range(max_retries):
                try:
                    # Método estándar
                    docs = retriever.invoke(query)
                    
                    if not docs:
                        logger.warning(f"No se encontraron documentos relevantes para: {query}")
                        return []
                    
                    return docs
                    
                except Exception as e:
                    logger.error(f"Error en intento {attempt + 1}: {str(e)}")
                    
                    # Detectar error específico de multi-vector search
                    if "_collection_search does not support multi-vector search" in str(e) and use_hybrid:
                        # Reintentar con búsqueda híbrida manual
                        try:
                            logger.info("Detectado error de multi-vector. Reintentando con método manual.")
                            
                            # Usar hybrid_search directamente
                            search_results = retriever._vectorstore.hybrid_search(
                                query=query,
                                k=VECTORSTORE_CONFIG.get("k_retrieval", 4),
                                fusion_coefficient=[0.7, 0.3]  # 70% dense, 30% sparse
                            )
                            
                            # Convertir resultados a formato Document
                            if search_results:
                                return [doc[0] for doc in search_results]
                            return []
                            
                        except Exception as hybrid_error:
                            logger.error(f"Error al usar hybrid_search manual: {hybrid_error}")
                    
                    if attempt == max_retries - 1:
                        logger.error("Se agotaron los reintentos")
                        return []
                    time.sleep(1)  # Esperar antes de reintentar
    
    def _build_filter_expression(self, metadata_filters: Dict[str, Any]) -> str:
        """
        Construye una expresión de filtro para Milvus a partir de un diccionario de filtros.
        
        Args:
            metadata_filters: Diccionario con filtros de metadatos
            
        Returns:
            str: Expresión de filtro para Milvus
        """
        expressions = []
        
        for key, value in metadata_filters.items():
            if value is None:
                continue
                
            # Manejar diferentes tipos de datos
            if isinstance(value, bool):
                value_str = str(value).lower()
                expressions.append(f'{key} == "{value_str}"')
            elif isinstance(value, (int, float)):
                expressions.append(f'{key} == {value}')
            elif isinstance(value, list):
                if not value:
                    continue
                value_items = [f'"{item}"' if isinstance(item, str) else str(item) for item in value]
                expressions.append(f'{key} in [{", ".join(value_items)}]')
            else:
                value_str = str(value)
                expressions.append(f'{key} == "{value_str}"')
        
        if not expressions:
            return ""
            
        return " && ".join(expressions)
    
    def add_documents_to_collection(self, vectorstore: Milvus, documents: List[Document], 
                                 source_documents: Dict[str, Document] = None) -> bool:
        """
        Añade documentos a una vectorstore Milvus existente.
        Si está habilitado, genera contexto para mejorar la recuperación.
        Muestra una barra de progreso para visualizar el avance.
        
        Args:
            vectorstore: Instancia de Milvus vectorstore
            documents: Lista de documentos a añadir
            source_documents: Diccionario con los documentos originales completos (opcional)
            
        Returns:
            bool: True si los documentos se añadieron correctamente
        """
        if not documents:
            logger.warning("No hay documentos para añadir a la colección")
            return False
        
        logger.info(f"Añadiendo {len(documents)} documentos a la colección")
        
        # Verificar si source_documents es None o está vacío
        if source_documents is None or len(source_documents) == 0:
            logger.warning("No se proporcionaron documentos originales (source_documents es None o está vacío)")
            if self.use_context_generation and self.context_generator:
                logger.warning("Se activó la generación de contexto pero no se proporcionaron documentos originales")
                logger.warning("La generación de contexto se omitirá para estos documentos")
        
        # Si tenemos documentos originales y el generador de contexto está configurado,
        # generamos contexto antes de añadir los documentos
        if self.use_context_generation and self.context_generator and source_documents and len(source_documents) > 0:
            logger.info(f"Generando contexto para chunks antes de añadirlos a la colección...")
            
            # Mostrar ejemplo de los primeros documentos originales
            for i, doc in enumerate(list(source_documents.items())[:1]):
                source_path, source_doc = doc
                logger.info(f"Documento original {i}: {source_path}")
                logger.info(f"  Contenido: {source_doc.page_content[:100]}...")
            
            # Añadir mensaje claro que indique que comienza la generación de contexto
            logger.info("=== INICIANDO GENERACIÓN DE CONTEXTO ===")
            documents = self._generate_context_for_chunks(documents, source_documents)
            logger.info("=== FINALIZADA GENERACIÓN DE CONTEXTO ===")
            
            # Comprobar si algún documento tiene contexto
            docs_with_context = sum(1 for doc in documents if doc.metadata.get('context_generation', '').strip())
            logger.info(f"Documentos con contexto generado: {docs_with_context}/{len(documents)}")
        elif self.use_context_generation and not self.context_generator:
            logger.warning("Generación de contexto activada pero el generador no está configurado")
        else:
            logger.info("Generación de contexto desactivada para esta operación")
            
        # Verificar y asegurar que los documentos tienen los metadatos requeridos
        # Usar tqdm para mostrar el progreso
        logger.info("Verificando metadatos de los documentos...")
        with tqdm(total=len(documents), desc="Verificando metadatos", unit="doc") as progress_bar:
            updated_documents = []
            for doc in documents:
                # Verificar que el documento tiene un objeto de metadatos
                if 'metadata' not in doc.__dict__ or doc.metadata is None:
                    doc.metadata = {}
                
                # Asegurar que tiene el campo ambito
                if 'ambito' not in doc.metadata or not doc.metadata['ambito']:
                    # Intentar obtener el ámbito a partir del cubo_source
                    if 'cubo_source' in doc.metadata and doc.metadata['cubo_source'] in CUBO_TO_AMBITO:
                        doc.metadata['ambito'] = CUBO_TO_AMBITO[doc.metadata['cubo_source']]
                    else:
                        # Si no se puede determinar, usar un valor predeterminado
                        doc.metadata['ambito'] = "general"
                
                # Asegurar que tiene el campo cubo_source
                if 'cubo_source' not in doc.metadata or not doc.metadata['cubo_source']:
                    doc.metadata['cubo_source'] = "general"
                    
                # Inicializar el campo context_generation si no existe
                if 'context_generation' not in doc.metadata:
                    doc.metadata['context_generation'] = ""
                    
                # Convertir valores booleanos a string para evitar problemas con Milvus
                if 'is_consulta' in doc.metadata and isinstance(doc.metadata['is_consulta'], bool):
                    doc.metadata['is_consulta'] = str(doc.metadata['is_consulta']).lower()
                
                updated_documents.append(doc)
                progress_bar.update(1)
        
        # Reemplazar los documentos originales con los actualizados
        documents = updated_documents
            
        try:
            # Para colecciones grandes, dividir en lotes
            batch_size = 1000
            total_docs = len(documents)
            
            if total_docs <= batch_size:
                # Si son pocos documentos, añadirlos directamente
                logger.info(f"Añadiendo {total_docs} documentos a la colección")
                vectorstore.add_documents(documents)
                logger.info(f"Se han añadido {total_docs} documentos correctamente")
            else:
                # Para muchos documentos, procesarlos en lotes
                logger.info(f"Añadiendo {total_docs} documentos en lotes de {batch_size}")
                
                # Crear barra de progreso para el proceso de adición por lotes
                total_batches = (total_docs + batch_size - 1) // batch_size
                with tqdm(total=total_batches, desc="Añadiendo documentos", unit="lote") as progress_bar:
                    for i in range(0, total_docs, batch_size):
                        end_idx = min(i + batch_size, total_docs)
                        batch = documents[i:end_idx]
                        
                        # Actualizar la descripción con información del lote actual
                        current_batch = i // batch_size + 1
                        progress_bar.set_description(f"Añadiendo lote {current_batch}/{total_batches} ({len(batch)} docs)")
                        
                        # Añadir el lote
                        vectorstore.add_documents(batch)
                        
                        # Actualizar la barra de progreso
                        progress_bar.update(1)
                
                logger.info(f"Se han añadido {total_docs} documentos correctamente en {total_batches} lotes")
            
            return True
            
        except Exception as e:
            logger.error(f"Error al añadir documentos a la colección: {str(e)}")
            return False
    
    def _generate_context_for_chunks(self, documents: List[Document], 
                               source_documents: Dict[str, Document]) -> List[Document]:
        """
        Genera contexto para cada chunk utilizando el documento completo y el LLM.
        Muestra una barra de progreso para visualizar el avance del procesamiento.
        
        Args:
            documents: Lista de chunks (documentos) a enriquecer con contexto
            source_documents: Diccionario con los documentos originales completos
            
        Returns:
            List[Document]: Documentos con contexto generado añadido
        """
        if not self.use_context_generation or not self.context_generator:
            logger.warning("No se puede generar contexto: generador no configurado o función desactivada")
            logger.warning(f"use_context_generation: {self.use_context_generation}, context_generator existe: {self.context_generator is not None}")
            return documents
        
        if not source_documents or len(source_documents) == 0:
            logger.warning("No se puede generar contexto: no se proporcionaron documentos originales")
            return documents
            
        logger.info(f"Generando contexto para {len(documents)} chunks...")
        
        # Rastrear documentos procesados
        processed_count = 0
        total_docs = len(documents)
        docs_with_context = 0
        docs_without_source = 0
        
        # Crear barra de progreso
        progress_bar = tqdm(total=total_docs, desc="Generando contexto", unit="chunk")
        
        for i, doc in enumerate(documents):
            # Obtener la ruta del documento original
            source_path = doc.metadata.get('source', '')
            
            # Si no podemos identificar el documento original, lo registramos y continuamos
            if not source_path:
                logger.warning(f"El chunk {i} no tiene campo 'source' en sus metadatos")
                docs_without_source += 1
                progress_bar.update(1)  # Actualizar barra aunque se omita
                continue
                
            # Si el documento original no está en la colección, lo registramos y continuamos
            if source_path not in source_documents:
                logger.warning(f"No se encontró el documento original para el chunk {i}: {source_path}")
                docs_without_source += 1
                progress_bar.update(1)  # Actualizar barra aunque se omita
                continue
                
            # Obtener el documento original completo
            full_document = source_documents[source_path]
            
            # Si ya tiene un contexto generado, podemos saltarlo a menos que queramos regenerar
            if doc.metadata.get('context_generation', '').strip() and VECTORSTORE_CONFIG.get("log_context_generation", False):
                logger.info(f"El chunk {i} ya tiene contexto: {doc.metadata['context_generation'][:50]}...")
                docs_with_context += 1
                processed_count += 1
                progress_bar.update(1)  # Actualizar barra de progreso
                continue
            
            try:
                # Generar contexto para el chunk usando el LLM
                if VECTORSTORE_CONFIG.get("log_context_generation", False):
                    logger.info(f"Generando contexto para chunk {i}/{total_docs}: {source_path}")
                
                # Actualizar descripción de la barra con el avance
                progress_bar.set_description(f"Generando contexto ({processed_count}/{total_docs})")
                
                context_result = self.context_generator.invoke({
                    "document": full_document.page_content,
                    "chunk": doc.page_content
                })
                
                # Procesar el resultado: ahora es un dict con un campo 'context'
                if isinstance(context_result, dict) and 'context' in context_result:
                    context = context_result['context']
                else:
                    # Fallback si el formato no es el esperado
                    logger.warning(f"Formato inesperado de contexto generado: {type(context_result)}")
                    # Intentar convertir a string
                    context = str(context_result).strip()
                
                # Guardar el contexto generado en los metadatos
                doc.metadata['context_generation'] = context.strip()
                
                # Mostrar los primeros contextos generados para verificación
                if processed_count < 3 or VECTORSTORE_CONFIG.get("log_context_generation", False):
                    logger.info(f"Contexto generado para chunk {i}:")
                    logger.info(f"  Chunk: {doc.page_content[:100]}...")
                    logger.info(f"  Contexto: {context.strip()}")
                
                # Si el contexto no está vacío, contar
                if context.strip():
                    docs_with_context += 1
                
                # Actualizar contador
                processed_count += 1
                
                # Actualizar barra de progreso
                progress_bar.update(1)
                
                # Actualizar la descripción de la barra con el porcentaje
                completion_percentage = (processed_count / total_docs) * 100
                progress_bar.set_description(f"Generando contexto {completion_percentage:.1f}%")
                    
            except Exception as e:
                logger.error(f"Error al generar contexto para chunk {i}: {str(e)}")
                # En caso de error, establecer un contexto vacío
                doc.metadata['context_generation'] = ""
                progress_bar.update(1)  # Actualizar barra a pesar del error
        
        # Cerrar la barra de progreso
        progress_bar.close()
        
        # Mostrar resumen completo al finalizar
        logger.info(f"Resumen de generación de contexto:")
        logger.info(f"  Total de chunks: {total_docs}")
        logger.info(f"  Chunks procesados: {processed_count}")
        logger.info(f"  Chunks con contexto generado: {docs_with_context}")
        logger.info(f"  Chunks sin documento original: {docs_without_source}")
        
        # Verificar si se generó algún contexto
        if docs_with_context == 0:
            logger.warning("¡ADVERTENCIA! No se generó ningún contexto para ningún documento.")
            if docs_without_source > 0:
                logger.warning(f"  {docs_without_source} chunks no tenían documento original disponible.")
            logger.warning("Revisa la configuración del LLM y el generador de contexto.")
            
        return documents 