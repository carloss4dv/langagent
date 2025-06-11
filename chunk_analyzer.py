#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizador de chunks para documentos de la Universidad de Zaragoza
Analiza la estructura jerárquica (Sección, Párrafo, Oración) para encontrar
el tamaño de chunk y overlap óptimo para el sistema RAG de langagent.
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

@dataclass
class TextUnit:
    """Representa una unidad de texto (oración, párrafo o sección)"""
    content: str
    unit_type: str  # 'sentence', 'paragraph', 'section'
    char_count: int
    word_count: int
    start_pos: int
    end_pos: int
    
class DocumentAnalyzer:
    """Analizador de documentos para extraer estructura jerárquica"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.documents = []
        self.text_units = []
        
    def load_documents(self) -> List[str]:
        """Carga todos los documentos .md del directorio data"""
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
    
    def extract_sections(self, text: str) -> List[TextUnit]:
        """Extrae secciones basadas en la estructura de los documentos"""
        sections = []
        
        # Patrones para identificar secciones
        main_section_pattern = r'^=== (.+?) ===\s*$'
        sub_section_pattern = r'^## (.+?) ##\s*$'
        
        lines = text.split('\n')
        current_section = []
        current_section_name = ""
        start_pos = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Detectar inicio de sección principal
            main_match = re.match(main_section_pattern, line_stripped)
            sub_match = re.match(sub_section_pattern, line_stripped)
            
            if main_match or sub_match:
                # Procesar sección anterior si existe
                if current_section:
                    section_content = '\n'.join(current_section)
                    if section_content.strip():
                        sections.append(TextUnit(
                            content=section_content.strip(),
                            unit_type='section',
                            char_count=len(section_content),
                            word_count=len(word_tokenize(section_content)),
                            start_pos=start_pos,
                            end_pos=start_pos + len(section_content)
                        ))
                
                # Iniciar nueva sección
                current_section = [line]
                current_section_name = main_match.group(1) if main_match else sub_match.group(1)
                start_pos = sum(len(lines[j]) + 1 for j in range(i))
            else:
                current_section.append(line)
        
        # Procesar última sección
        if current_section:
            section_content = '\n'.join(current_section)
            if section_content.strip():
                sections.append(TextUnit(
                    content=section_content.strip(),
                    unit_type='section',
                    char_count=len(section_content),
                    word_count=len(word_tokenize(section_content)),
                    start_pos=start_pos,
                    end_pos=start_pos + len(section_content)
                ))
        
        return sections
    
    def extract_paragraphs(self, text: str) -> List[TextUnit]:
        """Extrae párrafos del texto"""
        paragraphs = []
        
        # Dividir por líneas vacías (párrafos)
        raw_paragraphs = re.split(r'\n\s*\n', text)
        start_pos = 0
        
        for para in raw_paragraphs:
            para = para.strip()
            if para:
                paragraphs.append(TextUnit(
                    content=para,
                    unit_type='paragraph',
                    char_count=len(para),
                    word_count=len(word_tokenize(para)),
                    start_pos=start_pos,
                    end_pos=start_pos + len(para)
                ))
                start_pos += len(para) + 2  # +2 para el salto de línea
        
        return paragraphs
    
    def extract_sentences(self, text: str) -> List[TextUnit]:
        """Extrae oraciones del texto"""
        sentences = []
        
        # Usar NLTK para tokenizar oraciones
        sent_list = sent_tokenize(text)
        start_pos = 0
        
        for sent in sent_list:
            sent = sent.strip()
            if sent:
                sentences.append(TextUnit(
                    content=sent,
                    unit_type='sentence',
                    char_count=len(sent),
                    word_count=len(word_tokenize(sent)),
                    start_pos=start_pos,
                    end_pos=start_pos + len(sent)
                ))
                # Buscar la posición real de la siguiente oración
                start_pos = text.find(sent, start_pos) + len(sent)
        
        return sentences
    
    def analyze_all_documents(self):
        """Analiza todos los documentos y extrae unidades de texto"""
        if not self.documents:
            self.load_documents()
        
        all_units = []
        
        for doc in self.documents:
            print(f"\nAnalizando: {doc['filename']}")
            content = doc['content']
            
            # Extraer diferentes tipos de unidades
            sections = self.extract_sections(content)
            paragraphs = self.extract_paragraphs(content)
            sentences = self.extract_sentences(content)
            
            # Añadir metadatos del documento
            for unit in sections + paragraphs + sentences:
                unit_dict = {
                    'filename': doc['filename'],
                    'content': unit.content,
                    'unit_type': unit.unit_type,
                    'char_count': unit.char_count,
                    'word_count': unit.word_count,
                    'start_pos': unit.start_pos,
                    'end_pos': unit.end_pos
                }
                all_units.append(unit_dict)
            
            print(f"  - {len(sections)} secciones")
            print(f"  - {len(paragraphs)} párrafos")
            print(f"  - {len(sentences)} oraciones")
        
        self.text_units = all_units
        return all_units

class ChunkOptimizer:
    """Optimizador de chunks basado en análisis estadístico"""
    
    def __init__(self, text_units: List[Dict[str, Any]]):
        self.text_units = text_units
        self.df = pd.DataFrame(text_units)
    
    def calculate_additional_metrics(self):
        """Calcula métricas adicionales para enriquecer el análisis"""
        print("\n" + "="*80)
        print("🔬 ANÁLISIS DETALLADO DE MÉTRICAS TEXTUALES")
        print("="*80)
        
        # Métricas generales del corpus
        total_units = len(self.df)
        total_chars = self.df['char_count'].sum()
        total_words = self.df['word_count'].sum()
        unique_files = self.df['filename'].nunique()
        
        print(f"\n📊 RESUMEN GENERAL DEL CORPUS:")
        print(f"   📁 Archivos analizados: {unique_files}")
        print(f"   📝 Total de unidades textuales: {total_units:,}")
        print(f"   📏 Total de caracteres: {total_chars:,}")
        print(f"   📖 Total de palabras: {total_words:,}")
        print(f"   📈 Promedio chars/palabra: {total_chars/total_words:.2f}")
        print(f"   📉 Densidad textual: {total_chars/total_units:.1f} chars/unidad")
        
        # Análisis por documento
        print(f"\n📋 ANÁLISIS POR DOCUMENTO:")
        doc_stats = self.df.groupby('filename').agg({
            'char_count': ['count', 'sum', 'mean', 'std'],
            'word_count': ['sum', 'mean'],
            'unit_type': lambda x: x.value_counts().to_dict()
        }).round(2)
        
        for filename in self.df['filename'].unique():
            doc_data = self.df[self.df['filename'] == filename]
            doc_chars = doc_data['char_count'].sum()
            doc_words = doc_data['word_count'].sum()
            doc_units = len(doc_data)
            
            # Distribución por tipo de unidad
            unit_dist = doc_data['unit_type'].value_counts()
            
            print(f"\n   📄 {filename}:")
            print(f"      🔢 Unidades totales: {doc_units}")
            print(f"      📏 Caracteres: {doc_chars:,} ({doc_chars/total_chars*100:.1f}% del total)")
            print(f"      📖 Palabras: {doc_words:,}")
            print(f"      📊 Distribución: ", end="")
            for unit_type, count in unit_dist.items():
                print(f"{unit_type}s={count}", end=" ")
            print()
            print(f"      🎯 Densidad: {doc_chars/doc_units:.1f} chars/unidad")
        
        # Análisis de densidad léxica
        print(f"\n🎯 ANÁLISIS DE DENSIDAD LÉXICA:")
        for unit_type in ['sentence', 'paragraph', 'section']:
            units = self.df[self.df['unit_type'] == unit_type]
            if len(units) > 0:
                avg_chars_per_word = (units['char_count'] / units['word_count']).mean()
                lexical_density = units['word_count'] / units['char_count'] * 100
                
                print(f"   📝 {unit_type.upper()}S:")
                print(f"      📐 Promedio chars/palabra: {avg_chars_per_word:.2f}")
                print(f"      📊 Densidad léxica: {lexical_density.mean():.2f}% (±{lexical_density.std():.2f})")
                print(f"      📏 Eficiencia textual: {1/avg_chars_per_word:.3f} palabras/char")
    
    def calculate_distribution_metrics(self):
        """Calcula métricas de distribución estadística avanzadas"""
        print(f"\n📈 MÉTRICAS DE DISTRIBUCIÓN ESTADÍSTICA:")
        
        for unit_type in ['sentence', 'paragraph', 'section']:
            units = self.df[self.df['unit_type'] == unit_type]
            if len(units) > 0:
                chars = units['char_count']
                words = units['word_count']
                
                # Métricas de forma de distribución
                char_skewness = chars.skew()
                char_kurtosis = chars.kurtosis()
                char_cv = chars.std() / chars.mean()  # Coeficiente de variación
                
                # Métricas de dispersión
                char_range = chars.max() - chars.min()
                char_iqr = chars.quantile(0.75) - chars.quantile(0.25)
                
                # Percentiles extendidos
                percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
                char_percentiles = [chars.quantile(p/100) for p in percentiles]
                
                print(f"\n   📊 {unit_type.upper()}S - CARACTERES:")
                print(f"      📏 Rango: {char_range} (min: {chars.min()}, max: {chars.max()})")
                print(f"      📐 Rango intercuartílico: {char_iqr:.1f}")
                print(f"      📊 Coeficiente de variación: {char_cv:.3f}")
                print(f"      📈 Asimetría (skewness): {char_skewness:.3f}", end="")
                if char_skewness > 1:
                    print(" (muy sesgada a la derecha)")
                elif char_skewness > 0.5:
                    print(" (sesgada a la derecha)")
                elif char_skewness < -1:
                    print(" (muy sesgada a la izquierda)")
                elif char_skewness < -0.5:
                    print(" (sesgada a la izquierda)")
                else:
                    print(" (aproximadamente simétrica)")
                
                print(f"      📉 Curtosis: {char_kurtosis:.3f}", end="")
                if char_kurtosis > 3:
                    print(" (leptocúrtica - más puntiaguda)")
                elif char_kurtosis < -1:
                    print(" (platicúrtica - más aplanada)")
                else:
                    print(" (aproximadamente normal)")
                
                print(f"      📊 Percentiles: ", end="")
                for i, (p, val) in enumerate(zip(percentiles, char_percentiles)):
                    if i > 0 and i % 4 == 0:
                        print(f"\n                      ", end="")
                    print(f"P{p}={val:.0f}", end=" ")
                print()
                
                # Análisis de outliers
                q1 = chars.quantile(0.25)
                q3 = chars.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = chars[(chars < lower_bound) | (chars > upper_bound)]
                
                print(f"      🎯 Outliers detectados: {len(outliers)} ({len(outliers)/len(units)*100:.1f}%)")
                if len(outliers) > 0:
                    print(f"         Valores extremos: {outliers.min():.0f} - {outliers.max():.0f}")
    
    def calculate_chunk_efficiency_metrics(self):
        """Calcula métricas de eficiencia para diferentes tamaños de chunk"""
        print(f"\n⚡ ANÁLISIS DE EFICIENCIA DE CHUNKING:")
        
        # Tamaños de chunk comunes para analizar
        chunk_sizes = [256, 512, 768, 1024, 1536, 2048]
        
        sentences = self.df[self.df['unit_type'] == 'sentence']
        paragraphs = self.df[self.df['unit_type'] == 'paragraph']
        
        if len(sentences) > 0 and len(paragraphs) > 0:
            avg_sentence = sentences['char_count'].mean()
            avg_paragraph = paragraphs['char_count'].mean()
            
            print(f"\n   📊 EFICIENCIA POR TAMAÑO DE CHUNK:")
            print(f"   {'Chunk Size':<12} {'Oraciones':<12} {'Párrafos':<12} {'Fragmentación':<15} {'Utilización':<12} {'Eficiencia':<12}")
            print(f"   {'-'*80}")
            
            for chunk_size in chunk_sizes:
                # Estimaciones basadas en oraciones
                sentences_per_chunk = chunk_size / avg_sentence
                sentence_utilization = (sentences_per_chunk % 1) * 100  # % de oración parcial
                
                # Estimaciones basadas en párrafos
                paragraphs_per_chunk = chunk_size / avg_paragraph
                paragraph_fragmentation = paragraphs_per_chunk % 1  # Fragmentación de párrafo
                
                # Métrica de eficiencia compuesta
                efficiency = (1 - paragraph_fragmentation) * (sentence_utilization / 100)
                
                print(f"   {chunk_size:<12} {sentences_per_chunk:<12.1f} {paragraphs_per_chunk:<12.1f} "
                      f"{paragraph_fragmentation:<15.3f} {sentence_utilization:<12.1f}% {efficiency:<12.3f}")
        
        # Análisis de cobertura semántica
        print(f"\n   🎯 ANÁLISIS DE COBERTURA SEMÁNTICA:")
        
        for unit_type in ['paragraph', 'section']:
            units = self.df[self.df['unit_type'] == unit_type]
            if len(units) > 0:
                median_size = units['char_count'].median()
                
                print(f"\n   📝 {unit_type.upper()}S como base de chunking:")
                for multiplier in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
                    target_size = int(median_size * multiplier)
                    coverage = len(units[units['char_count'] <= target_size]) / len(units) * 100
                    semantic_completeness = multiplier * 100  # Proxy para completitud semántica
                    
                    print(f"      📏 {target_size:4d} chars: {coverage:5.1f}% cobertura, "
                          f"{semantic_completeness:5.1f}% completitud semántica")
    
    def analyze_text_quality_metrics(self):
        """Analiza métricas de calidad del texto"""
        print(f"\n🔍 ANÁLISIS DE CALIDAD TEXTUAL:")
        
        # Análisis de longitud de palabras
        all_words = []
        all_sentences = []
        
        for idx, row in self.df.iterrows():
            words = word_tokenize(row['content'])
            all_words.extend(words)
            if row['unit_type'] == 'sentence':
                all_sentences.append(row['content'])
        
        # Métricas de palabras
        word_lengths = [len(word) for word in all_words if word.isalpha()]
        
        if word_lengths:
            print(f"\n   📝 ANÁLISIS DE PALABRAS ({len(word_lengths):,} palabras):")
            print(f"      📏 Longitud promedio: {np.mean(word_lengths):.2f} caracteres")
            print(f"      📊 Longitud mediana: {np.median(word_lengths):.1f} caracteres")
            print(f"      📈 Desviación estándar: {np.std(word_lengths):.2f}")
            print(f"      📐 Rango: {min(word_lengths)} - {max(word_lengths)} caracteres")
            
            # Distribución de longitudes de palabras
            word_length_dist = Counter(word_lengths)
            print(f"      📊 Distribución por longitud:")
            for length in sorted(word_length_dist.keys())[:10]:  # Top 10
                count = word_length_dist[length]
                pct = count / len(word_lengths) * 100
                print(f"         {length} chars: {count:,} palabras ({pct:.1f}%)")
        
        # Análisis de complejidad sintáctica
        if all_sentences:
            print(f"\n   🔤 ANÁLISIS DE COMPLEJIDAD SINTÁCTICA:")
            
            # Métricas de puntuación
            punctuation_counts = Counter()
            for sentence in all_sentences:
                for char in sentence:
                    if char in '.,;:!?()[]{}"-':
                        punctuation_counts[char] += 1
            
            total_punct = sum(punctuation_counts.values())
            total_chars = sum(len(s) for s in all_sentences)
            punct_density = total_punct / total_chars * 100
            
            print(f"      🎯 Densidad de puntuación: {punct_density:.2f}%")
            print(f"      📊 Signos más frecuentes:", end="")
            for punct, count in punctuation_counts.most_common(5):
                print(f" '{punct}':{count}", end="")
            print()
            
            # Análisis de estructura de oraciones
            sentence_complexities = []
            for sentence in all_sentences:
                # Proxy de complejidad: número de cláusulas (comas + punto y coma)
                clauses = sentence.count(',') + sentence.count(';') + 1
                words_in_sentence = len(word_tokenize(sentence))
                complexity = clauses * (words_in_sentence / clauses) if clauses > 0 else words_in_sentence
                sentence_complexities.append(complexity)
            
            if sentence_complexities:
                print(f"      🧠 Complejidad sintáctica promedio: {np.mean(sentence_complexities):.2f}")
                print(f"      📊 Distribución de complejidad:")
                complexity_percentiles = [25, 50, 75, 90, 95]
                for p in complexity_percentiles:
                    val = np.percentile(sentence_complexities, p)
                    print(f"         P{p}: {val:.1f}", end="  ")
                print()
    
    def analyze_unit_statistics(self):
        """Analiza estadísticas completas por tipo de unidad"""
        print("\n" + "="*80)
        print("📊 ESTADÍSTICAS DETALLADAS POR TIPO DE UNIDAD")
        print("="*80)
        
        # Primero ejecutar análisis adicionales
        self.calculate_additional_metrics()
        self.calculate_distribution_metrics()
        self.calculate_chunk_efficiency_metrics()
        self.analyze_text_quality_metrics()
        
        # Análisis estadístico principal mejorado
        print("\n" + "="*80)
        print("📈 ESTADÍSTICAS DESCRIPTIVAS COMPLETAS")
        print("="*80)
        
        for unit_type in ['sentence', 'paragraph', 'section']:
            units = self.df[self.df['unit_type'] == unit_type]
            if len(units) > 0:
                chars = units['char_count']
                words = units['word_count']
                
                print(f"\n🔷 {unit_type.upper()}S ({len(units):,} unidades):")
                
                # Estadísticas de caracteres
                print(f"   📏 CARACTERES:")
                print(f"      📊 Media: {chars.mean():.1f} ± {chars.std():.1f}")
                print(f"      📐 Mediana: {chars.median():.1f}")
                print(f"      📈 Moda: {chars.mode().iloc[0] if not chars.mode().empty else 'N/A'}")
                print(f"      📉 Rango: {chars.min()} - {chars.max()} (amplitud: {chars.max() - chars.min()})")
                print(f"      📊 Cuartiles: Q1={chars.quantile(0.25):.0f}, Q2={chars.median():.0f}, Q3={chars.quantile(0.75):.0f}")
                print(f"      🎯 Percentiles clave: P5={chars.quantile(0.05):.0f}, P10={chars.quantile(0.10):.0f}, "
                      f"P90={chars.quantile(0.90):.0f}, P95={chars.quantile(0.95):.0f}")
                print(f"      📏 Rango intercuartílico: {chars.quantile(0.75) - chars.quantile(0.25):.1f}")
                print(f"      📈 Coeficiente de variación: {chars.std() / chars.mean():.3f}")
                
                # Estadísticas de palabras
                print(f"   📖 PALABRAS:")
                print(f"      📊 Media: {words.mean():.1f} ± {words.std():.1f}")
                print(f"      📐 Mediana: {words.median():.1f}")
                print(f"      📉 Rango: {words.min()} - {words.max()}")
                print(f"      📊 Cuartiles: Q1={words.quantile(0.25):.0f}, Q2={words.median():.0f}, Q3={words.quantile(0.75):.0f}")
                
                # Relaciones y ratios
                char_per_word = chars / words
                print(f"   🔗 RELACIONES:")
                print(f"      📐 Caracteres por palabra: {char_per_word.mean():.2f} ± {char_per_word.std():.2f}")
                print(f"      📊 Densidad léxica: {(words / chars * 100).mean():.2f}% palabras por char")
                print(f"      🎯 Eficiencia textual: {(chars / words).mean():.2f} chars por palabra")
                
                # Análisis de forma de distribución
                char_skew = chars.skew()
                char_kurt = chars.kurtosis()
                
                print(f"   📈 FORMA DE DISTRIBUCIÓN:")
                print(f"      📊 Asimetría: {char_skew:.3f}", end="")
                if abs(char_skew) < 0.5:
                    print(" (aproximadamente simétrica)")
                elif char_skew > 0.5:
                    print(" (cola derecha larga)")
                else:
                    print(" (cola izquierda larga)")
                
                print(f"      📉 Curtosis: {char_kurt:.3f}", end="")
                if char_kurt > 0:
                    print(" (más puntiaguda que normal)")
                elif char_kurt < 0:
                    print(" (más aplanada que normal)")
                else:
                    print(" (similar a distribución normal)")
                
                # Análisis de categorización por tamaño
                print(f"   🏷️  CATEGORIZACIÓN POR TAMAÑO:")
                q1, q2, q3 = chars.quantile(0.25), chars.median(), chars.quantile(0.75)
                
                small = len(chars[chars <= q1])
                medium_small = len(chars[(chars > q1) & (chars <= q2)])
                medium_large = len(chars[(chars > q2) & (chars <= q3)])
                large = len(chars[chars > q3])
                
                print(f"      🔹 Pequeño (≤{q1:.0f}): {small} ({small/len(units)*100:.1f}%)")
                print(f"      🔸 Mediano-pequeño ({q1:.0f}-{q2:.0f}): {medium_small} ({medium_small/len(units)*100:.1f}%)")
                print(f"      🔶 Mediano-grande ({q2:.0f}-{q3:.0f}): {medium_large} ({medium_large/len(units)*100:.1f}%)")
                print(f"      🔷 Grande (>{q3:.0f}): {large} ({large/len(units)*100:.1f}%)")
                
                # Recomendaciones específicas por tipo
                print(f"   💡 RECOMENDACIONES PARA CHUNKING:")
                if unit_type == 'sentence':
                    optimal_sentences = [3, 5, 8, 12, 20]
                    for n in optimal_sentences:
                        chunk_size = int(chars.mean() * n)
                        print(f"      🎯 {n} oraciones ≈ {chunk_size} caracteres")
                elif unit_type == 'paragraph':
                    fractions = [(0.5, "1/2"), (0.75, "3/4"), (1.0, "1"), (1.5, "1.5"), (2.0, "2")]
                    for frac, desc in fractions:
                        chunk_size = int(chars.median() * frac)
                        print(f"      🎯 {desc} párrafo(s) ≈ {chunk_size} caracteres")
                else:  # sections
                    fractions = [(0.25, "1/4"), (0.5, "1/2"), (0.75, "3/4")]
                    for frac, desc in fractions:
                        chunk_size = int(chars.median() * frac)
                        print(f"      🎯 {desc} sección ≈ {chunk_size} caracteres")

    def suggest_chunk_sizes(self) -> Dict[str, List[int]]:
        """Sugiere tamaños de chunk basados en la estructura jerárquica"""
        suggestions = {}
        
        print("\n" + "="*60)
        print("SUGERENCIAS DE TAMAÑO DE CHUNK")
        print("="*60)
        
        # Basado en oraciones
        sentences = self.df[self.df['unit_type'] == 'sentence']
        if len(sentences) > 0:
            # Chunks de 3-5 oraciones, 6-10 oraciones, 11-20 oraciones
            avg_sentence_chars = sentences['char_count'].mean()
            suggestions['sentence_based'] = [
                int(avg_sentence_chars * 3),  # 3 oraciones
                int(avg_sentence_chars * 5),  # 5 oraciones
                int(avg_sentence_chars * 8),  # 8 oraciones
                int(avg_sentence_chars * 12), # 12 oraciones
                int(avg_sentence_chars * 20)  # 20 oraciones
            ]
            print(f"\nBasado en ORACIONES (media: {avg_sentence_chars:.0f} chars):")
            for i, size in enumerate(suggestions['sentence_based'], 1):
                n_sentences = size / avg_sentence_chars
                print(f"  Opción {i}: {size} chars (≈{n_sentences:.1f} oraciones)")
        
        # Basado en párrafos
        paragraphs = self.df[self.df['unit_type'] == 'paragraph']
        if len(paragraphs) > 0:
            # Chunks de 1, 2, 3 párrafos
            p25 = paragraphs['char_count'].quantile(0.25)
            median = paragraphs['char_count'].median()
            p75 = paragraphs['char_count'].quantile(0.75)
            p90 = paragraphs['char_count'].quantile(0.90)
            
            suggestions['paragraph_based'] = [
                int(p25),     # Párrafos pequeños
                int(median),  # Párrafos medianos
                int(p75),     # Párrafos grandes
                int(p90),     # Párrafos muy grandes
                int(median * 2)  # 2 párrafos medianos
            ]
            print(f"\nBasado en PÁRRAFOS:")
            print(f"  P25: {int(p25)} chars (párrafos pequeños)")
            print(f"  Mediana: {int(median)} chars (párrafos típicos)")
            print(f"  P75: {int(p75)} chars (párrafos grandes)")
            print(f"  P90: {int(p90)} chars (párrafos muy grandes)")
            print(f"  2×Mediana: {int(median * 2)} chars (2 párrafos típicos)")
        
        # Basado en secciones
        sections = self.df[self.df['unit_type'] == 'section']
        if len(sections) > 0:
            # Fracciones de sección
            s_median = sections['char_count'].median()
            s_p25 = sections['char_count'].quantile(0.25)
            
            suggestions['section_based'] = [
                int(s_p25 * 0.5),  # 1/2 de sección pequeña
                int(s_p25),        # Sección pequeña completa
                int(s_median * 0.5), # 1/2 de sección mediana
                int(s_median * 0.75), # 3/4 de sección mediana
                int(s_median)      # Sección mediana completa
            ]
            print(f"\nBasado en SECCIONES:")
            print(f"  1/2 sección pequeña: {int(s_p25 * 0.5)} chars")
            print(f"  Sección pequeña: {int(s_p25)} chars")
            print(f"  1/2 sección mediana: {int(s_median * 0.5)} chars")
            print(f"  3/4 sección mediana: {int(s_median * 0.75)} chars")
            print(f"  Sección mediana: {int(s_median)} chars")
        
        return suggestions
    
    def suggest_overlap_sizes(self, chunk_sizes: List[int]) -> Dict[str, List[Tuple[int, int]]]:
        """Sugiere tamaños de overlap específicos para cada tamaño de chunk"""
        suggestions = {}
        
        print("\n" + "="*60)
        print("SUGERENCIAS DE OVERLAP POR TAMAÑO DE CHUNK")
        print("="*60)
        
        # Obtener estadísticas de oraciones
        sentences = self.df[self.df['unit_type'] == 'sentence']
        avg_sentence_chars = sentences['char_count'].mean() if len(sentences) > 0 else 100
        
        # Para cada tamaño de chunk, calcular overlaps óptimos
        for chunk_size in chunk_sizes:
            print(f"\n📦 CHUNK DE {chunk_size} CARACTERES:")
            chunk_overlaps = []
            
            # Estrategia 1: Basado en oraciones (1-4 oraciones)
            sentence_overlaps = []
            for n_sentences in range(1, 5):
                overlap_size = int(avg_sentence_chars * n_sentences)
                if overlap_size < chunk_size * 0.4:  # Máximo 40% del chunk
                    sentence_overlaps.append((overlap_size, f"{n_sentences} oración(es)"))
                    print(f"  🔸 {n_sentences} oración(es): {overlap_size} chars ({overlap_size/chunk_size*100:.1f}% del chunk)")
            
            # Estrategia 2: Basado en porcentajes (10%, 15%, 20%, 25%)
            percentage_overlaps = []
            for pct in [10, 15, 20, 25, 30]:
                overlap_size = int(chunk_size * pct / 100)
                if overlap_size <= chunk_size * 0.35:  # Máximo 35% del chunk
                    percentage_overlaps.append((overlap_size, f"{pct}%"))
                    n_sentences_approx = overlap_size / avg_sentence_chars
                    print(f"  🔹 {pct}% del chunk: {overlap_size} chars (≈{n_sentences_approx:.1f} oraciones)")
            
            # Estrategia 3: Basado en párrafos (para chunks grandes)
            paragraph_overlaps = []
            paragraphs = self.df[self.df['unit_type'] == 'paragraph']
            if len(paragraphs) > 0 and chunk_size > 800:
                para_p25 = paragraphs['char_count'].quantile(0.25)
                para_median = paragraphs['char_count'].median()
                
                for para_fraction, desc in [(0.5, "1/2 párrafo pequeño"), (1.0, "1 párrafo pequeño"), (0.5, "1/2 párrafo mediano")]:
                    if desc == "1/2 párrafo mediano":
                        overlap_size = int(para_median * 0.5)
                    elif desc == "1 párrafo pequeño":
                        overlap_size = int(para_p25)
                    else:  # 1/2 párrafo pequeño
                        overlap_size = int(para_p25 * 0.5)
                    
                    if overlap_size < chunk_size * 0.35 and overlap_size > 50:
                        paragraph_overlaps.append((overlap_size, desc))
                        print(f"  🔺 {desc}: {overlap_size} chars ({overlap_size/chunk_size*100:.1f}% del chunk)")
            
            # Seleccionar los mejores overlaps para este chunk
            all_overlaps = sentence_overlaps + percentage_overlaps + paragraph_overlaps
            # Ordenar por tamaño y eliminar duplicados similares
            all_overlaps = sorted(set(all_overlaps), key=lambda x: x[0])
            
            # Filtrar overlaps muy similares (diferencia < 20 chars)
            filtered_overlaps = []
            for overlap, desc in all_overlaps:
                if not filtered_overlaps or overlap - filtered_overlaps[-1][0] > 20:
                    filtered_overlaps.append((overlap, desc))
            
            # Tomar los 3-5 mejores
            best_overlaps = filtered_overlaps[:5]
            suggestions[f"chunk_{chunk_size}"] = best_overlaps
            
            print(f"  ✅ Recomendados para chunk {chunk_size}:")
            for i, (overlap, desc) in enumerate(best_overlaps, 1):
                pct = overlap/chunk_size*100
                n_sent = overlap/avg_sentence_chars
                print(f"     {i}. {overlap} chars ({desc}) - {pct:.1f}% del chunk, ≈{n_sent:.1f} oraciones")
        
        return suggestions
    
    def get_optimal_chunk_overlap_pairs(self) -> List[Tuple[int, int, str]]:
        """Genera pares óptimos de (chunk_size, overlap_size, justificación)"""
        # Obtener sugerencias de chunks
        chunk_suggestions = self.suggest_chunk_sizes()
        
        # Combinar todas las sugerencias de chunks
        all_chunk_sizes = []
        for category, sizes in chunk_suggestions.items():
            all_chunk_sizes.extend(sizes)
        
        # Remover duplicados y ordenar
        unique_chunk_sizes = sorted(list(set(all_chunk_sizes)))
        
        # Seleccionar los tamaños más representativos (5-7 opciones)
        n_options = min(7, len(unique_chunk_sizes))
        selected_chunks = []
        
        if n_options > 0:
            # Distribuir uniformemente a través del rango
            for i in range(n_options):
                idx = int(i * (len(unique_chunk_sizes) - 1) / (n_options - 1))
                selected_chunks.append(unique_chunk_sizes[idx])
        
        # Obtener overlaps para cada chunk seleccionado
        overlap_suggestions = self.suggest_overlap_sizes(selected_chunks)
        
        # Generar pares óptimos
        optimal_pairs = []
        
        for chunk_size in selected_chunks:
            overlaps = overlap_suggestions.get(f"chunk_{chunk_size}", [])
            if overlaps:
                # Seleccionar el overlap más equilibrado (generalmente el 2do o 3er elemento)
                best_idx = min(1, len(overlaps) - 1)  # Preferir el segundo, o primero si solo hay uno
                best_overlap, best_desc = overlaps[best_idx]
                
                # Clasificar el tamaño del chunk
                if chunk_size < 400:
                    size_category = "pequeño"
                elif chunk_size < 800:
                    size_category = "mediano"
                else:
                    size_category = "grande"
                
                justification = f"{size_category} - {best_desc}"
                optimal_pairs.append((chunk_size, best_overlap, justification))
        
        return optimal_pairs
    
    def create_visualization(self):
        """Crea visualizaciones individuales para mejor claridad"""
        plt.style.use('seaborn-v0_8')
        
        # Variables comunes
        unit_types = ['sentence', 'paragraph', 'section']
        colors = ['lightblue', 'lightgreen', 'lightcoral']
        
        # FIGURA 1: Distribución de caracteres por tipo (boxplot)
        fig1 = plt.figure(figsize=(12, 8))
        ax1 = fig1.add_subplot(1, 1, 1)
        
        data_to_plot = []
        labels = []
        for unit_type in unit_types:
            units = self.df[self.df['unit_type'] == unit_type]
            if len(units) > 0:
                data_to_plot.append(units['char_count'].values)
                labels.append(f'{unit_type.title()}s\n(n={len(units)})')
        
        if data_to_plot:
            bp1 = ax1.boxplot(data_to_plot, tick_labels=labels, patch_artist=True)
            for patch, color in zip(bp1['boxes'], colors[:len(data_to_plot)]):
                patch.set_facecolor(color)
        
        ax1.set_title('📦 Distribución de Caracteres por Tipo de Unidad', fontsize=16, fontweight='bold')
        ax1.set_ylabel('Número de Caracteres', fontsize=12)
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('chunk_analysis_1_boxplot_distribucion.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # FIGURA 2: Histograma de párrafos con métricas estadísticas
        fig2 = plt.figure(figsize=(12, 8))
        ax2 = fig2.add_subplot(1, 1, 1)
        
        paragraphs = self.df[self.df['unit_type'] == 'paragraph']
        if len(paragraphs) > 0:
            n, bins, patches = ax2.hist(paragraphs['char_count'], bins=30, alpha=0.7, color='lightgreen', edgecolor='black')
            
            # Añadir líneas estadísticas
            median_val = paragraphs['char_count'].median()
            mean_val = paragraphs['char_count'].mean()
            p25_val = paragraphs['char_count'].quantile(0.25)
            p75_val = paragraphs['char_count'].quantile(0.75)
            
            ax2.axvline(median_val, color='red', linestyle='--', linewidth=3, label=f'Mediana: {median_val:.0f}')
            ax2.axvline(mean_val, color='blue', linestyle='--', linewidth=3, label=f'Media: {mean_val:.0f}')
            ax2.axvline(p25_val, color='orange', linestyle=':', linewidth=2, alpha=0.8, label=f'Q1: {p25_val:.0f}')
            ax2.axvline(p75_val, color='orange', linestyle=':', linewidth=2, alpha=0.8, label=f'Q3: {p75_val:.0f}')
            ax2.legend(fontsize=11)
        
        ax2.set_title('📈 Distribución Detallada de Párrafos con Métricas', fontsize=16, fontweight='bold')
        ax2.set_xlabel('Número de Caracteres', fontsize=12)
        ax2.set_ylabel('Frecuencia', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('chunk_analysis_2_histograma_paragrafos.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # FIGURA 3: Scatter plot - Relación Caracteres vs Palabras
        fig3 = plt.figure(figsize=(12, 8))
        ax3 = fig3.add_subplot(1, 1, 1)
        
        for i, unit_type in enumerate(unit_types):
            units = self.df[self.df['unit_type'] == unit_type]
            if len(units) > 0:
                ax3.scatter(units['word_count'], units['char_count'], 
                           c=colors[i], alpha=0.7, s=40, label=f'{unit_type.title()}s')
        
        ax3.set_title('🔗 Relación Caracteres vs Palabras por Tipo de Unidad', fontsize=16, fontweight='bold')
        ax3.set_xlabel('Número de Palabras', fontsize=12)
        ax3.set_ylabel('Número de Caracteres', fontsize=12)
        ax3.legend(fontsize=11)
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('chunk_analysis_3_scatter_chars_palabras.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # FIGURA 4: Distribución de longitud de palabras
        fig4 = plt.figure(figsize=(12, 8))
        ax4 = fig4.add_subplot(1, 1, 1)
        
        all_words = []
        for _, row in self.df.iterrows():
            words = word_tokenize(row['content'])
            word_lengths = [len(word) for word in words if word.isalpha()]
            all_words.extend(word_lengths)
        
        if all_words:
            word_counts = Counter(all_words)
            lengths = sorted(word_counts.keys())[:15]  # Top 15 longitudes
            counts = [word_counts[l] for l in lengths]
            
            bars = ax4.bar(lengths, counts, color='skyblue', alpha=0.8, edgecolor='navy', linewidth=1.5)
            ax4.set_title('📝 Distribución de Longitud de Palabras en el Corpus', fontsize=16, fontweight='bold')
            ax4.set_xlabel('Longitud de Palabra (caracteres)', fontsize=12)
            ax4.set_ylabel('Frecuencia', fontsize=12)
            ax4.grid(True, alpha=0.3)
            
            # Añadir valores en las barras más altas
            max_count = max(counts)
            for bar, count in zip(bars, counts):
                if count > max_count * 0.08:
                    height = bar.get_height()
                    ax4.text(bar.get_x() + bar.get_width()/2., height + max_count*0.01,
                             f'{count:,}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('chunk_analysis_4_longitud_palabras.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # FIGURA 5: Comparación de configuraciones (Actuales vs Sugeridas)
        fig5 = plt.figure(figsize=(12, 8))
        ax5 = fig5.add_subplot(1, 1, 1)
        
        current_sizes = [256, 512, 1024]
        paragraphs = self.df[self.df['unit_type'] == 'paragraph']
        
        if len(paragraphs) > 0:
            suggested_sizes = [
                int(paragraphs['char_count'].quantile(0.25)),
                int(paragraphs['char_count'].median()),
                int(paragraphs['char_count'].quantile(0.75))
            ]
        else:
            suggested_sizes = [300, 600, 900]
        
        x_pos = range(len(current_sizes))
        width = 0.35
        
        bars1 = ax5.bar([x - width/2 for x in x_pos], current_sizes, width, 
                       label='Configuración Actual', color='lightcoral', alpha=0.8, edgecolor='darkred')
        bars2 = ax5.bar([x + width/2 for x in x_pos], suggested_sizes, width, 
                       label='Configuración Sugerida', color='lightblue', alpha=0.8, edgecolor='darkblue')
        
        # Añadir valores en las barras
        for bar, value in zip(bars1, current_sizes):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height + 20,
                    f'{int(value)}', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        for bar, value in zip(bars2, suggested_sizes):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height + 20,
                    f'{int(value)}', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax5.set_title('⚖️ Comparación: Configuraciones Actuales vs Sugeridas', fontsize=16, fontweight='bold')
        ax5.set_xlabel('Tipo de Configuración', fontsize=12)
        ax5.set_ylabel('Tamaño de Chunk (caracteres)', fontsize=12)
        ax5.set_xticks(x_pos)
        ax5.set_xticklabels(['Pequeño', 'Mediano', 'Grande'])
        ax5.legend(fontsize=11)
        ax5.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('chunk_analysis_5_comparacion_configs.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # FIGURA 6: Configuraciones óptimas de chunk-overlap
        fig6 = plt.figure(figsize=(14, 8))
        ax6 = fig6.add_subplot(1, 1, 1)
        
        optimal_pairs = self.get_optimal_chunk_overlap_pairs()
        
        if optimal_pairs:
            top_configs = optimal_pairs[:7]  # Top 7 configuraciones
            chunk_sizes = [pair[0] for pair in top_configs]
            overlaps = [pair[1] for pair in top_configs]
            overlap_percentages = [(overlap/chunk)*100 for chunk, overlap in zip(chunk_sizes, overlaps)]
            
            x_pos = np.arange(len(top_configs))
            width = 0.35
            
            bars1 = ax6.bar(x_pos - width/2, chunk_sizes, width, 
                           label='Tamaño de Chunk', color='steelblue', alpha=0.8, edgecolor='navy')
            bars2 = ax6.bar(x_pos + width/2, overlaps, width, 
                           label='Tamaño de Overlap', color='darkorange', alpha=0.8, edgecolor='darkorange')
            
            # Añadir valores en las barras
            for bar, value in zip(bars1, chunk_sizes):
                height = bar.get_height()
                ax6.text(bar.get_x() + bar.get_width()/2., height + 10,
                        f'{int(value)}', ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            for bar, value in zip(bars2, overlaps):
                height = bar.get_height()
                ax6.text(bar.get_x() + bar.get_width()/2., height + 3,
                        f'{int(value)}', ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            config_labels = [f'Config {i+1}\n{pct:.1f}% overlap' for i, pct in enumerate(overlap_percentages)]
            ax6.set_xticks(x_pos)
            ax6.set_xticklabels(config_labels, fontsize=10)
            
        ax6.set_title('🎯 Top Configuraciones Óptimas de Chunk-Overlap', fontsize=16, fontweight='bold')
        ax6.set_xlabel('Configuraciones Recomendadas', fontsize=12)
        ax6.set_ylabel('Tamaño (caracteres)', fontsize=12)
        ax6.legend(fontsize=11)
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('chunk_analysis_6_configuraciones_optimas.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # FIGURA 7: Resumen completo con métricas utilizadas
        fig7 = plt.figure(figsize=(16, 10))
        ax7 = fig7.add_subplot(1, 1, 1)
        ax7.axis('off')
        
        # Crear texto de resumen completo y detallado
        total_units = len(self.df)
        total_chars = self.df['char_count'].sum()
        total_words = self.df['word_count'].sum()
        
        # Calcular métricas estadísticas clave
        sentences = self.df[self.df['unit_type'] == 'sentence']
        paragraphs = self.df[self.df['unit_type'] == 'paragraph']
        sections = self.df[self.df['unit_type'] == 'section']
        
        summary_text = f"""
