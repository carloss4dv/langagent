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
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
import deepeval
from deepeval.evaluate import AsyncConfig
from deepeval import evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualRelevancyMetric,
    ContextualRecallMetric,
    ContextualPrecisionMetric
)
from deepeval.test_case import LLMTestCase
from deepeval.dataset import Golden
from deepeval.evaluate import CacheConfig
from deepeval.evaluate import ErrorConfig
import pickle
from datetime import datetime

# Asegurarnos que podemos importar desde el directorio raíz
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Importar LangChainAgent desde el módulo core
from langagent.core.lang_chain_agent import LangChainAgent

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

class AgentEvaluator:
    """
    Evaluador que utiliza deepeval para evaluar las respuestas del agente LangChain.
    """
    
    def __init__(self, data_dir=None, vectorstore_dir=None, vector_db_type="milvus", local_llm=None, local_llm2=None, local_llm3=None):
        """
        Inicializa el evaluador con el agente LangChain.
        
        Args:
            data_dir (str, optional): Directorio con los documentos markdown.
            vectorstore_dir (str, optional): Directorio base para las bases de datos vectoriales.
            vector_db_type (str, optional): Tipo de vectorstore a utilizar ('chroma' o 'milvus').
            local_llm (str, optional): Nombre del modelo LLM principal.
            local_llm2 (str, optional): Nombre del segundo modelo LLM.
            local_llm3 (str, optional): Nombre del tercer modelo LLM.
        """
        self.agent = LangChainAgent(
            data_dir=data_dir,
            vectorstore_dir=vectorstore_dir,
            vector_db_type=vector_db_type,
            local_llm=local_llm,
            local_llm2=local_llm2,
            local_llm3=local_llm3
        )
        self.checkpoint_dir = os.path.join(os.getcwd(), "checkpoints")
        if not os.path.exists(self.checkpoint_dir):
            os.makedirs(self.checkpoint_dir)
            
    def generar_nombre_checkpoint(self, preguntas: List[str], config_hash: str = None) -> str:
        """
        Genera un nombre único para el archivo de checkpoint basado en las preguntas y configuración.
        
        Args:
            preguntas (List[str]): Lista de preguntas a evaluar.
            config_hash (str, optional): Hash de la configuración del agente.
            
        Returns:
            str: Nombre del archivo de checkpoint.
        """
        # Crear un hash simple de las preguntas
        preguntas_text = "|".join(preguntas)
        preguntas_hash = str(hash(preguntas_text))[-8:]  # Últimos 8 caracteres del hash
        
        # Incluir configuración del modelo si está disponible
        modelo_info = f"{self.agent.local_llm or 'default'}"
        
        # Crear nombre del archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"checkpoint_{modelo_info}_{preguntas_hash}_{timestamp}.pkl"
        
        return os.path.join(self.checkpoint_dir, nombre)
        return os.path.join(self.checkpoint_dir, nombre)
    
    def buscar_checkpoint_existente(self, preguntas: List[str]) -> Optional[str]:
        """
        Busca un checkpoint existente que coincida con las preguntas proporcionadas.
        
        Args:
            preguntas (List[str]): Lista de preguntas a evaluar.
            
        Returns:
            Optional[str]: Ruta del checkpoint si existe, None en caso contrario.
        """
        if not os.path.exists(self.checkpoint_dir):
            return None
        
        # Crear hash de las preguntas actuales
        preguntas_text = "|".join(preguntas)
        preguntas_hash = str(hash(preguntas_text))[-8:]
        
        # Buscar archivos de checkpoint que coincidan
        for archivo in os.listdir(self.checkpoint_dir):
            if archivo.endswith('.pkl'):
                ruta_completa = os.path.join(self.checkpoint_dir, archivo)
                # Verificar que el archivo sea válido
                try:
                    with open(ruta_completa, 'rb') as f:
                        data = pickle.load(f)
                        # Verificar que tenga la estructura esperada
                        if isinstance(data, dict) and "test_cases" in data and "metadata" in data:
                            # Verificar que las preguntas coincidan exactamente
                            checkpoint_preguntas = [tc.input for tc in data["test_cases"]]
                            if checkpoint_preguntas == preguntas:
                                logger.info(f"✓ Checkpoint encontrado: {archivo}")
                                return ruta_completa
                except Exception as e:
                    logger.warning(f"⚠️  Checkpoint corrupto ignorado: {archivo} - {e}")
                    continue
        
        return None

    def guardar_checkpoint(self, test_cases: List, preguntas: List[str], metadata: Dict = None) -> str:
        """
        Guarda los casos de prueba en un archivo de checkpoint.
        
        Args:
            test_cases (List): Lista de casos de prueba evaluados.
            preguntas (List[str]): Lista de preguntas originales.
            metadata (Dict, optional): Metadatos adicionales.
            
        Returns:
            str: Ruta del archivo de checkpoint guardado.
        """
        checkpoint_data = {
            "test_cases": test_cases,
            "preguntas": preguntas,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "agent_config": {
                "local_llm": getattr(self.agent, 'local_llm', None),
                "local_llm2": getattr(self.agent, 'local_llm2', None),
                "local_llm3": getattr(self.agent, 'local_llm3', None),
                "vector_db_type": getattr(self.agent, 'vector_db_type', None)
            }
        }
        
        archivo_checkpoint = self.generar_nombre_checkpoint(preguntas)
        
        try:
            with open(archivo_checkpoint, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            logger.info(f"✓ Checkpoint guardado: {archivo_checkpoint}")
            return archivo_checkpoint
        except Exception as e:
            logger.error(f"✗ Error al guardar checkpoint: {e}")
            raise
        
    def cargar_checkpoint(self, ruta_checkpoint: str) -> Dict:
        """
        Carga los datos desde un archivo de checkpoint.
        
        Args:
            ruta_checkpoint (str): Ruta del archivo de checkpoint.
            
        Returns:
            Dict: Datos del checkpoint cargados.
        """
        try:
            with open(ruta_checkpoint, 'rb') as f:
                data = pickle.load(f)
                logger.info(f"✓ Checkpoint cargado: {ruta_checkpoint}")
                logger.info(f"  - Timestamp: {data.get('timestamp', 'No disponible')}")
                logger.info(f"  - Casos de prueba: {len(data.get('test_cases', []))}")
                return data
        except Exception as e:
            logger.error(f"✗ Error al cargar checkpoint: {e}")
            raise
    
    
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
                logger.error(f"Error al procesar los metadatos de respuesta: {e}")
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
        # Si es un diccionario con campo answer directo (nuevo formato)
        if isinstance(respuesta, dict) and "answer" in respuesta:
            return respuesta["answer"]
        
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
                            # Asegurar que tenemos un JSON completo antes de parsear
                            if content_str.strip().startswith('{') and content_str.strip().endswith('}'):
                                content_json = json.loads(content_str)
                                if "answer" in content_json:
                                    return content_json["answer"]
                        except json.JSONDecodeError:
                            # Si falla el parsing, extraer manualmente
                            answer_start = content_str.find('"answer": "') + 10
                            if answer_start > 9:
                                # Buscar el último cierre de comillas, para evitar truncamiento en dos puntos
                                content_remainder = content_str[answer_start:]
                                # Buscar el último cierre de comillas antes del cierre de llave
                                last_brace = content_remainder.rfind('}')
                                search_end = last_brace if last_brace > 0 else len(content_remainder)
                                last_quote = content_remainder[:search_end].rfind('"')
                                if last_quote > 0:
                                    return content_remainder[:last_quote]
                                
                except Exception as e:
                    logger.error(f"Error al procesar formato de respuesta específico: {e}")
            
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
                                    # Asegurar que tenemos un JSON completo
                                    if json_str.strip().startswith('{') and json_str.strip().endswith('}'):
                                        content_json = json.loads(json_str)
                                        return content_json.get("answer", "No se pudo extraer la respuesta")
                                except json.JSONDecodeError:
                                    # Si falla, usar un enfoque más robusto para extraer la respuesta
                                    answer_start = json_str.find('"answer": "') + 11
                                    if answer_start > 10:
                                        # Buscar el último cierre de comillas antes del cierre de llave
                                        json_remainder = json_str[answer_start:]
                                        last_brace = json_remainder.rfind('}')
                                        search_end = last_brace if last_brace > 0 else len(json_remainder)
                                        last_quote = json_remainder[:search_end].rfind('"')
                                        if last_quote > 0:
                                            return json_remainder[:last_quote]
                except Exception as e:
                    logger.error(f"Error al procesar la generación: {e}")
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
                        # Si falla el parsing pero tiene estructura de JSON, extraer manualmente
                        if '"answer":' in content:
                            answer_start = content.find('"answer": "') + 11
                            if answer_start > 10:
                                content_remainder = content[answer_start:]
                                last_brace = content_remainder.rfind('}')
                                search_end = last_brace if last_brace > 0 else len(content_remainder)
                                last_quote = content_remainder[:search_end].rfind('"')
                                if last_quote > 0:
                                    return content_remainder[:last_quote]
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
            
            # Verificar si el resultado requiere clarificación
            if resultado.get("type") == "clarification_needed":
                logger.warning(f"⚠️  Pregunta requiere clarificación, marcando como no evaluable: {pregunta}")
                logger.warning(f"   Pregunta de clarificación: {resultado.get('question', 'No disponible')}")
                
                # Crear un caso de prueba marcado como no evaluable
                test_case = LLMTestCase(
                    input=golden.input,
                    actual_output=f"CLARIFICATION_NEEDED: {resultado.get('question', 'Se requiere clarificación')}",
                    expected_output=golden.expected_output,
                    retrieval_context=[],
                    token_cost=0,
                    completion_time=tiempo_completado
                )
                # Agregar metadatos para identificar que no debe evaluarse
                test_case.clarification_needed = True
                test_cases.append(test_case)
                time.sleep(0.5)
                continue
            
            
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
                token_cost=token_info.get("cost_estimate", {}).get("total_cost", 0),
                completion_time=tiempo_completado
            )
            time.sleep(0.5)  # Esperar medio segundo entre ejecuciones
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

    def evaluar(self, preguntas: List[str], respuestas_esperadas: List[str] = None, usar_checkpoint: bool = True, forzar_reevaluacion: bool = False):
        """
        Evalúa una lista de preguntas con las métricas configuradas.
        
        Args:
            preguntas (List[str]): Lista de preguntas a evaluar.
            respuestas_esperadas (List[str], optional): Lista de respuestas esperadas. 
                Si no se proporciona, se usa None para cada pregunta.
            usar_checkpoint (bool): Si buscar y usar checkpoints existentes.
            forzar_reevaluacion (bool): Si forzar una nueva evaluación ignorando checkpoints.
                
        Returns:
            Dict: Resultados de la evaluación.
        """
        # Buscar checkpoint existente si está habilitado
        checkpoint_path = None
        if usar_checkpoint and not forzar_reevaluacion:
            checkpoint_path = self.buscar_checkpoint_existente(preguntas)
        
        if checkpoint_path:
            logger.info("🔄 Cargando desde checkpoint existente...")
            checkpoint_data = self.cargar_checkpoint(checkpoint_path)
            test_cases = checkpoint_data["test_cases"]
            
            # Filtrar casos que requieren clarificación para la evaluación
            casos_evaluables = [tc for tc in test_cases if not hasattr(tc, 'clarification_needed') or not tc.clarification_needed]
            casos_clarificacion = [tc for tc in test_cases if hasattr(tc, 'clarification_needed') and tc.clarification_needed]
            
            if casos_clarificacion:
                logger.warning(f"⚠️  {len(casos_clarificacion)} casos requieren clarificación y no serán evaluados con métricas")
            
            if casos_evaluables:
                logger.info("🔄 Ejecutando evaluación con métricas desde checkpoint...")
                
                # Definir las métricas para la evaluación
                metrics = [
                    deepeval.metrics.AnswerRelevancyMetric(),
                    deepeval.metrics.FaithfulnessMetric(),
                    deepeval.metrics.ContextualPrecisionMetric(),
                    deepeval.metrics.ContextualRecallMetric(),
                    deepeval.metrics.ContextualRelevancyMetric()
                ]
                
                # Evaluar solo los casos evaluables
                results = evaluate(cache_config=CacheConfig(write_cache=True, use_cache=True),
                                   error_config=ErrorConfig(ignore_errors=False),
                                   async_config=AsyncConfig(run_async=False),
                                   test_cases=casos_evaluables, metrics=metrics)
                return {
                    "results": results,
                    "test_cases": test_cases,  # Incluir todos los casos (evaluables y no evaluables)
                    "casos_evaluables": len(casos_evaluables),
                    "casos_clarificacion": len(casos_clarificacion),
                    "checkpoint_usado": checkpoint_path
                }
            else:
                logger.warning("⚠️  No hay casos evaluables en el checkpoint")
                return {
                    "results": None,
                    "test_cases": test_cases,
                    "casos_evaluables": 0,
                    "casos_clarificacion": len(casos_clarificacion),
                    "checkpoint_usado": checkpoint_path
                }
        else:
            logger.info("🚀 Iniciando nueva evaluación...")
            
            # Convertir preguntas y respuestas a objetos Golden
            goldens = self.convertir_a_golden(preguntas, respuestas_esperadas)
            
            # Convertir los goldens a casos de prueba
            logger.info("🔄 Ejecutando agente para generar respuestas...")
            test_cases = self.convertir_goldens_a_test_cases(goldens)
            
            # Guardar checkpoint después de generar los casos de prueba
            metadata = {
                "total_casos": len(test_cases),
                "respuestas_esperadas_proporcionadas": respuestas_esperadas is not None
            }
            checkpoint_path = self.guardar_checkpoint(test_cases, preguntas, metadata)
            
            # Filtrar casos que requieren clarificación
            casos_evaluables = [tc for tc in test_cases if not hasattr(tc, 'clarification_needed') or not tc.clarification_needed]
            casos_clarificacion = [tc for tc in test_cases if hasattr(tc, 'clarification_needed') and tc.clarification_needed]
            
            if casos_clarificacion:
                logger.warning(f"⚠️  {len(casos_clarificacion)} casos requieren clarificación y no serán evaluados con métricas")
            
            if casos_evaluables:
                time.sleep(10)  # Esperar 10 segundos antes de iniciar la evaluación
                
                logger.info("🔄 Ejecutando evaluación con métricas...")
                
                # Definir las métricas para la evaluación
                metrics = [
                    deepeval.metrics.AnswerRelevancyMetric(),
                    deepeval.metrics.FaithfulnessMetric(),
                    deepeval.metrics.ContextualPrecisionMetric(),
                    deepeval.metrics.ContextualRecallMetric(),
                    deepeval.metrics.ContextualRelevancyMetric()
                ]
                
                # Evaluar solo los casos evaluables
                results = evaluate(cache_config=CacheConfig(write_cache=True, use_cache=True),
                                   error_config=ErrorConfig(ignore_errors=False),
                                   async_config=AsyncConfig(run_async=False),
                                   test_cases=casos_evaluables, metrics=metrics)
                return {
                    "results": results,
                    "test_cases": test_cases,
                    "casos_evaluables": len(casos_evaluables),
                    "casos_clarificacion": len(casos_clarificacion),
                    "checkpoint_guardado": checkpoint_path
                }
            else:
                logger.warning("⚠️  No hay casos evaluables para métricas")
                return {
                    "results": None,
                    "test_cases": test_cases,
                    "casos_evaluables": 0,
                    "casos_clarificacion": len(casos_clarificacion),
                    "checkpoint_guardado": checkpoint_path
                }

def main():
    parser = argparse.ArgumentParser(description="Evaluador de agentes RAG")
    parser.add_argument("--data_dir", help="Directorio con documentos")
    parser.add_argument("--chroma_dir", help="Directorio de bases vectoriales Chroma")
    parser.add_argument("--modelo", help="Nombre del modelo LLM principal")
    parser.add_argument("--modelo2", help="Nombre del segundo modelo LLM")
    parser.add_argument("--modelo3", help="Nombre del tercer modelo LLM")
    parser.add_argument("--casos", help="Archivo JSON con casos de prueba")
    parser.add_argument("--vector_db_type", default="milvus", choices=["chroma", "milvus"],
                       help="Tipo de vectorstore a utilizar (default: milvus)")
    
    args = parser.parse_args()
    
    # Crear evaluador
    evaluador = AgentEvaluator(
        data_dir=args.data_dir,
        vectorstore_dir=args.chroma_dir,
        vector_db_type=args.vector_db_type,
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
    evaluador.evaluar(preguntas, respuestas_esperadas)

if __name__ == "__main__":
    main()