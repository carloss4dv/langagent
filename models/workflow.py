"""
Módulo para el flujo de control del agente utilizando LangGraph.

Este módulo implementa el flujo de control para el agente de respuesta a preguntas
utilizando LangGraph, con un mecanismo de reintento para respuestas no exitosas.
Soporta múltiples vectorstores organizados en cubos.
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
import json
import re

from langagent.config.config import WORKFLOW_CONFIG, VECTORSTORE_CONFIG

class GraphState(TypedDict):
    """
    Representa el estado del grafo.

    Attributes:
        question: pregunta del usuario
        generation: generación del LLM
        documents: lista de documentos
        retry_count: contador de reintentos
        relevant_cubos: lista de cubos relevantes para la pregunta
        retrieval_details: detalles de recuperación por cubo
    """
    question: str
    generation: str
    documents: List[Document]
    retry_count: int
    hallucination_score: Optional[str]
    answer_score: Optional[str]
    relevant_cubos: List[str]
    retrieval_details: Dict[str, Dict[str, Any]]

def find_relevant_cubos_by_keywords(query, available_cubos):
    """
    Encuentra cubos relevantes basados en palabras clave en la consulta.
    
    Args:
        query (str): La consulta del usuario
        available_cubos (list): Lista de cubos disponibles
        
    Returns:
        list: Lista de cubos relevantes basados en keywords
    """
    # Mapeo de palabras clave a cubos con pesos de relevancia
    keyword_to_cubo = {
        # Acuerdos bilaterales
        "acuerdo bilateral": ("acuerdos_bilaterales", 1.0),
        "convenio": ("acuerdos_bilaterales", 0.9),
        "acuerdo internacional": ("acuerdos_bilaterales", 0.8),
        "colaboración": ("acuerdos_bilaterales", 0.7),
        "partnership": ("acuerdos_bilaterales", 0.7),
        
        # Admisión
        "admisión": ("admision", 1.0),
        "acceso": ("admision", 0.9),
        "entrada": ("admision", 0.8),
        "nuevo ingreso": ("admision", 0.9),
        "requisitos de admisión": ("admision", 1.0),
        "proceso de admisión": ("admision", 1.0),
        
        # Cargo
        "cargo": ("cargo", 1.0),
        "puesto administrativo": ("cargo", 0.9),
        "posición": ("cargo", 0.8),
        "responsabilidad": ("cargo", 0.7),
        
        # Docencia asignatura
        "asignatura": ("docenciaAsignatura", 1.0),
        "materia": ("docenciaAsignatura", 0.9),
        "curso": ("docenciaAsignatura", 0.8),
        "programa académico": ("docenciaAsignatura", 0.9),
        "plan de estudios": ("docenciaAsignatura", 0.8),
        
        # Docencia PDI
        "docencia": ("docenciaPDI", 1.0),
        "profesor": ("docenciaPDI", 0.9),
        "PDI": ("docenciaPDI", 1.0),
        "facultad": ("docenciaPDI", 0.8),
        "profesorado": ("docenciaPDI", 0.9),
        
        # Egresados
        "egresado": ("egresados", 1.0),
        "graduado": ("egresados", 0.9),
        "alumni": ("egresados", 0.8),
        "titulado": ("egresados", 0.9),
        "exalumno": ("egresados", 0.8),
        
        # Estudiantes IN
        "estudiante extranjero": ("estudiantesIN", 1.0),
        "estudiante internacional": ("estudiantesIN", 0.9),
        "incoming": ("estudiantesIN", 0.8),
        "exchange": ("estudiantesIN", 0.8),
        "estudiante foráneo": ("estudiantesIN", 0.9),
        
        # Estudiantes OUT
        "movilidad saliente": ("estudiantesOUT", 1.0),
        "estudiante en el extranjero": ("estudiantesOUT", 0.9),
        "outgoing": ("estudiantesOUT", 0.8),
        "estudiante fuera": ("estudiantesOUT", 0.8),
        "movilidad internacional": ("estudiantesOUT", 0.9),
        
        # Grupos
        "grupo": ("grupos", 1.0),
        "grupo de investigación": ("grupos", 0.9),
        "equipo de investigación": ("grupos", 0.9),
        "investigación": ("grupos", 0.8),
        "línea de investigación": ("grupos", 0.9),
        
        # Índices bibliométricos
        "bibliométrico": ("indicesBibliometricos", 1.0),
        "publicación": ("indicesBibliometricos", 0.9),
        "índice de impacto": ("indicesBibliometricos", 0.9),
        "citas": ("indicesBibliometricos", 0.8),
        "H-index": ("indicesBibliometricos", 0.9),
        
        # Matrícula
        "matrícula": ("matricula", 1.0),
        "inscripción": ("matricula", 0.9),
        "registro": ("matricula", 0.8),
        "enrollment": ("matricula", 0.8),
        "registro académico": ("matricula", 0.9),
        
        # Rendimiento
        "rendimiento": ("rendimiento", 1.0),
        "resultados académicos": ("rendimiento", 0.9),
        "calificación": ("rendimiento", 0.8),
        "nota": ("rendimiento", 0.8),
        "promedio": ("rendimiento", 0.8),
        "aprobado": ("rendimiento", 0.7),
        "reprobado": ("rendimiento", 0.7)
    }
    
    # Diccionario para almacenar puntuaciones por cubo
    cubo_scores = {}
    
    # Convertir la consulta a minúsculas para comparar keywords
    query_lower = query.lower()
    
    # Buscar keywords en la consulta y acumular puntuaciones
    for keyword, (cubo, score) in keyword_to_cubo.items():
        if keyword.lower() in query_lower and cubo in available_cubos:
            if cubo not in cubo_scores:
                cubo_scores[cubo] = 0
            cubo_scores[cubo] += score
    
    # Ordenar cubos por puntuación
    sorted_cubos = sorted(cubo_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Seleccionar cubos con puntuación significativa (umbral de 0.5)
    relevant_cubos = [cubo for cubo, score in sorted_cubos if score >= 0.5]
    
    # Si no hay cubos relevantes, usar todos los disponibles
    if not relevant_cubos:
        relevant_cubos = list(available_cubos)
    
    return relevant_cubos

def create_workflow(retrievers, rag_chain, retrieval_grader, hallucination_grader, answer_grader, question_router):
    """
    Crea un flujo de trabajo para el agente utilizando LangGraph.
    Soporta múltiples vectorstores organizados en cubos.
    
    Args:
        retrievers(dict): Diccionario de retrievers por cubo.
        rag_chain: Cadena de RAG.
        retrieval_grader: Evaluador de relevancia de documentos.
        hallucination_grader: Evaluador de alucinaciones.
        answer_grader: Evaluador de utilidad de respuestas.
        question_router: Router de preguntas para determinar cubos relevantes.
        
    Returns:
        StateGraph: Grafo de estado configurado.
    """
    # Definimos el grafo de estado
    workflow = StateGraph(GraphState)
    
    # Nodos
    
    def route_question(state):
        """
        Determina qué cubos son relevantes para la pregunta.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con cubos relevantes identificados.
        """
        print("---ROUTE QUESTION---")
        question = state["question"]
        print(question)
        
        try:
            # Invocar el router y parsear el resultado
            routing_result = question_router.invoke({"question": question})
            
            # El router puede devolver un diccionario directamente o una cadena JSON
            if isinstance(routing_result, dict):
                cubo_name = routing_result.get("cubo", "")
                datasource = routing_result.get("datasource", "")
            elif isinstance(routing_result, str):
                try:
                    # Intentar parsear como JSON si es una cadena
                    parsed = json.loads(routing_result)
                    cubo_name = parsed.get("cubo", "")
                    datasource = parsed.get("datasource", "")
                except json.JSONDecodeError:
                    # Si no es JSON válido, buscar el nombre del cubo en el texto
                    match = re.search(r'"cubo"\s*:\s*"([^"]+)"', routing_result)
                    cubo_name = match.group(1) if match else ""
                    match = re.search(r'"datasource"\s*:\s*"([^"]+)"', routing_result)
                    datasource = match.group(1) if match else ""
            else:
                cubo_name = ""
                datasource = ""
                
            print(f"Router ha identificado el cubo: {cubo_name}")
            
            # Verificar si el cubo existe
            if cubo_name and cubo_name in retrievers:
                state["relevant_cubos"] = [cubo_name]
                print(f"Usando cubo específico: {cubo_name}")
            else:
                # Si el cubo no existe o no se identificó, usar cubos relevantes basados en keywords
                print(f"Cubo '{cubo_name}' no encontrado o no especificado. Buscando cubos relevantes por palabras clave.")
                relevant_cubos = find_relevant_cubos_by_keywords(question, list(retrievers.keys()))
                
                if relevant_cubos:
                    state["relevant_cubos"] = relevant_cubos
                    print(f"Cubos relevantes por keywords: {relevant_cubos}")
                else:
                    # Si no se encontraron cubos relevantes, usar todos
                    state["relevant_cubos"] = list(retrievers.keys())
                    print("Usando todos los cubos disponibles")
                    
        except Exception as e:
            print(f"Error en route_question: {e}")
            # En caso de error, usar todos los cubos
            state["relevant_cubos"] = list(retrievers.keys())
            print("Error en router. Usando todos los cubos disponibles")
        
        # Inicializar contador de reintentos
        state["retry_count"] = 0
        state["retrieval_details"] = {}
        
        return state
    
    def retrieve(state):
        """
        Recupera documentos de los vectorstores relevantes.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con los documentos recuperados.
        """
        print("---RETRIEVE---")
        question = state["question"]
        retry_count = state.get("retry_count", 0)
        relevant_cubos = state.get("relevant_cubos", list(retrievers.keys()))
        
        all_docs = []
        retrieval_details = {}
        
        # Para cada cubo relevante, recuperar documentos
        for cubo in relevant_cubos:
            if cubo in retrievers:
                try:
                    print(f"Recuperando documentos del cubo: {cubo}")
                    retriever = retrievers[cubo]
                    docs = retriever.invoke(question)
                    
                    # Añadir metadatos sobre el cubo de origen a cada documento
                    for doc in docs:
                        doc.metadata["cubo_source"] = cubo
                    
                    # Guardar los documentos y detalles para este cubo
                    retrieval_details[cubo] = {
                        "count": len(docs),
                        "first_doc_snippet": docs[0].page_content[:100] + "..." if docs else "No documents retrieved"
                    }
                    
                    all_docs.extend(docs)
                    print(f"Recuperados {len(docs)} documentos del cubo {cubo}")
                    
                except Exception as e:
                    print(f"Error al recuperar documentos del cubo {cubo}: {e}")
                    retrieval_details[cubo] = {
                        "count": 0,
                        "error": str(e)
                    }
        
        # Si no se encontraron documentos, intentar con todos los cubos en caso de reintentos
        if not all_docs and retry_count > 0:
            print("No se encontraron documentos en los cubos iniciales. Probando con todos los cubos...")
            for cubo, retriever in retrievers.items():
                if cubo not in relevant_cubos:
                    try:
                        docs = retriever.invoke(question)
                        for doc in docs:
                            doc.metadata["cubo_source"] = cubo
                        all_docs.extend(docs)
                        print(f"Recuperados {len(docs)} documentos del cubo {cubo}")
                    except Exception as e:
                        print(f"Error al recuperar documentos del cubo {cubo}: {e}")
        
        # Limitar el número total de documentos para no sobrecargar el modelo
        max_docs = VECTORSTORE_CONFIG.get("max_docs_total", 10)
        if len(all_docs) > max_docs:
            all_docs = all_docs[:max_docs]
        
        return {
            "documents": all_docs,
            "question": question,
            "retry_count": retry_count,
            "relevant_cubos": relevant_cubos,
            "retrieval_details": retrieval_details
        }
    
    def grade_documents(state):
        """
        Determina si los documentos recuperados son relevantes para la pregunta.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con documentos filtrados.
        """
        print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
        question = state["question"]
        documents = state["documents"]
        retry_count = state.get("retry_count", 0)
        relevant_cubos = state.get("relevant_cubos", [])
        retrieval_details = state.get("retrieval_details", {})
        
        # Evaluar cada documento
        filtered_docs = []
        for d in documents:
            score = retrieval_grader.invoke(
                {"document": d.page_content, "question": question}
            )
            score_value = score["score"].lower() if isinstance(score, dict) else "no"
            
            if score_value == "yes":
                print("---GRADE: DOCUMENT RELEVANT---")
                filtered_docs.append(d)
            else:
                print("---GRADE: DOCUMENT NOT RELEVANT---")
        
        print("---ASSESS GRADED DOCUMENTS---")
        if not filtered_docs:
            print("---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION---")
        
        return {
            "documents": filtered_docs if filtered_docs else documents,
            "question": question,
            "retry_count": retry_count,
            "relevant_cubos": relevant_cubos,
            "retrieval_details": retrieval_details
        }
    
    def generate(state):
        """
        Genera una respuesta utilizando RAG en los documentos recuperados.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con la generación del LLM.
        """
        print("---GENERATE---")
        question = state["question"]
        documents = state["documents"]
        retry_count = state.get("retry_count", 0)
        relevant_cubos = state.get("relevant_cubos", [])
        retrieval_details = state.get("retrieval_details", {})
        
        # Generación RAG
        generation = rag_chain.invoke({"context": documents, "question": question})
        
        # Verificar alucinaciones
        print("---CHECK HALLUCINATIONS---")
        documents_text = "\n".join([d.page_content for d in documents])
        hallucination_score = hallucination_grader.invoke(
            {"documents": documents_text, "generation": generation}
        )
        
        # Verificar si la respuesta aborda la pregunta
        print("---GRADE GENERATION vs QUESTION---")
        answer_score = answer_grader.invoke(
            {"question": question, "generation": generation}
        )
        
        # Determinar si la generación es exitosa
        is_grounded = hallucination_score["score"].lower() == "yes" if isinstance(hallucination_score, dict) else False
        is_useful = answer_score["score"].lower() == "yes" if isinstance(answer_score, dict) else False
        
        if is_grounded:
            print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        else:
            print("---DECISION: GENERATION CONTAINS HALLUCINATIONS---")
            
        if is_useful:
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
        else:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
        
        # Si la generación no es exitosa, incrementar contador de reintentos
        if not (is_grounded and is_useful):
            retry_count += 1
            print(f"---RETRY ATTEMPT {retry_count}---")
            
        return {
            "documents": documents,
            "question": question,
            "generation": generation,
            "retry_count": retry_count,
            "hallucination_score": hallucination_score,
            "answer_score": answer_score,
            "relevant_cubos": relevant_cubos,
            "retrieval_details": retrieval_details
        }
    
    # Añadir nodos al grafo
    workflow.add_node("route_question", route_question)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)
    
    # Definir bordes
    workflow.set_entry_point("route_question")
    workflow.add_edge("route_question", "retrieve")
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_edge("grade_documents", "generate")
    
    # Definir condiciones para reintentos o finalización
    def should_retry(state):
        """
        Determina si se debe reintentar la generación.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            str: Siguiente nodo a ejecutar.
        """
        retry_count = state.get("retry_count", 0)
        max_retries = WORKFLOW_CONFIG["max_retries"]
        
        if retry_count < max_retries:
            return "retrieve"
        else:
            return END
    
    workflow.add_conditional_edges(
        "generate",
        should_retry,
        {
            "retrieve": "retrieve",
            END: END
        }
    )
    
    return workflow
