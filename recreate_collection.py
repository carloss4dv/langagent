#!/usr/bin/env python
"""
Script para recrear la colección unificada de Milvus.

Este script es útil cuando hay problemas con la colección existente y
necesitas recrearla desde cero con todos los documentos.
"""

import sys
import os
from dotenv import load_dotenv

# Asegurarse de que el módulo está en el path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar variables de entorno
load_dotenv()

from langagent.core.lang_chain_agent import LangChainAgent
from langagent.utils.terminal_visualization import print_title

def main():
    """Función principal para recrear la colección unificada."""
    print_title("RECREACIÓN DE COLECCIÓN UNIFICADA DE MILVUS")
    
    # Crear instancia del agente
    print("Inicializando agente...")
    agent = LangChainAgent(vector_db_type="milvus")
    
    # Verificar que estamos usando Milvus con colección única
    from langagent.config.config import VECTORSTORE_CONFIG
    if VECTORSTORE_CONFIG.get("vector_db_type", "").lower() != "milvus":
        print("ERROR: Este script solo funciona con Milvus como vectorstore")
        return 1
        
    if not VECTORSTORE_CONFIG.get("use_single_collection", False):
        print("ERROR: Este script solo funciona en modo de colección única")
        return 1
    
    # Recrear la colección
    print("Recreando colección unificada...")
    success = agent.recreate_unified_collection()
    
    if success:
        print_title("RECREACIÓN EXITOSA")
        print("La colección unificada ha sido recreada correctamente.")
        print(f"Nombre de la colección: {VECTORSTORE_CONFIG.get('unified_collection_name', 'UnifiedKnowledgeBase')}")
        return 0
    else:
        print_title("ERROR EN LA RECREACIÓN")
        print("No se pudo recrear la colección unificada. Revisa los logs para más detalles.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 