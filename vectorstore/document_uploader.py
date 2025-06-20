"""
DocumentUploader para gestionar la carga inteligente de documentos en vectorstores.
Maneja la verificación de documentos existentes y actualizaciones incrementales.
"""

import os
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langagent.vectorstore.base import VectorStoreBase
from langagent.config.config import VECTORSTORE_CONFIG
from langagent.models.constants import CUBO_TO_AMBITO
from tqdm import tqdm

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

class DocumentUploader:
    """Gestor inteligente de carga de documentos en vectorstores."""
    
    def __init__(self, vectorstore_handler: VectorStoreBase, embeddings: Embeddings):
        """
        Inicializa el DocumentUploader.
        
        Args:
            vectorstore_handler: Instancia del handler de vectorstore
            embeddings: Modelo de embeddings a utilizar
        """
        self.vectorstore_handler = vectorstore_handler
        self.embeddings = embeddings
        # No inicializar text_splitter aquí - se creará dinámicamente según la colección
    
    def extract_cubo_and_version(self, source: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Extrae el nombre del cubo y la versión del source path.
        Es más robusto para manejar paths completos.
        
        Args:
            source: Path del archivo fuente
            
        Returns:
            Tuple[str, int]: (nombre_cubo, version_numero) o (None, None)
        """
        if not source:
            return None, None
            
        file_name = os.path.basename(source)
        # Extraer el nombre del cubo y versión usando el patrón info_cubo_X_vY.md
        match = re.search(r'info_cubo_([^_]+)_v(\d+)\.md', file_name)
        if match:
            cubo_name = match.group(1)
            version = int(match.group(2))
            return cubo_name, version
        
        logger.debug(f"No se pudo extraer el cubo y la versión de: {source}")
        return None, None
    
    def get_existing_cubos_with_versions(self, vectorstore) -> Dict[str, int]:
        """
        Obtiene los cubos existentes con sus versiones.
        
        Args:
            vectorstore: Instancia de vectorstore
            
        Returns:
            Dict[str, int]: Diccionario de cubo -> versión_máxima
        """
        existing_cubos = {}
        
        try:
            # Obtener metadatos existentes
            existing_metadata = self.vectorstore_handler.get_existing_documents_metadata(vectorstore, "source")
            
            logger.info(f"Analizando {len(existing_metadata)} fuentes existentes...")
            
            for source in existing_metadata:
                cubo, version = self.extract_cubo_and_version(source)
                if cubo and version is not None and cubo != "general":
                    # Mantener la versión más alta encontrada para cada cubo
                    existing_version = existing_cubos.get(cubo)
                    if existing_version is None or version > existing_version:
                        existing_cubos[cubo] = version
            
            logger.info(f"Cubos existentes con versiones: {existing_cubos}")
            
        except Exception as e:
            logger.warning(f"No se pudieron verificar cubos existentes: {e}", exc_info=True)
            
        return existing_cubos
    
    def analyze_document_updates(self, documents: List[Document], 
                               existing_cubos: Dict[str, int]) -> Tuple[List[Document], List[str]]:
        """
        Analiza qué documentos son nuevos o actualizados y cuáles hay que eliminar.
        
        Args:
            documents: Lista de documentos a verificar
            existing_cubos: Diccionario de cubos existentes con versiones
            
        Returns:
            Tuple[List[Document], List[str]]: (documentos_a_cargar, cubos_a_eliminar)
        """
        new_documents = []
        cubos_to_remove = []
        processed_cubos = set()
        
        logger.info("Analizando actualizaciones de documentos...")
        
        for doc in documents:
            source = doc.metadata.get('source', '')
            cubo, version = self.extract_cubo_and_version(source)

            if not cubo:
                continue

            if cubo == "general":
                # Documentos generales siempre se añaden
                new_documents.append(doc)
                continue
                
            # Evitar procesar el mismo cubo múltiples veces
            if cubo in processed_cubos:
                new_documents.append(doc)
                continue
                
            processed_cubos.add(cubo)
            
            existing_version = existing_cubos.get(cubo)

            if existing_version is None:
                # Cubo nuevo - añadir
                logger.info(f"Cubo nuevo detectado: {cubo} v{version}")
                new_documents.append(doc)
            elif version is not None and version > existing_version:
                # Versión más nueva - eliminar la anterior y añadir la nueva
                logger.info(f"Actualización detectada: {cubo} v{existing_version} -> v{version}")
                cubos_to_remove.append(cubo)
                new_documents.append(doc)
            elif version is not None and version == existing_version:
                # Misma versión - no hacer nada
                logger.info(f"Cubo {cubo} v{version} ya existe con la misma versión")
            else:
                # Versión más antigua o version is None
                if version is not None:
                    logger.warning(f"Versión más antigua ignorada: {cubo} v{version} (existente: v{existing_version})")
                else:
                    logger.warning(f"Versión no encontrada para el cubo {cubo} en el documento {source}. Se ignora.")
        
        # Añadir todos los documentos de los cubos que necesitan ser cargados
        final_documents = []
        cubos_to_load = set()
        
        # Identificar todos los cubos que necesitan ser cargados
        for doc in new_documents:
            source = doc.metadata.get('source', '')
            cubo, _ = self.extract_cubo_and_version(source)
            if cubo != "general":
                cubos_to_load.add(cubo)
        
        # Añadir todos los documentos de esos cubos
        for doc in documents:
            source = doc.metadata.get('source', '')
            cubo, _ = self.extract_cubo_and_version(source)
            
            if cubo == "general" or cubo in cubos_to_load:
                final_documents.append(doc)
        
        logger.info(f"Documentos a cargar: {len(final_documents)}")
        logger.info(f"Cubos a eliminar: {cubos_to_remove}")
        
        return final_documents, cubos_to_remove
    
    def remove_documents_by_cubo(self, vectorstore, cubos_to_remove: List[str]) -> bool:
        """
        Elimina documentos de cubos específicos de la vectorstore.
        
        Args:
            vectorstore: Instancia de vectorstore
            cubos_to_remove: Lista de cubos a eliminar
            
        Returns:
            bool: True si se eliminaron correctamente
        """
        if not cubos_to_remove:
            return True
            
        logger.info(f"Eliminando documentos de cubos: {cubos_to_remove}")
        
        try:
            # Usar el método específico del handler de vectorstore
            if hasattr(self.vectorstore_handler, 'remove_documents_by_cubo'):
                return self.vectorstore_handler.remove_documents_by_cubo(vectorstore, cubos_to_remove)
            else:
                logger.warning("Método de eliminación no implementado en el handler")
                return False
        except Exception as e:
            logger.error(f"Error general eliminando documentos: {e}")
            return False
    
    def load_documents_intelligently(self, documents: List[Document], 
                                   collection_name: str = None,
                                   force_recreate: bool = False,
                                   chunk_size: Optional[int] = None) -> bool:
        """
        Carga documentos de forma inteligente en la vectorstore.
        
        Args:
            documents: Lista de documentos a cargar
            collection_name: Nombre de la colección
            force_recreate: Si True, fuerza la recreación completa
            chunk_size: Si se proporciona, sobreescribe el tamaño de chunk
            
        Returns:
            bool: True si se cargaron correctamente
        """
        if not documents:
            logger.warning("No hay documentos para cargar")
            return False
        
        collection_name = collection_name or VECTORSTORE_CONFIG.get("collection_name", "default_collection")
        
        # Usar el chunk_size proporcionado o extraerlo de la configuración/nombre
        final_chunk_size = chunk_size if chunk_size is not None else self.extract_chunk_size_from_collection(collection_name)
        
        logger.info(f"Preparando para cargar documentos en '{collection_name}' con chunk_size={final_chunk_size}")
        
        text_splitter = self.create_text_splitter(final_chunk_size)
        
        # Intentar cargar vectorstore existente
        existing_vectorstore = self.vectorstore_handler.load_vectorstore(self.embeddings, collection_name)
        
        if existing_vectorstore and not force_recreate:
            logger.info("Vectorstore existente encontrado - analizando actualizaciones...")
            
            # Obtener cubos existentes con versiones
            existing_cubos = self.get_existing_cubos_with_versions(existing_vectorstore)
            
            # Analizar qué documentos cargar y cuáles eliminar
            documents_to_load, cubos_to_remove = self.analyze_document_updates(documents, existing_cubos)
            
            if not documents_to_load and not cubos_to_remove:
                logger.info("No hay cambios que aplicar")
                return True
              # Eliminar documentos obsoletos si es necesario
            if cubos_to_remove:
                logger.info(f"Eliminando documentos obsoletos de cubos: {cubos_to_remove}")
                if not self.remove_documents_by_cubo(existing_vectorstore, cubos_to_remove):
                    logger.error("Error eliminando documentos obsoletos")
                    return False
            
            if documents_to_load:
                logger.info(f"Cargando {len(documents_to_load)} documentos actualizados...")
                
                # Chunkar documentos a cargar usando el text_splitter dinámico
                new_chunks = text_splitter.split_documents(documents_to_load)
                
                # Crear diccionario de documentos originales para generación de contexto
                source_documents = {doc.metadata.get('source', str(i)): doc for i, doc in enumerate(documents_to_load)}
                  # Añadir documentos con generación de contexto, pasando el chunk_size específico
                return self.vectorstore_handler.add_documents_to_collection(
                    existing_vectorstore, 
                    new_chunks, 
                    source_documents,
                    chunk_size=final_chunk_size
                )
            
            return True
            
        else:
            # Crear nueva vectorstore
            logger.info("Creando nueva vectorstore...")
            
            # Chunkar todos los documentos usando el text_splitter dinámico
            chunked_documents = text_splitter.split_documents(documents)
            
            # Crear diccionario de documentos originales para generación de contexto
            source_documents = {doc.metadata.get('source', str(i)): doc for i, doc in enumerate(documents)}
              # Cargar documentos usando el método existente (incluye generación de contexto)
            return self.vectorstore_handler.load_documents(
                chunked_documents, 
                embeddings=self.embeddings,
                source_documents=source_documents,
                chunk_size=final_chunk_size
            )
    
    def create_adaptive_collections(self, documents: List[Document]) -> Dict[str, bool]:
        """
        Crea colecciones adaptativas con diferentes tamaños de chunk usando la configuración.
        Incluye lógica de versiones para cada colección.
        
        Args:
            documents: Lista de documentos a procesar
            
        Returns:
            Dict[str, bool]: Resultado de cada colección creada
        """
        results = {}
        adaptive_collections = VECTORSTORE_CONFIG.get("adaptive_collections", {})
        
        if not adaptive_collections:
            logger.warning("No hay colecciones adaptativas configuradas en VECTORSTORE_CONFIG.")
            return results
        
        logger.info(f"Creando/actualizando colecciones adaptativas: {list(adaptive_collections.keys())}")

        for strategy, collection_name in adaptive_collections.items():
            try:
                chunk_size = int(strategy)
                logger.info(f"Procesando estrategia '{strategy}' para la colección '{collection_name}' con chunk_size={chunk_size}")
                
                # No forzar la recreación completa por defecto, la lógica inteligente se encargará
                force_recreate = False

                success = self.load_documents_intelligently(
                    documents,
                    collection_name=collection_name,
                    force_recreate=force_recreate,
                    chunk_size=chunk_size
                )
                results[collection_name] = success
            except ValueError:
                logger.warning(f"La clave de estrategia '{strategy}' en adaptive_collections no es un entero válido para chunk_size. Saltando...")
            except Exception as e:
                logger.error(f"Error al crear la colección adaptativa para la estrategia '{strategy}': {e}", exc_info=True)
                results[collection_name] = False
                
        return results
    
    def extract_chunk_size_from_collection(self, collection_name: str) -> int:
        """
        Extrae el tamaño de chunk del nombre de la colección.
        
        Args:
            collection_name: Nombre de la colección (ej: default_collection_369)
            
        Returns:
            int: Tamaño de chunk extraído, o el valor por defecto si no se encuentra
        """
        # Buscar patrón de números en el nombre de la colección
        import re
        match = re.search(r'_(\d+)(?:_|$)', collection_name)
        if match:
            chunk_size = int(match.group(1))
            logger.info(f"Tamaño de chunk extraído de '{collection_name}': {chunk_size}")
            return chunk_size
        
        # Si no se encuentra, usar el chunk_size por defecto de la configuración
        default_size = VECTORSTORE_CONFIG.get("chunk_size", 646)
        logger.warning(f"No se pudo extraer chunk_size de '{collection_name}', usando default: {default_size}")
        return default_size
    
    def create_text_splitter(self, chunk_size: int) -> RecursiveCharacterTextSplitter:
        """
        Crea un text_splitter con el tamaño de chunk especificado.
        
        Args:
            chunk_size: Tamaño de chunk a usar
            
        Returns:
            RecursiveCharacterTextSplitter: Splitter configurado
        """
        chunk_overlap = int(chunk_size * 0.1)  # 10% de overlap
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
