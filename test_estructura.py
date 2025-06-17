#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test de extracción de estructura del corpus"""

import re
from pathlib import Path

def test_extraction():
    # Leer un archivo de ejemplo
    with open('output_md/info_cubo_docenciaPDI_v11.md', 'r', encoding='utf-8') as f:
        text = f.read()

    print('=== PROBANDO EXTRACCIÓN DE ESTRUCTURA ===')
    print(f'Archivo total: {len(text)} chars')

    # 1. Probar extracción de SECCIONES PRINCIPALES
    medidas_match = re.search(r'=== MEDIDAS ===', text)
    dimensiones_match = re.search(r'=== DIMENSIONES ===', text)
    
    if medidas_match and dimensiones_match:
        medidas_content = text[medidas_match.start():dimensiones_match.start()].strip()
        dimensiones_content = text[dimensiones_match.start():].strip()
        
        print(f'\n📊 SECCIÓN MEDIDAS: {len(medidas_content)} chars')
        print(f'📊 SECCIÓN DIMENSIONES: {len(dimensiones_content)} chars')

    # 2. Probar extracción de dimensiones individuales CORREGIDA
    dimension_headers = list(re.finditer(r'^## DIMENSION: (.+?) ##', text, re.MULTILINE))
    
    print(f'\n🔷 DIMENSIONES INDIVIDUALES: {len(dimension_headers)} encontradas')
    for i, match in enumerate(dimension_headers[:3]):  # Solo las primeras 3
        dimension_title = match.group(1).strip()
        start_pos = match.start()
        
        # Encontrar el final de esta dimensión
        if i + 1 < len(dimension_headers):
            end_pos = dimension_headers[i + 1].start()
        else:
            end_pos = len(text)
        
        # Extraer todo el contenido de la dimensión
        dimension_content = text[start_pos:end_pos].strip()
        
        print(f'  {i+1}. {dimension_title}: {len(dimension_content)} chars')
        
        # Contar atributos dentro de esta dimensión
        attr_in_dim = len(re.findall(r'^• (.+?):', dimension_content, re.MULTILINE))
        print(f'      Atributos en esta dimensión: {attr_in_dim}')
        
        if len(dimension_content) > 500:
            print(f'      [Dimensión grande] Primeros 150 chars: {dimension_content[:150]}...')

    # 3. Probar extracción de atributos
    attribute_pattern = r'^• (.+?):\s*(.*?)(?=^• |^## |^=== |$)'
    attr_matches = list(re.finditer(attribute_pattern, text, re.MULTILINE | re.DOTALL))

    print(f'\n🔸 ATRIBUTOS INDIVIDUALES: {len(attr_matches)} encontrados')
    for i, match in enumerate(attr_matches[:5]):  # Solo los primeros 5
        attr_name = match.group(1).strip()
        attr_desc = match.group(2).strip()
        full_content = f'• {attr_name}:'
        if attr_desc:
            full_content += f'\n{attr_desc}'
        
        print(f'  {i+1}. {attr_name}: {len(full_content)} chars')
        if len(full_content) > 300:
            print(f'      [Atributo largo] Primeros 100 chars: {full_content[:100]}...')

    # 4. Verificar estructura jerárquica
    print(f'\n📈 VERIFICACIÓN DE JERARQUÍA:')
    
    # Encontrar la primera dimensión
    if dimension_headers:
        first_match = dimension_headers[0]
        start_pos = first_match.start()
        
        if len(dimension_headers) > 1:
            end_pos = dimension_headers[1].start()
        else:
            end_pos = len(text)
        
        first_dim_content = text[start_pos:end_pos].strip()
        attrs_in_first = list(re.finditer(attribute_pattern, first_dim_content, re.MULTILINE | re.DOTALL))
        
        print(f'  Primera dimensión: {len(first_dim_content)} chars')
        print(f'  Atributos dentro: {len(attrs_in_first)}')
        
        if attrs_in_first:
            avg_attr_size = sum(len(match.group(0)) for match in attrs_in_first) / len(attrs_in_first)
            print(f'  Tamaño promedio de atributo: {avg_attr_size:.1f} chars')
            
            ratio = len(first_dim_content) / avg_attr_size
            print(f'  Ratio dimensión/atributo: {ratio:.1f}x')
        
        print(f'\n📝 MUESTRA DE LA PRIMERA DIMENSIÓN:')
        print(f'   {first_dim_content[:300]}...')

if __name__ == "__main__":
    test_extraction() 