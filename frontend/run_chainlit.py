"""
Script para iniciar tanto el servidor Rasa como la aplicación Chainlit.
"""

import subprocess
import sys
import os
import time
import signal
import webbrowser
from threading import Thread

def run_rasa():
    """Ejecuta el servidor Rasa."""
    rasa_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ambito_selector")
    os.chdir(rasa_dir)
    
    # Iniciar el servidor Rasa
    rasa_process = subprocess.Popen(
        ["rasa", "run", "--enable-api"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Esperar a que el servidor esté listo
    while True:
        line = rasa_process.stdout.readline()
        if "Rasa server is up and running" in line:
            print("Servidor Rasa iniciado correctamente")
            break
        if rasa_process.poll() is not None:
            print("Error al iniciar el servidor Rasa")
            sys.exit(1)
    
    return rasa_process

def run_chainlit():
    """Ejecuta la aplicación Chainlit."""
    # Volver al directorio frontend
    os.chdir(os.path.dirname(__file__))
    
    # Iniciar Chainlit
    chainlit_process = subprocess.Popen(
        ["chainlit", "run", "chainlit_app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Esperar a que Chainlit esté listo
    while True:
        line = chainlit_process.stdout.readline()
        if "Your app is running at" in line:
            print("Aplicación Chainlit iniciada correctamente")
            # Extraer la URL y abrir en el navegador
            url = line.split("http://")[1].strip()
            webbrowser.open(f"http://{url}")
            break
        if chainlit_process.poll() is not None:
            print("Error al iniciar Chainlit")
            sys.exit(1)
    
    return chainlit_process

def main():
    """Función principal que inicia ambos servicios."""
    try:
        # Iniciar Rasa
        rasa_process = run_rasa()
        
        # Dar tiempo para que Rasa se inicialice completamente
        time.sleep(5)
        
        # Iniciar Chainlit
        chainlit_process = run_chainlit()
        
        # Mantener el script en ejecución
        while True:
            if rasa_process.poll() is not None:
                print("El servidor Rasa se ha detenido")
                break
            if chainlit_process.poll() is not None:
                print("La aplicación Chainlit se ha detenido")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nDeteniendo servicios...")
    finally:
        # Detener los procesos
        for process in [rasa_process, chainlit_process]:
            if process and process.poll() is None:
                process.terminate()
                process.wait()

if __name__ == "__main__":
    main() 