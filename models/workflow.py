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
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
import json
import re

from langagent.config.config import WORKFLOW_CONFIG, VECTORSTORE_CONFIG, SQL_CONFIG
from langagent.models.constants import (
    AMBITOS_CUBOS, CUBO_TO_AMBITO, AMBITO_KEYWORDS, 
    AMBITO_EN_ES, CUBO_EN_ES
)

class GraphState(TypedDict):
    """
    Representa el estado del grafo.

    Attributes:
        question: pregunta del usuario
        rewritten_question: pregunta reescrita con términos técnicos de SEGEDA
        generation: generación del LLM
        documents: lista de documentos
        retrieved_documents: lista de documentos recuperados
        retry_count: contador de reintentos
        hallucination_score: puntuación de alucinaciones
        answer_score: puntuación de la respuesta
        relevant_cubos: lista de cubos relevantes para la pregunta
        ambito: ámbito identificado para la pregunta
        retrieval_details: detalles de recuperación por cubo
        is_consulta: indica si la pregunta es sobre una consulta guardada o SQL
        consulta_documents: documentos de consultas guardadas recuperados
        sql_query: consulta SQL generada
        sql_result: resultado de la consulta SQL
    """
    question: str
    rewritten_question: str
    generation: str
    documents: List[Document]
    retrieved_documents: List[Document]
    retry_count: int
    hallucination_score: Optional[str]
    answer_score: Optional[str]
    relevant_cubos: List[str]
    ambito: Optional[str]
    retrieval_details: Dict[str, Dict[str, Any]]
    is_consulta: bool
    consulta_documents: List[Document]
    sql_query: Optional[str]
    sql_result: Optional[str]

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

def execute_query(state):
    """
    Ejecuta la consulta SQL generada.
    
    Args:
        state (dict): Estado actual del grafo.
        
    Returns:
        dict: Estado actualizado con el resultado de la consulta SQL.
    """
    sql_query = state.get("sql_query")
    if not sql_query:
        print("No hay consulta SQL para ejecutar.")
        return state
    
    print("---EXECUTE QUERY---")
    print(f"Ejecutando consulta SQL: {sql_query}")
    
    try:
        # Crear la conexión a la base de datos y herramienta de consulta
        if SQL_CONFIG.get("db_uri"):
            db = SQLDatabase.from_uri(SQL_CONFIG.get("db_uri"))
            execute_query_tool = QuerySQLDatabaseTool(db=db)
            
            # Ejecutar la consulta
            result = execute_query_tool.invoke(sql_query)
            print("Consulta ejecutada con éxito.")
            
            # Actualizar el estado con el resultado
            return {
                **state,
                "sql_result": result
            }
        else:
            error = "No se ha configurado la conexión a la base de datos."
            print(error)
            return {
                **state,
                "sql_result": error
            }
    except Exception as e:
        error = f"Error al ejecutar la consulta SQL: {str(e)}"
        print(error)
        return {
            **state,
            "sql_result": error
        }

