"""
Módulo principal para la configuración y ejecución del agente.

Este script configura y ejecuta el agente de respuesta a preguntas
utilizando LangGraph, LLaMA3 y Chroma vector store.
"""
import re
import os
import sys
import argparse
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Asegurarnos que podemos importar desde el directorio actual
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from langagent.utils.document_loader import (
    load_documents_from_directory,
    load_consultas_guardadas
)
from langagent.vectorstore import (
    VectorStoreFactory,
    create_embeddings
)
from langagent.models.llm import (
    create_llm, 
    create_rag_chain, 
    create_retrieval_grader, 
    create_hallucination_grader, 
    create_answer_grader, 
    create_question_router
)
from langagent.models.workflow import create_workflow
from langagent.utils.terminal_visualization import (
    print_title, 
    print_documents, 
    print_workflow_result, 
    print_workflow_steps
)
from langagent.config.config import (
    LLM_CONFIG,
    VECTORSTORE_CONFIG,
    PATHS_CONFIG
)
from langagent.core.lang_chain_agent import LangChainAgent

def main():
    """Función principal para ejecutar el agente desde línea de comandos."""
    parser = argparse.ArgumentParser(description="Agente de respuesta a preguntas con LangGraph")
    parser.add_argument("--data_dir", default=None, help="Directorio con documentos markdown")
    parser.add_argument("--chroma_dir", default=None, help="Directorio para la base de datos vectorial")
    parser.add_argument("--local_llm", default=None, help="Modelo LLM principal")
    parser.add_argument("--local_llm2", default=None, help="Modelo LLM secundario (opcional)")
    parser.add_argument("--question", help="Pregunta a responder")
    parser.add_argument("--vector_db_type", default="milvus", choices=["chroma", "milvus"],
                       help="Tipo de vectorstore a utilizar (default: milvus)")
    
    args = parser.parse_args()
    
    # Crear una instancia del agente
    agent = LangChainAgent(
        data_dir=args.data_dir, 
        vectorstore_dir=args.chroma_dir, 
        vector_db_type=args.vector_db_type,
        local_llm=args.local_llm, 
        local_llm2=args.local_llm2
    )
    
    # Ejecutar el agente con la pregunta proporcionada o una de ejemplo
    question = args.question if args.question else "¿Cómo se calcula la tasa de éxito académico en el ambito Academico?"
    print(f"Ejecutando consulta: {question}")
    result = agent.run(question)
    
    return result

if __name__ == "__main__":
    main()
