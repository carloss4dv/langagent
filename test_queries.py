"""
Script para ejecutar una batería de pruebas de consultas al agente.
"""

import sys
import os

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.document_loader import load_documents_from_directory
from utils.vectorstore import (
    create_embeddings, 
    create_vectorstore, 
    load_vectorstore, 
    create_retriever
)
from models.llm import (
    create_llm, 
    create_rag_chain, 
    create_retrieval_grader, 
    create_hallucination_grader, 
    create_answer_grader, 
    create_question_router
)
from models.workflow import create_workflow
from utils.terminal_visualization import (
    print_title, 
    print_documents, 
    print_workflow_result, 
    print_workflow_steps
)
from config.config import (
    LLM_CONFIG,
    VECTORSTORE_CONFIG,
    PATHS_CONFIG
)

# Batería de pruebas organizadas por ámbito
TEST_QUERIES = {
    "ACADÉMICO": [
        "¿Cuál es la tasa de graduación de los estudiantes de ingeniería en los últimos 3 años?",
        "¿Cuántos estudiantes se matricularon en el grado de Medicina en el curso 2022-2023?"
    ],
    "ADMISIÓN": [
        "¿Cuál fue la nota de corte para el grado de Derecho en la última convocatoria?"
    ],
    "DOCENCIA": [
        "¿Cuál es la carga docente media de los profesores titulares en el departamento de Matemáticas?"
    ],
    "I+D+i": [
        "¿Cuántos proyectos de investigación europeos están actualmente activos en la universidad?",
        "¿Cuál es el índice h promedio de los investigadores principales en los grupos de investigación?"
    ],
    "MOVILIDAD": [
        "¿Cuántos estudiantes Erasmus incoming recibió la universidad en el último año académico?"
    ],
    "RRHH": [
        "¿Cuál es la distribución por categorías del Personal de Administración y Servicios (PTGAS)?",
        "¿Cuántos profesores asociados hay en la Facultad de Ciencias?"
    ],
    "DOCTORADO": [
        "¿Cuál es el tiempo medio de finalización de tesis doctorales en los programas RD 99/2011?"
    ]
}

def setup_agent(data_dir=None, chroma_base_dir=None, local_llm=None, local_llm2=None):
    """
    Configura el agente con todos sus componentes.
    """
    print_title("Configurando el agente")
    
    # Usar valores de configuración si no se proporcionan argumentos
    data_dir = data_dir or PATHS_CONFIG["default_data_dir"]
    chroma_base_dir = chroma_base_dir or PATHS_CONFIG["default_chroma_dir"]
    local_llm = local_llm or LLM_CONFIG["default_model"]
    local_llm2 = local_llm2 or LLM_CONFIG["default_model2"]
    
    # Crear embeddings
    print("Creando embeddings...")
    embeddings = create_embeddings()
    
    # Cargar documentos
    print("Cargando documentos...")
    documents = load_documents_from_directory(data_dir)
    
    # Crear o cargar vectorstore
    if not os.path.exists(chroma_base_dir):
        print("Creando nueva base de datos vectorial...")
        db = create_vectorstore(documents, embeddings, chroma_base_dir)
    else:
        print("Cargando base de datos vectorial existente...")
        db = load_vectorstore(chroma_base_dir, embeddings)
    
    # Crear retriever
    retriever = create_retriever(db)
    
    # Crear LLMs y cadenas
    llm = create_llm(model_name=local_llm)
    llm2 = create_llm(model_name=local_llm2)
    
    rag_chain = create_rag_chain(llm)
    retrieval_grader = create_retrieval_grader(llm2)
    hallucination_grader = create_hallucination_grader(llm2)
    answer_grader = create_answer_grader(llm2)
    question_router = create_question_router(llm)
    
    # Crear y compilar workflow
    workflow = create_workflow(
        retriever,
        rag_chain,
        retrieval_grader,
        hallucination_grader,
        answer_grader,
        question_router
    )
    
    app = workflow.compile()
    
    return app, {
        "retriever": retriever,
        "vectorstore": db,
        "rag_chain": rag_chain,
        "retrieval_grader": retrieval_grader,
        "hallucination_grader": hallucination_grader,
        "answer_grader": answer_grader,
        "question_router": question_router
    }

def run_agent(app, question):
    """
    Ejecuta el agente con una pregunta.
    """
    print_title(f"Procesando pregunta: {question}")
    
    # Ejecutar workflow
    inputs = {"question": question}
    state_transitions = []
    
    for output in app.stream(inputs):
        state_transitions.append(output)
        for key, value in output.items():
            print(f"Completado: {key}")
    
    # Imprimir pasos y resultado
    print_workflow_steps(state_transitions)
    final_output = state_transitions[-1]
    print_workflow_result(final_output)
    
    return final_output

def run_test_queries():
    """
    Ejecuta todas las consultas de prueba y muestra los resultados.
    """
    print("\n=== Iniciando pruebas del agente ===\n")
    
    # Configurar el agente una sola vez para todas las pruebas
    app, components = setup_agent()
    
    # Ejecutar cada consulta de prueba
    for ambito, queries in TEST_QUERIES.items():
        print(f"\n=== Probando consultas del ámbito: {ambito} ===\n")
        
        for query in queries:
            print(f"\nPregunta: {query}")
            print("-" * 80)
            
            try:
                result = run_agent(app, query)
                print("\nResultado obtenido correctamente")
                print("-" * 80)
            except Exception as e:
                print(f"Error al procesar la consulta: {str(e)}")
                print("-" * 80)
        
        print(f"\nFinalizadas pruebas del ámbito: {ambito}")

if __name__ == "__main__":
    run_test_queries() 
