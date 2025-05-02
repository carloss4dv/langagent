# Investigación Detallada: ChatterBot para Selección de Ámbitos y Cubos

## 1. ChatterBot: Características Principales

### 1.1 Arquitectura
- **Motor de Respuestas**: Basado en machine learning
- **Procesamiento de Lenguaje**: Utiliza NLTK para procesamiento de lenguaje natural
- **Base de Conocimiento**: Almacena conversaciones y aprende de ellas
- **Adaptabilidad**: Se mejora con cada interacción

### 1.2 Ventajas para el Caso de Uso
- **Aprendizaje Continuo**: Mejora con cada interacción del usuario
- **Manejo de Contexto**: Puede mantener el contexto de la conversación
- **Personalización**: Se puede entrenar específicamente para ámbitos y cubos
- **Integración Simple**: Fácil de integrar con Chainlit

## 2. Implementación Específica para SEGEDA

### 2.1 Estructura de Datos
```python
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer, ListTrainer
from typing import Dict, List

class SEGEDAAmbitoSelector:
    def __init__(self):
        self.chatbot = ChatBot(
            'SEGEDA_Selector',
            storage_adapter='chatterbot.storage.SQLStorageAdapter',
            logic_adapters=[
                'chatterbot.logic.BestMatch',
                'chatterbot.logic.MathematicalEvaluation'
            ]
        )
        
        # Estructura de ámbitos y cubos
        self.ambitos = {
            "ACADÉMICO": {
                "cubos": ["MATRÍCULA", "RENDIMIENTO", "EGRESADOS", "COHORTE"],
                "descripcion": "Información sobre estudiantes, rendimiento académico y graduados",
                "palabras_clave": ["estudiante", "asignatura", "nota", "graduado"]
            },
            "DOCENCIA": {
                "cubos": ["DOCENCIA ASIGNATURA", "DOCENCIA PDI"],
                "descripcion": "Información sobre enseñanza y profesorado",
                "palabras_clave": ["profesor", "clase", "docencia", "asignatura"]
            },
            "I+D+i": {
                "cubos": [
                    "GRUPOS DE INVESTIGACIÓN", 
                    "ÍNDICES BIBLIOMÉTRICOS",
                    "PRODUCCIÓN CIENTÍFICA",
                    "PROYECTOS Y CONTRATOS"
                ],
                "descripcion": "Información sobre investigación y desarrollo",
                "palabras_clave": ["investigación", "proyecto", "publicación", "grupo"]
            }
            # ... más ámbitos
        }
        
        # Entrenamiento inicial
        self._entrenar_chatbot()
    
    def _entrenar_chatbot(self):
        trainer = ListTrainer(self.chatbot)
        
        # Entrenamiento con ejemplos de selección de ámbito
        conversaciones = [
            ["Quiero información sobre estudiantes", "¿Te refieres a información académica sobre estudiantes? (Ámbito ACADÉMICO)"],
            ["Necesito datos de profesores", "¿Buscas información sobre la docencia? (Ámbito DOCENCIA)"],
            ["Información sobre investigación", "¿Te interesa el ámbito de I+D+i?"],
            ["No sé en qué ámbito buscar", "Te ayudo a encontrar el ámbito correcto. ¿Qué tipo de información necesitas?"]
        ]
        
        trainer.train(conversaciones)
```

### 2.2 Manejo de Dudas y Navegación
```python
    async def procesar_duda(self, mensaje: str) -> Dict:
        """
        Procesa mensajes de duda y ayuda a navegar por ámbitos y cubos
        """
        # Obtener respuesta del chatbot
        respuesta = self.chatbot.get_response(mensaje)
        
        # Analizar la respuesta para determinar el siguiente paso
        if "no sé" in mensaje.lower() or "duda" in mensaje.lower():
            return {
                "tipo": "guia",
                "opciones": self._generar_opciones_guia(),
                "mensaje": "Te ayudo a encontrar el ámbito correcto. ¿Qué tipo de información buscas?"
            }
        
        # Si la respuesta sugiere un ámbito específico
        for ambito, info in self.ambitos.items():
            if ambito.lower() in respuesta.text.lower():
                return {
                    "tipo": "ambito_sugerido",
                    "ambito": ambito,
                    "cubos": info["cubos"],
                    "mensaje": f"¿Te interesa el ámbito de {ambito}? Podemos explorar: {', '.join(info['cubos'])}"
                }
        
        return {
            "tipo": "pregunta_clarificacion",
            "mensaje": "¿Podrías ser más específico sobre qué información necesitas?"
        }
```

### 2.3 Navegación por Cubos y Dimensiones
```python
    async def explorar_cubo(self, cubo: str) -> Dict:
        """
        Explora las dimensiones y medidas de un cubo específico
        """
        # Cargar información del cubo desde los archivos de data
        info_cubo = self._cargar_info_cubo(cubo)
        
        return {
            "tipo": "exploracion_cubo",
            "cubo": cubo,
            "dimensiones": info_cubo["dimensiones"],
            "medidas": info_cubo["medidas"],
            "mensaje": f"El cubo {cubo} contiene las siguientes dimensiones y medidas:"
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
```

## 3. Flujos de Conversación