📊 RESUMEN COMPLETO DEL ANÁLISIS DE CHUNKS
{'='*60}

📈 DATOS GENERALES DEL CORPUS:
   📁 Documentos analizados: {self.df['filename'].nunique()}
   📝 Total de unidades textuales: {total_units:,}
   📏 Total de caracteres: {total_chars:,}
   📖 Total de palabras: {total_words:,}
   🎯 Densidad textual promedio: {total_chars/total_units:.1f} chars/unidad
   📊 Eficiencia léxica: {total_words/total_chars*100:.2f}% (palabras por carácter)

📈 MÉTRICAS ESTADÍSTICAS UTILIZADAS EN EL ANÁLISIS:
   🔹 Medidas de tendencia central: Media aritmética, Mediana, Moda
   🔸 Medidas de dispersión: Desviación estándar, Varianza, Coeficiente de variación
   🔷 Medidas de posición: Cuartiles (Q1, Q2, Q3), Percentiles (P5, P10, P90, P95)
   🔺 Medidas de forma: Asimetría (skewness), Curtosis (kurtosis)
   🔻 Análisis de outliers: Método del rango intercuartílico (IQR)
   ⚡ Análisis de distribuciones: Histogramas, boxplots, distribuciones acumulativas

📊 DISTRIBUCIONES ESTADÍSTICAS POR TIPO DE UNIDAD:
"""
        
        if len(sentences) > 0:
            sent_mean = sentences['char_count'].mean()
            sent_std = sentences['char_count'].std()
            sent_median = sentences['char_count'].median()
            sent_skew = sentences['char_count'].skew()
            summary_text += f"""
   🔹 ORACIONES ({len(sentences):,} unidades):
      • Media: {sent_mean:.1f} ± {sent_std:.1f} caracteres
      • Mediana: {sent_median:.1f} caracteres
      • Asimetría: {sent_skew:.2f} ({'sesgada derecha' if sent_skew > 0.5 else 'aproximadamente simétrica' if abs(sent_skew) < 0.5 else 'sesgada izquierda'})
      • Rango intercuartílico: {sentences['char_count'].quantile(0.75) - sentences['char_count'].quantile(0.25):.1f}"""
        
        if len(paragraphs) > 0:
            para_mean = paragraphs['char_count'].mean()
            para_std = paragraphs['char_count'].std()
            para_median = paragraphs['char_count'].median()
            para_skew = paragraphs['char_count'].skew()
            summary_text += f"""
   🔸 PÁRRAFOS ({len(paragraphs):,} unidades):
      • Media: {para_mean:.1f} ± {para_std:.1f} caracteres
      • Mediana: {para_median:.1f} caracteres
      • Asimetría: {para_skew:.2f} ({'sesgada derecha' if para_skew > 0.5 else 'aproximadamente simétrica' if abs(para_skew) < 0.5 else 'sesgada izquierda'})
      • Rango intercuartílico: {paragraphs['char_count'].quantile(0.75) - paragraphs['char_count'].quantile(0.25):.1f}"""
        
        if len(sections) > 0:
            sect_mean = sections['char_count'].mean()
            sect_std = sections['char_count'].std()
            sect_median = sections['char_count'].median()
            sect_skew = sections['char_count'].skew()
            summary_text += f"""
   🔷 SECCIONES ({len(sections):,} unidades):
      • Media: {sect_mean:.1f} ± {sect_std:.1f} caracteres
      • Mediana: {sect_median:.1f} caracteres
      • Asimetría: {sect_skew:.2f} ({'sesgada derecha' if sect_skew > 0.5 else 'aproximadamente simétrica' if abs(sect_skew) < 0.5 else 'sesgada izquierda'})
      • Rango intercuartílico: {sections['char_count'].quantile(0.75) - sections['char_count'].quantile(0.25):.1f}"""
        
        summary_text += f"""

