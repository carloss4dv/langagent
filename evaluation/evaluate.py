# Archivo: evaluate.py

"""
Script de evaluación para LangChainAgent utilizando deepeval.
Este script permite evaluar las respuestas del agente RAG con métricas de deepeval.
"""

import os
import argparse
import json
import time
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
    ContextualRecallMetric,
    ContextualPrecisionMetric
)
from deepeval.test_case import LLMTestCase
import deepeval

# Asegurarnos que podemos importar desde el directorio raíz
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Importar LangChainAgent desde el módulo core
from langagent.core.lang_chain_agent import LangChainAgent


class AgentEvaluator:
    """
    Evaluador que utiliza deepeval para evaluar las respuestas del agente LangChain.
    """
    
    def __init__(self, data_dir=None, chroma_base_dir=None, local_llm=None, local_llm2=None):
        """
        Inicializa el evaluador con el agente LangChain.
        
        Args:
            data_dir (str, optional): Directorio con los documentos markdown.
            chroma_base_dir (str, optional): Directorio base para las bases de datos vectoriales.
            local_llm (str, optional): Nombre del modelo LLM principal.
            local_llm2 (str, optional): Nombre del segundo modelo LLM.
        """
        self.agent = LangChainAgent(
            data_dir=data_dir,
            chroma_base_dir=chroma_base_dir,
            local_llm=local_llm,
            local_llm2=local_llm2
        )
        
        # Inicializar métricas de evaluación
        self.metrics = {
            "answer_relevancy": AnswerRelevancyMetric(threshold=0.7),
            "faithfulness": FaithfulnessMetric(threshold=0.7),
            "contextual_relevancy": ContextualRelevancyMetric(threshold=0.7),
            "contextual_recall": ContextualRecallMetric(threshold=0.7),
            "contextual_precision": ContextualPrecisionMetric(threshold=0.7)
        }
        
        self.test_cases = []
        self.raw_outputs = []  # Almacenar las salidas completas del agente
    
    def calcular_token_cost(self, response_metadata):
        """
        Calcula el costo estimado de los tokens usados en la generación.
        
        Args:
            response_metadata (Dict): Metadatos de respuesta del modelo.
            
        Returns:
            Dict: Información de costo y tokens.
        """
        # Extraer información de tokens si está disponible
        token_info = {}
        
        # Si response_metadata es un string que contiene 'response_metadata'
        if isinstance(response_metadata, str) and 'response_metadata' in response_metadata:
            # Intentar extraer el JSON de los metadatos
            try:
                metadata_start = response_metadata.find("response_metadata={") + 19
                metadata_end = response_metadata.find("} id=")
                if metadata_start > 19 and metadata_end > 0:
                    # Extraer el modelo del string
                    if "'model':" in response_metadata:
                        model_start = response_metadata.find("'model': '") + 10
                        model_end = response_metadata.find("'", model_start)
                        if model_start > 10 and model_end > 0:
                            token_info["model"] = response_metadata[model_start:model_end]
                
                # Buscar usage_metadata
                usage_start = response_metadata.find("usage_metadata={") + 16
                usage_end = response_metadata.rfind("}")
                if usage_start > 16 and usage_end > 0:
                    # Extraer tokens de entrada, salida y total
                    if "'input_tokens':" in response_metadata:
                        input_tokens_start = response_metadata.find("'input_tokens': ") + 15
                        input_tokens_end = response_metadata.find(",", input_tokens_start)
                        if input_tokens_start > 15 and input_tokens_end > 0:
                            token_info["input_tokens"] = int(response_metadata[input_tokens_start:input_tokens_end])
                    
                    if "'output_tokens':" in response_metadata:
                        output_tokens_start = response_metadata.find("'output_tokens': ") + 16
                        output_tokens_end = response_metadata.find(",", output_tokens_start)
                        if output_tokens_start > 16 and output_tokens_end > 0:
                            token_info["output_tokens"] = int(response_metadata[output_tokens_start:output_tokens_end])
                    
                    if "'total_tokens':" in response_metadata:
                        total_tokens_start = response_metadata.find("'total_tokens': ") + 15
                        total_tokens_end = response_metadata.find("}", total_tokens_start)
                        if total_tokens_start > 15 and total_tokens_end > 0:
                            token_info["total_tokens"] = int(response_metadata[total_tokens_start:total_tokens_end])
            except Exception as e:
                print(f"Error al procesar los metadatos de respuesta: {e}")
        elif isinstance(response_metadata, dict):
            # Para el formato original
            if "usage_metadata" in response_metadata:
                usage = response_metadata["usage_metadata"]
                token_info["input_tokens"] = usage.get("input_tokens", 0)
                token_info["output_tokens"] = usage.get("output_tokens", 0)
                token_info["total_tokens"] = usage.get("total_tokens", 0)
            elif "total_tokens" in response_metadata:
                # Para modelos antiguos
                token_info["total_tokens"] = response_metadata.get("total_tokens", 0)
        
        # Calcular costos aproximados (precios típicos por 1000 tokens)
        token_info["cost_estimate"] = {}
        
        # Si tenemos información detallada de tokens
        if "input_tokens" in token_info and "output_tokens" in token_info:
            # Precios aproximados para modelos tipo GPT-3.5
            precio_entrada = 0.0005  # $ por 1000 tokens de entrada
            precio_salida = 0.0015   # $ por 1000 tokens de salida
            
            token_info["cost_estimate"]["input_cost"] = (token_info["input_tokens"] / 1000) * precio_entrada
            token_info["cost_estimate"]["output_cost"] = (token_info["output_tokens"] / 1000) * precio_salida
            token_info["cost_estimate"]["total_cost"] = token_info["cost_estimate"]["input_cost"] + token_info["cost_estimate"]["output_cost"]
        elif "total_tokens" in token_info:
            # Estimación básica si solo tenemos tokens totales
            precio_promedio = 0.001  # $ por 1000 tokens
            token_info["cost_estimate"]["total_cost"] = (token_info["total_tokens"] / 1000) * precio_promedio
        
        return token_info
    
    def extraer_texto_respuesta(self, respuesta):
        """
        Extrae el texto de respuesta de diferentes formatos posibles.
        
        Args:
            respuesta: Respuesta del modelo en diversos formatos posibles.
            
        Returns:
            str: Texto de la respuesta extraído.
        """
        # Si es un string directamente
        if isinstance(respuesta, str):
            # Nuevo formato de generación con content='...'
            if "content='" in respuesta:
                try:
                    # Buscar el contenido JSON en el formato content='{ "answer": "..." }'
                    content_start = respuesta.find("content='") + 9
                    content_end = respuesta.find("' additional_kwargs")
                    if content_start > 9 and content_end > 0:
                        content_str = respuesta[content_start:content_end]
                        # Extraer el campo "answer" del JSON
                        if '"answer":' in content_str:
                            json_start = content_str.find('{')
                            json_end = content_str.rfind('}') + 1
                            if json_start >= 0 and json_end > json_start:
                                # Manejo para escapado doble de comillas
                                content_str = content_str.replace('\\"', '"')
                                json_str = content_str[json_start:json_end]
                                try:
                                    content_json = json.loads(json_str)
                                    return content_json.get("answer", "No se pudo extraer la respuesta")
                                except json.JSONDecodeError:
                                    # Si falla, usar un enfoque más simple para extraer la respuesta
                                    answer_start = json_str.find('"answer": "') + 11
                                    answer_end = json_str.rfind('"')
                                    if answer_start > 11 and answer_end > answer_start:
                                        return json_str[answer_start:answer_end]
                except Exception as e:
                    print(f"Error al procesar la generación: {e}")
                    return respuesta
            return respuesta
            
        # Si es un diccionario con campo content o answer
        if isinstance(respuesta, dict):
            if "content" in respuesta:
                content = respuesta["content"]
                # A veces el content es otro diccionario con el campo answer
                if isinstance(content, dict) and "answer" in content:
                    return content["answer"]
                return content
            elif "answer" in respuesta:
                return respuesta["answer"]
            elif "text" in respuesta:
                return respuesta["text"]
        
        # Si no pudimos extraer, convertir a string
        return str(respuesta)

    def crear_caso_prueba(self, pregunta: str, respuesta_esperada: str = None):
        """
        Ejecuta el agente con una pregunta y crea un caso de prueba para evaluación.
        
        Args:
            pregunta (str): Pregunta a evaluar.
            respuesta_esperada (str, optional): Respuesta esperada para la pregunta.
        
        Returns:
            LLMTestCase: Caso de prueba para evaluación con deepeval.
        """
        # Registrar el tiempo de inicio
        tiempo_inicio = time.time()
        
        # Ejecutar el agente para obtener la respuesta
        resultado = self.agent.run(pregunta)
        print(resultado)
        
        # Calcular tiempo de completado
        tiempo_completado = time.time() - tiempo_inicio
        
        # Guardar la respuesta completa para análisis
        self.raw_outputs.append({
            "pregunta": pregunta,
            "resultado_completo": resultado,
            "tiempo_completado": tiempo_completado
        })
        
        # Extraer los componentes necesarios para el caso de prueba
        generation = None
        
        # Intentar extraer el texto de la respuesta de diferentes formatos posibles
        if "generation" in resultado:
            generation = self.extraer_texto_respuesta(resultado["generation"])
        
        # Si no encontramos la generación, buscar en otros campos comunes
        if not generation and "response" in resultado:
            generation = self.extraer_texto_respuesta(resultado["response"])
        
        # Extraer otros campos importantes
        documents = resultado.get("documents", [])
        relevant_cubos = resultado.get("relevant_cubos", [])
        is_consulta = resultado.get("is_consulta", False)
        consulta_documents = resultado.get("consulta_documents", [])
        
        # Extraer puntuaciones si existen
        hallucination_score = None
        if "hallucination_score" in resultado and isinstance(resultado["hallucination_score"], dict):
            hallucination_score = resultado["hallucination_score"].get("score")
        
        answer_score = None
        if "answer_score" in resultado and isinstance(resultado["answer_score"], dict):
            answer_score = resultado["answer_score"].get("score")
        
        ambito = resultado.get("ambito")
        retrieval_details = resultado.get("retrieval_details", {})
        
        # Extraer metadatos de respuesta si existen
        response_metadata = resultado.get("generation", "")
        
        # Calcular información de tokens y costos
        token_info = self.calcular_token_cost(response_metadata)
        
        # Si es una consulta, agregar los documentos de consulta al contexto
        if is_consulta and consulta_documents:
            context_docs = consulta_documents
        else:
            # Usar los documentos recuperados normalmente
            context_docs = documents
        
        # Convertir los documentos al formato esperado por deepeval
        formatted_context = []
        for doc in context_docs:
            if isinstance(doc, Document):
                # Si es un objeto Document de LangChain
                formatted_context.append(doc.page_content)
            elif isinstance(doc, dict) and "page_content" in doc:
                # Si es un diccionario con page_content
                formatted_context.append(doc["page_content"])
            elif isinstance(doc, dict) and "text" in doc:
                # Si es un diccionario con text
                formatted_context.append(doc["text"])
            elif isinstance(doc, str):
                # Si es un string directamente
                formatted_context.append(doc)
            else:
                # En cualquier otro caso, convertir a string
                formatted_context.append(str(doc))
        
        # Crear y devolver el caso de prueba con los parámetros permitidos
        test_case = LLMTestCase(
            input=pregunta,
            actual_output=generation or "No se pudo extraer una respuesta",
            expected_output=respuesta_esperada,
            context=formatted_context,
            token_cost=token_info.get("total_tokens", 0),
            completion_time=tiempo_completado
        )
        
        # Guardar los metadatos adicionales como atributos del objeto para uso posterior
        test_case.hallucination_score = hallucination_score
        test_case.answer_score = answer_score
        test_case.relevant_cubos = relevant_cubos
        test_case.ambito = ambito
        test_case.is_consulta = is_consulta
        test_case.model_info = token_info.get("model", "unknown")
        test_case.token_info = token_info
        test_case.retrieval_details = retrieval_details
        
        self.test_cases.append(test_case)
        return test_case
    
    def evaluar(self, preguntas: List[str], respuestas_esperadas: List[str] = None):
        """
        Evalúa una lista de preguntas con las métricas configuradas.
        
        Args:
            preguntas (List[str]): Lista de preguntas a evaluar.
            respuestas_esperadas (List[str], optional): Lista de respuestas esperadas. 
                Si no se proporciona, se usa None para cada pregunta.
                
        Returns:
            Dict: Resultados de la evaluación, incluyendo métricas y puntuaciones.
        """
        # Normalizar respuestas esperadas
        if respuestas_esperadas is None:
            respuestas_esperadas = [None] * len(preguntas)
        elif len(respuestas_esperadas) < len(preguntas):
            # Completar con None si hay menos respuestas que preguntas
            respuestas_esperadas.extend([None] * (len(preguntas) - len(respuestas_esperadas)))
        
        # Crear casos de prueba para cada pregunta
        for pregunta, respuesta_esperada in zip(preguntas, respuestas_esperadas):
            self.evaluar_pregunta(pregunta, respuesta_esperada)
        
        # Generar resultados
        return {
            "metrics": list(self.metrics.values()),
            "scores": {metric.name: [] for metric in self.metrics.values()},
            "test_cases": self.test_cases
        }
    
    def evaluar_pregunta(self, pregunta: str, respuesta_esperada: str = None):
        """
        Evalúa una sola pregunta con todas las métricas configuradas.
        
        Args:
            pregunta (str): Pregunta a evaluar.
            respuesta_esperada (str, optional): Respuesta esperada para la pregunta.
            
        Returns:
            Dict: Resultados de la evaluación para esta pregunta.
        """
        # Crear caso de prueba
        test_case = self.crear_caso_prueba(pregunta, respuesta_esperada)
        
        # Evaluar con cada métrica
        for metric_name, metric in self.metrics.items():
            try:
                # Ejecutar evaluación
                result = evaluate(test_case, metric)
                
                # Añadir el resultado al test_case para referencia futura
                if not hasattr(test_case, "results"):
                    test_case.results = {}
                test_case.results[metric_name] = result
            except Exception as e:
                print(f"Error evaluando métrica {metric_name}: {e}")

