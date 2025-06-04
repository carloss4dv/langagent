"""
Configuración centralizada de logging para langagent.

Este módulo configura el sistema de logging de manera centralizada
para asegurar que todos los logs se muestren correctamente.
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path

def setup_logging(level=logging.INFO, log_to_file=True, log_to_console=True):
    """
    Configura el sistema de logging de manera centralizada.
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Si guardar logs en archivo
        log_to_console: Si mostrar logs en consola
    """
    
    # Configuración básica del formato
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Limpiar configuraciones anteriores
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configurar el logger raíz
    logging.root.setLevel(level)
    
    handlers = []
    
    # Handler para consola (siempre con colores si es posible)
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Formato con colores para la consola si está disponible
        try:
            import colorlog
            console_formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt=date_format,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(console_formatter)
        except ImportError:
            # Si no está disponible colorlog, usar formato normal
            console_formatter = logging.Formatter(log_format, datefmt=date_format)
            console_handler.setFormatter(console_formatter)
        
        handlers.append(console_handler)
    
    # Handler para archivo (opcional)
    if log_to_file:
        # Crear directorio de logs si no existe
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Archivo de log con timestamp
        log_filename = f"langagent_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = log_dir / log_filename
        
        file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configurar el logging básico
    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
        force=True  # Forzar reconfiguración
    )
    
    # Configurar niveles específicos para módulos ruidosos
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # Mostrar mensaje de configuración
    logger = logging.getLogger(__name__)
    logger.info(f"Sistema de logging configurado correctamente (Nivel: {logging.getLevelName(level)})")
    if log_to_file:
        logger.info(f"Logs guardándose en: {log_filepath}")

def get_logger(name):
    """
    Obtiene un logger configurado para el módulo especificado.
    
    Args:
        name: Nombre del módulo (usar __name__)
        
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)

# Configuración por defecto al importar
def configure_default_logging():
    """Configura logging por defecto si no se ha configurado aún."""
    if not logging.root.handlers:
        setup_logging(level=logging.INFO)

# Auto-configurar al importar si no hay configuración previa
configure_default_logging() 