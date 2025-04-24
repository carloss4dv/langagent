#!/usr/bin/env python
"""
Script para ejecutar la aplicación Streamlit.
"""

import os
import subprocess
import sys
import argparse

def run_streamlit(api_url="http://localhost:8000", port=8501):
    """
    Ejecuta la aplicación Streamlit conectada a la API.
    
    Args:
        api_url (str): URL de la API del agente.
        port (int): Puerto en el que se ejecutará Streamlit.
    """
    # Obtener la ruta del directorio actual
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Establecer la variable de entorno para la API
    os.environ["API_URL"] = api_url
    
    # Construir el comando para ejecutar Streamlit
    app_path = os.path.join(current_dir, "app.py")
    cmd = [
        "streamlit", "run", app_path,
        "--server.port", str(port),
        "--browser.serverAddress", "localhost",
        "--browser.gatherUsageStats", "false"
    ]
    
    try:
        # Ejecutar Streamlit
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nServidor Streamlit detenido.")
    except Exception as e:
        print(f"Error al ejecutar Streamlit: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Ejecutar la aplicación Streamlit para el agente")
    parser.add_argument("--api-url", default="http://localhost:8000", 
                      help="URL de la API del agente (por defecto: http://localhost:8000)")
    parser.add_argument("--port", type=int, default=8501,
                      help="Puerto para ejecutar Streamlit (por defecto: 8501)")
    
    args = parser.parse_args()
    
    # Ejecutar Streamlit
    run_streamlit(api_url=args.api_url, port=args.port) 