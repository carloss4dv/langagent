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
            
        try:
            # Crear la vectorstore
            vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=os.path.join(self.persist_directory, collection_name)
            )
            
            # Persistir la base de datos
            vectorstore.persist()
            
            logger.info(f"Vectorstore Chroma creada correctamente con {len(documents)} documentos")
            return vectorstore
            
        except Exception as e:
            logger.error(f"Error al crear la vectorstore Chroma: {e}")
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
        try:
            # Cargar la vectorstore
            vectorstore = Chroma(
                persist_directory=os.path.join(self.persist_directory, collection_name),
                embedding_function=embeddings
            )
            
            logger.info(f"Vectorstore Chroma cargada correctamente")
            return vectorstore
            
        except Exception as e:
            logger.error(f"Error al cargar la vectorstore Chroma: {e}")
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
            
        try:
            # Obtener parámetros de búsqueda desde la configuración o parámetros
            k = k or VECTORSTORE_CONFIG.get("k_retrieval", 4)
            
            # Crear el retriever
            retriever = vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": k,
                    "fetch_k": k * 2,  # Buscar más documentos para MMR
                    "lambda_mult": 0.7  # Balance entre relevancia y diversidad
                }
            )
            
            logger.info("Retriever Chroma creado correctamente")
            return retriever
            
        except Exception as e:
            logger.error(f"Error al crear retriever Chroma: {e}")
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
            
        try:
            # Añadir documentos
            vectorstore.add_documents(documents)
            
            # Persistir cambios
            vectorstore.persist()
            
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
            vectorstore = self.create_vectorstore(documents, embeddings, collection_name)
            if vectorstore is None:
                logger.error("No se pudo crear la vectorstore")
                return False
                
        # Añadir los documentos a la colección
        return self.add_documents_to_collection(vectorstore, documents, source_documents) 