### 3.1 Flujo de Selección de Ámbito
```
Usuario: Quiero información sobre estudiantes
Chatbot: ¿Te refieres a información académica sobre estudiantes? (Ámbito ACADÉMICO)
Usuario: Sí, exacto
Chatbot: En el ámbito ACADÉMICO tenemos los siguientes cubos:
- MATRÍCULA: Información sobre estudiantes matriculados
- RENDIMIENTO: Datos de rendimiento académico
- EGRESADOS: Información sobre graduados
¿Qué información específica necesitas?
```

### 3.2 Flujo con Dudas
```
Usuario: No sé en qué ámbito buscar información sobre publicaciones
Chatbot: Te ayudo a encontrar el ámbito correcto. ¿Qué tipo de información buscas?
[Opción 1: Información sobre publicaciones científicas]
[Opción 2: Información sobre publicaciones docentes]
[Opción 3: Información sobre publicaciones administrativas]
Usuario: [Selecciona Opción 1]
Chatbot: Entonces deberías buscar en el ámbito de I+D+i, específicamente en el cubo PRODUCCIÓN CIENTÍFICA.
¿Quieres explorar las dimensiones y medidas disponibles?
```

### 3.3 Flujo de Exploración de Cubo
```
Usuario: ¿Qué información hay en el cubo MATRÍCULA?
Chatbot: El cubo MATRÍCULA contiene las siguientes dimensiones:
- Estudiante
- Asignatura
- Curso Académico
- Centro
- Titulación

Y las siguientes medidas:
- Número de Matriculados
- Créditos Matriculados
- Créditos Superados

¿Qué dimensión o medida te interesa explorar?
```

### 3.4 Flujo de Cruce de Datos
```
Usuario: Quiero cruzar información de RENDIMIENTO y EGRESADOS
Chatbot: Podemos cruzar datos de los cubos RENDIMIENTO y EGRESADOS en el ámbito ACADÉMICO.
Las dimensiones comunes son:
- Estudiante
- Titulación
- Curso Académico

¿Qué información específica necesitas cruzar?
```

## 4. Integración con Chainlit

### 4.1 Estructura de Integración
```python
from chainlit import cl
from typing import Dict

@cl.on_chat_start
async def on_chat_start():
    selector = SEGEDAAmbitoSelector()
    await cl.Message(
        content="¡Hola! Soy tu asistente para navegar por SEGEDA. ¿En qué ámbito te gustaría buscar información?",
        elements=[
            cl.Button(name="explorar", label="Explorar Ámbitos"),
            cl.Button(name="duda", label="No sé por dónde empezar")
        ]
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    selector = SEGEDAAmbitoSelector()
    
    if message.content.startswith("explorar"):
        await selector.iniciar_exploracion()
    elif message.content.startswith("duda"):
        resultado = await selector.procesar_duda(message.content)
        await mostrar_resultado(resultado)
    else:
        # Procesar mensaje normal
        respuesta = await selector.procesar_mensaje(message.content)
        await mostrar_resultado(respuesta)
```

## 5. Consideraciones de Implementación

### 5.1 Ventajas de Usar ChatterBot
- **Aprendizaje Continuo**: Mejora con cada interacción
- **Manejo de Contexto**: Mantiene el contexto de la conversación
- **Flexibilidad**: Se adapta a diferentes formas de preguntar
- **Personalización**: Se puede entrenar específicamente para SEGEDA

### 5.2 Desventajas y Soluciones
- **Precisión**: Puede requerir entrenamiento extensivo
  - Solución: Entrenar con ejemplos específicos de SEGEDA
- **Mantenimiento**: Necesita actualización periódica
  - Solución: Sistema de feedback y actualización automática
- **Complejidad**: Manejo de múltiples ámbitos y cubos
  - Solución: Estructura jerárquica clara

### 5.3 Recomendaciones
1. Implementar un sistema de feedback para mejorar el entrenamiento
2. Mantener un registro de conversaciones exitosas
3. Actualizar periódicamente el corpus de entrenamiento
4. Implementar un sistema de caché para respuestas comunes

## 6. Ejemplos de Uso Avanzado

### 6.1 Exploración de Dimensiones
```
Usuario: ¿Qué dimensiones tiene el cubo RENDIMIENTO?
Chatbot: El cubo RENDIMIENTO tiene las siguientes dimensiones:
- Estudiante
- Asignatura
- Curso Académico
- Centro
- Titulación
- Profesor

¿Qué dimensión te interesa explorar?
```

### 6.2 Cruce de Datos Complejo
```
Usuario: Quiero cruzar información de rendimiento con docencia
Chatbot: Podemos cruzar datos de los cubos RENDIMIENTO y DOCENCIA ASIGNATURA.
Las dimensiones comunes son:
- Asignatura
- Curso Académico
- Centro
- Titulación

¿Qué información específica necesitas cruzar?
```

## 7. Conclusión

La implementación de ChatterBot para la selección de ámbitos y navegación por cubos en SEGEDA ofrece:

1. **Experiencia Guiada**: Ayuda al usuario a encontrar la información correcta
2. **Flexibilidad**: Se adapta a diferentes niveles de conocimiento
3. **Aprendizaje**: Mejora con cada interacción
4. **Integración**: Se integra bien con el sistema existente

La clave del éxito está en:
- Un buen entrenamiento inicial
- Mantenimiento continuo del corpus
- Sistema de feedback efectivo
- Integración fluida con Chainlit y LangGraph 