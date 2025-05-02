# Investigación: Selección de Ámbitos mediante Conversación

## 1. Frameworks Conversacionales en Python

### 1.1 Rasa
- **Descripción**: Framework open-source para construir asistentes conversacionales
- **Ventajas**:
  - Muy flexible y personalizable
  - Soporte para NLU (Natural Language Understanding)
  - Fácil integración con APIs externas
  - Buena documentación
- **Ejemplo de uso**:
```python
from rasa.core.agent import Agent
from rasa.core.interpreter import RasaNLUInterpreter

# Cargar el modelo entrenado
interpreter = RasaNLUInterpreter("models/nlu")
agent = Agent.load("models/dialogue", interpreter=interpreter)

# Procesar mensaje
responses = agent.handle_text("¿En qué ámbito quieres buscar información?")
```

### 1.2 Botpress
- **Descripción**: Plataforma de código abierto para chatbots
- **Ventajas**:
  - Interfaz visual para diseño de flujos
  - Fácil integración con Python
  - Soporte para múltiples canales
- **Ejemplo de uso**:
```python
from botpress import Botpress

bot = Botpress("http://localhost:3000")
response = bot.send_message("user123", "¿En qué ámbito quieres buscar información?")
```

### 1.3 ChatterBot
- **Descripción**: Biblioteca de machine learning para generar respuestas
- **Ventajas**:
  - Fácil de implementar
  - Aprendizaje automático
  - No requiere configuración compleja
- **Ejemplo de uso**:
```python
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

chatbot = ChatBot('AmbitoSelector')
trainer = ChatterBotCorpusTrainer(chatbot)
trainer.train("chatterbot.corpus.spanish")

response = chatbot.get_response("¿En qué ámbito quieres buscar información?")
```

## 2. Enfoque Personalizado con Chainlit

### 2.1 Estructura Propuesta
```python
from chainlit import cl
from typing import Dict, List

class AmbitoSelector:
    def __init__(self):
        self.ambitos = {
            "docencia": {
                "nombre": "Docencia",
                "descripcion": "Información sobre asignaturas, profesores, etc.",
                "palabras_clave": ["asignatura", "profesor", "clase", "docencia"]
            },
            "investigacion": {
                "nombre": "Investigación",
                "descripcion": "Información sobre proyectos, publicaciones, etc.",
                "palabras_clave": ["proyecto", "investigación", "publicación"]
            }
            # ... más ámbitos
        }
        
    async def iniciar_seleccion(self):
        await cl.Message(
            content="¿En qué ámbito te gustaría buscar información?",
            elements=[
                cl.Button(name=ambito, label=info["nombre"])
                for ambito, info in self.ambitos.items()
            ]
        ).send()
    
    async def procesar_seleccion(self, ambito: str):
        if ambito in self.ambitos:
            return self.ambitos[ambito]
        return None
```

### 2.2 Integración con Chainlit
```python
@cl.on_chat_start
async def on_chat_start():
    selector = AmbitoSelector()
    await selector.iniciar_seleccion()

@cl.on_message
async def on_message(message: cl.Message):
    if message.content.startswith("Seleccionar ámbito:"):
        ambito = message.content.split(":")[1].strip()
        selector = AmbitoSelector()
        resultado = await selector.procesar_seleccion(ambito)
        if resultado:
            # Iniciar el workflow de LangGraph con el ámbito seleccionado
            await iniciar_langgraph_workflow(resultado)
```

## 3. Ejemplo de Flujo Conversacional

### 3.1 Flujo Básico
1. Usuario inicia la conversación
2. Sistema muestra lista de ámbitos disponibles
3. Usuario selecciona un ámbito
4. Sistema confirma la selección
5. Se inicia el workflow de LangGraph

### 3.2 Flujo con Dudas
1. Usuario inicia la conversación
2. Sistema muestra lista de ámbitos
3. Usuario indica que no está seguro
4. Sistema muestra descripciones detalladas
5. Sistema hace preguntas guía
6. Usuario selecciona ámbito
7. Se inicia el workflow de LangGraph

