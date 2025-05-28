"""
Configuración de la base de datos SQLite y gestión de conexiones.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Directorio donde se almacenará la base de datos
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "pdi_database.db")

# Crear la conexión a la base de datos SQLite
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Solo necesario para SQLite
)

# Crear una sesión local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para declarar modelos
Base = declarative_base()

def get_db():
    """
    Función para obtener una sesión de base de datos.
    Debe usarse como contexto (with) o cerrar la sesión después de usarla.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 