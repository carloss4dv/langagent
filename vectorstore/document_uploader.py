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
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=VECTORSTORE_CONFIG["chunk_size"],
            chunk_overlap=VECTORSTORE_CONFIG["chunk_overlap"]
        )
    
    def extract_cubo_and_version(self, source: str) -> Tuple[str, int]:
        """
        Extrae el nombre del cubo y la versión del source path.
        
        Args:
            source: Path del archivo fuente
            
        Returns:
            Tuple[str, int]: (nombre_cubo, version_numero)
        """
        # Extraer el nombre del cubo y versión usando el patrón info_cubo_X_vY.md
        match = re.search(r'info_cubo_([^_]+)_v(\d+)\.md', source)
        if match:
            cubo_name = match.group(1)
            version = int(match.group(2))
            return cubo_name, version
        return "general", 0
    
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
                if cubo != "general":
                    # Mantener la versión más alta encontrada para cada cubo
                    if cubo not in existing_cubos or version > existing_cubos[cubo]:
                        existing_cubos[cubo] = version
            
            logger.info(f"Cubos existentes con versiones: {existing_cubos}")
            
        except Exception as e:
            logger.warning(f"No se pudieron verificar cubos existentes: {e}")
            
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
            
            if cubo == "general":
                # Documentos generales siempre se añaden
                new_documents.append(doc)
                continue
                
            # Evitar procesar el mismo cubo múltiples veces
            if cubo in processed_cubos:
                new_documents.append(doc)
                continue
                
            processed_cubos.add(cubo)
            
            if cubo not in existing_cubos:
                # Cubo nuevo - añadir
                logger.info(f"Cubo nuevo detectado: {cubo} v{version}")
                new_documents.append(doc)
            elif version > existing_cubos[cubo]:
                # Versión más nueva - eliminar la anterior y añadir la nueva
                logger.info(f"Actualización detectada: {cubo} v{existing_cubos[cubo]} -> v{version}")
                cubos_to_remove.append(cubo)
                new_documents.append(doc)
            elif version == existing_cubos[cubo]:
                # Misma versión - no hacer nada
                logger.info(f"Cubo {cubo} v{version} ya existe con la misma versión")
            else:
                # Versión más antigua - no añadir
                logger.warning(f"Versión más antigua ignorada: {cubo} v{version} (existente: v{existing_cubos[cubo]})")
        
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
                                   force_recreate: bool = False) -> bool:
        """
        Carga documentos de forma inteligente en la vectorstore.
        
        Args:
            documents: Lista de documentos a cargar
            collection_name: Nombre de la colección
            force_recreate: Si True, fuerza la recreación completa
            
        Returns:
            bool: True si se cargaron correctamente
        """
        if not documents:
            logger.warning("No hay documentos para cargar")
            return False
        
        collection_name = collection_name or VECTORSTORE_CONFIG.get("collection_name", "default_collection")
        
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
                
                # Chunkar documentos a cargar
                new_chunks = self.text_splitter.split_documents(documents_to_load)
                
                # Crear diccionario de documentos originales para generación de contexto
                source_documents = {doc.metadata.get('source', str(i)): doc for i, doc in enumerate(documents_to_load)}
                
                # Añadir documentos con generación de contexto
                return self.vectorstore_handler.add_documents_to_collection(
                    existing_vectorstore, 
                    new_chunks, 
                    source_documents
                )
            
            return True
        else:
            # Crear nueva vectorstore
            logger.info("Creando nueva vectorstore...")
            
            # Chunkar todos los documentos
            chunked_documents = self.text_splitter.split_documents(documents)
            
            # Crear diccionario de documentos originales para generación de contexto
            source_documents = {doc.metadata.get('source', str(i)): doc for i, doc in enumerate(documents)}            
            # Cargar documentos usando el método existente (incluye generación de contexto)
            return self.vectorstore_handler.load_documents(
                chunked_documents, 
                embeddings=self.embeddings,
                source_documents=source_documents
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
            logger.warning("No se encontraron colecciones adaptativas configuradas")
            return {}
        
        logger.info(f"Colecciones adaptativas configuradas: {adaptive_collections}")
          # Mapeo de estrategias a tamaños de chunk reales
        # Basado en la configuración actual en config.py
        strategy_to_chunk_size = {
            "167": 167,   # Chunk size pequeño (actual en config)
            "369": 369,   # Chunk size mediano
            "646": 646,   # Chunk size grande (actual en config)
            "1094": 1094  # Chunk size muy grande
        }
        
        for strategy, collection_name in adaptive_collections.items():
            # Obtener el tamaño de chunk correspondiente a la estrategia
            if strategy not in strategy_to_chunk_size:
                logger.warning(f"Estrategia {strategy} no tiene un tamaño de chunk definido, saltando...")
                continue
                
            chunk_size = strategy_to_chunk_size[strategy]
            logger.info(f"Procesando colección adaptativa {collection_name} para estrategia {strategy} (chunk_size: {chunk_size})")
            
            # Verificar si existe la colección
            existing_vectorstore = self.vectorstore_handler.load_vectorstore(self.embeddings, collection_name)
            
            if existing_vectorstore:
                logger.info(f"Colección {collection_name} existe - analizando actualizaciones...")
                
                # Analizar actualizaciones para esta colección
                existing_cubos = self.get_existing_cubos_with_versions(existing_vectorstore)
                documents_to_load, cubos_to_remove = self.analyze_document_updates(documents, existing_cubos)
                
                if cubos_to_remove:
                    if not self.remove_documents_by_cubo(existing_vectorstore, cubos_to_remove):
                        logger.error(f"Error eliminando documentos obsoletos de {collection_name}")
                        results[strategy] = False
                        continue
                
                if documents_to_load:
                    # Crear text splitter específico para este tamaño
                    adaptive_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=chunk_size,
                        chunk_overlap=int(chunk_size * 0.1)  # 10% de overlap
                    )
                    
                    # Chunkar documentos con el tamaño específico
                    adaptive_chunks = adaptive_splitter.split_documents(documents_to_load)
                    
                    # Crear diccionario de documentos originales
                    source_documents = {doc.metadata.get('source', str(i)): doc for i, doc in enumerate(documents_to_load)}
                    
                    # Añadir documentos actualizados
                    success = self.vectorstore_handler.add_documents_to_collection(
                        existing_vectorstore, 
                        adaptive_chunks, 
                        source_documents
                    )
                    results[strategy] = success
                else:
                    logger.info(f"No hay actualizaciones para {collection_name}")
                    results[strategy] = True
            else:
                # Crear nueva colección adaptativa
                logger.info(f"Creando nueva colección adaptativa {collection_name}...")
                
                # Crear text splitter específico para este tamaño
                adaptive_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=int(chunk_size * 0.1)  # 10% de overlap
                )
                
                # Chunkar documentos con el tamaño específico
                adaptive_chunks = adaptive_splitter.split_documents(documents)
                
                # Crear vectorstore para esta estrategia
                vectorstore = self.vectorstore_handler.create_vectorstore(
                    documents=adaptive_chunks,
                    embeddings=self.embeddings,
                    collection_name=collection_name,
                    drop_old=True
                )
                
                results[strategy] = vectorstore is not None
            
            if results[strategy]:
                logger.info(f"Colección {collection_name} procesada correctamente")
            else:
                logger.error(f"Error procesando colección {collection_name}")
        
        return results
                