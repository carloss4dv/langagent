"""
Módulo para el flujo de control del agente utilizando LangGraph.

Este módulo implementa el flujo de control para el agente de respuesta a preguntas
utilizando LangGraph, con un mecanismo de reintento para respuestas no exitosas.
Soporta múltiples vectorstores organizados en cubos y ámbitos.
"""

from typing import List, Dict, Any, Optional, Tuple
from typing_extensions import TypedDict
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
import json
import re

from langagent.config.config import WORKFLOW_CONFIG, VECTORSTORE_CONFIG
from langagent.models.constants import AMBITOS_CUBOS, CUBO_TO_AMBITO, AMBITO_KEYWORDS

class GraphState(TypedDict):
    """
    Representa el estado del grafo.

    Attributes:
        question: pregunta del usuario
        generation: generación del LLM
        documents: lista de documentos
        retry_count: contador de reintentos
        relevant_cubos: lista de cubos relevantes para la pregunta
        ambito: ámbito identificado para la pregunta
        retrieval_details: detalles de recuperación por cubo
    """
    question: str
    generation: str
    documents: List[Document]
    retry_count: int
    hallucination_score: Optional[str]
    answer_score: Optional[str]
    relevant_cubos: List[str]
    ambito: Optional[str]
    retrieval_details: Dict[str, Dict[str, Any]]

