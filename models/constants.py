"""
Constantes utilizadas en el sistema de recuperación de información.
Define la estructura de ámbitos y sus cubos asociados.
"""

AMBITOS_CUBOS = {
    "academico": {
        "nombre": "ACADÉMICO",
        "cubos": ["cohorte", "egresados", "matricula", "rendimiento"],
        "descripcion": "Información académica general, incluyendo matrículas, rendimiento y egresados"
    },
    "admision": {
        "nombre": "ADMISIÓN",
        "cubos": ["admision", "oferta_plazas"],
        "descripcion": "Procesos de admisión y oferta de plazas"
    },
    "docencia": {
        "nombre": "DOCENCIA",
        "cubos": ["docenciaAsignatura", "docenciaPDI"],
        "descripcion": "Información sobre docencia, asignaturas y personal docente"
    },
    "doctorado": {
        "nombre": "DOCTORADO",
        "cubos": ["doctorado"],
        "descripcion": "Estudios de doctorado"
    },
    "estudios_propios": {
        "nombre": "ESTUDIOS PROPIOS",
        "cubos": ["matricula_estudios_propios"],
        "descripcion": "Información sobre estudios propios y títulos específicos"
    },
    "idi": {
        "nombre": "I+D+i",
        "cubos": [
            "grupos",
            "indicesBibliometricos",
            "movilidad_entrada",
            "produccion_cientifica",
            "proyectos_contratos",
            "recursos_humanos_idi",
            "solicitud_convocatoria"
        ],
        "descripcion": "Investigación, desarrollo e innovación"
    },
    "movilidad": {
        "nombre": "MOVILIDAD",
        "cubos": [
            "acuerdos_bilaterales",
            "estudiantesIN",
            "estudiantesOUT",
            "solicitudes_movilidad_out"
        ],
        "descripcion": "Movilidad internacional de estudiantes y acuerdos"
    },
    "rrhh": {
        "nombre": "RRHH",
        "cubos": ["cargo", "pdi", "ptgas", "puesto"],
        "descripcion": "Recursos humanos y personal"
    }
}

# Mapeo inverso de cubos a ámbitos
CUBO_TO_AMBITO = {
    cubo: ambito_key
    for ambito_key, ambito_data in AMBITOS_CUBOS.items()
    for cubo in ambito_data["cubos"]
}

# Keywords por ámbito para búsqueda
AMBITO_KEYWORDS = {
    "academico": [
        "académico", "academico", "estudiante", "matrícula", "matricula",
        "rendimiento", "egresado", "graduado", "cohorte"
    ],
    "admision": [
        "admisión", "admision", "nuevo ingreso", "plaza", "acceso",
        "oferta", "admitido"
    ],
    "docencia": [
        "docencia", "asignatura", "profesor", "enseñanza", "docente",
        "clase", "curso"
    ],
    "doctorado": [
        "doctorado", "tesis", "doctoral", "investigación", "investigacion",
        "doctorando"
    ],
    "estudios_propios": [
        "estudio propio", "título propio", "titulo propio",
        "formación específica", "formacion especifica"
    ],
    "idi": [
        "investigación", "investigacion", "desarrollo", "innovación",
        "innovacion", "i+d+i", "científico", "cientifico", "publicación",
        "publicacion"
    ],
    "movilidad": [
        "movilidad", "internacional", "erasmus", "intercambio",
        "extranjero", "acuerdo bilateral"
    ],
    "rrhh": [
        "recursos humanos", "personal", "trabajador", "empleado",
        "plantilla", "rrhh", "pdi", "pas", "ptgas"
    ]
} 
