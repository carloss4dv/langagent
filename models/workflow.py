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
        hallucination_score: puntuación de alucinaciones
        answer_score: puntuación de la respuesta
        relevant_cubos: lista de cubos relevantes para la pregunta
        ambito: ámbito identificado para la pregunta
        retrieval_details: detalles de recuperación por cubo
        is_consulta: indica si la pregunta es sobre una consulta guardada o SQL
        consulta_documents: documentos de consultas guardadas recuperados
        sql_query: consulta SQL generada
        sql_result: resultado de la consulta SQL
        needs_sql_interpretation: indica si se necesita generar interpretación de resultados SQL
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
    needs_sql_interpretation: bool

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

def create_workflow(retriever, retrieval_grader, hallucination_grader, answer_grader, query_rewriter=None, rag_sql_chain=None, sql_interpretation_chain=None):
    """
    Crea un flujo de trabajo para el agente utilizando LangGraph.
    
    Args:
        retriever: Retriever para recuperar documentos.
        rag_chain: Cadena de RAG.
        retrieval_grader: Evaluador de relevancia de documentos.
        hallucination_grader: Evaluador de alucinaciones.
        answer_grader: Evaluador de utilidad de respuestas.
        query_rewriter: Reescritor de consultas para mejorar la recuperación.
        rag_sql_chain: Cadena para consultas SQL cuando se detecta que es una consulta de base de datos.
        sql_interpretation_chain: Cadena para generar interpretación de resultados SQL.
        
    Returns:
        StateGraph: Grafo de estado configurado.
    """
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
        question = state["question"]
        rewritten_question = state.get("rewritten_question", question)
        retry_count = state.get("retry_count", 0)
        ambito = state.get("ambito")
        is_consulta = state.get("is_consulta", False)
        
        logger.info("---RETRIEVE---")
        logger.info(f"Búsqueda con pregunta: {rewritten_question}")
        logger.info(f"Ámbito identificado: {ambito}")
        
        try:
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
                docs = retriever.invoke(rewritten_question)
            elif filters:
                logger.info(f"Aplicando filtros para {vector_db_type}: {filters}")
                docs = retriever.invoke(rewritten_question, filter=filters)
            else:
                docs = retriever.invoke(rewritten_question)
                
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
            
            return {
                "documents": docs,
                "question": question,
                "rewritten_question": rewritten_question,
                "retry_count": retry_count,
                "ambito": ambito,
                "retrieval_details": retrieval_details
            }
            
        except Exception as e:
            logger.error(f"Error al recuperar documentos: {str(e)}")
            return {
                "documents": [],
                "question": question,
                "rewritten_question": rewritten_question,
                "retry_count": retry_count,
                "ambito": ambito,
                "retrieval_details": {"error": str(e)}
            }

    def grade_relevance(state):
        """
        Evalúa la relevancia de los documentos recuperados.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con los documentos relevantes.
        """
        logger.info("---GRADE RELEVANCE---")
        
        documents = state["documents"]
        question = state["question"]
        ambito = state["ambito"]
        rewritten_question = state.get("rewritten_question", question)
        retrieval_details = state.get("retrieval_details", {})
        
        try:
            # Comprobar si los documentos son relevantes
            relevant_docs = []
            for doc in documents:
                document_data = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "unknown")
                }
                
                relevance = retrieval_grader.invoke({
                    "content": document_data["content"],
                    "metadata": str(document_data["metadata"]),
                    "source": document_data["source"],
                    "question": question,
                    "ambito": ambito,
                })
                
                if isinstance(relevance, dict) and relevance.get("score", "").lower() == "yes":
                    relevant_docs.append(doc)
            
            # Si no hay documentos relevantes, usar todos
            if not relevant_docs and documents:
                logger.info("No se encontraron documentos relevantes. Usando todos los documentos recuperados.")
                relevant_docs = documents
            
            # Actualizar detalles de recuperación
            retrieval_details.update({
                "relevant_count": len(relevant_docs),
                "relevance_checked": True
            })
            
            return {
                **state,
                "documents": relevant_docs,
                "retrieval_details": retrieval_details
            }
            
        except Exception as e:
            logger.error(f"Error al evaluar relevancia: {str(e)}")
            return {
                **state,
                "retrieval_details": {
                    **retrieval_details,
                    "relevance_error": str(e)
                }
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
        rewritten_question = state.get("rewritten_question", question)
        retry_count = state.get("retry_count", 0)
        relevant_cubos = state.get("relevant_cubos", [])
        retrieval_details = state.get("retrieval_details", {})
        is_consulta = state.get("is_consulta", False)
        
        logger.info("---GENERATE---")
        if not documents:
            logger.info("No se encontraron documentos relevantes.")
            response_json = "No se encontró información relevante en SEGEDA para responder a esta pregunta."
            return {
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
            
            return {
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
            
        except Exception as e:
            logger.error(f"Error al generar respuesta: {str(e)}")
            logger.error(f"Tipo de error: {type(e)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            response_json = f"Se produjo un error al generar la respuesta: {str(e)}"
            return {
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

    def evaluate(state):
        """
        Evalúa la respuesta generada para determinar su calidad y fundamentación.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con las evaluaciones.
        """
        logger.info("---EVALUATE---")
        
        generation = state["generation"]
        question = state["question"]
        rewritten_question = state.get("rewritten_question", question)
        retry_count = state.get("retry_count", 0)
        is_consulta = state.get("is_consulta", False)
        
        try:
            # Evaluar la respuesta solo si no es una consulta SQL
            if not is_consulta or not rag_sql_chain:
                logger.info("Evaluando si la respuesta contiene alucinaciones...")
                # Verificar si la respuesta contiene alucinaciones
                hallucination_eval = hallucination_grader.invoke({
                    "documents": state["documents"],
                    "generation": generation
                })
                
                if isinstance(hallucination_eval, dict) and "score" in hallucination_eval:
                    is_grounded = hallucination_eval["score"].lower() == "yes"
                    logger.info(f"¿Respuesta fundamentada en los documentos? {'Sí' if is_grounded else 'No'}")
                else:
                    logger.warning(f"Advertencia: Evaluación de alucinaciones no válida: {hallucination_eval}")
                    is_grounded = True  # Por defecto, asumir que está fundamentada
                
                logger.info("Evaluando calidad de la respuesta...")
                # Verificar si la respuesta es útil
                answer_eval = answer_grader.invoke({
                    "generation": generation,
                    "question": rewritten_question
                })
                
                if isinstance(answer_eval, dict) and "score" in answer_eval:
                    is_useful = answer_eval["score"].lower() == "yes"
                    logger.info(f"¿Respuesta útil para la pregunta? {'Sí' if is_useful else 'No'}")
                else:
                    logger.warning(f"Advertencia: Evaluación de utilidad no válida: {answer_eval}")
                    is_useful = True  # Por defecto, asumir que es útil
            else:
                # Para consultas SQL, asumimos que son útiles y fundamentadas
                is_grounded = True
                is_useful = True
                hallucination_eval = {"score": "yes"}
                answer_eval = {"score": "yes"}
            
            # Si la generación no es exitosa, incrementar contador de reintentos
            if not (is_grounded and is_useful):
                retry_count += 1
                logger.info(f"---RETRY ATTEMPT {retry_count}---")
            
            return {
                **state,
                "retry_count": retry_count,
                "hallucination_score": hallucination_eval,
                "answer_score": answer_eval
            }
            
        except Exception as e:
            logger.error(f"Error al evaluar respuesta: {str(e)}")
            return {
                **state,
                "retry_count": retry_count,
                "hallucination_score": None,
                "answer_score": None
            }
    
    def generate_sql_interpretation(state):
        """
        Genera una respuesta interpretativa basada en los resultados de la consulta SQL.
        
        Args:
            state (dict): Estado actual del grafo.
            
        Returns:
            dict: Estado actualizado con la respuesta interpretativa.
        """
        question = state["question"]
        rewritten_question = state.get("rewritten_question", question)
        sql_query = state.get("sql_query", "")
        sql_result = state.get("sql_result", "")
        documents = state.get("documents", [])
        
        logger.info("---GENERATE SQL INTERPRETATION---")
        
        if not sql_result:
            logger.info("No hay resultados SQL para interpretar.")
            return {
                **state,
                "generation": "No se pudieron obtener resultados de la consulta SQL.",
                "needs_sql_interpretation": False
            }
        
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
            
            return {
                **state,
                "generation": interpretation,
                "needs_sql_interpretation": False
            }
            
        except Exception as e:
            logger.error(f"Error al generar interpretación SQL: {str(e)}")
            logger.error(f"Tipo de error: {type(e)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
            return {
                **state,
                "generation": f"Se obtuvieron los siguientes resultados de la consulta: {sql_result}",
                "needs_sql_interpretation": False
            }
    
    # Añadir nodos al grafo
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_relevance", grade_relevance)
    workflow.add_node("generate", generate)
    workflow.add_node("evaluate", evaluate)
    workflow.add_node("execute_query", execute_query)
    workflow.add_node("generate_sql_interpretation", generate_sql_interpretation)
    
    # Definir bordes - flujo simplificado
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade_relevance")
    workflow.add_edge("grade_relevance", "generate")
    workflow.add_edge("generate", "evaluate")
    
    # Definir condición para ejecución de consulta SQL o verificación de reintento
    def route_after_evaluate(state):
        """
        Determina qué hacer después de evaluar la respuesta:
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
            logger.info("Se detectó una consulta SQL válida. Procediendo a ejecutarla.")
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
        should_retry = (is_hallucination and is_unhelpful) and retry_count < max_retries
        
        if should_retry:
            logger.info(f"Reintentando (intento {retry_count+1}/{max_retries})")
            logger.info(f"- Contiene alucinaciones: {is_hallucination}")
            logger.info(f"- No aborda adecuadamente la pregunta: {is_unhelpful}")
            return "generate"
        else:
            if retry_count >= max_retries and (is_hallucination or is_unhelpful):
                logger.info(f"Máximo de reintentos alcanzado ({max_retries}). Finalizando con la mejor respuesta disponible.")
            else:
                logger.info("Generación exitosa. Finalizando.")
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
    
    # Añadir borde condicional para la decisión después de evaluar
    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "execute_query": "execute_query",
            "generate": "generate",
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
    
    return workflow
