"""
Análisis de consultas y estrategias Mix-of-Granularity (MoG) para SEGEDA.

Este módulo contiene la lógica avanzada para analizar la complejidad de consultas
específicas del dominio SEGEDA y determinar las estrategias óptimas de granularidad
de chunks basadas en el enfoque Mix-of-Granularity.
"""

import re
from typing import List, Dict, Any, Optional

from langagent.models.constants import (
    AMBITOS_CUBOS, CUBO_TO_AMBITO, AMBITO_KEYWORDS
)
from langagent.config.config import CHUNK_STRATEGY_CONFIG

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)


def analyze_segeda_query_complexity(query: str, granularity_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analiza la complejidad semántica de una consulta específica del dominio SEGEDA.
    
    Args:
        query (str): Consulta a analizar
        granularity_history (List[Dict]): Histórico de granularidades probadas
        
    Returns:
        Dict[str, Any]: Análisis de complejidad incluyendo tipo de granularidad recomendada
    """
    
    # Indicadores de consulta específica (fine-grained - 256 tokens)
    specific_indicators = [
        # Números específicos y conteos exactos
        r'\bcuantos?\b',
        r'\bnumero\s+(total\s+)?de\b',
        r'\bcantidad\s+(total\s+)?de\b',
        r'\btotal\s+de\b',
        r'\bsum[ao]\s+de\b',
        r'\bconteo\s+de\b',
        r'\brecuento\s+de\b',
        
        # Métricas específicas de SEGEDA
        r'\b(tasa|ratio|porcentaje|media|promedio)\s+(de|del)\b',
        r'\bnota\s+media\b',
        r'\bindice\b',
        r'\btasa\s+de\s+(exito|rendimiento|evaluacion)\b',
        r'\bcréditos?\s+(matriculados?|superados?|presentados?|suspendidos?|evaluados?|reconocidos?)\b',
        r'\bconvocatorias?\s+consumidas?\b',
        r'\bcarga\s+docente\b',
        r'\bhoras?\s+de\s+docencia\b',
        r'\bquinquenios?\b',
        r'\btrienios?\b', 
        r'\bsexenios?\b',
        
        # Definiciones específicas del dominio
        r'\bque\s+(es|son|significa|define)\b.*\b(alumno|estudiante|credito|sexenio|quinquenio|trienio|puesto|cargo)\b',
        r'\bdefinicion\s+de\b',
        r'\bconcepto\s+de\b',
        r'\bsignificado\s+de\b',
        
        # Atributos y características específicas
        r'\batributos?\s+(de|del)\b',
        r'\bvalores?\s+posibles?\b',
        r'\bdimension\b.*\bcontiene\b',
        r'\bcaracteristicas?\s+(de|del)\b',
        
        # Elementos únicos y específicos
        r'\b(un|una|el|la)\s+(estudiante|alumno|profesor|investigador|proyecto|grupo|cargo|puesto|asignatura)\b',
        r'\bese\s+(cubo|ambito|dimension)\b',
        r'\besta\s+(medida|dimension|variable)\b',
        
        # Calificaciones específicas
        r'\bcalificacion\b',
        r'\b(aprobado|suspenso|sobresaliente|notable|matricula\s+de\s+honor|apto|no\s+apto)\b',
        
        # Estados específicos
        r'\b(nuevo\s+ingreso|egresado|graduado|doctorando)\b',
        r'\bsituacion\s+administrativa\b',
        r'\bestado\s+(civil|academico)\b'
    ]
    
    # Indicadores de consulta analítica (medium-grained - 512 tokens)
    analytical_indicators = [
        # Procesos y procedimientos de SEGEDA
        r'\bcomo\s+se\s+(calcula|determina|clasifica|mide|obtiene|gestiona|evalua)\b',
        r'\b(proceso|procedimiento|metodologia|mecanismo|metodo)\s+(de|para)\b',
        r'\bforma\s+de\b',
        r'\bmanera\s+de\b',
        r'\bmodo\s+de\b',
        
        # Comparaciones y diferencias
        r'\bdiferencia\s+entre\b',
        r'\bcomparacion\s+entre\b',
        r'\brelacion\s+entre\b',
        r'\bcontraste\s+entre\b',
        r'\b(mayor|menor|superior|inferior|mejor|peor)\s+(a|que)\b',
        r'\bfrente\s+a\b',
        r'\brrespecto\s+a\b',
        
        # Tipos y categorías del dominio
        r'\btipo[s]?\s+de\b',
        r'\bcategoria[s]?\s+de\b',
        r'\bclasificacion\s+de\b',
        r'\bmodalidades?\s+de\b',
        r'\bgrupos?\s+de\b',
        r'\bvariedades?\s+de\b',
        r'\bclases?\s+de\b',
        
        # Análisis específicos
        r'\banalisis\s+de\b',
        r'\bevaluacion\s+de\b',
        r'\bestudio\s+de\b',
        r'\bexamen\s+de\b',
        r'\brevision\s+de\b',
        
        # Criterios y condiciones
        r'\bcriterios?\s+(de|para)\b',
        r'\bcondiciones?\s+(de|para)\b',
        r'\brequisitos?\s+(de|para)\b',
        r'\bnormas?\s+(de|para)\b',
        
        # Específico de docencia y académico
        r'\b(docencia|investigacion|gestion)\s+(universitaria|academica)\b',
        r'\bplan\s+de\s+estudios?\b',
        r'\btitulacion\b',
        r'\basignatura[s]?\b.*\b(imparte|cursa|matricula)\b',
        r'\brama\s+de\s+conocimiento\b'
    ]
    
    # Indicadores de consulta amplia (coarse-grained - 1024 tokens)
    broad_indicators = [
        # Tendencias temporales y evolución
        r'\b(tendencia|evolucion|cambio|variacion|progresion|desarrollo)\b',
        r'\ba\s+lo\s+largo\s+de\b',
        r'\ben\s+el\s+tiempo\b',
        r'\bhistorial\b',
        r'\bevolucion\s+temporal\b',
        r'\bcomportamiento\s+a\s+lo\s+largo\b',
        r'\bserie\s+temporal\b',
        r'\b(crecimiento|decrecimiento|aumento|disminucion)\b',
        
        # Múltiples elementos y conjuntos
        r'\btodos?\s+(los?|las?)\b',
        r'\bconjunto\s+(completo\s+)?de\b',
        r'\blistado\s+(completo\s+)?de\b',
        r'\bresumen\s+(general\s+)?de\b',
        r'\binventario\s+de\b',
        r'\bcatalogo\s+de\b',
        r'\bdirectorio\s+de\b',
        
        # Consultas amplias y panorámicas
        r'\ben\s+general\b',
        r'\bpanorama\s+(general|completo|global)\b',
        r'\bvision\s+(general|global|integral|completa)\b',
        r'\bcontexto\s+(general|completo|global)\b',
        r'\bperspectiva\s+(general|global|amplia)\b',
        r'\bescenario\s+(general|completo)\b',
        
        # Múltiples ámbitos de SEGEDA
        r'\b(academico|investigacion|movilidad|rrhh)\b.*\by\b.*\b(academico|investigacion|movilidad|rrhh)\b',
        r'\bmultiples?\s+(cubos?|ambitos?|dimensiones?|areas?)\b',
        r'\bvarios?\s+(ambitos?|areas?|sectores?)\b',
        r'\bconjunto\s+de\s+(ambitos?|areas?)\b',
        
        # Análisis comprehensivos
        r'\banalisis\s+(completo|integral|exhaustivo|global|general)\b',
        r'\bestudio\s+(completo|integral|exhaustivo|global|general)\b',
        r'\binforme\s+(completo|general|global)\b',
        r'\bdiagnostico\s+(completo|integral|general)\b',
        r'\bevaluacion\s+(completa|integral|global)\b',
        
        # Distribuciones y estadísticas amplias
        r'\bdistribucion\s+(de|por)\b',
        r'\bestructura\s+(de|por)\b',
        r'\bcomposicion\s+(de|por)\b',
        r'\breparto\s+(de|por)\b',
        r'\bdesglose\s+(de|por)\b',
        
        # Específico de SEGEDA amplio
        r'\buniversidad\s+de\s+zaragoza\s+en\s+general\b',
        r'\bactividad\s+universitaria\s+global\b',
        r'\bfuncionamiento\s+general\b'
    ]
    
    query_lower = query.lower()
    
    # Contar coincidencias por categoría
    specific_count = sum(1 for pattern in specific_indicators if re.search(pattern, query_lower))
    analytical_count = sum(1 for pattern in analytical_indicators if re.search(pattern, query_lower))
    broad_count = sum(1 for pattern in broad_indicators if re.search(pattern, query_lower))
    
    # Análisis adicional del dominio SEGEDA más específico
    segeda_domain_score = 0
    
    # Detectar cubos específicos mencionados (más completo)
    cubo_mentions = re.findall(r'\b(matricula|admision|egresados|rendimiento|pdi|ptgas|proyectos|grupos|movilidad|docencia|oferta|plazas|solicitud|convocatoria|indices|bibliometricos|produccion|cientifica|acuerdos|bilaterales|cargo|puesto|rrhh|eepp)\b', query_lower)
    
    # Detectar medidas específicas (más completo)
    medida_mentions = re.findall(r'\b(alumnos?|estudiantes?|creditos?|efectivos?|puestos?|articulos?|tesis|libros?|capitulos?|actividades?|congresos?|citas|documentos?|investigadores?|profesores?|docentes?|quinquenios?|trienios?|sexenios?|horas?|asignaturas?|convocatorias?|solicitudes?|proyectos?|grupos?)\b', query_lower)
    
    # Detectar dimensiones específicas (más completo)
    dimension_mentions = re.findall(r'\b(curso\s+academico|centro|titulacion|asignatura|investigador|profesor|alumno|estudiante|acceso|matricula|rendimiento|calificacion|edad|sexo|nacionalidad|departamento|area|conocimiento|campus|localidad|dedicacion|categoria|permanente|doctor|tiempo|fecha|actualizacion)\b', query_lower)
    
    # Detectar términos técnicos específicos de SEGEDA
    technical_terms = re.findall(r'\b(eees|cneai|evau|pau|cfgs|sigma|preinscripcion|convalidacion|adaptacion|reconocimiento|intercambio|erasmus|permanencia|experimentalidad|interuniversitario|habilitante|rpt|idi|otri|ope|sgi|iis|aragon)\b', query_lower)
    
    # Calcular puntuación del dominio
    segeda_domain_score = len(cubo_mentions) + len(medida_mentions) + len(dimension_mentions) + len(technical_terms)
    
    # Aplicar histórico de granularidades si está disponible
    history_adjustment = 0
    tried_strategies = []
    if granularity_history:
        tried_strategies = [entry.get('strategy', '') for entry in granularity_history]
        
        # Si se han probado todas las estrategias, penalizar ligeramente
        all_strategies_tried = all(strategy in tried_strategies for strategy in ['256', '512', '1024'])
        if all_strategies_tried:
            history_adjustment = -0.1
        
        # Si una estrategia específica ha fallado múltiples veces, evitarla
        strategy_failures = {}
        for entry in granularity_history:
            strategy = entry.get('strategy', '')
            success = entry.get('success', False)
            if not success:
                strategy_failures[strategy] = strategy_failures.get(strategy, 0) + 1
    
    # Determinar granularidad recomendada con lógica mejorada
    total_indicators = specific_count + analytical_count + broad_count
    
    # Obtener estrategias disponibles ordenadas de menor a mayor granularidad
    strategies_sorted = sorted(CHUNK_STRATEGY_CONFIG["available_strategies"], key=int)
    fine_grained = strategies_sorted[0]  # Estrategia más fina
    medium_grained = strategies_sorted[len(strategies_sorted)//2] if len(strategies_sorted) > 2 else strategies_sorted[1] if len(strategies_sorted) > 1 else strategies_sorted[0]  # Estrategia media
    coarse_grained = strategies_sorted[-1]  # Estrategia más gruesa
    
    if total_indicators == 0:
        # Sin indicadores claros, usar análisis del dominio
        if segeda_domain_score >= 3:
            recommended_granularity = medium_grained  # Dominio específico → granularidad media
            confidence = 0.6
            reason = f"Sin patrones claros pero alto dominio SEGEDA (score: {segeda_domain_score}). Usando granularidad media."
        else:
            recommended_granularity = medium_grained  # Por defecto
            confidence = 0.5
            reason = "Sin patrones detectados. Granularidad media por defecto."
    elif specific_count > analytical_count and specific_count > broad_count:
        recommended_granularity = fine_grained
        confidence = specific_count / (total_indicators + 1)
        reason = f"Consulta específica detectada ({specific_count} indicadores específicos)"
    elif broad_count > analytical_count and broad_count >= specific_count:
        recommended_granularity = coarse_grained
        confidence = broad_count / (total_indicators + 1)
        reason = f"Consulta amplia detectada ({broad_count} indicadores amplios)"
    else:
        recommended_granularity = medium_grained
        confidence = max(analytical_count, 1) / (total_indicators + 1)
        reason = f"Consulta analítica detectada ({analytical_count} indicadores analíticos)" if analytical_count > 0 else "Granularidad media por patrones mixtos"
    
    # Ajustar confianza por dominio SEGEDA
    if segeda_domain_score >= 2:
        confidence = min(1.0, confidence + 0.1)  # Bonus por especificidad del dominio
    
    # Aplicar ajuste del histórico
    confidence += history_adjustment
    confidence = max(0.0, min(1.0, confidence))  # Mantener en rango [0, 1]
    
    # Evitar estrategias que han fallado múltiples veces
    if granularity_history and strategy_failures.get(recommended_granularity, 0) >= 2:
        # Buscar estrategia alternativa
        alternative_strategies = [s for s in CHUNK_STRATEGY_CONFIG["available_strategies"] if s != recommended_granularity]
        
        # Elegir la estrategia con menos fallos
        best_alternative = min(alternative_strategies, 
                              key=lambda s: strategy_failures.get(s, 0))
        
        original_strategy = recommended_granularity
        recommended_granularity = best_alternative
        reason += f" (Evitando {original_strategy} por múltiples fallos previos)"
    
    return {
        "recommended_granularity": recommended_granularity,
        "confidence": confidence,
        "reason": reason,
        "specific_indicators": specific_count,
        "analytical_indicators": analytical_count,
        "broad_indicators": broad_count,
        "segeda_domain_score": segeda_domain_score,
        "cubo_mentions": cubo_mentions,
        "medida_mentions": medida_mentions,
        "dimension_mentions": dimension_mentions,
        "technical_terms": technical_terms,
        "tried_strategies": tried_strategies,
        "history_adjustment": history_adjustment
    }


def suggest_alternative_strategy_mog(current_strategy: str, metrics: Dict[str, float], query_analysis: Dict[str, Any], granularity_history: List[Dict[str, Any]] = None) -> str:
    """
    Sugiere una estrategia alternativa basada en el análisis MoG y las métricas actuales.
    
    Args:
        current_strategy (str): Estrategia actual de chunking
        metrics (Dict[str, float]): Métricas de evaluación actuales
        query_analysis (Dict[str, Any]): Análisis de la consulta
        granularity_history (List[Dict]): Histórico de granularidades probadas
        
    Returns:
        str: Estrategia alternativa recomendada
    """
    
    # Extraer métricas relevantes
    context_recall = metrics.get("context_recall", 0.0)
    context_precision = metrics.get("context_precision", 0.0)
    faithfulness = metrics.get("faithfulness", 0.0)
    answer_relevance = metrics.get("answer_relevance", 0.0)
    
    # Estrategia recomendada por análisis de consulta
    optimal_strategy = query_analysis.get("recommended_granularity", CHUNK_STRATEGY_CONFIG["default_strategy"])
    confidence = query_analysis.get("confidence", 0.5)
    
    # Analizar histórico para evitar bucles
    tried_strategies = []
    if granularity_history:
        tried_strategies = [entry.get('strategy', '') for entry in granularity_history[-3:]]  # Últimos 3 intentos
    
    # Si la confianza del análisis es alta (>0.75), priorizar la estrategia óptima
    if confidence > 0.75 and current_strategy != optimal_strategy and optimal_strategy not in tried_strategies:
        return optimal_strategy
    
    # Lógica específica basada en problemas de métricas con conocimiento del dominio SEGEDA
    strategies_sorted = sorted(CHUNK_STRATEGY_CONFIG["available_strategies"], key=int)
    fine_grained = strategies_sorted[0]
    medium_grained = strategies_sorted[len(strategies_sorted)//2] if len(strategies_sorted) > 2 else strategies_sorted[1] if len(strategies_sorted) > 1 else strategies_sorted[0]
    coarse_grained = strategies_sorted[-1]
    
    # Problema de recall bajo: necesitamos más contexto
    if context_recall < 0.6:
        # Para consultas sobre medidas específicas, el recall bajo puede indicar que necesitamos
        # más contexto sobre las definiciones y observaciones
        if query_analysis.get("medida_mentions") and current_strategy == fine_grained:
            return medium_grained  # Las medidas necesitan contexto sobre observaciones
        elif current_strategy == medium_grained:
            return coarse_grained  # Necesitamos más contexto general
        elif current_strategy == fine_grained:
            return medium_grained  # Incrementar moderadamente
        else:  # current_strategy == coarse_grained
            return coarse_grained  # Ya en máximo, mantener
    
    # Problema de precisión/faithfulness bajo: necesitamos más precisión
    if context_precision < 0.6 or faithfulness < 0.6:
        # Para consultas con términos técnicos específicos, la precisión baja indica chunks demasiado amplios
        if query_analysis.get("technical_terms") and current_strategy == coarse_grained:
            return fine_grained  # Términos técnicos necesitan contexto específico
        elif current_strategy == coarse_grained:
            return medium_grained  # Decrementar moderadamente
        elif current_strategy == medium_grained:
            return fine_grained  # Decrementar más
        else:  # current_strategy == fine_grained
            return fine_grained  # Ya en mínimo, mantener
    
    # Problema de relevancia: estrategias específicas por tipo de consulta
    if answer_relevance < 0.6:
        # Para consultas específicas sobre cubos pero usando granularidad gruesa
        if query_analysis.get("cubo_mentions") and query_analysis.get("specific_indicators", 0) > 0 and current_strategy != fine_grained:
            return fine_grained
        
        # Para consultas amplias pero usando granularidad fina
        if query_analysis.get("broad_indicators", 0) > 0 and current_strategy != coarse_grained:
            return coarse_grained
        
        # Para consultas sobre procesos/procedimientos, usar granularidad media
        if query_analysis.get("analytical_indicators", 0) > 0 and current_strategy != medium_grained:
            return medium_grained
        
        # Si tenemos alta puntuación de dominio SEGEDA, ajustar según el tipo de contenido
        segeda_score = query_analysis.get("segeda_domain_score", 0)
        if segeda_score >= 3:
            # Alto conocimiento del dominio → usar estrategia según indicadores dominantes
            if query_analysis.get("specific_indicators", 0) >= query_analysis.get("broad_indicators", 0):
                return fine_grained if current_strategy != fine_grained else medium_grained
            else:
                return coarse_grained if current_strategy != coarse_grained else medium_grained
    
    # Evitar estrategias recién probadas para prevenir bucles
    if len(tried_strategies) >= 2:
        available_strategies = [s for s in CHUNK_STRATEGY_CONFIG["available_strategies"] if s not in tried_strategies]
        
        if available_strategies:
            # Elegir la mejor estrategia disponible basada en el análisis
            if optimal_strategy in available_strategies:
                return optimal_strategy
            else:
                return available_strategies[0]
    
    # Si no hay problemas claros, usar la estrategia óptima del análisis
    if optimal_strategy != current_strategy:
        return optimal_strategy
    
    # Como último recurso, probar la estrategia no usada
    all_strategies = [s for s in CHUNK_STRATEGY_CONFIG["available_strategies"] if s != current_strategy]
    
    # Preferir estrategia según el tipo de consulta detectado
    if query_analysis.get("specific_indicators", 0) > 0 and fine_grained in all_strategies:
        return fine_grained
    elif query_analysis.get("broad_indicators", 0) > 0 and coarse_grained in all_strategies:
        return coarse_grained
    elif medium_grained in all_strategies:
        return medium_grained
    
    return all_strategies[0] if all_strategies else current_strategy


def update_granularity_history_entry(granularity_history: List[Dict[str, Any]], 
                                     strategy: str, 
                                     retry_count: int, 
                                     metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Actualiza el histórico de granularidades con una nueva entrada.
    
    Args:
        granularity_history (List[Dict]): Histórico actual
        strategy (str): Estrategia de chunk usada
        retry_count (int): Número de reintento
        metrics (Dict): Métricas de evaluación
        
    Returns:
        List[Dict]: Histórico actualizado
    """
    # Extraer métricas con valores por defecto
    faithfulness = metrics.get("faithfulness", 0.0)
    context_precision = metrics.get("context_precision", 0.0)
    context_recall = metrics.get("context_recall", 0.0)
    answer_relevance = metrics.get("answer_relevance", 0.0)
    
    # Verificar si todas las métricas están por encima de los umbrales
    metrics_successful = (
        faithfulness >= CHUNK_STRATEGY_CONFIG["evaluation_thresholds"]["faithfulness"] and
        context_precision >= CHUNK_STRATEGY_CONFIG["evaluation_thresholds"]["context_precision"] and
        context_recall >= CHUNK_STRATEGY_CONFIG["evaluation_thresholds"]["context_recall"] and
        answer_relevance >= CHUNK_STRATEGY_CONFIG["evaluation_thresholds"]["answer_relevance"]
    )
    
    # Solo añadir al histórico si tenemos métricas válidas (retry_count > 0 o métricas exitosas)
    if retry_count > 0 or metrics_successful:
        current_entry = {
            "strategy": strategy,
            "retry_count": retry_count,
            "metrics": {
                "faithfulness": faithfulness,
                "context_precision": context_precision,
                "context_recall": context_recall,
                "answer_relevance": answer_relevance
            },
            "success": metrics_successful,
            "timestamp": retry_count
        }
        
        # Evitar duplicados: verificar si ya existe una entrada para este retry_count y estrategia
        existing_entry = next(
            (entry for entry in granularity_history 
             if entry.get('retry_count') == retry_count and entry.get('strategy') == strategy),
            None
        )
        
        if not existing_entry:
            granularity_history.append(current_entry)
            
            # Mantener solo las últimas 5 entradas para evitar consumo excesivo de memoria
            if len(granularity_history) > 5:
                granularity_history = granularity_history[-5:]
            
            logger.info(f"Histórico de granularidades actualizado. Entrada añadida: estrategia={strategy}, retry={retry_count}, éxito={metrics_successful}")
            logger.info(f"Histórico actual - Total entradas: {len(granularity_history)}")
            for i, entry in enumerate(granularity_history):
                logger.info(f"  [{i+1}] Estrategia: {entry['strategy']}, Retry: {entry['retry_count']}, Éxito: {entry['success']}")
        else:
            logger.info(f"Entrada ya existente en el histórico para retry_count={retry_count} y estrategia={strategy}")
    
    return granularity_history 