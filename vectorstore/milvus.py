"""
Implementación de VectorStoreBase para Milvus/Zilliz.

Este módulo proporciona una implementación concreta de la interfaz VectorStoreBase
para la base de datos vectorial Milvus/Zilliz, aprovechando sus capacidades avanzadas
como filtrado por metadatos y búsqueda híbrida.
"""

import os
import time
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
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.retrievers.document_compressors import CrossEncoderReranker
import torch
# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

class MilvusVectorStore(VectorStoreBase):
    """Implementación de VectorStoreBase para Milvus/Zilliz con soporte para búsqueda híbrida."""
    
    def __init__(self):
        """Inicializa la implementación de Milvus Vector Store."""
        self.use_hybrid_search = VECTORSTORE_CONFIG.get("use_hybrid_search", False)
        self.collection_name = VECTORSTORE_CONFIG.get("collection_name", "unified")
        self.partition_key_field = VECTORSTORE_CONFIG.get("partition_key_field", "ambito")
        self.use_context_generation = VECTORSTORE_CONFIG.get("use_context_generation", False)
        self.context_generator = None
        self.host = VECTORSTORE_CONFIG.get("milvus_host", "localhost")
        self.port = VECTORSTORE_CONFIG.get("milvus_port", "19530")
        self.user = VECTORSTORE_CONFIG.get("milvus_user", "")
        self.password = VECTORSTORE_CONFIG.get("milvus_password", "")
        self.secure = VECTORSTORE_CONFIG.get("milvus_secure", False)
    
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
    
    def remove_documents_by_cubo(self, vectorstore, cubos_to_remove: List[str]) -> bool:
        """
        Elimina documentos de cubos específicos de la vectorstore Milvus.
        
        Args:
            vectorstore: Instancia de Milvus vectorstore
            cubos_to_remove: Lista de cubos a eliminar
            
        Returns:
            bool: True si se eliminaron correctamente
        """
        if not cubos_to_remove:
            return True
            
        logger.info(f"Eliminando documentos de cubos en Milvus: {cubos_to_remove}")
        
        try:
            # Para Milvus, usar delete con filtros
            for cubo in cubos_to_remove:
                try:
                    # Usar expresión de filtro de Milvus
                    filter_expr = f'cubo_source == "{cubo}"'
                    
                    # Verificar si la colección soporta delete
                    if hasattr(vectorstore, 'col') and vectorstore.col is not None:
                        # Usar la colección directamente para delete
                        vectorstore.col.delete(expr=filter_expr)
                        logger.info(f"Documentos del cubo {cubo} eliminados de Milvus")
                    else:
                        logger.warning(f"No se pudo acceder a la colección para eliminar cubo {cubo}")
                        
                except Exception as e:
                    logger.error(f"Error eliminando cubo {cubo} de Milvus: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error general eliminando documentos de Milvus: {e}")
            return False

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
                    if 'source' in doc.metadata:
                        # Extraer el nombre del cubo del source usando el patrón info_cubo_X_vY.md
                        match = re.search(r'info_cubo_([^_]+)_v\d+\.md', doc.metadata['source'])
                        if match:
                            cubo_name = match.group(1)
                            if cubo_name in CUBO_TO_AMBITO:
                                doc.metadata['ambito'] = CUBO_TO_AMBITO[cubo_name]
                                doc.metadata['cubo_source'] = cubo_name
                            else:
                                doc.metadata['ambito'] = "general"
                                doc.metadata['cubo_source'] = "general"
                        else:
                            doc.metadata['ambito'] = "general"
                            doc.metadata['cubo_source'] = "general"
                    else:
                        # Si no se puede determinar, usar un valor predeterminado
                        doc.metadata['ambito'] = "general"
                        doc.metadata['cubo_source'] = "general"
                
                # Asegurar que tiene el campo source
                if 'source' not in doc.metadata or not doc.metadata['source']:
                    doc.metadata['source'] = "general"
                    
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
                "consistency_level": consistency_level,
                "auto_id": True  # Asegurar que auto_id está siempre en True
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
                # Asegurar que auto_id sigue siendo True
                vs_kwargs["auto_id"] = True
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
                    # Asegurar que auto_id sigue siendo True
                    vs_kwargs["auto_id"] = True
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
        
        Args:
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección en Milvus
            
        Returns:
            Milvus: Instancia de la vectorstore cargada o None si no existe
        """
        connection_args = self._get_connection_args()
        logger.info(f"Cargando vectorstore Milvus existente: {collection_name}")
        
        # Determinar si queremos usar búsqueda híbrida
        use_hybrid_search = kwargs.get("use_hybrid_search", self.use_hybrid_search)
        
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
            milvus_db = Milvus(**vs_kwargs)
            
            # Verificar si la colección existe realmente
            if hasattr(milvus_db, 'col') and milvus_db.col is not None:
                logger.info(f"Colección {collection_name} cargada correctamente")
                return milvus_db
            else:
                logger.error(f"La colección {collection_name} no existe")
                return None
                
        except Exception as e:
            logger.error(f"Error al cargar la vectorstore Milvus: {str(e)}")
            return None
    
    def create_retriever(self, vectorstore: Milvus, k: Optional[int] = None, 
                      similarity_threshold: float = 0.7, **kwargs) -> BaseRetriever:
        """
        Crea un retriever para una vectorstore Milvus usando búsqueda híbrida.
        Opcionalmente aplica compresión contextual con BGE reranker.
        
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
        
        # Verificar si la compresión contextual está habilitada
        use_compression = VECTORSTORE_CONFIG.get("use_contextual_compression", False)
        
        try:
            # Crear el retriever base con búsqueda híbrida
            base_retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "k": k * VECTORSTORE_CONFIG.get("compression_top_k_multiplier", 2) if use_compression else k,
                    "score_threshold": similarity_threshold
                }
            )
            
            # Si la compresión contextual está habilitada, aplicarla
            if use_compression:
                
                logger.info("Configurando compresión contextual con BGE reranker")
                
                # Configuración del modelo
                model_name = VECTORSTORE_CONFIG.get("bge_reranker_model", "BAAI/bge-reranker-v2-m3")
                device = VECTORSTORE_CONFIG.get("bge_device", "cpu")
                max_length = VECTORSTORE_CONFIG.get("bge_max_length", 512)
                
                # Detectar automáticamente si CUDA está disponible
                if device == "auto":
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                
                logger.info(f"Cargando modelo BGE: {model_name} en dispositivo: {device}")
                
                # Crear el cross encoder con configuración específica
                cross_encoder = HuggingFaceCrossEncoder(
                    model_name=model_name,
                    model_kwargs={"device": device}
                )
                
                # Crear el compresor reranker
                compressor = CrossEncoderReranker(
                    model=cross_encoder,
                    top_n=k
                )
                
                # Crear el retriever con compresión
                compression_retriever = ContextualCompressionRetriever(
                    base_compressor=compressor, 
                    base_retriever=base_retriever
                )
                
                logger.info(f"Retriever con compresión contextual BGE creado correctamente")
                logger.info(f"  Modelo: {model_name}")
                logger.info(f"  Dispositivo: {device}")
                logger.info(f"  Top-k final: {k}")
                logger.info(f"  Documentos iniciales: {k * VECTORSTORE_CONFIG.get('compression_top_k_multiplier', 3)}")
                
                return compression_retriever
            else:
                logger.info("Retriever híbrido creado correctamente (sin compresión)")
                return base_retriever
            
        except Exception as e:
            logger.error(f"Error al crear retriever híbrido: {e}")
            logger.error(f"Detalles del error: {str(e)}")
            
            # Si falla la compresión, intentar sin ella
            if use_compression:
                logger.warning("Error con compresión contextual, intentando sin compresión como fallback")
                try:
                    fallback_retriever = vectorstore.as_retriever(
                        search_type="similarity",
                        search_kwargs={
                            "k": k,
                            "score_threshold": similarity_threshold
                        }
                    )
                    logger.info("Retriever fallback (sin compresión) creado correctamente")
                    return fallback_retriever
                except Exception as e_fallback:
                    logger.error(f"Error incluso con retriever fallback: {e_fallback}")
            
            # Último intento con parámetros mínimos
            try:
                logger.info("Intentando crear retriever con parámetros mínimos")
                return vectorstore.as_retriever()
            except Exception as e2:
                logger.error(f"Error al crear retriever con parámetros mínimos: {e2}")
                return None
    
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
        
        # VERIFICACIÓN CRUCIAL: Si la generación de contexto está activa, necesitamos source_documents
        if self.use_context_generation:
            if not self.context_generator:
                logger.error("ERROR: Generación de contexto está activada pero el generador no está configurado")
                logger.error("Asegúrate de llamar a set_context_generator() antes de cargar documentos")
                return False
                
            if not source_documents or len(source_documents) == 0:
                logger.error("ERROR: Generación de contexto está activada pero no se proporcionaron documentos originales")
                logger.error("Los source_documents son necesarios para generar contexto para los chunks")
                logger.error("Verifica que se estén pasando correctamente desde el DocumentUploader")
                return False
            
            logger.info("✓ Generación de contexto activada y configurada correctamente")
            logger.info(f"✓ Generador de contexto: {type(self.context_generator)}")
            logger.info(f"✓ Documentos originales disponibles: {len(source_documents)}")
        
        # Verificar si source_documents es None o está vacío y log apropiado
        if source_documents is None or len(source_documents) == 0:
            if self.use_context_generation and self.context_generator:
                logger.error("PROBLEMA: Generación de contexto activada pero no hay documentos originales")
                logger.error("Esto impedirá la generación de contexto. Verifica la configuración del DocumentUploader")
                return False
            else:
                logger.info("No se proporcionaron documentos originales (generación de contexto desactivada)")
        
        # Si tenemos documentos originales y el generador de contexto está configurado,
        # generamos contexto antes de añadir los documentos
        if self.use_context_generation and self.context_generator and source_documents and len(source_documents) > 0:
            logger.info(f"🚀 INICIANDO GENERACIÓN DE CONTEXTO para {len(documents)} chunks")
            logger.info(f"📚 Documentos originales disponibles: {len(source_documents)}")
            
            # Mostrar ejemplo de los primeros documentos originales
            for i, (source_path, source_doc) in enumerate(list(source_documents.items())[:2]):
                logger.info(f"📄 Documento original {i+1}: {source_path}")
                logger.info(f"   📝 Contenido: {source_doc.page_content[:100]}...")
            
            # Añadir mensaje claro que indique que comienza la generación de contexto
            logger.info("=" * 70)
            logger.info("🤖 INICIANDO GENERACIÓN DE CONTEXTO CON LLM")
            logger.info("=" * 70)
            
            documents = self._generate_context_for_chunks(documents, source_documents)
            
            logger.info("=" * 70)
            logger.info("✅ GENERACIÓN DE CONTEXTO COMPLETADA")
            logger.info("=" * 70)
            
            # Comprobar si algún documento tiene contexto
            docs_with_context = sum(1 for doc in documents if doc.metadata.get('context_generation', '').strip())
            logger.info(f"📊 Documentos con contexto generado: {docs_with_context}/{len(documents)}")
            
            if docs_with_context == 0:
                logger.warning("⚠️  ATENCIÓN: Ningún documento obtuvo contexto generado")
                logger.warning("⚠️  Verifica que el generador de contexto esté funcionando correctamente")
            elif docs_with_context < len(documents):
                logger.info(f"ℹ️  {len(documents) - docs_with_context} documentos no obtuvieron contexto (posiblemente ya lo tenían)")
            else:
                logger.info("🎉 Todos los documentos obtuvieron contexto exitosamente")
                
        elif self.use_context_generation and not self.context_generator:
            logger.error("❌ ERROR: Generación de contexto activada pero el generador no está configurado")
            logger.error("❌ Llama a set_context_generator() antes de cargar documentos")
            return False
        else:
            logger.info("ℹ️  Generación de contexto desactivada para esta operación")
            
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
                    if 'source' in doc.metadata:
                        # Extraer el nombre del cubo del source usando el patrón info_cubo_X_vY.md
                        match = re.search(r'info_cubo_([^_]+)_v\d+\.md', doc.metadata['source'])
                        if match:
                            cubo_name = match.group(1)
                            if cubo_name in CUBO_TO_AMBITO:
                                doc.metadata['ambito'] = CUBO_TO_AMBITO[cubo_name]
                                doc.metadata['cubo_source'] = cubo_name
                            else:
                                doc.metadata['ambito'] = "general"
                                doc.metadata['cubo_source'] = "general"
                        else:
                            doc.metadata['ambito'] = "general"
                            doc.metadata['cubo_source'] = "general"
                    else:
                        # Si no se puede determinar, usar un valor predeterminado
                        doc.metadata['ambito'] = "general"
                        doc.metadata['cubo_source'] = "general"
                
                # Asegurar que tiene el campo source
                if 'source' not in doc.metadata or not doc.metadata['source']:
                    doc.metadata['source'] = "general"
                    
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
            batch_size = 50  # Reducir aún más para evitar problemas
            total_docs = len(documents)
            
            if total_docs <= batch_size:
                # Si son pocos documentos, añadirlos directamente
                logger.info(f"Añadiendo {total_docs} documentos a la colección Milvus")
                
                # Verificar una vez más que auto_id está configurado correctamente
                try:
                    if hasattr(vectorstore, 'col') and vectorstore.col is not None:
                        schema = vectorstore.col.schema
                        if not schema.auto_id or not schema.primary_field.auto_id:
                            logger.error("La colección TODAVÍA no tiene auto_id configurado correctamente")
                            logger.error("Es necesario recrear la colección desde cero")
                            return False
                except Exception as final_check_error:
                    logger.warning(f"Error en verificación final de auto_id: {final_check_error}")
                
                # Intentar añadir directamente sin especificar IDs
                ids = vectorstore.add_documents(documents)
                logger.info(f"Se han añadido {total_docs} documentos correctamente")
                logger.info(f"IDs generados: {len(ids) if ids else 0}")
            else:
                # Para muchos documentos, procesarlos en lotes más pequeños
                logger.info(f"Añadiendo {total_docs} documentos en lotes de {batch_size}")
                
                # Crear barra de progreso para el proceso de adición por lotes
                total_batches = (total_docs + batch_size - 1) // batch_size
                with tqdm(total=total_batches, desc="Añadiendo documentos", unit="lote") as progress_bar:
                    all_ids = []
                    for i in range(0, total_docs, batch_size):
                        end_idx = min(i + batch_size, total_docs)
                        batch = documents[i:end_idx]
                        
                        # Actualizar la descripción con información del lote actual
                        current_batch = i // batch_size + 1
                        progress_bar.set_description(f"Añadiendo lote {current_batch}/{total_batches} ({len(batch)} docs)")
                        
                        try:
                            # Añadir el lote sin especificar IDs (auto_id=True)
                            # Pasar ids=None explícitamente para forzar auto-generación
                            batch_ids = vectorstore.add_documents(batch, ids=None)
                            if batch_ids:
                                all_ids.extend(batch_ids)
                            
                            # Actualizar la barra de progreso
                            progress_bar.update(1)
                            
                        except Exception as batch_error:
                            logger.error(f"Error añadiendo lote {current_batch}: {str(batch_error)}")
                            
                            # Si el error es sobre IDs, intentar con método alternativo
                            if "auto_id" in str(batch_error) or "valid ids" in str(batch_error):
                                logger.warning("Error relacionado con IDs - intentando método alternativo")
                                
                                try:
                                    # Método alternativo: usar directamente la colección de Milvus
                                    if hasattr(vectorstore, 'col') and vectorstore.col is not None:
                                        logger.info("Intentando inserción directa en la colección")
                                        
                                        # Preparar datos para inserción directa
                                        texts = [doc.page_content for doc in batch]
                                        metadatas = [doc.metadata for doc in batch]
                                        
                                        # Usar el método insert de vectorstore con ids=None
                                        batch_ids = vectorstore.add_texts(
                                            texts=texts,
                                            metadatas=metadatas,
                                            ids=None  # Explícitamente None para auto-generación
                                        )
                                        
                                        if batch_ids:
                                            all_ids.extend(batch_ids)
                                        logger.info(f"Lote {current_batch} añadido exitosamente con método alternativo")
                                        progress_bar.update(1)
                                        
                                    else:
                                        logger.error("No se pudo acceder a la colección para método alternativo")
                                        raise batch_error
                                        
                                except Exception as alt_error:
                                    logger.error(f"Error en método alternativo del lote {current_batch}: {str(alt_error)}")
                                    
                                    # Último intento: recrear documentos completamente limpios
                                    try:
                                        logger.info("Último intento con documentos completamente limpios")
                                        
                                        clean_texts = []
                                        clean_metadatas = []
                                        
                                        for doc in batch:
                                            # Limpiar contenido
                                            clean_text = doc.page_content.strip()
                                            if not clean_text:
                                                clean_text = "Contenido vacío"
                                            
                                            # Limpiar metadatos
                                            clean_metadata = {}
                                            for key, value in doc.metadata.items():
                                                if value is not None and str(value).strip():
                                                    clean_metadata[key] = str(value).strip()
                                                else:
                                                    clean_metadata[key] = "default"
                                            
                                            clean_texts.append(clean_text)
                                            clean_metadatas.append(clean_metadata)
                                        
                                        # Intentar con textos y metadatos limpios
                                        batch_ids = vectorstore.add_texts(
                                            texts=clean_texts,
                                            metadatas=clean_metadatas
                                            # No especificar ids en absoluto
                                        )
                                        
                                        if batch_ids:
                                            all_ids.extend(batch_ids)
                                        logger.info(f"Lote {current_batch} añadido exitosamente con limpieza completa")
                                        progress_bar.update(1)
                                        
                                    except Exception as final_error:
                                        logger.error(f"Error en último intento del lote {current_batch}: {str(final_error)}")
                                        raise batch_error
                            else:
                                raise batch_error
                
                logger.info(f"Se han añadido {total_docs} documentos correctamente en {total_batches} lotes")
                logger.info(f"Total de IDs generados: {len(all_ids)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error al añadir documentos a la colección Milvus: {str(e)}")
            
            # Log adicional para debugging
            if "auto_id" in str(e) or "valid ids" in str(e):
                logger.error("Error relacionado con generación automática de IDs en Milvus")
                logger.error("Verificando si la colección está configurada correctamente con auto_id=True")
                
                # Intentar diagnosticar el problema
                try:
                    if hasattr(vectorstore, 'col') and vectorstore.col is not None:
                        logger.info(f"Colección: {vectorstore.col.name}")
                        logger.info(f"Descripción: {vectorstore.col.description}")
                        
                        # Verificar schema
                        schema = vectorstore.col.schema
                        logger.info(f"Schema de la colección: {schema}")
                        for field in schema.fields:
                            logger.info(f"Campo: {field.name}, Tipo: {field.dtype}, Auto ID: {field.auto_id}")
                        
                        # Información adicional sobre el campo primario
                        primary_field = schema.primary_field
                        if primary_field:
                            logger.info(f"Campo primario: {primary_field.name}, Auto ID: {primary_field.auto_id}")
                            
                except Exception as diag_error:
                    logger.error(f"Error en diagnóstico: {diag_error}")
            
            return False
    

    def _generate_context_for_chunks(self, documents: List[Document], 
                               source_documents: Dict[str, Document]) -> List[Document]:
        """
        Genera contexto para cada chunk utilizando el documento completo y el LLM.
        Optimizado para procesamiento en lotes y concurrencia.
        
        Args:
            documents: Lista de chunks (documentos) a enriquecer con contexto
            source_documents: Diccionario con los documentos originales completos
            
        Returns:
            List[Document]: Documentos con contexto generado añadido
        """
        if not self.use_context_generation or not self.context_generator:
            logger.warning("No se puede generar contexto: generador no configurado o función desactivada")
            return documents
        
        if not source_documents or len(source_documents) == 0:
            logger.warning("No se puede generar contexto: no se proporcionaron documentos originales")
            return documents
            
        logger.info(f"Generando contexto para {len(documents)} chunks...")
        
        # Configuración de optimización
        batch_size = VECTORSTORE_CONFIG.get("context_batch_size", 10)  # Procesar en lotes
        max_workers = VECTORSTORE_CONFIG.get("context_max_workers", 3)  # Concurrencia limitada
        skip_existing = VECTORSTORE_CONFIG.get("skip_existing_context", True)
        
        # Filtrar documentos que necesitan contexto
        docs_to_process = []
        docs_with_existing_context = 0
        
        for i, doc in enumerate(documents):
            # Saltar documentos que ya tienen contexto si está configurado
            if skip_existing and doc.metadata.get('context_generation', '').strip():
                docs_with_existing_context += 1
                continue
                
            source_path = doc.metadata.get('source', '')
            if source_path and source_path in source_documents:
                docs_to_process.append((i, doc, source_documents[source_path]))
        
        if docs_with_existing_context > 0:
            logger.info(f"Saltando {docs_with_existing_context} documentos que ya tienen contexto")
        
        if not docs_to_process:
            logger.info("No hay documentos para procesar contexto")
            return documents
        
        logger.info(f"Procesando contexto para {len(docs_to_process)} chunks en lotes de {batch_size}")
        
        # Función para procesar un lote de documentos
        def process_batch(batch):
            batch_results = []
            for doc_idx, doc, full_document in batch:
                try:
                    # Preparar input para el generador
                    context_input = {
                        "document": full_document.page_content,
                        "chunk": doc.page_content
                    }
                    
                    # Generar contexto
                    context_result = self.context_generator.invoke(context_input)
                    
                    # Procesar resultado
                    if isinstance(context_result, dict) and 'context' in context_result:
                        context = context_result['context']
                        if isinstance(context, dict):
                            import json
                            context = json.dumps(context, ensure_ascii=False, indent=2)
                    else:
                        if isinstance(context_result, dict):
                            import json
                            context = json.dumps(context_result, ensure_ascii=False, indent=2)
                        else:
                            context = str(context_result)
                    
                    if not isinstance(context, str):
                        import json
                        context = json.dumps(context, ensure_ascii=False, indent=2)
                    
                    batch_results.append((doc_idx, context.strip()))
                    
                except Exception as e:
                    logger.error(f"Error procesando chunk {doc_idx}: {str(e)}")
                    batch_results.append((doc_idx, ""))
            
            return batch_results
        
        # Procesar en lotes con ThreadPoolExecutor para I/O concurrente
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        processed_count = 0
        total_docs = len(docs_to_process)
        
        # Crear barra de progreso
        progress_bar = tqdm(total=total_docs, desc="Generando contexto", unit="chunk")
        
        # Dividir en lotes
        batches = [docs_to_process[i:i + batch_size] for i in range(0, len(docs_to_process), batch_size)]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Enviar todos los lotes
            future_to_batch = {executor.submit(process_batch, batch): batch for batch in batches}
            
            for future in as_completed(future_to_batch):
                try:
                    batch_results = future.result()
                    
                    # Aplicar resultados al documento original
                    for doc_idx, context in batch_results:
                        documents[doc_idx].metadata['context_generation'] = context
                        processed_count += 1
                        
                        # Actualizar barra de progreso
                        progress_bar.update(1)
                        completion_percentage = (processed_count / total_docs) * 100
                        progress_bar.set_description(f"Generando contexto {completion_percentage:.1f}%")
                        
                except Exception as e:
                    logger.error(f"Error procesando lote: {str(e)}")
                    # Actualizar progreso incluso si falla el lote
                    batch = future_to_batch[future]
                    progress_bar.update(len(batch))
        
        progress_bar.close()
        
        # Contar documentos con contexto final
        docs_with_context = sum(1 for doc in documents if doc.metadata.get('context_generation', '').strip())
        
        logger.info(f"Resumen de generación de contexto:")
        logger.info(f"  Total de chunks: {len(documents)}")
        logger.info(f"  Chunks procesados: {processed_count}")
        logger.info(f"  Chunks con contexto final: {docs_with_context}")
        logger.info(f"  Chunks con contexto previo: {docs_with_existing_context}")
        
        return documents 

    def load_documents(self, documents: List[Document], embeddings: Embeddings = None, 
                     source_documents: Dict[str, Document] = None) -> bool:
        """
        Carga documentos en la vectorstore.
        Si la colección no existe, la crea.
        Si la generación de contexto está activa, maneja el contexto apropiadamente.
        
        Args:
            documents: Lista de documentos a cargar
            embeddings: Modelo de embeddings a utilizar (opcional)
            source_documents: Diccionario con los documentos originales completos (opcional)
            
        Returns:
            bool: True si los documentos se cargaron correctamente
        """
        if not documents:
            logger.warning("No hay documentos para cargar")
            return False
            
        # Usar los embeddings proporcionados o los existentes
        embeddings = embeddings or self.embeddings
        if not embeddings:
            logger.error("No se pueden cargar documentos sin embeddings")
            return False
            
        # Obtener el nombre de la colección
        collection_name = VECTORSTORE_CONFIG.get("collection_name", "default_collection")
        
        # Intentar cargar la vectorstore existente
        vectorstore = self.load_vectorstore(embeddings, collection_name)
        
        if vectorstore is None:
            # Si no existe, crear una nueva
            logger.info("Creando nueva vectorstore...")
            
            # Si la generación de contexto está activa, crear una colección vacía primero
            if self.use_context_generation:
                logger.info("Generación de contexto activa: creando colección vacía primero")
                empty_doc = Document(
                    page_content="Documento de inicialización", 
                    metadata={"source": "init", "ambito": "general", "cubo_source": "general", "context_generation": ""}
                )
                vectorstore = self.create_vectorstore([empty_doc], embeddings, collection_name, drop_old=True)
                if vectorstore is None:
                    logger.error("No se pudo crear la colección vacía")
                    return False
                
                # Ahora añadir los documentos reales con generación de contexto
                return self.add_documents_to_collection(vectorstore, documents, source_documents)
            else:
                # Sin generación de contexto, crear directamente
                vectorstore = self.create_vectorstore(documents, embeddings, collection_name)
                if vectorstore is None:
                    logger.error("No se pudo crear la vectorstore")
                    return False
                return True
        else:
            # La colección ya existe, añadir los documentos
            logger.info("Vectorstore existente encontrado - añadiendo documentos...")
            return self.add_documents_to_collection(vectorstore, documents, source_documents)
    
    def get_existing_documents_metadata(self, vectorstore, field: str = "source") -> set:
        """
        Obtiene metadatos de documentos existentes para verificar duplicados.
        
        Args:
            vectorstore: Instancia de Milvus vectorstore
            field: Campo de metadata a verificar
            
        Returns:
            set: Conjunto de valores únicos del campo especificado
        """
        existing_values = set()
        
        try:
            if hasattr(vectorstore, 'similarity_search'):
                # Hacer múltiples búsquedas para obtener más documentos
                search_terms = ["cubo", "información", "datos", "consulta", ""]
                
                for term in search_terms:
                    try:
                        docs = vectorstore.similarity_search(term, k=50)
                        for doc in docs:
                            if field in doc.metadata and doc.metadata[field]:
                                existing_values.add(doc.metadata[field])
                    except Exception as e:
                        logger.debug(f"Error en búsqueda con término '{term}': {e}")
                        continue
                        
                logger.info(f"Metadatos existentes encontrados para '{field}': {len(existing_values)} valores únicos")
                        
        except Exception as e:
            logger.warning(f"No se pudieron obtener metadatos existentes: {e}")
            
        return existing_values