def create_workflow(retrievers, rag_chain, retrieval_grader, hallucination_grader, answer_grader, question_router, query_rewriter=None, rag_sql_chain=None):
    """
    Crea un flujo de trabajo para el agente utilizando LangGraph.
    Soporta múltiples vectorstores organizados en cubos y consultas a bases de datos SQL.
    
    Args:
        retrievers(dict): Diccionario de retrievers por cubo.
        rag_chain: Cadena de RAG.
        retrieval_grader: Evaluador de relevancia de documentos.
        hallucination_grader: Evaluador de alucinaciones.
        answer_grader: Evaluador de utilidad de respuestas.
        question_router: Router de preguntas para determinar cubos relevantes.
        query_rewriter: Reescritor de consultas para mejorar la recuperación.
        rag_sql_chain: Cadena para consultas SQL cuando se detecta que es una consulta de base de datos.
        
    Returns:
        StateGraph: Grafo de estado configurado.
    """
    # Definimos el grafo de estado
    workflow = StateGraph(GraphState)
    
    # Nodos
    
    def route_question(state):
        """
        Determines which cubes are relevant for the question and the corresponding scope.
        Also rewrites the question to improve retrieval if query_rewriter is provided.
        
        Args:
            state (dict): Current graph state.
            
        Returns:
            dict: Updated state with identified relevant cubes, scope, rewritten question, and if it's a query.
        """
        print("---ROUTE QUESTION---")
        question = state["question"]
        print(f"Pregunta original: {question}")
        
        # Inicializar el indicador de consulta y la pregunta reescrita
        state["is_consulta"] = False
        state["consulta_documents"] = []
        state["rewritten_question"] = question  # Por defecto, usar la pregunta original
        
        try:
            # Reescribir la pregunta si tenemos un reescritor
            if query_rewriter:
                try:
                    rewritten_question = query_rewriter.invoke({"question": question})
                    if rewritten_question and isinstance(rewritten_question, str) and len(rewritten_question.strip()) > 0:
                        state["rewritten_question"] = rewritten_question.strip()
                        print(f"Pregunta reescrita: {state['rewritten_question']}")
                except Exception as e:
                    print(f"Error al reescribir la pregunta: {e}")
                    # En caso de error, mantener la pregunta original
            
            # Usar la pregunta reescrita para el resto del procesamiento
            processed_question = state["rewritten_question"]
            
            # Determinar si la pregunta es sobre una consulta guardada
            consulta_keywords = [
                "consulta guardada", "consultas guardadas", "dashboard", 
                "visualización", "visualizacion", "reporte", "informe", 
                "cuadro de mando", "análisis predefinido", "analisis predefinido"
            ]
            
            # Verificar si alguna palabra clave está en la pregunta
            question_lower = processed_question.lower()
            es_consulta = any(keyword in question_lower for keyword in consulta_keywords)
            
            # Si el router es un retriever de llama-index, usarlo directamente
            if hasattr(question_router, '_router_query_engine'):
                # Obtener documentos usando el router retriever con la pregunta reescrita
                docs = question_router.invoke({"question": processed_question})
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
                # Usar el router de preguntas estándar con la pregunta reescrita
                routing_result = question_router.invoke({"question": processed_question})
                
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
                
                # Nombres en inglés recibidos del router
                cube_name_lower = cube_name.lower() if cube_name else ""
                scope_lower = scope.lower() if scope else ""
                
                # Simplemente usamos los nombres originales, ya que están en español
                es_cube_name = cube_name
                es_scope = scope
                
                # SOLO intentamos traducir cuando realmente tenemos nombres en inglés
                # Para cubos: comprobamos si el cubo está en las claves de inglés a español, pero NO en las claves español a inglés
                if es_cube_name:
                    # Comprobar si es un nombre en inglés conocido: está en CUBO_EN_ES pero no como clave española
                    nombre_normalizado = normalize_name(es_cube_name)
                    
                    # Verificar si el nombre está como clave inglesa pero no como clave española
                    es_nombre_ingles = False
                    for en_name in list(CUBO_EN_ES.keys())[:25]:  # Solo las claves inglés->español (primera mitad)
                        if normalize_name(en_name) == nombre_normalizado:
                            es_nombre_ingles = True
                            es_cube_name = CUBO_EN_ES[en_name]
                            print(f"Traducido cubo (inglés->español): {cube_name} -> {es_cube_name}")
                            break
                
                # Para ámbitos: similar, comprobamos si está en las claves de inglés a español, pero NO es un ámbito en español conocido
                if es_scope:
                    # Comprobar si es un nombre en inglés conocido: está en AMBITO_EN_ES pero no como clave española
                    nombre_normalizado = normalize_name(es_scope)
                    
                    # Verificar si el nombre está en las claves inglesas pero no es un ámbito válido en español
                    if nombre_normalizado not in AMBITOS_CUBOS:
                        for en_name in list(AMBITO_EN_ES.keys())[:8]:  # Solo las claves inglés->español (primera mitad)
                            if normalize_name(en_name) == nombre_normalizado:
                                es_scope = AMBITO_EN_ES[en_name]
                                print(f"Traducido ámbito (inglés->español): {scope} -> {es_scope}")
                                break
                
                # Normalizar nombres para la búsqueda en retrievers
                normalized_cube = normalize_name(es_cube_name)
                normalized_scope = normalize_name(es_scope)
                
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
                    
                    # Añadir todos los cubos del ámbito
                    cubos_ambito = AMBITOS_CUBOS[normalized_scope]["cubos"]
                    for cubo in cubos_ambito:
                        if cubo in retrievers and cubo not in state["relevant_cubos"]:
                            state["relevant_cubos"].append(cubo)
                    
                    # Comprobar si tenemos cubos en la lista
                    if not state["relevant_cubos"]:
                        print(f"ADVERTENCIA: No se encontraron cubos disponibles para el ámbito '{normalized_scope}'")
                        print(f"Cubos definidos en el ámbito: {cubos_ambito}")
                        print(f"Cubos disponibles en retrievers: {list(retrievers.keys())}")
                        
                        # Verificar si hay alguna coincidencia parcial en los retrievers
                        for retriever_key in retrievers.keys():
                            for cubo in cubos_ambito:
                                if cubo in retriever_key:
                                    state["relevant_cubos"].append(retriever_key)
                                    print(f"Añadida coincidencia parcial: {retriever_key}")
                        
                        # Si aún no hay cubos, usar la colección unificada si existe
                        if not state["relevant_cubos"] and "unified" in retrievers:
                            state["relevant_cubos"].append("unified")
                            print("Usando colección unificada como fallback")
                    
                    # Añadir retriever de consultas guardadas si aplica
                    if state["is_consulta"]:
                        consulta_retriever_key = f"consultas_{normalized_scope}"
                        if consulta_retriever_key in retrievers:
                            state["relevant_cubos"].append(consulta_retriever_key)
                            print(f"Adding saved query retriever for scope: {normalized_scope}")
                    
                    state["ambito"] = normalized_scope
                    print(f"Using scope {normalized_scope} with cubes: {state['relevant_cubos']}")
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
        Retrieves documents from the relevant cubes.
        
        Args:
            state (dict): Current graph state.
            
        Returns:
            dict: Updated state with retrieved documents.
        """
        question = state["question"]
        rewritten_question = state.get("rewritten_question", question)  # Usar pregunta reescrita si existe, sino la original
        relevant_cubos = state.get("relevant_cubos", [])
        ambito = state.get("ambito")
        retry_count = state.get("retry_count", 0)
        
        print("---RETRIEVE---")
        print(f"Búsqueda con pregunta: {rewritten_question}")
        print(f"Ámbito identificado: {ambito}")
        print(f"Cubos relevantes: {relevant_cubos}")
        
        # Si no hay cubos relevantes, usar todos disponibles
        if not relevant_cubos and isinstance(retrievers, dict):
            relevant_cubos = list(retrievers.keys())
            print(f"No se identificaron cubos relevantes. Usando todos: {relevant_cubos}")
        
        # Si estamos en el último intento y la estrategia es usar todos los cubos, pasar directamente al retrieve_from_unified
        unified_retriever_exists = "unified" in retrievers if isinstance(retrievers, dict) else False
        if retry_count >= WORKFLOW_CONFIG.get("max_retries", 2) and unified_retriever_exists:
            print(f"Último intento (retry {retry_count}). Usando colección unificada.")
            return retrieve_from_unified(state)
        
        all_docs = []
        retrieval_details = {}
        
        # Comprobar si tenemos un retriever combinado para todos los cubos
        combined_retriever_exists = "combined" in retrievers if isinstance(retrievers, dict) else False
        
        # En el último intento, si hay un retriever combinado, usarlo
        if retry_count >= WORKFLOW_CONFIG.get("max_retries", 2) - 1 and combined_retriever_exists:
            try:
                print("Usando retriever combinado para todos los cubos...")
                docs = retrievers["combined"].invoke(rewritten_question)
                
                # Comprobar si todos los documentos son relevantes
                relevant_docs = []
                for doc in docs:
                    relevance = retrieval_grader.invoke({
                        "document": doc.page_content,
                        "question": rewritten_question
                    })
                    
                    if isinstance(relevance, dict) and relevance.get("score", "").lower() == "yes":
                        # Añadir metadatos sobre el cubo y ámbito si no existen
                        if "cubo_source" not in doc.metadata:
                            doc.metadata["cubo_source"] = "combined"
                        if "ambito" not in doc.metadata and ambito:
                            doc.metadata["ambito"] = ambito
                        relevant_docs.append(doc)
                
                # Si no hay documentos relevantes, usar todos
                if not relevant_docs and docs:
                    for doc in docs:
                        if "cubo_source" not in doc.metadata:
                            doc.metadata["cubo_source"] = "combined"
                        if "ambito" not in doc.metadata and ambito:
                            doc.metadata["ambito"] = ambito
                    relevant_docs = docs
                
                retrieval_details["combined"] = {
                    "count": len(docs),
                    "relevant_count": len(relevant_docs),
                    "ambito": ambito,
                    "first_doc_snippet": relevant_docs[0].page_content[:100] + "..." if relevant_docs else "No documents retrieved"
                }
                
                all_docs.extend(relevant_docs)
                
            except Exception as e:
                print(f"Error al recuperar documentos del retriever combinado: {str(e)}")
        else:
            # Si no, iterar sobre los cubos relevantes
            for cubo in relevant_cubos:
                try:
                    if cubo not in retrievers:
                        print(f"ADVERTENCIA: No se encontró retriever para el cubo '{cubo}'")
                        continue
                    
                    # Obtener documentos del cubo
                    print(f"Recuperando documentos del cubo: {cubo}")
                    docs = retrievers[cubo].invoke(rewritten_question)
                    print(f"Documentos recuperados de {cubo}: {len(docs)}")
                    
                    # Comprobar si todos los documentos son relevantes
                    relevant_docs = []
                    
                    if cubo.startswith("consultas_"):
                        # Para consultas guardadas, añadir siempre todos los documentos sin evaluar relevancia
                        for doc in docs:
                            # Añadir metadatos sobre el cubo y ámbito si no existen
                            if "cubo_source" not in doc.metadata:
                                doc.metadata["cubo_source"] = cubo
                            if "ambito" not in doc.metadata and ambito:
                                doc.metadata["ambito"] = ambito
                            # Marcar explícitamente como consulta guardada
                            doc.metadata["is_consulta"] = "true"
                            relevant_docs.append(doc)
                        
                        # Añadir a la lista de documentos de consultas guardadas
                        state["consulta_documents"] = relevant_docs
                    else:
                        # Para otros cubos, evaluar relevancia
                        for doc in docs:
                            relevance = retrieval_grader.invoke({
                                "document": doc.page_content,
                                "question": rewritten_question
                            })
                            
                            # Extraer score de la respuesta
                            if isinstance(relevance, dict) and "score" in relevance:
                                is_relevant = relevance["score"].lower() == "yes"
                            else:
                                # Por defecto, considerar el documento como relevante
                                is_relevant = True
                            
                            if is_relevant:
                                # Añadir metadatos sobre el cubo y ámbito si no existen
                                if "cubo_source" not in doc.metadata:
                                    doc.metadata["cubo_source"] = cubo
                                if "ambito" not in doc.metadata and ambito:
                                    doc.metadata["ambito"] = ambito
                                relevant_docs.append(doc)
                        
                        # Si no hay documentos relevantes, usar todos los documentos del cubo
                        if not relevant_docs and docs:
                            print(f"No se encontraron documentos relevantes en el cubo {cubo}. Usando todos los documentos recuperados.")
                            for doc in docs:
                                # Añadir metadatos sobre el cubo y ámbito si no existen
                                if "cubo_source" not in doc.metadata:
                                    doc.metadata["cubo_source"] = cubo
                                if "ambito" not in doc.metadata and ambito:
                                    doc.metadata["ambito"] = ambito
                                relevant_docs.append(doc)
                        
                    # Añadir documentos relevantes a la lista
                    all_docs.extend(relevant_docs)
                    
                    # Guardar detalles de este cubo
                    retrieval_details[cubo] = {
                        "count": len(docs),
                        "relevant_count": len(relevant_docs),
                    "ambito": ambito,
                        "first_doc_snippet": relevant_docs[0].page_content[:100] + "..." if relevant_docs else "No documents retrieved"
                    }
                        
                except Exception as e:
                    print(f"Error al recuperar documentos del cubo {cubo}: {str(e)}")
        
        # Limitar el número total de documentos para evitar tokens excesivos
        max_docs = VECTORSTORE_CONFIG.get("max_docs_total", 10)
        if len(all_docs) > max_docs:
            print(f"Limitando a {max_docs} documentos (de {len(all_docs)} recuperados)")
            all_docs = all_docs[:max_docs]
        
        print("=== FIN DE RECUPERACIÓN DE DOCUMENTOS ===\n")
        
        return {
            "documents": all_docs,
            "question": question,
            "rewritten_question": rewritten_question,
            "retry_count": retry_count,
            "relevant_cubos": state.get("relevant_cubos", []),
            "ambito": ambito,
            "retrieval_details": retrieval_details
        }
        
    # Función auxiliar para recuperar documentos de la colección unificada
    def retrieve_from_unified(state):
        """
        Recupera documentos de la colección unificada como fallback.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con los documentos recuperados.
        """
        question = state["question"]
        rewritten_question = state.get("rewritten_question", question)  # Usar pregunta reescrita si existe, sino la original
        retry_count = state.get("retry_count", 0)
        ambito = state.get("ambito")
        
        try:
            # Usar el retriever unificado sin filtros
            docs = retrievers["unified"].invoke(rewritten_question)
            
            # Procesar los documentos recuperados
            print(f"Documentos recuperados de la colección unificada (sin filtros): {len(docs)}")
            
            # Filtrar por relevancia
            relevant_docs = []
            for doc in docs:
                relevance = retrieval_grader.invoke({
                    "document": doc.page_content,
                    "question": rewritten_question
                })
                
                if isinstance(relevance, dict) and relevance.get("score", "").lower() == "yes":
                    relevant_docs.append(doc)
                
            # Si no hay documentos relevantes, usar todos
            if not relevant_docs and docs:
                relevant_docs = docs
            
            retrieval_details = {
                "unified": {
                    "count": len(docs),
                    "relevant_count": len(relevant_docs),
                    "ambito": ambito,
                    "first_doc_snippet": relevant_docs[0].page_content[:100] + "..." if relevant_docs else "No documents retrieved"
                }
            }
            
            # Limitar el número total de documentos
            max_docs = VECTORSTORE_CONFIG.get("max_docs_total", 10)
            if len(relevant_docs) > max_docs:
                relevant_docs = relevant_docs[:max_docs]
            
            return {
                "documents": relevant_docs,
                "question": question,
                "rewritten_question": rewritten_question,
                "retry_count": retry_count,
                "relevant_cubos": state.get("relevant_cubos", []),
                "ambito": ambito,
                "retrieval_details": retrieval_details
            }
            
        except Exception as e:
            print(f"Error en retrieve_from_unified: {str(e)}")
            return {
                "documents": [],
                "question": question,
                "rewritten_question": rewritten_question,
                "retry_count": retry_count,
                "relevant_cubos": state.get("relevant_cubos", []),
                "ambito": ambito,
                "retrieval_details": {"unified": {"error": str(e)}}
            }
    
    def generate(state):
        """
        Genera una respuesta basada en los documentos recuperados.
        Puede generar una consulta SQL si el sistema determina que es una consulta a base de datos.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con la respuesta generada.
        """
        documents = state["documents"]
        question = state["question"]
        rewritten_question = state.get("rewritten_question", question)  # Usar pregunta reescrita si existe, sino la original
        retry_count = state.get("retry_count", 0)
        relevant_cubos = state.get("relevant_cubos", [])
        retrieval_details = state.get("retrieval_details", {})
        is_consulta = state.get("is_consulta", False)
        
        print("---GENERATE---")
        if not documents:
            print("No se encontraron documentos relevantes.")
            response_json = "No se encontró información relevante en SEGEDA para responder a esta pregunta."
            return {
                "documents": documents,
                "question": question,
                "rewritten_question": rewritten_question,
                "generation": response_json,
                "retry_count": retry_count,
                "hallucination_score": None,
                "answer_score": None,
                "relevant_cubos": relevant_cubos,
                "ambito": state.get("ambito"),
                "retrieval_details": retrieval_details,
                "sql_query": None,
                "sql_result": None
            }
        
        try:
            print("Creando contexto a partir de los documentos recuperados...")
            # Crear contexto a partir de los documentos
            context_docs = []
            for idx, doc in enumerate(documents):
                doc_source = doc.metadata.get('cubo_source', 'Desconocido')
                doc_id = doc.metadata.get('doc_id', f'doc_{idx}')
                
                # Usar el contexto generado si está disponible, de lo contrario usar el contenido original
                doc_content = doc.page_content
                generated_context = doc.metadata.get('context_generation', '')
                
                # Si existe context_generation y no está vacío, añadirlo antes del contenido
                context_info = ""
                if generated_context.strip():
                    context_info = f"\n[CONTEXTO: {generated_context}]\n"
                
                # Crear string con la info del documento
                doc_string = f"\n[DOCUMENTO {idx+1} - {doc_source} - ID: {doc_id}]{context_info}\n{doc_content}\n"
                context_docs.append(doc_string)
            
            context = "\n".join(context_docs)
            
            print("Generando respuesta...")
            
            # Determinar si usar SQL o RAG basado en si es una consulta
            if is_consulta and rag_sql_chain:
                print("Se detectó que es una consulta SQL. Generando consulta SQL...")
                # Generar consulta SQL utilizando sql_query_chain
                sql_query = rag_sql_chain["sql_query_chain"].invoke({
                    "context": context,
                    "question": rewritten_question
                })
                
                # Guardar la consulta SQL generada
                state["sql_query"] = sql_query
                print(f"Consulta SQL generada: {sql_query}")
                
                # La respuesta será generada después con el resultado de la consulta SQL
                response_json = sql_query
            else:
                # Usar la cadena RAG estándar para preguntas regulares
                print("Generando respuesta con RAG estándar...")
                response = rag_chain.invoke({
                    "context": context,
                    "question": rewritten_question
                })
                
                # La respuesta es un string
                if not isinstance(response, str):
                    print(f"Advertencia: La respuesta no es un string: {type(response)}")
                    response_json = str(response)
                else:
                    response_json = response
            
            # Evaluar la respuesta solo si no es una consulta SQL
            if not is_consulta or not rag_sql_chain:
                print("Evaluando si la respuesta contiene alucinaciones...")
                # Verificar si la respuesta contiene alucinaciones
                hallucination_eval = hallucination_grader.invoke({
                    "documents": context,
                    "generation": response_json
                })
                
                if isinstance(hallucination_eval, dict) and "score" in hallucination_eval:
                    is_grounded = hallucination_eval["score"].lower() == "yes"
                    print(f"¿Respuesta fundamentada en los documentos? {'Sí' if is_grounded else 'No'}")
                else:
                    print(f"Advertencia: Evaluación de alucinaciones no válida: {hallucination_eval}")
                    is_grounded = True  # Por defecto, asumir que está fundamentada
                
                print("Evaluando calidad de la respuesta...")
                # Verificar si la respuesta es útil
                answer_eval = answer_grader.invoke({
                    "generation": response_json,
                    "question": rewritten_question
                })
                
                if isinstance(answer_eval, dict) and "score" in answer_eval:
                    is_useful = answer_eval["score"].lower() == "yes"
                    print(f"¿Respuesta útil para la pregunta? {'Sí' if is_useful else 'No'}")
                else:
                    print(f"Advertencia: Evaluación de utilidad no válida: {answer_eval}")
                    is_useful = True  # Por defecto, asumir que es útil
            else:
                # Para consultas SQL, asumimos que son útiles y fundamentadas
                is_grounded = True
                is_useful = True
                hallucination_eval = {"score": "yes"}
                answer_eval = {"score": "yes"}
            
            # Función auxiliar para extraer el valor del "score" de la respuesta
            def extract_score(response) -> bool:
                if isinstance(response, dict) and "score" in response:
                    return response["score"].lower() == "yes"
                return True  # Por defecto, asumimos que es válido
        
        except Exception as e:
            print(f"Error al generar respuesta: {str(e)}")
            response_json = f"Se produjo un error al generar la respuesta: {str(e)}"
            is_grounded = False
            is_useful = False
            hallucination_eval = None
            answer_eval = None
        
        # Si la generación no es exitosa, incrementar contador de reintentos
        if not (is_grounded and is_useful):
            retry_count += 1
            print(f"---RETRY ATTEMPT {retry_count}---")
        
        return {
            "documents": context_docs,
            "question": question,
            "rewritten_question": rewritten_question,
            "generation": response_json,
            "retry_count": retry_count,
            "hallucination_score": hallucination_eval,
            "answer_score": answer_eval,
            "relevant_cubos": relevant_cubos,
            "ambito": state.get("ambito"),
            "retrieval_details": retrieval_details,
            "sql_query": state.get("sql_query"),
            "sql_result": state.get("sql_result")
        }
    
    # Añadir nodos al grafo
    workflow.add_node("route_question", route_question)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate)
    workflow.add_node("execute_query", execute_query)
    
    # Definir bordes - flujo simplificado
    workflow.set_entry_point("route_question")
    workflow.add_edge("route_question", "retrieve")
    workflow.add_edge("retrieve", "generate")
    
    # Definir condición para ejecución de consulta SQL o verificación de reintento
    def route_after_generate(state):
        """
        Determina qué hacer después de generar la respuesta:
        - Ejecutar SQL si es una consulta
        - Reintentar si la respuesta no es buena
        - Finalizar si todo está bien
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            str: Siguiente nodo a ejecutar
        """
        # Verificar si es una consulta SQL
        is_consulta = state.get("is_consulta", False)
        sql_query = state.get("sql_query")
        
        if is_consulta and sql_query:
            print("Se detectó una consulta SQL válida. Procediendo a ejecutarla.")
            return "execute_query"
        
        # Si no es consulta, verificar si necesita reintento
        retry_count = state.get("retry_count", 0)
        hallucination_score = state.get("hallucination_score")
        answer_score = state.get("answer_score")
        
        # Función para extraer score de diferentes formatos
        def extract_score(response):
            if isinstance(response, dict) and "score" in response:
                value = str(response["score"]).lower().strip()
                return value == "yes" or value == "true" or value == "1"
            return False
        
        # Determinar si hay problemas con la generación
        is_hallucination = not extract_score(hallucination_score) if hallucination_score else False
        is_unhelpful = not extract_score(answer_score) if answer_score else False
        
        # Lógica de reintento
        max_retries = WORKFLOW_CONFIG.get("max_retries", 2)
        should_retry = (is_hallucination or is_unhelpful) and retry_count < max_retries
        
        if should_retry:
            print(f"Reintentando (intento {retry_count+1}/{max_retries})")
            print(f"- Contiene alucinaciones: {is_hallucination}")
            print(f"- No aborda adecuadamente la pregunta: {is_unhelpful}")
            return "retrieve"
        else:
            if retry_count >= max_retries and (is_hallucination or is_unhelpful):
                print(f"Máximo de reintentos alcanzado ({max_retries}). Finalizando con la mejor respuesta disponible.")
            else:
                print("Generación exitosa. Finalizando.")
            return "END"
    
    # Añadir borde condicional para la decisión después de generar
    workflow.add_conditional_edges(
        "generate",
        route_after_generate,
        {
            "execute_query": "execute_query",
            "retrieve": "retrieve",
            "END": END
        }
    )
    
    # Añadir borde desde execute_query a END
    workflow.add_edge("execute_query", END)
    
    return workflow
