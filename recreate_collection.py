#!/usr/bin/env python
"""
Script para recrear la colección unificada de Milvus.

Este script elimina y recrea la colección unificada en Milvus,
útil para limpiar datos corruptos o cambiar configuraciones.
"""

import sys
import os

# Agregar el directorio padre al path para importar módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from langagent.core.lang_chain_agent import LangChainAgent
from langagent.config.config import VECTORSTORE_CONFIG

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

def main():
    """
    Función principal para recrear la colección unificada.
    """
    try:
        logger.info("Inicializando agente...")
        
        # Verificar que estamos usando Milvus
        vector_db_type = VECTORSTORE_CONFIG.get("vector_db_type", "milvus")
        if vector_db_type != "milvus":
            logger.error("ERROR: Este script solo funciona con Milvus como vectorstore")
            return
        
        # Verificar que estamos en modo de colección única
        if not VECTORSTORE_CONFIG.get("use_unified_collection", False):
            logger.error("ERROR: Este script solo funciona en modo de colección única")
            return
        
        # Crear el agente (esto cargará o creará la vectorstore)
        logger.info("Recreando colección unificada...")
        agent = LangChainAgent()
        
        # Si llegamos aquí, la recreación fue exitosa
        logger.info("La colección unificada ha sido recreada correctamente.")
        logger.info(f"Nombre de la colección: {VECTORSTORE_CONFIG.get('unified_collection_name', 'UnifiedKnowledgeBase')}")
        
    except Exception as e:
        logger.error(f"Error durante la recreación: {e}")
        logger.error("No se pudo recrear la colección unificada. Revisa los logs para más detalles.")

if __name__ == "__main__":
    main() 