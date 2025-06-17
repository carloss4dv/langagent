#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para quitar todas las tildes y caracteres acentuados de archivos PlantUML.
Este script procesa todos los archivos .puml en el directorio diagrams/
para evitar problemas de codificación al generar los diagramas.

Autor: Script generado automáticamente
"""

import os
import unicodedata
import argparse
import shutil
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

def process_puml_file(file_path, backup=True):
    """
    Procesa un archivo PlantUML para quitar tildes.
    
    Args:
        file_path (str): Ruta del archivo PlantUML
        backup (bool): Si crear una copia de seguridad del archivo original
    
    Returns:
        bool: True si el archivo fue procesado exitosamente
    """
    try:
        print(f"Procesando: {file_path}")
        
        # Crear backup si se solicita
        if backup:
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)
            print(f"  ✓ Backup creado: {backup_path}")
        
        # Leer el archivo
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Procesar el contenido para quitar tildes
        processed_content = remove_accents(content)
        
        # Verificar si hubo cambios
        if content != processed_content:
            # Guardar el archivo procesado
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            print(f"  ✓ Archivo actualizado (tildes eliminadas)")
        else:
            print(f"  ✓ Sin cambios necesarios")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error al procesar {file_path}: {e}")
        return False

def process_diagrams_directory(diagrams_dir, backup=True, file_pattern="*.puml"):
    """
    Procesa todos los archivos PlantUML en un directorio.
    
    Args:
        diagrams_dir (str): Directorio que contiene los diagramas
        backup (bool): Si crear copias de seguridad
        file_pattern (str): Patrón de archivos a procesar
    
    Returns:
        dict: Estadísticas del procesamiento
    """
    diagrams_path = Path(diagrams_dir)
    
    if not diagrams_path.exists():
        print(f"❌ El directorio {diagrams_dir} no existe.")
        return {"success": 0, "failed": 0, "total": 0}
    
    # Buscar archivos PlantUML
    puml_files = list(diagrams_path.glob(file_pattern))
    
    if not puml_files:
        print(f"❌ No se encontraron archivos {file_pattern} en {diagrams_dir}")
        return {"success": 0, "failed": 0, "total": 0}
    
    print(f"Encontrados {len(puml_files)} archivos PlantUML para procesar:")
    print("-" * 60)
    
    # Procesar cada archivo
    success_count = 0
    failed_count = 0
    
    for puml_file in puml_files:
        if process_puml_file(str(puml_file), backup):
            success_count += 1
        else:
            failed_count += 1
    
    print("-" * 60)
    print(f"✅ Procesamiento completado:")
    print(f"   Total archivos: {len(puml_files)}")
    print(f"   Exitosos: {success_count}")
    print(f"   Fallidos: {failed_count}")
    
    if backup and success_count > 0:
        print(f"\n💾 Se crearon archivos de backup con extensión .backup")
        print(f"   Para restaurar: mv archivo.puml.backup archivo.puml")
    
    return {"success": success_count, "failed": failed_count, "total": len(puml_files)}

def restore_from_backup(diagrams_dir):
    """
    Restaura todos los archivos desde sus backups.
    
    Args:
        diagrams_dir (str): Directorio que contiene los diagramas
    """
    diagrams_path = Path(diagrams_dir)
    backup_files = list(diagrams_path.glob("*.puml.backup"))
    
    if not backup_files:
        print("❌ No se encontraron archivos de backup.")
        return
    
    print(f"Restaurando {len(backup_files)} archivos desde backup:")
    print("-" * 60)
    
    for backup_file in backup_files:
        original_file = backup_file.with_suffix('')
        try:
            shutil.copy2(str(backup_file), str(original_file))
            print(f"  ✓ Restaurado: {original_file.name}")
        except Exception as e:
            print(f"  ❌ Error restaurando {original_file.name}: {e}")
    
    print("-" * 60)
    print("✅ Restauración completada")

def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Quita todas las tildes y acentos de archivos PlantUML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python remove_accents_diagrams.py
  python remove_accents_diagrams.py --no-backup
  python remove_accents_diagrams.py --restore
  python remove_accents_diagrams.py --dir "mi_directorio_diagramas"
        """
    )
    
    parser.add_argument(
        '--dir',
        default='diagrams',
        help='Directorio que contiene los archivos PlantUML (por defecto: diagrams)'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='No crear archivos de backup antes de procesar'
    )
    
    parser.add_argument(
        '--restore',
        action='store_true',
        help='Restaurar archivos desde backup (restaura todos los .puml.backup encontrados)'
    )
    
    parser.add_argument(
        '--pattern',
        default='*.puml',
        help='Patrón de archivos a procesar (por defecto: *.puml)'
    )
    
    args = parser.parse_args()
    
    # Ejecutar acción solicitada
    if args.restore:
        restore_from_backup(args.dir)
    else:
        backup = not args.no_backup
        process_diagrams_directory(args.dir, backup, args.pattern)

if __name__ == "__main__":
    main()
