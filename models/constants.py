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

# Mapeo entre nombres en inglés y español para ámbitos
AMBITO_EN_ES = {
    # Inglés -> Español
    "academic": "academico",
    "admission": "admision",
    "teaching": "docencia",
    "doctorate": "doctorado",
    "specific_degrees": "estudios_propios",
    "rd": "idi",
    "mobility": "movilidad",
    "hr": "rrhh",
    
    # Español -> Inglés
    "academico": "academic",
    "admision": "admission",
    "docencia": "teaching",
    "doctorado": "doctorate",
    "estudios_propios": "specific_degrees",
    "idi": "rd",
    "movilidad": "mobility",
    "rrhh": "hr"
}

# Mapeo entre nombres en inglés y español para cubos
CUBO_EN_ES = {
    # Inglés -> Español
    "cohort": "cohorte",
    "graduates": "egresados",
    "enrollment": "matricula",
    "performance": "rendimiento",
    "admission": "admision",
    "available_places": "oferta_plazas",
    "course_teaching": "docenciaAsignatura",
    "faculty_teaching": "docenciaPDI",
    "doctorate_rd": "doctorado",
    "specific_programs_enrollment": "matricula_estudios_propios",
    "research_groups": "grupos",
    "bibliometric_indices": "indicesBibliometricos",
    "incoming_mobility": "movilidad_entrada",
    "scientific_production": "produccion_cientifica",
    "research_projects": "proyectos_contratos",
    "rd_human_resources": "recursos_humanos_idi",
    "grant_applications": "solicitud_convocatoria",
    "bilateral_agreements": "acuerdos_bilaterales",
    "incoming_students": "estudiantesIN",
    "outgoing_students": "estudiantesOUT",
    "outgoing_mobility_applications": "solicitudes_movilidad_out",
    "positions": "cargo",
    "teaching_staff": "pdi",
    "admin_staff": "ptgas",
    "job_positions": "puesto",
    
    # Español -> Inglés
    "cohorte": "cohort",
    "egresados": "graduates",
    "matricula": "enrollment",
    "rendimiento": "performance",
    "admision": "admission",
    "oferta_plazas": "available_places",
    "docenciaAsignatura": "course_teaching",
    "docenciaPDI": "faculty_teaching",
    "doctorado": "doctorate_rd",
    "matricula_estudios_propios": "specific_programs_enrollment",
    "grupos": "research_groups",
    "indicesBibliometricos": "bibliometric_indices",
    "movilidad_entrada": "incoming_mobility",
    "produccion_cientifica": "scientific_production",
    "proyectos_contratos": "research_projects",
    "recursos_humanos_idi": "rd_human_resources",
    "solicitud_convocatoria": "grant_applications",
    "acuerdos_bilaterales": "bilateral_agreements",
    "estudiantesIN": "incoming_students",
    "estudiantesOUT": "outgoing_students",
    "solicitudes_movilidad_out": "outgoing_mobility_applications",
    "cargo": "positions",
    "pdi": "teaching_staff",
    "ptgas": "admin_staff",
    "puesto": "job_positions"
} 