🎯 CONFIGURACIONES RECOMENDADAS BASADAS EN ANÁLISIS ESTADÍSTICO:
   📈 Basadas en cuartiles de párrafos:
      • Chunk pequeño (Q1): ~{int(paragraphs['char_count'].quantile(0.25)) if len(paragraphs) > 0 else 400} caracteres
      • Chunk mediano (Q2): ~{int(paragraphs['char_count'].median()) if len(paragraphs) > 0 else 600} caracteres  
      • Chunk grande (Q3): ~{int(paragraphs['char_count'].quantile(0.75)) if len(paragraphs) > 0 else 900} caracteres
   
   📊 Basadas en oraciones promedio:
      • 3-5 oraciones: ~{int(sentences['char_count'].mean() * 4) if len(sentences) > 0 else 600} caracteres
      • 8-12 oraciones: ~{int(sentences['char_count'].mean() * 10) if len(sentences) > 0 else 1500} caracteres

⚡ MÉTRICAS DE EFICIENCIA Y CALIDAD TEXTUAL:
   🔹 Densidad léxica promedio: {total_words/total_chars*100:.2f}%
   🔸 Caracteres por palabra: {total_chars/total_words:.2f}
   🔷 Palabras por unidad textual: {total_words/total_units:.1f}
   🎯 Coeficiente de eficiencia: {(total_words/total_chars) / (total_units/total_chars):.3f}

