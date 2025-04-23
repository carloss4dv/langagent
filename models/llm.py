"""
Módulo para la configuración y uso de modelos de lenguaje (LLMs).

Este módulo proporciona funciones para configurar y utilizar diferentes modelos
de lenguaje para tareas como generación de texto, evaluación y clasificación.
"""

from langchain_ollama import ChatOllama
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langagent.prompts import PROMPTS 
from langagent.config.config import LLM_CONFIG

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

def create_llm(model_name: str = None, temperature: float = None, format: str = None):
    """
    Crea un modelo de lenguaje basado en Ollama.
    
    Args:
        model_name (str, optional): Nombre del modelo a utilizar.
        temperature (float, optional): Temperatura para la generación (0-1).
        format (str, optional): Formato de salida ('json' u otro).
        
    Returns:
        ChatOllama: Modelo de lenguaje configurado.
    """
    # Usar valores de configuración si no se proporcionan argumentos
    model_name = model_name or LLM_CONFIG["default_model"]
    temperature = temperature if temperature is not None else LLM_CONFIG["model_temperature"]
    format = format or LLM_CONFIG["model_format"]
    
    return ChatOllama(model=model_name, format=format, temperature=temperature)

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
    
    retrieval_grader = prompt | llm | JsonOutputParser()
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
    
    hallucination_grader = prompt | llm | JsonOutputParser()
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
    
    answer_grader = prompt | llm | JsonOutputParser()
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
    
    question_router = prompt | llm | JsonOutputParser()
    return question_router
