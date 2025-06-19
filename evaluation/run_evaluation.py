# Archivo: run_evaluation.py

"""
Script para ejecutar la evaluación del agente LangChain con casos predefinidos.
Este script usa el evaluador de evaluate.py para probar el agente con un conjunto
de preguntas predefinidas y genera un informe de evaluación.
También puede ejecutarse en modo batch para solo generar respuestas.
"""

import os
import json
import argparse
from datetime import datetime
import sys

# Asegurarnos que podemos importar desde el directorio raíz
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Importar desde el módulo local
from langagent.evaluation.evaluate import AgentEvaluator
from langagent.core.lang_chain_agent import LangChainAgent
from langagent.config.logging_config import get_logger

logger = get_logger(__name__)

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

def run_batch_evaluation(preguntas_file, output_dir, agent_config):
    """
    Ejecuta una evaluación en batch de preguntas usando el LangChainAgent.
    """
    logger.info(f"Iniciando evaluación en batch desde el archivo: {preguntas_file}")

    # Cargar preguntas
    try:
        with open(preguntas_file, 'r', encoding='utf-8') as f:
            preguntas_data = json.load(f)
        # Soporta ambos formatos: lista de strings o lista de dicts con "pregunta"
        if isinstance(preguntas_data[0], dict):
            preguntas = [item["pregunta"] for item in preguntas_data]
        else:
            preguntas = preguntas_data
        logger.info(f"Se cargaron {len(preguntas)} preguntas.")
    except Exception as e:
        logger.error(f"Error al cargar el archivo de preguntas: {e}")
        return

    # Inicializar agente
    try:
        agent = LangChainAgent(
            data_dir=agent_config.get("data_dir"),
            vectorstore_dir=agent_config.get("vectorstore_dir"),
            vector_db_type=agent_config.get("vector_db_type"),
            local_llm=agent_config.get("modelo"),
            local_llm2=agent_config.get("modelo2"),
            local_llm3=agent_config.get("modelo3")
        )
    except Exception as e:
        logger.error(f"Error al inicializar LangChainAgent: {e}")
        return

    results = []
    for i, pregunta in enumerate(preguntas):
        logger.info(f"Procesando pregunta {i+1}/{len(preguntas)}: {pregunta}")
        try:
            # Ejecutar la consulta a través del agente
            result = agent.run(pregunta)

            # Capturar metadatos
            serializable_result = {}
            for key, value in result.items():
                try:
                    json.dumps(value)
                    serializable_result[key] = value
                except (TypeError, OverflowError):
                    serializable_result[key] = str(value)

            results.append({
                "pregunta": pregunta,
                "respuesta_generada": serializable_result.get('generation', ''),
                "metadata_completa": serializable_result
            })

        except Exception as e:
            logger.error(f"Error procesando la pregunta '{pregunta}': {e}")
            results.append({
                "pregunta": pregunta,
                "error": str(e)
            })

    # Guardar resultados
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"batch_results_{timestamp}.json")

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        logger.info(f"Resultados de la evaluación guardados en: {output_file}")
    except Exception as e:
        logger.error(f"Error al guardar los resultados: {e}")


def main():
    parser = argparse.ArgumentParser(description="Ejecuta una evaluación completa del agente RAG")
    parser.add_argument("--data_dir", help="Directorio con datos de documentos")
    parser.add_argument("--chroma_dir", help="Directorio de bases vectoriales Chroma")
    parser.add_argument("--modelo", help="Nombre del modelo LLM principal")
    parser.add_argument("--modelo2", help="Nombre del segundo modelo LLM")
    parser.add_argument("--modelo3", help="Nombre del tercer modelo LLM (para batch mode)")
    parser.add_argument("--salida", help="Ruta para guardar los resultados (modo deepeval)")
    parser.add_argument("--verbose", action="store_true", help="Mostrar información detallada")
    parser.add_argument("--casos", help="Archivo JSON con casos de prueba")
    parser.add_argument("--vector_db_type", default="milvus", choices=["chroma", "milvus"],
                       help="Tipo de vectorstore a utilizar (default: milvus)")
    parser.add_argument("--batch", action="store_true", help="Ejecutar en modo batch para solo generar respuestas.")
    parser.add_argument("--output_dir", default="batch_results", help="Directorio para guardar los resultados en modo batch.")
    
    args = parser.parse_args()

    if args.batch:
        if not args.casos:
            logger.error("El modo batch requiere un archivo de casos de prueba con --casos.")
            sys.exit(1)
        
        agent_config = {
            "data_dir": args.data_dir,
            "vectorstore_dir": args.chroma_dir,
            "vector_db_type": args.vector_db_type,
            "modelo": args.modelo,
            "modelo2": args.modelo2,
            "modelo3": args.modelo3
        }
        run_batch_evaluation(args.casos, args.output_dir, agent_config)
    else:
        # Lógica original de deepeval
        evaluador = AgentEvaluator(
            data_dir=args.data_dir,
            vectorstore_dir=args.chroma_dir,
            vector_db_type=args.vector_db_type,
            local_llm=args.modelo,
            local_llm2=args.modelo2
        )
        
        # Cargar casos de prueba
        if args.casos and os.path.exists(args.casos):
            with open(args.casos, 'r', encoding='utf-8') as f:
                casos = json.load(f)
            preguntas = [caso["pregunta"] for caso in casos]
            respuestas_esperadas = [caso.get("respuesta_esperada") for caso in casos]
        else:
            preguntas = [caso["pregunta"] for caso in CASOS_PRUEBA]
            respuestas_esperadas = [caso["respuesta_esperada"] for caso in CASOS_PRUEBA]
        
        # Ejecutar evaluación
        resultados = evaluador.evaluar(preguntas, respuestas_esperadas)
        
        # Guardar resultados si se especifica
        if args.salida:
            if not os.path.exists(os.path.dirname(args.salida)):
                os.makedirs(os.path.dirname(args.salida))
            with open(args.salida, 'w', encoding='utf-8') as f:
                json.dump(resultados, f, ensure_ascii=False, indent=4)
            print(f"Resultados guardados en {args.salida}")

if __name__ == "__main__":
    main()