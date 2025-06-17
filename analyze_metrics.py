#!/usr/bin/env python3
"""
Script de análisis de métricas del workflow de LangGraph.

Analiza los archivos CSV generados por MetricsCollector y produce estadísticas
detalladas sobre el rendimiento del sistema por estrategia de chunking.

Uso:
    python analyze_metrics.py [--metrics-dir metrics] [--output-format table|json|csv]
"""

import os
import csv
import json
import argparse
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import sys

def get_strategy_directories(metrics_dir: Path) -> List[str]:
    """
    Detecta dinámicamente los directorios de estrategias disponibles.
    
    Args:
        metrics_dir: Directorio base de métricas
        
    Returns:
        Lista de nombres de directorios de estrategias encontrados
    """
    if not metrics_dir.exists():
        return []
    
    strategy_dirs = []
    for item in metrics_dir.iterdir():
        if item.is_dir():
            # Verificar que el directorio contiene archivos de métricas
            node_metrics = item / 'node_metrics.csv'
            workflow_metrics = item / 'workflow_metrics.csv'
            
            # Considerar como directorio de estrategia si tiene al menos uno de los archivos
            if node_metrics.exists() or workflow_metrics.exists():
                strategy_dirs.append(item.name)
    
    # Ordenar para consistencia en el output
    return sorted(strategy_dirs)

def load_csv_data(file_path: Path) -> List[Dict[str, Any]]:
    """
    Carga datos de un archivo CSV.
    
    Args:
        file_path: Ruta al archivo CSV
        
    Returns:
        Lista de diccionarios con los datos del CSV
    """
    if not file_path.exists():
        return []
    
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    except Exception as e:
        print(f"Error al leer {file_path}: {e}")
        return []
    
    return data

def convert_numeric_fields(data: List[Dict[str, Any]], numeric_fields: List[str]) -> List[Dict[str, Any]]:
    """
    Convierte campos específicos a numéricos.
    
    Args:
        data: Lista de diccionarios con datos
        numeric_fields: Lista de campos a convertir a numéricos
        
    Returns:
        Lista con campos numéricos convertidos
    """
    converted_data = []
    for row in data:
        converted_row = row.copy()
        for field in numeric_fields:
            if field in converted_row and converted_row[field]:
                try:
                    converted_row[field] = float(converted_row[field])
                except (ValueError, TypeError):
                    converted_row[field] = 0.0
        converted_data.append(converted_row)
    return converted_data

