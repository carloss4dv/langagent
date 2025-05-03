"""
Módulo para cargar y procesar documentos desde archivos markdown.

Este módulo proporciona funciones para cargar documentos desde archivos markdown
y procesarlos para su uso en sistemas de recuperación de información.
"""

import os
from typing import Dict, List
from langchain_core.documents import Document
from langchain_community.document_loaders import UnstructuredMarkdownLoader

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
        print(f"Advertencia: {file_path} está vacío o no se pudo cargar.")
        return []
    
    # Añade metadatos a cada documento
    for doc in elements:
        doc.metadata["source"] = file_path
    
    return elements




def load_documents_from_directory(directory_path: str) -> List[Document]:
    """
    Carga todos los archivos markdown de un directorio y los convierte en documentos.
    
    Args:
        directory_path (str): Ruta al directorio que contiene los archivos markdown.
        
    Returns:
        List[Document]: Lista de documentos extraídos de todos los archivos markdown.
    """
    # Obtenemos la lista de archivos en el directorio
    files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f)) and f.endswith('.md')]
    
    # Cargamos cada archivo y acumulamos los documentos
    all_docs = []
    for file in files:
        file_path = os.path.join(directory_path, file)
        docs = load_file(file_path)
        print(f" Loaded file {file} with {len(docs)} documents")
        all_docs.extend(docs)
    
    return all_docs

def load_consultas_guardadas(consultas_dir: str) -> Dict[str, List[Document]]:
    """
    Carga las consultas guardadas organizadas por ámbito.
    
    Args:
        consultas_dir (str): Directorio donde se encuentran las consultas guardadas.
        
    Returns:
        Dict[str, List[Document]]: Diccionario con las consultas organizadas por ámbito.
    """
    consultas_por_ambito = {}
    
    # Verificar si el directorio existe
    if not os.path.exists(consultas_dir):
        print(f"El directorio de consultas {consultas_dir} no existe. Se creará uno vacío.")
        return consultas_por_ambito
    
    # Recorrer cada archivo en el directorio
    for filename in os.listdir(consultas_dir):
        if filename.endswith(".md"):
            # Extraer el ámbito del nombre del archivo
            # Formato esperado: consulta_ambito_nombre.md
            parts = filename.split('_')
            if len(parts) >= 2:
                ambito = parts[1]  # El ámbito es la segunda parte
                
                # Leer el contenido del archivo
                file_path = os.path.join(consultas_dir, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Crear el documento
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": file_path,
                        "ambito": ambito,
                        "tipo": "consulta_guardada"
                    }
                )
                
                # Agregar al diccionario por ámbito
                if ambito not in consultas_por_ambito:
                    consultas_por_ambito[ambito] = []
                consultas_por_ambito[ambito].append(doc)
    
    return consultas_por_ambito
