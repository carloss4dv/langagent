"""
Módulo de inicialización del paquete langagent.

Este módulo inicializa el paquete langagent y proporciona acceso a sus componentes.
"""

__version__ = "0.1.0"

# Exportamos los módulos principales para facilitar su acceso desde fuera del paquete
from core.lang_chain_agent import LangChainAgent
from evaluation.evaluate import AgentEvaluator, guardar_resultados_deepeval
