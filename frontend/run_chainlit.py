"""
Script para iniciar la aplicación Chainlit.
"""

import subprocess
import sys
import os
import time
import signal
import webbrowser

def run_chainlit():
    """Ejecuta la aplicación Chainlit."""
    # Asegurarse de estar en el directorio frontend
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
    """Función principal que inicia la aplicación."""
    chainlit_process = None
    try:
        # Iniciar Chainlit
        chainlit_process = run_chainlit()
        
        # Mantener el script en ejecución
        while True:
            if chainlit_process.poll() is not None:
                print("La aplicación Chainlit se ha detenido")
                break
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nDeteniendo servicio...")
    except Exception as e:
        print(f"Error al iniciar Chainlit: {str(e)}")
    finally:
        # Detener el proceso
        if chainlit_process and chainlit_process.poll() is None:
            chainlit_process.terminate()
            chainlit_process.wait()

if __name__ == "__main__":
    main() 