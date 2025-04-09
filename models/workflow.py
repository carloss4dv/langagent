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
        is_consulta: indica si la pregunta es sobre una consulta guardada
        consulta_documents: documentos de consultas guardadas recuperados
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
    is_consulta: bool
    consulta_documents: List[Document]

def normalize_name(name: str) -> str:
    """
    Normaliza un nombre de cubo o ámbito eliminando acentos, espacios y convirtiendo a minúsculas.
    
    Args:
        name (str): Nombre a normalizar
        
    Returns:
        str: Nombre normalizado
    """
    if not name:
        return ""
        
    # Mapeo de caracteres con acento a sin acento
    accent_map = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'a', 'É': 'e', 'Í': 'i', 'Ó': 'o', 'Ú': 'u',
        'ñ': 'n', 'Ñ': 'n'
    }
    
    # Convertir a minúsculas y reemplazar caracteres con acento
    normalized = name.lower()
    for accented, unaccented in accent_map.items():
        normalized = normalized.replace(accented, unaccented)
    
    # Eliminar espacios y caracteres especiales
    normalized = re.sub(r'[^a-z0-9]', '', normalized)
    
    return normalized

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
        Also identifies if the question is about a saved query.
        
        Args:
            state (dict): Current graph state.
            
        Returns:
            dict: Updated state with identified relevant cubes, scope, and if it's a query.
        """
        print("---ROUTE QUESTION---")
        question = state["question"]
        print(question)
        
        # Inicializar el indicador de consulta
        state["is_consulta"] = False
        state["consulta_documents"] = []
        
        try:
            # Determinar si la pregunta es sobre una consulta guardada
            consulta_keywords = [
                "consulta guardada", "consultas guardadas", "dashboard", 
                "visualización", "visualizacion", "reporte", "informe", 
                "cuadro de mando", "análisis predefinido", "analisis predefinido"
            ]
            
            # Verificar si alguna palabra clave está en la pregunta
            question_lower = question.lower()
            es_consulta = any(keyword in question_lower for keyword in consulta_keywords)
            
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
            
            # Normalizar nombres
            normalized_cube = normalize_name(cube_name)
            normalized_scope = normalize_name(scope)
            
            # Mapeo de ámbitos normalizados a sus claves internas
            scope_mapping = {
                "academico": "academico",
                "admission": "admision",
                "admission": "admision",
                "teaching": "docencia",
                "doctorate": "doctorado",
                "specificdegrees": "estudios_propios",
                "rd": "idi",
                "mobility": "movilidad",
                "hr": "rrhh"
            }
            
            # Obtener el ámbito normalizado
            normalized_scope = scope_mapping.get(normalized_scope, normalized_scope)
            
            # Marcar si es una consulta guardada basado en las palabras clave
            state["is_consulta"] = es_consulta
            
            # Si tenemos alta confianza y el cubo existe, usarlo directamente
            if confidence == "HIGH" and normalized_cube in retrievers:
                state["relevant_cubos"] = [normalized_cube]
                state["ambito"] = normalized_scope
                print(f"Using specific cube with high confidence: {normalized_cube}")
                
                # Si es una consulta y tenemos el ámbito, añadir el retriever de consultas
                if es_consulta and normalized_scope:
                    consulta_retriever_key = f"consultas_{normalized_scope}"
                    if consulta_retriever_key in retrievers:
                        state["relevant_cubos"].append(consulta_retriever_key)
                        print(f"Adding saved query retriever for scope: {normalized_scope}")
            
            # Si tenemos un ámbito válido pero confianza media/baja, usar todos los cubos de ese ámbito
            elif normalized_scope in AMBITOS_CUBOS:
                # Inicializar con el cubo específico si existe
                state["relevant_cubos"] = [normalized_cube] if normalized_cube in retrievers else []
                
                # Añadir retriever de consultas guardadas si aplica
                if es_consulta:
                    consulta_retriever_key = f"consultas_{normalized_scope}"
                    if consulta_retriever_key in retrievers:
                        state["relevant_cubos"].append(consulta_retriever_key)
                        print(f"Adding saved query retriever for scope: {normalized_scope}")
                
                state["ambito"] = normalized_scope
                print(f"Using scope {normalized_scope} with cube {normalized_cube}")
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
        Recupera documentos relevantes para la pregunta utilizando los cubos identificados.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con documentos recuperados.
        """
        print("---RETRIEVE---")
        question = state["question"]
        relevant_cubos = state["relevant_cubos"]
        
        print(f"Question: {question}")
        print(f"Using cubes: {relevant_cubos}")
        
        all_documents = []
        retrieval_details = {}
        consulta_documents = []
        
        # Recuperar documentos de cada cubo relevante
        for cubo in relevant_cubos:
            if cubo in retrievers:
                print(f"Retrieving from {cubo}...")
                docs = retrievers[cubo].get_relevant_documents(question)
                
                # Verificar si es un retriever de consultas guardadas
                if cubo.startswith("consultas_"):
                    print(f"Found {len(docs)} saved query documents from {cubo}")
                    # Añadir al listado específico de documentos de consultas
                    consulta_documents.extend(docs)
                    
                    # Agregar info al registro de detalles
                    retrieval_details[cubo] = {
                        "count": len(docs),
                        "documents": docs
                    }
                else:
                    # Verificar relevancia de documentos para cubos normales
                    relevant_docs = []
                    print(f"Evaluating relevance of {len(docs)} documents from {cubo}")
                    
                    for doc in docs:
                        try:
                            # Evaluar relevancia del documento
                            score_result = retrieval_grader.invoke({
                                "document": doc.page_content,
                                "question": question
                            })
                            
                            # Determinar si el documento es relevante
                            is_relevant = False
                            if isinstance(score_result, dict) and "score" in score_result:
                                is_relevant = score_result["score"].lower() == "yes"
                            elif isinstance(score_result, str):
                                # Intentar interpretar resultado como JSON
                                try:
                                    parsed = json.loads(score_result)
                                    is_relevant = parsed.get("score", "").lower() == "yes"
                                except:
                                    # Búsqueda por regex si falla el parsing JSON
                                    score_match = re.search(r'"score"\s*:\s*"(\w+)"', score_result)
                                    if score_match:
                                        is_relevant = score_match.group(1).lower() == "yes"
                            
                            # Añadir documento si es relevante
                            if is_relevant:
                                relevant_docs.append(doc)
                                print(f"Document considered relevant")
                            else:
                                print(f"Document NOT relevant, skipping...")
                                
                        except Exception as e:
                            print(f"Error evaluating document relevance: {e}")
                            # En caso de error, considerar el documento como relevante
                            relevant_docs.append(doc)
                    
                    # Añadir documentos relevantes a la lista completa
                    all_documents.extend(relevant_docs)
                    
                    # Agregar info al registro de detalles
                    retrieval_details[cubo] = {
                        "total": len(docs),
                        "relevant": len(relevant_docs),
                        "documents": relevant_docs
                    }
        
        # Añadir los documentos de consultas guardadas al estado y a la lista general
        state["consulta_documents"] = consulta_documents
        all_documents.extend(consulta_documents)
        
        # Actualizar estado
        state["documents"] = all_documents
        state["retrieval_details"] = retrieval_details
        
        print(f"Retrieved a total of {len(all_documents)} relevant documents" 
              f" ({len(consulta_documents)} are saved queries)")
        
        return state
    
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
        hallucination_eval = hallucination_grader.invoke(
            {"documents": documents_text, "generation": generation}
        )
        print(f"Hallucination evaluation: {hallucination_eval}")
        
        # Verificar si la respuesta aborda la pregunta
        print("---GRADE GENERATION vs QUESTION---")
        answer_eval = answer_grader.invoke(
            {"question": question, "generation": generation}
        )
        print(f"Answer evaluation: {answer_eval}")
        
        # Función auxiliar para extraer score de diferentes formatos de respuesta
        def extract_score(response) -> bool:
            """
            Extrae un valor booleano de la respuesta del evaluador.
            
            Args:
                response: Respuesta del evaluador (dict, str, bool, int, float)
                
            Returns:
                bool: True si la evaluación es positiva, False en caso contrario
            """
            try:
                # Si es un diccionario, buscar la clave 'score' primero
                if isinstance(response, dict):
                    if "score" in response:
                        value = str(response["score"]).lower().strip()
                        return value == "yes" or value == "true" or value == "1"
                        
                    # Si no hay 'score', buscar otras claves comunes
                    for key in ["result", "evaluation", "is_grounded", "is_relevant"]:
                        if key in response:
                            value = str(response[key]).lower().strip()
                            return value == "yes" or value == "true" or value == "1"
                            
            except Exception as e:
                print(f"Error extracting score: {e}")
                
            # Por defecto, asumir que no es válido
            return False
        
        # Determinar si la generación es exitosa
        is_grounded = extract_score(hallucination_eval)
        is_useful = extract_score(answer_eval)
        
        if is_grounded:
            print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        else:
            print("---DECISION: GENERATION CONTAINS HALLUCINATIONS---")
            
        if is_useful:
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
        else:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
        
        # Formatear la respuesta
        if isinstance(generation, dict):
            if "answer" in generation:
                formatted_generation = generation["answer"]
            else:
                formatted_generation = str(generation)
        else:
            formatted_generation = str(generation)
        
        # Limpiar y formatear la respuesta
        formatted_generation = formatted_generation.strip()
        formatted_generation = re.sub(r'\n\s*\n', '\n\n', formatted_generation)  # Eliminar líneas vacías múltiples
        formatted_generation = re.sub(r'\s+', ' ', formatted_generation)  # Eliminar espacios múltiples
        
        # Si la generación no es exitosa, incrementar contador de reintentos
        if not (is_grounded and is_useful):
            retry_count += 1
            print(f"---RETRY ATTEMPT {retry_count}---")
        
        return {
            "documents": documents,
            "question": question,
            "generation": formatted_generation,
            "retry_count": retry_count,
            "hallucination_score": hallucination_eval,
            "answer_score": answer_eval,
            "relevant_cubos": relevant_cubos,
            "ambito": state.get("ambito"),
            "retrieval_details": retrieval_details
        }
    
    def should_retry(state):
        """
        Determina si se debe reintentar la consulta.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            bool: True si se debe reintentar, False en caso contrario.
        """
        print("---SHOULD RETRY---")
        
        retry_count = state.get("retry_count", 0)
        max_retries = WORKFLOW_CONFIG.get("max_retries", 2)
        
        # Verificar si la respuesta actual es satisfactoria
        hallucination_score = state.get("hallucination_score")
        answer_score = state.get("answer_score")
        
        is_hallucination = False
        is_useful = False
        
        # Interpretar los scores
        if isinstance(hallucination_score, dict) and "score" in hallucination_score:
            is_hallucination = hallucination_score["score"].lower() != "yes"
        
        if isinstance(answer_score, dict) and "score" in answer_score:
            is_useful = answer_score["score"].lower() == "yes"
        
        # Determinar si necesitamos un nuevo intento
        need_retry = (is_hallucination or not is_useful) and retry_count < max_retries
        
        if need_retry:
            print(f"Reintento {retry_count + 1}/{max_retries} necesario.")
            print(f"Hallucination: {'Sí' if is_hallucination else 'No'}")
            print(f"Respuesta útil: {'Sí' if is_useful else 'No'}")
            
            # Incrementar contador de reintentos
            state["retry_count"] = retry_count + 1
            
            # Si estamos en el último intento, ampliar la búsqueda
            if state["retry_count"] == max_retries - 1:
                print("Último intento: ampliando criterios de búsqueda...")
                # Si la pregunta es sobre una consulta, añadir más retrievers de consultas
                if state.get("is_consulta", False) and state.get("ambito"):
                    ambito = state["ambito"]
                    relevant_cubos = list(state.get("relevant_cubos", []))
                    consulta_key = f"consultas_{ambito}"
                    if consulta_key not in relevant_cubos:
                        relevant_cubos.append(consulta_key)
                        state["relevant_cubos"] = relevant_cubos
                        print(f"Añadiendo retriever de consultas para {ambito}")
        else:
            reason = "Respuesta satisfactoria" if (not is_hallucination and is_useful) else "Máximo de reintentos alcanzado"
            print(f"No se necesita reintento. Razón: {reason}")
        
        return need_retry
    
    # Añadimos los nodos al grafo
    workflow.add_node("route_question", route_question)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate)
    workflow.add_node("should_retry", should_retry)
    
    # Configuramos las transiciones
    workflow.set_entry_point("route_question")
    workflow.add_edge("route_question", "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_conditional_edges(
        "should_retry",
        {
            True: "route_question",
            False: END 
        }
    )
    workflow.add_edge("generate", "should_retry")
    
    return workflow
