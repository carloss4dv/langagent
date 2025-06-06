"""
Constantes utilizadas en el sistema de recuperación de información.
Define la estructura de ámbitos y sus cubos asociados.
"""

AMBITOS_CUBOS = {
    "admision": {
        "nombre": "ADMISIÓN",
        "cubos": ["admision", "ofertaplazas"],
        "descripcion": "Procesos de admisión y oferta de plazas"
    },
    "academico": {
        "nombre": "ACADÉMICO",
        "cubos": ["cohorte", "egresados", "matricula", "rendimiento"],
        "descripcion": "Información académica general, incluyendo matrículas, rendimiento y egresados"
    },
    "doctorado": {
        "nombre": "DOCTORADO",
        "cubos": ["doctorado"],
        "descripcion": "Estudios de doctorado"
    },
    "estudios_propios": {
        "nombre": "ESTUDIOS PROPIOS",
        "cubos": ["matriEEPP"],
        "descripcion": "Información sobre estudios propios y títulos específicos"
    },
    "docencia": {
        "nombre": "DOCENCIA",
        "cubos": ["docenciaAsignatura", "docenciaPDI"],
        "descripcion": "Información sobre docencia, asignaturas y personal docente"
    },
    "idi": {
        "nombre": "I+D+i",
        "cubos": [
            "grupos",
            "indicesBibliometricos",
            "movilidad_idi",
            "produccionCientifica",
            "proyectos",
            "RRHHidi",
            "solicitudConvocatoria"
        ],
        "descripcion": "Investigación, desarrollo e innovación"
    },
    "movilidad": {
        "nombre": "MOVILIDAD",
        "cubos": [
            "acuerdos_bilaterales",
            "estudiantesIN",
            "estudiantesOUT",
            "solicitudes_movilidad_OUT"
        ],
        "descripcion": "Movilidad internacional de estudiantes y acuerdos"
    },
    "rrhh": {
        "nombre": "RRHH",
        "cubos": ["cargo", "PDI", "PTGAS", "puesto"],
        "descripcion": "Recursos humanos y personal"
    }
}

# Mapeo inverso de cubos a ámbitos
CUBO_TO_AMBITO = {
    "admision": "admision",
    "ofertaplazas": "admision",
    "cohorte": "academico",
    "egresados": "academico",
    "matricula": "academico",
    "rendimiento": "academico",
    "doctorado": "doctorado",
    "matriEEPP": "estudios_propios",
    "docenciaAsignatura": "docencia",
    "docenciaPDI": "docencia",
    "grupos": "idi",
    "indicesBibliometricos": "idi",
    "movilidad_idi": "idi",
    "produccionCientifica": "idi",
    "proyectos": "idi",
    "RRHHidi": "idi",
    "solicitudConvocatoria": "idi",
    "acuerdos_bilaterales": "movilidad",
    "estudiantesIN": "movilidad",
    "estudiantesOUT": "movilidad",
    "solicitudes_movilidad_OUT": "movilidad",
    "cargo": "rrhh",
    "PDI": "rrhh",
    "PTGAS": "rrhh",
    "puesto": "rrhh"
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
    "available_places": "ofertaplazas",
    "course_teaching": "docenciaAsignatura",
    "faculty_teaching": "docenciaPDI",
    "doctorate_rd": "doctorado",
    "specific_programs_enrollment": "matriEEPP",
    "research_groups": "grupos",
    "bibliometric_indices": "indicesBibliometricos",
    "incoming_mobility": "movilidad_idi",
    "scientific_production": "produccionCientifica",
    "research_projects": "proyectos",
    "rd_human_resources": "RRHHidi",
    "grant_applications": "solicitudConvocatoria",
    "bilateral_agreements": "acuerdos_bilaterales",
    "incoming_students": "estudiantesIN",
    "outgoing_students": "estudiantesOUT",
    "outgoing_mobility_applications": "solicitudes_movilidad_OUT",
    "positions": "cargo",
    "teaching_staff": "PDI",
    "admin_staff": "PTGAS",
    "job_positions": "puesto",
    
    # Español -> Inglés
    "cohorte": "cohort",
    "egresados": "graduates",
    "matricula": "enrollment",
    "rendimiento": "performance",
    "admision": "admission",
    "ofertaplazas": "available_places",
    "docenciaAsignatura": "course_teaching",
    "docenciaPDI": "faculty_teaching",
    "doctorado": "doctorate_rd",
    "matriEEPP": "specific_programs_enrollment",
    "grupos": "research_groups",
    "indicesBibliometricos": "bibliometric_indices",
    "movilidad_idi": "incoming_mobility",
    "produccionCientifica": "scientific_production",
    "proyectos": "research_projects",
    "RRHHidi": "rd_human_resources",
    "solicitudConvocatoria": "grant_applications",
    "acuerdos_bilaterales": "bilateral_agreements",
    "estudiantesIN": "incoming_students",
    "estudiantesOUT": "outgoing_students",
    "solicitudes_movilidad_OUT": "outgoing_mobility_applications",
    "cargo": "positions",
    "PDI": "teaching_staff",
    "PTGAS": "admin_staff",
    "puesto": "job_positions"
} 

# Añadir al final del archivo las nuevas constantes para recuperación adaptativa

# Configuración de Recuperación Adaptativa
CHUNK_STRATEGIES = ["256", "512", "1024"]
DEFAULT_CHUNK_STRATEGY = "512"
MAX_RETRIES = 2  # Total 3 intentos (inicial + 2 reintentos)

# Umbrales de evaluación granular
EVALUATION_THRESHOLDS = {
    "faithfulness": 0.7,
    "context_precision": 0.6,
    "context_recall": 0.6,
    "answer_relevance": 0.7
}

# Configuración de colecciones por estrategia
COLLECTION_CONFIG = {
    "256": {
        "collection_name": "segeda_collection_256",
        "chunk_size": 256,
        "chunk_overlap": 25
    },
    "512": {
        "collection_name": "segeda_collection_512", 
        "chunk_size": 512,
        "chunk_overlap": 50
    },
    "1024": {
        "collection_name": "segeda_collection_1024",
        "chunk_size": 1024,
        "chunk_overlap": 100
    }
} 
