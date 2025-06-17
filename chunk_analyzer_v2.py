#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizador de chunks MEJORADO para documentos de la Universidad de Zaragoza
Analiza la estructura jerárquica semántica (Atributo, Dimensión, Sección Principal) 
para encontrar configuraciones de chunk adaptativas óptimas basadas en métricas reales.

Versión 2.0 - Con métricas de evaluación reales del sistema RAG
"""

import os
import re
import statistics
from pathlib import Path
from typing import List, Dict, Tuple, Any
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import numpy as np
from collections import Counter

# Descargar recursos de NLTK si es necesario
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# ============================================================================
# MÉTRICAS DE EVALUACIÓN REALES OBTENIDAS DE LAS PRUEBAS DEL SISTEMA RAG
# ============================================================================
EVALUATION_METRICS = {
    "fixed_chunks": {
        256: {
            "answer_relevancy": 0.78, 
            "faithfulness": 0.83, 
            "contextual_precision": 0.63, 
            "contextual_recall": 0.65, 
            "contextual_relevancy": 0.39
        },
        512: {
            "answer_relevancy": 0.80, 
            "faithfulness": 0.81, 
            "contextual_precision": 0.45, 
            "contextual_recall": 0.57, 
            "contextual_relevancy": 0.40
        },
        1024: {
            "answer_relevancy": 0.79, 
            "faithfulness": 0.79, 
            "contextual_precision": 0.70, 
            "contextual_recall": 0.71, 
            "contextual_relevancy": 0.36
        }
    },
    "adaptive_chunks_classic": {
        256: {
            "answer_relevancy": 0.77, 
            "faithfulness": 0.84, 
            "contextual_precision": 0.64, 
            "contextual_recall": 0.71, 
            "contextual_relevancy": 0.40
        },
        512: {
            "answer_relevancy": 0.81, 
            "faithfulness": 0.81, 
            "contextual_precision": 0.63, 
            "contextual_recall": 0.82, 
            "contextual_relevancy": 0.39
        },
        1024: {
            "answer_relevancy": 0.80, 
            "faithfulness": 0.79, 
            "contextual_precision": 0.70, 
            "contextual_recall": 0.76, 
            "contextual_relevancy": 0.35
        }
    },
    "adaptive_chunks_nltk": {
        167: {
            "answer_relevancy": 0.75, 
            "faithfulness": 0.81, 
            "contextual_precision": 0.59, 
            "contextual_recall": 0.55, 
            "contextual_relevancy": 0.44
        },
        307: {
            "answer_relevancy": 0.76, 
            "faithfulness": 0.81, 
            "contextual_precision": 0.68, 
            "contextual_recall": 0.68, 
            "contextual_relevancy": 0.46
        },
        755: {
            "answer_relevancy": 0.79, 
            "faithfulness": 0.85, 
            "contextual_precision": 0.65, 
            "contextual_recall": 0.61, 
            "contextual_relevancy": 0.49
        }
    }
}

@dataclass
class SemanticTextUnit:
    """Representa una unidad de texto con información semántica del corpus de la UZ"""
    content: str
    unit_type: str  # 'attribute', 'dimension', 'main_section'
    char_count: int
    word_count: int
    start_pos: int
    end_pos: int
    semantic_level: str  # 'attribute', 'dimension', 'main_section'
    context_info: str = ""  # Información adicional de contexto

class CorpusAnalyzer:
    """Analizador semántico específico para el corpus de documentos de la Universidad de Zaragoza"""
    
    def __init__(self, data_dir: str = "output_md"):
        self.data_dir = Path(data_dir)
        self.documents = []
        self.semantic_units = []
        
    def load_documents(self) -> List[Dict]:
        """Carga documentos del corpus de la UZ"""
        documents = []
        for md_file in self.data_dir.glob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    documents.append({
                        'filename': md_file.name,
                        'content': content,
                        'size': len(content)
                    })
                    print(f"✓ Cargado: {md_file.name} ({len(content)} caracteres)")
            except Exception as e:
                print(f"✗ Error cargando {md_file.name}: {e}")
        
        self.documents = documents
        return documents
    
    def extract_main_sections(self, text: str) -> List[SemanticTextUnit]:
        """Extrae las secciones principales completas: # Medidas y # Dimensiones"""
        main_sections = []
        
        # Buscar las secciones principales (# Medidas, # Dimensiones)
        section_pattern = r'^# (Medidas|Dimensiones)\s*$'
        section_matches = list(re.finditer(section_pattern, text, re.MULTILINE))
        
        for i, match in enumerate(section_matches):
            section_title = match.group(1).strip()
            start_pos = match.start()
            
            # Encontrar el final de esta sección (inicio de la siguiente sección # o final del texto)
            if i + 1 < len(section_matches):
                end_pos = section_matches[i + 1].start()
            else:
                # Buscar si hay otra sección # después
                next_section = re.search(r'^# [^#]', text[start_pos + len(match.group(0)):], re.MULTILINE)
                if next_section:
                    end_pos = start_pos + len(match.group(0)) + next_section.start()
                else:
                    end_pos = len(text)
            
            # Extraer todo el contenido de la sección
            section_content = text[start_pos:end_pos].strip()
            
            # Solo incluir si tiene contenido sustancial
            if len(section_content) > 100:  # Mínimo 100 chars para ser una sección válida
                main_sections.append(SemanticTextUnit(
                    content=section_content,
                    unit_type='main_section',
                    char_count=len(section_content),
                    word_count=len(word_tokenize(section_content)),
                    start_pos=start_pos,
                    end_pos=end_pos,
                    semantic_level='main_section',
                    context_info=f"Sección: {section_title}"
                ))
        
        return main_sections
    
    def extract_dimensions(self, text: str) -> List[SemanticTextUnit]:
        """Extrae dimensiones/medidas completas: cada ## NOMBRE con todo su contenido incluyendo sub-elementos ###"""
        dimensions = []
        
        # Buscar todas las dimensiones/medidas (títulos ##)
        dimension_pattern = r'^## (.+?)$'
        dimension_matches = list(re.finditer(dimension_pattern, text, re.MULTILINE))
        
        for i, match in enumerate(dimension_matches):
            dimension_title = match.group(1).strip()
            start_pos = match.start()
            
            # Encontrar el final de esta dimensión (siguiente ## o # principal)
            if i + 1 < len(dimension_matches):
                # Siguiente dimensión ##
                end_pos = dimension_matches[i + 1].start()
            else:
                # Buscar siguiente sección principal # o final del texto
                remaining_text = text[start_pos + len(match.group(0)):]
                next_section = re.search(r'^# [^#]', remaining_text, re.MULTILINE)
                if next_section:
                    end_pos = start_pos + len(match.group(0)) + next_section.start()
                else:
                    end_pos = len(text)
            
            # Extraer todo el contenido de la dimensión (incluyendo sub-elementos ###)
            dimension_content = text[start_pos:end_pos].strip()
            
            # Limpiar separadores finales múltiples pero mantener estructura
            dimension_content = re.sub(r'\n---\s*$', '', dimension_content)
            dimension_content = re.sub(r'\n---\s*\n---\s*$', '', dimension_content)
            
            # Solo incluir si tiene contenido sustancial
            if len(dimension_content) > 50:  # Mínimo 50 chars para ser una dimensión válida
                dimensions.append(SemanticTextUnit(
                    content=dimension_content,
                    unit_type='dimension',
                    char_count=len(dimension_content),
                    word_count=len(word_tokenize(dimension_content)),
                    start_pos=start_pos,
                    end_pos=end_pos,
                    semantic_level='dimension',
                    context_info=f"Dimensión/Medida: {dimension_title}"
                ))
        
        return dimensions
    
    def extract_attributes(self, text: str) -> List[SemanticTextUnit]:
        """Extrae atributos/elementos específicos: ### títulos y elementos con •"""
        attributes = []
        
        # 1. Extraer sub-elementos ### (atributos de nivel 3)
        sub_pattern = r'^### (.+?)$'
        sub_matches = list(re.finditer(sub_pattern, text, re.MULTILINE))
        
        for i, match in enumerate(sub_matches):
            sub_title = match.group(1).strip()
            start_pos = match.start()
            
            # Encontrar el final de este sub-elemento
            if i + 1 < len(sub_matches):
                # Siguiente sub-elemento ###
                end_pos = sub_matches[i + 1].start()
            else:
                # Buscar siguiente elemento ## o # o final del texto
                next_element = re.search(r'^(##|#) [^#]', text[start_pos + len(match.group(0)):], re.MULTILINE)
                if next_element:
                    end_pos = start_pos + len(match.group(0)) + next_element.start()
                else:
                    # Buscar el siguiente separador ---
                    next_sep = text.find('\n---', start_pos + len(match.group(0)))
                    if next_sep != -1:
                        end_pos = next_sep
                    else:
                        end_pos = len(text)
            
            # Extraer contenido del sub-elemento
            sub_content = text[start_pos:end_pos].strip()
            sub_content = re.sub(r'\n---\s*$', '', sub_content)
            
            if len(sub_content) > 20:  # Mínimo 20 chars
                attributes.append(SemanticTextUnit(
                    content=sub_content,
                    unit_type='attribute',
                    char_count=len(sub_content),
                    word_count=len(word_tokenize(sub_content)),
                    start_pos=start_pos,
                    end_pos=end_pos,
                    semantic_level='attribute',
                    context_info=f"Sub-elemento: {sub_title}"
                ))
        
        # 2. Extraer elementos específicos con • (puntos de lista significativos)
        bullet_pattern = r'• ([^:•\n]+?)[:：]\s*([^•\n]*(?:\n(?![•#])[^•\n]*){0,3})'
        bullet_matches = re.finditer(bullet_pattern, text, re.MULTILINE | re.DOTALL)
        
        for match in bullet_matches:
            bullet_name = match.group(1).strip()
            bullet_description = match.group(2).strip()
            
            # Construir contenido completo del elemento
            full_content = f"• {bullet_name}:"
            if bullet_description:
                # Limitar la descripción a un tamaño razonable
                if len(bullet_description) > 300:
                    bullet_description = bullet_description[:300] + "..."
                full_content += f" {bullet_description}"
            
            full_content = full_content.strip()
            
            # Filtrar elementos muy cortos o genéricos
            if len(full_content) > 30 and len(bullet_name) > 2:  
                attributes.append(SemanticTextUnit(
                    content=full_content,
                    unit_type='attribute',
                    char_count=len(full_content),
                    word_count=len(word_tokenize(full_content)),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    semantic_level='attribute',
                    context_info=f"Elemento: {bullet_name}"
                ))
        
        return attributes
    
    def analyze_corpus_structure(self):
        """Analiza la estructura completa del corpus"""
        if not self.documents:
            self.load_documents()
        
        all_units = []
        
        for doc in self.documents:
            print(f"\n🔍 Analizando estructura semántica: {doc['filename']}")
            content = doc['content']
            
            # Extraer unidades semánticas
            main_sections = self.extract_main_sections(content)
            dimensions = self.extract_dimensions(content)
            attributes = self.extract_attributes(content)
            
            # Añadir metadatos
            for unit in main_sections + dimensions + attributes:
                unit_dict = {
                    'filename': doc['filename'],
                    'content': unit.content,
                    'unit_type': unit.unit_type,
                    'char_count': unit.char_count,
                    'word_count': unit.word_count,
                    'start_pos': unit.start_pos,
                    'end_pos': unit.end_pos,
                    'semantic_level': unit.semantic_level,
                    'context_info': unit.context_info
                }
                all_units.append(unit_dict)
            
            print(f"  📊 {len(main_sections)} secciones principales")
            print(f"  📋 {len(dimensions)} dimensiones")
            print(f"  🔸 {len(attributes)} atributos")
        
        self.semantic_units = all_units
        return all_units

