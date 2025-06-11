"""
Recolector de métricas para el workflow de LangGraph.

Este módulo implementa la recopilación de métricas detalladas por nodo y workflow,
organizadas por estrategia de chunking para análisis de rendimiento.
Incluye captura de métricas LLM simplificadas enfocadas en tiempo y modelo.
"""

import os
import csv
import json
import time
import uuid
import psutil  # Para obtener información de memoria
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
    Incluye recolección simplificada de métricas de llamadas a LLM enfocada en tiempo y modelo.
    """
    
    # Mapeo de nodos a modelos basado en la configuración de LangAgent
    NODE_TO_MODEL_MAPPING = {
        'rewrite_query': 'default_model3',           # Modelo terciario para reescritura
        'grade_relevance': 'default_model2',         # Modelo secundario para evaluación de relevancia
        'generate': 'default_model',                 # Modelo principal para generación RAG/SQL
        'evaluate_response_granular': 'default_model3',  # Modelo terciario para evaluación granular
        'generate_sql_interpretation': 'default_model',  # Modelo principal para interpretación SQL
        # Agrega más mapeos según sea necesario
    }
    
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
        
        # Headers simplificados para los archivos CSV enfocados en tiempo y modelo
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
            'total_llm_calls', 'total_llm_time_ms', 'evaluation_metrics', 'success'
        ]
        
        # Headers simplificados para métricas de LLM enfocados en tiempo y modelo
        self.llm_metrics_headers = [
            'timestamp', 'question_id', 'node_name', 'call_order', 'model_name',
            'model_config_key', 'prompt_length', 'response_length', 'duration_ms', 
            'memory_mb', 'success'
        ]
        
        # Crear directorios base
        self._ensure_directories()
        
        logger.info(f"MetricsCollector inicializado con directorio base: {self.base_metrics_dir}")
        logger.info(f"Mapeo de modelos disponible: {self.get_model_mapping()}")
    
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
                'evaluation_metrics': {},
                'success': False
            }
            
        logger.info(f"Iniciado workflow con ID: {self.question_id}, estrategia: {display_strategy}")
    
    def log_llm_call(self, node_name: str, response_data: Any, prompt_text: str = "", success: bool = True):
        """
        Registra una llamada a LLM con métricas simplificadas enfocadas en tiempo y modelo.
        
        Args:
            node_name: Nombre del nodo que realizó la llamada
            response_data: Respuesta del LLM (AIMessageChunk o similar)
            prompt_text: Texto del prompt enviado
            success: Si la llamada fue exitosa
        """
        try:
            call_timestamp = time.time()
            call_order = len(self.llm_calls) + 1
            
            # Obtener el modelo correcto para este nodo desde la configuración
            model_name, config_key = self.get_model_for_node(node_name)
            
            logger.debug(f"=== LLM CALL - Nodo: {node_name} ===")
            logger.debug(f"Modelo asignado: {model_name} (config: {config_key})")
            logger.debug(f"Tipo de response_data: {type(response_data)}")
            
            # Inicializar métricas simplificadas
            llm_metrics = {
                'timestamp': call_timestamp,
                'question_id': self.question_id or 'unknown',
                'node_name': node_name,
                'call_order': call_order,
                'model_name': model_name,
                'model_config_key': config_key,
                'prompt_length': len(prompt_text) if prompt_text else 0,
                'response_length': 0,
                'duration_ms': 0,
                'memory_mb': self.get_memory_usage(),
                'success': success
            }
            
            # Extraer métricas básicas enfocadas en tiempo y contenido
            start_extraction = time.time()
            
            # Extraer contenido de respuesta
            if hasattr(response_data, 'content'):
                llm_metrics['response_length'] = len(str(response_data.content))
            elif isinstance(response_data, str):
                llm_metrics['response_length'] = len(response_data)
            elif isinstance(response_data, dict) and 'content' in response_data:
                llm_metrics['response_length'] = len(str(response_data['content']))
            
            # Extraer tiempo de duración si está disponible
            if hasattr(response_data, 'response_metadata'):
                metadata = response_data.response_metadata
                if isinstance(metadata, dict) and 'total_duration' in metadata:
                    llm_metrics['duration_ms'] = round(metadata['total_duration'] / 1_000_000, 2)
                    logger.debug(f"Duration extraído: {llm_metrics['duration_ms']}ms")
            elif isinstance(response_data, dict) and 'response_metadata' in response_data:
                metadata = response_data['response_metadata']
                if isinstance(metadata, dict) and 'total_duration' in metadata:
                    llm_metrics['duration_ms'] = round(metadata['total_duration'] / 1_000_000, 2)
            
            # Si no se pudo extraer duración, calcular tiempo de procesamiento de respuesta
            if llm_metrics['duration_ms'] == 0:
                processing_time = (time.time() - start_extraction) * 1000
                llm_metrics['duration_ms'] = round(processing_time, 2)
                logger.debug(f"Duration calculado por procesamiento: {llm_metrics['duration_ms']}ms")
                
            logger.debug(f"Métricas finales: modelo={llm_metrics['model_name']}, duration={llm_metrics['duration_ms']}ms, memory={llm_metrics['memory_mb']}MB")
                
            # Almacenar llamada LLM
            with self._lock:
                self.llm_calls.append(llm_metrics)
                
                # Actualizar métricas simplificadas del workflow
                if self.workflow_data:
                    self.workflow_data['total_llm_calls'] += 1
                    self.workflow_data['total_llm_time_ms'] += llm_metrics['duration_ms']
            
            # Escribir métricas LLM inmediatamente
            current_strategy = self._get_current_strategy_dir()
            self._write_llm_metrics(llm_metrics, current_strategy)
            
            logger.debug(f"Llamada LLM registrada para nodo {node_name}: {llm_metrics['duration_ms']:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error al registrar llamada LLM en nodo {node_name}: {str(e)}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
    
    def _extract_metadata_from_dict(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae métricas simplificadas de un diccionario de metadatos."""
        metrics = {}
        
        logger.debug(f"Extrayendo metadata de dict: {metadata}")
        
        # Tiempo de duración solamente (nanosegundos -> milisegundos)
        if 'total_duration' in metadata:
            metrics['duration_ms'] = round(metadata['total_duration'] / 1_000_000, 2)
            logger.debug(f"Duration desde dict: {metrics['duration_ms']}ms")
        
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
    
    def get_total_llm_time(self) -> float:
        """
        Retorna el tiempo total utilizado en llamadas LLM.
        
        Returns:
            Tiempo total en milisegundos
        """
        if not self.workflow_data:
            return 0.0
            
        return self.workflow_data.get('total_llm_time_ms', 0.0)

    def get_model_mapping(self) -> Dict[str, str]:
        """
        Obtiene el mapeo de nodos a nombres de modelo reales desde la configuración.
        
        Returns:
            Diccionario con mapeo de nodos a nombres de modelo
        """
        mapping = {}
        for node_name, config_key in self.NODE_TO_MODEL_MAPPING.items():
            model_name = LLM_CONFIG.get(config_key, 'unknown')
            mapping[node_name] = model_name
        return mapping
    
    def get_model_for_node(self, node_name: str) -> tuple[str, str]:
        """
        Obtiene el nombre del modelo y la clave de configuración para un nodo específico.
        
        Args:
            node_name: Nombre del nodo
            
        Returns:
            Tupla (nombre_modelo, clave_configuracion)
        """
        config_key = self.NODE_TO_MODEL_MAPPING.get(node_name, 'default_model')
        model_name = LLM_CONFIG.get(config_key, 'unknown')
        return model_name, config_key
    
    def get_memory_usage(self) -> float:
        """
        Obtiene el uso actual de memoria del proceso en MB.
        
        Returns:
            Uso de memoria en MB
        """
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return round(memory_info.rss / 1024 / 1024, 2)  # Convertir bytes a MB
        except Exception as e:
            logger.debug(f"No se pudo obtener información de memoria: {e}")
            return 0.0 