def analyze_node_metrics(metrics_dir: Path) -> Dict[str, Any]:
    """
    Analiza las métricas por nodo de todas las estrategias.
    
    Args:
        metrics_dir: Directorio base de métricas
        
    Returns:
        Diccionario con análisis por estrategia y nodo
    """
    strategies = get_strategy_directories(metrics_dir)
    if not strategies:
        print(f"⚠️  No se encontraron directorios de estrategias en {metrics_dir}")
        return {'by_strategy': {}, 'by_node': {}, 'global_stats': {}}
    
    print(f"📁 Estrategias detectadas: {', '.join(strategies)}")
    
    analysis = {
        'by_strategy': {},
        'by_node': {},
        'global_stats': {}
    }
    
    all_node_data = []
    
    for strategy in strategies:
        strategy_dir = metrics_dir / strategy
        node_file = strategy_dir / 'node_metrics.csv'
        
        if not node_file.exists():
            print(f"⚠️  Archivo no encontrado: {node_file}")
            continue
        
        print(f"📊 Analizando métricas de nodos para estrategia {strategy}...")
        
        # Cargar datos
        data = load_csv_data(node_file)
        if not data:
            continue
        
        # Convertir campos numéricos
        numeric_fields = ['execution_time_ms', 'context_size_chars', 'context_size_tokens', 
                         'documents_count', 'retry_attempt']
        data = convert_numeric_fields(data, numeric_fields)
        
        all_node_data.extend([(strategy, row) for row in data])
        
        # Análisis por estrategia
        strategy_stats = {
            'total_executions': len(data),
            'success_rate': sum(1 for row in data if row.get('success', '').lower() == 'true') / len(data) if data else 0,
            'avg_execution_time_ms': statistics.mean([row['execution_time_ms'] for row in data]) if data else 0,
            'median_execution_time_ms': statistics.median([row['execution_time_ms'] for row in data]) if data else 0,
            'avg_context_size_chars': statistics.mean([row['context_size_chars'] for row in data]) if data else 0,
            'avg_documents_count': statistics.mean([row['documents_count'] for row in data]) if data else 0,
            'by_node': {}
        }
        
        # Análisis por nodo dentro de la estrategia
        nodes_in_strategy = defaultdict(list)
        for row in data:
            nodes_in_strategy[row['node_name']].append(row)
        
        for node_name, node_data in nodes_in_strategy.items():
            strategy_stats['by_node'][node_name] = {
                'executions': len(node_data),
                'success_rate': sum(1 for row in node_data if row.get('success', '').lower() == 'true') / len(node_data),
                'avg_execution_time_ms': statistics.mean([row['execution_time_ms'] for row in node_data]),
                'min_execution_time_ms': min([row['execution_time_ms'] for row in node_data]),
                'max_execution_time_ms': max([row['execution_time_ms'] for row in node_data]),
                'avg_context_size_chars': statistics.mean([row['context_size_chars'] for row in node_data]) if node_data[0]['context_size_chars'] > 0 else 0,
                'avg_documents_count': statistics.mean([row['documents_count'] for row in node_data]) if node_data[0]['documents_count'] > 0 else 0
            }
        
        analysis['by_strategy'][strategy] = strategy_stats
    
    # Análisis global por nodo (across strategies)
    global_nodes = defaultdict(list)
    for strategy, row in all_node_data:
        global_nodes[row['node_name']].append((strategy, row))
    
    for node_name, node_data in global_nodes.items():
        times_by_strategy = defaultdict(list)
        for strategy, row in node_data:
            times_by_strategy[strategy].append(row['execution_time_ms'])
        
        analysis['by_node'][node_name] = {
            'total_executions': len(node_data),
            'by_strategy': {}
        }
        
        for strategy, times in times_by_strategy.items():
            analysis['by_node'][node_name]['by_strategy'][strategy] = {
                'executions': len(times),
                'avg_time_ms': statistics.mean(times),
                'median_time_ms': statistics.median(times),
                'min_time_ms': min(times),
                'max_time_ms': max(times)
            }
    
    # Estadísticas globales
    if all_node_data:
        all_times = [row['execution_time_ms'] for _, row in all_node_data]
        analysis['global_stats'] = {
            'total_node_executions': len(all_node_data),
            'overall_avg_time_ms': statistics.mean(all_times),
            'overall_median_time_ms': statistics.median(all_times),
            'fastest_execution_ms': min(all_times),
            'slowest_execution_ms': max(all_times)
        }
    
    return analysis