🚀 RECOMENDACIONES FINALES PARA IMPLEMENTACIÓN:
   1. Utilizar configuraciones basadas en percentiles de párrafos para mejor coherencia semántica
   2. Considerar overlap de 15-25% del tamaño del chunk para mantener contexto
   3. Priorizar chunks de ~{int(paragraphs['char_count'].median()) if len(paragraphs) > 0 else 600} caracteres (mediana de párrafos)
   4. Implementar análisis A/B testing con las configuraciones sugeridas vs actuales
"""
        
        ax7.text(0.02, 0.98, summary_text, transform=ax7.transAxes, fontsize=10,
                 verticalalignment='top', bbox=dict(boxstyle='round,pad=1', facecolor='lightblue', alpha=0.2),
                 family='monospace')
        
        plt.tight_layout()
        plt.savefig('chunk_analysis_7_resumen_completo.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"\n📊 Análisis completado - 7 figuras individuales generadas:")
        print(f"   📈 1. chunk_analysis_1_boxplot_distribucion.png - Distribución por tipos")
        print(f"   📈 2. chunk_analysis_2_histograma_paragrafos.png - Histograma con métricas")
        print(f"   📈 3. chunk_analysis_3_scatter_chars_palabras.png - Relación chars-palabras")
        print(f"   📈 4. chunk_analysis_4_longitud_palabras.png - Distribución longitud palabras")
        print(f"   📈 5. chunk_analysis_5_comparacion_configs.png - Configuraciones actuales vs sugeridas")
        print(f"   📈 6. chunk_analysis_6_configuraciones_optimas.png - Top configuraciones chunk-overlap")
        print(f"   📈 7. chunk_analysis_7_resumen_completo.png - Resumen completo con métricas utilizadas")
        print(f"📊 Total: 7 gráficos individuales enfocados y claros")

def main():
    """Función principal del analizador"""
    print("🔍 ANALIZADOR DE CHUNKS PARA LANGAGENT")
    print("="*60)
    print("Analizando documentos para encontrar tamaño de chunk y overlap óptimo")
    print("Estructura jerárquica: Sección → Párrafo → Oración")
    
    # Inicializar analizador
    analyzer = DocumentAnalyzer()
    
    # Cargar y analizar documentos
    print(f"\n📁 Cargando documentos desde '{analyzer.data_dir}'...")
    documents = analyzer.load_documents()
    
    if not documents:
        print("❌ No se encontraron documentos .md en la carpeta data/")
        return
    
    print(f"\n✅ Cargados {len(documents)} documentos")
    total_chars = sum(doc['size'] for doc in documents)
    print(f"📊 Total de caracteres: {total_chars:,}")
    
    # Analizar estructura
    print(f"\n🔬 Analizando estructura jerárquica...")
    units = analyzer.analyze_all_documents()
    
    # Optimizar chunks
    optimizer = ChunkOptimizer(units)
    optimizer.analyze_unit_statistics()
    
    # Generar sugerencias de chunks
    chunk_suggestions = optimizer.suggest_chunk_sizes()
    
    # Obtener pares óptimos de chunk-overlap
    optimal_pairs = optimizer.get_optimal_chunk_overlap_pairs()
    
    # Crear visualizaciones
    print(f"\n📈 Generando visualizaciones...")
    optimizer.create_visualization()
    
    # Recomendaciones finales
    print("\n" + "="*60)
    print("🎯 RECOMENDACIONES FINALES DE PARES CHUNK-OVERLAP")
    print("="*60)
    
    if optimal_pairs:
        print(f"\n📊 CONFIGURACIONES ÓPTIMAS ENCONTRADAS:")
        print(f"{'Rank':<6} {'Chunk Size':<12} {'Overlap':<10} {'% Overlap':<12} {'Justificación':<25}")
        print("-" * 75)
        
        for i, (chunk_size, overlap, justification) in enumerate(optimal_pairs, 1):
            overlap_pct = (overlap / chunk_size * 100)
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🔸"
            print(f"{emoji:<6} {chunk_size:<12} {overlap:<10} {overlap_pct:<11.1f}% {justification:<25}")
        
        # Destacar las top 3 recomendaciones
        print(f"\n🏆 TOP 3 RECOMENDACIONES PARA IMPLEMENTAR:")
        for i, (chunk_size, overlap, justification) in enumerate(optimal_pairs[:3], 1):
            overlap_pct = (overlap / chunk_size * 100)
            priority = "ALTA" if i == 1 else "MEDIA" if i == 2 else "BAJA"
            print(f"\n  {i}. PRIORIDAD {priority}:")
            print(f"     📏 Chunk: {chunk_size} caracteres")
            print(f"     🔗 Overlap: {overlap} caracteres ({overlap_pct:.1f}% del chunk)")
            print(f"     📝 Tipo: {justification}")
            
            # Estimación de rendimiento
            if chunk_size < 400:
                performance = "Rápido pero menos contexto"
            elif chunk_size < 800:
                performance = "Equilibrio ideal entre velocidad y contexto"
            else:
                performance = "Más contexto pero procesamiento más lento"
            print(f"     ⚡ Rendimiento: {performance}")
    
    print(f"\n💡 COMPARACIÓN CON CONFIGURACIÓN ACTUAL:")
    current_configs = [(256, 50, "pequeño"), (512, 50, "medio"), (1024, 50, "grande")]
    
    for current_chunk, current_overlap, desc in current_configs:
        # Encontrar la configuración recomendada más cercana
        if optimal_pairs:
            closest_pair = min(optimal_pairs, key=lambda x: abs(x[0] - current_chunk))
            chunk_diff = closest_pair[0] - current_chunk
            overlap_diff = closest_pair[1] - current_overlap
            overlap_improvement = (closest_pair[1] / closest_pair[0] * 100) - (current_overlap / current_chunk * 100)
            
            print(f"\n  📦 Config {desc} actual: {current_chunk} chars chunk, {current_overlap} chars overlap")
            print(f"  ✨ Recomendado: {closest_pair[0]} chars chunk, {closest_pair[1]} chars overlap")
            print(f"  📈 Mejora: {chunk_diff:+d} chars chunk, {overlap_diff:+d} chars overlap")
            print(f"  🎯 Mejor proporción: {overlap_improvement:+.1f}% de overlap respecto al chunk")
    
    # Guardar resultados en CSV
    results_df = pd.DataFrame(units)
    results_df.to_csv('chunk_analysis_results.csv', index=False)
    
    # Guardar configuraciones óptimas
    if optimal_pairs:
        optimal_configs_df = pd.DataFrame(optimal_pairs, columns=['chunk_size', 'overlap_size', 'justification'])
        optimal_configs_df['overlap_percentage'] = (optimal_configs_df['overlap_size'] / optimal_configs_df['chunk_size'] * 100).round(1)
        optimal_configs_df.to_csv('optimal_chunk_overlap_configs.csv', index=False)
        print(f"\n💾 Resultados detallados guardados en:")
        print(f"   📊 'chunk_analysis_results.csv' - Datos completos del análisis")
        print(f"   🎯 'optimal_chunk_overlap_configs.csv' - Configuraciones recomendadas")
    else:
        print(f"\n💾 Resultados guardados en 'chunk_analysis_results.csv'")
    
    print(f"\n✅ Análisis completado. Usa estos valores para optimizar tu sistema RAG!")
    
    if optimal_pairs:
        print(f"\n🚀 PASOS SIGUIENTES:")
        print(f"   1. Revisa las configuraciones en 'optimal_chunk_overlap_configs.csv'")
        print(f"   2. Implementa la configuración de PRIORIDAD ALTA primero")
        print(f"   3. Prueba y compara el rendimiento con tus configuraciones actuales")
        print(f"   4. Ajusta según los resultados específicos de tu caso de uso")

if __name__ == "__main__":
    main()