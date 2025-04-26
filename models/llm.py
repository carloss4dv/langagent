"""
Módulo para la configuración y uso de modelos de lenguaje (LLMs).

Este módulo proporciona funciones para configurar y utilizar diferentes modelos
de lenguaje para tareas como generación de texto, evaluación y clasificación.
"""

from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.utilities import SQLDatabase
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langagent.prompts import PROMPTS 
from langagent.config.config import LLM_CONFIG, SQL_CONFIG
import json
import re

# Clase para parsear JSON de manera más robusta
class RobustJsonOutputParser:
    """
    Un parseador de JSON más robusto que intenta extraer JSON válido incluso 
    cuando la respuesta no es perfecta.
    """
    def __init__(self, default_values=None):
        """
        Inicializa el parseador con valores por defecto.
        
        Args:
            default_values (dict, optional): Valores por defecto si el parseo falla.
        """
        self.default_values = default_values or {}
    
    def __call__(self, text):
        """
        Intenta extraer y parsear JSON de un texto.
        
        Args:
            text (str): El texto que contiene JSON.
            
        Returns:
            dict: El objeto JSON parseado o los valores por defecto.
        """
        if not text:
            return self.default_values
        
        # Primero intentar parsear directamente si es JSON válido
        try:
            if isinstance(text, dict):
                return text
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Intentar encontrar JSON usando expresiones regulares
        try:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Si todo falla, extraer manualmente campos clave
        result = self.default_values.copy()
        
        # Buscar campos específicos
        explanation_match = re.search(r'"explanation"\s*:\s*"([^"]*)"', text)
        if explanation_match:
            result["explanation"] = explanation_match.group(1)
        
        query_match = re.search(r'"query"\s*:\s*"([^"]*)"', text)
        if query_match:
            result["query"] = query_match.group(1)
        
        return result

def _get_prompt_template(llm, prompt_key: str):
    """Helper para obtener plantillas del modelo correcto."""
    model_name = llm.model
    if "llama" in llm.model:
        model_name = "llama"
    elif "qwen" in llm.model:
        model_name = "qwen"
    try:
        return PROMPTS[model_name][prompt_key]
    except KeyError:
        raise ValueError(f"No prompt found for model '{model_name}' and key '{prompt_key}'")

def create_llm(model_name: str = None, temperature: float = None, format: str = None, max_tokens: int = None):
    """
    Crea un modelo de lenguaje basado en Ollama.
    
    Args:
        model_name (str, optional): Nombre del modelo a utilizar.
        temperature (float, optional): Temperatura para la generación (0-1).
        format (str, optional): Formato de salida ('json' u otro).
        max_tokens (int, optional): Número máximo de tokens para la generación.
        
    Returns:
        ChatOllama: Modelo de lenguaje configurado.
    """
    # Usar valores de configuración si no se proporcionan argumentos
    model_name = model_name or LLM_CONFIG["default_model"]
    temperature = temperature if temperature is not None else LLM_CONFIG["model_temperature"]
    format = format or LLM_CONFIG["model_format"]
    max_tokens = max_tokens if max_tokens is not None else LLM_CONFIG["max_tokens"]
    
    return ChatOllama(
        model=model_name, 
        format=format, 
        temperature=temperature,
        max_tokens=max_tokens
    )


def create_rag_sql_chain(llm, db_uri, dialect="sqlite"):
    """
    Crea una cadena combinada RAG + SQL que genera tanto una respuesta como una consulta SQL.
    
    Esta cadena utiliza primero un enfoque RAG para entender el contexto y luego genera
    una consulta SQL basada en la pregunta. La consulta se puede ejecutar posteriormente.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        db_uri: URI de conexión a la base de datos SQL.
        dialect: Dialecto SQL a utilizar (por defecto: sqlite).
        
    Returns:
        dict: Diccionario con dos cadenas - 'answer_chain' para RAG y 'sql_query_chain' para generar SQL.
    """
    # Crear la conexión a la base de datos
    db = SQLDatabase.from_uri(db_uri)
    
    # Obtener información del esquema
    table_info = db.get_table_info()
    
    # Crear plantilla para generar consultas SQL
    sql_prompt = PromptTemplate.from_template(
        """
        Dado el contexto y la pregunta, crea una consulta SQL sintácticamente correcta para {dialect}.
        A menos que se especifique un número de resultados, limita a 10 resultados máximo.
        Puedes ordenar los resultados por una columna relevante para mostrar los ejemplos más interesantes.
        
        Nunca consultes todas las columnas de una tabla, solo selecciona las columnas relevantes para la pregunta.
        
        Presta atención a usar solo los nombres de columnas que puedes ver en la descripción del esquema.
        Ten cuidado de no consultar columnas que no existen. También, presta atención a qué columna está en qué tabla.
        
        Solo usa las siguientes tablas:
        {table_info}
        
        Contexto: {context}
        Pregunta: {question}
        
        IMPORTANTE: Tu respuesta debe ser un objeto JSON válido con este formato exacto:
        {{
            "explanation": "Una explicación breve de lo que hace esta consulta SQL",
            "query": "SELECT ... FROM ... WHERE ..."
        }}
        
        Asegúrate de que el JSON sea válido y que tanto "explanation" como "query" estén presentes.
        NO incluyas comillas triples, marcadores de código ni ningún otro formato adicional alrededor del JSON.
        """
    )
    
    # Configurar valores predeterminados para el parseador robusto
    default_sql_values = {
        "explanation": "No se pudo generar una explicación",
        "query": "SELECT * FROM " + SQL_CONFIG["default_table"] + " LIMIT 10"
    }
    
    # Crear la cadena para generar consultas SQL con el parseador robusto
    sql_query_chain = (
        {
            "dialect": lambda _: dialect,
            "table_info": lambda _: table_info,
            "context": RunnablePassthrough(),
            "question": RunnablePassthrough()
        }
        | sql_prompt
        | llm
        | RobustJsonOutputParser(default_values=default_sql_values)
    )
    
    # Crear la cadena RAG normal (para generar respuestas basadas en contexto)
    rag_prompt_template = _get_prompt_template(llm, "rag")
    prompt = PromptTemplate.from_template(rag_prompt_template)
    
    answer_chain = (
        {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
        | prompt
        | llm
    )
    
    return {
        "answer_chain": answer_chain,
        "sql_query_chain": sql_query_chain
    }

def create_context_generator(llm):
    """
    Crea un generador de contexto para mejorar la calidad de los chunks.
    
    Este generador utiliza el LLM principal para crear una descripción contextual
    para cada chunk basándose en el documento completo, mejorando así su recuperación.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena para generar contexto.
    """
    # Prompt para generación de contexto
    prompt_template = _get_prompt_template(llm, "context_generator")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["document", "chunk"],
    )
    
    # Valores predeterminados para el parseador de contexto
    default_context_values = {
        "context_description": "Información sobre el documento",
        "relevance_score": 0.5
    }
    
    # Definir la cadena de generación de contexto con el parseador robusto
    context_generator_chain = prompt | llm | RobustJsonOutputParser(default_values=default_context_values)
    
    return context_generator_chain

