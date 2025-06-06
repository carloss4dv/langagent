"""
Recolector de métricas para el workflow de LangGraph.

Este módulo implementa la recopilación de métricas detalladas por nodo y workflow,
organizadas por estrategia de chunking para análisis de rendimiento.
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

logger = get_logger(__name__)

class MetricsCollector:
    """
    Recolector de métricas para el workflow de LangGraph.
    
    Recopila métricas por nodo y por workflow completo, organizándolas
    por estrategia de chunking para análisis comparativo de rendimiento.
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
            'total_execution_time_ms', 'total_retries', 'final_chunk_strategy',
            'total_documents_retrieved', 'final_context_size_chars',
            'evaluation_metrics', 'success'
        ]
        
        # Crear directorios base
        self._ensure_directories()
        
        logger.info(f"MetricsCollector inicializado con directorio base: {self.base_metrics_dir}")
    
    def _ensure_directories(self):
        """Crea los directorios necesarios para las métricas."""
        strategies = ['256', '512', '1024']
        
        for strategy in strategies:
            strategy_dir = self.base_metrics_dir / strategy
            strategy_dir.mkdir(parents=True, exist_ok=True)
            
            # Crear archivos CSV con headers si no existen
            node_metrics_file = strategy_dir / 'node_metrics.csv'
            workflow_metrics_file = strategy_dir / 'workflow_metrics.csv'
            
            if not node_metrics_file.exists():
                with open(node_metrics_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.node_metrics_headers)
            
            if not workflow_metrics_file.exists():
                with open(workflow_metrics_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.workflow_metrics_headers)
    
    def start_workflow(self, question: str, chunk_strategy: str = "512"):
        """
        Inicia la recopilación de métricas para un nuevo workflow.
        
        Args:
            question: Pregunta original del usuario
            chunk_strategy: Estrategia de chunking inicial
        """
        with self._lock:
            self.question_id = str(uuid.uuid4())
            self.workflow_start_time = time.time()
            self.node_executions = []
            
            self.workflow_data = {
                'question_id': self.question_id,
                'question': question,
                'rewritten_question': '',
                'initial_chunk_strategy': chunk_strategy,
                'final_chunk_strategy': chunk_strategy,
                'total_retries': 0,
                'total_documents_retrieved': 0,
                'final_context_size_chars': 0,
                'evaluation_metrics': {},
                'success': False
            }
            
        logger.info(f"Iniciado workflow con ID: {self.question_id}")
    
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
            self._write_node_metrics(node_metrics, chunk_strategy)
            
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
            chunk_strategy = final_state.get('chunk_strategy', self.workflow_data['final_chunk_strategy'])
            self._write_workflow_metrics(chunk_strategy)
            
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
                'final_chunk_strategy': self.workflow_data['final_chunk_strategy'],
                'total_documents_retrieved': self.workflow_data['total_documents_retrieved'],
                'final_context_size_chars': self.workflow_data['final_context_size_chars'],
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