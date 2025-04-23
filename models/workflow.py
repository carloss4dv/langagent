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
from langagent.models.constants import (
    AMBITOS_CUBOS, CUBO_TO_AMBITO, AMBITO_KEYWORDS, 
    AMBITO_EN_ES, CUBO_EN_ES
)

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
    retrieved_documents: List[Document]
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
        print(f"Cubos relevantes: {state.get('relevant_cubos', [])}")
        
        question = state["question"]
        retry_count = state.get("retry_count", 0)
        ambito = state.get("ambito")
        relevant_cubos = state.get("relevant_cubos", [])
        
        # Obtener el tipo de vectorstore de la configuración
        from langagent.config.config import VECTORSTORE_CONFIG
        vector_db_type = VECTORSTORE_CONFIG.get("vector_db_type", "chroma")
        use_single_collection = VECTORSTORE_CONFIG.get("use_single_collection", True)
        
        all_docs = []
        retrieval_details = {}
        
        if use_single_collection and "unified" in retrievers:
            # Enfoque de colección única con filtrado por metadatos
            print("\n=== Usando colección única con filtrado por metadatos ===")
            
            # Crear filtros de metadatos basados en el ámbito y cubo identificados
            metadata_filters = {}
            
            # Si tenemos un ámbito identificado, usarlo como filtro
            if ambito:
                print(f"Filtrando por ámbito: {ambito}")
                metadata_filters["ambito"] = ambito
            
            # Si tenemos un cubo específico identificado (sólo uno), usarlo como filtro
            cubo_identificado = None
            if relevant_cubos and len(relevant_cubos) == 1 and relevant_cubos[0] != "unified":
                cubo = relevant_cubos[0]
                if not cubo.startswith("consultas_"):  # Evitar duplicar filtros de consultas
                    print(f"Filtrando por cubo específico: {cubo}")
                    metadata_filters["cubo_source"] = cubo
                    cubo_identificado = cubo
            
            # Si es una consulta guardada, añadir ese filtro
            if state.get("is_consulta", False):
                print("Filtrando por consultas guardadas")
                metadata_filters["is_consulta"] = "true"
            
            try:
                # Obtener el retriever unificado
                unified_retriever = retrievers["unified"]
                
                # Verificar si tenemos filtros para aplicar
                if metadata_filters:
                    print(f"Aplicando filtros: {metadata_filters}")
                    # Recuperar documentos aplicando los filtros de metadatos directamente
                    docs = unified_retriever.invoke(question, filter=metadata_filters)
                else:
                    print("No hay filtros para aplicar, recuperando sin filtros")
                    docs = unified_retriever.invoke(question)
                
                print(f"Documentos recuperados: {len(docs)}")
                
                # Si no hay documentos con el filtro por cubo, intentar solo con el ámbito
                if not docs and "cubo_source" in metadata_filters:
                    print(f"No se encontraron documentos para el cubo {metadata_filters['cubo_source']}. Intentando solo con ámbito.")
                    metadata_filters_ambito = {k: v for k, v in metadata_filters.items() if k != "cubo_source"}
                    if metadata_filters_ambito:
                        print(f"Aplicando filtros de ámbito: {metadata_filters_ambito}")
                        docs = unified_retriever.invoke(question, filter=metadata_filters_ambito)
                        print(f"Documentos recuperados con filtro de ámbito: {len(docs)}")
                
                # Si aún no hay documentos, intentar sin filtros como fallback
                if not docs and metadata_filters:
                    print("No se encontraron documentos con filtros. Intentando sin filtros...")
                    docs = unified_retriever.invoke(question)
                    print(f"Documentos recuperados sin filtros: {len(docs)}")
                
                # Filtrar documentos por relevancia usando el evaluador
                relevant_docs = []
                for doc in docs:
                    # Comentando el código de evaluación de relevancia
                    # relevance = retrieval_grader.invoke({
                    #     "document": doc.page_content,
                    #     "question": question
                    # })
                    
                    # # Extraer score de la respuesta del evaluador
                    # if isinstance(relevance, dict) and "score" in relevance:
                    #     is_relevant = relevance["score"].lower() == "yes"
                    # else:
                    #     # Por defecto, considerar el documento como relevante
                    #     is_relevant = True
                    
                    # Considerar todos los documentos como relevantes
                    is_relevant = True
                    
                    if is_relevant:
                        # Asegurar que tenga los metadatos correctos
                        if cubo_identificado and "cubo_source" not in doc.metadata:
                            doc.metadata["cubo_source"] = cubo_identificado
                        if ambito and "ambito" not in doc.metadata:
                            doc.metadata["ambito"] = ambito
                        relevant_docs.append(doc)
                
                # Si no hay documentos relevantes, usar todos los documentos
                if not relevant_docs and docs:
                    print(f"No se encontraron documentos relevantes. Usando todos los documentos recuperados.")
                    for doc in docs:
                        # Asegurar que tenga los metadatos correctos
                        if cubo_identificado and "cubo_source" not in doc.metadata:
                            doc.metadata["cubo_source"] = cubo_identificado
                        if ambito and "ambito" not in doc.metadata:
                            doc.metadata["ambito"] = ambito
                        relevant_docs.append(doc)
                
                retrieval_details["unified"] = {
                    "count": len(docs),
                    "relevant_count": len(relevant_docs),
                    "ambito": ambito,
                    "cubo": cubo_identificado,
                    "first_doc_snippet": relevant_docs[0].page_content[:100] + "..." if relevant_docs else "No documents retrieved"
                }
                
                all_docs.extend(relevant_docs)
                print(f"Documentos relevantes: {len(relevant_docs)}")
                
            except Exception as e:
                print(f"\nERROR al recuperar documentos de la colección unificada:")
                print(f"Tipo de error: {type(e).__name__}")
                print(f"Mensaje de error: {str(e)}")
                retrieval_details["unified"] = {
                    "count": 0,
                    "relevant_count": 0,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                
        else:
            # Enfoque con múltiples colecciones/retrievers
            # Determinar los cubos a consultar
            cubos_a_consultar = []
            
            # Si tenemos cubos relevantes específicos, usarlos
            if relevant_cubos and any(cubo != "unified" for cubo in relevant_cubos):
                cubos_a_consultar = [cubo for cubo in relevant_cubos if cubo != "unified" and cubo in retrievers]
                print(f"\nUsando cubos relevantes identificados específicamente:")
                print(f"Cubos a consultar: {cubos_a_consultar}")
            # Si tenemos un ámbito identificado, usar todos sus cubos
            elif ambito and ambito in AMBITOS_CUBOS:
                cubos_a_consultar = [
                    cubo for cubo in AMBITOS_CUBOS[ambito]["cubos"]
                    if cubo in retrievers
                ]
                print(f"\nUsando cubos del ámbito {AMBITOS_CUBOS[ambito]['nombre']}:")
                print(f"Cubos a consultar: {cubos_a_consultar}")
            # Si no tenemos ni ámbito ni cubos específicos, usar todos los retrievers
            else:
                cubos_a_consultar = [cubo for cubo in retrievers.keys() if cubo != "unified"]
                print(f"\nUsando todos los cubos disponibles:")
                print(f"Cubos a consultar: {cubos_a_consultar}")
            
            # Si no hay cubos específicos pero tenemos unified, usarlo
            if not cubos_a_consultar and "unified" in retrievers:
                print("No hay cubos específicos disponibles. Usando retriever unificado.")
                return retrieve_from_unified(state)
            
            # Recuperar documentos de cada cubo relevante
            for cubo in cubos_a_consultar:
                if cubo in retrievers:
                    try:
                        print(f"\nProcesando cubo: {cubo}")
                        
                        retriever = retrievers[cubo]
                        print("Iniciando recuperación de documentos...")
                        
                        # Crear filtros si es necesario (para Milvus)
                        metadata_filters = {}
                        if vector_db_type.lower() == "milvus":
                            if cubo != "unified" and not cubo.startswith("consultas_"):
                                metadata_filters["cubo_source"] = cubo
                            if ambito:
                                metadata_filters["ambito"] = ambito
                            if state.get("is_consulta", False) and cubo.startswith("consultas_"):
                                metadata_filters["is_consulta"] = "true"
                        
                        # Recuperar documentos, con filtros si es Milvus
                        if metadata_filters and vector_db_type.lower() == "milvus":
                            print(f"Aplicando filtros: {metadata_filters}")
                            docs = retriever.invoke(question, filter=metadata_filters)
                        else:
                            docs = retriever.invoke(question)
                        
                        print(f"Documentos recuperados del cubo {cubo}: {len(docs)}")
                        
                        # Filtrar documentos por relevancia usando el evaluador
                        relevant_docs = []
                        for doc in docs:
                            # Comentando el código de evaluación de relevancia
                            # # Evaluar relevancia del documento
                            # relevance = retrieval_grader.invoke({
                            #     "document": doc.page_content,
                            #     "question": question
                            # })
                            
                            # # Extraer score de la respuesta
                            # if isinstance(relevance, dict) and "score" in relevance:
                            #     is_relevant = relevance["score"].lower() == "yes"
                            # else:
                            #     # Por defecto, considerar el documento como relevante
                            #     is_relevant = True
                            
                            # Considerar todos los documentos como relevantes
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
                        
                        retrieval_details[cubo] = {
                            "count": len(docs),
                            "relevant_count": len(relevant_docs),
                            "ambito": ambito or CUBO_TO_AMBITO.get(cubo),
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
        print(f"Detalles por cubo/colección:")
        for key, details in retrieval_details.items():
            print(f"- {key}: {details['count']} documentos recuperados, {details.get('relevant_count', 0)} relevantes")
            if "error" in details:
                print(f"  Error: {details['error']}")
        
        print("=== FIN DE RECUPERACIÓN DE DOCUMENTOS ===\n")
        
        return {
            "documents": all_docs,
            "question": question,
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
        retry_count = state.get("retry_count", 0)
        ambito = state.get("ambito")
        
        try:
            # Usar el retriever unificado sin filtros
            docs = retrievers["unified"].invoke(question)
            
            # Procesar los documentos recuperados
            print(f"Documentos recuperados de la colección unificada (sin filtros): {len(docs)}")
            
            # Filtrar por relevancia
            relevant_docs = []
            for doc in docs:
                # Comentando el código de evaluación de relevancia
                # # Evaluar relevancia del documento
                # relevance = retrieval_grader.invoke({
                #     "document": doc.page_content,
                #     "question": question
                # })
                
                # if isinstance(relevance, dict) and relevance.get("score", "").lower() == "yes":
                #     relevant_docs.append(doc)
                
                # Considerar todos los documentos como relevantes
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
                "retry_count": retry_count,
                "relevant_cubos": state.get("relevant_cubos", []),
                "ambito": ambito,
                "retrieval_details": retrieval_details
            }
            
        except Exception as e:
            print(f"\nERROR al usar retriever unificado como fallback:")
            print(f"Tipo de error: {type(e).__name__}")
            print(f"Mensaje de error: {str(e)}")
            
            return {
                "documents": [],
                "question": question,
                "retry_count": retry_count,
                "relevant_cubos": state.get("relevant_cubos", []),
                "ambito": ambito,
                "retrieval_details": {"unified_fallback": {"count": 0, "error": str(e)}}
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
        formatted_generation = ""
        if isinstance(generation, dict):
            if "answer" in generation:
                formatted_generation = generation["answer"]
            else:
                formatted_generation = str(generation)
        else:
            formatted_generation = str(generation)
        
        # Limpiar y formatear la respuesta
        formatted_generation = formatted_generation.strip()
        
        # Normalizar los saltos de línea para JSON - asegurar que usamos \\n en lugar de \n
        # Primero reemplazamos los saltos de línea escapados por un marcador temporal
        formatted_generation = formatted_generation.replace('\\n', '[NEWLINE]')
        
        # Reemplazar los saltos de línea reales por la secuencia \\n para JSON
        formatted_generation = formatted_generation.replace('\n', '\\n')
        
        # Eliminar espacios múltiples
        formatted_generation = re.sub(r'\s+', ' ', formatted_generation)
        
        # Restaurar los marcadores temporales
        formatted_generation = formatted_generation.replace('[NEWLINE]', '\\n')
        
        # Crear un objeto JSON para la respuesta
        response_json = {"answer": formatted_generation}
        
        # Si la generación no es exitosa, incrementar contador de reintentos
        if not (is_grounded and is_useful):
            retry_count += 1
            print(f"---RETRY ATTEMPT {retry_count}---")
        
        return {
            "documents": documents,
            "question": question,
            "generation": response_json,  # Devolver el objeto JSON completo
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
