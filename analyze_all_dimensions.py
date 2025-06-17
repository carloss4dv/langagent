#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de todas las dimensiones para ver cuáles son pequeñas
"""

import re
from pathlib import Path

def analyze_all_dimensions():
    """Analiza todas las dimensiones de un documento"""
    
    # Leer el archivo
    with open('output_md/info_cubo_cargo_v14.md', 'r', encoding='utf-8') as f:
        text = f.read()
    
    print("🔍 ANÁLISIS DE TODAS LAS DIMENSIONES")
    print("="*60)
    
    # Encontrar todas las dimensiones ##
    dimension_pattern = r'^## (.+?)$'
    dimension_matches = list(re.finditer(dimension_pattern, text, re.MULTILINE))
    
    dimensions_info = []
    
    for i, match in enumerate(dimension_matches):
        title = match.group(1).strip()
        start_pos = match.start()
        
        # Encontrar el final
        if i + 1 < len(dimension_matches):
            end_pos = dimension_matches[i + 1].start()
        else:
            # Buscar siguiente sección principal # o final del texto
            remaining_text = text[start_pos + len(match.group(0)):]
            next_section = re.search(r'^# [^#]', remaining_text, re.MULTILINE)
            if next_section:
                end_pos = start_pos + len(match.group(0)) + next_section.start()
            else:
                end_pos = len(text)
        
        # Extraer contenido
        dimension_content = text[start_pos:end_pos].strip()
        dimension_content = re.sub(r'\n---\s*$', '', dimension_content)
        
        # Contar sub-elementos
        sub_elements = len(re.findall(r'^### (.+?)$', dimension_content, re.MULTILINE))
        bullet_elements = len(re.findall(r'^• (.+?):', dimension_content, re.MULTILINE))
        
        dimensions_info.append({
            'title': title,
            'size': len(dimension_content),
            'sub_elements': sub_elements,
            'bullet_elements': bullet_elements,
            'content_preview': dimension_content[:100] + "..." if len(dimension_content) > 100 else dimension_content
        })
    
    # Ordenar por tamaño
    dimensions_info.sort(key=lambda x: x['size'])
    
    print(f"📊 Total dimensiones: {len(dimensions_info)}")
    print(f"📏 Tamaño promedio: {sum(d['size'] for d in dimensions_info) / len(dimensions_info):.1f} chars")
    
    print(f"\n🔸 DIMENSIONES MÁS PEQUEÑAS (< 200 chars):")
    small_count = 0
    for dim in dimensions_info:
        if dim['size'] < 200:
            small_count += 1
            print(f"   {small_count}. {dim['title']}: {dim['size']} chars")
            print(f"      Sub-elementos: {dim['sub_elements']}, Bullets: {dim['bullet_elements']}")
            print(f"      Preview: {dim['content_preview']}")
            print()
    
    print(f"\n🔷 DIMENSIONES GRANDES (> 500 chars):")
    large_count = 0
    for dim in reversed(dimensions_info):  # Ordenar de mayor a menor
        if dim['size'] > 500:
            large_count += 1
            print(f"   {large_count}. {dim['title']}: {dim['size']} chars")
            print(f"      Sub-elementos: {dim['sub_elements']}, Bullets: {dim['bullet_elements']}")
            print(f"      Preview: {dim['content_preview']}")
            print()
    
    print(f"\n📈 ESTADÍSTICAS:")
    sizes = [d['size'] for d in dimensions_info]
    print(f"   📏 Mínimo: {min(sizes)} chars")
    print(f"   📐 Máximo: {max(sizes)} chars")
    print(f"   📊 Mediana: {sorted(sizes)[len(sizes)//2]} chars")
    print(f"   🔸 Pequeñas (< 200): {sum(1 for s in sizes if s < 200)}")
    print(f"   🔹 Medianas (200-500): {sum(1 for s in sizes if 200 <= s <= 500)}")
    print(f"   🔷 Grandes (> 500): {sum(1 for s in sizes if s > 500)}")

if __name__ == "__main__":
    analyze_all_dimensions()
