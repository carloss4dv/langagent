import chainlit as cl
from agents.segeda_selector import SEGEDASelector

# Inicializar el selector de SEGEDA
selector = SEGEDASelector()

@cl.on_chat_start
async def on_chat_start():
    """
    Inicializa la conversación cuando el usuario inicia el chat
    """
    await cl.Message(
        content="¡Hola! Soy tu asistente para navegar por SEGEDA. ¿En qué ámbito te gustaría buscar información?",
        elements=[
            cl.Button(name="explorar", label="Explorar Ámbitos"),
            cl.Button(name="duda", label="No sé por dónde empezar")
        ]
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """
    Procesa los mensajes del usuario y genera respuestas
    """
    if message.content.startswith("explorar"):
        # Mostrar todos los ámbitos disponibles
        elementos = []
        for ambito, info in selector.ambitos.items():
            elementos.append(
                cl.Button(
                    name=f"ambito_{ambito}",
                    label=f"{ambito}: {info['descripcion']}"
                )
            )
        await cl.Message(
            content="Estos son los ámbitos disponibles en SEGEDA:",
            elements=elementos
        ).send()
    
    elif message.content.startswith("duda"):
        await cl.Message(
            content="Te ayudo a encontrar el ámbito correcto. ¿Qué tipo de información necesitas?",
            elements=[
                cl.Button(name="estudiantes", label="Información sobre estudiantes"),
                cl.Button(name="profesores", label="Información sobre profesores"),
                cl.Button(name="investigacion", label="Información sobre investigación"),
                cl.Button(name="movilidad", label="Información sobre movilidad"),
                cl.Button(name="personal", label="Información sobre personal")
            ]
        ).send()
    
    elif message.content.startswith("ambito_"):
        # Extraer el ámbito del nombre del botón
        ambito = message.content.replace("ambito_", "")
        if ambito in selector.ambitos:
            info = selector.ambitos[ambito]
            elementos = []
            for cubo in info["cubos"]:
                elementos.append(
                    cl.Button(
                        name=f"cubo_{cubo}",
                        label=cubo
                    )
                )
            await cl.Message(
                content=f"En el ámbito {ambito} tenemos los siguientes cubos:",
                elements=elementos
            ).send()
    
    elif message.content.startswith("cubo_"):
        # Extraer el cubo del nombre del botón
        cubo = message.content.replace("cubo_", "")
        resultado = await selector.explorar_cubo(cubo)
        await cl.Message(
            content=resultado["mensaje"],
            elements=[
                cl.Button(name="volver_ambitos", label="Volver a Ámbitos"),
                cl.Button(name="cruzar_datos", label="Cruzar con otro cubo")
            ]
        ).send()
    
    else:
        # Procesar consulta normal
        resultado = await selector.procesar_consulta(message.content)
        
        if resultado["tipo"] == "ambito_sugerido":
            elementos = []
            for cubo in resultado["cubos"]:
                elementos.append(
                    cl.Button(
                        name=f"cubo_{cubo}",
                        label=cubo
                    )
                )
            await cl.Message(
                content=resultado["mensaje"],
                elements=elementos
            ).send()
        else:
            await cl.Message(
                content=resultado["mensaje"],
                elements=[
                    cl.Button(name="explorar", label="Explorar Ámbitos"),
                    cl.Button(name="duda", label="No sé por dónde empezar")
                ]
            ).send() 