def analyze_workflow_metrics(metrics_dir: Path) -> Dict[str, Any]:
    """
    Analiza las métricas completas de workflow.
    
    Args:
        metrics_dir: Directorio base de métricas
        
    Returns:
        Diccionario con análisis de workflows
    """
    strategies = get_strategy_directories(metrics_dir)
    if not strategies:
        print(f"⚠️  No se encontraron directorios de estrategias en {metrics_dir}")
        return {'by_strategy': {}, 'comparison': {}, 'evaluation_metrics': {}}
    
    analysis = {
        'by_strategy': {},
        'comparison': {},
        'evaluation_metrics': {}
    }
    
    all_workflow_data = []
    
    for strategy in strategies:
        strategy_dir = metrics_dir / strategy
        workflow_file = strategy_dir / 'workflow_metrics.csv'
        
        if not workflow_file.exists():
            print(f"⚠️  Archivo no encontrado: {workflow_file}")
            continue
        
        print(f"📈 Analizando métricas de workflow para estrategia {strategy}...")
        
        # Cargar datos
        data = load_csv_data(workflow_file)
        if not data:
            continue
        
        # Convertir campos numéricos
        numeric_fields = ['total_execution_time_ms', 'total_retries', 'total_documents_retrieved', 
                         'final_context_size_chars']
        data = convert_numeric_fields(data, numeric_fields)
        
        all_workflow_data.extend([(strategy, row) for row in data])
        
        # Análisis por estrategia
        strategy_stats = {
            'total_workflows': len(data),
            'success_rate': sum(1 for row in data if row.get('success', '').lower() == 'true') / len(data) if data else 0,
            'avg_execution_time_ms': statistics.mean([row['total_execution_time_ms'] for row in data]) if data else 0,
            'median_execution_time_ms': statistics.median([row['total_execution_time_ms'] for row in data]) if data else 0,
            'avg_retries': statistics.mean([row['total_retries'] for row in data]) if data else 0,
            'avg_documents_retrieved': statistics.mean([row['total_documents_retrieved'] for row in data]) if data else 0,
            'avg_context_size_chars': statistics.mean([row['final_context_size_chars'] for row in data]) if data else 0,
            'fastest_workflow_ms': min([row['total_execution_time_ms'] for row in data]) if data else 0,
            'slowest_workflow_ms': max([row['total_execution_time_ms'] for row in data]) if data else 0
        }
        
        # Analizar métricas de evaluación
        evaluation_metrics = []
        for row in data:
            if row.get('evaluation_metrics'):
                try:
                    metrics = json.loads(row['evaluation_metrics'])
                    evaluation_metrics.append(metrics)
                except (json.JSONDecodeError, TypeError):
                    continue
        
        if evaluation_metrics:
            strategy_stats['evaluation_metrics'] = {
                'avg_faithfulness': statistics.mean([m.get('faithfulness', 0) for m in evaluation_metrics]),
                'avg_context_precision': statistics.mean([m.get('context_precision', 0) for m in evaluation_metrics]),
                'avg_context_recall': statistics.mean([m.get('context_recall', 0) for m in evaluation_metrics]),
                'avg_answer_relevance': statistics.mean([m.get('answer_relevance', 0) for m in evaluation_metrics]),
                'count': len(evaluation_metrics)
            }
        
        analysis['by_strategy'][strategy] = strategy_stats
    
    # Análisis comparativo entre estrategias
    if len(analysis['by_strategy']) > 1:
        strategies_with_data = list(analysis['by_strategy'].keys())
        
        # Comparar tiempos de ejecución
        times_comparison = {}
        for strategy in strategies_with_data:
            times_comparison[strategy] = analysis['by_strategy'][strategy]['avg_execution_time_ms']
        
        fastest_strategy = min(times_comparison.items(), key=lambda x: x[1])
        slowest_strategy = max(times_comparison.items(), key=lambda x: x[1])
        
        analysis['comparison'] = {
            'fastest_strategy': {
                'strategy': fastest_strategy[0],
                'avg_time_ms': fastest_strategy[1]
            },
            'slowest_strategy': {
                'strategy': slowest_strategy[0],
                'avg_time_ms': slowest_strategy[1]
            },
            'time_differences': times_comparison
        }
        
        # Comparar métricas de evaluación si existen
        eval_comparison = {}
        for strategy in strategies_with_data:
            strategy_data = analysis['by_strategy'][strategy]
            if 'evaluation_metrics' in strategy_data:
                eval_comparison[strategy] = strategy_data['evaluation_metrics']
        
        if eval_comparison:
            analysis['evaluation_metrics'] = eval_comparison
    
    return analysis

