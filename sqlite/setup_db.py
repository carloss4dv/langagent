"""
Configuración y inicialización de la base de datos SQLite para PDI.

Este módulo crea las tablas necesarias y carga datos de ejemplo
para el sistema de información del Personal Docente e Investigador.
"""

import sqlite3
import random
from typing import List, Dict
import os

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

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

def crear_tablas(db_path: str = "pdi_database.db"):
    """
    Crea las tablas necesarias en la base de datos.
    
    Args:
        db_path: Ruta del archivo de base de datos
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Crear tabla de centros
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS centros (
        id INTEGER PRIMARY KEY,
        nombre TEXT NOT NULL,
        descripcion TEXT
    )
    ''')
    
    # Crear tabla de profesores
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profesores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        centro_id INTEGER NOT NULL,
        categoria_pdi TEXT NOT NULL,
        es_doctor INTEGER NOT NULL,
        es_permanente INTEGER NOT NULL,
        num_sexenios INTEGER DEFAULT 0,
        num_quinquenios INTEGER DEFAULT 0,
        horas_impartidas REAL DEFAULT 0,
        imparte_primer_curso INTEGER DEFAULT 0,
        curso_academico TEXT DEFAULT '2024/2025',
        plan_estudio_id INTEGER DEFAULT 6037,
        FOREIGN KEY (centro_id) REFERENCES centros (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info("Tablas creadas correctamente.")

def generar_datos_ejemplo(db_path: str = "pdi_database.db", num_profesores: int = 100):
    """
    Genera datos de ejemplo para las tablas.
    
    Args:
        db_path: Ruta del archivo de base de datos
        num_profesores: Número de profesores a generar
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Insertar centros de ejemplo
        centros = [
            (148, "Escuela Técnica Superior de Ingeniería Informática", "Centro principal de informática"),
            (149, "Facultad de Ciencias", "Centro de ciencias básicas"),
            (150, "Escuela Politécnica Superior", "Centro de ingenierías")
        ]
        
        cursor.executemany('INSERT OR REPLACE INTO centros (id, nombre, descripcion) VALUES (?, ?, ?)', centros)
        
        # Categorías de PDI con sus distribuciones aproximadas
        categorias = [
            ("Catedrático de Universidad", 0.08),
            ("Profesor Titular de Universidad", 0.25),
            ("Profesor Contratado Doctor", 0.15),
            ("Profesor Ayudante Doctor", 0.12),
            ("Profesor Asociado", 0.25),
            ("Profesor Sustituto Interino", 0.10),
            ("Otros", 0.05)
        ]
        
        # Generar profesores
        profesores = []
        total_registros = 0
        
        for _ in range(num_profesores):
            centro_id = random.choice([148, 149, 150])
            categoria = random.choices([cat[0] for cat in categorias], 
                                     weights=[cat[1] for cat in categorias])[0]
            
            # Configurar probabilidades según la categoría
            if categoria in ["Catedrático de Universidad", "Profesor Titular de Universidad"]:
                es_doctor = 1
                es_permanente = 1
                sexenios = random.randint(1, 6)
                quinquenios = random.randint(2, 8)
                horas = random.uniform(120, 240)
            elif categoria == "Profesor Contratado Doctor":
                es_doctor = 1
                es_permanente = random.choice([0, 1])
                sexenios = random.randint(0, 3)
                quinquenios = random.randint(0, 4)
                horas = random.uniform(180, 240)
            elif categoria == "Profesor Ayudante Doctor":
                es_doctor = 1
                es_permanente = 0
                sexenios = random.randint(0, 1)
                quinquenios = random.randint(0, 2)
                horas = random.uniform(120, 180)
            else:  # Asociados, Sustitutos, etc.
                es_doctor = random.choice([0, 1])
                es_permanente = 0
                sexenios = 0 if not es_doctor else random.randint(0, 2)
                quinquenios = random.randint(0, 3)
                horas = random.uniform(60, 120)
            
            imparte_primer_curso = random.choice([0, 1])
            
            profesores.append((
                centro_id, categoria, es_doctor, es_permanente,
                sexenios, quinquenios, horas, imparte_primer_curso,
                '2024/2025', 6037
            ))
            total_registros += 1
        
        cursor.executemany('''
            INSERT INTO profesores 
            (centro_id, categoria_pdi, es_doctor, es_permanente, num_sexenios, 
             num_quinquenios, horas_impartidas, imparte_primer_curso, 
             curso_academico, plan_estudio_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', profesores)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Se han generado {total_registros} registros de prueba.")
        
    except Exception as e:
        logger.error(f"Error al generar datos de prueba: {e}")

def mostrar_ejemplo_consulta(db_path: str = "pdi_database.db"):
    """
    Muestra un ejemplo de consulta a la base de datos.
    
    Args:
        db_path: Ruta del archivo de base de datos
    """
    try:
        from .queries import obtener_estructura_profesorado
        
        logger.info("\n--- ESTRUCTURA DEL PROFESORADO 2024/2025 ---")
        logger.info("Estudio: Grado en Ingeniería Informática")
        
        resultados = obtener_estructura_profesorado(db_path)
        
        if resultados and not resultados.get("error"):
            total_pdi = sum(r.total for r in resultados)
            logger.info(f"Total personal académico: {total_pdi}")
            logger.info("-" * 60)
            logger.info(f"{'Categoría':<40} | {'Total':<5} | {'%':<6} | {'1er curso':<9} | {'Sexenios':<8} | {'Quinq.':<6} | {'Horas':<10} | {'%':<6}")
            logger.info("-" * 60)
            
            for r in resultados:
                logger.info(f"{r.categoria_pdi:<40} | {r.total:<5} | {r.porcentaje:.2f} | {r.en_primer_curso:<9} | {r.num_sexenios:<8} | {r.num_quinquenios:<6} | {r.horas_impartidas:<10.1f} | {r.porcentaje_horas:.2f}")
        
    except Exception as e:
        logger.error(f"Error al ejecutar consulta de ejemplo: {e}")

if __name__ == "__main__":
    # Crear tablas si no existen
    crear_tablas()
    
    # Generar datos de prueba
    generar_datos_ejemplo(20)
    
    # Ejecutar consulta de ejemplo
    mostrar_ejemplo_consulta() 