class AdaptiveChunkOptimizer:
    """Optimizador de chunks adaptativos basado en métricas reales y análisis semántico"""
    
    def __init__(self, semantic_units: List[Dict[str, Any]]):
        self.semantic_units = semantic_units
        self.df = pd.DataFrame(semantic_units)
        self.evaluation_metrics = EVALUATION_METRICS
    
    def calculate_performance_score(self, metrics: Dict[str, float]) -> float:
        """Calcula score de rendimiento ponderado"""
        weights = {
            'answer_relevancy': 0.25,
            'faithfulness': 0.25,
            'contextual_precision': 0.20,
            'contextual_recall': 0.20,
            'contextual_relevancy': 0.10
        }
        
        return sum(weights.get(metric, 0) * value for metric, value in metrics.items())
    
    def analyze_semantic_statistics(self):
        """Analiza estadísticas por nivel semántico"""
        print("\n" + "="*80)
        print("📊 ANÁLISIS ESTADÍSTICO SEMÁNTICO DEL CORPUS")
        print("="*80)
        
        semantic_stats = {}
        
        for semantic_level in ['attribute', 'dimension', 'main_section']:
            units = self.df[self.df['semantic_level'] == semantic_level]
            if len(units) > 0:
                chars = units['char_count']
                words = units['word_count']
                
                # Análisis de distribución por rangos
                small_units = chars[chars < 200].count()
                medium_units = chars[(chars >= 200) & (chars < 500)].count()
                large_units = chars[chars >= 500].count()
                
                # Percentiles adicionales para mejor comprensión
                percentiles = [10, 25, 40, 50, 60, 75, 80, 85, 88, 90, 95]
                char_percentiles = {f'p{p}': chars.quantile(p/100) for p in percentiles}
                
                stats = {
                    'count': len(units),
                    'char_mean': chars.mean(),
                    'char_std': chars.std(),
                    'char_median': chars.median(),
                    'char_q25': chars.quantile(0.25),
                    'char_q75': chars.quantile(0.75),
                    'char_min': chars.min(),
                    'char_max': chars.max(),
                    'word_mean': words.mean(),
                    'word_median': words.median(),
                    'small_count': small_units,
                    'medium_count': medium_units,
                    'large_count': large_units,
                    'percentiles': char_percentiles
                }
                
                semantic_stats[semantic_level] = stats
                
                print(f"\n🔷 {semantic_level.upper().replace('_', ' ')}S ({len(units):,} unidades):")
                print(f"   📏 Caracteres: μ={stats['char_mean']:.1f} ± {stats['char_std']:.1f}")
                print(f"   📐 Mediana: {stats['char_median']:.1f}")
                print(f"   📊 Cuartiles: Q1={stats['char_q25']:.0f}, Q3={stats['char_q75']:.0f}")
                print(f"   📉 Rango: {stats['char_min']} - {stats['char_max']}")
                print(f"   📖 Palabras promedio: {stats['word_mean']:.1f}")
                
                # Mostrar distribución por tamaños
                print(f"   📋 Distribución:")
                print(f"      🔸 < 200 chars: {small_units} ({small_units/len(units)*100:.1f}%)")
                print(f"      🔹 200-500 chars: {medium_units} ({medium_units/len(units)*100:.1f}%)")
                print(f"      🔷 > 500 chars: {large_units} ({large_units/len(units)*100:.1f}%)")
                
                # Mostrar percentiles clave
                print(f"   📈 Percentiles: P10={char_percentiles['p10']:.0f}, P25={char_percentiles['p25']:.0f}, P75={char_percentiles['p75']:.0f}, P90={char_percentiles['p90']:.0f}")
                
                # Detectar si hay mucha variabilidad
                cv = stats['char_std'] / stats['char_mean']  # Coeficiente de variación
                if cv > 1.0:
                    print(f"   ⚠️  ALTA VARIABILIDAD detectada (CV={cv:.2f}) - corpus heterogéneo")
                    print(f"      🎯 Recomendación: usar estrategia adaptativa que maneje rangos amplios")
        
        return semantic_stats
    
    def analyze_current_performance(self):
        """Analiza el rendimiento de las configuraciones actuales"""
        print(f"\n📈 ANÁLISIS DE RENDIMIENTO ACTUAL:")
        print("="*60)
        
        best_configs = {}
        
        for strategy_name, strategy_data in self.evaluation_metrics.items():
            print(f"\n🔹 {strategy_name.upper().replace('_', ' ')}:")
            
            strategy_scores = {}
            for chunk_size, metrics in strategy_data.items():
                score = self.calculate_performance_score(metrics)
                strategy_scores[chunk_size] = {
                    'score': score,
                    'metrics': metrics
                }
                
                print(f"   📏 Chunk {chunk_size}: Score {score:.3f}")
                print(f"      AR: {metrics['answer_relevancy']:.3f} | F: {metrics['faithfulness']:.3f} | "
                      f"CP: {metrics['contextual_precision']:.3f} | CR: {metrics['contextual_recall']:.3f}")
            
            # Mejor configuración de esta estrategia
            best_chunk = max(strategy_scores.items(), key=lambda x: x[1]['score'])
            best_configs[strategy_name] = best_chunk
            print(f"   🏆 Mejor: Chunk {best_chunk[0]} (Score: {best_chunk[1]['score']:.3f})")
        
        return best_configs
    
    def generate_adaptive_triplets(self, semantic_stats: Dict) -> List[Dict]:
        """Genera tríos adaptativos de tamaños de chunk considerando la variabilidad natural del corpus"""
        print(f"\n🎯 GENERANDO TRÍOS ADAPTATIVOS DE CHUNKS")
        print("="*60)
        
        triplets = []
        
        # Verificar que tenemos estadísticas para todos los niveles
        required_levels = ['attribute', 'dimension', 'main_section']
        available_levels = [level for level in required_levels if level in semantic_stats]
        
        if len(available_levels) < 2:
            print(f"⚠️  Datos insuficientes para generar tríos. Niveles disponibles: {available_levels}")
            return triplets
        
        # Análisis de la variabilidad del corpus
        print(f"\n🔍 ANÁLISIS DE VARIABILIDAD DEL CORPUS:")
        
        total_variability_high = False
        if 'dimension' in semantic_stats:
            dim_stats = semantic_stats['dimension']
            cv = dim_stats['char_std'] / dim_stats['char_mean']
            print(f"   📊 Coeficiente de variación en dimensiones: {cv:.2f}")
            if cv > 1.0:
                total_variability_high = True
                print(f"   ⚠️  CORPUS ALTAMENTE HETEROGÉNEO - necesitamos estrategia robusta")
        
        # TRÍO 1: Basado en percentiles robustos (maneja variabilidad)
        if 'dimension' in semantic_stats:
            dim_stats = semantic_stats['dimension']
            # Usar percentiles más amplios para manejar variabilidad
            small = int(dim_stats['percentiles']['p25'])    # P25 en lugar de Q1
            medium = int(dim_stats['percentiles']['p50'])   # Mediana
            large = int(dim_stats['percentiles']['p75'])    # P75
            
            triplets.append({
                'id': 1,
                'name': 'Percentiles Robustos',
                'description': 'Basado en percentiles P25, P50, P75 para manejar variabilidad',
                'small_chunk': small,
                'medium_chunk': medium,
                'large_chunk': large,
                'semantic_basis': 'robust_percentiles',
                'variability_aware': True
            })
        
        # TRÍO 2: Estrategia de rangos adaptativos
        if 'dimension' in semantic_stats:
            dim_stats = semantic_stats['dimension']
            # Chunks que capturen diferentes tipos de dimensiones
            small = max(150, int(dim_stats['percentiles']['p10']))   # Mínimo 150 para dimensiones cortas
            medium = int(dim_stats['char_median'])                   # Dimensión típica
            large = min(1200, int(dim_stats['percentiles']['p90']))  # Máximo 1200 para dimensiones largas
            
            triplets.append({
                'id': 2,
                'name': 'Rangos Adaptativos',
                'description': 'P10 con mínimo 150, mediana, P90 con máximo 1200',
                'small_chunk': small,
                'medium_chunk': medium,
                'large_chunk': large,
                'semantic_basis': 'adaptive_ranges',
                'variability_aware': True
            })
        
        # TRÍO 3: Estrategia por tipos de contenido
        if 'attribute' in semantic_stats and 'dimension' in semantic_stats:
            attr_stats = semantic_stats['attribute']
            dim_stats = semantic_stats['dimension']
            
            # Chunk pequeño: para atributos simples
            small = max(100, int(attr_stats['char_median'] * 1.5))
            # Chunk medio: para dimensiones pequeñas-medianas
            medium = int(dim_stats['percentiles']['p60'])  # P60 de dimensiones
            # Chunk grande: para dimensiones extensas
            large = int(dim_stats['percentiles']['p85'])   # P85 de dimensiones
            
            triplets.append({
                'id': 3,
                'name': 'Tipo de Contenido',
                'description': 'Atributos (1.5x mediana) → Dim P60 → Dim P85',
                'small_chunk': small,
                'medium_chunk': medium,
                'large_chunk': large,
                'semantic_basis': 'content_type_aware',
                'variability_aware': True
            })
        
        # TRÍO 4: Optimizado por métricas + variabilidad
        best_nltk = max(self.evaluation_metrics['adaptive_chunks_nltk'].items(), 
                       key=lambda x: self.calculate_performance_score(x[1]))
        
        base_size = best_nltk[0]
        
        # Ajustar según variabilidad detectada
        if total_variability_high:
            # Rangos más amplios para corpus variable
            small = int(base_size * 0.6)    # 60% del mejor actual
            medium = base_size              # El mejor actual
            large = int(base_size * 1.8)    # 180% del mejor actual
        else:
            # Rangos normales para corpus uniforme
            small = int(base_size * 0.7)    # 70% del mejor actual
            medium = base_size              # El mejor actual
            large = int(base_size * 1.4)    # 140% del mejor actual
        
        triplets.append({
            'id': 4,
            'name': 'Métricas + Variabilidad',
            'description': f'Basado en mejor actual ({base_size}) con ajuste por variabilidad',
            'small_chunk': small,
            'medium_chunk': medium,
            'large_chunk': large,
            'semantic_basis': 'performance_variability_optimized',
            'variability_aware': total_variability_high
        })
        
        # TRÍO 5: Estrategia de cobertura completa
        all_chars = self.df['char_count']
        # Asegurar que cubrimos desde dimensiones muy cortas hasta muy largas
        small = max(120, int(all_chars.quantile(0.20)))    # P20 con mínimo 120
        medium = int(all_chars.quantile(0.55))             # P55
        large = min(1500, int(all_chars.quantile(0.88)))   # P88 con máximo 1500
        
        triplets.append({
            'id': 5,
            'name': 'Cobertura Completa',
            'description': 'P20 (min 120), P55, P88 (max 1500) - cubre todo el espectro',
            'small_chunk': small,
            'medium_chunk': medium,
            'large_chunk': large,
            'semantic_basis': 'full_coverage',
            'variability_aware': True
        })
        
        # TRÍO 6: Granularidad múltiple inteligente
        if 'attribute' in semantic_stats and 'dimension' in semantic_stats:
            attr_stats = semantic_stats['attribute']
            dim_stats = semantic_stats['dimension']
            
            # Diseñado para capturar diferentes niveles de granularidad
            small = int(attr_stats['char_mean'] * 2.5)      # 2-3 atributos
            medium = int(dim_stats['percentiles']['p40'])   # Dimensiones pequeñas-medias
            large = int(dim_stats['percentiles']['p80'])    # Dimensiones grandes
            
            triplets.append({
                'id': 6,
                'name': 'Granularidad Múltiple',
                'description': 'Multi-atributo (2.5x) → Dim P40 → Dim P80',
                'small_chunk': small,
                'medium_chunk': medium,
                'large_chunk': large,
                'semantic_basis': 'multi_granular',
                'variability_aware': True
            })
        
        # Mostrar tríos generados con análisis de cobertura
        print(f"\n📋 TRÍOS GENERADOS CON ANÁLISIS DE COBERTURA:")
        
        if 'dimension' in semantic_stats:
            dim_stats = semantic_stats['dimension']
            total_dims = dim_stats['count']
            
            for triplet in triplets:
                print(f"\n  {triplet['id']}. {triplet['name']}:")
                print(f"     📝 {triplet['description']}")
                print(f"     🔸 Pequeño: {triplet['small_chunk']} chars")
                print(f"     🔹 Mediano: {triplet['medium_chunk']} chars")
                print(f"     🔷 Grande: {triplet['large_chunk']} chars")
                
                # Verificar proporciones
                ratio_med = triplet['medium_chunk'] / triplet['small_chunk']
                ratio_large = triplet['large_chunk'] / triplet['small_chunk']
                print(f"     📊 Proporciones: 1 : {ratio_med:.1f} : {ratio_large:.1f}")
                
                # Estimar cobertura de dimensiones
                dims_covered_small = len(self.df[(self.df['semantic_level'] == 'dimension') & 
                                                (self.df['char_count'] <= triplet['small_chunk'])])
                dims_covered_medium = len(self.df[(self.df['semantic_level'] == 'dimension') & 
                                                 (self.df['char_count'] <= triplet['medium_chunk'])])
                dims_covered_large = len(self.df[(self.df['semantic_level'] == 'dimension') & 
                                                (self.df['char_count'] <= triplet['large_chunk'])])
                
                print(f"     📈 Cobertura estimada:")
                print(f"        🔸 Pequeño cubre: {dims_covered_small}/{total_dims} dimensiones ({dims_covered_small/total_dims*100:.1f}%)")
                print(f"        🔹 Mediano cubre: {dims_covered_medium}/{total_dims} dimensiones ({dims_covered_medium/total_dims*100:.1f}%)")
                print(f"        🔷 Grande cubre: {dims_covered_large}/{total_dims} dimensiones ({dims_covered_large/total_dims*100:.1f}%)")
                
                # Marcar si está diseñado para manejar variabilidad
                if triplet.get('variability_aware', False):
                    print(f"     ⚡ DISEÑADO PARA ALTA VARIABILIDAD")
        
        return triplets
    
    def calculate_optimal_overlaps(self, triplets: List[Dict]) -> List[Dict]:
        """Calcula overlaps óptimos para cada trio"""
        print(f"\n⚡ CALCULANDO OVERLAPS ÓPTIMOS")
        print("="*50)
        
        # Estadísticas base para overlaps
        attributes = self.df[self.df['semantic_level'] == 'attribute']
        avg_attribute = attributes['char_count'].mean() if len(attributes) > 0 else 80
        
        optimized_triplets = []
        
        for triplet in triplets:
            # Calcular overlaps adaptativos
            small_overlap = max(int(triplet['small_chunk'] * 0.15), int(avg_attribute * 0.8))
            medium_overlap = max(int(triplet['medium_chunk'] * 0.12), int(avg_attribute * 1.2))
            large_overlap = max(int(triplet['large_chunk'] * 0.10), int(avg_attribute * 1.5))
            
            # Asegurar que overlaps no excedan límites razonables
            small_overlap = min(small_overlap, triplet['small_chunk'] // 3)
            medium_overlap = min(medium_overlap, triplet['medium_chunk'] // 3)
            large_overlap = min(large_overlap, triplet['large_chunk'] // 3)
            
            optimized_triplet = triplet.copy()
            optimized_triplet.update({
                'small_overlap': small_overlap,
                'medium_overlap': medium_overlap,
                'large_overlap': large_overlap,
                'small_overlap_pct': (small_overlap / triplet['small_chunk'] * 100),
                'medium_overlap_pct': (medium_overlap / triplet['medium_chunk'] * 100),
                'large_overlap_pct': (large_overlap / triplet['large_chunk'] * 100)
            })
            
            optimized_triplets.append(optimized_triplet)
            
            print(f"\n📦 {triplet['name']}:")
            print(f"   🔸 Pequeño: {triplet['small_chunk']} chars, overlap {small_overlap} ({small_overlap/triplet['small_chunk']*100:.1f}%)")
            print(f"   🔹 Mediano: {triplet['medium_chunk']} chars, overlap {medium_overlap} ({medium_overlap/triplet['medium_chunk']*100:.1f}%)")
            print(f"   🔷 Grande: {triplet['large_chunk']} chars, overlap {large_overlap} ({large_overlap/triplet['large_chunk']*100:.1f}%)")
        
        return optimized_triplets
    
    def create_visualizations(self, optimized_triplets: List[Dict]):
        """Crea visualizaciones sin mostrarlas"""
        plt.style.use('seaborn-v0_8')
        plt.ioff()  # Desactivar modo interactivo
        
        # FIGURA 1: Métricas de evaluación reales comparadas
        fig1, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig1.suptitle('📊 Métricas de Evaluación Reales por Estrategia', fontsize=16, fontweight='bold')
        
        metrics_names = ['answer_relevancy', 'faithfulness', 'contextual_precision', 
                        'contextual_recall', 'contextual_relevancy']
        metric_labels = ['Answer Relevancy', 'Faithfulness', 'Contextual Precision',
                        'Contextual Recall', 'Contextual Relevancy']
        
        for idx, (metric, label) in enumerate(zip(metrics_names, metric_labels)):
            if idx < 5:  # Solo tenemos 5 métricas
                row, col = idx // 3, idx % 3
                ax = axes[row, col]
                
                for strategy_name, strategy_data in self.evaluation_metrics.items():
                    chunk_sizes = list(strategy_data.keys())
                    values = [strategy_data[size][metric] for size in chunk_sizes]
                    
                    strategy_label = strategy_name.replace('_', ' ').title()
                    ax.plot(chunk_sizes, values, marker='o', linewidth=2.5, 
                           markersize=8, label=strategy_label)
                
                ax.set_title(f'{label}', fontsize=12, fontweight='bold')
                ax.set_xlabel('Chunk Size')
                ax.set_ylabel(label)
                ax.legend(fontsize=9)
                ax.grid(True, alpha=0.3)
        
        # Ocultar subplot vacío
        axes[1, 2].axis('off')
        
        plt.tight_layout()
        plt.savefig('chunk_analysis_metricas_evaluacion_reales.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # FIGURA 2: Tríos adaptativos generados
        fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        fig2.suptitle('🎯 Tríos Adaptativos de Chunks Generados', fontsize=16, fontweight='bold')
        
        # Preparar datos
        triplet_names = [f"T{t['id']}: {t['name'][:15]}..." for t in optimized_triplets]
        small_sizes = [t['small_chunk'] for t in optimized_triplets]
        medium_sizes = [t['medium_chunk'] for t in optimized_triplets]
        large_sizes = [t['large_chunk'] for t in optimized_triplets]
        
        x = np.arange(len(triplet_names))
        width = 0.25
        
        # Subplot 1: Tamaños de chunks
        bars1 = ax1.bar(x - width, small_sizes, width, label='Pequeño', color='lightblue', alpha=0.8)
        bars2 = ax1.bar(x, medium_sizes, width, label='Mediano', color='lightgreen', alpha=0.8)
        bars3 = ax1.bar(x + width, large_sizes, width, label='Grande', color='lightcoral', alpha=0.8)
        
        ax1.set_title('Tamaños de Chunks por Trío')
        ax1.set_xlabel('Tríos Adaptativos')
        ax1.set_ylabel('Tamaño (caracteres)')
        ax1.set_xticks(x)
        ax1.set_xticklabels(triplet_names, rotation=45, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Añadir valores en las barras más altas
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                if height > 300:  # Solo mostrar valores en barras grandes
                    ax1.text(bar.get_x() + bar.get_width()/2., height + 10,
                            f'{int(height)}', ha='center', va='bottom', fontsize=8)
        
        # Subplot 2: Porcentajes de overlap
        small_overlaps = [t['small_overlap_pct'] for t in optimized_triplets]
        medium_overlaps = [t['medium_overlap_pct'] for t in optimized_triplets]
        large_overlaps = [t['large_overlap_pct'] for t in optimized_triplets]
        
        bars1 = ax2.bar(x - width, small_overlaps, width, label='Pequeño', color='lightblue', alpha=0.8)
        bars2 = ax2.bar(x, medium_overlaps, width, label='Mediano', color='lightgreen', alpha=0.8)
        bars3 = ax2.bar(x + width, large_overlaps, width, label='Grande', color='lightcoral', alpha=0.8)
        
        ax2.set_title('Porcentajes de Overlap por Trío')
        ax2.set_xlabel('Tríos Adaptativos')
        ax2.set_ylabel('Overlap (%)')
        ax2.set_xticks(x)
        ax2.set_xticklabels(triplet_names, rotation=45, ha='right')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Añadir valores de porcentaje
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                        f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig('chunk_analysis_trios_adaptativos.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"\n📊 Visualizaciones generadas (guardadas, no mostradas):")
        print(f"   📈 chunk_analysis_metricas_evaluacion_reales.png")
        print(f"   📈 chunk_analysis_trios_adaptativos.png")
    
    def save_results(self, optimized_triplets: List[Dict]):
        """Guarda resultados en archivos CSV y de configuración"""
        
        # CSV con todos los tríos
        triplets_df = pd.DataFrame(optimized_triplets)
        triplets_df.to_csv('trios_adaptativos_chunks.csv', index=False)
        
        # Archivo de configuración para implementar en config.py
        config_content = """# ============================================================================
# CONFIGURACIONES ADAPTATIVAS GENERADAS POR CHUNK_ANALYZER V2.0
# Basadas en análisis semántico del corpus UZ y métricas de evaluación reales
# ============================================================================

CHUNK_STRATEGIES_ADAPTIVE_TRIPLETS = {
"""
        
        for triplet in optimized_triplets:
            config_content += f'''    # {triplet['name']}: {triplet['description']}
    "{triplet['small_chunk']}_small": {{
        "collection_name": "adaptive_collection_{triplet['small_chunk']}_s",
        "chunk_size": {triplet['small_chunk']},
        "chunk_overlap": {triplet['small_overlap']},
        "semantic_basis": "{triplet['semantic_basis']}",
        "triplet_id": {triplet['id']}
    }},
    "{triplet['medium_chunk']}_medium": {{
        "collection_name": "adaptive_collection_{triplet['medium_chunk']}_m",
        "chunk_size": {triplet['medium_chunk']},
        "chunk_overlap": {triplet['medium_overlap']},
        "semantic_basis": "{triplet['semantic_basis']}",
        "triplet_id": {triplet['id']}
    }},
    "{triplet['large_chunk']}_large": {{
        "collection_name": "adaptive_collection_{triplet['large_chunk']}_l",
        "chunk_size": {triplet['large_chunk']},
        "chunk_overlap": {triplet['large_overlap']},
        "semantic_basis": "{triplet['semantic_basis']}",
        "triplet_id": {triplet['id']}
    }},
    
'''
        
        config_content += """}

# Configuración para usar en CHUNK_STRATEGY_CONFIG
ADAPTIVE_TRIPLET_STRATEGIES = {
"""
        
        for triplet in optimized_triplets:
            config_content += f'''    "triplet_{triplet['id']}": {{
        "small": "{triplet['small_chunk']}_small",
        "medium": "{triplet['medium_chunk']}_medium", 
        "large": "{triplet['large_chunk']}_large",
        "description": "{triplet['name']}"
    }},
'''
        
        config_content += "}\n"
        
        with open('config_trios_adaptativos.py', 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        # Resumen de recomendaciones
        recommendations = []
        
        # Evaluar tríos basándose en métricas actuales
        best_current_score = max([
            self.calculate_performance_score(metrics)
            for strategy_data in self.evaluation_metrics.values()
            for metrics in strategy_data.values()
        ])
        
        for triplet in optimized_triplets:
            # Estimación de rendimiento (heurística basada en tamaños similares a configuraciones actuales)
            estimated_score = 0
            
            # Buscar configuración actual más similar para cada tamaño del trío
            for size in [triplet['small_chunk'], triplet['medium_chunk'], triplet['large_chunk']]:
                closest_size = min(
                    [s for strategy in self.evaluation_metrics.values() for s in strategy.keys()],
                    key=lambda x: abs(x - size)
                )
                
                # Encontrar la estrategia y métricas de este tamaño
                for strategy_data in self.evaluation_metrics.values():
                    if closest_size in strategy_data:
                        score = self.calculate_performance_score(strategy_data[closest_size])
                        estimated_score += score
                        break
            
            estimated_score /= 3  # Promedio de los 3 tamaños
            
            recommendations.append({
                'triplet': triplet,
                'estimated_score': estimated_score,
                'improvement': estimated_score - best_current_score
            })
        
        # Ordenar por score estimado
        recommendations.sort(key=lambda x: x['estimated_score'], reverse=True)
        
        # Generar archivo de recomendaciones
        rec_content = "# RECOMENDACIONES DE IMPLEMENTACIÓN\n\n"
        rec_content += f"Mejor configuración actual: Score {best_current_score:.3f}\n\n"
        
        for i, rec in enumerate(recommendations[:3], 1):  # Top 3
            triplet = rec['triplet']
            priority = "ALTA" if i == 1 else "MEDIA" if i == 2 else "BAJA"
            
            rec_content += f"{i}. PRIORIDAD {priority}: {triplet['name']}\n"
            rec_content += f"   Descripción: {triplet['description']}\n"
            rec_content += f"   Score estimado: {rec['estimated_score']:.3f}\n"
            rec_content += f"   Mejora estimada: {rec['improvement']:+.3f}\n"
            rec_content += f"   Configuraciones:\n"
            rec_content += f"     - Pequeño: {triplet['small_chunk']} chars, {triplet['small_overlap']} overlap\n"
            rec_content += f"     - Mediano: {triplet['medium_chunk']} chars, {triplet['medium_overlap']} overlap\n"
            rec_content += f"     - Grande: {triplet['large_chunk']} chars, {triplet['large_overlap']} overlap\n\n"
        
        with open('recomendaciones_implementacion.txt', 'w', encoding='utf-8') as f:
            f.write(rec_content)
        
        print(f"\n💾 ARCHIVOS GENERADOS:")
        print(f"   📊 trios_adaptativos_chunks.csv - Todos los tríos con detalles")
        print(f"   🔧 config_trios_adaptativos.py - Configuración para integrar")
        print(f"   📋 recomendaciones_implementacion.txt - Prioridades de implementación")

def main():
    """Función principal del analizador mejorado v2.0"""
    print("🔍 ANALIZADOR DE CHUNKS V2.0 - LANGAGENT")
    print("="*70)
    print("Análisis semántico con métricas reales y generación de tríos adaptativos")
    print("Corpus: Documentos Universidad de Zaragoza")
    
    # Inicializar analizador
    analyzer = CorpusAnalyzer()
    
    # Cargar documentos
    print(f"\n📁 Cargando corpus desde '{analyzer.data_dir}'...")
    documents = analyzer.load_documents()
    
    if not documents:
        print("❌ No se encontraron documentos .md")
        return
    
    print(f"\n✅ Corpus cargado: {len(documents)} documentos")
    total_chars = sum(doc['size'] for doc in documents)
    print(f"📊 Total caracteres: {total_chars:,}")
    
    # Analizar estructura semántica
    print(f"\n🔬 Analizando estructura semántica del corpus...")
    semantic_units = analyzer.analyze_corpus_structure()
    
    # Optimizar con métricas reales
    optimizer = AdaptiveChunkOptimizer(semantic_units)
    
    # Análisis estadístico semántico
    semantic_stats = optimizer.analyze_semantic_statistics()
    
    # Análisis de rendimiento actual
    current_performance = optimizer.analyze_current_performance()
    
    # Generar tríos adaptativos
    triplets = optimizer.generate_adaptive_triplets(semantic_stats)
    
    if not triplets:
        print("❌ No se pudieron generar tríos adaptativos")
        return
    
    # Calcular overlaps óptimos
    optimized_triplets = optimizer.calculate_optimal_overlaps(triplets)
    
    # Crear visualizaciones
    optimizer.create_visualizations(optimized_triplets)
    
    # Guardar resultados
    optimizer.save_results(optimized_triplets)
    
    # Resumen final
    print("\n" + "="*70)
    print("🏆 RESUMEN FINAL - MEJORES CONFIGURACIONES")
    print("="*70)
    
    # Encontrar mejor configuración actual
    best_current = None
    best_score = 0
    
    for strategy_name, strategy_data in EVALUATION_METRICS.items():
        for chunk_size, metrics in strategy_data.items():
            score = optimizer.calculate_performance_score(metrics)
            if score > best_score:
                best_score = score
                best_current = (strategy_name, chunk_size, score)
    
    if best_current:
        print(f"\n📊 MEJOR CONFIGURACIÓN ACTUAL:")
        print(f"   📈 Estrategia: {best_current[0].replace('_', ' ').title()}")
        print(f"   📏 Chunk Size: {best_current[1]}")
        print(f"   ⭐ Score: {best_current[2]:.3f}")
    
    print(f"\n🎯 TOP 3 TRÍOS RECOMENDADOS PARA PROBAR:")
    
    for i, triplet in enumerate(optimized_triplets[:3], 1):
        priority = "🥇 ALTA" if i == 1 else "🥈 MEDIA" if i == 2 else "🥉 BAJA"
        print(f"\n  {priority}: {triplet['name']}")
        print(f"     📝 {triplet['description']}")
        print(f"     🔸 Pequeño: {triplet['small_chunk']} chars ({triplet['small_overlap']} overlap)")
        print(f"     🔹 Mediano: {triplet['medium_chunk']} chars ({triplet['medium_overlap']} overlap)")
        print(f"     🔷 Grande: {triplet['large_chunk']} chars ({triplet['large_overlap']} overlap)")
    
    print(f"\n🚀 SIGUIENTE PASO:")
    print(f"   1. Integra config_trios_adaptativos.py en tu config.py")
    print(f"   2. Implementa el trío de PRIORIDAD ALTA primero")
    print(f"   3. Evalúa el rendimiento con tus métricas RAG")
    print(f"   4. Ajusta basándose en resultados específicos")
    
    print(f"\n✅ Análisis completado exitosamente!")

if __name__ == "__main__":
    main() 