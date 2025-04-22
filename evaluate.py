# Archivo: evaluate.py

"""
Script de evaluación para LangChainAgent utilizando deepeval.
Este script permite evaluar las respuestas del agente RAG con métricas de deepeval.
"""

import os
import argparse
import json
import time
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
from langagent.lang_chain_agent import LangChainAgent

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
        hallucination_score = resultado.get("hallucination_score")
        answer_score = resultado.get("answer_score")
        ambito = resultado.get("ambito")
        retrieval_details = resultado.get("retrieval_details", {})
        
        # Extraer metadatos de respuesta si existen
        response_metadata = resultado.get("response_metadata", {})
        
        # Calcular información de tokens y costos
        token_info = self.calcular_token_cost(response_metadata)
        
        # Agregar tiempo de completado e info de tokens como metadatos adicionales
        metadata = {
            "completion_time": tiempo_completado,
            "token_info": token_info,
            "model_info": response_metadata.get("model", "unknown"),
            "hallucination_score": hallucination_score,
            "answer_score": answer_score,
            "relevant_cubos": relevant_cubos,
            "ambito": ambito,
            "is_consulta": is_consulta,
            "retrieval_details": retrieval_details
        }
        
        # Convertir documentos a formato de texto para el contexto
        retrieval_context = [doc.page_content for doc in documents] if documents else []
        
        # Si es una consulta, agregar documentos de consulta al contexto
        if is_consulta and consulta_documents:
            retrieval_context.extend([doc.page_content for doc in consulta_documents])
        
        # Crear caso de prueba
        test_case = LLMTestCase(
            input=pregunta,
            actual_output=generation if generation else str(resultado.get("generation", "")),
            expected_output=respuesta_esperada if respuesta_esperada else None,
            retrieval_context=retrieval_context,
            metadata=metadata
        )
        
        self.test_cases.append(test_case)
        return test_case
    
    def evaluar(self, preguntas: List[str], respuestas_esperadas: List[str] = None):
        """
        Evalúa una lista de preguntas usando el agente y deepeval.
        
        Args:
            preguntas (List[str]): Lista de preguntas a evaluar.
            respuestas_esperadas (List[str], optional): Lista de respuestas esperadas.
            
        Returns:
            Dict: Resultados de la evaluación.
        """
        # Asegurar que respuestas_esperadas tenga la misma longitud que preguntas
        if respuestas_esperadas is None:
            respuestas_esperadas = [None] * len(preguntas)
        elif len(respuestas_esperadas) != len(preguntas):
            respuestas_esperadas.extend([None] * (len(preguntas) - len(respuestas_esperadas)))
        
        # Crear casos de prueba para cada pregunta
        self.test_cases = []
        self.raw_outputs = []
        for pregunta, respuesta_esperada in zip(preguntas, respuestas_esperadas):
            self.crear_caso_prueba(pregunta, respuesta_esperada)
        
        # Definir qué métricas usar basado en si tenemos respuestas esperadas
        metricas_a_usar = list(self.metrics.values())
        if all(resp is None for resp in respuestas_esperadas):
            # Si no hay respuestas esperadas, quitar métricas que las requieren
            metricas_a_usar = [
                self.metrics["answer_relevancy"],
                self.metrics["faithfulness"],
                self.metrics["contextual_relevancy"]
            ]
        
        # Evaluar todos los casos de prueba
        resultados = evaluate(
            test_cases=self.test_cases,
            metrics=metricas_a_usar
        )
        
        # Agregar información adicional a los resultados
        resultados["raw_outputs"] = self.raw_outputs
        
        return resultados
    
    def evaluar_pregunta(self, pregunta: str, respuesta_esperada: str = None):
        """
        Evalúa una sola pregunta usando el agente y deepeval.
        
        Args:
            pregunta (str): Pregunta a evaluar.
            respuesta_esperada (str, optional): Respuesta esperada para la pregunta.
            
        Returns:
            Dict: Resultados de la evaluación.
        """
        test_case = self.crear_caso_prueba(pregunta, respuesta_esperada)
        
        # Definir qué métricas usar basado en si tenemos respuesta esperada
        metricas_a_usar = list(self.metrics.values())
        if respuesta_esperada is None:
            # Si no hay respuesta esperada, quitar métricas que la requieren
            metricas_a_usar = [
                self.metrics["answer_relevancy"],
                self.metrics["faithfulness"],
                self.metrics["contextual_relevancy"]
            ]
        
        # Evaluar el caso de prueba
        resultados = evaluate(
            test_cases=[test_case],
            metrics=metricas_a_usar
        )
        
        # Agregar información adicional a los resultados
        resultados["raw_outputs"] = self.raw_outputs
        
        return resultados

