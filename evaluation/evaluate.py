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
from deepeval.dataset import Golden

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
            # Extraer modelo
            if "model" in response_metadata:
                token_info["model"] = response_metadata.get("model", "unknown")
        
        # Calcular costos aproximados (precios típicos por 1000 tokens)
        token_info["cost_estimate"] = {}
        
        # Determinar los precios según el modelo
        modelo = token_info.get("model", "").lower()
        
        # Precios predeterminados (GPT-3.5-turbo)
        precio_entrada = 0.0005  # $ por 1000 tokens de entrada
        precio_salida = 0.0015   # $ por 1000 tokens de salida
        
        # Ajustar precios según el modelo
        if "mistral" in modelo:
            precio_entrada = 0.0002  # $ por 1000 tokens de entrada para Mistral
            precio_salida = 0.0006   # $ por 1000 tokens de salida para Mistral
        elif "gpt-4" in modelo:
            precio_entrada = 0.03    # $ por 1000 tokens de entrada para GPT-4
            precio_salida = 0.06     # $ por 1000 tokens de salida para GPT-4
        elif "claude-3" in modelo or "claude3" in modelo:
            if "haiku" in modelo:
                precio_entrada = 0.00025  # $ por 1000 tokens de entrada para Claude 3 Haiku
                precio_salida = 0.00125   # $ por 1000 tokens de salida para Claude 3 Haiku
            elif "sonnet" in modelo:
                precio_entrada = 0.003   # $ por 1000 tokens de entrada para Claude 3 Sonnet
                precio_salida = 0.015    # $ por 1000 tokens de salida para Claude 3 Sonnet
            elif "opus" in modelo:
                precio_entrada = 0.015   # $ por 1000 tokens de entrada para Claude 3 Opus
                precio_salida = 0.075    # $ por 1000 tokens de salida para Claude 3 Opus
            else:
                precio_entrada = 0.003   # $ por 1000 tokens de entrada para Claude por defecto
                precio_salida = 0.015    # $ por 1000 tokens de salida para Claude por defecto
        
        # Si tenemos información detallada de tokens
        if "input_tokens" in token_info and "output_tokens" in token_info:
            token_info["cost_estimate"]["input_cost"] = (token_info["input_tokens"] / 1000) * precio_entrada
            token_info["cost_estimate"]["output_cost"] = (token_info["output_tokens"] / 1000) * precio_salida
            token_info["cost_estimate"]["total_cost"] = token_info["cost_estimate"]["input_cost"] + token_info["cost_estimate"]["output_cost"]
        elif "total_tokens" in token_info:
            # Estimación básica si solo tenemos tokens totales
            precio_promedio = (precio_entrada + precio_salida) / 2
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
            # Formato específico mostrado en el ejemplo del usuario
            # content='{ "answer": "I cannot answer based on the available data" }'
            if "content='" in respuesta and '"answer":' in respuesta:
                try:
                    # Extraer el contenido JSON
                    content_start = respuesta.find("content='") + 9
                    content_end = respuesta.find("'", content_start)
                    if content_start > 9 and content_end > content_start:
                        content_str = respuesta[content_start:content_end]
                        # Intentar parsear como JSON
                        try:
                            content_json = json.loads(content_str)
                            if "answer" in content_json:
                                return content_json["answer"]
                        except json.JSONDecodeError:
                            # Si falla el parsing, extraer manualmente
                            answer_start = content_str.find('"answer": "') + 10
                            answer_end = content_str.rfind('"')
                            if answer_start > 10 and answer_end > answer_start:
                                return content_str[answer_start:answer_end]
                except Exception as e:
                    print(f"Error al procesar formato de respuesta específico: {e}")
            
            # Formato antiguo de generación con content
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
                # Verificar si content es un string JSON
                if isinstance(content, str) and content.startswith('{') and content.endswith('}'):
                    try:
                        content_json = json.loads(content)
                        if "answer" in content_json:
                            return content_json["answer"]
                    except json.JSONDecodeError:
                        pass
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
        response_metadata = None
        
        # Extraer metadatos de respuesta si existen antes de procesar la generación
        if "response_metadata" in resultado:
            response_metadata = resultado["response_metadata"]
        
        # Verificar si generation es un string con formato especial
        if "generation" in resultado:
            gen = resultado["generation"]
            # Formato específico con response_metadata y usage_metadata
            if isinstance(gen, str) and "response_metadata=" in gen:
                try:
                    # Extraer el texto de la respuesta
                    generation = self.extraer_texto_respuesta(gen)
                    
                    # Extraer los metadatos de respuesta
                    metadata_start = gen.find("response_metadata={") 
                    if metadata_start > 0:
                        # Cortar el string para obtener solo la parte de los metadatos
                        metadata_str = gen[metadata_start:]
                        response_metadata = metadata_str
                except Exception as e:
                    print(f"Error al procesar metadatos del formato especial: {e}")
            else:
                # Formato normal
                generation = self.extraer_texto_respuesta(gen)
                # Si no hay response_metadata, intentar extraerlo de generation
                if not response_metadata and isinstance(gen, dict):
                    response_metadata = gen.get("response_metadata")
        
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
    
    def convertir_a_golden(self, preguntas: List[str], respuestas_esperadas: List[str] = None):
        """
        Convierte una lista de preguntas y respuestas esperadas en objetos Golden
        para su uso en la evaluación.
        
        Args:
            preguntas (List[str]): Lista de preguntas a evaluar.
            respuestas_esperadas (List[str], optional): Lista de respuestas esperadas.
                
        Returns:
            List: Lista de objetos Golden.
        """
        # Normalizar respuestas esperadas
        if respuestas_esperadas is None:
            respuestas_esperadas = [None] * len(preguntas)
        elif len(respuestas_esperadas) < len(preguntas):
            # Completar con None si hay menos respuestas que preguntas
            respuestas_esperadas.extend([None] * (len(preguntas) - len(respuestas_esperadas)))
        
        goldens = []
        for pregunta, respuesta_esperada in zip(preguntas, respuestas_esperadas):
            golden = Golden(
                input=pregunta,
                expected_output=respuesta_esperada
            )
            goldens.append(golden)
        
        return goldens

    def convertir_goldens_a_test_cases(self, goldens):
        """
        Convierte objetos Golden a casos de prueba LLMTestCase ejecutando el agente
        para cada pregunta en los Golden.
        
        Args:
            goldens: Lista de objetos Golden.
                
        Returns:
            List: Lista de objetos LLMTestCase.
        """
        test_cases = []
        
        for golden in goldens:
            # Registrar el tiempo de inicio
            tiempo_inicio = time.time()
            
            # Ejecutar el agente para obtener la respuesta
            pregunta = golden.input
            resultado = self.agent.run(pregunta)
            
            # Calcular tiempo de completado
            tiempo_completado = time.time() - tiempo_inicio
            
            # Guardar la respuesta completa para análisis
            self.raw_outputs.append({
                "pregunta": pregunta,
                "resultado_completo": resultado,
                "tiempo_completado": tiempo_completado
            })
            
            # Extraer el texto de la respuesta
            generation = None
            if "generation" in resultado:
                generation = self.extraer_texto_respuesta(resultado["generation"])
            if not generation and "response" in resultado:
                generation = self.extraer_texto_respuesta(resultado["response"])
            
            # Obtener el contexto utilizado
            documents = resultado.get("documents", [])
            is_consulta = resultado.get("is_consulta", False)
            consulta_documents = resultado.get("consulta_documents", [])
            relevant_cubos = resultado.get("relevant_cubos", [])
            ambito = resultado.get("ambito")
            retrieval_details = resultado.get("retrieval_details", {})
            
            # Extraer puntuaciones si existen
            hallucination_score = None
            if "hallucination_score" in resultado and isinstance(resultado["hallucination_score"], dict):
                hallucination_score = resultado["hallucination_score"].get("score")
            
            answer_score = None
            if "answer_score" in resultado and isinstance(resultado["answer_score"], dict):
                answer_score = resultado["answer_score"].get("score")
            
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
            
            # Extraer el contexto formateado
            context = self.obtener_contexto_formateado(context_docs)
            
            # Crear un caso de prueba con todos los campos disponibles
            test_case = LLMTestCase(
                input=golden.input,
                actual_output=generation or "No se pudo extraer una respuesta",
                expected_output=golden.expected_output,
                retrieval_context=context,
                token_cost=token_info.get("total_tokens", 0),
                completion_time=tiempo_completado
            )
            
            # Guardar metadatos adicionales como atributos del objeto para uso posterior
            test_case.hallucination_score = hallucination_score
            test_case.answer_score = answer_score
            test_case.relevant_cubos = relevant_cubos
            test_case.ambito = ambito
            test_case.is_consulta = is_consulta
            test_case.model_info = token_info.get("model", "unknown")
            test_case.token_info = token_info
            test_case.retrieval_details = retrieval_details
            
            test_cases.append(test_case)
        
        return test_cases

    def obtener_contexto_formateado(self, context_docs):
        """
        Convierte los documentos al formato esperado por deepeval.
        
        Args:
            context_docs: Lista de documentos a formatear.
                
        Returns:
            List[str]: Lista de strings con el contenido de los documentos.
        """
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
        return formatted_context

    def query_with_context(self, input_query):
        """
        Ejecuta una consulta y devuelve el resultado y el contexto.
        
        Args:
            input_query (str): La consulta a ejecutar.
                
        Returns:
            Tuple: (contexto, respuesta)
        """
        resultado = self.agent.run(input_query)
        generation = None
        
        if "generation" in resultado:
            generation = self.extraer_texto_respuesta(resultado["generation"])
        if not generation and "response" in resultado:
            generation = self.extraer_texto_respuesta(resultado["response"])
        
        # Obtener el contexto utilizado
        documents = resultado.get("documents", [])
        is_consulta = resultado.get("is_consulta", False)
        consulta_documents = resultado.get("consulta_documents", [])
        
        # Si es una consulta, agregar los documentos de consulta al contexto
        if is_consulta and consulta_documents:
            context_docs = consulta_documents
        else:
            # Usar los documentos recuperados normalmente
            context_docs = documents
        
        # Extraer el contexto
        context = self.obtener_contexto_formateado(context_docs)
        
        return context, generation

    def evaluar(self, preguntas: List[str], respuestas_esperadas: List[str] = None):
        """
        Evalúa una lista de preguntas con las métricas configuradas.
        Primero recopila todas las respuestas y luego realiza la evaluación.
        
        Args:
            preguntas (List[str]): Lista de preguntas a evaluar.
            respuestas_esperadas (List[str], optional): Lista de respuestas esperadas. 
                Si no se proporciona, se usa None para cada pregunta.
                
        Returns:
            Dict: Resultados de la evaluación, incluyendo métricas y puntuaciones.
        """
        # Convertir preguntas y respuestas a objetos Golden
        goldens = self.convertir_a_golden(preguntas, respuestas_esperadas)
        
        # Crear dataset para pruebas
        golden_dataset = goldens
        
        # Convertir los goldens a casos de prueba
        data = self.convertir_goldens_a_test_cases(golden_dataset)
        
        # Definir las métricas para la evaluación
        metrics = [
            deepeval.metrics.AnswerRelevancyMetric(),
            deepeval.metrics.FaithfulnessMetric(),
            deepeval.metrics.ContextualPrecisionMetric(),
            deepeval.metrics.ContextualRecallMetric(),
            deepeval.metrics.ContextualRelevancyMetric()
        ]
        
        # Evaluar todos los casos de prueba con todas las métricas
        results = deepeval.evaluate(data, metrics=metrics)
        
        # Guardar los casos de prueba para uso posterior
        self.test_cases = data
        
        return {
            "results": results,
            "test_cases": data
        }

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
    
    # Obtener los resultados de la evaluación y los casos de prueba
    test_cases = resultados.get("test_cases", [])
    eval_results = resultados.get("results", {})
    
    # Preparar resultados para serialización
    resultados_json = {
        "timestamp": timestamp,
        "nombre_evaluacion": f"Evaluación {timestamp}",
        "num_preguntas": len(test_cases),
        "metricas": {},
        "casos": []
    }
    
    # Extraer puntuaciones de las métricas
    if hasattr(eval_results, "metrics"):
        for metric in eval_results.metrics:
            metric_name = metric.__class__.__name__.replace("Metric", "").lower()
            resultados_json["metricas"][metric_name] = {
                "promedio": getattr(eval_results, f"{metric_name}_score", None),
                "passed": getattr(eval_results, f"{metric_name}_passed", False)
            }
    
    # Datos de cada caso
    for i, test_case in enumerate(test_cases):
        caso = {
            "id": i + 1,
            "pregunta": test_case.input,
            "respuesta": test_case.actual_output,
            "esperado": test_case.expected_output,
            "contexto": test_case.retrieval_context[:3] if hasattr(test_case, "retrieval_context") else [],
            "puntuaciones": {}
        }
        
        # Añadir metadatos relevantes
        caso["metadata"] = {
            "tiempo_completado": getattr(test_case, "completion_time", 0),
        }
        
        # Obtener puntuaciones individuales si están disponibles
        if hasattr(test_case, "metrics"):
            for metric_result in test_case.metrics:
                metric_name = metric_result.__class__.__name__.replace("Metric", "").lower()
                caso["puntuaciones"][metric_name] = metric_result.score
        
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
    parser.add_argument("--modelo3", help="Nombre del tercer modelo LLM")
    parser.add_argument("--salida", help="Ruta para guardar resultados")
    parser.add_argument("--verbose", action="store_true", help="Mostrar información detallada")
    parser.add_argument("--casos", help="Archivo JSON con casos de prueba")
    
    args = parser.parse_args()
    
    # Crear evaluador
    evaluador = AgentEvaluator(
        data_dir=args.data_dir,
        chroma_base_dir=args.chroma_dir,
        local_llm=args.modelo,
        local_llm2=args.modelo2,
        local_llm3=args.modelo3
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
    
    if args.verbose:
        print(f"Evaluación completada. Resultados guardados en: {ruta_resultados}")

if __name__ == "__main__":
    main() 