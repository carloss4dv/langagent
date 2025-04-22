# Archivo: run_evaluation.py

"""
Script para ejecutar la evaluación del agente LangChain con casos predefinidos.
Este script usa el evaluador de evaluate.py para probar el agente con un conjunto
de preguntas predefinidas y genera un informe de evaluación.
"""

import os
import json
import argparse
from datetime import datetime
from evaluate import AgentEvaluator, guardar_resultados_deepeval

# Casos de prueba predefinidos (preguntas, respuestas esperadas opcionales)
CASOS_PRUEBA = [
    {
        "pregunta": "¿Cuál es la diferencia entre un cubo BIC y un cubo OCEANO?",
        "respuesta_esperada": None  # Opcional
    },
    {
        "pregunta": "¿Qué es un cubo BIC?",
        "respuesta_esperada": None
    },
    {
        "pregunta": "¿Qué cubos están disponibles en el sistema?",
        "respuesta_esperada": None
    },
    {
        "pregunta": "¿Cómo puedo obtener información de ventas por región?",
        "respuesta_esperada": None
    }
]

def main():
    parser = argparse.ArgumentParser(description="Ejecuta una evaluación completa del agente RAG")
    parser.add_argument("--data_dir", help="Directorio con datos de documentos")
    parser.add_argument("--chroma_dir", help="Directorio de bases vectoriales Chroma")
    parser.add_argument("--modelo", help="Nombre del modelo LLM principal")
    parser.add_argument("--modelo2", help="Nombre del segundo modelo LLM")
    parser.add_argument("--salida", help="Ruta para guardar los resultados")
    parser.add_argument("--verbose", action="store_true", help="Mostrar información detallada")
    parser.add_argument("--casos", help="Archivo JSON con casos de prueba personalizados")
    
    args = parser.parse_args()
    
    # Cargar casos personalizados si se proporciona un archivo
    casos_prueba = CASOS_PRUEBA
    if args.casos and os.path.exists(args.casos):
        try:
            with open(args.casos, 'r', encoding='utf-8') as f:
                casos_prueba = json.load(f)
            print(f"Casos de prueba personalizados cargados de: {args.casos}")
        except Exception as e:
            print(f"Error al cargar casos personalizados: {e}")
    
    # Crear evaluador
    evaluador = AgentEvaluator(
        data_dir=args.data_dir,
        chroma_base_dir=args.chroma_dir,
        local_llm=args.modelo,
        local_llm2=args.modelo2
    )
    
    # Extraer preguntas y respuestas esperadas
    preguntas = [caso["pregunta"] for caso in casos_prueba]
    respuestas_esperadas = [caso.get("respuesta_esperada") for caso in casos_prueba]
    
    print(f"Evaluando {len(preguntas)} casos de prueba...")
    
    # Ejecutar evaluación
    resultados = evaluador.evaluar(preguntas, respuestas_esperadas)
    
    # Guardar resultados utilizando la función mejorada
    ruta_resultados = guardar_resultados_deepeval(evaluador, resultados, args.salida)
    
    # Mostrar resultados
    print("\nResultados detallados de evaluación:")
    for i, test_case in enumerate(evaluador.test_cases):
        print(f"\nCaso {i+1}: {test_case.input}")
        print(f"Respuesta: {test_case.actual_output}")
        
        # Mostrar métricas
        print("Métricas:")
        for metric in resultados["metrics"]:
            if i < len(resultados["scores"][metric.name]):
                score = resultados["scores"][metric.name][i]
                print(f"  - {metric.name}: {score:.4f}")
        
        # Mostrar metadatos si se solicita modo verbose
        if args.verbose and hasattr(test_case, "metadata"):
            metadata = test_case.metadata
            print("\nMetadatos:")
            print(f"  - Tiempo de completado: {metadata.get('completion_time', 'N/A'):.4f} segundos")
            
            # Mostrar información de tokens si está disponible
            token_info = metadata.get("token_info", {})
            if token_info:
                print("  - Información de tokens:")
                if "input_tokens" in token_info:
                    print(f"    - Tokens de entrada: {token_info.get('input_tokens', 0)}")
                    print(f"    - Tokens de salida: {token_info.get('output_tokens', 0)}")
                print(f"    - Tokens totales: {token_info.get('total_tokens', 0)}")
                
                # Mostrar costos estimados
                if "cost_estimate" in token_info:
                    cost = token_info["cost_estimate"]
                    print("    - Costo estimado:")
                    if "input_cost" in cost:
                        print(f"      - Costo de entrada: ${cost.get('input_cost', 0):.6f}")
                        print(f"      - Costo de salida: ${cost.get('output_cost', 0):.6f}")
                    print(f"      - Costo total: ${cost.get('total_cost', 0):.6f}")
            
            # Mostrar otros metadatos relevantes
            if "model_info" in metadata:
                print(f"  - Modelo utilizado: {metadata['model_info']}")
            if "hallucination_score" in metadata and metadata["hallucination_score"] is not None:
                print(f"  - Puntuación de alucinación: {metadata['hallucination_score']}")
            if "answer_score" in metadata and metadata["answer_score"] is not None:
                print(f"  - Puntuación de respuesta: {metadata['answer_score']}")
    
    # Calcular y mostrar promedios de métricas
    print("\nPuntuaciones promedio:")
    for metric in resultados["metrics"]:
        scores = resultados["scores"][metric.name]
        if scores:
            promedio = sum(scores) / len(scores)
            print(f"  - {metric.name}: {promedio:.4f}")
    
    # Calcular y mostrar promedios de tiempo y tokens
    if evaluador.test_cases and hasattr(evaluador.test_cases[0], "metadata"):
        tiempos = [tc.metadata.get("completion_time", 0) for tc in evaluador.test_cases if hasattr(tc, "metadata")]
        if tiempos:
            promedio_tiempo = sum(tiempos) / len(tiempos)
            print(f"\nTiempo promedio de completado: {promedio_tiempo:.4f} segundos")
        
        token_totales = [tc.metadata.get("token_info", {}).get("total_tokens", 0) 
                         for tc in evaluador.test_cases if hasattr(tc, "metadata")]
        if token_totales:
            promedio_tokens = sum(token_totales) / len(token_totales)
            print(f"Tokens promedio por consulta: {promedio_tokens:.1f}")
    
    print(f"\nResultados guardados en: {ruta_resultados}")

if __name__ == "__main__":
    main() 