import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os
from pathlib import Path

# Configurar estilo
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

def ensure_dir_exists(path):
    """Crear directorio si no existe"""
    Path(path).mkdir(parents=True, exist_ok=True)

def safe_value(value, default=0):
    """Convertir valores nulos a default"""
    return value if value is not None else default

def safe_duration(value):
    """Convertir duraciones de 0 a 0.001 ms"""
    if value is None or value == 0:
        return 0.001
    return value

def load_metrics(filename):
    """Cargar métricas desde JSON"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_node_metrics_by_strategy(data, output_dir):
    """Diagramas de métricas de nodos por estrategia"""
    node_metrics = data['node_metrics']['by_strategy']
    
    # 1. Tiempo de ejecución promedio por estrategia
    strategies = []
    avg_times = []
    
    for strategy, metrics in node_metrics.items():
        strategies.append(strategy)
        avg_times.append(safe_duration(metrics['avg_execution_time_ms']))
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(strategies, avg_times, color=sns.color_palette("husl", len(strategies)))
    plt.title('Tiempo de Ejecución Promedio por Estrategia (Nodos)', fontsize=14, fontweight='bold')
    plt.xlabel('Estrategia')
    plt.ylabel('Tiempo Promedio (ms)')
    plt.xticks(rotation=45)
    
    # Añadir valores en las barras
    for bar, value in zip(bars, avg_times):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(avg_times)*0.01,
                f'{value:.1f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/node_avg_execution_time_by_strategy.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Tasa de éxito por estrategia
    strategies = []
    success_rates = []
    
    for strategy, metrics in node_metrics.items():
        strategies.append(strategy)
        success_rates.append(safe_value(metrics['success_rate'], 0) * 100)
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(strategies, success_rates, color=sns.color_palette("viridis", len(strategies)))
    plt.title('Tasa de Éxito por Estrategia (Nodos)', fontsize=14, fontweight='bold')
    plt.xlabel('Estrategia')
    plt.ylabel('Tasa de Éxito (%)')
    plt.ylim(0, 105)
    plt.xticks(rotation=45)
    
    for bar, value in zip(bars, success_rates):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{value:.1f}%', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/node_success_rate_by_strategy.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Tamaño de contexto promedio por estrategia
    strategies = []
    context_sizes = []
    
    for strategy, metrics in node_metrics.items():
        strategies.append(strategy)
        context_sizes.append(safe_value(metrics['avg_context_size_chars'], 0))
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(strategies, context_sizes, color=sns.color_palette("plasma", len(strategies)))
    plt.title('Tamaño de Contexto Promedio por Estrategia (Nodos)', fontsize=14, fontweight='bold')
    plt.xlabel('Estrategia')
    plt.ylabel('Caracteres')
    plt.xticks(rotation=45)
    
    for bar, value in zip(bars, context_sizes):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(context_sizes)*0.01,
                f'{value:.0f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/node_context_size_by_strategy.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_workflow_metrics(data, output_dir):
    """Diagramas de métricas de workflow"""
    workflow_metrics = data['workflow_metrics']['by_strategy']
    
    # 1. Tiempo de ejecución de workflows
    strategies = []
    avg_times = []
    
    for strategy, metrics in workflow_metrics.items():
        strategies.append(strategy)
        avg_times.append(safe_duration(metrics['avg_execution_time_ms']))
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(strategies, avg_times, color=sns.color_palette("rocket", len(strategies)))
    plt.title('Tiempo de Ejecución Promedio por Estrategia (Workflows)', fontsize=14, fontweight='bold')
    plt.xlabel('Estrategia')
    plt.ylabel('Tiempo Promedio (ms)')
    plt.xticks(rotation=45)
    
    for bar, value in zip(bars, avg_times):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(avg_times)*0.01,
                f'{value:.0f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/workflow_execution_time_by_strategy.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Número de workflows por estrategia
    strategies = []
    total_workflows = []
    
    for strategy, metrics in workflow_metrics.items():
        strategies.append(strategy)
        total_workflows.append(safe_value(metrics['total_workflows'], 0))
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(strategies, total_workflows, color=sns.color_palette("mako", len(strategies)))
    plt.title('Número Total de Workflows por Estrategia', fontsize=14, fontweight='bold')
    plt.xlabel('Estrategia')
    plt.ylabel('Número de Workflows')
    plt.xticks(rotation=45)
    
    for bar, value in zip(bars, total_workflows):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(total_workflows)*0.01,
                f'{value}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/workflow_count_by_strategy.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Promedio de reintentos por estrategia
    strategies = []
    avg_retries = []
    
    for strategy, metrics in workflow_metrics.items():
        strategies.append(strategy)
        avg_retries.append(safe_value(metrics['avg_retries'], 0))
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(strategies, avg_retries, color=sns.color_palette("flare", len(strategies)))
    plt.title('Promedio de Reintentos por Estrategia', fontsize=14, fontweight='bold')
    plt.xlabel('Estrategia')
    plt.ylabel('Promedio de Reintentos')
    plt.xticks(rotation=45)
    
    for bar, value in zip(bars, avg_retries):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(avg_retries)*0.05,
                f'{value:.2f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/workflow_retries_by_strategy.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_evaluation_metrics(data, output_dir):
    """Diagramas de métricas de evaluación"""
    eval_metrics = data['workflow_metrics']['evaluation_metrics']
    
    # Preparar datos
    strategies = list(eval_metrics.keys())
    metrics_names = ['avg_faithfulness', 'avg_context_precision', 'avg_context_recall', 'avg_answer_relevance']
    
    # Crear matriz de datos
    matrix_data = []
    for strategy in strategies:
        row = []
        for metric in metrics_names:
            row.append(safe_value(eval_metrics[strategy][metric], 0))
        matrix_data.append(row)
    
    # 1. Heatmap de métricas de evaluación
    plt.figure(figsize=(10, 8))
    df = pd.DataFrame(matrix_data, index=strategies, columns=metrics_names)
    sns.heatmap(df, annot=True, fmt='.3f', cmap='YlOrRd', center=0.5)
    plt.title('Métricas de Evaluación por Estrategia', fontsize=14, fontweight='bold')
    plt.ylabel('Estrategia')
    plt.xlabel('Métrica')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/evaluation_metrics_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Gráfico de barras agrupadas para métricas de evaluación
    x = np.arange(len(strategies))
    width = 0.2
    
    plt.figure(figsize=(15, 8))
    
    for i, metric in enumerate(metrics_names):
        values = [safe_value(eval_metrics[strategy][metric], 0) for strategy in strategies]
        plt.bar(x + i * width, values, width, label=metric.replace('avg_', '').replace('_', ' ').title())
    
    plt.xlabel('Estrategia')
    plt.ylabel('Puntuación')
    plt.title('Métricas de Evaluación por Estrategia', fontsize=14, fontweight='bold')
    plt.xticks(x + width * 1.5, strategies, rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{output_dir}/evaluation_metrics_grouped.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_llm_metrics(data, output_dir):
    """Diagramas de métricas de LLM"""
    llm_metrics = data['llm_metrics']['by_model']
    
    # 1. Número de llamadas por modelo
    models = []
    total_calls = []
    
    for model, metrics in llm_metrics.items():
        models.append(model)
        total_calls.append(safe_value(metrics['total_calls'], 0))
    
    plt.figure(figsize=(12, 6))
    bars = plt.bar(models, total_calls, color=sns.color_palette("Set2", len(models)))
    plt.title('Número Total de Llamadas por Modelo LLM', fontsize=14, fontweight='bold')
    plt.xlabel('Modelo')
    plt.ylabel('Número de Llamadas')
    plt.xticks(rotation=45)
    
    for bar, value in zip(bars, total_calls):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(total_calls)*0.01,
                f'{value}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/llm_calls_by_model.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Longitud promedio de prompt por modelo (tokens)
    llm_strategy_metrics = data['llm_metrics']['by_strategy']
    
    models_data = {}
    for strategy, strategy_data in llm_strategy_metrics.items():
        for model, model_data in strategy_data['by_model'].items():
            if model not in models_data:
                models_data[model] = []
            avg_prompt = safe_value(model_data['avg_prompt_length'], 0)
            if avg_prompt > 0:  # Solo incluir si no es 0
                models_data[model].append(avg_prompt)
    
    if models_data:
        models = list(models_data.keys())
        avg_prompts = [np.mean(models_data[model]) if models_data[model] else 0 for model in models]
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(models, avg_prompts, color=sns.color_palette("Set1", len(models)))
        plt.title('Longitud Promedio de Prompt por Modelo (Tokens)', fontsize=14, fontweight='bold')
        plt.xlabel('Modelo')
        plt.ylabel('Tokens Promedio')
        plt.xticks(rotation=45)
        
        for bar, value in zip(bars, avg_prompts):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(avg_prompts)*0.01,
                    f'{value:.0f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/llm_prompt_length_by_model.png', dpi=300, bbox_inches='tight')
        plt.close()

def create_node_comparison(data, output_dir):
    """Diagramas de comparación entre tipos de nodos"""
    node_metrics = data['node_metrics']['by_node']
    
    # 1. Tiempo de ejecución por tipo de nodo
    node_types = []
    avg_times = []
    
    for node_type, metrics in node_metrics.items():
        # Calcular promedio ponderado
        total_time = 0
        total_executions = 0
        
        for strategy, strategy_data in metrics['by_strategy'].items():
            executions = safe_value(strategy_data['executions'], 0)
            avg_time = safe_duration(strategy_data['avg_time_ms'])
            total_time += avg_time * executions
            total_executions += executions
        
        if total_executions > 0:
            node_types.append(node_type)
            avg_times.append(total_time / total_executions)
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(node_types, avg_times, color=sns.color_palette("deep", len(node_types)))
    plt.title('Tiempo de Ejecución Promedio por Tipo de Nodo', fontsize=14, fontweight='bold')
    plt.xlabel('Tipo de Nodo')
    plt.ylabel('Tiempo Promedio (ms)')
    plt.xticks(rotation=45)
    
    for bar, value in zip(bars, avg_times):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(avg_times)*0.01,
                f'{value:.1f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/node_execution_time_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Número total de ejecuciones por tipo de nodo
    node_types = []
    total_executions = []
    
    for node_type, metrics in node_metrics.items():
        node_types.append(node_type)
        total_executions.append(safe_value(metrics['total_executions'], 0))
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(node_types, total_executions, color=sns.color_palette("pastel", len(node_types)))
    plt.title('Número Total de Ejecuciones por Tipo de Nodo', fontsize=14, fontweight='bold')
    plt.xlabel('Tipo de Nodo')
    plt.ylabel('Número de Ejecuciones')
    plt.xticks(rotation=45)
    
    for bar, value in zip(bars, total_executions):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(total_executions)*0.01,
                f'{value}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/node_executions_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_global_stats_diagram(data, output_dir):
    """Diagrama de estadísticas globales"""
    global_stats = data['node_metrics']['global_stats']
    
    # Crear un gráfico de resumen
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # 1. Total de ejecuciones de nodos
    ax1.bar(['Total Executions'], [safe_value(global_stats['total_node_executions'], 0)], 
            color='skyblue')
    ax1.set_title('Total de Ejecuciones de Nodos')
    ax1.set_ylabel('Número de Ejecuciones')
    
    # 2. Tiempos de ejecución
    times = [
        safe_duration(global_stats['overall_avg_time_ms']),
        safe_duration(global_stats['overall_median_time_ms']),
        safe_duration(global_stats['fastest_execution_ms']),
        safe_duration(global_stats['slowest_execution_ms'])
    ]
    labels = ['Promedio', 'Mediana', 'Más Rápido', 'Más Lento']
    
    ax2.bar(labels, times, color=['orange', 'green', 'blue', 'red'])
    ax2.set_title('Tiempos de Ejecución Globales')
    ax2.set_ylabel('Tiempo (ms)')
    ax2.tick_params(axis='x', rotation=45)
    
    # 3. Métricas LLM globales
    llm_global = data['llm_metrics']['global_stats']
    ax3.bar(['Total LLM Calls'], [safe_value(llm_global['total_llm_calls'], 0)], 
            color='lightcoral')
    ax3.set_title('Total de Llamadas LLM')
    ax3.set_ylabel('Número de Llamadas')
    
    # 4. Caracteres totales
    chars_data = [
        safe_value(llm_global['total_prompt_chars'], 0),
        safe_value(llm_global['total_response_chars'], 0)
    ]
    ax4.bar(['Prompt', 'Response'], chars_data, color=['purple', 'brown'])
    ax4.set_title('Total de Caracteres')
    ax4.set_ylabel('Número de Caracteres')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/global_statistics.png', dpi=300, bbox_inches='tight')
    plt.close()

def main():
    # Configuración
    json_file = 'metrics_report.json'
    output_dir = 'img/metrics'
    
    # Crear directorio de salida
    ensure_dir_exists(output_dir)
    
    # Cargar datos
    print("Cargando datos de métricas...")
    data = load_metrics(json_file)
    
    # Generar diagramas
    print("Generando diagramas de métricas de nodos...")
    create_node_metrics_by_strategy(data, output_dir)
    
    print("Generando diagramas de métricas de workflows...")
    create_workflow_metrics(data, output_dir)
    
    print("Generando diagramas de métricas de evaluación...")
    create_evaluation_metrics(data, output_dir)
    
    print("Generando diagramas de métricas de LLM...")
    create_llm_metrics(data, output_dir)
    
    print("Generando diagramas de comparación de nodos...")
    create_node_comparison(data, output_dir)
    
    print("Generando diagrama de estadísticas globales...")
    create_global_stats_diagram(data, output_dir)
    
    print(f"¡Todos los diagramas han sido generados y guardados en '{output_dir}'!")

if __name__ == "__main__":
    main() 