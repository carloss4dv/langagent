"""
Script para inicializar la base de datos SQLite y cargar datos de prueba.
"""

import os
import sys
import random
from decimal import Decimal
from pathlib import Path

# Añadir el directorio raíz al path para poder importar los módulos
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from sqlite.database import engine, SessionLocal, Base
from sqlite.models import PDI_Docencia

# Categorías de profesorado
CATEGORIAS_PDI = [
    "Cuerpo de Profesores Titulares de Universidad",
    "Cuerpo de Catedráticos de Universidad",
    "Profesor contratado doctor",
    "Profesor colaborador",
    "Profesor permanente laboral",
    "Profesor ayudante doctor",
    "Cuerpo de Profesores Titulares de Escuelas Universitarias",
    "Personal investigador en formación",
    "Profesor con contrato de interinidad",
    "Personal docente, investigador o técnico",
    "Profesor sustituto"
]

# Centros
CENTROS = [
    {"id": 1, "nombre": "Escuela de Ingeniería y Arquitectura"},
    {"id": 2, "nombre": "Escuela Universitaria Politécnica de Teruel"}
]

def crear_tablas():
    """Crea todas las tablas definidas en los modelos."""
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente.")

def generar_datos_prueba(total_registros=20):
    """
    Genera datos de prueba para la tabla PDI_Docencia.
    
    Args:
        total_registros: Número de registros a generar
    """
    db = SessionLocal()
    
    try:
        # Limpiar datos existentes
        db.query(PDI_Docencia).delete()
        db.commit()
        
        # Generar nuevos datos
        registros = []
        for i in range(1, total_registros + 1):
            # Seleccionar centro aleatoriamente
            centro = random.choice(CENTROS)
            
            # Datos aleatorios
            categoria = random.choice(CATEGORIAS_PDI)
            sexenios = random.randint(0, 6)
            quinquenios = random.randint(0, 8)
            
            # Más probabilidad de permanente y doctor para categorías superiores
            if "Catedrático" in categoria or "Titular" in categoria:
                permanente = 'S'
                doctor = 'S'
                horas = Decimal(str(round(random.uniform(150.0, 300.0), 2)))
            elif "contratado doctor" in categoria or "colaborador" in categoria:
                permanente = 'S'
                doctor = 'S' if random.random() > 0.2 else 'N'
                horas = Decimal(str(round(random.uniform(100.0, 250.0), 2)))
            else:
                permanente = 'N'
                doctor = 'S' if random.random() > 0.5 else 'N'
                horas = Decimal(str(round(random.uniform(30.0, 150.0), 2)))
            
            # Crear registro
            registro = PDI_Docencia(
                id=i,
                categoria_pdi=categoria,
                centro_id=centro["id"],
                centro_nombre=centro["nombre"],
                plan_estudio_id=148,  # Grado en Ingeniería Informática
                curso_academico="2024/2025",
                curso=random.choice([1, 2, 3, 4, None]),
                sexenios=sexenios,
                quinquenios=quinquenios,
                horas_impartidas=horas,
                permanente=permanente,
                doctor=doctor
            )
            
            registros.append(registro)
        
        # Insertar todos los registros
        db.add_all(registros)
        db.commit()
        print(f"Se han generado {total_registros} registros de prueba.")
        
    except Exception as e:
        db.rollback()
        print(f"Error al generar datos de prueba: {e}")
    finally:
        db.close()

def consulta_ejemplo():
    """Ejecuta una consulta de ejemplo similar a la web de Unizar."""
    db = SessionLocal()
    
    try:
        # Consulta SQL usando SQLAlchemy
        from sqlalchemy import func, desc
        
        # Total de registros para calcular porcentajes
        total_pdi = db.query(func.count(PDI_Docencia.id)).filter(
            PDI_Docencia.plan_estudio_id == 148,
            PDI_Docencia.curso_academico == "2024/2025"
        ).scalar()
        
        total_horas = db.query(func.sum(PDI_Docencia.horas_impartidas)).filter(
            PDI_Docencia.plan_estudio_id == 148,
            PDI_Docencia.curso_academico == "2024/2025"
        ).scalar()
        
        # Consulta principal
        resultados = db.query(
            PDI_Docencia.categoria_pdi,
            func.count(PDI_Docencia.id).label("total"),
            (func.count(PDI_Docencia.id) * 100.0 / total_pdi).label("porcentaje"),
            func.sum(func.case(
                [(PDI_Docencia.curso == 1, 1)],
                else_=0
            )).label("en_primer_curso"),
            func.sum(PDI_Docencia.sexenios).label("num_sexenios"),
            func.sum(PDI_Docencia.quinquenios).label("num_quinquenios"),
            func.sum(PDI_Docencia.horas_impartidas).label("horas_impartidas"),
            (func.sum(PDI_Docencia.horas_impartidas) * 100.0 / total_horas).label("porcentaje_horas")
        ).filter(
            PDI_Docencia.plan_estudio_id == 148,
            PDI_Docencia.curso_academico == "2024/2025"
        ).group_by(
            PDI_Docencia.categoria_pdi
        ).order_by(
            desc("horas_impartidas")
        ).all()
        
        # Mostrar resultados
        print("\n--- ESTRUCTURA DEL PROFESORADO 2024/2025 ---")
        print("Estudio: Grado en Ingeniería Informática")
        print(f"Total personal académico: {total_pdi}")
        print("-" * 60)
        print(f"{'Categoría':<40} | {'Total':<5} | {'%':<6} | {'1er curso':<9} | {'Sexenios':<8} | {'Quinq.':<6} | {'Horas':<10} | {'%':<6}")
        print("-" * 60)
        
        for r in resultados:
            print(f"{r.categoria_pdi:<40} | {r.total:<5} | {r.porcentaje:.2f} | {r.en_primer_curso:<9} | {r.num_sexenios:<8} | {r.num_quinquenios:<6} | {r.horas_impartidas:<10.1f} | {r.porcentaje_horas:.2f}")
            
    except Exception as e:
        print(f"Error al ejecutar consulta de ejemplo: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Crear tablas si no existen
    crear_tablas()
    
    # Generar datos de prueba
    generar_datos_prueba(20)
    
    # Ejecutar consulta de ejemplo
    consulta_ejemplo() 