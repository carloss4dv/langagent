#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test específico para verificar extracción de dimensiones
"""

import re
from pathlib import Path

def test_dimension_extraction():
    """Test específico para una dimensión conocida"""
    
    # Leer el archivo
    with open('output_md/info_cubo_cargo_v14.md', 'r', encoding='utf-8') as f:
        text = f.read()
    
    print("🔍 TEST DE EXTRACCIÓN DE DIMENSIÓN 'CARGO'")
    print("="*60)
    
    # Encontrar todas las dimensiones ##
    dimension_pattern = r'^## (.+?)$'
    dimension_matches = list(re.finditer(dimension_pattern, text, re.MULTILINE))
    
    print(f"📊 Dimensiones encontradas: {len(dimension_matches)}")
    
    # Buscar específicamente "Cargo"
    cargo_match = None
    cargo_index = None
    
    for i, match in enumerate(dimension_matches):
        title = match.group(1).strip()
        if title == "Cargo":
            cargo_match = match
            cargo_index = i
            break
    
    if not cargo_match:
        print("❌ No se encontró la dimensión 'Cargo'")
        return
    
    print(f"\n🎯 DIMENSIÓN 'CARGO' ENCONTRADA:")
    print(f"   📍 Posición: {cargo_match.start()}")
    print(f"   📝 Título: '{cargo_match.group(1)}'")
    
    # Encontrar el final de esta dimensión
    start_pos = cargo_match.start()
    
    if cargo_index + 1 < len(dimension_matches):
        next_match = dimension_matches[cargo_index + 1]
        end_pos = next_match.start()
        next_title = next_match.group(1).strip()
        print(f"   🔚 Termina en: {end_pos} (siguiente: '{next_title}')")
    else:
        end_pos = len(text)
        print(f"   🔚 Termina en: {end_pos} (final del texto)")
    
    # Extraer contenido completo
    dimension_content = text[start_pos:end_pos].strip()
    
    # Limpiar separadores finales
    dimension_content = re.sub(r'\n---\s*$', '', dimension_content)
    
    print(f"\n📏 CONTENIDO EXTRAÍDO:")
    print(f"   📊 Tamaño: {len(dimension_content)} caracteres")
    print(f"   📖 Palabras: {len(dimension_content.split())}")
    
    print(f"\n📝 CONTENIDO COMPLETO:")
    print("=" * 40)
    print(dimension_content)
    print("=" * 40)
    
    # Verificar sub-elementos ###
    sub_elements = re.findall(r'^### (.+?)$', dimension_content, re.MULTILINE)
    print(f"\n🔸 Sub-elementos ### encontrados: {len(sub_elements)}")
    for i, sub in enumerate(sub_elements, 1):
        print(f"   {i}. {sub}")
    
    # Verificar elementos con •
    bullet_elements = re.findall(r'^• (.+?):', dimension_content, re.MULTILINE)
    print(f"\n🔹 Elementos • encontrados: {len(bullet_elements)}")
    for i, bullet in enumerate(bullet_elements, 1):
        print(f"   {i}. {bullet}")
    
    print(f"\n✅ VERIFICACIÓN:")
    expected_size = 800  # Tamaño esperado aproximado
    if len(dimension_content) > expected_size:
        print(f"   ✅ Tamaño correcto: {len(dimension_content)} chars > {expected_size}")
    else:
        print(f"   ❌ Tamaño incorrecto: {len(dimension_content)} chars < {expected_size}")
        print(f"       Posible problema en la extracción")

if __name__ == "__main__":
    test_dimension_extraction()