def guardar_resultados_deepeval(evaluador, resultados, ruta_salida=None):
    """
    Guarda los resultados de la evaluación en un archivo.
    
    Args:
        evaluador (AgentEvaluator): El evaluador utilizado.
        resultados (Dict): Resultados de la evaluación.
        ruta_salida (str, optional): Ruta donde guardar los resultados.
        
    Returns:
        str: Ruta donde se guardaron los resultados.
    """
    # Generar nombre de archivo con marca de tiempo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if ruta_salida:
        os.makedirs(ruta_salida, exist_ok=True)
        archivo_resultados = os.path.join(ruta_salida, f"eval_results_{timestamp}.json")
    else:
        # Crear directorio output_eval si no existe
        os.makedirs("output_eval", exist_ok=True)
        archivo_resultados = os.path.join("output_eval", f"eval_results_{timestamp}.json")
    
    # Preparar resultados para serialización
    resultados_json = {
        "timestamp": timestamp,
        "nombre_evaluacion": f"Evaluación {timestamp}",
        "metricas": [metric.name for metric in resultados["metrics"]],
        "num_preguntas": len(evaluador.test_cases),
        "puntuaciones": {},
        "casos": []
    }
    
    # Calcular puntuaciones agregadas
    for metric in resultados["metrics"]:
        metric_name = metric.name
        scores = [score for score in evaluador.test_cases if hasattr(score, "results") and metric_name in score.results]
        if scores:
            resultados_json["puntuaciones"][metric_name] = {
                "promedio": sum(score.results[metric_name].score for score in scores if score.results[metric_name].score is not None) / len(scores),
                "min": min(score.results[metric_name].score for score in scores if score.results[metric_name].score is not None),
                "max": max(score.results[metric_name].score for score in scores if score.results[metric_name].score is not None)
            }
        else:
            resultados_json["puntuaciones"][metric_name] = {"promedio": None, "min": None, "max": None}
    
    # Datos de cada caso
    for i, test_case in enumerate(evaluador.test_cases):
        caso = {
            "id": i + 1,
            "pregunta": test_case.input,
            "respuesta": test_case.actual_output,
            "esperado": test_case.expected_output,
            "contexto": test_case.context[:3],  # Limitar a los primeros 3 fragmentos para no hacer el archivo demasiado grande
            "puntuaciones": {}
        }
        
        # Procesar puntuaciones específicas para el formato de respuesta actualizado
        hallucination_score = getattr(test_case, "hallucination_score", None)
        answer_score = getattr(test_case, "answer_score", None)
        
        # Convertir string "yes"/"no" a booleano si es necesario
        if isinstance(hallucination_score, str):
            hallucination_score = hallucination_score.lower() == "yes"
        if isinstance(answer_score, str):
            answer_score = answer_score.lower() == "yes"
            
        # Añadir metadatos relevantes
        caso["metadata"] = {
            "tiempo_completado": test_case.completion_time,
            "tokens_totales": test_case.token_cost,
            "modelo": getattr(test_case, "model_info", "unknown"),
            "cubos_relevantes": getattr(test_case, "relevant_cubos", []),
            "es_consulta": getattr(test_case, "is_consulta", False),
            "puntuacion_alucinacion": hallucination_score,
            "puntuacion_respuesta": answer_score
        }
        
        # Añadir puntuaciones individuales
        if hasattr(test_case, "results"):
            for metric_name, result in test_case.results.items():
                caso["puntuaciones"][metric_name] = result.score if result.score is not None else None
        
        resultados_json["casos"].append(caso)
    
    # Guardar a archivo
    with open(archivo_resultados, 'w', encoding='utf-8') as f:
        json.dump(resultados_json, f, ensure_ascii=False, indent=2)
    
    return archivo_resultados

