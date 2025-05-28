"""
Funciones para ejecutar consultas comunes sobre la base de datos PDI.
"""

from sqlalchemy import func, desc
from sqlite.database import SessionLocal
from sqlite.models import PDI_Docencia

def get_estructura_profesorado(plan_estudio_id=148, curso_academico="2024/2025", centro_id=None):
    """
    Obtiene la estructura del profesorado para un plan de estudios y curso académico.
    Similar a la consulta de la web de Unizar.
    
    Args:
        plan_estudio_id (int): ID del plan de estudios
        curso_academico (str): Curso académico en formato "YYYY/YYYY"
        centro_id (int, optional): ID del centro para filtrar
        
    Returns:
        dict: Resultados de la consulta con stats generales y datos por categoría
    """
    db = SessionLocal()
    
    try:
        # Crear filtro base
        filtro_base = [
            PDI_Docencia.plan_estudio_id == plan_estudio_id,
            PDI_Docencia.curso_academico == curso_academico
        ]
        
        # Añadir filtro de centro si se especifica
        if centro_id:
            filtro_base.append(PDI_Docencia.centro_id == centro_id)
        
        # Total de registros para calcular porcentajes
        total_pdi = db.query(func.count(PDI_Docencia.id)).filter(*filtro_base).scalar()
        
        total_horas = db.query(func.sum(PDI_Docencia.horas_impartidas)).filter(*filtro_base).scalar()
        
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
            *filtro_base
        ).group_by(
            PDI_Docencia.categoria_pdi
        ).order_by(
            desc("horas_impartidas")
        ).all()
        
        # Preparar resultados en formato diccionario
        datos = []
        for r in resultados:
            datos.append({
                "categoria": r.categoria_pdi,
                "total": r.total,
                "porcentaje": round(r.porcentaje, 2),
                "en_primer_curso": r.en_primer_curso,
                "num_sexenios": r.num_sexenios,
                "num_quinquenios": r.num_quinquenios,
                "horas_impartidas": float(r.horas_impartidas),
                "porcentaje_horas": round(r.porcentaje_horas, 2)
            })
        
        # Añadir fila de totales
        datos.append({
            "categoria": "Total personal académico",
            "total": total_pdi,
            "porcentaje": 100.00,
            "en_primer_curso": sum(d["en_primer_curso"] for d in datos),
            "num_sexenios": sum(d["num_sexenios"] for d in datos),
            "num_quinquenios": sum(d["num_quinquenios"] for d in datos),
            "horas_impartidas": float(total_horas),
            "porcentaje_horas": 100.00
        })
        
        # Estructura final del resultado
        resultado_final = {
            "stats": {
                "total_pdi": total_pdi,
                "total_horas": float(total_horas),
                "plan_estudio_id": plan_estudio_id,
                "curso_academico": curso_academico,
                "centro_id": centro_id
            },
            "datos": datos
        }
        
        return resultado_final
        
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return {"error": str(e)}
    finally:
        db.close()

def get_profesores_por_categoria(categoria, plan_estudio_id=148, curso_academico="2024/2025"):
    """
    Obtiene los profesores pertenecientes a una categoría específica.
    
    Args:
        categoria (str): Categoría del profesorado
        plan_estudio_id (int): ID del plan de estudios
        curso_academico (str): Curso académico en formato "YYYY/YYYY"
        
    Returns:
        list: Lista de diccionarios con información de los profesores
    """
    db = SessionLocal()
    
    try:
        # Consulta de profesores por categoría
        profesores = db.query(PDI_Docencia).filter(
            PDI_Docencia.categoria_pdi == categoria,
            PDI_Docencia.plan_estudio_id == plan_estudio_id,
            PDI_Docencia.curso_academico == curso_academico
        ).all()
        
        # Formatear resultados
        resultados = []
        for p in profesores:
            resultados.append({
                "id": p.id,
                "categoria": p.categoria_pdi,
                "centro": p.centro_nombre,
                "sexenios": p.sexenios,
                "quinquenios": p.quinquenios,
                "horas_impartidas": float(p.horas_impartidas),
                "curso": p.curso,
                "doctor": p.doctor == 'S',
                "permanente": p.permanente == 'S'
            })
            
        return resultados
        
    except Exception as e:
        print(f"Error al ejecutar la consulta: {e}")
        return {"error": str(e)}
    finally:
        db.close()

def get_centros():
    """
    Obtiene la lista de centros con profesores.
    
    Returns:
        list: Lista de diccionarios con los centros
    """
    db = SessionLocal()
    
    try:
        centros = db.query(
            PDI_Docencia.centro_id,
            PDI_Docencia.centro_nombre,
            func.count(PDI_Docencia.id).label("total_profesores")
        ).group_by(
            PDI_Docencia.centro_id,
            PDI_Docencia.centro_nombre
        ).all()
        
        return [
            {
                "id": c.centro_id,
                "nombre": c.centro_nombre,
                "total_profesores": c.total_profesores
            }
            for c in centros
        ]
        
    except Exception as e:
        print(f"Error al obtener los centros: {e}")
        return {"error": str(e)}
    finally:
        db.close() 