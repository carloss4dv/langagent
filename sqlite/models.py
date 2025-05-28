"""
Modelos de base de datos para almacenar información del PDI y su docencia.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from .database import Base

class PDI_Docencia(Base):
    """
    Modelo que representa al Personal Docente e Investigador y su docencia.
    Combina información de los cubos PDI y DocenciaPDI.
    """
    __tablename__ = "pdi_docencia"

    id = Column(Integer, primary_key=True, index=True)
    categoria_pdi = Column(String(100), nullable=False, index=True)
    centro_id = Column(Integer, nullable=False)
    centro_nombre = Column(String(100), nullable=False)
    plan_estudio_id = Column(Integer, nullable=False, index=True)
    curso_academico = Column(String(10), nullable=False)
    curso = Column(Integer, nullable=True)
    sexenios = Column(Integer, default=0)
    quinquenios = Column(Integer, default=0)
    horas_impartidas = Column(Numeric(10, 2), default=0.0)
    permanente = Column(String(1), default='N')
    doctor = Column(String(1), default='N')

    def __repr__(self):
        return f"<PDI_Docencia(id={self.id}, categoria={self.categoria_pdi}, centro={self.centro_nombre})>" 