def main():
    parser = argparse.ArgumentParser(description="Evaluador de agentes RAG")
    parser.add_argument("--data_dir", help="Directorio con documentos")
    parser.add_argument("--chroma_dir", help="Directorio de bases vectoriales Chroma")
    parser.add_argument("--modelo", help="Nombre del modelo LLM principal")
    parser.add_argument("--modelo2", help="Nombre del segundo modelo LLM")
    parser.add_argument("--salida", help="Ruta para guardar resultados")
    parser.add_argument("--verbose", action="store_true", help="Mostrar información detallada")
    parser.add_argument("--casos", help="Archivo JSON con casos de prueba")
    
    args = parser.parse_args()
    
    # Crear evaluador
    evaluador = AgentEvaluator(
        data_dir=args.data_dir,
        chroma_base_dir=args.chroma_dir,
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
        # Casos de prueba por defecto
        preguntas = [
            "¿Cómo se calcula la tasa de éxito académico?",
            "¿Qué diferencia hay entre créditos evaluados y créditos superados?"
        ]
        respuestas_esperadas = [None, None]
    
    # Ejecutar evaluación
    resultados = evaluador.evaluar(preguntas, respuestas_esperadas)
    
    # Guardar resultados
    ruta_resultados = guardar_resultados_deepeval(evaluador, resultados, args.salida)
    
    print(f"Evaluación completada. Resultados guardados en: {ruta_resultados}")

if __name__ == "__main__":
    main() 