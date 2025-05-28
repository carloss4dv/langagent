"""
Script de ejemplo que muestra cómo usar el módulo SQLite para consultar
información sobre la estructura del profesorado.
"""

import sys
import os
from pathlib import Path

# Añadir el directorio raíz al path para poder importar los módulos
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

# Importar funciones del módulo
from sqlite.setup_db import crear_tablas, generar_datos_prueba
from sqlite.queries import get_estructura_profesorado, get_profesores_por_categoria, get_centros
from sqlite.database import SessionLocal
from sqlite.models import PDI_Docencia

def mostrar_tabla_estructura(datos):
    """
    Muestra en formato tabla los datos de estructura del profesorado.
    
    Args:
        datos (dict): Diccionario con stats y datos de estructura
    """
    stats = datos["stats"]
    filas = datos["datos"]
    
    print("\n")
    print("=" * 100)
    print(f"ESTRUCTURA DEL PROFESORADO - CURSO {stats['curso_academico']}")
    print(f"Plan de Estudios: {stats['plan_estudio_id']} - Grado en Ingeniería Informática")
    if stats.get("centro_id"):
        print(f"Centro: {next((f['centro_nombre'] for f in filas if f.get('centro_id') == stats['centro_id']), 'Desconocido')}")
    print("=" * 100)
    
    # Encabezados
    print(f"{'CATEGORÍA':<40} | {'TOTAL':<5} | {'%':<6} | {'1ER CURSO':<9} | {'SEXENIOS':<8} | {'QUINQ.':<6} | {'HORAS':<10} | {'%':<6}")
    print("-" * 100)
    
    # Datos
    for fila in filas:
        print(f"{fila['categoria']:<40} | {fila['total']:<5} | {fila['porcentaje']:<6.2f} | "
              f"{fila['en_primer_curso']:<9} | {fila['num_sexenios']:<8} | {fila['num_quinquenios']:<6} | "
              f"{fila['horas_impartidas']:<10.1f} | {fila['porcentaje_horas']:<6.2f}")
    
    print("=" * 100)

def mostrar_profesores_categoria(profesores, categoria):
    """
    Muestra en formato tabla los profesores de una categoría.
    
    Args:
        profesores (list): Lista de diccionarios con información de profesores
        categoria (str): Nombre de la categoría
    """
    print("\n")
    print("=" * 80)
    print(f"PROFESORES DE LA CATEGORÍA: {categoria}")
    print(f"Total: {len(profesores)} profesores")
    print("=" * 80)
    
    # Encabezados
    print(f"{'ID':<4} | {'CENTRO':<30} | {'SEXENIOS':<8} | {'QUINQ.':<6} | {'HORAS':<8} | {'DOCTOR':<6} | {'PERMANENTE':<10}")
    print("-" * 80)
    
    # Datos
    for profesor in profesores:
        print(f"{profesor['id']:<4} | {profesor['centro']:<30} | {profesor['sexenios']:<8} | "
              f"{profesor['quinquenios']:<6} | {profesor['horas_impartidas']:<8.1f} | "
              f"{'Sí' if profesor['doctor'] else 'No':<6} | {'Sí' if profesor['permanente'] else 'No':<10}")
    
    print("=" * 80)

def mostrar_centros(centros):
    """
    Muestra la lista de centros disponibles.
    
    Args:
        centros (list): Lista de diccionarios con información de centros
    """
    print("\n")
    print("=" * 60)
    print("CENTROS DISPONIBLES")
    print("=" * 60)
    
    # Encabezados
    print(f"{'ID':<4} | {'NOMBRE':<40} | {'PROFESORES':<10}")
    print("-" * 60)
    
    # Datos
    for centro in centros:
        print(f"{centro['id']:<4} | {centro['nombre']:<40} | {centro['total_profesores']:<10}")
    
    print("=" * 60)

def crear_tablas_si_no_existen():
    """Crea las tablas y carga datos de prueba si no existen."""
    db = SessionLocal()
    try:
        # Verificar si ya hay datos
        count = db.query(PDI_Docencia).count()
        if count == 0:
            print("La base de datos está vacía. Creando tablas y cargando datos de prueba...")
            crear_tablas()
            generar_datos_prueba(20)
        else:
            print(f"Base de datos ya inicializada con {count} registros.")
    finally:
        db.close()

def main():
    """Función principal del script de ejemplo."""
    print("=" * 50)
    print("EJEMPLO DE USO DEL MÓDULO SQLITE PARA PDI")
    print("=" * 50)
    
    # Asegurar que la base de datos existe y tiene datos
    crear_tablas_si_no_existen()
    
    # 1. Mostrar los centros disponibles
    print("\n1. Centros disponibles:")
    centros = get_centros()
    mostrar_centros(centros)
    
    # 2. Mostrar la estructura del profesorado global
    print("\n2. Estructura global del profesorado:")
    estructura = get_estructura_profesorado()
    mostrar_tabla_estructura(estructura)
    
    # 3. Mostrar la estructura del profesorado para un centro específico
    if centros and len(centros) > 0:
        centro_id = centros[0]["id"]
        print(f"\n3. Estructura del profesorado para el centro ID {centro_id}:")
        estructura_centro = get_estructura_profesorado(centro_id=centro_id)
        mostrar_tabla_estructura(estructura_centro)
    
    # 4. Mostrar los profesores de una categoría específica
    categoria = "Cuerpo de Profesores Titulares de Universidad"
    print(f"\n4. Profesores de la categoría '{categoria}':")
    profesores = get_profesores_por_categoria(categoria)
    mostrar_profesores_categoria(profesores, categoria)
    
    print("\nEjemplo completado.")

if __name__ == "__main__":
    main() 