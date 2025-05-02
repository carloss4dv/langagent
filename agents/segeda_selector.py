from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
from typing import Dict, List, Optional
import json
import os

class SEGEDASelector:
    def __init__(self):
        self.chatbot = ChatBot(
            'SEGEDA_Selector',
            storage_adapter='chatterbot.storage.SQLStorageAdapter',
            logic_adapters=[
                'chatterbot.logic.BestMatch',
                'chatterbot.logic.MathematicalEvaluation'
            ],
            language_adapters=[
                'chatterbot.language.SpanishLanguageAdapter'
            ]
        )
        
        # Estructura de ámbitos y cubos
        self.ambitos = {
            "ADMISIÓN": {
                "cubos": ["ADMISIÓN", "OFERTA DE PLAZAS"],
                "descripcion": "Procesos de admisión y requisitos en la Universidad de Zaragoza",
                "palabras_clave": [
                    "admisión", "plaza", "preinscripción", "oferta", "acceso", "matrícula",
                    "solicitud", "nota media", "solicitante", "adjudicación", "convocatoria",
                    "cupo", "preferencia", "calificación", "titulación", "estudio previo",
                    "evaluación", "requisitos", "proceso selectivo", "distrito", "matrícula directa",
                    "plazas ofertadas", "plazas matriculadas", "plazas solicitadas",
                    "nota de corte", "cupo general", "cupo reserva", "convocatoria ordinaria",
                    "convocatoria extraordinaria", "adjudicación de plazas", "llamamientos",
                    "recursos", "prelación", "proceso de preinscripción", "acceso a ciclos",
                    "EVAU", "PAU", "CFGS", "Credencial UNED", "mayores de 25", "mayores de 45",
                    "discapacitados", "deportistas", "experiencia profesional"
                ]
            },
            "ACADÉMICO": {
                "cubos": ["COHORTE", "EGRESADOS", "MATRÍCULA", "RENDIMIENTO"],
                "descripcion": "Información sobre estudiantes, rendimiento académico y graduados",
                "palabras_clave": [
                    "estudiante", "asignatura", "nota", "graduado", "matrícula", "rendimiento", "cohorte",
                    "créditos", "plan de estudios", "titulación", "modalidad", "curso académico",
                    "centro", "campus", "nuevo ingreso", "experimentalidad", "interuniversitario",
                    "múltiple titulación", "rama de conocimiento", "grado", "máster", "doctorado",
                    "asignaturas básicas", "asignaturas obligatorias", "asignaturas optativas",
                    "trabajo fin de grado", "trabajo fin de máster", "prácticas externas",
                    "tasa de éxito", "tasa de rendimiento", "tasa de evaluación", "créditos superados",
                    "créditos suspendidos", "créditos evaluados", "créditos presentados",
                    "nota media", "calificación", "convocatorias", "reconocimiento de créditos",
                    "adaptación de créditos", "convalidación", "evaluación continua",
                    "matrícula de honor", "sobresaliente", "notable", "aprobado", "suspenso",
                    "no presentado", "apto", "no apto", "anulada", "incompatible", "renuncia",
                    "suspenso compensable", "pendiente de calificar", "grupo de asignatura",
                    "tiempo completo", "tiempo parcial", "otra dedicación", "número de veces",
                    "convocatorias consumidas", "rango de nota numérica", "estudio previo",
                    "nuevo ingreso", "rango de nota de admisión", "país nacionalidad",
                    "rango de edad", "residencia familiar", "sexo", "clase de asignatura",
                    "formación básica", "obligatoria", "optativa", "libre elección", "troncal",
                    "complementos de formación", "actividades académicas complementarias",
                    "alumnos graduados", "alumnos que interrumpen", "alumnos que se trasladan",
                    "duración media", "media de cursos matriculados", "media de créditos matriculados",
                    "tasa de eficiencia", "abandono inicial", "créditos necesarios",
                    "créditos reconocidos", "curso más alto matriculado", "número de años cursados",
                    "solicita título", "tipo de egreso", "graduado", "abandono voluntario",
                    "régimen de permanencia", "cambio de estudios", "traslado a otra universidad",
                    "centro de egreso", "centro de origen", "duración oficial", "múltiple titulación",
                    "movilidad internacional", "programa de movilidad", "Erasmus", "Movilidad Iberoamérica",
                    "UZ/Norteamérica", "Oceanía y Asia", "Movilidad UE-Suiza"
                ]
            },
            "DOCTORADO": {
                "cubos": ["DOCTORADO RD 99/2011"],
                "descripcion": "Información sobre estudios de doctorado en la UZ (modificado por RD 576/2023)",
                "palabras_clave": [
                    "doctorado", "tesis", "doctor", "investigación doctoral", "RD 99/2011", "RD 576/2023",
                    "tesis doctoral", "mención internacional", "doctorando", "lectura de tesis",
                    "programa doctoral", "investigación", "director de tesis", "codirector",
                    "estudios de doctorado", "investigación avanzada", "formación doctoral"
                ]
            },
            "ESTUDIOS PROPIOS": {
                "cubos": ["MATRÍCULA DE ESTUDIOS PROPIOS"],
                "descripcion": "Programas de grado específicos en la Universidad de Zaragoza",
                "palabras_clave": [
                    "estudios propios", "programa específico", "título propio", "matrícula específica",
                    "matrícula estudios propios", "programa específico de grado", "título específico",
                    "formación específica", "programa propio", "estudios no oficiales",
                    "matrícula no oficial", "programa especializado", "formación complementaria"
                ]
            },
            "DOCENCIA": {
                "cubos": ["DOCENCIA ASIGNATURA", "DOCENCIA PDI"],
                "descripcion": "Información sobre enseñanza y profesorado",
                "palabras_clave": [
                    "profesor", "clase", "docencia", "asignatura", "enseñanza", "PDI",
                    "horas de docencia", "asignaturas especiales", "clases magistrales",
                    "prácticas de laboratorio", "trabajos fin de grado", "trabajos fin de máster",
                    "prácticas externas", "docencia tutorizada", "coordinación docente",
                    "responsabilidad docente", "tipo de docencia", "dedicación docente",
                    "quinquenios", "trienios", "sexenios", "área de conocimiento",
                    "departamento", "categoría docente", "cuerpo docente"
                ]
            },
            "I+D+i": {
                "cubos": ["PRODUCCIÓN CIENTÍFICA", "GRUPOS DE INVESTIGACIÓN", "SOLICITUD CONVOCATORIA", "PROYECTOS", "ÍNDICES BIBLIOMÉTRICOS", "MOVILIDAD DE ENTRADA"],
                "descripcion": "Información sobre investigación, desarrollo e innovación",
                "palabras_clave": [
                    "investigación", "grupo", "publicación", "proyecto", "financiación",
                    "artículo científico", "congreso", "ponencia", "póster", "libro",
                    "capítulo de libro", "grupo de investigación", "instituto de investigación",
                    "macroárea", "área de conocimiento", "publicación en abierto",
                    "actividad científica", "comité científico", "comité organizador",
                    "índices de impacto", "citas", "revista científica", "investigación sanitaria",
                    "investigación básica", "investigación aplicada", "transferencia de conocimiento",
                    "investigador principal", "colaborador", "becario", "investigador externo",
                    "grupo emergente", "grupo consolidado", "grupo excelente",
                    "subvención", "financiación", "proyecto de investigación",
                    "sexenios", "tramos de investigación", "CNEAI", "responsable de grupo",
                    "instituto universitario de investigación", "IUI", "investigación aplicada",
                    "investigación básica", "investigación sanitaria", "solicitud", "convocatoria",
                    "importe solicitado", "importe concedido", "solicitudes concedidas",
                    "solicitudes denegadas", "tasa de éxito", "tasa éxito importes",
                    "alegación", "fecha de resolución", "oficina gestora", "programa",
                    "tipo de convocatoria", "tipo de oportunidad", "ámbito territorial",
                    "local", "autonómico", "nacional", "europeo", "internacional",
                    "grupos", "proyectos I+D+i", "proyectos colaborativos", "movilidades",
                    "asesorías", "cursos y seminarios", "servicios técnicos",
                    "recursos humanos", "infraestructuras", "royalties", "licencias",
                    "mecenazgo", "donaciones", "CIT", "contrato", "convenio",
                    "subcontratación", "centro", "departamento", "edad", "grupo de investigación",
                    "instituto", "macroárea", "otros centros de investigación", "sexo",
                    "área", "concedido", "denegado", "fecha de solicitud",
                    "proyectos vigentes", "proyectos nuevos", "ingresos totales",
                    "ingresos IVA", "ingresos overhead", "ingresos proyecto",
                    "costes totales", "costes IVA", "costes al proyecto",
                    "bienes y servicios", "gastos generales", "gastos de funcionamiento",
                    "dietas y viajes", "material bibliográfico", "fungible",
                    "inventariable", "equipo de laboratorio", "estancias",
                    "investigación básica europea", "investigación básica no europea",
                    "proyectos colaborativos con empresa", "contratos y convenios",
                    "categoría baremo", "proyectos no baremables", "convocatorias competitivas",
                    "convocatorias no competitivas", "asesorías I+D", "servicios",
                    "sector industrial", "agrupación", "oficina de proyectos europeos",
                    "oficina de transferencia", "servicio de gestión de la investigación",
                    "proyectos externos", "artículos", "revistas", "factor impacto",
                    "JCR", "cuartil", "decil", "materia", "ranking", "producción científica",
                    "año de publicación", "año de registro", "índices bibliométricos",
                    "impacto científico", "visibilidad científica", "calidad científica",
                    "movilidad de entrada", "duración", "fecha de inicio", "fecha de finalización",
                    "prórroga", "tipo de entidad origen", "empresa", "universidad",
                    "unidad de investigación", "tipo de movilidad", "estancia", "vinculación",
                    "investigador visitante", "nacionalidad", "edad", "sexo", "grupo de investigación",
                    "instituto de investigación", "macroárea", "año de la movilidad"
                ]
            },
            "MOVILIDAD": {
                "cubos": ["SOLICITUDES DE MOVILIDAD", "MOVILIDAD DE ENTRADA"],
                "descripcion": "Información sobre movilidad internacional y programas de intercambio",
                "palabras_clave": [
                    "movilidad", "intercambio", "estancia", "universidad", "destino",
                    "solicitud", "programa", "acuerdo", "convenio", "contrato de estudios",
                    "estancia", "vinculación", "prórroga", "duración", "fecha de inicio",
                    "fecha de finalización", "tipo de entidad", "universidad de origen",
                    "universidad de destino", "acuerdo bilateral", "programa de intercambio",
                    "movilidad de entrada", "movilidad de salida", "estudiante internacional",
                    "investigador visitante", "estancia de investigación", "convenio de movilidad",
                    "programa Erasmus", "programa SICUE", "programa UZ/NOA",
                    "programa Movilidad Iberoamérica", "programa Movilidad UE-Suiza",
                    "alianza UNITA", "orden de preferencia", "preferencia aceptada",
                    "renuncia", "idioma", "nivel de estudios", "área de estudios",
                    "créditos superados", "cursos matriculados", "residencia familiar",
                    "nacionalidad", "rango de edad", "sexo"
                ]
            },
            "RRHH": {
                "cubos": ["CARGO", "PDI", "PTGAS", "PUESTO"],
                "descripcion": "Información sobre recursos humanos y personal",
                "palabras_clave": [
                    "personal", "profesor", "administrativo", "cargo", "puesto", "PDI", "PTGAS",
                    "categoría", "cuerpo", "escala", "departamento", "centro", "campus",
                    "dedicación", "contrato", "funcionario", "interino", "indefinido",
                    "temporal", "colaborador", "emérito", "sexenios", "quinquenios",
                    "trienios", "área de conocimiento", "doctor", "investigador",
                    "personal de administración", "personal de servicios", "personal docente",
                    "personal investigador", "personal técnico", "personal de gestión"
                ]
            }
        }
        
        # Palabras clave para detectar reportes
        self.reporte_keywords = [
            "reporte", "informe", "estadística", "estadisticas", "estadísticas",
            "gráfico", "grafico", "gráficos", "graficos", "tabla", "tablas",
            "visualización", "visualizacion", "visualizar", "mostrar datos",
            "comparar", "comparación", "comparacion", "tendencia", "tendencias",
            "evolución", "evolucion", "distribución", "distribucion",
            "porcentaje", "porcentajes", "proporción", "proporcion",
            "análisis", "analisis", "resumen", "resúmenes", "resumenes"
        ]
        
        # Entrenamiento inicial
        self._entrenar_chatbot()
    
    def _entrenar_chatbot(self):
        trainer = ListTrainer(self.chatbot)
        
        # Entrenamiento con ejemplos de selección de ámbito
        conversaciones = [
            ["Quiero información sobre estudiantes", "¿Te refieres a información académica sobre estudiantes? (Ámbito ACADÉMICO)"],
            ["Necesito datos de profesores", "¿Buscas información sobre la docencia? (Ámbito DOCENCIA)"],
            ["Información sobre investigación", "¿Te interesa el ámbito de I+D+i?"],
            ["No sé en qué ámbito buscar", "Te ayudo a encontrar el ámbito correcto. ¿Qué tipo de información necesitas?"],
            ["Quiero saber sobre movilidad internacional", "¿Te interesa el ámbito de MOVILIDAD?"],
            ["Necesito información sobre personal", "¿Buscas información en el ámbito de RRHH?"],
            ["Información sobre admisión", "¿Te interesa el ámbito de ADMISIÓN?"],
            ["Datos sobre doctorado", "¿Buscas información en el ámbito de DOCTORADO?"],
            ["Información sobre estudios propios", "¿Te interesa el ámbito de ESTUDIOS PROPIOS?"],
            ["Quiero saber sobre grupos de investigación", "¿Te interesa el ámbito de I+D+i?"],
            ["Necesito información sobre producción científica", "¿Buscas información en el ámbito de I+D+i?"],
            ["Datos sobre movilidad de entrada", "¿Te interesa el ámbito de I+D+i?"],
            ["Información sobre acuerdos bilaterales", "¿Buscas información en el ámbito de MOVILIDAD?"],
            ["¿Cuál es la tasa de éxito en las asignaturas?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo RENDIMIENTO"],
            ["Necesito saber las notas de corte", "¿Te interesa el ámbito ADMISIÓN? Podemos explorar el cubo OFERTA DE PLAZAS"],
            ["¿Cuántos alumnos se han graduado este año?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo EGRESADOS"],
            ["¿Cuál es la duración media de los estudios?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo EGRESADOS"],
            ["¿Cuántas plazas se ofertan en cada titulación?", "¿Te interesa el ámbito ADMISIÓN? Podemos explorar el cubo OFERTA DE PLAZAS"],
            ["¿Cuál es el rendimiento académico por asignatura?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo RENDIMIENTO"],
            ["¿Cuántos créditos se han matriculado este curso?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo MATRÍCULA"],
            ["¿Cuál es la tasa de abandono inicial?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo COHORTE"],
            ["¿Cuántos estudiantes han cambiado de estudios?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo EGRESADOS"],
            ["¿Cuál es la nota media de admisión?", "¿Te interesa el ámbito ADMISIÓN? Podemos explorar el cubo ADMISIÓN"],
            ["¿Cuántos estudiantes han solicitado reconocimiento de créditos?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo RENDIMIENTO"],
            ["¿Cuál es la distribución de calificaciones?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo RENDIMIENTO"],
            ["¿Cuántos estudiantes han obtenido matrícula de honor?", "¿Te interesa el ámbito ACADÉMICO? Podemos explorar el cubo RENDIMIENTO"],
            ["¿Cuántas horas de docencia tiene cada profesor?", "¿Te interesa el ámbito DOCENCIA? Podemos explorar el cubo DOCENCIA PDI"],
            ["¿Cuántos trabajos fin de grado se han dirigido?", "¿Te interesa el ámbito DOCENCIA? Podemos explorar el cubo DOCENCIA ASIGNATURA"],
            ["¿Cuál es la distribución de tipos de docencia?", "¿Te interesa el ámbito DOCENCIA? Podemos explorar el cubo DOCENCIA PDI"],
            ["¿Cuántos profesores tienen sexenios?", "¿Te interesa el ámbito DOCENCIA? Podemos explorar el cubo DOCENCIA PDI"],
            ["¿Cuántos artículos científicos se han publicado?", "¿Te interesa el ámbito I+D+i? Podemos explorar el cubo PRODUCCIÓN CIENTÍFICA"],
            ["¿Cuál es el factor de impacto de las revistas?", "¿Te interesa el ámbito I+D+i? Podemos explorar el cubo ÍNDICES BIBLIOMÉTRICOS"],
            ["¿Cuántos proyectos de investigación hay activos?", "¿Te interesa el ámbito I+D+i? Podemos explorar el cubo PROYECTOS"],
            ["¿Cuál es la financiación total de los proyectos?", "¿Te interesa el ámbito I+D+i? Podemos explorar el cubo PROYECTOS"],
            ["¿Cuántos investigadores visitantes han venido?", "¿Te interesa el ámbito I+D+i? Podemos explorar el cubo MOVILIDAD DE ENTRADA"],
            ["¿Cuántos estudiantes han participado en Erasmus?", "¿Te interesa el ámbito MOVILIDAD? Podemos explorar el cubo SOLICITUDES DE MOVILIDAD"],
            ["¿Cuál es la duración media de las estancias?", "¿Te interesa el ámbito MOVILIDAD? Podemos explorar el cubo SOLICITUDES DE MOVILIDAD"],
            ["¿Cuántos acuerdos bilaterales hay activos?", "¿Te interesa el ámbito MOVILIDAD? Podemos explorar el cubo SOLICITUDES DE MOVILIDAD"],
            ["¿Cuántos estudiantes han renunciado a la movilidad?", "¿Te interesa el ámbito MOVILIDAD? Podemos explorar el cubo SOLICITUDES DE MOVILIDAD"],
            ["¿Cuál es la distribución de destinos de movilidad?", "¿Te interesa el ámbito MOVILIDAD? Podemos explorar el cubo SOLICITUDES DE MOVILIDAD"],
            ["¿Cuántos grupos de investigación hay?", "¿Te interesa el ámbito I+D+i? Podemos explorar el cubo GRUPOS DE INVESTIGACIÓN"],
            ["¿Cuál es la tasa de éxito en las convocatorias?", "¿Te interesa el ámbito I+D+i? Podemos explorar el cubo SOLICITUD CONVOCATORIA"],
            ["¿Cuántos congresos se han organizado?", "¿Te interesa el ámbito I+D+i? Podemos explorar el cubo PRODUCCIÓN CIENTÍFICA"],
            ["¿Cuál es la distribución de tipos de movilidad?", "¿Te interesa el ámbito MOVILIDAD? Podemos explorar el cubo SOLICITUDES DE MOVILIDAD"],
            ["¿Cuántos estudiantes han participado en SICUE?", "¿Te interesa el ámbito MOVILIDAD? Podemos explorar el cubo SOLICITUDES DE MOVILIDAD"],
            ["¿Cuál es la distribución de idiomas en movilidad?", "¿Te interesa el ámbito MOVILIDAD? Podemos explorar el cubo SOLICITUDES DE MOVILIDAD"],
            ["¿Cuántos profesores hay por departamento?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo PDI"],
            ["¿Cuál es la distribución de categorías del PDI?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo PDI"],
            ["¿Cuántos funcionarios hay en la universidad?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo CARGO"],
            ["¿Cuál es la distribución de personal técnico?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo PTGAS"],
            ["¿Cuántos doctorandos hay matriculados?", "¿Te interesa el ámbito DOCTORADO? Podemos explorar el cubo DOCTORADO RD 99/2011"],
            ["¿Cuántas tesis se han leído este año?", "¿Te interesa el ámbito DOCTORADO? Podemos explorar el cubo DOCTORADO RD 99/2011"],
            ["¿Cuántos doctorados tienen mención internacional?", "¿Te interesa el ámbito DOCTORADO? Podemos explorar el cubo DOCTORADO RD 99/2011"],
            ["¿Cuántos estudiantes hay en estudios propios?", "¿Te interesa el ámbito ESTUDIOS PROPIOS? Podemos explorar el cubo MATRÍCULA DE ESTUDIOS PROPIOS"],
            ["¿Cuál es la distribución de títulos propios?", "¿Te interesa el ámbito ESTUDIOS PROPIOS? Podemos explorar el cubo MATRÍCULA DE ESTUDIOS PROPIOS"],
            ["¿Cuántos profesores tienen quinquenios?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo PDI"],
            ["¿Cuál es la distribución de personal por campus?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo CARGO"],
            ["¿Cuántos doctorandos tienen director y codirector?", "¿Te interesa el ámbito DOCTORADO? Podemos explorar el cubo DOCTORADO RD 99/2011"],
            ["¿Cuántos programas de doctorado hay?", "¿Te interesa el ámbito DOCTORADO? Podemos explorar el cubo DOCTORADO RD 99/2011"],
            ["¿Cuántos estudiantes hay en programas específicos?", "¿Te interesa el ámbito ESTUDIOS PROPIOS? Podemos explorar el cubo MATRÍCULA DE ESTUDIOS PROPIOS"],
            ["¿Cuál es la distribución de personal por área?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo PDI"],
            ["¿Cuántos profesores eméritos hay?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo PDI"],
            ["¿Cuántos doctorandos tienen beca?", "¿Te interesa el ámbito DOCTORADO? Podemos explorar el cubo DOCTORADO RD 99/2011"],
            ["¿Cuántos títulos propios se ofertan?", "¿Te interesa el ámbito ESTUDIOS PROPIOS? Podemos explorar el cubo MATRÍCULA DE ESTUDIOS PROPIOS"],
            ["¿Cuál es la distribución de personal por dedicación?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo CARGO"],
            ["¿Cuántos profesores tienen trienios?", "¿Te interesa el ámbito RRHH? Podemos explorar el cubo PDI"],
            ["Necesito un reporte de rendimiento académico", "¿Te interesa el ámbito ACADÉMICO? Podemos generar un reporte del cubo RENDIMIENTO"],
            ["Quiero un informe sobre la producción científica", "¿Te interesa el ámbito I+D+i? Podemos generar un reporte del cubo PRODUCCIÓN CIENTÍFICA"],
            ["Necesito visualizar datos de movilidad", "¿Te interesa el ámbito MOVILIDAD? Podemos generar un reporte del cubo SOLICITUDES DE MOVILIDAD"],
            ["Quiero comparar datos de admisión", "¿Te interesa el ámbito ADMISIÓN? Podemos generar un reporte del cubo OFERTA DE PLAZAS"],
            ["Necesito un análisis de la distribución de personal", "¿Te interesa el ámbito RRHH? Podemos generar un reporte del cubo CARGO"]
        ]
        
        # Convertir las conversaciones a una lista plana de strings
        conversaciones_planas = []
        for conversacion in conversaciones:
            conversaciones_planas.extend(conversacion)
        
        trainer.train(conversaciones_planas)
    
    def _es_reporte(self, mensaje: str) -> bool:
        """
        Determina si la consulta es sobre generar un reporte.
        
        Args:
            mensaje (str): Mensaje del usuario
            
        Returns:
            bool: True si es una consulta de reporte
        """
        mensaje = mensaje.lower()
        return any(keyword in mensaje for keyword in self.reporte_keywords)
    
    async def procesar_consulta(self, mensaje: str) -> Dict:
        """
        Procesa la consulta del usuario y sugiere ámbitos y cubos relevantes
        """
        # Obtener respuesta del chatbot
        respuesta = self.chatbot.get_response(mensaje)
        
        # Analizar el mensaje para identificar palabras clave
        ambito_sugerido = self._identificar_ambito(mensaje)
        
        # Determinar si es una consulta de reporte
        es_reporte = self._es_reporte(mensaje)
        
        if ambito_sugerido:
            return {
                "tipo": "ambito_sugerido",
                "ambito": ambito_sugerido,
                "cubos": self.ambitos[ambito_sugerido]["cubos"],
                "is_consulta": es_reporte,
                "mensaje": f"¿Te interesa el ámbito de {ambito_sugerido}? Podemos explorar: {', '.join(self.ambitos[ambito_sugerido]['cubos'])}"
            }
        
        return {
            "tipo": "pregunta_clarificacion",
            "mensaje": "¿Podrías ser más específico sobre qué información necesitas?"
        }
    
    def _identificar_ambito(self, mensaje: str) -> Optional[str]:
        """
        Identifica el ámbito más relevante basado en palabras clave
        """
        mensaje = mensaje.lower()
        max_coincidencias = 0
        ambito_sugerido = None
        
        for ambito, info in self.ambitos.items():
            coincidencias = sum(1 for palabra in info["palabras_clave"] if palabra.lower() in mensaje)
            if coincidencias > max_coincidencias:
                max_coincidencias = coincidencias
                ambito_sugerido = ambito
        
        return ambito_sugerido
    
    async def explorar_cubo(self, cubo: str) -> Dict:
        """
        Explora las dimensiones y medidas de un cubo específico
        """
        # Aquí se implementaría la lógica para cargar la información del cubo
        # desde los archivos de data
        return {
            "tipo": "exploracion_cubo",
            "cubo": cubo,
            "mensaje": f"¿Qué información específica necesitas del cubo {cubo}?"
        }
    
    async def cruzar_datos(self, cubos: List[str]) -> Dict:
        """
        Maneja consultas que requieren cruzar datos de múltiples cubos
        """
        ambito_comun = self._encontrar_ambito_comun(cubos)
        
        return {
            "tipo": "cruce_datos",
            "ambito": ambito_comun,
            "cubos": cubos,
            "mensaje": f"Podemos cruzar datos de los cubos {', '.join(cubos)} en el ámbito {ambito_comun}"
        }
    
    def _encontrar_ambito_comun(self, cubos: List[str]) -> Optional[str]:
        """
        Encuentra el ámbito común para un conjunto de cubos
        """
        for ambito, info in self.ambitos.items():
            if all(cubo in info["cubos"] for cubo in cubos):
                return ambito
        return None 