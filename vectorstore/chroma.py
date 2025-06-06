"""
Implementación de VectorStoreBase para ChromaDB.

Este módulo proporciona una implementación concreta de la interfaz VectorStoreBase
para la base de datos vectorial ChromaDB.
"""

import os
import time
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore
from langchain_chroma import Chroma
from langagent.vectorstore.base import VectorStoreBase
from langagent.config.config import VECTORSTORE_CONFIG

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

class ChromaVectorStore(VectorStoreBase):
    """Implementación de VectorStoreBase para Chroma."""
    
    def __init__(self):
        """Inicializa la implementación de Chroma Vector Store."""
        self.persist_directory = VECTORSTORE_CONFIG.get("persist_directory", "./vectordb")
        logger.info(f"ChromaVectorStore inicializado con directorio: {self.persist_directory}")
    
    def create_vectorstore(self, documents: List[Document], embeddings: Embeddings, 
                         collection_name: str, **kwargs) -> Chroma:
        """
        Crea una nueva vectorstore Chroma con los documentos proporcionados.
        
        Args:
            documents: Lista de documentos a indexar
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección en Chroma
            
        Returns:
            Chroma: Instancia de la vectorstore creada
        """
        if not documents:
            logger.error("No se pueden crear vectorstores sin documentos.")
            return None
            
        persist_dir = os.path.join(self.persist_directory, collection_name)
        logger.info(f"Creando vectorstore Chroma en: {persist_dir}")
        logger.info(f"Número de documentos a indexar: {len(documents)}")
        
        # Verificar que los documentos tienen contenido
        empty_docs = [i for i, doc in enumerate(documents) if not doc.page_content.strip()]
        if empty_docs:
            logger.warning(f"Se encontraron {len(empty_docs)} documentos vacíos en posiciones: {empty_docs[:5]}...")
            
        try:
            # Crear directorio si no existe
            os.makedirs(persist_dir, exist_ok=True)
            
            # Crear la vectorstore
            vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=persist_dir,
                collection_name=collection_name
            )
            
            # Verificar que se creó correctamente
            try:
                # Intentar una búsqueda simple para verificar que funciona
                test_results = vectorstore.similarity_search("test", k=1)
                logger.info(f"Vectorstore Chroma creada correctamente con {len(documents)} documentos")
                logger.info(f"Verificación exitosa - se encontraron {len(test_results)} resultados en búsqueda de prueba")
            except Exception as e:
                logger.warning(f"Vectorstore creada pero falló la verificación: {e}")
            
            return vectorstore
            
        except Exception as e:
            logger.error(f"Error al crear la vectorstore Chroma: {e}")
            logger.error(f"Directorio de persistencia: {persist_dir}")
            logger.error(f"Tipo de embeddings: {type(embeddings)}")
            return None
    
    def load_vectorstore(self, embeddings: Embeddings, collection_name: str, 
                       **kwargs) -> Chroma:
        """
        Carga una vectorstore Chroma existente.
        
        Args:
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección en Chroma
            
        Returns:
            Chroma: Instancia de la vectorstore cargada o None si no existe
        """
        persist_dir = os.path.join(self.persist_directory, collection_name)
        logger.info(f"Intentando cargar vectorstore Chroma desde: {persist_dir}")
        
        # Verificar si el directorio existe
        if not os.path.exists(persist_dir):
            logger.warning(f"El directorio {persist_dir} no existe")
            return None
            
        # Verificar si hay archivos en el directorio
        files_in_dir = os.listdir(persist_dir) if os.path.exists(persist_dir) else []
        logger.info(f"Archivos en directorio: {files_in_dir}")
        
        try:
            # Cargar la vectorstore
            vectorstore = Chroma(
                persist_directory=persist_dir,
                embedding_function=embeddings,
                collection_name=collection_name
            )
            
            # Verificar que se cargó correctamente contando documentos
            try:
                # Intentar obtener algunos documentos para verificar que hay contenido
                test_results = vectorstore.similarity_search("test", k=1)
                doc_count = len(vectorstore.get()['ids']) if hasattr(vectorstore, 'get') else "desconocido"
                logger.info(f"Vectorstore Chroma cargada correctamente")
                logger.info(f"Número de documentos en la colección: {doc_count}")
                logger.info(f"Búsqueda de prueba devolvió {len(test_results)} resultados")
                
                # Log de ejemplo de documento si existe
                if test_results:
                    logger.info(f"Ejemplo de documento recuperado: {test_results[0].page_content[:100]}...")
                
                return vectorstore
            except Exception as e:
                logger.error(f"Error al verificar la vectorstore cargada: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error al cargar la vectorstore Chroma: {e}")
            logger.error(f"Directorio: {persist_dir}")
            logger.error(f"Collection name: {collection_name}")
            return None
    
    def create_retriever(self, vectorstore: Chroma, k: Optional[int] = None, 
                      similarity_threshold: float = 0.7, **kwargs) -> BaseRetriever:
        """
        Crea un retriever para una vectorstore Chroma.
        
        Args:
            vectorstore: Instancia de Chroma vectorstore
            k: Número de documentos a recuperar
            similarity_threshold: Umbral mínimo de similitud
            
        Returns:
            BaseRetriever: Retriever configurado para Chroma
        """
        if vectorstore is None:
            logger.error("No se puede crear un retriever con una vectorstore None")
            return None
            
        # Obtener parámetros de búsqueda desde la configuración o parámetros
        k = k or VECTORSTORE_CONFIG.get("k_retrieval", 4)
        
        logger.info(f"Creando retriever Chroma con k={k}, threshold={similarity_threshold}")
        
        try:
            # Primero, intentar con similarity search (más compatible)
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={
                    "k": k,
                }
            )
            
            # Hacer una prueba de recuperación
            try:
                test_query = "test"
                test_docs = retriever.invoke(test_query)
                logger.info(f"Retriever creado exitosamente - prueba devolvió {len(test_docs)} documentos")
                
                if test_docs:
                    logger.info(f"Ejemplo de documento recuperado: {test_docs[0].page_content[:100]}...")
                else:
                    logger.warning("La prueba de retriever no devolvió documentos - posible problema")
                    
            except Exception as test_error:
                logger.error(f"Error en prueba de retriever: {test_error}")
                
            return retriever
            
        except Exception as e:
            logger.error(f"Error al crear retriever Chroma: {e}")
            
            # Intentar con parámetros mínimos como fallback
            try:
                logger.info("Intentando crear retriever con configuración mínima...")
                fallback_retriever = vectorstore.as_retriever()
                logger.info("Retriever de fallback creado exitosamente")
                return fallback_retriever
            except Exception as e2:
                logger.error(f"Error incluso con retriever de fallback: {e2}")
                return None
    
    def add_documents_to_collection(self, vectorstore: Chroma, documents: List[Document], 
                                 source_documents: Dict[str, Document] = None) -> bool:
        """
        Añade documentos a una vectorstore Chroma existente.
        
        Args:
            vectorstore: Instancia de Chroma vectorstore
            documents: Lista de documentos a añadir
            source_documents: Diccionario con los documentos originales completos (opcional)
            
        Returns:
            bool: True si los documentos se añadieron correctamente
        """
        if not documents:
            logger.warning("No hay documentos para añadir a la colección")
            return False
            
        logger.info(f"Añadiendo {len(documents)} documentos a la colección")
        
        try:
            # Contar documentos antes
            try:
                before_count = len(vectorstore.get()['ids']) if hasattr(vectorstore, 'get') else "desconocido"
                logger.info(f"Documentos antes de añadir: {before_count}")
            except:
                logger.info("No se pudo contar documentos antes de añadir")
            
            # Añadir documentos
            vectorstore.add_documents(documents)
            
            # Contar documentos después
            try:
                after_count = len(vectorstore.get()['ids']) if hasattr(vectorstore, 'get') else "desconocido"
                logger.info(f"Documentos después de añadir: {after_count}")
            except:
                logger.info("No se pudo contar documentos después de añadir")
            
            logger.info(f"Se han añadido {len(documents)} documentos correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al añadir documentos a la colección Chroma: {str(e)}")
            return False
    
    def load_documents(self, documents: List[Document], embeddings: Embeddings = None, 
                     source_documents: Dict[str, Document] = None) -> bool:
        """
        Carga documentos en la vectorstore Chroma.
        
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
            
        logger.info(f"Cargando {len(documents)} documentos en vectorstore")
        
        # Usar los embeddings proporcionados o los existentes
        embeddings = embeddings or self.embeddings
        if not embeddings:
            logger.error("No se pueden cargar documentos sin embeddings")
            return False
            
        # Obtener el nombre de la colección
        collection_name = VECTORSTORE_CONFIG.get("collection_name", "default_collection")
        logger.info(f"Usando colección: {collection_name}")
        
        # Intentar cargar la vectorstore existente
        vectorstore = self.load_vectorstore(embeddings, collection_name)
        
        if vectorstore is None:
            # Si no existe, crear una nueva
            logger.info("Creando nueva vectorstore...")
            vectorstore = self.create_vectorstore(documents, embeddings, collection_name)
            if vectorstore is None:
                logger.error("No se pudo crear la vectorstore")
                return False
        else:
            # Añadir los documentos a la colección existente
            logger.info("Añadiendo documentos a vectorstore existente...")
            return self.add_documents_to_collection(vectorstore, documents, source_documents)
                
        return True

    def debug_vectorstore_status(self, vectorstore: Chroma, collection_name: str = None):
        """
        Función de debug para diagnosticar el estado de la vectorstore.
        
        Args:
            vectorstore: Instancia de Chroma vectorstore
            collection_name: Nombre de la colección (opcional)
        """
        logger.info("=== DEBUG VECTORSTORE STATUS ===")
        
        if vectorstore is None:
            logger.error("Vectorstore es None")
            return
            
        try:
            # Información básica
            logger.info(f"Tipo de vectorstore: {type(vectorstore)}")
            logger.info(f"Collection name: {collection_name}")
            
            # Intentar obtener información de la colección
            if hasattr(vectorstore, 'get'):
                try:
                    all_data = vectorstore.get()
                    doc_count = len(all_data.get('ids', []))
                    logger.info(f"Número total de documentos: {doc_count}")
                    
                    if doc_count > 0:
                        # Mostrar algunos IDs y metadatos
                        ids = all_data.get('ids', [])[:3]
                        metadatas = all_data.get('metadatas', [])[:3]
                        logger.info(f"Primeros 3 IDs: {ids}")
                        logger.info(f"Primeros 3 metadatos: {metadatas}")
                except Exception as e:
                    logger.error(f"Error al obtener datos de la colección: {e}")
            
            # Probar búsqueda simple
            try:
                test_results = vectorstore.similarity_search("test", k=3)
                logger.info(f"Búsqueda de prueba 'test' devolvió: {len(test_results)} documentos")
                for i, doc in enumerate(test_results):
                    logger.info(f"Documento {i}: {doc.page_content[:100]}...")
            except Exception as e:
                logger.error(f"Error en búsqueda de prueba: {e}")
                
        except Exception as e:
            logger.error(f"Error en debug de vectorstore: {e}")
        
        logger.info("=== FIN DEBUG VECTORSTORE ===") 