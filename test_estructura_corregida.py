#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test para verificar la extracción correcta de la estructura semántica CORREGIDA
"""

import os
from pathlib import Path
from chunk_analyzer_v2 import CorpusAnalyzer

def test_estructura_documento():
    """Test de extracción de estructura de un documento específico"""
    
    # Usar el archivo actual del editor
    test_file = Path("output_md/info_cubo_cargo_v14.md")
    
    if not test_file.exists():
        print(f"❌ Archivo no encontrado: {test_file}")
        return
    
    # Leer contenido
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"🔍 ANALIZANDO ESTRUCTURA CORREGIDA DE: {test_file.name}")
    print(f"📄 Tamaño total: {len(content)} caracteres")
    print("="*70)
    
    # Inicializar analizador
    analyzer = CorpusAnalyzer()
    
    # Extraer elementos semánticos
    main_sections = analyzer.extract_main_sections(content)
    dimensions = analyzer.extract_dimensions(content)
    attributes = analyzer.extract_attributes(content)
    
    # Mostrar resultados
    print(f"\n📊 RESUMEN DE EXTRACCIÓN:")
    print(f"   🔷 Secciones principales: {len(main_sections)}")
    print(f"   🔹 Dimensiones/Medidas: {len(dimensions)}")
    print(f"   🔸 Atributos/Elementos: {len(attributes)}")
    
    if main_sections:
        print(f"\n🔷 SECCIONES PRINCIPALES:")
        for i, section in enumerate(main_sections, 1):
            print(f"   {i}. {section.context_info}")
            print(f"      📏 {section.char_count} chars, {section.word_count} palabras")
            print(f"      📝 Inicio: {section.content[:100]}...")
    
    if dimensions:
        print(f"\n🔹 DIMENSIONES/MEDIDAS (primeras 10):")
        for i, dim in enumerate(dimensions[:10], 1):
            print(f"   {i}. {dim.context_info}")
            print(f"      📏 {dim.char_count} chars, {dim.word_count} palabras")
            print(f"      📝 Inicio: {dim.content[:80]}...")
    
    if attributes:
        print(f"\n🔸 ATRIBUTOS/ELEMENTOS (primeros 10):")
        for i, attr in enumerate(attributes[:10], 1):
            print(f"   {i}. {attr.context_info}")
            print(f"      📏 {attr.char_count} chars, {attr.word_count} palabras")
            print(f"      📝 Contenido: {attr.content[:80]}...")
    
    # Verificar proporciones
    if main_sections and dimensions and attributes:
        avg_section = sum(s.char_count for s in main_sections) / len(main_sections)
        avg_dimension = sum(d.char_count for d in dimensions) / len(dimensions)
        avg_attribute = sum(a.char_count for a in attributes) / len(attributes)
        
        print(f"\n📊 ANÁLISIS DE PROPORCIONES:")
        print(f"   🔷 Sección promedio: {avg_section:.1f} chars")
        print(f"   🔹 Dimensión promedio: {avg_dimension:.1f} chars")
        print(f"   🔸 Atributo promedio: {avg_attribute:.1f} chars")
        
        if avg_dimension > 0 and avg_attribute > 0:
            ratio_sec_dim = avg_section / avg_dimension
            ratio_dim_attr = avg_dimension / avg_attribute
            print(f"   📈 Ratio Sección/Dimensión: {ratio_sec_dim:.1f}x")
            print(f"   📈 Ratio Dimensión/Atributo: {ratio_dim_attr:.1f}x")
            
            print(f"\n✅ VALIDACIÓN:")
            if ratio_sec_dim > 2 and ratio_dim_attr > 1.5:
                print(f"   ✅ Proporciones correctas: Sección > Dimensión > Atributo")
            else:
                print(f"   ⚠️  Proporciones pueden necesitar ajuste")
    
    # Ejemplo de cada tipo
    print(f"\n📝 EJEMPLOS DE CADA TIPO:")
    if main_sections:
        print(f"\n🔷 EJEMPLO SECCIÓN:")
        print(f"{main_sections[0].content[:200]}...")
        
    if dimensions:
        print(f"\n🔹 EJEMPLO DIMENSIÓN:")
        print(f"{dimensions[0].content[:200]}...")
        
    if attributes:
        print(f"\n🔸 EJEMPLO ATRIBUTO:")
        print(f"{attributes[0].content}")

if __name__ == "__main__":
    test_estructura_documento()
