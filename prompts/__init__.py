"""
Módulo de prompts para SEGEDA (DATUZ).
Organizado por modelo de IA para facilitar el mantenimiento.
"""

from .llama import PROMPTS as LLAMA_PROMPTS
from .mistral import PROMPTS as MISTRAL_PROMPTS  
from .qwen import PROMPTS as QWEN_PROMPTS

# Mantener compatibilidad con la estructura anterior
PROMPTS = {
    "llama": LLAMA_PROMPTS,
    "mistral-small-3.1:24b": MISTRAL_PROMPTS,
    "qwen": QWEN_PROMPTS
}

# Funciones de utilidad para acceder a las prompts
def get_prompt(model_name: str, prompt_type: str) -> str:
    """
    Obtiene una prompt específica para un modelo y tipo dados.
    
    Args:
        model_name: Nombre del modelo ('llama', 'mistral-small-3.1:24b', 'qwen')
        prompt_type: Tipo de prompt ('rag', 'context_generator', etc.)
    
    Returns:
        str: La prompt solicitada
        
    Raises:
        KeyError: Si el modelo o tipo de prompt no existe
    """
    return PROMPTS[model_name][prompt_type]

def list_models() -> list:
    """Retorna lista de modelos disponibles."""
    return list(PROMPTS.keys())

def list_prompt_types(model_name: str) -> list:
    """
    Retorna lista de tipos de prompt disponibles para un modelo.
    
    Args:
        model_name: Nombre del modelo
        
    Returns:
        list: Lista de tipos de prompt disponibles
    """
    return list(PROMPTS[model_name].keys())

def validate_prompt_structure():
    """Valida que todos los modelos tienen los tipos de prompt esperados."""
    expected_types = {
        'rag', 'context_generator', 'retrieval_grader', 
        'hallucination_grader', 'answer_grader', 'query_rewriter',
        'clarification_generator', 'sql_generator', 'sql_interpretation'
    }
    
    issues = []
    for model_name, model_prompts in PROMPTS.items():
        model_types = set(model_prompts.keys())
        
        # Verificar tipos faltantes
        missing = expected_types - model_types
        if missing:
            issues.append(f"Modelo '{model_name}' falta tipos: {missing}")
            
        # Verificar tipos extra
        extra = model_types - expected_types
        if extra:
            issues.append(f"Modelo '{model_name}' tiene tipos extra: {extra}")
    
    return issues

__all__ = [
    'PROMPTS', 
    'LLAMA_PROMPTS', 
    'MISTRAL_PROMPTS', 
    'QWEN_PROMPTS',
    'get_prompt',
    'list_models', 
    'list_prompt_types',
    'validate_prompt_structure'
]
