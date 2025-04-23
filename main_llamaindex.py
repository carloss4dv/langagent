"""
Módulo principal para la configuración y ejecución del agente con LlamaIndex.

Este script configura y ejecuta el agente de respuesta a preguntas
utilizando LangGraph, LlamaIndex, y diversos tipos de vectorstores.
"""

import os
import re
import sys
import json
import logging
import argparse
from typing import Dict, List, Any, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Importaciones de langagent para la carga de documentos y creación de modelos
from langagent.utils.document_loader import (
    load_documents_from_directory,
    load_consultas_guardadas
)
from langagent.vectorstore import (
    create_embeddings,
    VectorStoreFactory
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
                use_advanced_rag=False, advanced_techniques=None, consultas_dir=None,
                vector_db_type=None):
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
        vector_db_type (str, optional): Tipo de vectorstore a utilizar ('chroma' o 'milvus').
        
    Returns:
        tuple: Workflow compilado y componentes del agente.
    """
    print_title("Configurando el agente con llama-index")
    
    # Usar valores de configuración si no se proporcionan argumentos
    data_dir = data_dir or PATHS_CONFIG["default_data_dir"]
    persist_directory = persist_directory or PATHS_CONFIG["default_vectorstore_dir"]
    local_llm = local_llm or LLM_CONFIG["default_model"]
    local_llm2 = local_llm2 or LLM_CONFIG.get("default_model2", local_llm)
    consultas_dir = consultas_dir or os.path.join(data_dir, "consultas_guardadas")
    vector_db_type = vector_db_type or VECTORSTORE_CONFIG.get("vector_db_type", "chroma")
    
    # Verificar qué técnicas avanzadas usar
    advanced_techniques = advanced_techniques or []
    if use_advanced_rag and not advanced_techniques:
        # Si se solicita RAG avanzado pero no se especifican técnicas, usar todas
        advanced_techniques = ['dual_chunks', 'document_summary', 'router', 'optimize_embeddings']
    
    # Crear embeddings
    print("Creando embeddings...")
    embeddings = create_embeddings()
    
    # Obtener la instancia de vectorstore adecuada
    vectorstore_handler = VectorStoreFactory.get_vectorstore_instance(vector_db_type)
    
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
        
        # Añadir metadatos a los documentos
        for doc in doc_splits:
            doc.metadata["cubo_source"] = cubo_name
            # Intentar identificar el ámbito del cubo
            from langagent.models.constants import CUBO_TO_AMBITO
            if cubo_name in CUBO_TO_AMBITO:
                doc.metadata["ambito"] = CUBO_TO_AMBITO[cubo_name]
        
        # Nombre de la colección para el cubo
        collection_name = f"Cubo{cubo_name}"
        
        try:
            # Intentar cargar una vectorstore existente
            print(f"Intentando cargar vectorstore existente para {cubo_name}...")
            db = vectorstore_handler.load_vectorstore(
                embeddings=embeddings,
                collection_name=collection_name,
                persist_directory=os.path.join(persist_directory, collection_name)
            )
            print(f"Vectorstore existente cargada para {cubo_name}")
        except Exception as e:
            # Si no existe, crear una nueva
            print(f"Creando nueva vectorstore para {cubo_name}: {str(e)}")
            db = vectorstore_handler.create_vectorstore(
                documents=doc_splits,
                embeddings=embeddings,
                collection_name=collection_name,
                persist_directory=os.path.join(persist_directory, collection_name)
            )
            print(f"Nueva vectorstore creada para {cubo_name}")
        
        # Guardar la vectorstore básica
        vectorstores[cubo_name] = db
        
        # Implementar técnicas avanzadas de RAG según lo solicitado
        if 'dual_chunks' in advanced_techniques:
            print(f"Creando dual retriever para {cubo_name}...")
            retrievers[cubo_name] = create_dual_retriever(
                documents=doc_splits,
                embeddings=embeddings,
                persist_directory=os.path.join(persist_directory, f"{collection_name}_dual")
            )
        elif 'document_summary' in advanced_techniques:
            print(f"Creando document summary retriever para {cubo_name}...")
            retrievers[cubo_name] = create_document_summary_retriever(
                documents=doc_splits,
                embeddings=embeddings,
                persist_directory=os.path.join(persist_directory, f"{collection_name}_summary"),
                llm=llm2 if llm2 else llm
            )
        else:
            # Para un retriever estándar, usamos el vectorstore_handler
            retrievers[cubo_name] = vectorstore_handler.create_retriever(
                vectorstore=db,
                k=VECTORSTORE_CONFIG["k_retrieval"],
                similarity_threshold=VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
            )
    
    # Procesar consultas guardadas por ámbito
    for ambito, consultas in consultas_por_ambito.items():
        print(f"Procesando consultas guardadas para el ámbito: {ambito}")
        
        # Dividir consultas en chunks
        consulta_splits = text_splitter.split_documents(consultas)
        
        # Añadir metadatos sobre el ámbito a los documentos
        for doc in consulta_splits:
            doc.metadata["ambito"] = ambito
            doc.metadata["is_consulta"] = True
            
        # Nombre de la colección para las consultas de este ámbito
        collection_name = f"Consultas_{ambito}"
        
        try:
            # Intentar cargar una vectorstore existente
            print(f"Intentando cargar vectorstore existente para consultas de {ambito}...")
            db = vectorstore_handler.load_vectorstore(
                embeddings=embeddings,
                collection_name=collection_name,
                persist_directory=os.path.join(persist_directory, collection_name)
            )
            print(f"Vectorstore existente cargada para consultas de {ambito}")
        except Exception as e:
            # Si no existe, crear una nueva
            print(f"Creando nueva vectorstore para consultas de {ambito}: {str(e)}")
            db = vectorstore_handler.create_vectorstore(
                documents=consulta_splits,
                embeddings=embeddings,
                collection_name=collection_name,
                persist_directory=os.path.join(persist_directory, collection_name)
            )
            print(f"Nueva vectorstore creada para consultas de {ambito}")
        
        # Guardar la vectorstore de consultas
        consultas_vectorstores[ambito] = db
        
        # Crear retriever para las consultas de este ámbito
        retriever_key = f"consultas_{ambito}"
        retrievers[retriever_key] = vectorstore_handler.create_retriever(
            vectorstore=db,
            k=VECTORSTORE_CONFIG["k_retrieval"],
            similarity_threshold=VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
        )
    
    # Añadir un router retriever si está habilitado
    if 'router' in advanced_techniques and len(vectorstores) > 1:
        print("Creando router retriever para enrutar entre diferentes cubos...")
        router_retriever = create_router_retriever(
            vectorstores=vectorstores,
            llm=llm2 if llm2 else llm
        )
        # El router retriever se puede añadir como un retriever adicional
        retrievers['router'] = router_retriever
    
    # Optimizar embeddings si está habilitado
    if 'optimize_embeddings' in advanced_techniques:
        print("Optimizando embeddings...")
        optimize_embeddings(
            retrievers=retrievers,
            llm=llm2 if llm2 else llm
        )
    
    # Crear cadenas para rag y evaluación
    rag_chain = create_rag_chain(llm)
    retrieval_grader = create_retrieval_grader(llm2 if llm2 else llm)
    hallucination_grader = create_hallucination_grader(llm2 if llm2 else llm)
    answer_grader = create_answer_grader(llm2 if llm2 else llm)
    
    # Crear un router de preguntas que determine qué cubo usar
    question_router = create_question_router(llm2 if llm2 else llm)
    
    # Crear workflow con los retrievers configurados
    workflow = create_workflow(
        retrievers=retrievers, 
        rag_chain=rag_chain, 
        retrieval_grader=retrieval_grader, 
        hallucination_grader=hallucination_grader, 
        answer_grader=answer_grader,
        question_router=question_router
    )
    
    # Compilar workflow 
    app = workflow.compile()
    
    # Devolver el app junto con los componentes por si se necesitan en otros lugares
    components = {
        "embeddings": embeddings,
        "retrievers": retrievers,
        "vectorstores": vectorstores,
        "consultas_vectorstores": consultas_vectorstores,
        "llm": llm,
        "llm2": llm2,
        "rag_chain": rag_chain,
        "workflow": workflow,
        "question_router": question_router
    }
    
    return app, components

def run_agent(app, question):
    """
    Ejecuta el agente con una consulta del usuario.
    
    Args:
        app: Aplicación compilada.
        question (str): Consulta del usuario.
        
    Returns:
        Dict: Resultado de la ejecución del agente.
    """
    print_title(f"Consulta: {question}")
    
    # Ejecutar el workflow
    result = app.invoke({"question": question})
    
    # Mostrar documentos recuperados
    if "documents" in result:
        print_documents(result["documents"])
    
    # Mostrar resultados
    print_workflow_result(result)
    
    # Mostrar pasos del workflow si están disponibles
    if "workflow_trace" in result:
        print_workflow_steps(result["workflow_trace"])
    
    return result

def main():
    """Función principal para ejecutar el agente desde línea de comandos."""
    parser = argparse.ArgumentParser(description="Agente de respuesta a preguntas con LlamaIndex")
    parser.add_argument("--data_dir", default=None, help="Directorio con documentos markdown")
    parser.add_argument("--vectorstore_dir", default=None, help="Directorio para la base de datos vectorial")
    parser.add_argument("--vector_db_type", default=None, choices=["chroma", "milvus"], help="Tipo de base de datos vectorial")
    parser.add_argument("--local_llm", default=None, help="Modelo LLM principal")
    parser.add_argument("--local_llm2", default=None, help="Modelo LLM secundario")
    parser.add_argument("--question", help="Pregunta a responder")
    parser.add_argument("--advanced_rag", action="store_true", help="Usar técnicas avanzadas de RAG")
    parser.add_argument("--techniques", default=None, help="Lista de técnicas avanzadas separadas por comas")
    
    args = parser.parse_args()
    
    # Convertir la cadena de técnicas a una lista
    techniques = args.techniques.split(",") if args.techniques else None
    
    # Configurar el agente
    app, _ = setup_agent(
        data_dir=args.data_dir, 
        persist_directory=args.vectorstore_dir,
        local_llm=args.local_llm, 
        local_llm2=args.local_llm2,
        use_advanced_rag=args.advanced_rag,
        advanced_techniques=techniques,
        vector_db_type=args.vector_db_type
    )
    
    # Ejecutar el agente con la pregunta proporcionada o una de ejemplo
    question = args.question if args.question else "¿Cuál es la tasa de abandono en los grados de ingeniería?"
    print(f"Ejecutando consulta: {question}")
    result = run_agent(app, question)
    
    return result

if __name__ == "__main__":
    main()