def analyze_llm_metrics(metrics_dir: Path) -> Dict[str, Any]:
    """
    Analiza las métricas de llamadas a LLMs de todas las estrategias.
    
    Args:
        metrics_dir: Directorio base de métricas
        
    Returns:
        Diccionario con análisis de llamadas LLM por estrategia
    """
    strategies = get_strategy_directories(metrics_dir)
    if not strategies:
        print(f"⚠️  No se encontraron directorios de estrategias en {metrics_dir}")
        return {'by_strategy': {}, 'by_model': {}, 'global_stats': {}}
    
    analysis = {
        'by_strategy': {},
        'by_model': {},
        'global_stats': {}
    }
    
    all_llm_data = []
    
    for strategy in strategies:
        strategy_dir = metrics_dir / strategy
        llm_file = strategy_dir / 'llm_metrics.csv'
        
        if not llm_file.exists():
            print(f"⚠️  Archivo LLM no encontrado: {llm_file}")
            continue
        
        print(f"🤖 Analizando métricas de LLM para estrategia {strategy}...")
        
        # Cargar datos
        data = load_csv_data(llm_file)
        if not data:
            continue
        
        # Convertir campos numéricos (basados en los headers reales del metrics_collector)
        numeric_fields = ['duration_ms', 'prompt_length', 'response_length', 'memory_mb', 'call_order']
        data = convert_numeric_fields(data, numeric_fields)
        
        all_llm_data.extend([(strategy, row) for row in data])
        
        # Análisis por estrategia (usando campos reales del metrics_collector)
        durations = [row['duration_ms'] for row in data if row['duration_ms'] > 0]
        prompt_lengths = [row['prompt_length'] for row in data if row['prompt_length'] > 0]
        response_lengths = [row['response_length'] for row in data if row['response_length'] > 0]
        
        strategy_stats = {
            'total_calls': len(data),
            'success_rate': sum(1 for row in data if row.get('success', '').lower() == 'true') / len(data) if data else 0,
            'avg_duration_ms': statistics.mean(durations) if durations else 0,
            'median_duration_ms': statistics.median(durations) if durations else 0,
            'min_duration_ms': min(durations) if durations else 0,
            'max_duration_ms': max(durations) if durations else 0,
            'avg_prompt_length': statistics.mean(prompt_lengths) if prompt_lengths else 0,
            'avg_response_length': statistics.mean(response_lengths) if response_lengths else 0,
            'total_prompt_chars': sum(prompt_lengths) if prompt_lengths else 0,
            'total_response_chars': sum(response_lengths) if response_lengths else 0,
            'by_model': {},
            'by_operation': {}
        }
        
        # Análisis por modelo dentro de la estrategia
        models_in_strategy = defaultdict(list)
        for row in data:
            if row.get('model_name'):
                models_in_strategy[row['model_name']].append(row)
        
        for model_name, model_data in models_in_strategy.items():
            model_durations = [row['duration_ms'] for row in model_data if row['duration_ms'] > 0]
            model_prompt_lengths = [row['prompt_length'] for row in model_data if row['prompt_length'] > 0]
            model_response_lengths = [row['response_length'] for row in model_data if row['response_length'] > 0]
            
            strategy_stats['by_model'][model_name] = {
                'calls': len(model_data),
                'success_rate': sum(1 for row in model_data if row.get('success', '').lower() == 'true') / len(model_data),
                'avg_duration_ms': statistics.mean(model_durations) if model_durations else 0,
                'avg_prompt_length': statistics.mean(model_prompt_lengths) if model_prompt_lengths else 0,
                'avg_response_length': statistics.mean(model_response_lengths) if model_response_lengths else 0
            }
        
        # Análisis por operación (si existe el campo)
        operations_in_strategy = defaultdict(list)
        for row in data:
            if row.get('operation') or row.get('node_name'):
                operation = row.get('operation', row.get('node_name', 'unknown'))
                operations_in_strategy[operation].append(row)
        
        for operation_name, operation_data in operations_in_strategy.items():
            op_durations = [row['duration_ms'] for row in operation_data if row['duration_ms'] > 0]
            op_prompt_lengths = [row['prompt_length'] for row in operation_data if row['prompt_length'] > 0]
            
            strategy_stats['by_operation'][operation_name] = {
                'calls': len(operation_data),
                'avg_duration_ms': statistics.mean(op_durations) if op_durations else 0,
                'avg_prompt_length': statistics.mean(op_prompt_lengths) if op_prompt_lengths else 0
            }
        
        analysis['by_strategy'][strategy] = strategy_stats
    
    # Análisis global por modelo (across strategies)
    global_models = defaultdict(list)
    for strategy, row in all_llm_data:
        if row.get('model_name'):
            global_models[row['model_name']].append((strategy, row))
    
    for model_name, model_data in global_models.items():
        durations_by_strategy = defaultdict(list)
        prompt_lengths_by_strategy = defaultdict(list)
        response_lengths_by_strategy = defaultdict(list)
        
        for strategy, row in model_data:
            if row['duration_ms'] > 0:
                durations_by_strategy[strategy].append(row['duration_ms'])
            if row['prompt_length'] > 0:
                prompt_lengths_by_strategy[strategy].append(row['prompt_length'])
            if row['response_length'] > 0:
                response_lengths_by_strategy[strategy].append(row['response_length'])
        
        analysis['by_model'][model_name] = {
            'total_calls': len(model_data),
            'by_strategy': {}
        }
        
        for strategy in strategies:
            if strategy in durations_by_strategy or strategy in prompt_lengths_by_strategy:
                durations = durations_by_strategy.get(strategy, [])
                prompt_lengths = prompt_lengths_by_strategy.get(strategy, [])
                response_lengths = response_lengths_by_strategy.get(strategy, [])
                
                analysis['by_model'][model_name]['by_strategy'][strategy] = {
                    'calls': len([s for s, _ in model_data if s == strategy]),
                    'avg_duration_ms': statistics.mean(durations) if durations else 0,
                    'avg_prompt_length': statistics.mean(prompt_lengths) if prompt_lengths else 0,
                    'avg_response_length': statistics.mean(response_lengths) if response_lengths else 0
                }
    
    # Estadísticas globales
    if all_llm_data:
        all_durations = [row['duration_ms'] for _, row in all_llm_data if row['duration_ms'] > 0]
        all_prompt_lengths = [row['prompt_length'] for _, row in all_llm_data if row['prompt_length'] > 0]
        all_response_lengths = [row['response_length'] for _, row in all_llm_data if row['response_length'] > 0]
        
        analysis['global_stats'] = {
            'total_llm_calls': len(all_llm_data),
            'overall_avg_duration_ms': statistics.mean(all_durations) if all_durations else 0,
            'overall_median_duration_ms': statistics.median(all_durations) if all_durations else 0,
            'fastest_call_ms': min(all_durations) if all_durations else 0,
            'slowest_call_ms': max(all_durations) if all_durations else 0,
            'total_prompt_chars': sum(all_prompt_lengths) if all_prompt_lengths else 0,
            'total_response_chars': sum(all_response_lengths) if all_response_lengths else 0,
            'avg_prompt_length': statistics.mean(all_prompt_lengths) if all_prompt_lengths else 0,
            'avg_response_length': statistics.mean(all_response_lengths) if all_response_lengths else 0
        }
    
    return analysis

