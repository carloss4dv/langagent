#!/usr/bin/env python3
"""
Script para visualizar la máquina de estados del workflow de LangGraph.

Genera diagramas del workflow en diferentes formatos (PNG, SVG, Mermaid).
Se puede ejecutar desde cualquier directorio.

Uso:
    python visualize_workflow.py [--format png|svg|mermaid] [--output archivo]
"""

import argparse
import sys
import os
from pathlib import Path

def setup_path():
    """Configura el path para importar el módulo langagent desde cualquier ubicación."""
    # Obtener el directorio actual del script
    script_dir = Path(__file__).parent.absolute()
    
    # Buscar el directorio langagent
    langagent_path = None
    
    # Intentar diferentes ubicaciones posibles
    possible_paths = [
        script_dir / "langagent",  # Mismo directorio
        script_dir.parent / "langagent",  # Directorio padre
        script_dir / ".." / "langagent",  # Relativo al padre
    ]
    
    for path in possible_paths:
        if path.exists() and (path / "__init__.py").exists():
            langagent_path = path.parent
            break
    
    if langagent_path is None:
        print("❌ Error: No se pudo encontrar el módulo 'langagent'")
        print("Asegúrate de ejecutar este script desde un directorio que tenga acceso al módulo langagent")
        sys.exit(1)
    
    # Añadir al path si no está ya
    langagent_str = str(langagent_path)
    if langagent_str not in sys.path:
        sys.path.insert(0, langagent_str)
        print(f"✅ Módulo langagent encontrado en: {langagent_path}")
    
    return langagent_path

def create_workflow_diagram(format_type="mermaid", output_file=None):
    """
    Crea un diagrama del workflow en el formato especificado.
    
    Args:
        format_type (str): Formato del diagrama ('png', 'svg', 'mermaid')
        output_file (str): Archivo de salida (opcional)
    """
    try:
        # Importar después de configurar el path
        from langagent.core.lang_chain_agent import LangChainAgent
        from langagent.config.config import VECTORSTORE_CONFIG
        
        print("🔧 Inicializando agente...")
        
        # Crear una instancia mínima del agente para obtener el workflow
        agent = LangChainAgent()
        workflow = agent.workflow
        
        print("📊 Generando diagrama del workflow...")
        
        if format_type.lower() == "mermaid":
            # Generar diagrama Mermaid
            try:
                # LangGraph puede generar diagramas Mermaid directamente
                mermaid_code = workflow.get_graph().draw_mermaid()
                
                # Determinar archivo de salida
                if output_file is None:
                    output_file = "workflow_diagram.md"
                
                # Escribir archivo Mermaid
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("# Diagrama del Workflow LangAgent\n\n")
                    f.write("```mermaid\n")
                    f.write(mermaid_code)
                    f.write("\n```\n")
                
                print(f"✅ Diagrama Mermaid generado: {output_file}")
                print("💡 Puedes visualizarlo en GitHub, VS Code con extensión Mermaid, o en mermaid.live")
                
            except Exception as e:
                print(f"❌ Error generando Mermaid: {e}")
                print("🔄 Intentando método alternativo...")
                _generate_manual_mermaid(workflow, output_file)
        
        elif format_type.lower() in ["png", "svg"]:
            try:
                # Intentar generar imagen con graphviz
                _generate_image_diagram(workflow, format_type, output_file)
            except ImportError:
                print("❌ Error: Se requiere 'graphviz' para generar imágenes PNG/SVG")
                print("Instala con: pip install graphviz")
                print("🔄 Generando diagrama Mermaid como alternativa...")
                _generate_manual_mermaid(workflow, "workflow_diagram_fallback.md")
        
        else:
            print(f"❌ Formato no soportado: {format_type}")
            print("Formatos disponibles: png, svg, mermaid")
            return False
        
        # Mostrar información adicional del workflow
        _show_workflow_info(agent)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def _generate_image_diagram(workflow, format_type, output_file):
    """Genera diagrama de imagen usando graphviz."""
    try:
        import graphviz
        
        # Determinar archivo de salida
        if output_file is None:
            output_file = f"workflow_diagram.{format_type}"
        
        # Generar diagrama con LangGraph + graphviz
        graph_data = workflow.get_graph()
        
        # Crear grafo con graphviz
        dot = graphviz.Digraph(comment='LangAgent Workflow')
        dot.attr(rankdir='TB', size='12,8')
        dot.attr('node', shape='box', style='rounded,filled', fillcolor='lightblue')
        
        # Añadir nodos
        for node in graph_data.nodes:
            dot.node(node, node.replace('_', ' ').title())
        
        # Añadir bordes
        for edge in graph_data.edges:
            dot.edge(edge.source, edge.target)
        
        # Renderizar
        dot.render(output_file, format=format_type, cleanup=True)
        print(f"✅ Diagrama {format_type.upper()} generado: {output_file}.{format_type}")
        
    except Exception as e:
        raise e

