"""
Script para iniciar la aplicación Chainlit.
"""

import subprocess
import sys
import os
import time
import signal
import webbrowser
import threading

def print_output(pipe, prefix):
    """Imprime la salida de un pipe con un prefijo."""
    for line in iter(pipe.readline, ''):
        if line:
            print(f"{prefix}: {line.strip()}")

def run_chainlit():
    """Ejecuta la aplicación Chainlit."""
    # Obtener el directorio raíz del proyecto
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    
    # Cambiar al directorio raíz
    os.chdir(root_dir)
    
    try:
        # Iniciar Chainlit con la ruta relativa al directorio raíz
        chainlit_process = subprocess.Popen(
            ["chainlit", "run", os.path.join("frontend", "chainlit_app.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Crear hilos para mostrar la salida en tiempo real
        stdout_thread = threading.Thread(target=print_output, args=(chainlit_process.stdout, "OUT"))
        stderr_thread = threading.Thread(target=print_output, args=(chainlit_process.stderr, "ERR"))
        
        # Configurar los hilos como daemon para que se cierren cuando el programa principal termine
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        # Iniciar los hilos
        stdout_thread.start()
        stderr_thread.start()
        
        # Esperar a que Chainlit esté listo
        while True:
            if chainlit_process.poll() is not None:
                print("Error: Chainlit se ha detenido inesperadamente")
                sys.exit(1)
            
            # Verificar si hay algún error en stderr
            error_output = chainlit_process.stderr.readline()
            if error_output and "error" in error_output.lower():
                print(f"Error en Chainlit: {error_output.strip()}")
                sys.exit(1)
            
            # Verificar si la aplicación está lista
            stdout_line = chainlit_process.stdout.readline()
            if "Your app is running at" in stdout_line:
                print("Aplicación Chainlit iniciada correctamente")
                # Extraer la URL y abrir en el navegador
                url = stdout_line.split("http://")[1].strip()
                webbrowser.open(f"http://{url}")
                break
            
            time.sleep(0.1)  # Pequeña pausa para no saturar la CPU
        
        return chainlit_process
    except Exception as e:
        print(f"Error al iniciar Chainlit: {str(e)}")
        sys.exit(1)

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