def create_rag_chain(llm):
    """
    Crea una cadena de RAG (Retrieval Augmented Generation).
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena de RAG configurada.
    """
    # Prompt para RAG
    prompt_template = _get_prompt_template(llm, "rag")
    prompt = PromptTemplate.from_template(prompt_template)
    
    # Definimos la cadena de RAG
    rag_chain = (
        {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
        | prompt
        | llm
    )
    
    return rag_chain

def create_retrieval_grader(llm):
    """
    Crea un evaluador para determinar si un documento es relevante para una pregunta.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena de evaluación configurada.
    """
    # Prompt para evaluar relevancia de documentos
    prompt_template = _get_prompt_template(llm, "retrieval_grader")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["document", "question"],
    )
    
    # Valores predeterminados para el evaluador de recuperación
    default_retrieval_values = {
        "is_relevant": True,
        "relevance_score": 0.7,
        "explanation": "Documento posiblemente relevante para la consulta"
    }
    
    retrieval_grader = prompt | llm | RobustJsonOutputParser(default_values=default_retrieval_values)
    return retrieval_grader

def create_hallucination_grader(llm):
    """
    Crea un evaluador para determinar si una generación contiene alucinaciones.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena de evaluación configurada.
    """
    # Prompt para evaluar alucinaciones
    prompt_template = _get_prompt_template(llm, "hallucination_grader")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["documents", "generation"],
    )
    
    # Valores predeterminados para el evaluador de alucinaciones
    default_hallucination_values = {
        "has_hallucination": False,
        "confidence": 0.7,
        "explanation": "No se detectaron alucinaciones evidentes"
    }
    
    hallucination_grader = prompt | llm | RobustJsonOutputParser(default_values=default_hallucination_values)
    return hallucination_grader

def create_answer_grader(llm):
    """
    Crea un evaluador para determinar si una respuesta es útil para resolver una pregunta.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena de evaluación configurada.
    """
    # Prompt para evaluar utilidad de respuestas
    prompt_template = _get_prompt_template(llm, "answer_grader")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["generation", "question"],
    )
    
    # Valores predeterminados para el evaluador de respuestas
    default_answer_values = {
        "is_helpful": True,
        "helpfulness_score": 0.7,
        "explanation": "La respuesta parece abordar la pregunta"
    }
    
    answer_grader = prompt | llm | RobustJsonOutputParser(default_values=default_answer_values)
    return answer_grader

def create_question_router(llm):
    """
    Crea un router para determinar si una pregunta debe dirigirse a vectorstore o búsqueda web.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena de enrutamiento configurada.
    """
    # Prompt para enrutamiento de preguntas
    prompt_template = _get_prompt_template(llm, "question_router")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["question"],
    )
    
    # Valores predeterminados para el router de preguntas
    default_router_values = {
        "route_to": "vectorstore",
        "confidence": 0.8,
        "explanation": "La pregunta parece ser sobre información interna"
    }
    
    question_router = prompt | llm | RobustJsonOutputParser(default_values=default_router_values)
    return question_router

def create_query_rewriter(llm):
    """
    Crea un reescritor de consultas para mejorar la recuperación de información.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena de reescritura de consultas configurada.
    """
    # Prompt para reescritura de consultas
    prompt_template = _get_prompt_template(llm, "query_rewriter")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["question"],
    )
    
    # Aquí no usamos JsonOutputParser porque queremos texto plano
    query_rewriter = prompt | llm
    return query_rewriter
