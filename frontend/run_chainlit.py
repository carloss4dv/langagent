"""
Script para ejecutar la aplicación Chainlit.

Este script inicia la aplicación Chainlit para interactuar con el agente de respuesta a preguntas.
"""

import os
import sys
import argparse

# Añadir el directorio raíz al path para importar módulos
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

def run_chainlit(port=8000):
    """
    Ejecuta la aplicación Chainlit.
    
    Args:
        port (int): Puerto para ejecutar la aplicación
    """
    import subprocess
    
    # Ruta al archivo de la aplicación
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chainlit_app.py")
    
    print(f"Iniciando Chainlit en el puerto {port}...")
    print(f"Ruta de la aplicación: {app_path}")
    
    # Construir el comando para ejecutar chainlit
    cmd = [
        sys.executable, "-m", "chainlit", "run", 
        app_path,
        "--port", str(port),
        "--host", "0.0.0.0"
    ]
    
    # Ejecutar el comando
    subprocess.run(cmd)

if __name__ == "__main__":
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Ejecuta la aplicación Chainlit")
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000, 
        help="Puerto para ejecutar la aplicación (predeterminado: 8000)"
    )
    
    # Parsear argumentos
    args = parser.parse_args()
    
    # Ejecutar la aplicación
    run_chainlit(port=args.port) 