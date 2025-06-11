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
        
    def analyze_unit_statistics(self):
        """Analiza estadísticas por tipo de unidad"""
        print("\n" + "="*60)
        print("ESTADÍSTICAS POR TIPO DE UNIDAD")
        print("="*60)
        
        for unit_type in ['sentence', 'paragraph', 'section']:
            units = self.df[self.df['unit_type'] == unit_type]
            if len(units) > 0:
                print(f"\n{unit_type.upper()}S:")
                print(f"  Cantidad: {len(units)}")
                print(f"  Caracteres - Media: {units['char_count'].mean():.1f}, "
                      f"Mediana: {units['char_count'].median():.1f}, "
                      f"Std: {units['char_count'].std():.1f}")
                print(f"  Palabras - Media: {units['word_count'].mean():.1f}, "
                      f"Mediana: {units['word_count'].median():.1f}, "
                      f"Std: {units['word_count'].std():.1f}")
                print(f"  Percentiles (chars): P25={units['char_count'].quantile(0.25):.0f}, "
                      f"P75={units['char_count'].quantile(0.75):.0f}, "
                      f"P90={units['char_count'].quantile(0.90):.0f}")
    
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
        """Crea visualizaciones de la distribución de tamaños"""
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Análisis de Distribución de Texto por Unidades', fontsize=16, fontweight='bold')
        
        # Distribución de caracteres por tipo
        ax1 = axes[0, 0]
        unit_types = ['sentence', 'paragraph', 'section']
        colors = ['lightblue', 'lightgreen', 'lightcoral']
        
        data_to_plot = []
        labels = []
        for unit_type in unit_types:
            units = self.df[self.df['unit_type'] == unit_type]
            if len(units) > 0:
                data_to_plot.append(units['char_count'].values)
                labels.append(f'{unit_type.title()}s\n(n={len(units)})')
        
        if data_to_plot:
            bp1 = ax1.boxplot(data_to_plot, labels=labels, patch_artist=True)
            for patch, color in zip(bp1['boxes'], colors[:len(data_to_plot)]):
                patch.set_facecolor(color)
        
        ax1.set_title('Distribución de Caracteres por Tipo de Unidad')
        ax1.set_ylabel('Número de Caracteres')
        ax1.tick_params(axis='x', rotation=45)
        
        # Histograma de párrafos (más relevante para chunks)
        ax2 = axes[0, 1]
        paragraphs = self.df[self.df['unit_type'] == 'paragraph']
        if len(paragraphs) > 0:
            ax2.hist(paragraphs['char_count'], bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
            ax2.axvline(paragraphs['char_count'].median(), color='red', linestyle='--', 
                       label=f'Mediana: {paragraphs["char_count"].median():.0f}')
            ax2.axvline(paragraphs['char_count'].mean(), color='blue', linestyle='--', 
                       label=f'Media: {paragraphs["char_count"].mean():.0f}')
            ax2.legend()
        
        ax2.set_title('Distribución de Tamaño de Párrafos')
        ax2.set_xlabel('Número de Caracteres')
        ax2.set_ylabel('Frecuencia')
        
        # Comparación de tamaños actuales vs sugeridos
        ax3 = axes[1, 0]
        current_sizes = [256, 512, 1024]
        
        # Calcular sugerencias rápidas
        if len(paragraphs) > 0:
            suggested_sizes = [
                int(paragraphs['char_count'].quantile(0.25)),
                int(paragraphs['char_count'].median()),
                int(paragraphs['char_count'].quantile(0.75)),
                int(paragraphs['char_count'].median() * 2)
            ]
        else:
            suggested_sizes = [300, 600, 900, 1200]
        
        x_pos = range(len(current_sizes))
        ax3.bar([x - 0.2 for x in x_pos], current_sizes, 0.4, label='Actuales', color='lightcoral')
        ax3.bar([x + 0.2 for x in x_pos[:len(suggested_sizes)]], suggested_sizes[:len(current_sizes)], 0.4, 
               label='Sugeridos', color='lightblue')
        
        ax3.set_title('Comparación: Tamaños Actuales vs Sugeridos')
        ax3.set_xlabel('Configuración')
        ax3.set_ylabel('Tamaño de Chunk (caracteres)')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels([f'Config {i+1}' for i in x_pos])
        ax3.legend()
        
        # Comparación de configuraciones óptimas
        ax4 = axes[1, 1]
        
        # Obtener pares óptimos para mostrar
        optimal_pairs = self.get_optimal_chunk_overlap_pairs()
        
        if optimal_pairs:
            # Tomar las top 5 configuraciones
            top_configs = optimal_pairs[:5]
            chunk_sizes = [pair[0] for pair in top_configs]
            overlaps = [pair[1] for pair in top_configs]
            overlap_percentages = [(overlap/chunk)*100 for chunk, overlap in zip(chunk_sizes, overlaps)]
            
            # Crear gráfico de barras doble
            x_pos = np.arange(len(top_configs))
            width = 0.35
            
            bars1 = ax4.bar(x_pos - width/2, chunk_sizes, width, label='Tamaño de Chunk', color='lightblue', alpha=0.8)
            bars2 = ax4.bar(x_pos + width/2, overlaps, width, label='Tamaño de Overlap', color='lightcoral', alpha=0.8)
            
            # Añadir valores en las barras
            for bar, value in zip(bars1, chunk_sizes):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 20,
                        f'{int(value)}', ha='center', va='bottom', fontsize=8)
            
            for bar, value in zip(bars2, overlaps):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 5,
                        f'{int(value)}', ha='center', va='bottom', fontsize=8)
            
            # Configurar labels
            config_labels = [f'Config {i+1}\n({pct:.1f}%)' for i, pct in enumerate(overlap_percentages)]
            ax4.set_xticks(x_pos)
            ax4.set_xticklabels(config_labels)
            
        ax4.set_title('Top 5 Configuraciones Óptimas Chunk-Overlap')
        ax4.set_xlabel('Configuración (% overlap)')
        ax4.set_ylabel('Tamaño (caracteres)')
        ax4.legend()
        ax4.tick_params(axis='x', rotation=0)
        
        plt.tight_layout()
        plt.savefig('chunk_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"\n📊 Gráfico guardado como 'chunk_analysis.png'")

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