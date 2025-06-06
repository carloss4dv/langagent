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
    AMBITO_EN_ES, CUBO_EN_ES, CHUNK_STRATEGIES, DEFAULT_CHUNK_STRATEGY,
    MAX_RETRIES, EVALUATION_THRESHOLDS, COLLECTION_CONFIG
)
from langagent.models.metrics_collector import MetricsCollector

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

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
        hallucination_score: puntuación de alucinaciones (DEPRECATED - usar evaluation_metrics)
        answer_score: puntuación de la respuesta (DEPRECATED - usar evaluation_metrics)
        relevant_cubos: lista de cubos relevantes para la pregunta
        ambito: ámbito identificado para la pregunta
        retrieval_details: detalles de recuperación por cubo
        is_consulta: indica si la pregunta es sobre una consulta guardada o SQL
        consulta_documents: documentos de consultas guardadas recuperados
        sql_query: consulta SQL generada
        sql_result: resultado de la consulta SQL
        needs_sql_interpretation: indica si se necesita generar interpretación de resultados SQL
        chunk_strategy: estrategia de chunk actual (256, 512, 1024)
        evaluation_metrics: métricas granulares del evaluador
    """
    question: str
    rewritten_question: str
    generation: str
    documents: List[Document]
    retrieved_documents: List[Document]
    retry_count: int
    hallucination_score: Optional[str]  # DEPRECATED
    answer_score: Optional[str]  # DEPRECATED
    relevant_cubos: List[str]
    ambito: Optional[str]
    retrieval_details: Dict[str, Dict[str, Any]]
    is_consulta: bool
    consulta_documents: List[Document]
    sql_query: Optional[str]
    sql_result: Optional[str]
    needs_sql_interpretation: bool
    chunk_strategy: str  # Nuevo campo para recuperación adaptativa
    evaluation_metrics: Dict[str, Any]  # Nuevo campo para métricas granulares

def extract_chunk_strategy_from_name(name: str) -> str:
    """
    Extrae la estrategia de chunk del nombre de la colección/retriever.
    
    Args:
        name (str): Nombre que debe contener _256, _512, o _1024
        
    Returns:
        str: Estrategia de chunk ("256", "512", "1024")
        
    Raises:
        ValueError: Si no se encuentra un patrón válido de estrategia
    """
    if not name:
        raise ValueError("El nombre no puede estar vacío")
    
    # Buscar patrón _XXX donde XXX es 256, 512, o 1024
    import re
    pattern = r'_(256|512|1024)'
    match = re.search(pattern, name)
    
    if match:
        strategy = match.group(1)
        logger.info(f"Estrategia extraída del nombre '{name}': {strategy} tokens")
        return strategy
    else:
        raise ValueError(f"No se encontró un patrón válido de estrategia (_256, _512, _1024) en el nombre: '{name}'")

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

def validate_and_clean_context(context, question):
    """
    Valida y limpia el contexto para asegurar que es un string válido antes de pasarlo a las cadenas RAG.
    
    Args:
        context: Contexto a validar y limpiar
        question: Pregunta a validar
        
    Returns:
        Tuple[str, str]: (contexto limpio, pregunta limpia)
    """
    logger.debug(f"ENTRADA validate_and_clean_context - context type: {type(context)}, question type: {type(question)}")
    
    # Asegurar que el contexto es un string
    if isinstance(context, dict):
        logger.warning(f"Contexto es un diccionario, convirtiendo a string. Claves: {list(context.keys())}")
        logger.debug(f"Contenido del diccionario de contexto: {context}")
        if "context" in context:
            context = context["context"]
            logger.debug(f"Extraído contexto de clave 'context': {type(context)}")
        else:
            context = str(context)
            logger.warning("No se encontró clave 'context', convirtiendo diccionario completo a string")
    elif isinstance(context, list):
        logger.warning("Contexto es una lista, uniendo elementos")
        context = "\n".join([str(item) for item in context])
    elif not isinstance(context, str):
        logger.warning(f"Contexto tiene tipo inesperado {type(context)}, convirtiendo a string")
        logger.debug(f"Valor del contexto no-string: {context}")
        context = str(context)
    
    # Asegurar que la pregunta es un string
    if isinstance(question, dict):
        logger.warning(f"Pregunta es un diccionario, extrayendo. Claves: {list(question.keys())}")
        logger.debug(f"Contenido del diccionario de pregunta: {question}")
        if "question" in question:
            question = question["question"]
            logger.debug(f"Extraída pregunta de clave 'question': {type(question)}")
        else:
            question = str(question)
            logger.warning("No se encontró clave 'question', convirtiendo diccionario completo a string")
    elif not isinstance(question, str):
        logger.warning(f"Pregunta tiene tipo inesperado {type(question)}, convirtiendo a string")
        logger.debug(f"Valor de la pregunta no-string: {question}")
        question = str(question)
    
    # Validar que no están vacíos
    if not context.strip():
        logger.warning("Contexto está vacío después de la limpieza")
        context = "No hay contexto disponible."
    
    if not question.strip():
        logger.warning("Pregunta está vacía después de la limpieza")
        question = "¿Qué información necesitas?"
    
    logger.debug(f"SALIDA validate_and_clean_context - context type: {type(context)}, question type: {type(question)}")
    logger.debug(f"Context preview: {context[:100]}...")
    logger.debug(f"Question: {question}")
    
    return context, question

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
    # Obtener la consulta SQL del estado
    sql_query = state.get("sql_query")
    if not sql_query:
        logger.info("No hay consulta SQL para ejecutar.")
        return state
    
    logger.info("---EXECUTE QUERY---")
    
    # Comprobar si sql_query es un string JSON 
    if isinstance(sql_query, str):
        try:
            # Intentar parsear como JSON
            if sql_query.strip().startswith('{'):
                query_data = json.loads(sql_query)
                if isinstance(query_data, dict):
                    # Buscar la consulta en diferentes claves posibles
                    if "query" in query_data:
                        sql_query = query_data["query"]
                        logger.info("Consulta SQL extraída del objeto JSON (clave 'query').")
                    elif "sql" in query_data:
                        sql_query = query_data["sql"]
                        logger.info("Consulta SQL extraída del objeto JSON (clave 'sql').")
        except json.JSONDecodeError:
            # Si no es JSON válido, usar el string como está
            pass
    
    logger.info(f"Ejecutando consulta SQL: {sql_query}")
    
    try:
        # Crear la conexión a la base de datos y herramienta de consulta
        if SQL_CONFIG.get("db_uri"):
            db = SQLDatabase.from_uri(SQL_CONFIG.get("db_uri"))
            execute_query_tool = QuerySQLDatabaseTool(db=db)
            
            # Ejecutar la consulta
            result = execute_query_tool.invoke(sql_query)
            state["sql_result"] = result
            logger.info("Consulta ejecutada con éxito.")
            
        else:
            state["sql_result"] = "Error: No se ha configurado la URI de la base de datos"
            
    except Exception as e:
        error = f"Error al ejecutar la consulta SQL: {str(e)}"
        state["sql_result"] = error
        logger.error(error)
        
    # También notificar si hay problemas de permisos o conexión
    if state.get("sql_result", "").startswith("Error"):
        error = f"Error en la ejecución de la consulta: {state['sql_result']}"
        logger.error(error)
    
    # Marcar que necesita interpretación de resultados SQL
    state["needs_sql_interpretation"] = True
    
    return state

def create_workflow(retriever, retrieval_grader, granular_evaluator, query_rewriter=None, rag_sql_chain=None, sql_interpretation_chain=None, adaptive_retrievers=None, metrics_collector=None, collection_name=None):
    """
    Crea un flujo de trabajo para el agente utilizando LangGraph con recuperación adaptativa y recolección de métricas.
    
    Args:
        retriever: Retriever principal para recuperar documentos.
        retrieval_grader: Evaluador de relevancia de documentos.
        granular_evaluator: Evaluador granular que reemplaza hallucination_grader y answer_grader.
        query_rewriter: Reescritor de consultas para mejorar la recuperación.
        rag_sql_chain: Cadena para consultas SQL cuando se detecta que es una consulta de base de datos.
        sql_interpretation_chain: Cadena para generar interpretación de resultados SQL.
        adaptive_retrievers: Diccionario de retrievers por estrategia {"256": retriever, "512": retriever, "1024": retriever}.
        metrics_collector: Recolector de métricas para análisis de rendimiento.
        collection_name: Nombre de la colección para extraer la estrategia inicial (debe contener _256, _512, o _1024).
        
    Returns:
        StateGraph: Grafo de estado configurado con recuperación adaptativa y métricas.
    """
    # Inicializar el recolector de métricas si no se proporciona
    if metrics_collector is None:
        metrics_collector = MetricsCollector()
    
    # Extraer estrategia inicial del nombre de la colección
    initial_chunk_strategy = DEFAULT_CHUNK_STRATEGY  # Fallback por defecto
    if collection_name:
        try:
            initial_chunk_strategy = extract_chunk_strategy_from_name(collection_name)
            logger.info(f"Estrategia inicial establecida desde el nombre de colección: {initial_chunk_strategy} tokens")
        except ValueError as e:
            logger.error(f"Error al extraer estrategia del nombre de colección: {e}")
            raise e  # Re-lanzar la excepción para que "pete"
    else:
        logger.warning(f"No se proporcionó nombre de colección, usando estrategia por defecto: {initial_chunk_strategy}")
    
    # Definimos el grafo de estado
    workflow = StateGraph(GraphState)
    
    def retrieve(state):
        """
        Recupera documentos relevantes para la pregunta.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con los documentos recuperados.
        """
        # Iniciar medición del nodo
        node_context = metrics_collector.start_node("retrieve")
        
        question = state["question"]
        rewritten_question = state.get("rewritten_question", question)
        retry_count = state.get("retry_count", 0)
        ambito = state.get("ambito")
        is_consulta = state.get("is_consulta", False)
        chunk_strategy = state.get("chunk_strategy", DEFAULT_CHUNK_STRATEGY)
        
        logger.info("---RETRIEVE---")
        logger.info(f"Búsqueda con pregunta: {rewritten_question}")
        logger.info(f"Ámbito identificado: {ambito}")
        logger.info(f"Estrategia de chunk: {chunk_strategy} tokens")
        logger.info(f"Intento número: {retry_count + 1} (retry_count actual: {retry_count})")
        
        try:
            # Seleccionar retriever según la estrategia
            current_retriever = retriever  # Fallback al retriever principal
            if adaptive_retrievers and chunk_strategy in adaptive_retrievers:
                current_retriever = adaptive_retrievers[chunk_strategy]
                logger.info(f"Usando retriever adaptativo para chunks de {chunk_strategy} tokens")
            elif adaptive_retrievers:
                logger.info(f"Usando retriever principal (estrategia {chunk_strategy} no disponible en retrievers adaptativos)")
            else:
                logger.info(f"Usando retriever principal (recuperación adaptativa deshabilitada)")
            
            # Preparar filtros si hay ámbito identificado
            filters = {}
            if ambito:
                filters["ambito"] = ambito
            if is_consulta:
                filters["is_consulta"] = "true"
            
            vector_db_type = VECTORSTORE_CONFIG.get("vector_db_type", "chroma")
            
            # Solo aplicar filtros si no es Chroma
            if vector_db_type.lower() == "chroma" and filters:
                logger.info(f"⚠️  Vector DB es Chroma - filtros omitidos para mejor compatibilidad: {filters}")
                docs = current_retriever.invoke(rewritten_question)
            elif filters:
                logger.info(f"Aplicando filtros para {vector_db_type}: {filters}")
                docs = current_retriever.invoke(rewritten_question, filter=filters)
            else:
                docs = current_retriever.invoke(rewritten_question)
                
            logger.info(f"Documentos recuperados: {len(docs)}")
            
            # Limitar el número total de documentos
            max_docs = VECTORSTORE_CONFIG.get("max_docs_total", 10)
            if len(docs) > max_docs:
                logger.info(f"Limitando a {max_docs} documentos (de {len(docs)} recuperados)")
                docs = docs[:max_docs]
            
            retrieval_details = {
                "count": len(docs),
                "ambito": ambito,
                "first_doc_snippet": docs[0].page_content[:100] + "..." if docs else "No documents retrieved"
            }
            
            result_state = {
                "documents": docs,
                "question": question,
                "rewritten_question": rewritten_question,
                "retry_count": retry_count,
                "ambito": ambito,
                "retrieval_details": retrieval_details,
                "chunk_strategy": chunk_strategy
            }
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=True)
            
            return result_state
            
        except Exception as e:
            logger.error(f"Error al recuperar documentos: {str(e)}")
            error_state = {
                "documents": [],
                "question": question,
                "rewritten_question": rewritten_question,
                "retry_count": retry_count,
                "ambito": ambito,
                "retrieval_details": {"error": str(e)},
                "chunk_strategy": chunk_strategy
            }
            
            # Finalizar medición del nodo con error
            metrics_collector.end_node(node_context, error_state, success=False)
            
            return error_state

    def grade_relevance(state):
        """
        Evalúa la relevancia de los documentos recuperados.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con los documentos relevantes.
        """
        # Iniciar medición del nodo
        node_context = metrics_collector.start_node("grade_relevance")
        
        logger.info("---GRADE RELEVANCE---")
        
        documents = state["documents"]
        question = state["question"]
        ambito = state["ambito"]
        rewritten_question = state.get("rewritten_question", question)
        retrieval_details = state.get("retrieval_details", {})
        
        # BYPASS TEMPORAL: Saltar grading si hay problemas con el retrieval_grader
        BYPASS_GRADING = False  # Cambiar a False cuando el retrieval_grader funcione correctamente
        
        if BYPASS_GRADING:
            logger.warning("BYPASS activado: Saltando evaluación de relevancia, usando todos los documentos")
            retrieval_details.update({
                "relevant_count": len(documents),
                "relevance_checked": False,
                "bypass_used": True
            })
            
            result_state = {
                **state,
                "documents": documents,
                "retrieval_details": retrieval_details
            }
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=True)
            
            return result_state
        
        try:
            # Comprobar si los documentos son relevantes
            relevant_docs = []
            logger.info(f"Evaluando relevancia de {len(documents)} documentos...")
            
            for idx, doc in enumerate(documents):
                logger.info(f"Evaluando documento {idx + 1}/{len(documents)}")
                
                try:
                    document_data = {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "source": doc.metadata.get("source", "unknown")
                    }
                    
                    # Añadir timeout/protección para evitar recursión infinita
                    logger.debug(f"Llamando a retrieval_grader para documento {idx + 1}")
                    
                    relevance = retrieval_grader.invoke({
                        "content": document_data["content"],
                        "metadata": str(document_data["metadata"]),
                        "source": document_data["source"],
                        "question": question,
                        "ambito": ambito,
                    })
                    
                    logger.debug(f"Relevancia evaluada para documento {idx + 1}: {relevance}")
                    
                    if isinstance(relevance, dict) and relevance.get("score", "").lower() == "yes":
                        relevant_docs.append(doc)
                        logger.debug(f"Documento {idx + 1} marcado como relevante")
                    else:
                        logger.debug(f"Documento {idx + 1} marcado como no relevante")
                        
                except Exception as doc_error:
                    logger.error(f"Error al evaluar relevancia del documento {idx + 1}: {str(doc_error)}")
                    # En caso de error, incluir el documento (enfoque conservativo)
                    relevant_docs.append(doc)
                    logger.info(f"Documento {idx + 1} incluido por defecto debido a error en evaluación")
            
            # Si no hay documentos relevantes, usar todos
            if not relevant_docs and documents:
                logger.info("No se encontraron documentos relevantes. Usando todos los documentos recuperados.")
                relevant_docs = documents
            
            # Actualizar detalles de recuperación
            retrieval_details.update({
                "relevant_count": len(relevant_docs),
                "relevance_checked": True
            })
            
            result_state = {
                **state,
                "documents": relevant_docs,
                "retrieval_details": retrieval_details
            }
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=True)
            
            return result_state
            
        except Exception as e:
            logger.error(f"Error al evaluar relevancia: {str(e)}")
            error_state = {
                **state,
                "retrieval_details": {
                    **retrieval_details,
                    "relevance_error": str(e)
                }
            }
            
            # Finalizar medición del nodo con error
            metrics_collector.end_node(node_context, error_state, success=False)
            
            return error_state
    
    def generate(state):
        """
        Genera una respuesta basada en los documentos recuperados.
        Puede generar una consulta SQL si el sistema determina que es una consulta a base de datos.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con la respuesta generada.
        """
        # Iniciar medición del nodo
        node_context = metrics_collector.start_node("generate")
        
        documents = state["documents"]
        question = state["question"]
        rewritten_question = state.get("rewritten_question", question)
        retry_count = state.get("retry_count", 0)
        relevant_cubos = state.get("relevant_cubos", [])
        retrieval_details = state.get("retrieval_details", {})
        is_consulta = state.get("is_consulta", False)
        
        logger.info("---GENERATE---")
        if not documents:
            logger.info("No se encontraron documentos relevantes.")
            response_json = "No se encontró información relevante en SEGEDA para responder a esta pregunta."
            result_state = {
                "documents": documents,
                "question": question,
                "rewritten_question": rewritten_question,
                "generation": response_json,
                "retry_count": retry_count,
                "relevant_cubos": relevant_cubos,
                "ambito": state.get("ambito"),
                "retrieval_details": retrieval_details,
                "sql_query": None,
                "sql_result": None
            }
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=True)
            
            return result_state
        
        try:
            logger.info("Creando contexto a partir de los documentos recuperados...")
            # Crear contexto a partir de los documentos
            context_docs = []
            for idx, doc in enumerate(documents):
                # Verificar si doc es un Document o un string
                if isinstance(doc, str):
                    # Si es un string, usarlo directamente como contexto
                    doc_string = f"\n[DOCUMENTO {idx+1} - Contenido de reintento]\n{doc}\n"
                    context_docs.append(doc_string)
                elif hasattr(doc, 'metadata') and hasattr(doc, 'page_content'):
                    # Si es un Document válido, procesar normalmente
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
                else:
                    # Si no es ni string ni Document válido, convertir a string
                    logger.warning(f"Advertencia: Documento {idx+1} tiene tipo inesperado: {type(doc)}")
                    doc_string = f"\n[DOCUMENTO {idx+1} - Tipo inesperado]\n{str(doc)}\n"
                    context_docs.append(doc_string)
            
            # Crear el contexto completo como string
            context = "\n".join(context_docs)
            
            # Validar y limpiar el contexto y la pregunta
            clean_context, clean_question = validate_and_clean_context(context, rewritten_question)
            
            logger.info("Generando respuesta...")
            logger.info(f"Tamaño del contexto: {len(clean_context)} caracteres")
            logger.info(f"Pregunta reescrita: {clean_question}")
            
            # DEBUG: Mostrar una muestra del contexto para debug
            logger.debug(f"Muestra del contexto limpio (primeros 500 caracteres): {clean_context[:500]}")
            logger.debug(f"Tipo del contexto: {type(clean_context)}")
            logger.debug(f"Tipo de la pregunta: {type(clean_question)}")
            
            # Determinar si usar SQL o RAG basado en si es una consulta
            if is_consulta and rag_sql_chain:
                logger.info("Se detectó que es una consulta SQL. Generando consulta SQL...")
                # Generar consulta SQL utilizando sql_query_chain
                
                # Asegurar que se pasan los parámetros correctamente
                sql_input = {
                    "context": clean_context,
                    "question": clean_question
                }
                logger.info(f"Input para SQL query chain: context length={len(clean_context)}, question='{clean_question}'")
                
                sql_query = rag_sql_chain["sql_query_chain"].invoke(sql_input)
                
                # Guardar la consulta SQL generada
                state["sql_query"] = sql_query
                logger.info(f"Consulta SQL generada: {sql_query}")
                
                # La respuesta será generada después con el resultado de la consulta SQL
                response_json = sql_query
            else:
                # Usar la cadena RAG estándar para preguntas regulares
                logger.info("Generando respuesta con RAG estándar...")
                
                # Asegurar que se pasan los parámetros correctamente
                rag_input = {
                    "context": clean_context,
                    "question": clean_question
                }
                logger.info(f"Input para RAG chain: context length={len(clean_context)}, question='{clean_question}'")
                logger.debug(f"DEBUGGING RAG INPUT - Estructura completa del diccionario: {rag_input}")
                logger.debug(f"DEBUGGING RAG INPUT - Tipo de context: {type(clean_context)}")
                logger.debug(f"DEBUGGING RAG INPUT - Tipo de question: {type(clean_question)}")
                logger.debug(f"DEBUGGING RAG INPUT - Context preview (primeros 200 caracteres): {clean_context[:200]}")
                
                # Verificar que no hay anidamiento incorrecto
                if isinstance(clean_context, dict) or isinstance(clean_question, dict):
                    logger.error(f"ERROR: Después de limpieza, aún hay diccionarios anidados!")
                    logger.error(f"clean_context type: {type(clean_context)}, clean_question type: {type(clean_question)}")
                    raise ValueError("Contexto o pregunta aún contienen estructuras anidadas después de la limpieza")
                
                response = rag_sql_chain["answer_chain"].invoke(rag_input)
                
                # Extraer solo el campo answer si la respuesta es un diccionario
                if isinstance(response, dict) and "answer" in response:
                    response_json = response["answer"]
                elif isinstance(response, str):
                    response_json = response
                else:
                    logger.warning(f"Advertencia: Formato de respuesta no esperado: {type(response)}")
                    logger.warning(f"Respuesta completa: {response}")
                    response_json = str(response)
            
            logger.info(f"Respuesta generada exitosamente: {response_json[:100]}...")
            
            result_state = {
                "documents": context_docs,
                "question": question,
                "rewritten_question": clean_question,
                "generation": response_json,
                "retry_count": retry_count,
                "relevant_cubos": relevant_cubos,
                "ambito": state.get("ambito"),
                "retrieval_details": retrieval_details,
                "sql_query": state.get("sql_query"),
                "sql_result": state.get("sql_result")
            }
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=True)
            
            return result_state
            
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}")
            logger.error(f"Tipo de error: {type(e)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            response_json = f"Se produjo un error al generar la respuesta: {str(e)}"
            error_state = {
                "documents": documents,
                "question": question,
                "rewritten_question": rewritten_question,
                "generation": response_json,
                "retry_count": retry_count,
                "relevant_cubos": relevant_cubos,
                "ambito": state.get("ambito"),
                "retrieval_details": retrieval_details,
                "sql_query": None,
                "sql_result": None
            }
            
            # Finalizar medición del nodo con error
            metrics_collector.end_node(node_context, error_state, success=False)
            
            return error_state

    def evaluate_response_granular(state):
        """
        Evalúa la respuesta generada usando múltiples métricas de calidad granular.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con las métricas granulares.
        """
        # Iniciar medición del nodo
        node_context = metrics_collector.start_node("evaluate_response_granular")
        
        logger.info("---EVALUATE RESPONSE GRANULAR---")
        
        generation = state["generation"]
        question = state["question"]
        documents = state["documents"]
        is_consulta = state.get("is_consulta", False)
        
        try:
            # Evaluar la respuesta solo si no es una consulta SQL
            if not is_consulta or not rag_sql_chain:
                logger.info("Ejecutando evaluación granular de la respuesta...")
                
                # Preparar documentos para el evaluador
                docs_text = ""
                if documents:
                    for i, doc in enumerate(documents):
                        if isinstance(doc, str):
                            docs_text += f"[DOCUMENTO {i+1}]: {doc}\n"
                        elif hasattr(doc, 'page_content'):
                            docs_text += f"[DOCUMENTO {i+1}]: {doc.page_content}\n"
                        else:
                            docs_text += f"[DOCUMENTO {i+1}]: {str(doc)}\n"
                
                # Ejecutar evaluación granular
                evaluation_result = granular_evaluator.invoke({
                    "question": question,
                    "documents": docs_text,
                    "generation": generation
                })
                
                if isinstance(evaluation_result, dict):
                    logger.info("Métricas de evaluación granular:")
                    logger.info(f"  - Faithfulness: {evaluation_result.get('faithfulness', 'N/A')}")
                    logger.info(f"  - Context Precision: {evaluation_result.get('context_precision', 'N/A')}")
                    logger.info(f"  - Context Recall: {evaluation_result.get('context_recall', 'N/A')}")
                    logger.info(f"  - Answer Relevance: {evaluation_result.get('answer_relevance', 'N/A')}")
                    
                    evaluation_metrics = evaluation_result
                else:
                    logger.warning(f"Advertencia: Evaluación granular no válida: {evaluation_result}")
                    # Valores por defecto si falla la evaluación
                    evaluation_metrics = {
                        "faithfulness": 0.8,
                        "context_precision": 0.8,
                        "context_recall": 0.8,
                        "answer_relevance": 0.8,
                        "diagnosis": {
                            "faithfulness_reason": "Evaluación fallida - usando valores por defecto",
                            "context_precision_reason": "Evaluación fallida - usando valores por defecto",
                            "context_recall_reason": "Evaluación fallida - usando valores por defecto",
                            "answer_relevance_reason": "Evaluación fallida - usando valores por defecto"
                        }
                    }
            else:
                # Para consultas SQL, asumimos métricas altas
                logger.info("Consulta SQL - usando métricas por defecto altas")
                evaluation_metrics = {
                    "faithfulness": 0.9,
                    "context_precision": 0.9,
                    "context_recall": 0.9,
                    "answer_relevance": 0.9,
                    "diagnosis": {
                        "faithfulness_reason": "Consulta SQL - datos directos de base de datos",
                        "context_precision_reason": "Consulta SQL - contexto directo relevante", 
                        "context_recall_reason": "Consulta SQL - información completa recuperada",
                        "answer_relevance_reason": "Consulta SQL - respuesta directa a la consulta"
                    }
                }
            
            result_state = {
                **state,
                "evaluation_metrics": evaluation_metrics,
                # Mantener compatibilidad con campos legacy (deprecated)
                "hallucination_score": {"score": "yes" if evaluation_metrics.get("faithfulness", 0) >= 0.7 else "no"},
                "answer_score": {"score": "yes" if evaluation_metrics.get("answer_relevance", 0) >= 0.7 else "no"}
            }
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=True)
            
            return result_state
            
        except Exception as e:
            logger.error(f"Error al evaluar respuesta granular: {str(e)}")
            # Valores por defecto en caso de error
            error_state = {
                **state,
                "evaluation_metrics": {
                    "faithfulness": 0.5,
                    "context_precision": 0.5,
                    "context_recall": 0.5,
                    "answer_relevance": 0.5,
                    "diagnosis": {
                        "faithfulness_reason": f"Error en evaluación: {str(e)}",
                        "context_precision_reason": f"Error en evaluación: {str(e)}",
                        "context_recall_reason": f"Error en evaluación: {str(e)}",
                        "answer_relevance_reason": f"Error en evaluación: {str(e)}"
                    }
                },
                "hallucination_score": {"score": "no"},
                "answer_score": {"score": "no"}
            }
            
            # Finalizar medición del nodo con error
            metrics_collector.end_node(node_context, error_state, success=False)
            
            return error_state
    
    def generate_sql_interpretation(state):
        """
        Genera una respuesta interpretativa basada en los resultados de la consulta SQL.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con la respuesta interpretativa.
        """
        # Iniciar medición del nodo
        node_context = metrics_collector.start_node("generate_sql_interpretation")
        
        question = state["question"]
        rewritten_question = state.get("rewritten_question", question)
        sql_query = state.get("sql_query", "")
        sql_result = state.get("sql_result", "")
        documents = state.get("documents", [])
        
        logger.info("---GENERATE SQL INTERPRETATION---")
        
        if not sql_result:
            logger.info("No hay resultados SQL para interpretar.")
            result_state = {
                **state,
                "generation": "No se pudieron obtener resultados de la consulta SQL.",
                "needs_sql_interpretation": False
            }
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=True)
            
            return result_state
        
        try:
            # Crear contexto combinando documentos originales y resultados SQL
            context_parts = []
            
            # Añadir contexto de documentos originales si existen
            if documents:
                context_parts.append("[CONTEXTO ORIGINAL DE SEGEDA]")
                for idx, doc in enumerate(documents[:3]):  # Limitar a 3 documentos
                    if isinstance(doc, str):
                        context_parts.append(f"Documento {idx+1}: {doc[:200]}...")
                    elif hasattr(doc, 'page_content'):
                        context_parts.append(f"Documento {idx+1}: {doc.page_content[:200]}...")
            
            # Añadir información de la consulta SQL
            context_parts.append(f"\n[CONSULTA SQL EJECUTADA]\n{sql_query}")
            
            # Añadir resultados SQL
            context_parts.append(f"\n[RESULTADOS DE LA CONSULTA]\n{sql_result}")
            
            combined_context = "\n".join(context_parts)
            
            # Preparar la pregunta de interpretación
            interpretation_query = f"Interpreta y explica los siguientes resultados SQL para la pregunta '{rewritten_question}': {sql_result}"
            
            # Validar y limpiar el contexto y la pregunta
            clean_context, clean_question = validate_and_clean_context(combined_context, interpretation_query)
            
            # Generar interpretación usando el sql_interpretation_chain
            logger.info("Generando interpretación de resultados SQL...")
            logger.info(f"Tamaño del contexto combinado: {len(clean_context)} caracteres")
            
            # Usar sql_interpretation_chain que está disponible en el scope
            if sql_interpretation_chain:
                # Preparar el input de manera explícita
                interpretation_input = {
                    "context": clean_context,
                    "question": clean_question
                }
                logger.info(f"Input para interpretación SQL: context length={len(clean_context)}")
                
                response = sql_interpretation_chain.invoke(interpretation_input)
                
                # Extraer la respuesta del JSON
                if isinstance(response, dict) and "answer" in response:
                    interpretation = response["answer"]
                elif isinstance(response, str):
                    interpretation = response
                else:
                    logger.warning(f"Advertencia: Formato de respuesta de interpretación no esperado: {type(response)}")
                    logger.warning(f"Respuesta completa de interpretación: {response}")
                    interpretation = str(response)
            else:
                # Fallback si no hay cadena de interpretación disponible
                logger.warning("No hay cadena de interpretación SQL disponible, usando fallback")
                interpretation = f"Los resultados de la consulta muestran: {sql_result}. Estos datos corresponden a información del sistema SEGEDA (DATUZ) de la Universidad de Zaragoza."
            
            logger.info("Interpretación generada con éxito.")
            logger.info(f"Interpretación generada: {interpretation[:100]}...")
            
            result_state = {
                **state,
                "generation": interpretation,
                "needs_sql_interpretation": False
            }
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=True)
            
            return result_state
            
        except Exception as e:
            logger.error(f"Error al generar interpretación SQL: {str(e)}")
            logger.error(f"Tipo de error: {type(e)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            error_state = {
                **state,
                "generation": f"Se obtuvieron los siguientes resultados de la consulta: {sql_result}",
                "needs_sql_interpretation": False
            }
            
            # Finalizar medición del nodo con error
            metrics_collector.end_node(node_context, error_state, success=False)
            
            return error_state
    
    def route_next_strategy(state):
        """
        Determina la próxima estrategia de recuperación basada en métricas granulares.
        
        Utiliza lógica determinística simple (sin LLM) para decidir:
        - Si continuar con más intentos
        - Qué estrategia de chunk usar en el siguiente intento
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            str: Siguiente acción a tomar ("END", "RETRY")
        """
        retry_count = state.get("retry_count", 0)
        evaluation_metrics = state.get("evaluation_metrics", {})
        current_strategy = state.get("chunk_strategy", DEFAULT_CHUNK_STRATEGY)
        
        logger.info("---ROUTE NEXT STRATEGY---")
        logger.info(f"Intento actual: {retry_count + 1}, Estrategia actual: {current_strategy}")
        
        # Verificar si la recuperación adaptativa está habilitada
        adaptive_retrieval_enabled = VECTORSTORE_CONFIG.get("use_adaptive_retrieval", False)
        logger.info(f"Recuperación adaptativa habilitada: {adaptive_retrieval_enabled}")
        
        # Extraer métricas con valores por defecto
        faithfulness = evaluation_metrics.get("faithfulness", 0.0)
        context_precision = evaluation_metrics.get("context_precision", 0.0)
        context_recall = evaluation_metrics.get("context_recall", 0.0)
        answer_relevance = evaluation_metrics.get("answer_relevance", 0.0)
        
        logger.info(f"Métricas actuales - Faithfulness: {faithfulness}, Precision: {context_precision}, Recall: {context_recall}, Relevance: {answer_relevance}")
        
        # Si todas las métricas están por encima de los umbrales, terminar
        if (faithfulness >= EVALUATION_THRESHOLDS["faithfulness"] and
            context_precision >= EVALUATION_THRESHOLDS["context_precision"] and
            context_recall >= EVALUATION_THRESHOLDS["context_recall"] and
            answer_relevance >= EVALUATION_THRESHOLDS["answer_relevance"]):
            logger.info("Todas las métricas superan los umbrales. Finalizando con éxito.")
            return "END"
        
        # Si ya hicimos el máximo de intentos, terminar siempre
        if retry_count >= MAX_RETRIES:
            logger.info(f"Máximo de reintentos alcanzado ({MAX_RETRIES}). Finalizando.")
            return "END"
        
        # Incrementar contador de reintentos para el PRÓXIMO intento
        new_retry_count = retry_count + 1
        state["retry_count"] = new_retry_count
        
        logger.info(f"Preparando reintento {new_retry_count + 1} (máximo permitido: {MAX_RETRIES + 1})")
        
        # Si la recuperación adaptativa está desactivada, mantener la misma estrategia pero permitir reintentos
        if not adaptive_retrieval_enabled:
            # Verificar si las métricas justifican un reintento con la misma estrategia
            metrics_below_threshold = (
                faithfulness < EVALUATION_THRESHOLDS["faithfulness"] or
                context_precision < EVALUATION_THRESHOLDS["context_precision"] or
                context_recall < EVALUATION_THRESHOLDS["context_recall"] or
                answer_relevance < EVALUATION_THRESHOLDS["answer_relevance"]
            )
            
            if metrics_below_threshold:
                # Verificar si el próximo intento excedería el máximo ANTES de hacer RETRY
                if new_retry_count >= MAX_RETRIES:
                    logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido ({MAX_RETRIES + 1}). Finalizando.")
                    return "END"
                
                # Mantener la misma estrategia de chunk
                logger.info(f"Recuperación adaptativa deshabilitada. Reintentando con la misma estrategia: {current_strategy} tokens.")
                # No cambiar state["chunk_strategy"] - mantener la actual
                return "RETRY"
            else:
                logger.info("Métricas aceptables con recuperación adaptativa deshabilitada. Finalizando.")
                return "END"
        
        # Lógica determinística para seleccionar estrategia (solo si recuperación adaptativa está habilitada)
        
        # Context Recall bajo → necesitamos más contexto (chunks más grandes)
        if context_recall < EVALUATION_THRESHOLDS["context_recall"]:
            if current_strategy != "1024":
                # Verificar si el próximo intento excedería el máximo ANTES de hacer RETRY
                if new_retry_count >= MAX_RETRIES:
                    logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido ({MAX_RETRIES + 1}). Finalizando.")
                    return "END"
                
                state["chunk_strategy"] = "1024"
                logger.info(f"Context Recall bajo ({context_recall}). Cambiando a chunks de 1024 tokens.")
                return "RETRY"
        
        # Context Precision bajo O Faithfulness bajo → necesitamos más precisión (chunks más pequeños)
        if (context_precision < EVALUATION_THRESHOLDS["context_precision"] or
            faithfulness < EVALUATION_THRESHOLDS["faithfulness"]):
            if current_strategy != "256":
                # Verificar si el próximo intento excedería el máximo ANTES de hacer RETRY
                if new_retry_count >= MAX_RETRIES:
                    logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido ({MAX_RETRIES + 1}). Finalizando.")
                    return "END"
                
                state["chunk_strategy"] = "256"
                logger.info(f"Context Precision ({context_precision}) o Faithfulness ({faithfulness}) bajos. Cambiando a chunks de 256 tokens.")
                return "RETRY"
        
        # Answer Relevance bajo → probar estrategia diferente
        if answer_relevance < EVALUATION_THRESHOLDS["answer_relevance"]:
            # Verificar si el próximo intento excedería el máximo ANTES de hacer RETRY
            if new_retry_count >= MAX_RETRIES:
                logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido ({MAX_RETRIES + 1}). Finalizando.")
                return "END"
            
            # Ciclar entre estrategias: 512 -> 1024 -> 256 -> 512
            if current_strategy == "512":
                state["chunk_strategy"] = "1024"
            elif current_strategy == "1024":
                state["chunk_strategy"] = "256"
            else:  # current_strategy == "256"
                state["chunk_strategy"] = "512"
            
            logger.info(f"Answer Relevance bajo ({answer_relevance}). Cambiando de {current_strategy} a {state['chunk_strategy']} tokens.")
            return "RETRY"
        
        # Si llegamos aquí, las métricas no son suficientemente buenas pero no hay estrategia clara
        # Verificar si el próximo intento excedería el máximo ANTES de hacer RETRY
        if new_retry_count >= MAX_RETRIES:
            logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido ({MAX_RETRIES + 1}). Finalizando.")
            return "END"
        
        # Probar con la estrategia contraria a la actual
        if current_strategy == "512":
            state["chunk_strategy"] = "1024"
        elif current_strategy == "1024":
            state["chunk_strategy"] = "256"
        else:
            state["chunk_strategy"] = "512"
        
        logger.info(f"Métricas subóptimas. Probando estrategia alternativa: {state['chunk_strategy']} tokens.")
        return "RETRY"

    def execute_query_with_metrics(state):
        """
        Ejecuta la consulta SQL generada con métricas integradas.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con el resultado de la consulta SQL.
        """
        # Iniciar medición del nodo
        node_context = metrics_collector.start_node("execute_query")
        
        try:
            # Reutilizar la lógica de la función execute_query original
            result_state = execute_query(state)
            success = not result_state.get("sql_result", "").startswith("Error")
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=success)
            
            return result_state
            
        except Exception as e:
            logger.error(f"Error en execute_query_with_metrics: {str(e)}")
            error_state = {**state, "sql_result": f"Error: {str(e)}"}
            
            # Finalizar medición del nodo con error
            metrics_collector.end_node(node_context, error_state, success=False)
            
            return error_state

    # Añadir nodos al grafo
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_relevance", grade_relevance)
    workflow.add_node("generate", generate)
    workflow.add_node("evaluate_response_granular", evaluate_response_granular)
    workflow.add_node("execute_query", execute_query_with_metrics)
    workflow.add_node("generate_sql_interpretation", generate_sql_interpretation)
    
    # Definir bordes - flujo con recuperación adaptativa
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade_relevance")
    workflow.add_edge("grade_relevance", "generate")
    workflow.add_edge("generate", "evaluate_response_granular")
    
    # Definir condición para enrutamiento después de evaluación granular
    def route_after_granular_evaluation(state):
        """
        Determina qué hacer después de la evaluación granular:
        - Ejecutar SQL si es una consulta
        - Reintentar con nueva estrategia si las métricas no son suficientes
        - Finalizar si las métricas son buenas o se alcanzó el máximo de reintentos
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            str: Siguiente nodo a ejecutar
        """
        # Verificar si es una consulta SQL que necesita ejecución
        is_consulta = state.get("is_consulta", False)
        sql_query = state.get("sql_query")
        
        if is_consulta and sql_query and not state.get("sql_result"):
            logger.info("Se detectó una consulta SQL válida. Procediendo a ejecutarla.")
            return "execute_query"
        
        # Usar la lógica de route_next_strategy para decidir si reintentar
        decision = route_next_strategy(state)
        
        if decision == "RETRY":
            logger.info(f"Reintentando con nueva estrategia: {state.get('chunk_strategy', DEFAULT_CHUNK_STRATEGY)}")
            logger.info(f"Estado antes de RETRY - retry_count: {state.get('retry_count', 0)}")
            return "retrieve"
        else:  # decision == "END"
            logger.info("Finalizando workflow.")
            logger.info(f"Estado final - retry_count: {state.get('retry_count', 0)}")
            return "END"
    
    # Definir condición para después de ejecutar consulta SQL
    def route_after_execute_query(state):
        """
        Determina qué hacer después de ejecutar la consulta SQL.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            str: Siguiente nodo a ejecutar
        """
        needs_interpretation = state.get("needs_sql_interpretation", False)
        
        if needs_interpretation:
            logger.info("Generando interpretación de resultados SQL...")
            return "generate_sql_interpretation"
        else:
            return "END"
    
    # Añadir borde condicional desde evaluate_response_granular
    workflow.add_conditional_edges(
        "evaluate_response_granular",
        route_after_granular_evaluation,
        {
            "execute_query": "execute_query",
            "retrieve": "retrieve",
            "END": END
        }
    )
    
    # Añadir borde condicional desde execute_query
    workflow.add_conditional_edges(
        "execute_query",
        route_after_execute_query,
        {
            "generate_sql_interpretation": "generate_sql_interpretation",
            "END": END
        }
    )
    
    # Añadir borde desde interpretación SQL a END
    workflow.add_edge("generate_sql_interpretation", END)
    
    # Compilar el workflow con configuración de recursión
    compiled_workflow = workflow.compile(
        debug=False,
        checkpointer=None,
        interrupt_before=None,
        interrupt_after=None
    )
    
    # Crear función wrapper para el workflow que maneje las métricas
    def workflow_with_metrics(input_data):
        """
        Ejecuta el workflow con recolección de métricas integrada.
        
        Args:
            input_data: Datos de entrada del workflow
            
        Returns:
            Resultado del workflow con métricas recopiladas
        """
        # Extraer datos iniciales
        question = input_data.get("question", "")
        # Usar la estrategia inicial extraída del nombre si no se especifica otra
        chunk_strategy = input_data.get("chunk_strategy", initial_chunk_strategy)
        
        # Actualizar el input_data con la estrategia inicial si no estaba presente
        if "chunk_strategy" not in input_data:
            input_data["chunk_strategy"] = chunk_strategy
        
        # Iniciar recolección de métricas
        metrics_collector.start_workflow(question, chunk_strategy)
        
        try:
            # Ejecutar el workflow con configuración explícita de recursión
            config = {"recursion_limit": 50}  # Límite de recursión más alto para permitir reintentos
            result = compiled_workflow.invoke(input_data, config=config)
            
            # Finalizar métricas con éxito
            metrics_collector.end_workflow(result, success=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Error en la ejecución del workflow: {str(e)}")
            # Finalizar métricas con error
            error_state = input_data.copy()
            error_state.update({"generation": f"Error en workflow: {str(e)}", "success": False})
            metrics_collector.end_workflow(error_state, success=False)
            
            raise e
    
    # Retornar el workflow compilado con la función de métricas
    compiled_workflow.invoke_with_metrics = workflow_with_metrics
    compiled_workflow.metrics_collector = metrics_collector
    
    return compiled_workflow
