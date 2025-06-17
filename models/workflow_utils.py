"""
Utilidades determinísticas para el flujo de control del agente.

Este módulo contiene funciones de utilidad que no dependen directamente de LLM,
incluyendo análisis de texto, normalización, validación y lógica de negocio
específica del dominio SEGEDA.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document

# Importar configuraciones necesarias
from langagent.models.constants import (
    AMBITOS_CUBOS, CUBO_TO_AMBITO, AMBITO_KEYWORDS, 
    AMBITO_EN_ES, CUBO_EN_ES
)
from langagent.config.config import CHUNK_STRATEGY_CONFIG

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)


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
    pattern = r'_(167|256|307|512|755|1024|369|646|1094)'
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


def detect_insufficient_info_response(generation: str) -> bool:
    """
    Detecta si una respuesta indica información insuficiente para evitar bucles infinitos.
    
    Args:
        generation (str): Respuesta generada por el LLM
        
    Returns:
        bool: True si la respuesta indica información insuficiente
    """
    insufficient_info_phrases = [
        "no se encontró información",
        "no tengo suficiente información",
        "no hay información",
        "información no disponible",
        "no puedo responder",
        "no dispongo de información",
        "no se encuentra información"
    ]
    
    generation_lower = generation.lower()
    return any(phrase in generation_lower for phrase in insufficient_info_phrases)


def extract_sql_query_from_response(sql_query) -> str:
    """
    Extrae la consulta SQL del formato de respuesta, manejando diferentes formatos.
    
    Args:
        sql_query: Respuesta que puede ser string, JSON o diccionario
        
    Returns:
        str: Consulta SQL extraída
    """
    # Comprobar si sql_query es un string JSON 
    if isinstance(sql_query, str):
        try:
            # Intentar parsear como JSON
            if sql_query.strip().startswith('{'):
                query_data = json.loads(sql_query)
                if isinstance(query_data, dict):
                    # Buscar la consulta en diferentes claves posibles
                    if "query" in query_data:
                        return query_data["query"]
                    elif "sql" in query_data:
                        return query_data["sql"]
        except json.JSONDecodeError:
            # Si no es JSON válido, usar el string como está
            pass
    
    return str(sql_query)


def check_metrics_success(evaluation_metrics: Dict[str, Any]) -> bool:
    """
    Verifica si todas las métricas de evaluación superan los umbrales definidos.
    
    Args:
        evaluation_metrics (Dict[str, Any]): Métricas de evaluación
        
    Returns:
        bool: True si todas las métricas superan los umbrales
    """
    faithfulness = evaluation_metrics.get("faithfulness", 0.0)
    context_precision = evaluation_metrics.get("context_precision", 0.0)
    context_recall = evaluation_metrics.get("context_recall", 0.0)
    answer_relevance = evaluation_metrics.get("answer_relevance", 0.0)
    
    thresholds = CHUNK_STRATEGY_CONFIG["evaluation_thresholds"]
    return (
        faithfulness >= thresholds["faithfulness"] and
        context_precision >= thresholds["context_precision"] and
        context_recall >= thresholds["context_recall"] and
        answer_relevance >= thresholds["answer_relevance"]
    )


def should_terminate_workflow(retry_count: int, generation: str, evaluation_metrics: Dict[str, Any]) -> bool:
    """
    Determina si el workflow debe terminar basado en diversos criterios.
    
    Args:
        retry_count (int): Número actual de reintentos
        generation (str): Respuesta generada
        evaluation_metrics (Dict[str, Any]): Métricas de evaluación
        
    Returns:
        bool: True si el workflow debe terminar
    """
    # Terminar si se alcanzó el máximo de reintentos
    max_retries = CHUNK_STRATEGY_CONFIG["max_retries"]
    if retry_count >= max_retries:
        return True
    
    # Terminar si todas las métricas son exitosas
    if check_metrics_success(evaluation_metrics):
        return True
    
    # Terminar si la respuesta indica información insuficiente
    if detect_insufficient_info_response(generation):
        return True
    
    return False


def execute_sql_query(sql_query: str, sql_config: Dict[str, Any]) -> str:
    """
    Ejecuta una consulta SQL y devuelve el resultado.
    
    Args:
        sql_query (str): Consulta SQL a ejecutar
        sql_config (Dict[str, Any): Configuración de la base de datos
        
    Returns:
        str: Resultado de la consulta o mensaje de error
    """
    from langchain_community.utilities import SQLDatabase
    from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
    
    # Extraer la consulta SQL del formato si es necesario
    clean_sql_query = extract_sql_query_from_response(sql_query)
    
    logger.info(f"Ejecutando consulta SQL: {clean_sql_query}")
    
    try:
        # Crear la conexión a la base de datos y herramienta de consulta
        if sql_config.get("db_uri"):
            db = SQLDatabase.from_uri(sql_config.get("db_uri"))
            execute_query_tool = QuerySQLDatabaseTool(db=db)
            
            # Ejecutar la consulta
            result = execute_query_tool.invoke(clean_sql_query)
            logger.info("Consulta ejecutada con éxito.")
            return result
            
        else:
            error_msg = "Error: No se ha configurado la URI de la base de datos"
            logger.error(error_msg)
            return error_msg
            
    except Exception as e:
        error_msg = f"Error al ejecutar la consulta SQL: {str(e)}"
        logger.error(error_msg)
        return error_msg

def safe_get_attribute(obj, attr, default=None):
    """
    Obtiene un atributo de un objeto de forma segura.
    
    Args:
        obj: Objeto del cual obtener el atributo
        attr: Nombre del atributo
        default: Valor por defecto si no existe o hay error
        
    Returns:
        Valor del atributo o valor por defecto
    """
    try:
        if isinstance(obj, dict):
            return obj.get(attr, default)
        elif hasattr(obj, attr):
            return getattr(obj, attr, default)
        else:
            return default
    except:
        return default

def process_sql_result(result):
    """
    Procesa el resultado de una consulta SQL de forma segura.
    
    Args:
        result: Resultado de la consulta SQL
        
    Returns:
        Resultado procesado
    """
    try:
        # Si es un string, devolverlo tal como está
        if isinstance(result, str):
            return result
        
        # Si es una lista de tuplas, procesarla
        if isinstance(result, list):
            return result
        
        # Si tiene atributos como un objeto, intentar extraer información
        if hasattr(result, '__dict__'):
            return str(result)
        
        # Por defecto, convertir a string
        return str(result)
        
    except Exception as e:
        logger.error(f"Error al procesar resultado SQL: {str(e)}")
        return f"Error al procesar resultado: {str(e)}"