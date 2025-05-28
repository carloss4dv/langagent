"""
Paquete langagent para el sistema de consultas SEGEDA.

Este módulo inicializa el paquete langagent y proporciona acceso a sus componentes.
"""

__version__ = "0.1.0"

# Exportamos los módulos principales para facilitar su acceso desde fuera del paquete
try:
    # Intentamos importar de forma relativa para cuando se usa como módulo
    from .core.lang_chain_agent import LangChainAgent
    from .evaluation.evaluate import AgentEvaluator
except ImportError:
    # Fallback a importación absoluta para cuando se ejecuta directamente
    import sys
    import os
    
    # Añadir el directorio actual al path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        