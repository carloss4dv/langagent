"""
Punto de entrada al ejecutar el paquete langagent como módulo.

Este script permite ejecutar el módulo como 'python -m langagent <argumentos>'
y proporciona varias opciones como ejecutar el agente o realizar evaluaciones.
"""

import sys
import argparse
import os

# Asegurar que el módulo esté en el path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

def main():
    """Función principal para gestionar los comandos del paquete."""
    parser = argparse.ArgumentParser(
        description="Herramienta de agente de respuesta a preguntas basado en RAG",
        prog="langagent"
    )
    
    # Crear subparsers para diferentes comandos
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # Comando para ejecutar el agente
    run_parser = subparsers.add_parser("run", help="Ejecutar el agente con una consulta")
    run_parser.add_argument("--data_dir", help="Directorio con documentos markdown")
    run_parser.add_argument("--chroma_dir", help="Directorio para la base de datos vectorial")
    run_parser.add_argument("--local_llm", help="Modelo LLM principal")
    run_parser.add_argument("--local_llm2", help="Modelo LLM secundario (opcional)")
    run_parser.add_argument("--question", help="Pregunta a responder")
    run_parser.add_argument("--vector_db_type", default="milvus", choices=["chroma", "milvus"],
                           help="Tipo de vectorstore a utilizar (default: milvus)")
    
    # Comando para ejecutar la evaluación
    eval_parser = subparsers.add_parser("evaluate", help="Evaluar el rendimiento del agente")
    eval_parser.add_argument("--data_dir", help="Directorio con datos de documentos")
    eval_parser.add_argument("--chroma_dir", help="Directorio de bases vectoriales Chroma")
    eval_parser.add_argument("--modelo", help="Nombre del modelo LLM principal")
    eval_parser.add_argument("--modelo2", help="Nombre del segundo modelo LLM")
    eval_parser.add_argument("--salida", help="Ruta para guardar los resultados")
    eval_parser.add_argument("--verbose", action="store_true", help="Mostrar información detallada")
    eval_parser.add_argument("--casos", help="Archivo JSON con casos de prueba personalizados")
    eval_parser.add_argument("--vector_db_type", default="milvus", choices=["chroma", "milvus"],
                           help="Tipo de vectorstore a utilizar (default: milvus)")
    
    # Analizar argumentos
    args = parser.parse_args()
    
    # Ejecutar el comando correspondiente
    if args.command == "run":
        try:
            # Directamente llamamos a la función main en main.py
            from langagent.main import main as run_main
            run_main_args = []
            if args.data_dir:
                run_main_args.extend(["--data_dir", args.data_dir])
            if args.chroma_dir:
                run_main_args.extend(["--chroma_dir", args.chroma_dir])
            if args.local_llm:
                run_main_args.extend(["--local_llm", args.local_llm])
            if args.local_llm2:
                run_main_args.extend(["--local_llm2", args.local_llm2])
            if args.question:
                run_main_args.extend(["--question", args.question])
            
            # Agregar el tipo de vectorstore
            run_main_args.extend(["--vector_db_type", args.vector_db_type])
            
            # Reimplementar sys.argv
            sys.argv = ["main.py"] + run_main_args
            run_main()
        except ImportError:
            try:
                # Intentar importar desde el directorio actual
                from main import main as run_main
                run_main_args = []
                if args.data_dir:
                    run_main_args.extend(["--data_dir", args.data_dir])
                if args.chroma_dir:
                    run_main_args.extend(["--chroma_dir", args.chroma_dir])
                if args.local_llm:
                    run_main_args.extend(["--local_llm", args.local_llm])
                if args.local_llm2:
                    run_main_args.extend(["--local_llm2", args.local_llm2])
                if args.question:
                    run_main_args.extend(["--question", args.question])
                
                # Agregar el tipo de vectorstore
                run_main_args.extend(["--vector_db_type", args.vector_db_type])
                
                # Reimplementar sys.argv
                sys.argv = ["main.py"] + run_main_args
                run_main()
            except ImportError:
                logger.error("Error: No se pudo importar el módulo main.py.")
                logger.error("Asegúrate de que estás ejecutando el script desde el directorio correcto.")
                sys.exit(1)
        
    elif args.command == "evaluate":
        # Asegurarnos que el directorio actual está en el path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        try:
            # Importar directamente el script de evaluación
            from langagent.evaluation.run_evaluation import main as eval_main
            
            eval_main_args = []
            if args.data_dir:
                eval_main_args.extend(["--data_dir", args.data_dir])
            if args.chroma_dir:
                eval_main_args.extend(["--chroma_dir", args.chroma_dir])
            if args.modelo:
                eval_main_args.extend(["--modelo", args.modelo])
            if args.modelo2:
                eval_main_args.extend(["--modelo2", args.modelo2])
            if args.salida:
                eval_main_args.extend(["--salida", args.salida])
            if args.verbose:
                eval_main_args.append("--verbose")
            if args.casos:
                eval_main_args.extend(["--casos", args.casos])
            
            # Agregar el tipo de vectorstore
            eval_main_args.extend(["--vector_db_type", args.vector_db_type])
            
            # Reimplementar sys.argv
            sys.argv = ["evaluation/run_evaluation.py"] + eval_main_args
            eval_main()
        except ImportError:
            try:
                # Intentar importar desde el directorio actual
                from evaluation.run_evaluation import main as eval_main
                
                eval_main_args = []
                if args.data_dir:
                    eval_main_args.extend(["--data_dir", args.data_dir])
                if args.chroma_dir:
                    eval_main_args.extend(["--chroma_dir", args.chroma_dir])
                if args.modelo:
                    eval_main_args.extend(["--modelo", args.modelo])
                if args.modelo2:
                    eval_main_args.extend(["--modelo2", args.modelo2])
                if args.salida:
                    eval_main_args.extend(["--salida", args.salida])
                if args.verbose:
                    eval_main_args.append("--verbose")
                if args.casos:
                    eval_main_args.extend(["--casos", args.casos])
                
                # Agregar el tipo de vectorstore
                eval_main_args.extend(["--vector_db_type", args.vector_db_type])
                
                # Reimplementar sys.argv
                sys.argv = ["evaluation/run_evaluation.py"] + eval_main_args
                eval_main()
            except ImportError:
                logger.error("Error: No se pudo importar el módulo de evaluación.")
                logger.error("Asegúrate de que estás ejecutando el script desde el directorio correcto.")
                sys.exit(1)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 