def guardar_resultados_deepeval(evaluador, resultados, ruta_salida=None):
    """
    Guarda los resultados de evaluación incluyendo metadatos adicionales.
    
    Args:
        evaluador (AgentEvaluator): Instancia del evaluador usado.
        resultados (Dict): Resultados de la evaluación.
        ruta_salida (str, optional): Ruta donde guardar los resultados.
        
    Returns:
        str: Ruta donde se guardaron los resultados.
    """
    # Crear directorio de resultados si no existe
    if ruta_salida is None:
        directorio = "resultados_evaluacion"
        if not os.path.exists(directorio):
            os.makedirs(directorio)
        
        # Crear nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_salida = os.path.join(directorio, f"evaluacion_deepeval_{timestamp}.json")
    
    # Preparar datos para guardar
    datos_guardados = {
        "timestamp": datetime.now().isoformat(),
        "metricas_evaluadas": [metric.name for metric in resultados["metrics"]],
        "casos_evaluados": []
    }
    
    # Procesar resultados por cada caso
    for i, test_case in enumerate(evaluador.test_cases):
        # Extraer información de métricas
        scores = {}
        for metric in resultados["metrics"]:
            if i < len(resultados["scores"][metric.name]):
                scores[metric.name] = resultados["scores"][metric.name][i]
        
        # Extraer metadatos del caso de prueba
        metadata = test_case.metadata if hasattr(test_case, "metadata") else {}
        
        # Crear entrada para este caso
        caso = {
            "pregunta": test_case.input,
            "respuesta_generada": test_case.actual_output,
            "respuesta_esperada": test_case.expected_output if test_case.expected_output else "",
            "contexto_recuperado": test_case.retrieval_context,
            "scores": scores,
            "metadata": metadata
        }
        
        # Agregar salida completa del agente si está disponible
        if i < len(evaluador.raw_outputs):
            caso["raw_output"] = evaluador.raw_outputs[i]
        
        datos_guardados["casos_evaluados"].append(caso)
    
    # Guardar en archivo JSON
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(datos_guardados, f, ensure_ascii=False, indent=2)
    
    return ruta_salida

def main():
    parser = argparse.ArgumentParser(description="Evalúa el agente RAG con DeepEval")
    parser.add_argument("--preguntas", nargs="+", required=True, help="Preguntas para evaluar")
    parser.add_argument("--respuestas", nargs="*", help="Respuestas esperadas (opcional)")
    parser.add_argument("--data_dir", help="Directorio con datos de documentos")
    parser.add_argument("--chroma_dir", help="Directorio de bases vectoriales Chroma")
    parser.add_argument("--modelo", help="Nombre del modelo LLM principal")
    parser.add_argument("--modelo2", help="Nombre del segundo modelo LLM")
    parser.add_argument("--guardar", help="Ruta para guardar los resultados")
    parser.add_argument("--verbose", action="store_true", help="Mostrar información detallada")
    
    args = parser.parse_args()
    
    # Crear evaluador
    evaluador = AgentEvaluator(
        data_dir=args.data_dir,
        chroma_base_dir=args.chroma_dir,
        local_llm=args.modelo,
        local_llm2=args.modelo2
    )
    
    # Evaluar preguntas
    resultados = evaluador.evaluar(args.preguntas, args.respuestas)
    
    # Guardar resultados detallados
    ruta_resultados = guardar_resultados_deepeval(evaluador, resultados, args.guardar)
    
    print("\nResultados de evaluación:")
    for i, test_case in enumerate(evaluador.test_cases):
        print(f"\nPregunta {i+1}: {test_case.input}")
        print(f"Respuesta: {test_case.actual_output}")
        
        # Mostrar métricas
        print("Métricas:")
        for metric in resultados["metrics"]:
            if i < len(resultados["scores"][metric.name]):
                print(f"  - {metric.name}: {resultados['scores'][metric.name][i]}")
                if hasattr(metric, 'reason') and metric.reason:
                    print(f"    Razón: {metric.reason}")
        
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
    
    print(f"\nResultados guardados en: {ruta_resultados}")

if __name__ == "__main__":
    main()



