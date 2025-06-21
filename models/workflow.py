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
from langagent.config.config import CHUNK_STRATEGY_CONFIG
from langagent.models.metrics_collector import MetricsCollector

# Importar utilidades refactorizadas
from langagent.models.workflow_utils import (
    extract_chunk_strategy_from_name, normalize_name, validate_and_clean_context,
    find_relevant_cubos_by_keywords, detect_insufficient_info_response, 
    extract_sql_query_from_response, check_metrics_success, should_terminate_workflow,
    execute_sql_query
)
from langagent.models.query_analysis import (
    analyze_segeda_query_complexity, suggest_alternative_strategy_mog,
    update_granularity_history_entry
)

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
        came_from_clarification: indica si la pregunta viene de una clarificación previa
        granularity_history: histórico de granularidades probadas
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
    came_from_clarification: bool  # Nuevo campo para query rewriting condicional
    granularity_history: List[Dict[str, Any]]





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
    initial_chunk_strategy = CHUNK_STRATEGY_CONFIG["default_strategy"]  # Fallback por defecto
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
    
    def rewrite_query(state):
        """
        Reescribe la consulta para mejorar la recuperación usando términos técnicos de SEGEDA.
        Solo se ejecuta cuando la pregunta viene de una clarificación previa.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con la pregunta reescrita.
        """
        # Iniciar medición del nodo
        node_context = metrics_collector.start_node("rewrite_query")
        
        question = state["question"]
        logger.info("---REWRITE QUERY---")
        logger.info(f"Reescribiendo consulta que viene de clarificación: {question}")
        
        try:
            if query_rewriter:
                # Ejecutar el rewriter
                rewrite_result = query_rewriter.invoke({"question": question})
                
                # Registrar llamada LLM si el resultado tiene metadatos
                metrics_collector.log_llm_call("rewrite_query", rewrite_result, question, success=True)
                
                # Extraer la pregunta reescrita del resultado
                if isinstance(rewrite_result, dict) and "rewritten_question" in rewrite_result:
                    rewritten_question = rewrite_result["rewritten_question"]
                elif isinstance(rewrite_result, str):
                    rewritten_question = rewrite_result
                else:
                    logger.warning(f"Formato inesperado del query rewriter: {type(rewrite_result)}")
                    rewritten_question = str(rewrite_result)
                
                logger.info(f"Consulta reescrita: {rewritten_question}")
            else:
                logger.warning("Query rewriter no disponible, usando pregunta original")
                rewritten_question = question
            
            result_state = {
                **state,
                "rewritten_question": rewritten_question
            }
            
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=True)
            
            return result_state
            
        except Exception as e:
            logger.error(f"Error al reescribir consulta: {str(e)}")
            # En caso de error, usar la pregunta original
            error_state = {
                **state,
                "rewritten_question": question
            }
            
            # Finalizar medición del nodo con error
            metrics_collector.end_node(node_context, error_state, success=False)
            
            return error_state
    
    def route_entry_point(state):
        """
        Determina si se debe hacer rewrite de la consulta o ir directamente a retrieve.
        Solo hace rewrite si la pregunta viene de una clarificación previa.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            str: Siguiente nodo a ejecutar ("rewrite_query" o "retrieve")
        """
        came_from_clarification = state.get("came_from_clarification", False)
        
        if came_from_clarification:
            logger.info("Pregunta viene de clarificación. Ejecutando query rewriting.")
            return "rewrite_query"
        else:
            logger.info("Pregunta directa del usuario. Saltando rewriting.")
            # Asegurar que rewritten_question esté inicializada
            if "rewritten_question" not in state:
                state["rewritten_question"] = state["question"]
            return "retrieve"

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
        chunk_strategy = state.get("chunk_strategy", CHUNK_STRATEGY_CONFIG["default_strategy"])
        
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
                # Si tenemos retrievers adaptativos pero la estrategia actual no está incluida,
                # añadir el retriever principal con la estrategia actual para futuros usos
                adaptive_retrievers[chunk_strategy] = retriever
                current_retriever = retriever
                logger.info(f"Añadiendo retriever principal como adaptativo para estrategia {chunk_strategy} tokens")
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
                    
                    grader_input = {
                        "content": document_data["content"],
                        "ambito_document": str(document_data["metadata"][ambito]) if ambito in document_data["metadata"] else "",
                        "source": document_data["source"],
                        "question": question,
                        "ambito": ambito,
                    }
                    
                    logger.debug(f"=== INPUT PARA RETRIEVAL GRADER ===")
                    logger.debug(f"Tipo de grader_input: {type(grader_input)}")
                    logger.debug(f"Claves en grader_input: {list(grader_input.keys())}")
                    
                    relevance = retrieval_grader.invoke(grader_input)
                    
                    logger.debug(f"=== OUTPUT DEL RETRIEVAL GRADER ===")
                    logger.debug(f"Tipo de relevance: {type(relevance)}")
                    logger.debug(f"Contenido de relevance: {relevance}")
                    if hasattr(relevance, '__dict__'):
                        logger.debug(f"Dict de relevance: {relevance.__dict__}")
                    if hasattr(relevance, 'response_metadata'):
                        logger.debug(f"response_metadata de relevance: {relevance.response_metadata}")
                    
                    # Registrar llamada LLM para el grader de relevancia
                    metrics_collector.log_llm_call("grade_relevance", relevance, f"Documento {idx + 1}", success=True)
                    
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
                
                # Registrar llamada LLM para SQL query generation
                metrics_collector.log_llm_call("generate", sql_query, clean_context[:500] + "...", success=True)
                
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
                
                logger.debug(f"=== INPUT PARA RAG ANSWER CHAIN ===")
                logger.debug(f"Tipo de rag_input: {type(rag_input)}")
                logger.debug(f"Claves en rag_input: {list(rag_input.keys())}")
                logger.debug(f"Contenido de rag_input: {rag_input}")
                
                response = rag_sql_chain["answer_chain"].invoke(rag_input)
                
                logger.debug(f"=== OUTPUT DEL RAG ANSWER CHAIN ===")
                logger.debug(f"Tipo de response: {type(response)}")
                logger.debug(f"Contenido de response: {response}")
                if hasattr(response, '__dict__'):
                    logger.debug(f"Dict de response: {response.__dict__}")
                if hasattr(response, 'response_metadata'):
                    logger.debug(f"response_metadata de response: {response.response_metadata}")
                
                # Registrar llamada LLM para RAG answer generation
                metrics_collector.log_llm_call("generate", response, clean_context[:500] + "...", success=True)
                
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
                evaluator_input = {
                    "question": question,
                    "documents": docs_text,
                    "generation": generation
                }
                
                logger.debug(f"=== INPUT PARA GRANULAR EVALUATOR ===")
                logger.debug(f"Tipo de evaluator_input: {type(evaluator_input)}")
                logger.debug(f"Claves en evaluator_input: {list(evaluator_input.keys())}")
                
                evaluation_result = granular_evaluator.invoke(evaluator_input)
                
                logger.debug(f"=== OUTPUT DEL GRANULAR EVALUATOR ===")
                logger.debug(f"Tipo de evaluation_result: {type(evaluation_result)}")
                logger.debug(f"Contenido de evaluation_result: {evaluation_result}")
                if hasattr(evaluation_result, '__dict__'):
                    logger.debug(f"Dict de evaluation_result: {evaluation_result.__dict__}")
                if hasattr(evaluation_result, 'response_metadata'):
                    logger.debug(f"response_metadata de evaluation_result: {evaluation_result.response_metadata}")
                
                # Registrar llamada LLM para evaluación granular
                metrics_collector.log_llm_call("evaluate_response_granular", evaluation_result, question, success=True)
                
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
                
                # Registrar llamada LLM para interpretación SQL
                metrics_collector.log_llm_call("generate_sql_interpretation", response, clean_question, success=True)
                
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
    




    def update_granularity_history(state):
        """
        Actualiza el histórico de granularidades con la estrategia actual y sus métricas.
        Esta función debe llamarse antes de cada decisión de routing para capturar métricas.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con histórico actualizado.
        """
        retry_count = state.get("retry_count", 0)
        evaluation_metrics = state.get("evaluation_metrics", {})
        current_strategy = state.get("chunk_strategy", CHUNK_STRATEGY_CONFIG["default_strategy"])
        granularity_history = state.get("granularity_history", [])
        
        # Usar la función utilitaria para actualizar el histórico
        updated_history = update_granularity_history_entry(
            granularity_history,
            current_strategy,
            retry_count,
            evaluation_metrics
        )
        
        return {
            **state,
            "granularity_history": updated_history
        }

    def route_next_strategy(state):
        """
        Determina la próxima estrategia de recuperación basada en análisis granular de la consulta
        y métricas de evaluación, inspirado en Mix-of-Granularity (MoG).
        
        NOTA: Esta función ya no modifica el estado directamente. Las actualizaciones del histórico
        se manejan en el nodo update_granularity_history.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            str: Siguiente acción a tomar ("END", "RETRY", "UPDATE_HISTORY_AND_END", "UPDATE_HISTORY_AND_RETRY")
        """
        retry_count = state.get("retry_count", 0)
        evaluation_metrics = state.get("evaluation_metrics", {})
        current_strategy = state.get("chunk_strategy", CHUNK_STRATEGY_CONFIG["default_strategy"])
        question = state.get("question", "").lower()
        rewritten_question = state.get("rewritten_question", "").lower()
        
        logger.info("---ROUTE NEXT STRATEGY (MoG-INSPIRED)---")
        logger.info(f"Intento actual: {retry_count + 1}, Estrategia actual: {current_strategy}")
        
        # Verificar si la recuperación adaptativa está habilitada
        adaptive_retrieval_enabled = VECTORSTORE_CONFIG.get("use_adaptive_retrieval", False)
        logger.info(f"Recuperación adaptativa habilitada: {adaptive_retrieval_enabled}")
        
        # Extraer configuraciones y métricas con valores por defecto
        thresholds = CHUNK_STRATEGY_CONFIG["evaluation_thresholds"]
        max_retries = CHUNK_STRATEGY_CONFIG["max_retries"]
        faithfulness = evaluation_metrics.get("faithfulness", 0.0)
        context_precision = evaluation_metrics.get("context_precision", 0.0)
        context_recall = evaluation_metrics.get("context_recall", 0.0)
        answer_relevance = evaluation_metrics.get("answer_relevance", 0.0)
        
        logger.info(f"Métricas actuales - Faithfulness: {faithfulness}, Precision: {context_precision}, Recall: {context_recall}, Relevance: {answer_relevance}")
        
        # Si todas las métricas están por encima de los umbrales, terminar
        if (faithfulness >= thresholds["faithfulness"] and
            context_precision >= thresholds["context_precision"] and
            context_recall >= thresholds["context_recall"] and
            answer_relevance >= thresholds["answer_relevance"]):
            logger.info("Todas las métricas superan los umbrales. Finalizando con éxito.")
            return "UPDATE_HISTORY_AND_END"
        
        # Si ya hicimos el máximo de intentos, terminar siempre
        if retry_count >= max_retries:
            logger.info(f"Máximo de reintentos alcanzado ({max_retries}). Finalizando.")
            return "UPDATE_HISTORY_AND_END"
        
        # Incrementar contador de reintentos para el PRÓXIMO intento
        new_retry_count = retry_count + 1
        
        logger.info(f"Preparando reintento {new_retry_count + 1} (máximo permitido: {max_retries + 1})")
        
        # Si la recuperación adaptativa está desactivada, usar lógica simple
        if not adaptive_retrieval_enabled:
            metrics_below_threshold = (
                faithfulness < thresholds["faithfulness"] or
                context_precision < thresholds["context_precision"] or
                context_recall < thresholds["context_recall"] or
                answer_relevance < thresholds["answer_relevance"]
            )
            
            if metrics_below_threshold:
                if new_retry_count >= max_retries:
                    logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido ({max_retries + 1}). Finalizando.")
                    return "UPDATE_HISTORY_AND_END"
                
                logger.info(f"Recuperación adaptativa deshabilitada. Reintentando con la misma estrategia: {current_strategy} tokens.")
                return "UPDATE_HISTORY_AND_RETRY"
            else:
                logger.info("Métricas aceptables con recuperación adaptativa deshabilitada. Finalizando.")
                return "UPDATE_HISTORY_AND_END"
        
        # LÓGICA DETERMINÍSTICA AVANZADA INSPIRADA EN MoG
        # Analizar la granularidad de la consulta para determinar estrategia óptima
        
        # Usar la pregunta reescrita si está disponible, sino la original
        query_to_analyze = rewritten_question if rewritten_question else question
        
        # Obtener histórico de granularidades del estado actual
        granularity_history = state.get("granularity_history", [])
        
        # Obtener análisis de complejidad de la consulta con histórico
        query_analysis = analyze_segeda_query_complexity(query_to_analyze, granularity_history)
        
        # Log detallado del análisis de consulta
        logger.info(f"Análisis de consulta SEGEDA (con histórico):")
        logger.info(f"  - Granularidad recomendada: {query_analysis['recommended_granularity']} tokens")
        logger.info(f"  - Confianza: {query_analysis['confidence']:.2f}")
        logger.info(f"  - Razón: {query_analysis['reason']}")
        logger.info(f"  - Indicadores específicos: {query_analysis['specific_indicators']}")
        logger.info(f"  - Indicadores analíticos: {query_analysis['analytical_indicators']}")
        logger.info(f"  - Indicadores amplios: {query_analysis['broad_indicators']}")
        logger.info(f"  - Puntuación dominio SEGEDA: {query_analysis['segeda_domain_score']}")
        logger.info(f"  - Ajuste por histórico: {query_analysis['history_adjustment']}")
        if query_analysis['cubo_mentions']:
            logger.info(f"  - Cubos mencionados: {query_analysis['cubo_mentions']}")
        if query_analysis['medida_mentions']:
            logger.info(f"  - Medidas mencionadas: {query_analysis['medida_mentions']}")
        if query_analysis['dimension_mentions']:
            logger.info(f"  - Dimensiones mencionadas: {query_analysis['dimension_mentions']}")
        if query_analysis['technical_terms']:
            logger.info(f"  - Términos técnicos: {query_analysis['technical_terms']}")
        if query_analysis['tried_strategies']:
            logger.info(f"  - Estrategias probadas previamente: {query_analysis['tried_strategies']}")
        
        # Sugerir estrategia alternativa basada en análisis MoG con histórico
        alternative_strategy = suggest_alternative_strategy_mog(current_strategy, evaluation_metrics, query_analysis, granularity_history)
        
        logger.info(f"Estrategia alternativa sugerida por MoG: {alternative_strategy} tokens")
        
        # LÓGICA DE DECISIÓN BASADA EN MÉTRICAS Y ESTRATEGIA ÓPTIMA
        
        # Si la estrategia actual es la óptima pero las métricas son bajas,
        # ajustar según el problema específico
        if current_strategy == alternative_strategy:
            logger.info("Estrategia actual coincide con la alternativa sugerida. Analizando métricas específicas...")
            
            # Context Recall bajo → necesitamos más contexto (estrategia mayor)
            if context_recall < thresholds["context_recall"]:
                if new_retry_count >= max_retries:
                    logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido. Finalizando.")
                    return "UPDATE_HISTORY_AND_END"
                
                # Incrementar granularidad para obtener más contexto
                if current_strategy == "256":
                    logger.info(f"Context Recall bajo ({context_recall}). Aumentando de 256 a 512 tokens para más contexto.")
                    return "UPDATE_HISTORY_AND_RETRY"  # El cambio de estrategia se hará en otro nodo
                elif current_strategy == "512":
                    logger.info(f"Context Recall bajo ({context_recall}). Aumentando de 512 a 1024 tokens para más contexto.")
                    return "UPDATE_HISTORY_AND_RETRY"
                else:  # current_strategy == "1024"
                    # Ya estamos en la granularidad máxima, no cambiar
                    logger.info("Ya en granularidad máxima con recall bajo. Context Recall podría mejorar con datos adicionales.")
                    return "UPDATE_HISTORY_AND_END"
            
            # Context Precision bajo O Faithfulness bajo → necesitamos más precisión (estrategia menor)
            if (context_precision < thresholds["context_precision"] or
                faithfulness < thresholds["faithfulness"]):
                if new_retry_count >= max_retries:
                    logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido. Finalizando.")
                    return "UPDATE_HISTORY_AND_END"
                
                # Decrementar granularidad para obtener más precisión
                if current_strategy == "1024":
                    logger.info(f"Context Precision ({context_precision}) o Faithfulness ({faithfulness}) bajos. Reduciendo de 1024 a 512 tokens para más precisión.")
                    return "UPDATE_HISTORY_AND_RETRY"
                elif current_strategy == "512":
                    logger.info(f"Context Precision ({context_precision}) o Faithfulness ({faithfulness}) bajos. Reduciendo de 512 a 256 tokens para más precisión.")
                    return "UPDATE_HISTORY_AND_RETRY"
                else:  # current_strategy == "256"
                    # Ya estamos en la granularidad mínima, no cambiar
                    logger.info("Ya en granularidad mínima con precision/faithfulness bajos. Podría necesitarse mejor filtrado de contenido.")
                    return "UPDATE_HISTORY_AND_END"
            
            # Answer Relevance bajo con estrategia óptima → probar estrategias adyacentes inteligentemente
            if answer_relevance < thresholds["answer_relevance"]:
                if new_retry_count >= max_retries:
                    logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido. Finalizando.")
                    return "UPDATE_HISTORY_AND_END"
                
                # Usar análisis de consulta para decidir qué estrategia probar
                if query_analysis['specific_indicators'] > 0 and current_strategy != "256":
                    logger.info(f"Answer Relevance bajo ({answer_relevance}) con consulta específica detectada. Probando granularidad fina (256 tokens).")
                    return "UPDATE_HISTORY_AND_RETRY"
                elif query_analysis['broad_indicators'] > 0 and current_strategy != "1024":
                    logger.info(f"Answer Relevance bajo ({answer_relevance}) con consulta amplia detectada. Probando granularidad gruesa (1024 tokens).")
                    return "UPDATE_HISTORY_AND_RETRY"
                elif query_analysis['analytical_indicators'] > 0 and current_strategy != "512":
                    logger.info(f"Answer Relevance bajo ({answer_relevance}) con consulta analítica detectada. Probando granularidad media (512 tokens).")
                    return "UPDATE_HISTORY_AND_RETRY"
                else:
                    # Probar estrategia adyacente como fallback
                    if current_strategy == "512":
                        logger.info(f"Answer Relevance bajo ({answer_relevance}). Probando granularidad más específica (256 tokens).")
                        return "UPDATE_HISTORY_AND_RETRY"
                    elif current_strategy == "256":
                        logger.info(f"Answer Relevance bajo ({answer_relevance}). Probando granularidad amplia (1024 tokens).")
                        return "UPDATE_HISTORY_AND_RETRY"
                    elif current_strategy == "1024":
                        logger.info(f"Answer Relevance bajo ({answer_relevance}). Probando granularidad específica (256 tokens).")
                        return "UPDATE_HISTORY_AND_RETRY"
        
        # Si la estrategia actual NO es la óptima, cambiar a la óptima
        else:
            if new_retry_count >= max_retries:
                logger.info(f"El próximo intento ({new_retry_count + 1}) excedería el máximo permitido. Finalizando.")
                return "UPDATE_HISTORY_AND_END"
            
            logger.info(f"Cambiando de estrategia subóptima ({current_strategy}) a estrategia óptima ({alternative_strategy}) tokens.")
            logger.info(f"Justificación del cambio: {query_analysis['reason']}")
            return "UPDATE_HISTORY_AND_RETRY"
        
        # Si llegamos aquí con estrategia óptima y métricas no muy bajas, terminar
        logger.info("Estrategia óptima en uso y métricas aceptables para los umbrales actuales. Finalizando.")
        return "UPDATE_HISTORY_AND_END"

    def update_chunk_strategy(state):
        """
        Actualiza la estrategia de chunk basada en el análisis MoG y las métricas actuales.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con la nueva estrategia de chunk.
        """
        retry_count = state.get("retry_count", 0)
        evaluation_metrics = state.get("evaluation_metrics", {})
        current_strategy = state.get("chunk_strategy", CHUNK_STRATEGY_CONFIG["default_strategy"])
        question = state.get("question", "").lower()
        rewritten_question = state.get("rewritten_question", "").lower()
        
        logger.info("---UPDATE CHUNK STRATEGY---")
        logger.info(f"Estrategia actual: {current_strategy}")
        
        # Usar la pregunta reescrita si está disponible, sino la original
        query_to_analyze = rewritten_question if rewritten_question else question
        
        # Obtener histórico de granularidades del estado actual
        granularity_history = state.get("granularity_history", [])
        
        # Obtener análisis de complejidad de la consulta con histórico
        query_analysis = analyze_segeda_query_complexity(query_to_analyze, granularity_history)
          # Sugerir estrategia alternativa basada en análisis MoG con histórico
        alternative_strategy = suggest_alternative_strategy_mog(current_strategy, evaluation_metrics, query_analysis, granularity_history)
        
        # Extraer métricas para determinar el tipo de cambio necesario
        context_recall = evaluation_metrics.get("context_recall", 0.0)
        context_precision = evaluation_metrics.get("context_precision", 0.0)
        faithfulness = evaluation_metrics.get("faithfulness", 0.0)
        answer_relevance = evaluation_metrics.get("answer_relevance", 0.0)
        
        # Obtener umbrales de evaluación
        thresholds = CHUNK_STRATEGY_CONFIG["evaluation_thresholds"]
        
        # Obtener estrategias ordenadas dinámicamente
        strategies_sorted = sorted(CHUNK_STRATEGY_CONFIG["available_strategies"], key=int)
        fine_grained = strategies_sorted[0]  # Estrategia más fina
        medium_grained = strategies_sorted[len(strategies_sorted)//2] if len(strategies_sorted) > 2 else strategies_sorted[1] if len(strategies_sorted) > 1 else strategies_sorted[0]  # Estrategia media
        coarse_grained = strategies_sorted[-1]  # Estrategia más gruesa
        
        new_strategy = current_strategy  # Por defecto, mantener estrategia actual
        
        # Determinar nueva estrategia basada en las métricas y análisis
        if current_strategy == alternative_strategy:
            # Misma estrategia recomendada, ajustar según métricas específicas
            if context_recall < thresholds["context_recall"]:
                # Necesitamos más contexto - moverse hacia granularidad más gruesa
                current_index = strategies_sorted.index(current_strategy)
                if current_index < len(strategies_sorted) - 1:
                    new_strategy = strategies_sorted[current_index + 1]
                # Si ya estamos en la más gruesa, mantener
            elif (context_precision < thresholds["context_precision"] or
                  faithfulness < thresholds["faithfulness"]):
                # Necesitamos más precisión - moverse hacia granularidad más fina
                current_index = strategies_sorted.index(current_strategy)
                if current_index > 0:
                    new_strategy = strategies_sorted[current_index - 1]
                # Si ya estamos en la más fina, mantener
            elif answer_relevance < thresholds["answer_relevance"]:
                # Problema de relevancia, usar análisis de consulta
                if query_analysis['specific_indicators'] > 0 and current_strategy != fine_grained:
                    new_strategy = fine_grained
                elif query_analysis['broad_indicators'] > 0 and current_strategy != coarse_grained:
                    new_strategy = coarse_grained
                elif query_analysis['analytical_indicators'] > 0 and current_strategy != medium_grained:
                    new_strategy = medium_grained
                else:
                    # Fallback: probar estrategia adyacente
                    current_index = strategies_sorted.index(current_strategy)
                    if current_index == len(strategies_sorted) // 2:  # Si estamos en el medio
                        new_strategy = fine_grained
                    elif current_index == 0:  # Si estamos en la más fina
                        new_strategy = coarse_grained
                    elif current_index == len(strategies_sorted) - 1:  # Si estamos en la más gruesa
                        new_strategy = fine_grained
        else:
            # Usar la estrategia alternativa recomendada
            new_strategy = alternative_strategy
        
        if new_strategy != current_strategy:
            logger.info(f"Cambiando estrategia de {current_strategy} a {new_strategy} tokens")
            logger.info(f"Justificación: {query_analysis.get('reason', 'Análisis MoG')}")
        else:
            logger.info(f"Manteniendo estrategia actual: {current_strategy} tokens")
        
        return {
            **state,
            "chunk_strategy": new_strategy
        }

    def increment_retry_count(state):
        """
        Incrementa el contador de reintentos antes de volver a retrieve.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:            dict: Estado actualizado con retry_count incrementado.
        """
        current_retry_count = state.get("retry_count", 0)
        new_retry_count = current_retry_count + 1
        
        logger.info(f"Incrementando retry_count de {current_retry_count} a {new_retry_count}")
        
        return {
            **state,
            "retry_count": new_retry_count
        }

    def execute_sql_query(state):
        """
        Ejecuta una consulta SQL y devuelve el resultado usando la configuración SQL.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con el resultado de la consulta SQL.
        """
        from langchain_community.utilities import SQLDatabase
        from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
        
        logger.info("---EXECUTE SQL QUERY---")
        
        # Extraer la consulta SQL del estado
        sql_query = state.get("sql_query")
        if not sql_query:
            logger.error("No hay consulta SQL en el estado")
            return {
                **state,
                "sql_result": "Error: No se encontró consulta SQL para ejecutar",
                "needs_sql_interpretation": True
            }
        
        # Limpiar la consulta SQL si viene en formato JSON
        clean_sql_query = sql_query
        if isinstance(sql_query, str):
            try:
                if sql_query.strip().startswith('{'):
                    import json
                    query_data = json.loads(sql_query)
                    if "query" in query_data:
                        clean_sql_query = query_data["query"]
                    elif "sql" in query_data:
                        clean_sql_query = query_data["sql"]
            except json.JSONDecodeError:
                # Si no es JSON válido, usar como está
                pass
        
        logger.info(f"Ejecutando consulta SQL: {clean_sql_query}")
        
        try:
            # Crear la conexión a la base de datos usando la configuración
            if SQL_CONFIG.get("db_uri"):
                db = SQLDatabase.from_uri(SQL_CONFIG.get("db_uri"))
                execute_query_tool = QuerySQLDatabaseTool(db=db)
                
                # Ejecutar la consulta
                result = execute_query_tool.invoke(clean_sql_query)
                logger.info("Consulta SQL ejecutada con éxito.")
                logger.info(f"Resultado: {result}")
                
                return {
                    **state,
                    "sql_result": result,
                    "sql_query": clean_sql_query,
                    "needs_sql_interpretation": True
                }
                
            else:
                error_msg = "Error: No se ha configurado la URI de la base de datos"
                logger.error(error_msg)
                return {
                    **state,
                    "sql_result": error_msg,
                    "sql_query": clean_sql_query,
                    "needs_sql_interpretation": False
                }                
        except Exception as e:
            error_msg = f"Error al ejecutar la consulta SQL: {str(e)}"
            logger.error(error_msg)
            return {
                **state,
                "sql_result": error_msg,
                "sql_query": clean_sql_query,
                "needs_sql_interpretation": False
            }

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
            # Usar la función execute_sql_query
            result_state = execute_sql_query(state)
            success = not str(result_state.get("sql_result", "")).startswith("Error")
            # Finalizar medición del nodo
            metrics_collector.end_node(node_context, result_state, success=success)
            
            return result_state
            
        except Exception as e:
            logger.error(f"Error en execute_query_with_metrics: {str(e)}")
            error_state = {**state, "sql_result": f"Error: {str(e)}"}
            
            # Finalizar medición del nodo con error
            metrics_collector.end_node(node_context, error_state, success=False)
            
            return error_state    # Añadir nodos al grafo
    workflow.add_node("entry_point", lambda state: state)  # Nodo dummy para entrada condicional
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_relevance", grade_relevance)
    workflow.add_node("generate", generate)
    workflow.add_node("evaluate_response_granular", evaluate_response_granular)
    workflow.add_node("update_granularity_history", update_granularity_history)
    workflow.add_node("update_chunk_strategy", update_chunk_strategy)
    workflow.add_node("increment_retry_count", increment_retry_count)
    workflow.add_node("execute_query", execute_query_with_metrics)
    workflow.add_node("generate_sql_interpretation", generate_sql_interpretation)

    # Definir entrada condicional - flujo con query rewriting condicional
    workflow.set_entry_point("entry_point")
    workflow.add_conditional_edges(
        "entry_point",
        route_entry_point,
        {
            "rewrite_query": "rewrite_query",
            "retrieve": "retrieve"
        }
    )
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("retrieve", "grade_relevance")
    workflow.add_edge("grade_relevance", "generate")
    workflow.add_edge("generate", "evaluate_response_granular")
    workflow.add_edge("evaluate_response_granular", "update_granularity_history")
    workflow.add_edge("update_chunk_strategy", "increment_retry_count")
    workflow.add_edge("increment_retry_count", "retrieve")
    
    # Definir condición para enrutamiento después de actualizar histórico
    def route_after_update_history(state):
        """
        Determina qué hacer después de actualizar el histórico de granularidades:
        - Ejecutar SQL si es una consulta
        - Actualizar estrategia y reintentar si las métricas no son suficientes
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
        
        if decision == "UPDATE_HISTORY_AND_RETRY":
            logger.info("Actualizando estrategia y reintentando")
            return "update_chunk_strategy"
        elif decision in ["UPDATE_HISTORY_AND_END", "END"]:
            logger.info("Finalizando workflow después de actualizar histórico.")
            return "END"
        else:  # Fallback
            logger.warning(f"Decisión no reconocida: {decision}. Finalizando.")
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
    
    # Añadir borde condicional desde update_granularity_history
    workflow.add_conditional_edges(
        "update_granularity_history",
        route_after_update_history,
        {
            "execute_query": "execute_query",
            "update_chunk_strategy": "update_chunk_strategy",
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
        
        # Detectar si se está usando estrategia adaptativa
        # Se considera adaptativa si hay adaptive_retrievers disponibles o si hay granularity_history
        is_adaptive = bool(adaptive_retrievers) or len(input_data.get("granularity_history", [])) > 0
        
        # Actualizar el input_data con la estrategia inicial si no estaba presente
        if "chunk_strategy" not in input_data:
            input_data["chunk_strategy"] = chunk_strategy
        
        # Inicializar came_from_clarification si no está presente
        if "came_from_clarification" not in input_data:
            input_data["came_from_clarification"] = False
        
        # Inicializar granularity_history si no está presente
        if "granularity_history" not in input_data:
            input_data["granularity_history"] = []
        
        # Iniciar recolección de métricas con detección de estrategia adaptativa
        metrics_collector.start_workflow(question, chunk_strategy, is_adaptive=is_adaptive)
        
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
