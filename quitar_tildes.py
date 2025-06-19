#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para quitar todas las tildes y caracteres acentuados de archivos JSON y diagramas PlantUML.
Autor: Script generado automáticamente
"""

import json
import unicodedata
import argparse
import os
import glob
from pathlib import Path

def remove_accents(text):
    """
    Elimina todas las tildes y caracteres acentuados de un texto.
    
    Args:
        text (str): Texto con posibles tildes y acentos
    
    Returns:
        str: Texto sin tildes ni acentos
    """
    if not isinstance(text, str):
        return text
    
    # Normalizar el texto usando NFD (Normalization Form Decomposed)
    # Esto separa los caracteres base de sus marcas diacríticas (tildes, acentos)
    normalized = unicodedata.normalize('NFD', text)
    
    # Filtrar solo los caracteres que no son marcas diacríticas
    # La categoría 'Mn' corresponde a las marcas diacríticas
    without_accents = ''.join(char for char in normalized 
                              if unicodedata.category(char) != 'Mn')
    
    return without_accents

def process_json_data(data):
    """
    Procesa recursivamente un objeto JSON para quitar tildes de todos los strings.
    
    Args:
        data: Objeto JSON (dict, list, str, etc.)
    
    Returns:
        Objeto JSON procesado sin tildes
    """
    if isinstance(data, dict):
        return {key: process_json_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [process_json_data(item) for item in data]
    elif isinstance(data, str):
        return remove_accents(data)
    else:
        return data

def remove_accents_from_puml(input_file, output_file=None):
    """
    Quita todas las tildes de un archivo PlantUML.
    
    Args:
        input_file (str): Ruta del archivo PUML de entrada
        output_file (str, optional): Ruta del archivo PUML de salida. 
                                   Si no se especifica, sobrescribe el archivo original.
    """
    try:
        # Verificar que el archivo de entrada existe
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"El archivo {input_file} no existe.")
        
        # Leer el archivo PUML
        print(f"Leyendo archivo: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Procesar el contenido para quitar tildes
        print("Procesando contenido para quitar tildes...")
        processed_content = remove_accents(content)
        
        # Determinar el archivo de salida
        if output_file is None:
            output_file = input_file  # Sobrescribir el archivo original
        
        # Guardar el archivo procesado
        print(f"Guardando archivo procesado: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        print(f"✅ Archivo PUML procesado exitosamente: {output_file}")
        
        return output_file
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error inesperado procesando {input_file}: {e}")

def process_all_puml_files(diagrams_dir="diagrams"):
    """
    Procesa todos los archivos .puml en el directorio de diagramas.
    
    Args:
        diagrams_dir (str): Directorio que contiene los archivos .puml
    """
    if not os.path.exists(diagrams_dir):
        print(f"❌ El directorio {diagrams_dir} no existe.")
        return
    
    # Buscar todos los archivos .puml
    puml_pattern = os.path.join(diagrams_dir, "*.puml")
    puml_files = glob.glob(puml_pattern)
    
    if not puml_files:
        print(f"No se encontraron archivos .puml en {diagrams_dir}")
        return
    
    print(f"\n🔄 Procesando {len(puml_files)} archivos .puml...")
    
    processed_count = 0
    for puml_file in puml_files:
        print(f"\nProcesando: {os.path.basename(puml_file)}")
        result = remove_accents_from_puml(puml_file)
        if result:
            processed_count += 1
    
    print(f"\n✅ Se procesaron {processed_count} de {len(puml_files)} archivos .puml")

def remove_accents_from_json(input_file, output_file=None):
    """
    Quita todas las tildes de un archivo JSON.
    
    Args:
        input_file (str): Ruta del archivo JSON de entrada
        output_file (str, optional): Ruta del archivo JSON de salida. 
                                   Si no se especifica, se añade '_sin_tildes' al nombre original.
    """
    try:
        # Verificar que el archivo de entrada existe
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"El archivo {input_file} no existe.")
        
        # Leer el archivo JSON
        print(f"Leyendo archivo: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Procesar los datos para quitar tildes
        print("Procesando datos para quitar tildes...")
        processed_data = process_json_data(data)
        
        # Determinar el archivo de salida
        if output_file is None:
            input_path = Path(input_file)
            output_file = input_path.parent / f"{input_path.stem}_sin_tildes{input_path.suffix}"
        
        # Guardar el archivo procesado
        print(f"Guardando archivo procesado: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Proceso completado exitosamente!")
        print(f"   Archivo original: {input_file}")
        print(f"   Archivo sin tildes: {output_file}")
        
        return output_file
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Error al leer el JSON: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Quita todas las tildes y acentos de archivos JSON y diagramas PlantUML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  # Procesar un archivo JSON específico:
  python quitar_tildes.py archivo.json
  python quitar_tildes.py archivo.json -o archivo_limpio.json
  python quitar_tildes.py preguntas_eval.json
  
  # Procesar todos los diagramas .puml:
  python quitar_tildes.py --puml
  python quitar_tildes.py --puml -d ruta/a/diagramas
  
  # Procesar tanto JSON como diagramas:
  python quitar_tildes.py preguntas_eval.json --puml
        """
    )
    
    parser.add_argument(
        'input_file',
        nargs='?',
        help='Archivo JSON de entrada (opcional si solo se procesan diagramas)'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='Archivo JSON de salida (opcional). Si no se especifica, se añade "_sin_tildes" al nombre original.'
    )
    
    parser.add_argument(
        '--puml',
        action='store_true',
        help='Procesar todos los archivos .puml en el directorio de diagramas'
    )
    
    parser.add_argument(
        '-d', '--diagrams-dir',
        dest='diagrams_dir',
        default='diagrams',
        help='Directorio que contiene los archivos .puml (por defecto: diagrams)'
    )
    
    args = parser.parse_args()
    
    # Validar argumentos
    if not args.input_file and not args.puml:
        parser.error("Debe especificar un archivo JSON o usar --puml para procesar diagramas")
    
    # Procesar archivo JSON si se especifica
    if args.input_file:
        print("📄 Procesando archivo JSON...")
        remove_accents_from_json(args.input_file, args.output_file)
    
    # Procesar archivos PUML si se solicita
    if args.puml:
        print("📊 Procesando diagramas PlantUML...")
        process_all_puml_files(args.diagrams_dir)
    
    print("\n🎉 ¡Proceso completado!")

if __name__ == "__main__":
    main()