## 4. Integración con LangGraph

### 4.1 Punto de Integración
```python
async def iniciar_langgraph_workflow(ambito_seleccionado: Dict):
    # Configurar el estado inicial del workflow
    initial_state = {
        "question": "Consulta del usuario",
        "ambito": ambito_seleccionado["nombre"],
        "relevant_cubos": ambito_seleccionado["cubos"]
    }
    
    # Iniciar el workflow de LangGraph
    workflow = create_workflow(...)
    result = await workflow.arun(initial_state)
    
    # Procesar resultado
    await cl.Message(content=result["generation"]).send()
```

## 5. Consideraciones de Implementación

### 5.1 Ventajas del Enfoque
- Mayor control sobre el flujo de selección
- Mejor experiencia de usuario
- Más fácil de mantener y modificar
- Separación clara de responsabilidades

### 5.2 Desventajas
- Requiere más código
- Menos flexible que el enfoque basado en LLM
- Necesita mantenimiento manual de las reglas

### 5.3 Recomendaciones
1. Implementar un sistema de caché para respuestas comunes
2. Mantener un registro de selecciones previas
3. Implementar un sistema de feedback
4. Añadir capacidad de búsqueda en ámbitos

## 6. Ejemplos de Uso

### 6.1 Caso Simple
```
Usuario: Quiero buscar información sobre matriculados
Sistema: ¿En qué ámbito te gustaría buscar esta información?
[Botones: Docencia, Investigación, Personal, etc.]
Usuario: [Selecciona Docencia]
Sistema: Has seleccionado el ámbito de Docencia. ¿Qué información específica necesitas?
```

### 6.2 Caso con Dudas
```
Usuario: No sé en qué ámbito buscar
Sistema: Te ayudo a encontrar el ámbito correcto. ¿Qué tipo de información buscas?
[Opción 1: Información sobre asignaturas y clases]
[Opción 2: Información sobre proyectos y publicaciones]
[Opción 3: Información sobre personal y recursos]
Usuario: [Selecciona Opción 1]
Sistema: Entonces deberías buscar en el ámbito de Docencia. ¿Quieres proceder?
```

## 7. Frameworks Adicionales a Considerar

### 7.1 Streamlit
- **Ventajas**:
  - Fácil de implementar
  - Interfaz web atractiva
  - Buena integración con Python
- **Ejemplo**:
```python
import streamlit as st

def main():
    st.title("Selector de Ámbitos")
    ambito = st.selectbox(
        "Selecciona un ámbito",
        ["Docencia", "Investigación", "Personal"]
    )
    if st.button("Confirmar"):
        st.session_state.ambito = ambito
```

### 7.2 Gradio
- **Ventajas**:
  - Interfaz web simple
  - Fácil de implementar
  - Buena para prototipos
- **Ejemplo**:
```python
import gradio as gr

def seleccionar_ambito(ambito):
    return f"Has seleccionado: {ambito}"

interface = gr.Interface(
    fn=seleccionar_ambito,
    inputs=gr.Dropdown(["Docencia", "Investigación", "Personal"]),
    outputs="text"
)
```

## 8. Conclusión

El enfoque tradicional para la selección de ámbitos, implementado como un componente separado del workflow de LangGraph, ofrece varias ventajas:

1. Mayor control sobre el flujo de selección
2. Mejor experiencia de usuario
3. Separación clara de responsabilidades
4. Facilidad de mantenimiento

La implementación recomendada sería:
1. Usar Chainlit como base para la interfaz conversacional
2. Implementar un selector de ámbitos personalizado
3. Integrar con el workflow de LangGraph existente
4. Mantener un registro de selecciones y feedback

Este enfoque permite una experiencia más guiada y controlada, mientras mantiene la potencia del sistema RAG para la generación de respuestas. 