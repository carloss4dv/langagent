from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

class ActionSugerirAmbitos(Action):
    def name(self) -> Text:
        return "action_sugerir_ambitos"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ambitos = {
            "ACADÉMICO": "Información sobre matrículas, rendimiento, egresados y cohortes",
            "ADMISIÓN": "Datos sobre admisión de estudiantes y oferta de plazas",
            "DOCTORADO": "Estadísticas de programas de doctorado y tesis",
            "ESTUDIOS PROPIOS": "Información sobre estudios propios y cursos",
            "DOCENCIA": "Datos sobre docencia por asignatura y profesorado",
            "I+D+i": "Estadísticas de proyectos de investigación e innovación",
            "MOVILIDAD": "Información sobre programas de movilidad de estudiantes",
            "RRHH": "Datos sobre personal docente y de administración"
        }
        
        mensaje = "Los ámbitos disponibles son:\n"
        for ambito, descripcion in ambitos.items():
            mensaje += f"- {ambito}: {descripcion}\n"
        mensaje += "\n¿Qué ámbito te interesa consultar?"
        
        dispatcher.utter_message(text=mensaje)
        return []

class ActionConfirmarAmbito(Action):
    def name(self) -> Text:
        return "action_confirmar_ambito"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ambito = next(tracker.get_latest_entity_values("ambito"), None)
        
        if not ambito:
            dispatcher.utter_message(text="No he podido identificar el ámbito. ¿Podrías repetirlo?")
            return []
        
        dispatcher.utter_message(text=f"Has seleccionado el ámbito {ambito}. ¿Es correcto?")
        return [SlotSet("ambito_seleccionado", ambito)]

class ActionMostrarCubos(Action):
    def name(self) -> Text:
        return "action_mostrar_cubos"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ambito = tracker.get_slot("ambito_seleccionado")
        
        if not ambito:
            dispatcher.utter_message(text="Primero necesito que selecciones un ámbito.")
            return []
        
        # Mapeo de ámbitos a cubos disponibles con sus descripciones
        cubos_por_ambito = {
            "ACADÉMICO": {
                "MATRÍCULA": "Datos sobre estudiantes matriculados, créditos, nuevo ingreso y ratios",
                "RENDIMIENTO": "Estadísticas de rendimiento académico y tasas de éxito",
                "EGRESADOS": "Información sobre titulados y graduados",
                "COHORTE": "Seguimiento de cohortes de estudiantes"
            },
            "ADMISIÓN": {
                "ADMISIÓN": "Datos sobre el proceso de admisión de estudiantes",
                "OFERTA PLAZAS": "Información sobre plazas ofertadas y ocupadas"
            },
            "DOCENCIA": {
                "DOCENCIA ASIGNATURA": "Estadísticas de docencia por asignatura",
                "DOCENCIA PDI": "Datos sobre la actividad docente del profesorado"
            },
            "I+D+i": {
                "PROYECTOS": "Información sobre proyectos de investigación",
                "PRODUCCIÓN CIENTÍFICA": "Datos sobre publicaciones y producción científica"
            },
            "MOVILIDAD": {
                "MOVILIDAD IN": "Estadísticas de estudiantes entrantes",
                "MOVILIDAD OUT": "Datos sobre estudiantes salientes"
            },
            "RRHH": {
                "PDI": "Información sobre personal docente e investigador",
                "PAS": "Datos sobre personal de administración y servicios"
            }
        }
        
        cubos = cubos_por_ambito.get(ambito, {})
        
        if not cubos:
            dispatcher.utter_message(text=f"No hay cubos disponibles para el ámbito {ambito}.")
            return []
        
        mensaje = f"Los cubos disponibles para el ámbito {ambito} son:\n"
        for cubo, descripcion in cubos.items():
            mensaje += f"- {cubo}: {descripcion}\n"
        mensaje += "\n¿Qué cubo te interesa consultar?"
        
        dispatcher.utter_message(text=mensaje)
        return []

class ActionConfirmarCubo(Action):
    def name(self) -> Text:
        return "action_confirmar_cubo"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        cubo = next(tracker.get_latest_entity_values("cubo"), None)
        
        if not cubo:
            dispatcher.utter_message(text="No he podido identificar el cubo. ¿Podrías repetirlo?")
            return []
        
        # Información sobre dimensiones disponibles según el cubo
        dimensiones_por_cubo = {
            "MATRÍCULA": [
                "Acceso (estudio previo, nuevo ingreso)",
                "Alumno (nacionalidad, edad, residencia, sexo)",
                "Asignatura (clase, grupo)",
                "Centro (campus, localidad, tipo)",
                "Titulación (estudio, plan, rama de conocimiento)"
            ],
            "RENDIMIENTO": [
                "Asignatura",
                "Centro",
                "Curso Académico",
                "Titulación"
            ],
            "EGRESADOS": [
                "Titulación",
                "Centro",
                "Curso Académico",
                "Alumno"
            ],
            "DOCENCIA PDI": [
                "Profesor",
                "Asignatura",
                "Centro",
                "Curso Académico"
            ]
        }
        
        dimensiones = dimensiones_por_cubo.get(cubo, ["No hay información detallada disponible"])
        
        mensaje = f"Has seleccionado el cubo {cubo}.\n\n"
        mensaje += "Dimensiones disponibles:\n"
        for dim in dimensiones:
            mensaje += f"- {dim}\n"
        mensaje += "\n¿Qué información específica necesitas?"
        
        dispatcher.utter_message(text=mensaje)
        return [SlotSet("cubo_seleccionado", cubo)]

class ActionProcesarConsulta(Action):
    def name(self) -> Text:
        return "action_procesar_consulta"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        tipo_consulta = next(tracker.get_latest_entity_values("tipo_consulta"), None)
        ambito = tracker.get_slot("ambito_seleccionado")
        cubo = tracker.get_slot("cubo_seleccionado")
        
        if not all([tipo_consulta, ambito, cubo]):
            dispatcher.utter_message(text="Necesito que me indiques el ámbito, el cubo y el tipo de consulta que deseas realizar.")
            return []
        
        # Aquí se procesaría la consulta y se pasaría al agente LangGraph
        mensaje = f"Procesando consulta de {tipo_consulta} en el cubo {cubo} del ámbito {ambito}..."
        dispatcher.utter_message(text=mensaje)
        
        return [
            SlotSet("tipo_consulta", tipo_consulta),
            SlotSet("ambito_seleccionado", None),
            SlotSet("cubo_seleccionado", None)
        ] 