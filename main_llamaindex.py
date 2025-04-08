"""
Módulo principal para la integración de llama-index con langagent.

Este módulo proporciona la configuración y ejecución del agente con capacidades
de RAG avanzado utilizando llama-index.
"""

from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import IndexNode
from llama_index.core.retrievers import RecursiveRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.indices.document_summary import DocumentSummaryIndex
import logging

logger = logging.getLogger(__name__)

import re
import os
import argparse
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langagent.utils.document_loader import load_documents_from_directory
from langagent.utils.vectorstore import (
    create_embeddings, 
    create_vectorstore, 
    load_vectorstore, 
    create_retriever
)
from langagent.utils.llamaindex_integration import (
    create_dual_retriever,
    create_document_summary_retriever,
    create_router_retriever,
    optimize_embeddings
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

def configure_llamaindex_settings(embeddings, llm, chunk_size=512, chunk_overlap=20):
    """
    Configura los ajustes globales de LlamaIndex.
    
    Args:
        embeddings: Modelo de embeddings a utilizar
        llm: Modelo de lenguaje a utilizar
        chunk_size (int): Tamaño de chunks para el parser
        chunk_overlap (int): Solapamiento entre chunks
    """
    # Adaptar embeddings de LangChain a llama-index si es necesario
    from llama_index.embeddings.langchain import LangchainEmbedding
    llama_embeddings = (
        embeddings if hasattr(embeddings, "get_text_embedding") 
        else LangchainEmbedding(embeddings)
    )
    
    # Adaptar LLM de LangChain a llama-index si es necesario
    from llama_index.llms.langchain import LangChainLLM
    llama_llm = (
        llm if hasattr(llm, "complete") 
        else LangChainLLM(llm=llm)
    )
    
    # Configurar Settings globales
    Settings.embed_model = llama_embeddings
    Settings.llm = llama_llm
    Settings.node_parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    Settings.num_output = 512
    Settings.context_window = 3900
    
    logger.info("Configuración global de LlamaIndex completada")

def setup_agent(documents: List[Document], embeddings, llm, persist_directory: str):
    """
    Configura el agente con los componentes necesarios para RAG avanzado.
    
    Args:
        documents (List[Document]): Lista de documentos a indexar
        embeddings: Modelo de embeddings a utilizar
        llm: Modelo de lenguaje a utilizar
        persist_directory (str): Directorio donde persistir la base de datos
        
    Returns:
        agent: Agente configurado con capacidades de RAG avanzado
    """
    try:
        # Configurar Settings globales de LlamaIndex
        configure_llamaindex_settings(embeddings, llm)
        
        # Crear retrievers
        from utils.llamaindex_integration import (
            create_dual_retriever,
            create_document_summary_retriever,
            create_router_retriever
        )
        
        # Crear retriever dual
        dual_retriever = create_dual_retriever(
            documents=documents,
            embeddings=embeddings,
            persist_directory=persist_directory
        )
        
        # Crear retriever de resumen de documentos
        summary_retriever = create_document_summary_retriever(
            documents=documents,
            embeddings=embeddings,
            llm=llm,
            persist_directory=persist_directory
        )
        
        # Crear retriever router
        router_retriever = create_router_retriever(
            retrievers=[dual_retriever, summary_retriever],
            llm=llm
        )
        
        # Crear query engine
        from llama_index.core.query_engine import RetrieverQueryEngine
        query_engine = RetrieverQueryEngine(
            retriever=router_retriever,
            response_synthesizer=llm
        )
        
        # Adaptar el query engine a la interfaz de LangChain
        from langchain_core.retrievers import BaseRetriever
        
        class QueryEngineAdapter(BaseRetriever):
            def __init__(self, query_engine):
                super().__init__()
                self.query_engine = query_engine
                
            def _get_relevant_documents(self, query: str):
                # Obtener respuesta del query engine
                response = self.query_engine.query(query)
                
                # Convertir respuesta a documentos de LangChain
                docs = []
                for node in response.source_nodes:
                    doc = Document(
                        page_content=node.get_content(),
                        metadata=node.metadata
                    )
                    docs.append(doc)
                return docs
        
        # Devolver el agente adaptado
        return QueryEngineAdapter(query_engine)
        
    except Exception as e:
        logger.error(f"Error al configurar el agente: {str(e)}")
        raise

def run_agent(app, question):
    """
    Ejecuta el agente con una pregunta.
    
    Args:
        app: Workflow compilado.
        question (str): Pregunta a responder.
        
    Returns:
        dict: Resultado final del workflow.
    """
    print_title(f"Procesando pregunta: {question}")
    
    # Ejecutar workflow
    inputs = {"question": question}
    state_transitions = []
    
    for output in app.stream(inputs):
        state_transitions.append(output)
        for key, value in output.items():
            print(f"Completado: {key}")
    
    # Imprimir pasos del workflow
    print_workflow_steps(state_transitions)
    
    # Imprimir resultado final
    final_output = state_transitions[-1]
    print_workflow_result(final_output)
    
    return final_output

def main():
    """Función principal para ejecutar el agente desde línea de comandos."""
    parser = argparse.ArgumentParser(description="Agente de respuesta a preguntas con LangGraph y llama-index")
    parser.add_argument("--data_dir", default=None, help="Directorio con documentos markdown")
    parser.add_argument("--chroma_dir", default=None, help="Directorio para la base de datos vectorial")
    parser.add_argument("--local_llm", default=None, help="Modelo LLM principal")
    parser.add_argument("--local_llm2", default=None, help="Modelo LLM secundario (opcional)")
    parser.add_argument("--question", help="Pregunta a responder")
    parser.add_argument("--use_advanced_rag", action="store_true", help="Utilizar técnicas avanzadas de RAG")
    parser.add_argument("--advanced_techniques", nargs="+", 
                        choices=['dual_chunks', 'document_summary', 'router', 'optimize_embeddings'],
                        help="Técnicas avanzadas específicas a utilizar")
    
    args = parser.parse_args()
    
    try:
        # Configurar agente
        app, components = setup_agent(
            args.data_dir, 
            args.chroma_dir, 
            args.local_llm, 
            args.local_llm2,
            args.use_advanced_rag,
            args.advanced_techniques
        )
        
        # Si se proporciona una pregunta, ejecutar el agente
        if args.question:
            run_agent(app, args.question)
        else:
            # Modo interactivo
            print_title("Modo interactivo")
            print("Escribe 'salir' para terminar")
            
            while True:
                try:
                    question = input("\nPregunta: ")
                    if question.lower() in ["salir", "exit", "quit"]:
                        break
                    
                    if not question.strip():
                        print("Por favor, introduce una pregunta válida.")
                        continue
                        
                    run_agent(app, question)
                except KeyboardInterrupt:
                    print("\nOperación interrumpida por el usuario.")
                    break
                except Exception as e:
                    print(f"\nError al procesar la pregunta: {str(e)}")
                    print("Puedes intentar con otra pregunta o escribir 'salir' para terminar.")
    except Exception as e:
        print(f"Error al inicializar el agente: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
