"""
Paquete langagent para el sistema de consultas SEGEDA.

Este módulo inicializa el paquete langagent y proporciona acceso a sus componentes.
"""

__version__ = "0.1.0"

# Configurar logging automáticamente al importar el paquete
try:
    from langagent.config.logging_config import setup_logging
    from langagent.config.config import LOGGING_CONFIG
    import logging
    
    # Convertir string level a constante de logging
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    log_level = level_mapping.get(LOGGING_CONFIG.get('level', 'INFO'), logging.INFO)
    
    # Configurar logging con la configuración del proyecto
    setup_logging(
        level=log_level,
        log_to_file=LOGGING_CONFIG.get('log_to_file', True),
        log_to_console=LOGGING_CONFIG.get('log_to_console', True)
    )
    
except ImportError:
    # Si falla la importación, usar configuración básica
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

        