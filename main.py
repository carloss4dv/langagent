"""
Módulo principal para la configuración y ejecución del agente.

Este script configura y ejecuta el agente de respuesta a preguntas
utilizando LangGraph, LLaMA3 y Chroma vector store.
"""
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

def setup_agent(data_dir=None, chroma_base_dir=None, local_llm=None, local_llm2=None):
    """
    Configura el agente con todos sus componentes, creando una vectorstore separada
    para cada cubo identificado en los documentos.
    
    Args:
        data_dir (str, optional): Directorio con los documentos markdown.
        chroma_base_dir (str, optional): Directorio base para las bases de datos vectoriales.
        local_llm (str, optional): Nombre del modelo LLM principal.
        local_llm2 (str, optional): Nombre del segundo modelo LLM.
        
    Returns:
        tuple: Workflow compilado y componentes del agente.
    """
    print_title("Configurando el agente")
    
    # Usar valores de configuración si no se proporcionan argumentos
    data_dir = data_dir or PATHS_CONFIG["default_data_dir"]
    chroma_base_dir = chroma_base_dir or PATHS_CONFIG["default_chroma_dir"]
    local_llm = local_llm or LLM_CONFIG["default_model"]
    local_llm2 = local_llm2 or LLM_CONFIG["default_model2"]
    
    # Crear embeddings (compartidos por todas las vectorstores)
    print("Creando embeddings...")
    embeddings = create_embeddings()
    
    # Cargar documentos y agruparlos por cubo
    print("Cargando documentos y agrupándolos por cubo...")
    all_documents = load_documents_from_directory(data_dir)
    
    # Dividir documentos en chunks más pequeños
    print("Dividiendo documentos...")
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=VECTORSTORE_CONFIG["chunk_size"], 
        chunk_overlap=VECTORSTORE_CONFIG["chunk_overlap"]
    )
    
    # Diccionario para agrupar los documentos por cubo
    cubo_documents = {}
    
    # Extraer y agrupar por nombre de cubo
    for doc in all_documents:
        # Extraer el nombre del cubo del nombre del archivo o metadatos
        file_path = doc.metadata.get('source', '')
        file_name = os.path.basename(file_path)
        
        # Buscar el patrón info_cubo_X_vY.md y extraer X como nombre del cubo
        match = re.search(r'info_cubo_([^_]+)_v\d+\.md', file_name)
        if match:
            cubo_name = match.group(1)
            if cubo_name not in cubo_documents:
                cubo_documents[cubo_name] = []
            cubo_documents[cubo_name].append(doc)
        else:
            # Si no sigue el patrón, usar un grupo por defecto
            if "general" not in cubo_documents:
                cubo_documents["general"] = []
            cubo_documents["general"].append(doc)
    
    # Diccionarios para guardar los retrievers por cubo
    retrievers = {}
    vectorstores = {}
    
    # Procesar cada cubo y crear su vectorstore
    for cubo_name, docs in cubo_documents.items():
        print(f"Procesando documentos para el cubo: {cubo_name}")
        
        # Dividir documentos en chunks
        doc_splits = text_splitter.split_documents(docs)
        
        # Crear directorio para vectorstore de este cubo
        cubo_chroma_dir = os.path.join(chroma_base_dir, f"Cubo{cubo_name}")
        
        # Crear o cargar vectorstore para este cubo
        if not os.path.exists(cubo_chroma_dir):
            print(f"Creando nueva base de datos vectorial para {cubo_name}...")
            db = create_vectorstore(doc_splits, embeddings, cubo_chroma_dir)
        else:
            print(f"Cargando base de datos vectorial existente para {cubo_name}...")
            db = load_vectorstore(cubo_chroma_dir, embeddings)
        
        # Guardar la vectorstore
        vectorstores[cubo_name] = db
        
        # Crear retriever para este cubo
        retrievers[cubo_name] = create_retriever(db, k=VECTORSTORE_CONFIG["k_retrieval"])
    
    # Crear LLMs
    print("Configurando modelos de lenguaje...")
    llm = create_llm(model_name=local_llm)
    llm2 = create_llm(model_name=local_llm2)
    
    # Crear cadenas
    rag_chain = create_rag_chain(llm)
    retrieval_grader = create_retrieval_grader(llm2)
    hallucination_grader = create_hallucination_grader(llm2)
    answer_grader = create_answer_grader(llm2)
    
    # Crear un router de preguntas que determine qué cubo usar
    question_router = create_question_router(llm)
    
    # Modificar create_workflow para manejar múltiples retrievers
    print("Creando flujo de trabajo con múltiples vectorstores...")
    workflow = create_workflow(
        retrievers, 
        rag_chain, 
        retrieval_grader, 
        hallucination_grader, 
        answer_grader, 
        question_router
    )
    
    # Compilar workflow
    app = workflow.compile()
    
    return app, {
        "retrievers": retrievers,
        "vectorstores": vectorstores,
        "rag_chain": rag_chain,
        "retrieval_grader": retrieval_grader,
        "hallucination_grader": hallucination_grader,
        "answer_grader": answer_grader,
        "question_router": question_router
    }

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
    parser = argparse.ArgumentParser(description="Agente de respuesta a preguntas con LangGraph")
    parser.add_argument("--data_dir", default=None, help="Directorio con documentos markdown")
    parser.add_argument("--chroma_dir", default=None, help="Directorio para la base de datos vectorial")
    parser.add_argument("--local_llm", default=None, help="Modelo LLM principal")
    parser.add_argument("--local_llm2", default=None, help="Modelo LLM secundario (opcional)")
    parser.add_argument("--question", help="Pregunta a responder")
    
    args = parser.parse_args()
    
    # Configurar agente
    app, components = setup_agent(
        args.data_dir, 
        args.chroma_dir, 
        args.local_llm, 
        args.local_llm2
    )
    
    # Si se proporciona una pregunta, ejecutar el agente
    if args.question:
        run_agent(app, args.question)
    else:
        # Modo interactivo
        print_title("Modo interactivo")
        print("Escribe 'salir' para terminar")
        
        while True:
            question = input("\nPregunta: ")
            if question.lower() in ["salir", "exit", "quit"]:
                break
            
            run_agent(app, question)

if __name__ == "__main__":
    main()
