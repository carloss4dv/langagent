"""
Recolector de métricas para el workflow de LangGraph.

Este módulo implementa la recopilación de métricas detalladas por nodo y workflow,
organizadas por estrategia de chunking para análisis de rendimiento.
Incluye captura de métricas LLM detalladas.
"""

import os
import csv
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
from threading import Lock
from langagent.config.logging_config import get_logger
from langagent.config.config import LLM_CONFIG  # Añadir importación de configuración

logger = get_logger(__name__)

class MetricsCollector:
    """
    Recolector de métricas para el workflow de LangGraph.
    
    Recopila métricas por nodo y por workflow completo, organizándolas
    por estrategia de chunking para análisis comparativo de rendimiento.
    Incluye recolección detallada de métricas de llamadas a LLM.
    """
    
    def __init__(self, base_metrics_dir: str = "metrics"):
        """
        Inicializa el recolector de métricas.
        
        Args:
            base_metrics_dir: Directorio base para almacenar métricas
        """
        self.base_metrics_dir = Path(base_metrics_dir)
        self.question_id = None
        self.workflow_start_time = None
        self.workflow_data = {}
        self.node_executions = []
        self.llm_calls = []  # Lista para almacenar llamadas a LLM
        
        # Lock para operaciones thread-safe
        self._lock = Lock()
        
        # Headers para los archivos CSV
        self.node_metrics_headers = [
            'timestamp', 'question_id', 'node_name', 'execution_time_ms',
            'context_size_chars', 'context_size_tokens', 'documents_count',
            'retry_attempt', 'success'
        ]
        
        self.workflow_metrics_headers = [
            'timestamp', 'question_id', 'question', 'rewritten_question',
            'total_execution_time_ms', 'total_retries', 'initial_chunk_strategy',
            'final_chunk_strategy', 'is_adaptive_strategy', 'adaptive_chunks_used',
            'total_documents_retrieved', 'final_context_size_chars',
            'total_llm_calls', 'total_llm_time_ms', 'total_input_tokens', 
            'total_output_tokens', 'total_tokens', 'evaluation_metrics', 'success'
        ]
        
        # Headers para métricas de LLM
        self.llm_metrics_headers = [
            'timestamp', 'question_id', 'node_name', 'call_order', 'model',
            'prompt_length', 'response_length', 'input_tokens', 'output_tokens', 
            'total_tokens', 'duration_ms', 'load_duration_ms', 'prompt_eval_duration_ms',
            'eval_duration_ms', 'eval_count', 'run_id', 'success'
        ]
        
        # Crear directorios base
        self._ensure_directories()
        
        logger.info(f"MetricsCollector inicializado con directorio base: {self.base_metrics_dir}")
    
    def _ensure_directories(self):
        """Crea los directorios necesarios para las métricas."""
        # Estrategias fijas
        fixed_strategies = ['256', '512', '1024']
        
        # Estrategias adaptativas (con prefijo E)
        adaptive_strategies = ['E256', 'E512', 'E1024']
        
        all_strategies = fixed_strategies + adaptive_strategies
        
        for strategy in all_strategies:
            strategy_dir = self.base_metrics_dir / strategy
            strategy_dir.mkdir(parents=True, exist_ok=True)
            
            # Crear archivos CSV con headers si no existen
            node_metrics_file = strategy_dir / 'node_metrics.csv'
            workflow_metrics_file = strategy_dir / 'workflow_metrics.csv'
            llm_metrics_file = strategy_dir / 'llm_metrics.csv'
            
            if not node_metrics_file.exists():
                with open(node_metrics_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.node_metrics_headers)
            
            if not workflow_metrics_file.exists():
                with open(workflow_metrics_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.workflow_metrics_headers)
                    
            if not llm_metrics_file.exists():
                with open(llm_metrics_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.llm_metrics_headers)
    
    def start_workflow(self, question: str, chunk_strategy: str = "512", is_adaptive: bool = False):
        """
        Inicia la recopilación de métricas para un nuevo workflow.
        
        Args:
            question: Pregunta original del usuario
            chunk_strategy: Estrategia de chunking inicial
            is_adaptive: Si se está usando estrategia adaptativa
        """
        with self._lock:
            self.question_id = str(uuid.uuid4())
            self.workflow_start_time = time.time()
            self.node_executions = []
            self.llm_calls = []
            
            # Determinar la estrategia correcta con prefijo si es adaptativa
            if is_adaptive and not chunk_strategy.startswith('E'):
                display_strategy = f"E{chunk_strategy}"
            else:
                display_strategy = chunk_strategy
            
            self.workflow_data = {
                'question_id': self.question_id,
                'question': question,
                'rewritten_question': '',
                'initial_chunk_strategy': chunk_strategy,
                'final_chunk_strategy': chunk_strategy,
                'is_adaptive_strategy': is_adaptive,
                'adaptive_chunks_used': [],
                'total_retries': 0,
                'total_documents_retrieved': 0,
                'final_context_size_chars': 0,
                'total_llm_calls': 0,
                'total_llm_time_ms': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_tokens': 0,
                'evaluation_metrics': {},
                'success': False
            }
            
        logger.info(f"Iniciado workflow con ID: {self.question_id}, estrategia: {display_strategy}")
    
    def log_llm_call(self, node_name: str, response_data: Any, prompt_text: str = "", success: bool = True):
        """
        Registra una llamada a LLM con sus métricas detalladas.
        
        Args:
            node_name: Nombre del nodo que realizó la llamada
            response_data: Respuesta del LLM (AIMessageChunk o similar)
            prompt_text: Texto del prompt enviado
            success: Si la llamada fue exitosa
        """
        try:
            call_timestamp = time.time()
            call_order = len(self.llm_calls) + 1
            
            # LOGS DE DEBUG DETALLADOS
            logger.debug(f"=== DEBUGGING LLM CALL - Nodo: {node_name} ===")
            logger.debug(f"Tipo de response_data: {type(response_data)}")
            logger.debug(f"Atributos de response_data: {dir(response_data) if hasattr(response_data, '__dict__') else 'No tiene __dict__'}")
            
            if hasattr(response_data, '__dict__'):
                logger.debug(f"Dict de response_data: {response_data.__dict__}")
            
            # Intentar obtener el modelo desde la configuración como fallback
            default_model = LLM_CONFIG.get('default_model', 'unknown')
            
            # Inicializar métricas por defecto
            llm_metrics = {
                'timestamp': call_timestamp,
                'question_id': self.question_id or 'unknown',
                'node_name': node_name,
                'call_order': call_order,
                'model': default_model,  # Usar modelo de configuración como fallback
                'prompt_length': len(prompt_text) if prompt_text else 0,
                'response_length': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'duration_ms': 0,
                'load_duration_ms': 0,
                'prompt_eval_duration_ms': 0,
                'eval_duration_ms': 0,
                'eval_count': 0,
                'run_id': '',
                'success': success
            }
            
            # Extraer métricas del response_data
            if hasattr(response_data, 'response_metadata'):
                metadata = response_data.response_metadata
                logger.debug(f"response_metadata encontrado: {metadata}")
                logger.debug(f"Tipo de metadata: {type(metadata)}")
                logger.debug(f"Claves en metadata: {list(metadata.keys()) if isinstance(metadata, dict) else 'No es dict'}")
                
                # Extraer información básica
                if isinstance(metadata, dict):
                    llm_metrics['model'] = metadata.get('model', default_model)
                    logger.debug(f"Modelo extraído: {llm_metrics['model']}")
                    
                    llm_metrics['run_id'] = getattr(response_data, 'id', '').replace('run-', '') if hasattr(response_data, 'id') else ''
                    
                    # Extraer contenido de respuesta
                    if hasattr(response_data, 'content'):
                        llm_metrics['response_length'] = len(str(response_data.content))
                        logger.debug(f"Longitud de respuesta: {llm_metrics['response_length']}")
                    
                    # Extraer métricas de tiempo (en nanosegundos, convertir a ms)
                    if 'total_duration' in metadata:
                        llm_metrics['duration_ms'] = round(metadata['total_duration'] / 1_000_000, 2)
                        logger.debug(f"Duration extraído: {llm_metrics['duration_ms']}ms")
                    if 'load_duration' in metadata:
                        llm_metrics['load_duration_ms'] = round(metadata['load_duration'] / 1_000_000, 2)
                    if 'prompt_eval_duration' in metadata:
                        llm_metrics['prompt_eval_duration_ms'] = round(metadata['prompt_eval_duration'] / 1_000_000, 2)
                    if 'eval_duration' in metadata:
                        llm_metrics['eval_duration_ms'] = round(metadata['eval_duration'] / 1_000_000, 2)
                    
                    # Extraer información de tokens
                    llm_metrics['eval_count'] = metadata.get('eval_count', 0)
                    logger.debug(f"eval_count: {llm_metrics['eval_count']}")
                    
                    # Para algunos modelos, eval_count puede ser usado como output_tokens
                    if 'eval_count' in metadata and llm_metrics['eval_count'] > 0:
                        llm_metrics['output_tokens'] = llm_metrics['eval_count']
                    
                    # Buscar usage_metadata si está disponible
                    if 'usage_metadata' in metadata:
                        usage = metadata['usage_metadata']
                        logger.debug(f"usage_metadata encontrado: {usage}")
                        llm_metrics['input_tokens'] = usage.get('input_tokens', 0)
                        llm_metrics['output_tokens'] = usage.get('output_tokens', llm_metrics['output_tokens'])
                        llm_metrics['total_tokens'] = usage.get('total_tokens', 0)
                        logger.debug(f"Tokens extraídos - input: {llm_metrics['input_tokens']}, output: {llm_metrics['output_tokens']}, total: {llm_metrics['total_tokens']}")
                    
                    # Calcular total_tokens si no está disponible
                    if llm_metrics['total_tokens'] == 0:
                        llm_metrics['total_tokens'] = llm_metrics['input_tokens'] + llm_metrics['output_tokens']
                        logger.debug(f"Total tokens calculado: {llm_metrics['total_tokens']}")
                
            elif isinstance(response_data, dict):
                logger.debug(f"response_data es dict: {response_data}")
                if 'response_metadata' in response_data:
                    # Manejar caso donde response_data es un diccionario
                    metadata = response_data['response_metadata']
                    logger.debug(f"metadata desde dict: {metadata}")
                    extracted_metrics = self._extract_metadata_from_dict(metadata)
                    llm_metrics.update(extracted_metrics)
                    logger.debug(f"Métricas extraídas de dict: {extracted_metrics}")
                else:
                    logger.debug("response_data es dict pero no tiene 'response_metadata'")
                    # Revisar si hay contenido directo
                    if 'content' in response_data:
                        llm_metrics['response_length'] = len(str(response_data['content']))
                    # Intentar buscar directamente en el diccionario
                    if 'model' in response_data:
                        llm_metrics['model'] = response_data['model']
            else:
                logger.debug(f"response_data no tiene response_metadata ni es dict")
                # Intentar extraer contenido si es string o tiene contenido
                if isinstance(response_data, str):
                    llm_metrics['response_length'] = len(response_data)
                elif hasattr(response_data, 'content'):
                    llm_metrics['response_length'] = len(str(response_data.content))
                
            logger.debug(f"Métricas finales extraídas: modelo={llm_metrics['model']}, tokens={llm_metrics['total_tokens']}, duration={llm_metrics['duration_ms']}ms")
                
            # Almacenar llamada LLM
            with self._lock:
                self.llm_calls.append(llm_metrics)
                
                # Actualizar métricas del workflow
                if self.workflow_data:
                    self.workflow_data['total_llm_calls'] += 1
                    self.workflow_data['total_llm_time_ms'] += llm_metrics['duration_ms']
                    self.workflow_data['total_input_tokens'] += llm_metrics['input_tokens']
                    self.workflow_data['total_output_tokens'] += llm_metrics['output_tokens']
                    self.workflow_data['total_tokens'] += llm_metrics['total_tokens']
            
            # Escribir métricas LLM inmediatamente
            current_strategy = self._get_current_strategy_dir()
            self._write_llm_metrics(llm_metrics, current_strategy)
            
            logger.debug(f"Llamada LLM registrada para nodo {node_name}: {llm_metrics['duration_ms']:.2f}ms, tokens: {llm_metrics['total_tokens']}")
            
        except Exception as e:
            logger.error(f"Error al registrar llamada LLM en nodo {node_name}: {str(e)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
    
    def _extract_metadata_from_dict(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae métricas de un diccionario de metadatos."""
        metrics = {}
        
        # Usar modelo de configuración como fallback
        default_model = LLM_CONFIG.get('default_model', 'unknown')
        metrics['model'] = metadata.get('model', default_model)
        
        logger.debug(f"Extrayendo metadata de dict: {metadata}")
        logger.debug(f"Modelo extraído: {metrics['model']}")
        
        # Tiempos en nanosegundos -> milisegundos
        if 'total_duration' in metadata:
            metrics['duration_ms'] = round(metadata['total_duration'] / 1_000_000, 2)
            logger.debug(f"Duration desde dict: {metrics['duration_ms']}ms")
        if 'load_duration' in metadata:
            metrics['load_duration_ms'] = round(metadata['load_duration'] / 1_000_000, 2)
        if 'prompt_eval_duration' in metadata:
            metrics['prompt_eval_duration_ms'] = round(metadata['prompt_eval_duration'] / 1_000_000, 2)
        if 'eval_duration' in metadata:
            metrics['eval_duration_ms'] = round(metadata['eval_duration'] / 1_000_000, 2)
            
        metrics['eval_count'] = metadata.get('eval_count', 0)
        logger.debug(f"eval_count desde dict: {metrics['eval_count']}")
        
        # Buscar información de tokens
        if 'usage_metadata' in metadata:
            usage = metadata['usage_metadata']
            logger.debug(f"usage_metadata desde dict: {usage}")
            metrics['input_tokens'] = usage.get('input_tokens', 0)
            metrics['output_tokens'] = usage.get('output_tokens', 0)
            metrics['total_tokens'] = usage.get('total_tokens', 0)
            logger.debug(f"Tokens desde dict - input: {metrics['input_tokens']}, output: {metrics['output_tokens']}, total: {metrics['total_tokens']}")
        
        return metrics
    
    def _get_current_strategy_dir(self) -> str:
        """Obtiene el directorio de estrategia actual basado en el estado del workflow."""
        if not self.workflow_data:
            return "512"  # Por defecto
            
        is_adaptive = self.workflow_data.get('is_adaptive_strategy', False)
        current_strategy = self.workflow_data.get('final_chunk_strategy', '512')
        
        if is_adaptive and not current_strategy.startswith('E'):
            return f"E{current_strategy}"
        else:
            return current_strategy
    
    def start_node(self, node_name: str) -> Dict[str, Any]:
        """
        Inicia la medición de un nodo.
        
        Args:
            node_name: Nombre del nodo que se está ejecutando
            
        Returns:
            Dict con información de contexto para finalizar la medición
        """
        return {
            'node_name': node_name,
            'start_time': time.time(),
            'timestamp': time.time()
        }
    
    def end_node(self, node_context: Dict[str, Any], state: Dict[str, Any], success: bool = True):
        """
        Finaliza la medición de un nodo y registra las métricas.
        
        Args:
            node_context: Contexto devuelto por start_node
            state: Estado actual del workflow
            success: Indica si el nodo se ejecutó correctamente
        """
        try:
            end_time = time.time()
            execution_time_ms = (end_time - node_context['start_time']) * 1000
            
            # Extraer métricas del estado
            context_size_chars = 0
            context_size_tokens = 0
            documents_count = 0
            
            # Calcular tamaño del contexto
            documents = state.get('documents', [])
            if documents:
                documents_count = len(documents)
                total_content = ""
                for doc in documents:
                    if isinstance(doc, str):
                        total_content += doc
                    elif hasattr(doc, 'page_content'):
                        total_content += doc.page_content
                    else:
                        total_content += str(doc)
                
                context_size_chars = len(total_content)
                # Estimación simple de tokens (aproximadamente 4 caracteres por token)
                context_size_tokens = context_size_chars // 4
            
            retry_attempt = state.get('retry_count', 0)
            chunk_strategy = state.get('chunk_strategy', '512')
            
            # Actualizar datos del workflow
            with self._lock:
                if self.workflow_data:
                    self.workflow_data['total_retries'] = max(self.workflow_data['total_retries'], retry_attempt)
                    self.workflow_data['final_chunk_strategy'] = chunk_strategy
                    self.workflow_data['total_documents_retrieved'] = max(
                        self.workflow_data['total_documents_retrieved'], documents_count
                    )
                    self.workflow_data['final_context_size_chars'] = max(
                        self.workflow_data['final_context_size_chars'], context_size_chars
                    )
                    
                    # Rastrear chunks usados en estrategia adaptativa
                    if self.workflow_data.get('is_adaptive_strategy', False):
                        adaptive_chunks = self.workflow_data.get('adaptive_chunks_used', [])
                        if chunk_strategy not in adaptive_chunks:
                            adaptive_chunks.append(chunk_strategy)
                            self.workflow_data['adaptive_chunks_used'] = adaptive_chunks
                    
                    # Actualizar pregunta reescrita si está disponible
                    if state.get('rewritten_question') and not self.workflow_data['rewritten_question']:
                        self.workflow_data['rewritten_question'] = state.get('rewritten_question')
                    
                    # Actualizar métricas de evaluación si están disponibles
                    if state.get('evaluation_metrics'):
                        self.workflow_data['evaluation_metrics'] = state.get('evaluation_metrics')
            
            # Crear registro de métricas del nodo
            node_metrics = {
                'timestamp': node_context['timestamp'],
                'question_id': self.question_id or 'unknown',
                'node_name': node_context['node_name'],
                'execution_time_ms': round(execution_time_ms, 2),
                'context_size_chars': context_size_chars,
                'context_size_tokens': context_size_tokens,
                'documents_count': documents_count,
                'retry_attempt': retry_attempt,
                'success': success
            }
            
            # Escribir métricas del nodo inmediatamente
            strategy_dir = self._get_current_strategy_dir()
            self._write_node_metrics(node_metrics, strategy_dir)
            
            logger.debug(f"Métricas registradas para nodo {node_context['node_name']}: {execution_time_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error al registrar métricas del nodo {node_context.get('node_name', 'unknown')}: {str(e)}")
    
    def end_workflow(self, final_state: Dict[str, Any], success: bool = True):
        """
        Finaliza la recopilación de métricas del workflow y escribe el resumen final.
        
        Args:
            final_state: Estado final del workflow
            success: Indica si el workflow terminó exitosamente
        """
        if not self.workflow_start_time or not self.workflow_data:
            logger.warning("No se puede finalizar workflow - no se había iniciado correctamente")
            return
        
        try:
            end_time = time.time()
            total_execution_time_ms = (end_time - self.workflow_start_time) * 1000
            
            # Actualizar datos finales del workflow
            with self._lock:
                self.workflow_data.update({
                    'total_execution_time_ms': round(total_execution_time_ms, 2),
                    'success': success
                })
                
                # Actualizar con datos finales del estado
                if final_state.get('rewritten_question'):
                    self.workflow_data['rewritten_question'] = final_state['rewritten_question']
                
                if final_state.get('evaluation_metrics'):
                    self.workflow_data['evaluation_metrics'] = final_state['evaluation_metrics']
                
                # Calcular contexto final si no se había calculado
                if self.workflow_data['final_context_size_chars'] == 0:
                    documents = final_state.get('documents', [])
                    if documents:
                        total_content = ""
                        for doc in documents:
                            if isinstance(doc, str):
                                total_content += doc
                            elif hasattr(doc, 'page_content'):
                                total_content += doc.page_content
                            else:
                                total_content += str(doc)
                        self.workflow_data['final_context_size_chars'] = len(total_content)
                        self.workflow_data['total_documents_retrieved'] = len(documents)
            
            # Escribir métricas finales del workflow
            strategy_dir = self._get_current_strategy_dir()
            self._write_workflow_metrics(strategy_dir)
            
            logger.info(f"Workflow {self.question_id} finalizado en {total_execution_time_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error al finalizar métricas del workflow: {str(e)}")
        finally:
            # Limpiar datos del workflow actual
            with self._lock:
                self.question_id = None
                self.workflow_start_time = None
                self.workflow_data = {}
                self.node_executions = []
                self.llm_calls = []
    
    def _write_node_metrics(self, metrics: Dict[str, Any], chunk_strategy: str):
        """
        Escribe las métricas de un nodo al archivo CSV correspondiente.
        
        Args:
            metrics: Métricas del nodo
            chunk_strategy: Estrategia de chunking actual
        """
        try:
            strategy_dir = self.base_metrics_dir / chunk_strategy
            node_metrics_file = strategy_dir / 'node_metrics.csv'
            
            with open(node_metrics_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.node_metrics_headers)
                writer.writerow(metrics)
                
        except Exception as e:
            logger.error(f"Error al escribir métricas de nodo: {str(e)}")
    
    def _write_llm_metrics(self, metrics: Dict[str, Any], chunk_strategy: str):
        """
        Escribe las métricas de una llamada LLM al archivo CSV correspondiente.
        
        Args:
            metrics: Métricas de la llamada LLM
            chunk_strategy: Estrategia de chunking actual
        """
        try:
            strategy_dir = self.base_metrics_dir / chunk_strategy
            llm_metrics_file = strategy_dir / 'llm_metrics.csv'
            
            with open(llm_metrics_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.llm_metrics_headers)
                writer.writerow(metrics)
                
        except Exception as e:
            logger.error(f"Error al escribir métricas LLM: {str(e)}")
    
    def _write_workflow_metrics(self, chunk_strategy: str):
        """
        Escribe las métricas del workflow completo al archivo CSV correspondiente.
        
        Args:
            chunk_strategy: Estrategia de chunking final
        """
        try:
            strategy_dir = self.base_metrics_dir / chunk_strategy
            workflow_metrics_file = strategy_dir / 'workflow_metrics.csv'
            
            # Preparar los datos para escribir
            workflow_row = {
                'timestamp': self.workflow_start_time,
                'question_id': self.workflow_data['question_id'],
                'question': self.workflow_data['question'],
                'rewritten_question': self.workflow_data['rewritten_question'],
                'total_execution_time_ms': self.workflow_data['total_execution_time_ms'],
                'total_retries': self.workflow_data['total_retries'],
                'initial_chunk_strategy': self.workflow_data['initial_chunk_strategy'],
                'final_chunk_strategy': self.workflow_data['final_chunk_strategy'],
                'is_adaptive_strategy': self.workflow_data['is_adaptive_strategy'],
                'adaptive_chunks_used': json.dumps(self.workflow_data['adaptive_chunks_used']) if self.workflow_data['adaptive_chunks_used'] else '[]',
                'total_documents_retrieved': self.workflow_data['total_documents_retrieved'],
                'final_context_size_chars': self.workflow_data['final_context_size_chars'],
                'total_llm_calls': self.workflow_data['total_llm_calls'],
                'total_llm_time_ms': self.workflow_data['total_llm_time_ms'],
                'total_input_tokens': self.workflow_data['total_input_tokens'],
                'total_output_tokens': self.workflow_data['total_output_tokens'],
                'total_tokens': self.workflow_data['total_tokens'],
                'evaluation_metrics': json.dumps(self.workflow_data['evaluation_metrics'], ensure_ascii=False) if self.workflow_data['evaluation_metrics'] else '{}',
                'success': self.workflow_data['success']
            }
            
            with open(workflow_metrics_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.workflow_metrics_headers)
                writer.writerow(workflow_row)
                
        except Exception as e:
            logger.error(f"Error al escribir métricas de workflow: {str(e)}")
    
    def get_current_question_id(self) -> Optional[str]:
        """
        Retorna el ID de la pregunta actual.
        
        Returns:
            ID de la pregunta actual o None si no hay workflow activo
        """
        return self.question_id

    def get_llm_call_count(self) -> int:
        """
        Retorna el número total de llamadas LLM en el workflow actual.
        
        Returns:
            Número de llamadas LLM realizadas
        """
        return len(self.llm_calls)
    
    def get_total_llm_tokens(self) -> Dict[str, int]:
        """
        Retorna el total de tokens utilizados en llamadas LLM.
        
        Returns:
            Diccionario con totales de tokens (input, output, total)
        """
        if not self.workflow_data:
            return {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
            
        return {
            'input_tokens': self.workflow_data.get('total_input_tokens', 0),
            'output_tokens': self.workflow_data.get('total_output_tokens', 0),
            'total_tokens': self.workflow_data.get('total_tokens', 0)
        } 