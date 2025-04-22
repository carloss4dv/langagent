"""
Módulo para la visualización en terminal.

Este módulo proporciona funciones para visualizar información en la terminal,
reemplazando las visualizaciones gráficas del notebook original.
"""

import json
from typing import Dict, Any, List
from langchain_core.documents import Document

def print_separator(length: int = 50):
    """
    Imprime una línea separadora en la terminal.
    
    Args:
        length (int): Longitud de la línea separadora.
    """
    print("-" * length)

def print_title(title: str):
    """
    Imprime un título formateado en la terminal.
    
    Args:
        title (str): Título a imprimir.
    """
    print_separator()
    print(f"  {title.upper()}  ")
    print_separator()

def print_documents(documents, title="Documentos Recuperados"):
    """
    Imprime documentos en la terminal.
    
    Args:
        documents (List[Document]): Lista de documentos a imprimir.
        title (str): Título para la sección de documentos.
    """
    if not documents:
        print(f"\n{title}: No hay documentos para mostrar")
        return
    
    print_title(title)
    
    # Limitar a 3 documentos para evitar sobrecargar la terminal
    max_docs = 3
    if len(documents) > max_docs:
        print(f"Mostrando {max_docs} de {len(documents)} documentos:")
        documents = documents[:max_docs]
    
    for i, doc in enumerate(documents):
        print(f"Documento {i+1}:")
        
        # Intentar acceder a metadata de diferentes formas según el tipo de documento
        if hasattr(doc, 'metadata'):
            print(f"Fuente: {doc.metadata.get('source', 'Desconocida')}")
        elif isinstance(doc, dict) and 'metadata' in doc:
            print(f"Fuente: {doc['metadata'].get('source', 'Desconocida')}")
        
        # Extraer el contenido del documento
        if hasattr(doc, 'page_content'):
            content = doc.page_content
        elif isinstance(doc, dict) and 'page_content' in doc:
            content = doc['page_content']
        elif isinstance(doc, dict) and 'text' in doc:
            content = doc['text']
        elif isinstance(doc, str):
            content = doc
        else:
            content = str(doc)
        
        # Mostrar contenido truncado si es muy largo
        print("Contenido:")
        print(content[:500] + "..." if len(content) > 500 else content)
        print_separator(30)

def print_workflow_result(result: Dict[str, Any]):
    """
    Imprime el resultado del flujo de trabajo en la terminal.
    
    Args:
        result (Dict[str, Any]): Resultado del flujo de trabajo.
    """
    print_title("Resultado del Flujo de Trabajo")
    
    # Extraer la generación final
    final_output = list(result.values())[0]
    
    print(f"Pregunta: {final_output.get('question', 'N/A')}")
    print(f"Respuesta: {final_output.get('generation', 'N/A')}")
    print(f"Intentos realizados: {final_output.get('retry_count', 0)}")
    
    if final_output.get('retry_count', 0) >= 3:
        print("Nota: Se alcanzó el máximo de intentos sin una respuesta satisfactoria.")
    
    print_separator()

def print_json(data: Dict[str, Any], title: str = "Datos JSON"):
    """
    Imprime datos JSON formateados en la terminal.
    
    Args:
        data (Dict[str, Any]): Datos JSON a imprimir.
        title (str): Título para los datos.
    """
    print_title(title)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print_separator()

def print_workflow_steps(state_transitions: List[Dict[str, Any]]):
    """
    Imprime los pasos del flujo de trabajo en la terminal.
    
    Args:
        state_transitions (List[Dict[str, Any]]): Lista de transiciones de estado.
    """
    print_title("Pasos del Flujo de Trabajo")
    
    for i, transition in enumerate(state_transitions):
        print(f"Paso {i+1}: {list(transition.keys())[0]}")
    
    print_separator()
