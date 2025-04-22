"""
Punto de entrada al ejecutar el paquete langagent como módulo.

Este script permite ejecutar el módulo como 'python -m langagent <argumentos>'
y proporciona varias opciones como ejecutar el agente o realizar evaluaciones.
"""

import sys
import argparse
import os

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
    
    # Comando para ejecutar la evaluación
    eval_parser = subparsers.add_parser("evaluate", help="Evaluar el rendimiento del agente")
    eval_parser.add_argument("--data_dir", help="Directorio con datos de documentos")
    eval_parser.add_argument("--chroma_dir", help="Directorio de bases vectoriales Chroma")
    eval_parser.add_argument("--modelo", help="Nombre del modelo LLM principal")
    eval_parser.add_argument("--modelo2", help="Nombre del segundo modelo LLM")
    eval_parser.add_argument("--salida", help="Ruta para guardar los resultados")
    eval_parser.add_argument("--verbose", action="store_true", help="Mostrar información detallada")
    eval_parser.add_argument("--casos", help="Archivo JSON con casos de prueba personalizados")
    
    # Analizar argumentos
    args = parser.parse_args()
    
    # Ejecutar el comando correspondiente
    if args.command == "run":
        from main import main as run_main
        run_main_args = [
            "--data_dir", args.data_dir,
            "--chroma_dir", args.chroma_dir,
            "--local_llm", args.local_llm,
            "--local_llm2", args.local_llm2,
            "--question", args.question
        ]
        # Filtrar argumentos None
        filtered_args = [arg for i, arg in enumerate(run_main_args) if i % 2 == 0 or arg is not None]
        # Reimplementar sys.argv
        sys.argv = ["main.py"] + filtered_args
        run_main()
        
    elif args.command == "evaluate":
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
        
        # Reimplementar sys.argv
        sys.argv = ["evaluation/run_evaluation.py"] + eval_main_args
        eval_main()
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 