"""
Módulo que define la interfaz base para todas las implementaciones de vectorstores.

Proporciona una clase abstracta base y una factoría para crear instancias
de diferentes implementaciones de vectorstores de forma transparente.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore
from langagent.config.config import VECTORSTORE_CONFIG

class VectorStoreBase(ABC):
    """Clase base abstracta para implementaciones de vectorstore."""
    
    @abstractmethod
    def create_vectorstore(self, documents: List[Document], embeddings: Embeddings, 
                         collection_name: str, **kwargs) -> VectorStore:
        """
        Crea una nueva vectorstore con los documentos proporcionados.
        
        Args:
            documents: Lista de documentos a indexar
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección
            
        Returns:
            VectorStore: Instancia de la vectorstore creada
        """
        pass
    
    @abstractmethod
    def load_vectorstore(self, embeddings: Embeddings, collection_name: str, 
                       **kwargs) -> VectorStore:
        """
        Carga una vectorstore existente.
        
        Args:
            embeddings: Modelo de embeddings a utilizar
            collection_name: Nombre de la colección
            
        Returns:
            VectorStore: Instancia de la vectorstore cargada
        """
        pass
    
    @abstractmethod
    def create_retriever(self, vectorstore: VectorStore, k: Optional[int] = None, 
                      similarity_threshold: float = 0.7, **kwargs) -> BaseRetriever:
        """
        Crea un retriever para una vectorstore.
        
        Args:
            vectorstore: Instancia de vectorstore
            k: Número de documentos a recuperar
            similarity_threshold: Umbral mínimo de similitud
            
        Returns:
            BaseRetriever: Retriever configurado
        """
        pass
    
    @abstractmethod
    def add_documents_to_collection(self, vectorstore: VectorStore, documents: List[Document], 
                                 source_documents: Dict[str, Document] = None) -> bool:
        """
        Añade documentos a una vectorstore existente.
        
        Args:
            vectorstore: Instancia de vectorstore
            documents: Lista de documentos a añadir
            source_documents: Diccionario con los documentos originales completos (opcional)
            
        Returns:
            bool: True si los documentos se añadieron correctamente
        """
        pass
    
    @abstractmethod
    def load_documents(self, documents: List[Document], embeddings: Embeddings = None, 
                     source_documents: Dict[str, Document] = None) -> bool:
        """
        Carga documentos en la vectorstore.
        
        Args:
            documents: Lista de documentos a cargar
            embeddings: Modelo de embeddings a utilizar (opcional)
            source_documents: Diccionario con los documentos originales completos (opcional)
            
        Returns:
            bool: True si los documentos se cargaron correctamente
        """
        pass
    
    @staticmethod
    def add_metadata_to_documents(documents: List[Document], cubo: str, ambito: Optional[str] = None) -> List[Document]:
        """
        Añade metadatos sobre el cubo y ámbito a los documentos.
        
        Args:
            documents: Lista de documentos a procesar
            cubo: Nombre del cubo
            ambito: Nombre del ámbito (opcional)
            
        Returns:
            List[Document]: Lista de documentos con metadatos añadidos
        """
        for doc in documents:
            doc.metadata["cubo_source"] = cubo
            if ambito:
                doc.metadata["ambito"] = ambito
        return documents

class VectorStoreFactory:
    """Factoría para crear instancias de vectorstores."""
    
    @staticmethod
    def get_vectorstore_instance(vector_db_type: str = None) -> VectorStoreBase:
        """
        Obtiene una instancia de vectorstore según el tipo especificado.
        
        Args:
            vector_db_type: Tipo de vectorstore ('chroma' o 'milvus')
            
        Returns:
            VectorStoreBase: Instancia de la implementación específica
        """
        # Si no se especifica, usar el valor de la configuración
        if vector_db_type is None:
            vector_db_type = VECTORSTORE_CONFIG.get("vector_db_type", "chroma")
        
        # Importar las clases específicas aquí para evitar dependencias circulares
        from langagent.vectorstore.chroma import ChromaVectorStore
        from langagent.vectorstore.milvus import MilvusVectorStore
        
        if vector_db_type.lower() == "chroma":
            return ChromaVectorStore()
        elif vector_db_type.lower() == "milvus":
            return MilvusVectorStore()
        else:
            raise ValueError(f"Tipo de vectorstore no soportado: {vector_db_type}") 