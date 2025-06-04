"""
Módulo para cargar y procesar documentos desde archivos markdown.

Este módulo proporciona funciones para cargar documentos desde archivos markdown
y procesarlos para su uso en sistemas de recuperación de información.
"""

import os
from typing import Dict, List
from langchain_core.documents import Document
from langchain_community.document_loaders import UnstructuredMarkdownLoader, DirectoryLoader, TextLoader

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

def load_file(file_path: str) -> List[Document]:
    """
    Carga un archivo markdown y lo convierte en una lista de documentos.
    
    Args:
        file_path (str): Ruta al archivo markdown a cargar.
        
    Returns:
        List[Document]: Lista de documentos extraídos del archivo.
    """
    # Corrige el nombre de la variable (file_path en lugar de path)
    loader = UnstructuredMarkdownLoader(file_path)
    elements = loader.load()  # Esto ya devuelve una lista de Documents
    
    # Verifica que los elementos tengan contenido
    if not elements:
        logger.warning(f"Advertencia: {file_path} está vacío o no se pudo cargar.")
        return []
    
    # Añade metadatos a cada documento
    for doc in elements:
        doc.metadata["source"] = file_path
    
    return elements

def load_documents_from_directory(directory_path: str) -> List[Document]:
    """
    Carga documentos Markdown desde un directorio.
    
    Args:
        directory_path (str): Ruta del directorio que contiene los documentos.
        
    Returns:
        List[Document]: Lista de documentos cargados.
    """
    if not os.path.exists(directory_path):
        return []
    
    loader = DirectoryLoader(
        directory_path,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    
    documents = []
    try:
        documents = loader.load()
        # Filtrar documentos vacíos
        documents = [doc for doc in documents if doc.page_content.strip()]
        
        # Advertir sobre archivos vacíos si es necesario
        all_files = loader.load()
        empty_files = [doc for doc in all_files if not doc.page_content.strip()]
        for doc in empty_files:
            file_path = doc.metadata.get('source', 'archivo desconocido')
            logger.warning(f"Advertencia: {file_path} está vacío o no se pudo cargar.")
    except Exception as e:
        logger.error(f"Error al cargar documentos desde {directory_path}: {e}")
    
    return documents

def load_all_documents_from_directories(directory_paths: List[str]) -> List[Document]:
    """
    Carga documentos desde múltiples directorios.
    
    Args:
        directory_paths (List[str]): Lista de rutas de directorios.
        
    Returns:
        List[Document]: Lista combinada de documentos cargados.
    """
    all_documents = []
    
    for directory_path in directory_paths:
        documents = load_documents_from_directory(directory_path)
        all_documents.extend(documents)
    
    return all_documents

def load_documents_with_metadata(directory_path: str, metadata: dict = None) -> List[Document]:
    """
    Carga documentos y les añade metadata personalizado.
    
    Args:
        directory_path (str): Ruta del directorio que contiene los documentos.
        metadata (dict, optional): Metadata adicional para añadir a cada documento.
        
    Returns:
        List[Document]: Lista de documentos con metadata añadido.
    """
    documents = load_documents_from_directory(directory_path)
    
    if metadata:
        for doc in documents:
            for key, value in metadata.items():
                doc.metadata[key] = value
                
    for file in os.listdir(directory_path):
        if file.endswith('.md'):
            logger.info(f" Loaded file {file} with {len(docs)} documents")
    
    return documents

def load_consultas_guardadas(consultas_dir: str) -> List[Document]:
    """
    Carga consultas guardadas desde un directorio específico.
    
    Args:
        consultas_dir (str): Directorio que contiene las consultas guardadas.
        
    Returns:
        List[Document]: Lista de documentos de consultas.
    """
    if not os.path.exists(consultas_dir):
        logger.warning(f"El directorio de consultas {consultas_dir} no existe. Se creará uno vacío.")
        os.makedirs(consultas_dir, exist_ok=True)
        return []
    
    # Cargar consultas usando el loader estándar
    consultas = load_documents_from_directory(consultas_dir)
    
    # Añadir metadata específico para consultas
    for consulta in consultas:
        consulta.metadata["tipo"] = "consulta_guardada"
        consulta.metadata["is_consulta"] = True
    
    return consultas
