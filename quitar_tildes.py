#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para quitar todas las tildes y caracteres acentuados de un archivo JSON.
Autor: Script generado automáticamente
"""

import json
import unicodedata
import argparse
import os
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
        description="Quita todas las tildes y acentos de un archivo JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python quitar_tildes.py archivo.json
  python quitar_tildes.py archivo.json -o archivo_limpio.json
  python quitar_tildes.py preguntas_eval.json
        """
    )
    
    parser.add_argument(
        'input_file',
        help='Archivo JSON de entrada'
    )
    
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='Archivo JSON de salida (opcional). Si no se especifica, se añade "_sin_tildes" al nombre original.'
    )
    
    args = parser.parse_args()
    
    # Ejecutar el procesamiento
    remove_accents_from_json(args.input_file, args.output_file)

if __name__ == "__main__":
    main() 