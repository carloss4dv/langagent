"""
Aplicación Chainlit para interactuar con el agente de respuesta a preguntas.
No requiere FastAPI y se comunica directamente con el agente.
"""

import chainlit as cl
from chainlit.types import AskFileResponse
import pandas as pd
import os
import sys
import time
from typing import Dict, Any

# Añadir el directorio raíz al path para importar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar el agente
from core.lang_chain_agent import LangChainAgent

# Instanciar el agente
agent = LangChainAgent()

def format_sql_result(result_str):
    """
    Formatea el resultado SQL como una tabla si es posible.
    
    Args:
        result_str (str): String con el resultado SQL
        
    Returns:
        pd.DataFrame: DataFrame con los resultados si se puede parsear, None en caso contrario
    """
    try:
        # Si es una lista de tuplas (como los datos que compartió el usuario), convertirla a DataFrame
        if isinstance(result_str, list) and all(isinstance(item, tuple) for item in result_str):
            # Extraer los datos
            data = result_str
            
            # Inferir nombres de columnas según los datos
            # El ejemplo compartido parece tener: Categoría, Cantidad, Porcentaje, etc.
            columns = None
            if len(data) > 0 and len(data[0]) == 8:
                columns = [
                    "Categoría", "Cantidad", "Porcentaje", 
                    "Proyectos Internacionales", "Proyectos Nacionales", 
                    "Proyectos Autonómicos", "Total Fondos", "Porcentaje Fondos"
                ]
            
            # Crear un DataFrame con nombres de columnas
            df = pd.DataFrame(data, columns=columns)
            return df
        
        # Verificar si es un string que parece una tabla
        if isinstance(result_str, str) and "|" in result_str and "\n" in result_str:
            # Intentar convertir a dataframe
            lines = result_str.strip().split('\n')
            if len(lines) > 2:  # Al menos encabezado, separador y una fila
                # Extraer encabezados de la primera línea
                headers = [h.strip() for h in lines[0].split('|')]
                # Saltar la línea de separación (línea 1)
                # Crear filas desde la línea 2 en adelante
                data = []
                for line in lines[2:]:
                    if line.strip():  # Ignorar líneas vacías
                        row = [cell.strip() for cell in line.split('|')]
                        data.append(row)
                
                df = pd.DataFrame(data, columns=headers)
                return df
    except Exception as e:
        print(f"Error al formatear resultado SQL: {str(e)}")
    
    return None

@cl.on_chat_start
async def on_chat_start():
    """
    Inicializa el chat cuando un usuario se conecta.
    """
    # Mensaje de bienvenida
    await cl.Message(
        content="👋 ¡Hola! Soy el asistente de SEGEDA. ¿En qué puedo ayudarte?",
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """
    Procesa cada mensaje enviado por el usuario.
    
    Args:
        message: Mensaje del usuario
    """
    # Comprobar si el mensaje contiene datos en formato de lista de tuplas
    msg_content = message.content
    
    # Detectar si el mensaje tiene un formato específico que podría ser datos
    if "[(" in msg_content and ")]" in msg_content:
        try:
            # Intentar evaluar el contenido como estructura de datos Python
            data = eval(msg_content)
            
            # Verificar si es una lista de tuplas
            if isinstance(data, list) and all(isinstance(item, tuple) for item in data):
                # Crear DataFrame
                columns = None
                if len(data) > 0 and len(data[0]) == 8:
                    columns = [
                        "Categoría", "Cantidad", "Porcentaje", 
                        "Proyectos Internacionales", "Proyectos Nacionales", 
                        "Proyectos Autonómicos", "Total Fondos", "Porcentaje Fondos"
                    ]
                
                df = pd.DataFrame(data, columns=columns)
                
                # Mostrar tabla directamente
                await cl.Message(content="He detectado datos en formato tabular. Aquí está la tabla formateada:").send()
                await cl.Message(
                    content="Datos formateados:",
                    elements=[cl.Pandas(value=df, name="Datos")]
                ).send()
                return
        except:
            # Si falla la evaluación, continuar con el procesamiento normal
            pass
    
    # Mostrar que estamos procesando
    processing_msg = await cl.Message(content="Procesando tu consulta...").send()
    
    # Iniciar el temporizador para medir el tiempo de respuesta
    start_time = time.time()
    
    try:
        # Ejecutar el agente con la pregunta del usuario
        result = agent.run(message.content)
        
        # Calcular tiempo de respuesta
        response_time = time.time() - start_time
        
        # Eliminar el mensaje de procesamiento
        # El método update() no acepta content, así que eliminamos el mensaje
        try:
            await processing_msg.remove()
        except Exception as e:
            print(f"Error al eliminar mensaje de procesamiento: {str(e)}")
        
        # Verificar si fue una consulta SQL
        is_sql_query = result.get("is_consulta", False)
        sql_query = result.get("sql_query")
        sql_result = result.get("sql_result")
        
        # Elementos para mostrar información adicional
        elements = []
        
        # Si es una consulta SQL con resultados
        if is_sql_query and sql_query and sql_result:
            # Formatear el resultado SQL como DataFrame si es posible
            df = format_sql_result(sql_result)
            
            # Construir mensaje con la consulta SQL
            sql_message = f"### Consulta SQL generada:\n```sql\n{sql_query}\n```\n\n"
            
            if df is not None:
                # Añadir tabla al mensaje
                elements.append(
                    cl.Pandas(value=df, name="Resultados de la consulta")
                )
                sql_message += "### Resultados:\n\nLos resultados se muestran en la tabla adjunta."
            else:
                # Si no se pudo convertir a DataFrame, mostrar como texto
                sql_message += f"### Resultados:\n\n{sql_result}"
            
            # Enviar el mensaje con la consulta SQL y resultados
            await cl.Message(
                content=sql_message,
                elements=elements
            ).send()
        else:
            # Para respuestas normales, extraer la respuesta del campo generation
            answer = None
            
            if "generation" in result:
                generation = result["generation"]
                if isinstance(generation, dict) and "answer" in generation:
                    answer = generation["answer"]
                else:
                    answer = generation
            
            if answer is None and "response" in result:
                answer = result["response"]
                
            if answer is None:
                answer = "No se pudo generar una respuesta."
            
            # Enviar la respuesta al usuario
            await cl.Message(content=answer).send()
        
        # Mensaje con tiempo de respuesta
        await cl.Message(
            content=f"_Tiempo de respuesta: {response_time:.2f} segundos_",
            author="Sistema"
        ).send()
            
    except Exception as e:
        # Eliminar el mensaje de procesamiento en caso de error
        try:
            await processing_msg.remove()
        except Exception as err:
            print(f"Error al eliminar mensaje de procesamiento: {str(err)}")
        
        # En caso de error, enviar mensaje de error
        error_message = f"Error al generar respuesta: {str(e)}"
        await cl.Message(content=error_message).send()

def run_chainlit(port=8000):
    """
    Ejecuta la aplicación Chainlit.
    
    Args:
        port (int): Puerto para ejecutar la aplicación
    """
    import subprocess
    import sys
    
    # Construir el comando para ejecutar chainlit
    cmd = [
        sys.executable, "-m", "chainlit", "run", 
        os.path.abspath(__file__), 
        "--port", str(port),
        "--host", "0.0.0.0"
    ]
    
    # Ejecutar el comando
    subprocess.run(cmd)

if __name__ == "__main__":
    # Si se ejecuta directamente, lanzar Chainlit
    run_chainlit() 