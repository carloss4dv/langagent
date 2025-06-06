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
    strategies = ['256', '512', '1024']
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
    strategies = ['256', '512', '1024']
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

def print_table_report(node_analysis: Dict[str, Any], workflow_analysis: Dict[str, Any]):
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
        print(f"{'Estrategia':<12} {'Workflows':<10} {'Éxito %':<10} {'Tiempo Prom (ms)':<18} {'Reintentos Prom':<15}")
        print("-" * 70)
        
        for strategy in strategies:
            data = workflow_analysis['by_strategy'][strategy]
            print(f"{strategy + ' tokens':<12} {data['total_workflows']:<10} "
                  f"{data['success_rate']*100:.1f}%{'':<6} {data['avg_execution_time_ms']:<18.2f} "
                  f"{data['avg_retries']:<15.2f}")
    
    # Comparación de velocidad
    if 'comparison' in workflow_analysis and workflow_analysis['comparison']:
        print(f"\n⚡ ANÁLISIS DE VELOCIDAD")
        print("-" * 30)
        comp = workflow_analysis['comparison']
        print(f"🥇 Estrategia más rápida: {comp['fastest_strategy']['strategy']} tokens "
              f"({comp['fastest_strategy']['avg_time_ms']:.2f} ms)")
        print(f"🐌 Estrategia más lenta: {comp['slowest_strategy']['strategy']} tokens "
              f"({comp['slowest_strategy']['avg_time_ms']:.2f} ms)")
        
        speedup = comp['slowest_strategy']['avg_time_ms'] / comp['fastest_strategy']['avg_time_ms']
        print(f"📈 Diferencia de velocidad: {speedup:.2f}x")
    
    # Métricas de evaluación
    if 'evaluation_metrics' in workflow_analysis and workflow_analysis['evaluation_metrics']:
        print(f"\n🎯 MÉTRICAS DE CALIDAD PROMEDIO")
        print("-" * 40)
        print(f"{'Estrategia':<12} {'Faithfulness':<13} {'Precision':<11} {'Recall':<9} {'Relevance':<10}")
        print("-" * 60)
        
        for strategy, metrics in workflow_analysis['evaluation_metrics'].items():
            print(f"{strategy + ' tokens':<12} {metrics['avg_faithfulness']:<13.3f} "
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
            header += f"{strategy + ' tokens':<15}"
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
    
    # Estadísticas globales
    if 'global_stats' in node_analysis:
        stats = node_analysis['global_stats']
        print(f"\n📈 ESTADÍSTICAS GLOBALES")
        print("-" * 25)
        print(f"Total ejecuciones de nodos: {stats['total_node_executions']}")
        print(f"Tiempo promedio por nodo: {stats['overall_avg_time_ms']:.2f} ms")
        print(f"Tiempo mediano por nodo: {stats['overall_median_time_ms']:.2f} ms")
        print(f"Ejecución más rápida: {stats['fastest_execution_ms']:.2f} ms")
        print(f"Ejecución más lenta: {stats['slowest_execution_ms']:.2f} ms")
    
    print("\n" + "="*80)

def save_json_report(node_analysis: Dict[str, Any], workflow_analysis: Dict[str, Any], output_file: str):
    """
    Guarda el reporte completo en formato JSON.
    """
    report = {
        'timestamp': None,  # Se puede añadir
        'node_metrics': node_analysis,
        'workflow_metrics': workflow_analysis
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
    
    # Verificar que existen subdirectorios de estrategias
    strategies_found = []
    for strategy in ['256', '512', '1024']:
        strategy_dir = metrics_dir / strategy
        if strategy_dir.exists():
            strategies_found.append(strategy)
    
    if not strategies_found:
        print(f"❌ Error: No se encontraron directorios de estrategias (256, 512, 1024) en {metrics_dir}")
        sys.exit(1)
    
    print(f"📁 Estrategias encontradas: {', '.join(strategies_found)}")
    
    # Analizar métricas
    print("\n🔄 Iniciando análisis...")
    node_analysis = analyze_node_metrics(metrics_dir)
    workflow_analysis = analyze_workflow_metrics(metrics_dir)
    
    # Generar reporte según el formato solicitado
    if args.output_format == 'table':
        print_table_report(node_analysis, workflow_analysis)
    
    elif args.output_format == 'json':
        output_file = args.output_file or 'metrics_report.json'
        save_json_report(node_analysis, workflow_analysis, output_file)
        
    elif args.output_format == 'csv':
        output_file = args.output_file or 'metrics_summary.csv'
        save_csv_summary(workflow_analysis, output_file)
    
    print(f"\n✨ Análisis completado!")

if __name__ == '__main__':
    main() 