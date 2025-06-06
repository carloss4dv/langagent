#!/usr/bin/env python3
"""
Script para analizar y visualizar la estructura del workflow de LangGraph.

Uso:
    python scripts/analyze_workflow.py
"""

import sys
import os
from pathlib import Path

# Añadir el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from langagent.core.lang_chain_agent import LangChainAgent
from langagent.config.config import VECTORSTORE_CONFIG, PATHS_CONFIG
from langagent.utils.terminal_visualization import print_title
import json


def print_workflow_structure(workflow):
    """
    Imprime la estructura del workflow de manera legible.
    """
    print_title("Estructura del Workflow")
    
    try:
        # Obtener el grafo interno
        graph = workflow.get_graph()
        
        print("🔗 NODOS DEL WORKFLOW:")
        print("-" * 50)
        
        # Listar todos los nodos
        nodes = graph.nodes
        for i, node_id in enumerate(nodes, 1):
            node_data = nodes[node_id]
            print(f"{i:2d}. {node_id}")
            if hasattr(node_data, 'data') and node_data.data:
                print(f"    - Tipo: {type(node_data.data).__name__}")
        
        print("\n🔀 BORDES DEL WORKFLOW:")
        print("-" * 50)
        
        # Listar todos los bordes
        edges = graph.edges
        for i, edge in enumerate(edges, 1):
            print(f"{i:2d}. {edge.source} → {edge.target}")
            if hasattr(edge, 'data') and edge.data:
                print(f"    - Condición: {edge.data}")
        
        print("\n📊 ESTADÍSTICAS:")
        print("-" * 50)
        print(f"Total de nodos: {len(nodes)}")
        print(f"Total de bordes: {len(edges)}")
        
        # Mostrar punto de entrada
        print(f"Punto de entrada: {graph.first_node() if hasattr(graph, 'first_node') else 'N/A'}")
        
    except Exception as e:
        print(f"Error al analizar la estructura: {e}")
        print("Intentando método alternativo...")
        
        # Método alternativo - inspeccionar el workflow directamente
        print("\n📋 INFORMACIÓN BÁSICA DEL WORKFLOW:")
        print("-" * 50)
        print(f"Tipo de workflow: {type(workflow).__name__}")
        
        if hasattr(workflow, '_nodes'):
            print(f"Nodos disponibles: {list(workflow._nodes.keys())}")
        
        if hasattr(workflow, '_edges'):
            print(f"Bordes disponibles: {len(workflow._edges)}")


def generate_mermaid_diagram(workflow):
    """
    Genera un diagrama Mermaid de la estructura del workflow.
    """
    print_title("Diagrama Mermaid del Workflow")
    
    try:
        graph = workflow.get_graph()
        
        print("```mermaid")
        print("graph TD")
        
        # Añadir nodos
        nodes = graph.nodes
        for node_id in nodes:
            # Limpiar nombres para Mermaid (sin espacios, caracteres especiales)
            clean_id = node_id.replace(" ", "_").replace("-", "_")
            display_name = node_id.replace("_", " ").title()
            print(f"    {clean_id}[\"{display_name}\"]")
        
        # Añadir bordes
        edges = graph.edges
        for edge in edges:
            source_clean = edge.source.replace(" ", "_").replace("-", "_")
            target_clean = edge.target.replace(" ", "_").replace("-", "_")
            print(f"    {source_clean} --> {target_clean}")
        
        print("```")
        
    except Exception as e:
        print(f"Error al generar diagrama Mermaid: {e}")
        
        # Diagrama manual basado en la estructura conocida
        print("```mermaid")
        print("graph TD")
        print("    A[\"Retrieve\"] --> B[\"Grade Relevance\"]")
        print("    B --> C[\"Generate\"]")
        print("    C --> D[\"Evaluate Response Granular\"]")
        print("    D --> E{\"Route Decision\"}")
        print("    E -->|\"SQL Query\"| F[\"Execute Query\"]")
        print("    E -->|\"Retry\"| G[\"Increment Retry Count\"]")
        print("    E -->|\"End\"| H[\"END\"]")
        print("    G --> A")
        print("    F --> I{\"Needs Interpretation?\"}")
        print("    I -->|\"Yes\"| J[\"Generate SQL Interpretation\"]")
        print("    I -->|\"No\"| H")
        print("    J --> H")
        print("```")


def analyze_workflow_metrics(workflow):
    """
    Analiza las métricas y configuración del workflow.
    """
    print_title("Configuración y Métricas del Workflow")
    
    print("⚙️  CONFIGURACIÓN ACTUAL:")
    print("-" * 50)
    
    # Configuración del vectorstore
    vector_config = {
        "Tipo de Vector DB": VECTORSTORE_CONFIG.get("vector_db_type", "N/A"),
        "Colección Principal": VECTORSTORE_CONFIG.get("collection_name", "N/A"),
        "Recuperación Adaptativa": VECTORSTORE_CONFIG.get("use_adaptive_retrieval", False),
        "Colecciones Adaptativas": VECTORSTORE_CONFIG.get("adaptive_collections", {}),
        "Chunk Size": VECTORSTORE_CONFIG.get("chunk_size", "N/A"),
        "K Retrieval": VECTORSTORE_CONFIG.get("k_retrieval", "N/A"),
        "Max Docs Total": VECTORSTORE_CONFIG.get("max_docs_total", "N/A"),
    }
    
    for key, value in vector_config.items():
        print(f"  {key}: {value}")
    
    # Métricas del workflow si están disponibles
    if hasattr(workflow, 'metrics_collector'):
        print("\n📈 MÉTRICAS DISPONIBLES:")
        print("-" * 50)
        print("  - Recolector de métricas: ✅ Disponible")
        print("  - Métricas por nodo: ✅ Activadas")
        print("  - Métricas de workflow: ✅ Activadas")
    else:
        print("\n📈 MÉTRICAS:")
        print("-" * 50)
        print("  - Recolector de métricas: ❌ No disponible")


def main():
    """
    Función principal del script de análisis.
    """
    print_title("Analizador de Workflow LangGraph")
    
    try:
        # Crear instancia del agente
        print("🔧 Inicializando agente...")
        
        # Usar configuración mínima para análisis
        agent = LangChainAgent(
            data_dir=PATHS_CONFIG["default_data_dir"],
            vectorstore_dir=PATHS_CONFIG["default_vectorstore_dir"],
            vector_db_type=VECTORSTORE_CONFIG["vector_db_type"]
        )
        
        print("✅ Agente inicializado correctamente")
        
        # Analizar estructura
        print_workflow_structure(agent.workflow)
        
        print("\n" + "="*60 + "\n")
        
        # Generar diagrama
        generate_mermaid_diagram(agent.workflow)
        
        print("\n" + "="*60 + "\n")
        
        # Analizar configuración
        analyze_workflow_metrics(agent.workflow)
        
        print("\n" + "="*60 + "\n")
        print_title("Análisis Completado")
        print("💡 Puedes copiar el diagrama Mermaid y pegarlo en:")
        print("   - https://mermaid.live/")
        print("   - GitHub/GitLab (en archivos .md)")
        print("   - Notion, Obsidian, etc.")
        
    except Exception as e:
        print(f"❌ Error durante el análisis: {e}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 