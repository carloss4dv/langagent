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
from langagent.prompts import get_prompt, PROMPTS
from langagent.config.config import LLM_CONFIG, SQL_CONFIG

def _get_prompt_template(llm, prompt_key: str):
    """Helper para obtener plantillas del modelo correcto."""
    model_name = llm.model
    if "llama" in llm.model:
        model_name = "llama"
    elif "qwen" in llm.model:
        model_name = "qwen"
    elif "mistral" in llm.model:
        model_name = "mistral-small-3.1:24b"
    try:
        # Usar la nueva función de utilidad get_prompt
        return get_prompt(model_name, prompt_key)
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
        max_tokens=max_tokens,
        timeout=10,  # Timeout de 60 segundos para evitar bloqueos
        streaming=False  # Desactivar streaming para evitar problemas de compatibilidad
    )


def create_rag_sql_chain(llm, db_uri=SQL_CONFIG["db_uri"], dialect=SQL_CONFIG["dialect"]):
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
    sql_prompt_template = _get_prompt_template(llm, "sql_generator")
    sql_prompt = PromptTemplate.from_template(sql_prompt_template)
    
    # Crear la cadena para generar consultas SQL
    sql_query_chain = (
        {
            "dialect": lambda _: dialect,
            "table_info": lambda _: table_info,
            "context": lambda x: x["context"] if isinstance(x, dict) and "context" in x else x,
            "question": lambda x: x["question"] if isinstance(x, dict) and "question" in x else x
        }
        | sql_prompt
        | llm
        | (lambda x: x.content)
    )
    
    # Crear la cadena RAG normal (para generar respuestas basadas en contexto)
    rag_prompt_template = _get_prompt_template(llm, "rag")
    prompt = PromptTemplate.from_template(rag_prompt_template)
    
    answer_chain = (
        {
            "context": lambda x: x["context"] if isinstance(x, dict) and "context" in x else x,
            "question": lambda x: x["question"] if isinstance(x, dict) and "question" in x else x
        }
        | prompt
        | llm
        | JsonOutputParser()
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
    Incorpora conciencia jerárquica basada en el tamaño del chunk dinámicamente.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena para generar contexto con conciencia jerárquica.
    """
    # Prompt para generación de contexto
    prompt_template = _get_prompt_template(llm, "context_generator")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["document", "chunk", "chunk_size"],
    )
    
    # Definir la cadena de generación de contexto con JsonOutputParser
    # El chunk_size ahora debe pasarse dinámicamente en el input
    context_generator_chain = (
        {
            "document": lambda x: x["document"] if isinstance(x, dict) and "document" in x else x,
            "chunk": lambda x: x["chunk"] if isinstance(x, dict) and "chunk" in x else x,
            "chunk_size": lambda x: x.get("chunk_size", 512) if isinstance(x, dict) else 512  # Obtener dinámicamente o usar default
        }
        | prompt 
        | llm 
        | JsonOutputParser()
    )
    
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
        {
            "context": lambda x: x["context"] if isinstance(x, dict) and "context" in x else x,
            "question": lambda x: x["question"] if isinstance(x, dict) and "question" in x else x
        }
        | prompt
        | llm
        | JsonOutputParser()
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
        input_variables=["content", "metadata", "source", "question", "ambito"],
    )
    
    retrieval_grader = prompt | llm | JsonOutputParser()
    return retrieval_grader

def create_granular_evaluator(llm):
    """
    Crea un evaluador granular que evalúa múltiples métricas de calidad en una sola evaluación.
    
    Este evaluador reemplaza a los evaluadores individuales (hallucination_grader y answer_grader)
    y proporciona métricas detalladas para la recuperación adaptativa.
    
    Args:
        llm: Modelo de lenguaje a utilizar (debe ser qwen para tener el prompt correspondiente).
        
    Returns:
        Chain: Cadena de evaluación granular configurada.
    """
    # Prompt para evaluación granular (solo disponible para qwen)
    prompt_template = _get_prompt_template(llm, "granular_evaluator")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["question", "documents", "generation"],
    )
    
    granular_evaluator = prompt | llm | JsonOutputParser()
    return granular_evaluator

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
    
    question_router = prompt | llm | JsonOutputParser()
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

def create_clarification_generator(llm):
    """
    Crea un generador de preguntas de clarificación para el agente de ámbito.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena de generación de clarificación configurada.
    """
    # Prompt para generar preguntas de clarificación
    prompt_template = _get_prompt_template(llm, "clarification_generator")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["question", "context"],
    )
    
    # Definir la cadena de generación de clarificación
    # No usamos JsonOutputParser porque queremos texto plano para la pregunta de clarificación
    clarification_generator = prompt | llm
    return clarification_generator

def create_sql_interpretation(llm):
    """
    Crea un interpretador de resultados SQL para el sistema SEGEDA.
    
    Args:
        llm: Modelo de lenguaje a utilizar.
        
    Returns:
        Chain: Cadena de interpretación de SQL configurada.
    """
    # Prompt para interpretar resultados SQL
    prompt_template = _get_prompt_template(llm, "sql_interpretation")
    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"],
    )
    
    # Definir la cadena de interpretación SQL con JsonOutputParser
    sql_interpretation_chain = (
        {
            "context": lambda x: x["context"] if isinstance(x, dict) and "context" in x else x,
            "question": lambda x: x["question"] if isinstance(x, dict) and "question" in x else x
        }
        | prompt
        | llm
        | JsonOutputParser()
    )
    return sql_interpretation_chain