def _generate_manual_mermaid(workflow, output_file):
    """Genera diagrama Mermaid manualmente como fallback."""
    if output_file is None:
        output_file = "workflow_diagram_manual.md"
    
    # Crear diagrama Mermaid manualmente basado en la estructura conocida
    mermaid_content = """# Diagrama del Workflow LangAgent

```mermaid
graph TD
    A[retrieve] --> B[grade_relevance]
    B --> C[generate]
    C --> D[evaluate_response_granular]
    D --> E{route_after_granular_evaluation}
    E -->|SQL Query| F[execute_query]
    E -->|Retry| G[increment_retry_count]
    E -->|End| H[END]
    G --> A
    F --> I{route_after_execute_query}
    I -->|Needs Interpretation| J[generate_sql_interpretation]
    I -->|End| H
    J --> H
    
    %% Styling
    classDef startEnd fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef process fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef decision fill:#fff3e0,stroke:#e65100,stroke-width:2px
    
    class A,H startEnd
    class B,C,D,F,G,J process
    class E,I decision
```

## Descripción del Workflow

### Nodos principales:
- **retrieve**: Recupera documentos relevantes
- **grade_relevance**: Evalúa relevancia de documentos
- **generate**: Genera respuesta o consulta SQL
- **evaluate_response_granular**: Evalúa calidad de la respuesta
- **increment_retry_count**: Incrementa contador de reintentos
- **execute_query**: Ejecuta consulta SQL
- **generate_sql_interpretation**: Interpreta resultados SQL

### Decisiones:
- **route_after_granular_evaluation**: Decide si reintentar, ejecutar SQL o terminar
- **route_after_execute_query**: Decide si generar interpretación o terminar

### Flujo de reintentos:
1. Si las métricas son bajas → increment_retry_count → retrieve (máximo 3 intentos)
2. Si se detecta consulta SQL → execute_query
3. Si las métricas son buenas o se alcanza límite → END
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(mermaid_content)
    
    print(f"✅ Diagrama Mermaid manual generado: {output_file}")

def _show_workflow_info(agent):
    """Muestra información adicional sobre el workflow."""
    print("\n📋 Información del Workflow:")
    print("=" * 50)
    
    # Información de configuración
    print(f"🔧 Recuperación adaptativa: {agent.vectorstore_handler}")
    print(f"🎯 Modelo principal: {agent.local_llm}")
    print(f"🎯 Modelo secundario: {agent.local_llm2}")
    print(f"🎯 Modelo terciario: {agent.local_llm3}")
    
    # Información de retrievers
    if hasattr(agent, 'adaptive_retrievers') and agent.adaptive_retrievers:
        print(f"📊 Retrievers adaptativos: {list(agent.adaptive_retrievers.keys())}")
    else:
        print("📊 Retrievers adaptativos: No configurados")
    
    # Información de métricas
    if hasattr(agent.workflow, 'metrics_collector'):
        print("📈 Recolector de métricas: Configurado")
    else:
        print("📈 Recolector de métricas: No configurado")

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Visualiza la máquina de estados del workflow LangAgent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
    python visualize_workflow.py                           # Genera Mermaid por defecto
    python visualize_workflow.py --format png              # Genera imagen PNG
    python visualize_workflow.py --format svg --output mi_diagrama  # SVG personalizado
    python visualize_workflow.py --format mermaid --output flujo.md # Mermaid personalizado
        """
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['png', 'svg', 'mermaid'],
        default='mermaid',
        help='Formato del diagrama (default: mermaid)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Archivo de salida (opcional, se genera automáticamente si no se especifica)'
    )
    
    parser.add_argument(
        '--info', '-i',
        action='store_true',
        help='Solo mostrar información del workflow sin generar diagrama'
    )
    
    args = parser.parse_args()
    
    print("🚀 Visualizador de Workflow LangAgent")
    print("=" * 40)
    
    # Configurar el path
    langagent_path = setup_path()
    
    if args.info:
        # Solo mostrar información
        try:
            from langagent.core.lang_chain_agent import LangChainAgent
            agent = LangChainAgent()
            _show_workflow_info(agent)
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    else:
        # Generar diagrama
        success = create_workflow_diagram(args.format, args.output)
        if not success:
            sys.exit(1)
    
    print("\n✅ Proceso completado!")
    return True

if __name__ == "__main__":
    main() 