def print_table_report(node_analysis: Dict[str, Any], workflow_analysis: Dict[str, Any], llm_analysis: Dict[str, Any]):
    """
    Imprime un reporte en formato tabla legible.
    """
    print("\n" + "="*80)
    print(" 📊 REPORTE DE MÉTRICAS DEL WORKFLOW - ANÁLISIS COMPARATIVO")
    print("="*80)
    
    # Resumen por estrategia
    print("\n🎯 RESUMEN POR ESTRATEGIA DE CHUNKING")
    print("-" * 50)
    
    strategies = sorted(workflow_analysis['by_strategy'].keys())
    if strategies:
        print(f"{'Estrategia':<15} {'Workflows':<10} {'Éxito %':<10} {'Tiempo Prom (ms)':<18} {'Reintentos Prom':<15}")
        print("-" * 73)
        
        for strategy in strategies:
            data = workflow_analysis['by_strategy'][strategy]
            # Formatear el nombre de la estrategia para que se vea mejor
            strategy_name = f"{strategy}" if not strategy.isdigit() else f"{strategy} tokens"
            print(f"{strategy_name:<15} {data['total_workflows']:<10} "
                  f"{data['success_rate']*100:.1f}%{'':<6} {data['avg_execution_time_ms']:<18.2f} "
                  f"{data['avg_retries']:<15.2f}")
    
    # Comparación de velocidad
    if 'comparison' in workflow_analysis and workflow_analysis['comparison']:
        print(f"\n⚡ ANÁLISIS DE VELOCIDAD")
        print("-" * 30)
        comp = workflow_analysis['comparison']
        fastest_name = comp['fastest_strategy']['strategy'] if not comp['fastest_strategy']['strategy'].isdigit() else f"{comp['fastest_strategy']['strategy']} tokens"
        slowest_name = comp['slowest_strategy']['strategy'] if not comp['slowest_strategy']['strategy'].isdigit() else f"{comp['slowest_strategy']['strategy']} tokens"
        
        print(f"🥇 Estrategia más rápida: {fastest_name} "
              f"({comp['fastest_strategy']['avg_time_ms']:.2f} ms)")
        print(f"🐌 Estrategia más lenta: {slowest_name} "
              f"({comp['slowest_strategy']['avg_time_ms']:.2f} ms)")
        
        speedup = comp['slowest_strategy']['avg_time_ms'] / comp['fastest_strategy']['avg_time_ms']
        print(f"📈 Diferencia de velocidad: {speedup:.2f}x")
    
    # Métricas de evaluación
    if 'evaluation_metrics' in workflow_analysis and workflow_analysis['evaluation_metrics']:
        print(f"\n🎯 MÉTRICAS DE CALIDAD PROMEDIO")
        print("-" * 40)
        print(f"{'Estrategia':<15} {'Faithfulness':<13} {'Precision':<11} {'Recall':<9} {'Relevance':<10}")
        print("-" * 63)
        
        for strategy, metrics in workflow_analysis['evaluation_metrics'].items():
            strategy_name = f"{strategy}" if not strategy.isdigit() else f"{strategy} tokens"
            print(f"{strategy_name:<15} {metrics['avg_faithfulness']:<13.3f} "
                  f"{metrics['avg_context_precision']:<11.3f} {metrics['avg_context_recall']:<9.3f} "
                  f"{metrics['avg_answer_relevance']:<10.3f}")
    
    # Análisis por nodo
    print(f"\n⚙️  TIEMPO PROMEDIO POR NODO (ms)")
    print("-" * 50)
    
    if 'by_node' in node_analysis:
        node_names = ['retrieve', 'grade_relevance', 'generate', 'evaluate_response_granular', 
                     'execute_query', 'generate_sql_interpretation']
        
        # Header
        header = f"{'Nodo':<25}"
        for strategy in strategies:
            strategy_name = f"{strategy}" if not strategy.isdigit() else f"{strategy} tokens"
            header += f"{strategy_name:<15}"
        print(header)
        print("-" * (25 + 15 * len(strategies)))
        
        for node in node_names:
            if node in node_analysis['by_node']:
                row = f"{node:<25}"
                node_data = node_analysis['by_node'][node]
                for strategy in strategies:
                    if strategy in node_data['by_strategy']:
                        avg_time = node_data['by_strategy'][strategy]['avg_time_ms']
                        row += f"{avg_time:<15.2f}"
                    else:
                        row += f"{'N/A':<15}"
                print(row)
    
    # Métricas de LLM
    if 'by_strategy' in llm_analysis and llm_analysis['by_strategy']:
        print(f"\n🤖 MÉTRICAS DE LLAMADAS LLM")
        print("-" * 55)
        print(f"{'Estrategia':<15} {'Llamadas':<10} {'Éxito %':<10} {'Tiempo Prom (ms)':<18} {'Chars Prompt':<15}")
        print("-" * 73)
        
        strategies = sorted(llm_analysis['by_strategy'].keys())
        for strategy in strategies:
            data = llm_analysis['by_strategy'][strategy]
            strategy_name = f"{strategy}" if not strategy.isdigit() else f"{strategy} tokens"
            print(f"{strategy_name:<15} {data['total_calls']:<10} "
                  f"{data['success_rate']*100:.1f}%{'':<6} {data['avg_duration_ms']:<18.2f} "
                  f"{data['avg_prompt_length']:<15.0f}")
    
    # Análisis de tamaños de texto
    if 'by_strategy' in llm_analysis and llm_analysis['by_strategy']:
        print(f"\n📄 ANÁLISIS DE TAMAÑOS DE TEXTO")
        print("-" * 35)
        
        strategies = sorted(llm_analysis['by_strategy'].keys())
        for strategy in strategies:
            data = llm_analysis['by_strategy'][strategy]
            strategy_name = f"{strategy}" if not strategy.isdigit() else f"{strategy} tokens"
            print(f"📋 {strategy_name}:")
            print(f"   ├─ Prompt promedio: {data['avg_prompt_length']:,.0f} caracteres")
            print(f"   └─ Respuesta promedio: {data['avg_response_length']:,.0f} caracteres")
    
    # Análisis por modelo
    if 'by_model' in llm_analysis and llm_analysis['by_model']:
        print(f"\n🧠 RENDIMIENTO POR MODELO")
        print("-" * 40)
        print(f"{'Modelo':<25} {'Llamadas':<10} {'Tiempo Prom (ms)':<18} {'Chars Prompt':<15}")
        print("-" * 68)
        
        for model_name, model_data in llm_analysis['by_model'].items():
            total_calls = model_data['total_calls']
            # Calcular promedios across estrategias
            avg_duration = 0
            avg_prompt_length = 0
            strategy_count = 0
            
            for strategy, strategy_data in model_data['by_strategy'].items():
                if strategy_data['avg_duration_ms'] > 0:
                    avg_duration += strategy_data['avg_duration_ms']
                    strategy_count += 1
                if strategy_data['avg_prompt_length'] > 0:
                    avg_prompt_length += strategy_data['avg_prompt_length']
            
            avg_duration = avg_duration / strategy_count if strategy_count > 0 else 0
            avg_prompt_length = avg_prompt_length / strategy_count if strategy_count > 0 else 0
            
            print(f"{model_name:<25} {total_calls:<10} {avg_duration:<18.2f} {avg_prompt_length:<15.0f}")
    
    # Estadísticas globales
    if 'global_stats' in node_analysis:
        stats = node_analysis['global_stats']
        print(f"\n📈 ESTADÍSTICAS GLOBALES - NODOS")
        print("-" * 35)
        print(f"Total ejecuciones de nodos: {stats['total_node_executions']}")
        print(f"Tiempo promedio por nodo: {stats['overall_avg_time_ms']:.2f} ms")
        print(f"Tiempo mediano por nodo: {stats['overall_median_time_ms']:.2f} ms")
        print(f"Ejecución más rápida: {stats['fastest_execution_ms']:.2f} ms")
        print(f"Ejecución más lenta: {stats['slowest_execution_ms']:.2f} ms")
    
    # Estadísticas globales LLM
    if 'global_stats' in llm_analysis and llm_analysis['global_stats']:
        stats = llm_analysis['global_stats']
        print(f"\n🤖 ESTADÍSTICAS GLOBALES - LLM")
        print("-" * 35)
        print(f"Total llamadas LLM: {stats['total_llm_calls']}")
        print(f"Tiempo promedio por llamada: {stats['overall_avg_duration_ms']:.2f} ms")
        print(f"Tiempo mediano por llamada: {stats['overall_median_duration_ms']:.2f} ms")
        print(f"Llamada más rápida: {stats['fastest_call_ms']:.2f} ms")
        print(f"Llamada más lenta: {stats['slowest_call_ms']:.2f} ms")
        print(f"Caracteres de prompt totales: {stats['total_prompt_chars']:,}")
        print(f"Caracteres de respuesta totales: {stats['total_response_chars']:,}")
        print(f"Prompt promedio: {stats['avg_prompt_length']:.0f} caracteres")
        print(f"Respuesta promedio: {stats['avg_response_length']:.0f} caracteres")
    
    print("\n" + "="*80)

