# Investigación: Sistema de Selección de Ámbito Tradicional

## 1. Enfoque Propuesto

### 1.1 Visión General
El sistema propuesto separa la selección de ámbito en un componente independiente que:
- Guía al usuario en la selección del ámbito correcto
- No depende de inferencia por LLM
- Se integra con el workflow de LangGraph existente
- Proporciona una experiencia más controlada y predecible

### 1.2 Arquitectura Propuesta
```
Usuario -> Selección de Ámbito (Rasa) -> Workflow LangGraph (RAG)
```

## 2. Implementación con Rasa

### 2.1 Ventajas de Rasa
- Framework de código abierto para chatbots
- Permite crear flujos de conversación estructurados
- Fácil integración con APIs externas
- Soporte para múltiples idiomas
- Capacidad de manejar intenciones y entidades

### 2.2 Ejemplo de Implementación

#### 2.2.1 Estructura de Archivos
```
ambito_selector/
├── data/
│   ├── nlu.yml
│   └── stories.yml
├── domain.yml
├── config.yml
└── actions.py
```

#### 2.2.2 Ejemplo de Configuración

```yaml
# domain.yml
intents:
  - saludar
  - despedir
  - seleccionar_ambito
  - consultar_ambitos
  - confirmar_ambito
  - negar_ambito
  - solicitar_ayuda

entities:
  - ambito

slots:
  ambito_seleccionado:
    type: text
    mappings:
    - type: from_entity
      entity: ambito

responses:
  utter_saludar:
    - text: "¡Hola! Soy el asistente de SEGEDA. ¿En qué ámbito te gustaría consultar información?"
  
  utter_consultar_ambitos:
    - text: "Los ámbitos disponibles son:\n- Docencia\n- Investigación\n- Personal\n- Gestión\n¿Cuál te interesa?"

  utter_confirmar_ambito:
    - text: "Has seleccionado el ámbito de {ambito_seleccionado}. ¿Es correcto?"

  utter_ayuda_seleccion:
    - text: "Puedo ayudarte a encontrar el ámbito correcto. ¿Qué tipo de información necesitas consultar?"
```

#### 2.2.3 Ejemplo de Flujo de Conversación

```yaml
# stories.yml
stories:
- story: seleccion_ambito_directa
  steps:
  - intent: saludar
  - action: utter_saludar
  - intent: seleccionar_ambito
    entities:
    - ambito: "Docencia"
  - slot_was_set:
    - ambito_seleccionado: "Docencia"
  - action: utter_confirmar_ambito
  - intent: confirmar_ambito
  - action: action_pasar_a_langgraph

- story: seleccion_ambito_con_ayuda
  steps:
  - intent: saludar
  - action: utter_saludar
  - intent: solicitar_ayuda
  - action: utter_ayuda_seleccion
  - intent: informar_consulta
    entities:
    - tipo_consulta: "matrículas"
  - action: action_sugerir_ambito
  - intent: confirmar_ambito
  - action: action_pasar_a_langgraph
```

#### 2.2.4 Acciones Personalizadas

```python
# actions.py
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction

class ActionSugerirAmbito(Action):
    def name(self) -> Text:
        return "action_sugerir_ambito"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener el tipo de consulta
        tipo_consulta = tracker.get_slot("tipo_consulta")
        
        # Mapeo de tipos de consulta a ámbitos
        mapeo_consultas = {
            "matrículas": "Docencia",
            "asignaturas": "Docencia",
            "profesores": "Personal",
            "proyectos": "Investigación",
            "presupuesto": "Gestión"
        }
        
        ambito_sugerido = mapeo_consultas.get(tipo_consulta, "Docencia")
        
        dispatcher.utter_message(
            text=f"Basado en tu consulta sobre {tipo_consulta}, "
                 f"te sugiero el ámbito de {ambito_sugerido}. ¿Te parece correcto?"
        )
        
        return [SlotSet("ambito_seleccionado", ambito_sugerido)]

class ActionPasarALangGraph(Action):
    def name(self) -> Text:
        return "action_pasar_a_langgraph"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ambito = tracker.get_slot("ambito_seleccionado")
        
        # Aquí se implementaría la integración con LangGraph
        # Por ejemplo, llamando a una API que inicie el workflow
        
        dispatcher.utter_message(
            text=f"Perfecto, procederé a buscar la información en el ámbito de {ambito}."
        )
        
        return []
```

## 3. Integración con Chainlit

### 3.1 Enfoque de Integración
1. El usuario inicia la conversación en Chainlit
2. Si no especifica ámbito, se activa el bot de Rasa
3. Una vez seleccionado el ámbito, se pasa al workflow de LangGraph

### 3.2 Ejemplo de Integración

```python
# chainlit_app.py
import chainlit as cl
from rasa.core.agent import Agent
from rasa.core.interpreter import RasaNLUInterpreter
import asyncio

# Inicializar agente Rasa
interpreter = RasaNLUInterpreter("ambito_selector/models/nlu")
agent = Agent.load("ambito_selector/models/dialogue", interpreter=interpreter)

@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content="👋 ¡Hola! Soy el asistente de SEGEDA. ¿En qué ámbito te gustaría consultar información?",
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    # Verificar si el mensaje contiene un ámbito
    if not message.content.lower().startswith(("docencia", "investigación", "personal", "gestión")):
        # Si no especifica ámbito, usar Rasa
        response = await agent.handle_text(message.content)
        await cl.Message(content=response[0].get("text")).send()
    else:
        # Si especifica ámbito, pasar directamente a LangGraph
        # Implementar lógica de LangGraph aquí
        pass
```

## 4. Ventajas del Enfoque Propuesto

1. **Mayor Control**: El flujo de selección de ámbito es más predecible y controlado
2. **Mejor Experiencia de Usuario**: Guía paso a paso para usuarios que no conocen los ámbitos
3. **Separación de Responsabilidades**: Cada componente (selección de ámbito y RAG) se especializa en su tarea
4. **Mantenibilidad**: Más fácil de mantener y modificar que un sistema basado en LLM
5. **Eficiencia**: Menor consumo de recursos al no usar LLM para selección de ámbito

## 5. Consideraciones Adicionales

### 5.1 Manejo de Errores
- Implementar sistema de fallback para casos no cubiertos
- Proporcionar ayuda contextual cuando el usuario se confunde
- Mantener historial de selecciones para aprendizaje

### 5.2 Mejoras Futuras
- Añadir sistema de feedback para mejorar sugerencias
- Implementar aprendizaje de preferencias del usuario
- Integrar con sistema de búsqueda para sugerir ámbitos basados en palabras clave

### 5.3 Limitaciones
- Requiere mantenimiento de reglas y flujos de conversación
- Menos flexible que un sistema basado en LLM
- Necesita actualización manual de nuevos ámbitos o categorías

## 6. Conclusión

El enfoque propuesto ofrece una alternativa más estructurada y controlada a la selección de ámbito mediante LLM. La integración de Rasa con el workflow existente de LangGraph permite mantener la potencia del RAG mientras se proporciona una experiencia más guiada para la selección de ámbito.

La implementación requiere un esfuerzo inicial en la configuración de Rasa, pero ofrece beneficios a largo plazo en términos de mantenibilidad, control y experiencia de usuario. 