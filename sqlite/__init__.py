"""
Módulo SQLite para almacenar y consultar datos relacionados con el PDI (Personal Docente e Investigador)
de la Universidad de Zaragoza.
"""

from sqlite.database import engine, SessionLocal, Base
from sqlite.models import PDI_Docencia

__all__ = ["engine", "SessionLocal", "Base", "PDI_Docencia"] 