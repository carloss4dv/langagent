import argparse
import json
import os
from datetime import datetime
import sys

# Asegurarnos que podemos importar desde el directorio raíz
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from langagent.core.lang_chain_agent import LangChainAgent
from langagent.config.logging_config import get_logger

logger = get_logger(__name__)

def run_batch_evaluation(preguntas_file, output_dir, agent_config):
    """
    Ejecuta una evaluación en batch de preguntas usando el LangChainAgent.

    Args:
        preguntas_file (str): Ruta al archivo JSON con las preguntas.
        output_dir (str): Directorio para guardar los resultados.
        agent_config (dict): Configuración para el LangChainAgent.
    """
    logger.info(f"Iniciando evaluación en batch desde el archivo: {preguntas_file}")

    # Cargar preguntas
    try:
        with open(preguntas_file, 'r', encoding='utf-8') as f:
            preguntas_data = json.load(f)
        preguntas = [item["pregunta"] for item in preguntas_data]
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
            # El método 'run' ya devuelve un diccionario con toda la información.
            # Nos aseguramos de que sea serializable para JSON.
            serializable_result = {}
            for key, value in result.items():
                try:
                    json.dumps(value)
                    serializable_result[key] = value
                except (TypeError, OverflowError):
                    serializable_result[key] = str(value) # Convertir a string si no es serializable

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
    parser = argparse.ArgumentParser(description="Evaluador en batch para LangChainAgent.")
    parser.add_argument("--preguntas_file", required=True, help="Archivo JSON con las preguntas a evaluar.")
    parser.add_argument("--output_dir", default="batch_results", help="Directorio para guardar los resultados.")
    parser.add_argument("--data_dir", help="Directorio con documentos")
    parser.add_argument("--vectorstore_dir", help="Directorio de bases vectoriales")
    parser.add_argument("--vector_db_type", default="milvus", choices=["chroma", "milvus"], help="Tipo de vectorstore a utilizar.")
    parser.add_argument("--modelo", help="Nombre del modelo LLM principal")
    parser.add_argument("--modelo2", help="Nombre del segundo modelo LLM")
    parser.add_argument("--modelo3", help="Nombre del tercer modelo LLM")

    args = parser.parse_args()

    agent_config = {
        "data_dir": args.data_dir,
        "vectorstore_dir": args.vectorstore_dir,
        "vector_db_type": args.vector_db_type,
        "modelo": args.modelo,
        "modelo2": args.modelo2,
        "modelo3": args.modelo3
    }

    run_batch_evaluation(args.preguntas_file, args.output_dir, agent_config)

if __name__ == "__main__":
    main()