def save_json_report(node_analysis: Dict[str, Any], workflow_analysis: Dict[str, Any], llm_analysis: Dict[str, Any], output_file: str):
    """
    Guarda el reporte completo en formato JSON.
    """
    report = {
        'timestamp': None,  # Se puede añadir
        'node_metrics': node_analysis,
        'workflow_metrics': workflow_analysis,
        'llm_metrics': llm_analysis
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Reporte JSON guardado en: {output_file}")

def save_csv_summary(workflow_analysis: Dict[str, Any], output_file: str):
    """
    Guarda un resumen en formato CSV.
    """
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['Strategy', 'Total_Workflows', 'Success_Rate', 'Avg_Time_MS', 
                        'Avg_Retries', 'Avg_Faithfulness', 'Avg_Precision', 'Avg_Recall', 'Avg_Relevance'])
        
        # Data
        for strategy, data in workflow_analysis['by_strategy'].items():
            row = [
                strategy,
                data['total_workflows'],
                f"{data['success_rate']:.3f}",
                f"{data['avg_execution_time_ms']:.2f}",
                f"{data['avg_retries']:.2f}"
            ]
            
            # Añadir métricas de evaluación si existen
            if 'evaluation_metrics' in data:
                eval_metrics = data['evaluation_metrics']
                row.extend([
                    f"{eval_metrics['avg_faithfulness']:.3f}",
                    f"{eval_metrics['avg_context_precision']:.3f}",
                    f"{eval_metrics['avg_context_recall']:.3f}",
                    f"{eval_metrics['avg_answer_relevance']:.3f}"
                ])
            else:
                row.extend(['N/A', 'N/A', 'N/A', 'N/A'])
            
            writer.writerow(row)
    
    print(f"✅ Resumen CSV guardado en: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Analiza métricas del workflow de LangGraph')
    parser.add_argument('--metrics-dir', default='metrics', help='Directorio de métricas (default: metrics)')
    parser.add_argument('--output-format', choices=['table', 'json', 'csv'], default='table',
                       help='Formato de salida (default: table)')
    parser.add_argument('--output-file', help='Archivo de salida (para json/csv)')
    
    args = parser.parse_args()
    
    metrics_dir = Path(args.metrics_dir)
    
    if not metrics_dir.exists():
        print(f"❌ Error: Directorio de métricas no encontrado: {metrics_dir}")
        print(f"💡 Asegúrate de que el directorio existe y contiene datos de métricas.")
        sys.exit(1)
    
    print(f"🔍 Analizando métricas en: {metrics_dir.absolute()}")
    
    # Detectar estrategias dinámicamente
    strategies_found = get_strategy_directories(metrics_dir)
    
    if not strategies_found:
        print(f"❌ Error: No se encontraron directorios con archivos de métricas en {metrics_dir}")
        print(f"💡 Asegúrate de que existen directorios que contengan 'node_metrics.csv' o 'workflow_metrics.csv'")
        sys.exit(1)
    
    print(f"📁 Estrategias encontradas: {', '.join(strategies_found)}")
    
    # Analizar métricas
    print("\n🔄 Iniciando análisis...")
    node_analysis = analyze_node_metrics(metrics_dir)
    workflow_analysis = analyze_workflow_metrics(metrics_dir)
    llm_analysis = analyze_llm_metrics(metrics_dir)
    
    # Generar reporte según el formato solicitado
    if args.output_format == 'table':
        print_table_report(node_analysis, workflow_analysis, llm_analysis)
    
    elif args.output_format == 'json':
        output_file = args.output_file or 'metrics_report.json'
        save_json_report(node_analysis, workflow_analysis, llm_analysis, output_file)
        
    elif args.output_format == 'csv':
        output_file = args.output_file or 'metrics_summary.csv'
        save_csv_summary(workflow_analysis, output_file)
    
    print(f"\n✨ Análisis completado!")

if __name__ == '__main__':
    main() 