def find_relevant_cubos_by_keywords(query: str, available_cubos: List[str]) -> Tuple[List[str], Optional[str]]:
    """
    Encuentra cubos relevantes basados en palabras clave y ámbitos en la consulta.
    Si se identifica un ámbito, devuelve todos los cubos asociados a ese ámbito.
    
    Args:
        query: La consulta del usuario
        available_cubos: Lista de cubos disponibles
        
    Returns:
        Tuple[List[str], Optional[str]]: (Lista de cubos relevantes, ámbito identificado)
    """
    query_lower = query.lower()
    
    # Buscar referencias explícitas a ámbitos
    explicit_ambito_pattern = r"(?:ámbito|ambito)\s+(\w+)"
    ambito_matches = re.findall(explicit_ambito_pattern, query_lower)
    
    # Verificar ámbitos explícitos
    for match in ambito_matches:
        ambito_key = match.lower().replace(" ", "_")
        if ambito_key in AMBITOS_CUBOS:
            # Devolver todos los cubos disponibles del ámbito
            relevant_cubos = [
                cubo for cubo in AMBITOS_CUBOS[ambito_key]["cubos"]
                if cubo in available_cubos
            ]
            return relevant_cubos, ambito_key
    
    # Buscar referencias explícitas a cubos
    explicit_cubo_pattern = r"(?:del|en el|del cubo|en el cubo)\s+(\w+)"
    cubo_matches = re.findall(explicit_cubo_pattern, query_lower)
    
    for match in cubo_matches:
        if match in available_cubos:
            # Identificar el ámbito del cubo
            ambito = CUBO_TO_AMBITO.get(match)
            if ambito:
                # Devolver todos los cubos del ámbito
                relevant_cubos = [
                    cubo for cubo in AMBITOS_CUBOS[ambito]["cubos"]
                    if cubo in available_cubos
                ]
                return relevant_cubos, ambito
            return [match], None
    
    # Buscar keywords de ámbitos
    ambito_scores = {}
    for ambito, keywords in AMBITO_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in query_lower)
        if score > 0:
            ambito_scores[ambito] = score
    
    # Si encontramos ámbitos por keywords
    if ambito_scores:
        # Seleccionar el ámbito con mayor puntuación
        selected_ambito = max(ambito_scores.items(), key=lambda x: x[1])[0]
        relevant_cubos = [
            cubo for cubo in AMBITOS_CUBOS[selected_ambito]["cubos"]
            if cubo in available_cubos
        ]
        return relevant_cubos, selected_ambito
    
    # Si no encontramos nada, devolver todos los cubos disponibles
    return list(available_cubos), None

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
        Determines which cubes are relevant for the question and the corresponding scope.
        
        Args:
            state (dict): Current graph state.
            
        Returns:
            dict: Updated state with identified relevant cubes and scope.
        """
        print("---ROUTE QUESTION---")
        question = state["question"]
        print(question)
        
        try:
            # Invoke router and parse result
            routing_result = question_router.invoke({"question": question})
            
            # Router can return a dictionary directly or a JSON string
            if isinstance(routing_result, dict):
                cube_name = routing_result.get("cube", "")
                scope = routing_result.get("scope", "")
                confidence = routing_result.get("confidence", "LOW")
            elif isinstance(routing_result, str):
                try:
                    parsed = json.loads(routing_result)
                    cube_name = parsed.get("cube", "")
                    scope = parsed.get("scope", "")
                    confidence = parsed.get("confidence", "LOW")
                except json.JSONDecodeError:
                    # Fallback regex parsing if needed
                    cube_match = re.search(r'"cube"\s*:\s*"([^"]+)"', routing_result)
                    cube_name = cube_match.group(1) if cube_match else ""
                    scope_match = re.search(r'"scope"\s*:\s*"([^"]+)"', routing_result)
                    scope = scope_match.group(1) if scope_match else ""
                    confidence = "LOW"
            else:
                cube_name = ""
                scope = ""
                confidence = "LOW"
                
            print(f"Router identified cube: {cube_name}")
            print(f"Router identified scope: {scope}")
            print(f"Router confidence: {confidence}")
            
            # Map English scope names to Spanish ones
            scope_mapping = {
                "ACADEMIC": "ACADÉMICO",
                "ADMISSION": "ADMISIÓN", 
                "TEACHING": "DOCENCIA",
                "DOCTORATE": "DOCTORADO",
                "SPECIFIC DEGREES": "ESTUDIOS PROPIOS",
                "R&D": "I+D+i",
                "MOBILITY": "MOVILIDAD",
                "HR": "RRHH"
            }
            
            spanish_scope = scope_mapping.get(scope.upper(), scope)
            
            # If we have high confidence and the cube exists, use it directly
            if confidence == "HIGH" and cube_name in retrievers:
                state["relevant_cubos"] = [cube_name]
                state["ambito"] = spanish_scope
                print(f"Using specific cube with high confidence: {cube_name}")
            # If we have a valid scope but medium/low confidence, use all cubes in that scope
            elif spanish_scope:
                state["relevant_cubos"] = [cube_name] if cube_name else []
                state["ambito"] = spanish_scope
                print(f"Using scope {spanish_scope} with cube {cube_name}")
            else:
                # Fallback to using all available cubes
                state["relevant_cubos"] = list(retrievers.keys()) if isinstance(retrievers, dict) else []
                state["ambito"] = None
                print("No specific scope identified. Using all available cubes.")
                
        except Exception as e:
            print(f"Error in route_question: {e}")
            # On error, use all cubes if retrievers is a dict
            state["relevant_cubos"] = list(retrievers.keys()) if isinstance(retrievers, dict) else []
            state["ambito"] = None
            print("Error in router. Using all available cubes.")
        
        # Initialize retry counter
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
        ambito = state.get("ambito")
        
        # Si tenemos un ámbito identificado, usar todos sus cubos
        if ambito and ambito in AMBITOS_CUBOS:
            relevant_cubos = [
                cubo for cubo in AMBITOS_CUBOS[ambito]["cubos"]
                if cubo in retrievers
            ]
            print(f"Usando todos los cubos del ámbito {AMBITOS_CUBOS[ambito]['nombre']}")
        else:
            relevant_cubos = state.get("relevant_cubos", list(retrievers.keys()))
        
        all_docs = []
        retrieval_details = {}
        
        # Recuperar documentos de cada cubo relevante
        for cubo in relevant_cubos:
            if cubo in retrievers:
                try:
                    print(f"Recuperando documentos del cubo: {cubo}")
                    retriever = retrievers[cubo]
                    docs = retriever.invoke(question)
                    
                    # Añadir metadatos sobre el cubo y ámbito
                    for doc in docs:
                        doc.metadata["cubo_source"] = cubo
                        doc.metadata["ambito"] = CUBO_TO_AMBITO.get(cubo)
                    
                    retrieval_details[cubo] = {
                        "count": len(docs),
                        "ambito": CUBO_TO_AMBITO.get(cubo),
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
        
        # Limitar el número total de documentos
        max_docs = VECTORSTORE_CONFIG.get("max_docs_total", 10)
        if len(all_docs) > max_docs:
            all_docs = all_docs[:max_docs]
        
        return {
            "documents": all_docs,
            "question": question,
            "retry_count": retry_count,
            "relevant_cubos": relevant_cubos,
            "ambito": ambito,
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
            "ambito": state.get("ambito"),
            "retrieval_details": retrieval_details
        }
    
    # Añadir nodos al grafo
    workflow.add_node("route_question", route_question)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate)
    
    # Definir bordes - flujo simplificado
    workflow.set_entry_point("route_question")
    workflow.add_edge("route_question", "retrieve")
    workflow.add_edge("retrieve", "generate")
    
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
        
        # Verificar si la generación actual es exitosa
        hallucination_score = state.get("hallucination_score", {})
        answer_score = state.get("answer_score", {})
        
        is_grounded = hallucination_score.get("score", "").lower() == "yes"
        is_useful = answer_score.get("score", "").lower() == "yes"
        
        # Si la generación es exitosa o alcanzamos el máximo de reintentos, terminar
        if (is_grounded and is_useful) or retry_count >= max_retries:
            print(f"---DECISION: {'GENERATION SUCCESSFUL' if (is_grounded and is_useful) else 'MAX RETRIES REACHED'}---")
            return END
        
        # Si necesitamos reintentar, incrementar el contador
        state["retry_count"] = retry_count + 1
        print(f"---RETRY ATTEMPT {state['retry_count']} OF {max_retries}---")
        
        # Si estamos en el último reintento, usar todos los cubos disponibles
        if state["retry_count"] == max_retries - 1:
            state["relevant_cubos"] = list(retrievers.keys())
            print("---USING ALL AVAILABLE CUBES FOR FINAL ATTEMPT---")
        
        return "generate"
    
    workflow.add_conditional_edges(
        "generate",
        should_retry,
        {
            "generate": "generate",
            END: END
        }
    )
    
    return workflow
