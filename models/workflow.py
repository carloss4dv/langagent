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
            
            # Si el router es un retriever de llama-index, usarlo directamente
            if hasattr(question_router, '_router_query_engine'):
                # Obtener documentos usando el router retriever
                docs = question_router.get_relevant_documents(question)
                if docs:
                    # Extraer el cubo del primer documento
                    first_doc = docs[0]
                    cube_name = first_doc.metadata.get('cubo_source', '')
                    scope = first_doc.metadata.get('ambito', '')
                    state["relevant_cubos"] = [cube_name] if cube_name else list(retrievers.keys())
                    state["ambito"] = scope
                    print(f"Router identified cube: {cube_name}")
                    print(f"Router identified scope: {scope}")
                else:
                    state["relevant_cubos"] = list(retrievers.keys())
                    state["ambito"] = None
                    print("No specific cube identified. Using all available cubes.")
            else:
                # Usar el router de preguntas estándar
                routing_result = question_router.invoke({"question": question})
                
                # Router can return a dictionary directly or a JSON string
                if isinstance(routing_result, dict):
                    cube_name = routing_result.get("cube", "")
                    scope = routing_result.get("scope", "")
                    confidence = routing_result.get("confidence", "LOW")
                    is_query = routing_result.get("is_query", False)
                elif isinstance(routing_result, str):
                    try:
                        parsed = json.loads(routing_result)
                        cube_name = parsed.get("cube", "")
                        scope = parsed.get("scope", "")
                        confidence = parsed.get("confidence", "LOW")
                        is_query = parsed.get("is_query", False)
                    except json.JSONDecodeError:
                        # Fallback regex parsing if needed
                        cube_match = re.search(r'"cube"\s*:\s*"([^"]+)"', routing_result)
                        cube_name = cube_match.group(1) if cube_match else ""
                        scope_match = re.search(r'"scope"\s*:\s*"([^"]+)"', routing_result)
                        scope = scope_match.group(1) if scope_match else ""
                        confidence = "LOW"
                        is_query = False
                else:
                    cube_name = ""
                    scope = ""
                    confidence = "LOW"
                    is_query = False
                
                print(f"Router identified cube: {cube_name}")
                print(f"Router identified scope: {scope}")
                print(f"Router confidence: {confidence}")
                print(f"Is query: {is_query}")
                
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
                
                # Marcar si es una consulta guardada basado en las palabras clave o el router
                state["is_consulta"] = es_consulta or is_query
                
                # Si tenemos alta confianza y el cubo existe, usarlo directamente
                if confidence == "HIGH" and normalized_cube in retrievers:
                    state["relevant_cubos"] = [normalized_cube]
                    state["ambito"] = normalized_scope
                    print(f"Using specific cube with high confidence: {normalized_cube}")
                    
                    # Si es una consulta y tenemos el ámbito, añadir el retriever de consultas
                    if state["is_consulta"] and normalized_scope:
                        consulta_retriever_key = f"consultas_{normalized_scope}"
                        if consulta_retriever_key in retrievers:
                            state["relevant_cubos"].append(consulta_retriever_key)
                            print(f"Adding saved query retriever for scope: {normalized_scope}")
                
                # Si tenemos un ámbito válido pero confianza media/baja, usar todos los cubos de ese ámbito
                elif normalized_scope in AMBITOS_CUBOS:
                    # Inicializar con el cubo específico si existe
                    state["relevant_cubos"] = [normalized_cube] if normalized_cube in retrievers else []
                    
                    # Añadir retriever de consultas guardadas si aplica
                    if state["is_consulta"]:
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
        Recupera documentos de los vectorstores relevantes y los filtra por relevancia.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con los documentos recuperados y filtrados.
        """
        print("\n=== INICIO DE RECUPERACIÓN DE DOCUMENTOS ===")
        print(f"Pregunta: {state['question']}")
        print(f"Intento actual: {state.get('retry_count', 0)}")
        print(f"Ámbito identificado: {state.get('ambito', 'No identificado')}")
        
        question = state["question"]
        retry_count = state.get("retry_count", 0)
        ambito = state.get("ambito")
        
        # Si tenemos un ámbito identificado, usar todos sus cubos
        if ambito and ambito in AMBITOS_CUBOS:
            relevant_cubos = [
                cubo for cubo in AMBITOS_CUBOS[ambito]["cubos"]
                if cubo in retrievers
            ]
            print(f"\nUsando cubos del ámbito {AMBITOS_CUBOS[ambito]['nombre']}:")
            print(f"Cubos disponibles: {relevant_cubos}")
        else:
            relevant_cubos = state.get("relevant_cubos", list(retrievers.keys()))
            print(f"\nUsando cubos relevantes identificados:")
            print(f"Cubos disponibles: {relevant_cubos}")
        
        all_docs = []
        retrieval_details = {}
        
        # Recuperar documentos de cada cubo relevante
        for cubo in relevant_cubos:
            if cubo in retrievers:
                try:
                    print(f"\nProcesando cubo: {cubo}")
                    print(f"Retriever disponible: {cubo in retrievers}")
                    
                    retriever = retrievers[cubo]
                    print("Iniciando recuperación de documentos...")
                    docs = retriever.invoke(question)
                    
                    print(f"Documentos recuperados del cubo {cubo}: {len(docs)}")
                    
                    # Filtrar documentos por relevancia usando el retrieval_grader
                    relevant_docs = []
                    for doc in docs:
                        # Evaluar relevancia del documento
                        relevance = retrieval_grader.invoke({
                            "document": doc.page_content,
                            "question": question
                        })
                        
                        # Extraer score de la respuesta
                        if isinstance(relevance, dict) and "score" in relevance:
                            is_relevant = relevance["score"].lower() == "yes"
                        else:
                            # Por defecto, considerar el documento como relevante
                            is_relevant = True
                        
                        if is_relevant:
                            # Añadir metadatos sobre el cubo y ámbito
                            doc.metadata["cubo_source"] = cubo
                            doc.metadata["ambito"] = CUBO_TO_AMBITO.get(cubo)
                            relevant_docs.append(doc)
                    
                    retrieval_details[cubo] = {
                        "count": len(docs),
                        "relevant_count": len(relevant_docs),
                        "ambito": CUBO_TO_AMBITO.get(cubo),
                        "first_doc_snippet": relevant_docs[0].page_content[:100] + "..." if relevant_docs else "No documents retrieved"
                    }
                    
                    all_docs.extend(relevant_docs)
                    print(f"Documentos relevantes del cubo {cubo}: {len(relevant_docs)}")
                    print(f"Total acumulado de documentos: {len(all_docs)}")
                    
                except Exception as e:
                    print(f"\nERROR al recuperar documentos del cubo {cubo}:")
                    print(f"Tipo de error: {type(e).__name__}")
                    print(f"Mensaje de error: {str(e)}")
                    retrieval_details[cubo] = {
                        "count": 0,
                        "relevant_count": 0,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
        
        # Limitar el número total de documentos
        max_docs = VECTORSTORE_CONFIG.get("max_docs_total", 10)
        if len(all_docs) > max_docs:
            print(f"\nLímite de documentos alcanzado ({max_docs}). Recortando resultados...")
            all_docs = all_docs[:max_docs]
        
        print("\n=== RESUMEN DE LA RECUPERACIÓN ===")
        print(f"Total de documentos recuperados: {len(all_docs)}")
        print(f"Detalles por cubo:")
        for cubo, details in retrieval_details.items():
            print(f"- {cubo}: {details['count']} documentos recuperados, {details.get('relevant_count', 0)} relevantes")
            if "error" in details:
                print(f"  Error: {details['error']}")
        
        print("=== FIN DE RECUPERACIÓN DE DOCUMENTOS ===\n")
        
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
