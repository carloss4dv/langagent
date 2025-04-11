"""
Módulo principal para la integración de llama-index con langagent.
Este módulo proporciona la configuración y ejecución del agente con capacidades
de RAG avanzado utilizando llama-index.
"""
import re
import os
import argparse
import logging
from typing import List, Dict, Any, Optional

# Importaciones estándar
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Importaciones de langagent para la carga de documentos y creación de modelos
from langagent.utils.document_loader import (
    load_documents_from_directory,
    load_consultas_guardadas
)
from langagent.utils.vectorstore import (
    create_embeddings,
    create_vectorstore, 
    load_vectorstore
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

# Importar todas las funciones de integración con llama-index desde el nuevo módulo
from langagent.utils.llamaindex_integration import (
    configure_llamaindex_settings,
    create_dual_retriever,
    create_document_summary_retriever,
    create_router_retriever,
    optimize_embeddings
)

from langagent.config.config import (
    LLM_CONFIG,
    VECTORSTORE_CONFIG,
    PATHS_CONFIG
)

# Configurar logging
logger = logging.getLogger(__name__)

def setup_agent(data_dir=None, persist_directory=None, local_llm=None, local_llm2=None, 
                use_advanced_rag=False, advanced_techniques=None, consultas_dir=None):
    """
    Configura el agente con todos sus componentes para RAG avanzado.
    
    Args:
        data_dir (str, optional): Directorio con los documentos.
        persist_directory (str, optional): Directorio para las bases de datos vectoriales.
        local_llm (str, optional): Nombre del modelo LLM principal.
        local_llm2 (str, optional): Nombre del segundo modelo LLM.
        use_advanced_rag (bool): Si se deben usar técnicas avanzadas de RAG
        advanced_techniques (list): Lista de técnicas avanzadas específicas a utilizar
        consultas_dir (str, optional): Directorio con las consultas guardadas.
        
    Returns:
        tuple: Workflow compilado y componentes del agente.
    """
    print_title("Configurando el agente con llama-index")
    
    # Usar valores de configuración si no se proporcionan argumentos
    data_dir = data_dir or PATHS_CONFIG["default_data_dir"]
    persist_directory = persist_directory or PATHS_CONFIG["default_chroma_dir"]
    local_llm = local_llm or LLM_CONFIG["default_model"]
    local_llm2 = local_llm2 or LLM_CONFIG.get("default_model2", local_llm)
    consultas_dir = consultas_dir or os.path.join(os.path.dirname(data_dir), "consultas_guardadas")
    
    # Verificar qué técnicas avanzadas usar
    advanced_techniques = advanced_techniques or []
    if use_advanced_rag and not advanced_techniques:
        # Si se solicita RAG avanzado pero no se especifican técnicas, usar todas
        advanced_techniques = ['dual_chunks', 'document_summary', 'router', 'optimize_embeddings']
    
    # Crear embeddings
    print("Creando embeddings...")
    embeddings = create_embeddings()
    
    # Cargar documentos
    print("Cargando documentos...")
    all_documents = load_documents_from_directory(data_dir)
    
    # Cargar consultas guardadas
    print("Cargando consultas guardadas...")
    consultas_por_ambito = load_consultas_guardadas(consultas_dir)
    
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
    
    # Crear LLMs
    print("Configurando modelos de lenguaje...")
    llm = create_llm(model_name=local_llm)
    llm2 = create_llm(model_name=local_llm2) if local_llm2 else None
    
    # Configurar settings globales de LlamaIndex utilizando la función del módulo de integración
    llama_embeddings, llama_llm_principal, llama_llm_evaluador = configure_llamaindex_settings(
        embeddings=embeddings, 
        llm_principal=llm, 
        llm_evaluador=llm2,
        chunk_size=VECTORSTORE_CONFIG["chunk_size"],
        chunk_overlap=VECTORSTORE_CONFIG["chunk_overlap"]
    )
    
    # Diccionarios para guardar los retrievers por cubo
    retrievers = {}
    vectorstores = {}
    
    # Vectorstores para consultas guardadas por ámbito
    consultas_vectorstores = {}
    
    # Procesar cada cubo y crear su vectorstore/retrievers
    for cubo_name, docs in cubo_documents.items():
        print(f"Procesando documentos para el cubo: {cubo_name}")
        
        # Dividir documentos en chunks
        doc_splits = text_splitter.split_documents(docs)
        
        # Crear directorio para vectorstore de este cubo
        cubo_persist_dir = os.path.join(persist_directory, f"Cubo{cubo_name}")
        
        # Crear o cargar vectorstore básica para este cubo
        if not os.path.exists(cubo_persist_dir):
            print(f"Creando nueva base de datos vectorial para {cubo_name}...")
            db = create_vectorstore(doc_splits, embeddings, cubo_persist_dir)
        else:
            print(f"Cargando base de datos vectorial existente para {cubo_name}...")
            db = load_vectorstore(cubo_persist_dir, embeddings)
        
        # Guardar la vectorstore básica
        vectorstores[cubo_name] = db
        
        # Implementar técnicas avanzadas de RAG según lo solicitado
        if 'dual_chunks' in advanced_techniques:
            print(f"Creando dual retriever para {cubo_name}...")
            retrievers[cubo_name] = create_dual_retriever(
                documents=doc_splits,
                embeddings=embeddings,
                persist_directory=os.path.join(cubo_persist_dir, "dual")
            )
        elif 'document_summary' in advanced_techniques:
            print(f"Creando document summary retriever para {cubo_name}...")
            retrievers[cubo_name] = create_document_summary_retriever(
                documents=doc_splits,
                embeddings=embeddings,
                persist_directory=os.path.join(cubo_persist_dir, "summary"),
                llm=llm2 if llm2 else llm
            )
        else:
            # Para un retriever estándar, usamos create_retriever de vectorstore.py
            from langagent.utils.vectorstore import create_retriever
            retrievers[cubo_name] = create_retriever(db, k=VECTORSTORE_CONFIG["k_retrieval"])
    
    # Procesar consultas guardadas por ámbito
    for ambito, consultas in consultas_por_ambito.items():
        print(f"Procesando consultas guardadas para el ámbito: {ambito}")
        
        # Dividir consultas en chunks
        consulta_splits = text_splitter.split_documents(consultas)
        
        # Crear directorio para vectorstore de consultas de este ámbito
        consultas_persist_dir = os.path.join(persist_directory, f"Consultas_{ambito}")
        
        # Crear o cargar vectorstore para las consultas de este ámbito
        if not os.path.exists(consultas_persist_dir):
            print(f"Creando nueva base de datos vectorial para consultas de {ambito}...")
            db = create_vectorstore(consulta_splits, embeddings, consultas_persist_dir)
        else:
            print(f"Cargando base de datos vectorial existente para consultas de {ambito}...")
            db = load_vectorstore(consultas_persist_dir, embeddings)
        
        # Guardar la vectorstore de consultas
        consultas_vectorstores[ambito] = db
        
        # Crear retriever para las consultas de este ámbito
        retriever_key = f"consultas_{ambito}"
        
        # Aplicar técnicas avanzadas si están habilitadas
        if 'dual_chunks' in advanced_techniques:
            print(f"Creando dual retriever para consultas de {ambito}...")
            retrievers[retriever_key] = create_dual_retriever(
                documents=consulta_splits,
                embeddings=embeddings,
                persist_directory=os.path.join(consultas_persist_dir, "dual")
            )
        elif 'document_summary' in advanced_techniques:
            print(f"Creando document summary retriever para consultas de {ambito}...")
            retrievers[retriever_key] = create_document_summary_retriever(
                documents=consulta_splits,
                embeddings=embeddings,
                persist_directory=os.path.join(consultas_persist_dir, "summary"),
                llm=llm2 if llm2 else llm
            )
        else:
            # Retriever estándar para consultas
            retrievers[retriever_key] = create_retriever(db, k=VECTORSTORE_CONFIG["k_retrieval"])
    
    # Si se solicita la técnica de router, combinar los retrievers
    if 'router' in advanced_techniques and len(retrievers) > 1:
        print("Creando router retriever...")
        combined_retriever = create_router_retriever(
            retrievers=retrievers,  # Ahora le pasamos el diccionario completo
            llm=llm2 if llm2 else llm
        )
        # Reemplazar retrievers individuales con el combinado
        retrievers = {"combined": combined_retriever}
    
    # Optimizar embeddings si se solicita
    if 'optimize_embeddings' in advanced_techniques:
        print("Optimizando embeddings...")
        optimized_embeddings = optimize_embeddings(embeddings, 
                                               documents=all_documents,
                                               persist_directory=persist_directory)
        # No necesitamos actualizar las vectorstores porque optimize_embeddings
        # devuelve el modelo de embeddings optimizado, no las vectorstores
    
    # Crear cadenas
    rag_chain = create_rag_chain(llm)
    retrieval_grader = create_retrieval_grader(llm2 if llm2 else llm)
    hallucination_grader = create_hallucination_grader(llm2 if llm2 else llm)
    answer_grader = create_answer_grader(llm2 if llm2 else llm)
    
    # Crear un router de preguntas si hay múltiples cubos
    question_router = None
    if len(retrievers) > 1:
        question_router = create_question_router(llm2 if llm2 else llm)
    
    # Crear workflow
    print("Creando flujo de trabajo...")
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
    
    # Devolver aplicación compilada y componentes
    return app, {
        "retrievers": retrievers,
        "vectorstores": vectorstores,
        "consultas_vectorstores": consultas_vectorstores,
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
            data_dir=args.data_dir, 
            persist_directory=args.chroma_dir, 
            local_llm=args.local_llm, 
            local_llm2=args.local_llm2,
            use_advanced_rag=args.use_advanced_rag,
            advanced_techniques=args.advanced_techniques
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
