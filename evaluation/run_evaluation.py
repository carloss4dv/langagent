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
from evaluation.evaluate import AgentEvaluator, guardar_resultados_deepeval

# Casos de prueba basados en los cubos de datos del sistema
CASOS_PRUEBA = [
    {
        "pregunta": "¿Cómo se calcula la tasa de éxito académico?",
        "respuesta_esperada": "La tasa de éxito es la relación porcentual entre el número total de créditos superados por los estudiantes en un estudio y el número total de créditos presentados a examen. Se cuentan los créditos presentados una sola vez en el curso académico aunque se haya presentado a más de una convocatoria. Se excluyen del cálculo los créditos de asignaturas cursadas por estudiantes en programas de intercambio, los créditos matriculados en asignaturas que no son las del plan del alumno y los créditos reconocidos, adaptados o convalidados."
    },
    {
        "pregunta": "¿Qué diferencia hay entre créditos evaluados y créditos superados?",
        "respuesta_esperada": "Los créditos evaluados incluyen todos los créditos matriculados por los estudiantes que han sido calificados (presentado o no presentado) en actas, mientras que los créditos superados son específicamente los créditos de asignaturas cuyos resultados de examen han obtenido cualquiera de las siguientes calificaciones: Aprobado, Aprobado por compensación, Apto, Matrícula de Honor, Notable o Sobresaliente."
    },
    {
        "pregunta": "¿Cuántos tipos de programas de movilidad existen para estudiantes de la Universidad de Zaragoza?",
        "respuesta_esperada": "Existen varios programas de movilidad para estudiantes de la Universidad de Zaragoza, entre ellos: Erasmus, SICUE-SÉNECA, Movilidad en másteres (AGE), Movilidad UE-Suiza, Movilidad Transfronteriza, Movilidad Iberoamérica, UZ/Norteamérica, Oceanía y Asia, entre otros. Los programas se pueden clasificar como internacionales o nacionales (como SICUE)."
    },
    {
        "pregunta": "¿Cómo puedo saber si una universidad de destino pertenece a la alianza UNITA?",
        "respuesta_esperada": "En los cubos de movilidad existe un atributo específico llamado 'Universidad de Destino UNITA (S/N)' que permite clasificar los datos en función de si la universidad de destino pertenece a la alianza de universidades europeas UNITA (S) o no (N). El primer curso académico en que están registradas universidades UNITA es 2020/21."
    },
    {
        "pregunta": "¿Qué métricas permiten evaluar el rendimiento de los estudiantes?",
        "respuesta_esperada": "Las principales métricas para evaluar el rendimiento de los estudiantes son: Tasa de Éxito (relación entre créditos superados y créditos presentados), Tasa de Rendimiento (relación entre créditos superados y créditos matriculados) y Tasa de Evaluación (relación entre créditos presentados y créditos matriculados). También se cuenta con medidas como la Media de Convocatorias Consumidas y la Nota Media de Admisión."
    },
    {
        "pregunta": "¿Qué información se recoge sobre los estudiantes extranjeros que vienen a la Universidad de Zaragoza (Estudiantes IN)?",
        "respuesta_esperada": "Sobre los estudiantes IN se recoge: el número total de estudiantes, la duración media de la estancia en meses, su tasa de rendimiento, datos personales (nacionalidad, rango de edad, sexo), su centro de acogida, el centro de las asignaturas que cursan, información sobre su expediente (créditos matriculados y superados), detalles de la movilidad (país y universidad de origen, programa de movilidad, si la universidad pertenece a UNITA) y datos sobre la titulación cursada."
    },
    {
        "pregunta": "¿Cómo se contabilizan las renuncias a movilidad en el sistema?",
        "respuesta_esperada": "Las renuncias a movilidad se contabilizan como el número total de solicitudes aceptadas que no se han hecho efectivas, ya sea por renuncia expresa o tácita. En la dimensión 'Movilidad' existe un atributo 'Renuncia (S/N)' que permite distinguir entre las solicitudes de movilidad aceptadas que no se han hecho efectivas (S) de las que sí se han hecho efectivas (N)."
    },
    {
        "pregunta": "¿Qué tipos de movilidad existen para los investigadores?",
        "respuesta_esperada": "Para los investigadores existen dos tipos principales de movilidad según su tipología: estancias y vinculaciones. La información se clasifica según la duración de la movilidad en semanas, las fechas de inicio y finalización, si han realizado prórroga (S/N), el tipo de entidad de origen (empresa, universidad o unidad de investigación) y otros datos como el grupo de investigación, macroárea, nacionalidad, instituto de investigación, etc."
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