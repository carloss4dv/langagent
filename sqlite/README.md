# Módulo SQLite para datos de PDI

Este módulo proporciona una implementación sencilla de una base de datos SQLite para almacenar y consultar información sobre el Personal Docente e Investigador (PDI) y su docencia, similar a la estructura mostrada en la web de la Universidad de Zaragoza.

## Instalación

Asegúrate de tener instalado SQLAlchemy:

```bash
pip install sqlalchemy
```

## Estructura

El módulo contiene:

- **database.py**: Configuración de conexión a la base de datos
- **models.py**: Definición de modelos usando SQLAlchemy
- **setup_db.py**: Script para inicializar la base de datos y cargar datos de prueba
- **queries.py**: Funciones para ejecutar consultas comunes

## Modelo de datos

El modelo principal `PDI_Docencia` combina información de los cubos PDI y DocenciaPDI para representar la estructura mostrada en la web de Unizar sobre profesorado por categoría, incluyendo:

- Categoría del profesor
- Centro al que pertenece
- Plan de estudios
- Curso académico
- Nivel del curso (1-4)
- Sexenios, quinquenios y horas impartidas
- Información sobre si es permanente o doctor

## Uso básico

### Inicializar la base de datos

Para crear la base de datos y cargar datos de prueba:

```python
python -m sqlite.setup_db
```

### Consultar datos

```python
from sqlite.queries import get_estructura_profesorado, get_profesores_por_categoria

# Obtener estructura del profesorado
resultado = get_estructura_profesorado(plan_estudio_id=148, curso_academico="2024/2025")

# Obtener profesores por categoría
profesores = get_profesores_por_categoria("Cuerpo de Profesores Titulares de Universidad")

# Ver resultado
print(resultado)
```

## Ejemplo de consulta SQL equivalente

La consulta principal que representa la tabla de estructura del profesorado sería:

```sql
SELECT 
    categoria_pdi AS Categoría,
    COUNT(DISTINCT id) AS Total,
    (COUNT(DISTINCT id) * 100.0 / TotalPDI) AS Porcentaje,
    SUM(CASE WHEN curso = 1 THEN 1 ELSE 0 END) AS En_primer_curso,
    SUM(sexenios) AS Num_total_sexenios,
    SUM(quinquenios) AS Num_total_quinquenios,
    SUM(horas_impartidas) AS Horas_impartidas,
    (SUM(horas_impartidas) * 100.0 / TotalHoras) AS Porcentaje_horas
FROM 
    pdi_docencia
WHERE 
    plan_estudio_id = 148
    AND curso_academico = '2024/2025'
GROUP BY 
    categoria_pdi
ORDER BY 
    Horas_impartidas DESC
```

Donde `TotalPDI` es el número total de profesores y `TotalHoras` es el número total de horas impartidas.

## Ampliaciones posibles

Este módulo es una implementación sencilla. Se podría ampliar con:

- API REST para acceder a los datos
- Interfaz gráfica para visualizar los resultados
- Importación de datos reales desde CSV o Excel
- Más filtros y opciones de consulta
- Autenticación y autorización para acceso a los datos 