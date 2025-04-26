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
import re
import ast
import json
from typing import Dict, Any, List, Tuple, Union

# Añadir el directorio raíz al path para importar los módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar el agente
from core.lang_chain_agent import LangChainAgent

# Instanciar el agente
agent = LangChainAgent()

def extract_tuples_from_text(text: str) -> List[Tuple]:
    """
    Extrae tuplas de un texto que podría ser una representación de lista de tuplas
    
    Args:
        text (str): Texto con posibles tuplas
        
    Returns:
        List[Tuple]: Lista de tuplas extraídas o lista vacía si no se encuentra el patrón
    """
    try:
        # Intentar evaluar directamente si tiene formato Python válido
        if text.strip().startswith('[') and text.strip().endswith(']'):
            data = ast.literal_eval(text)
            if isinstance(data, list) and all(isinstance(item, tuple) for item in data):
                return data
        
        # Si falla, intentar extraer con regex
        pattern = r'\(\s*([^)]+)\s*\)'
        matches = re.findall(pattern, text)
        
        result = []
        for match in matches:
            # Separar elementos de la tupla
            elements = []
            parts = match.split(',')
            
            for part in parts:
                part = part.strip()
                # Intentar convertir a número si es posible
                try:
                    # Si es un número entero
                    if part.isdigit():
                        elements.append(int(part))
                    # Si es un número decimal
                    elif part.replace('.', '', 1).isdigit():
                        elements.append(float(part))
                    # Si es un string con comillas
                    elif (part.startswith("'") and part.endswith("'")) or (part.startswith('"') and part.endswith('"')):
                        elements.append(part[1:-1])
                    # Otros casos, dejarlo como string sin comillas
                    else:
                        elements.append(part)
                except:
                    elements.append(part)
            
            result.append(tuple(elements))
        
        return result
    except:
        return []

def format_sql_result(result_str: Union[str, List[Tuple]]) -> pd.DataFrame:
    """
    Formatea el resultado SQL como una tabla.
    
    Args:
        result_str: String con el resultado SQL o lista de tuplas
        
    Returns:
        pd.DataFrame: DataFrame con los resultados
    """
    try:
        # Si ya es una lista de tuplas
        if isinstance(result_str, list) and all(isinstance(item, tuple) for item in result_str):
            data = result_str
        else:
            # Intentar extraer tuplas del texto
            data = extract_tuples_from_text(result_str)
        
        if data:
            # Inferir nombres de columnas según los datos del ejemplo de personal docente
            columns = None
            if len(data) > 0 and len(data[0]) == 8:
                columns = [
                    "Categoría", "Cantidad", "Porcentaje", 
                    "Proyectos Internacionales", "Proyectos Nacionales", 
                    "Proyectos Autonómicos", "Total Fondos (K€)", "Porcentaje Fondos"
                ]
            
            # Crear un DataFrame 
            df = pd.DataFrame(data, columns=columns)
            
            # Aplicar formato a los números
            for col in df.columns:
                # Si la columna parece contener porcentajes
                if "Porcentaje" in col:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x)
                # Si la columna parece contener valores monetarios
                elif "Fondos" in col and "Porcentaje" not in col:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
            
            return df
        
        # Verificar si es un string que parece una tabla
        if isinstance(result_str, str) and "|" in result_str and "\n" in result_str:
            # Intentar convertir a dataframe
            lines = result_str.strip().split('\n')
            if len(lines) > 2:  # Al menos encabezado, separador y una fila
                # Extraer encabezados de la primera línea
                headers = [h.strip() for h in lines[0].split('|') if h.strip()]
                # Saltar la línea de separación (línea 1)
                # Crear filas desde la línea 2 en adelante
                data = []
                for line in lines[2:]:
                    if line.strip():  # Ignorar líneas vacías
                        row = [cell.strip() for cell in line.split('|') if cell.strip()]
                        if row:  # Solo añadir si hay datos
                            data.append(row)
                
                if headers and data:
                    # Asegurar que todas las filas tengan la misma longitud que los headers
                    clean_data = []
                    for row in data:
                        if len(row) == len(headers):
                            clean_data.append(row)
                        elif len(row) < len(headers):
                            # Rellenar con valores vacíos
                            clean_data.append(row + [''] * (len(headers) - len(row)))
                        else:
                            # Recortar
                            clean_data.append(row[:len(headers)])
                    
                    df = pd.DataFrame(clean_data, columns=headers)
                    return df
    except Exception as e:
        print(f"Error al formatear resultado SQL: {str(e)}")
    
    # Si todo falla, devolver un DataFrame vacío
    return pd.DataFrame()

def df_to_markdown(df):
    """
    Convierte un DataFrame a formato markdown para mostrar como tabla.
    
    Args:
        df: DataFrame de pandas
        
    Returns:
        str: Tabla en formato markdown
    """
    if df.empty:
        return "No hay datos disponibles."
    
    # Convertir DataFrame a tabla markdown
    markdown = "| " + " | ".join(str(col) for col in df.columns) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(df.columns)) + " |\n"
    
    # Añadir filas
    for _, row in df.iterrows():
        markdown += "| " + " | ".join(str(val) for val in row.values) + " |\n"
    
    return markdown

def df_to_html(df):
    """
    Convierte un DataFrame a HTML para mostrar como tabla.
    
    Args:
        df: DataFrame de pandas
        
    Returns:
        str: Tabla en formato HTML
    """
    if df.empty:
        return "<p>No hay datos disponibles.</p>"
    
    # Usar el método to_html de pandas con estilo básico
    html = df.to_html(index=False, border=0, classes="table table-striped table-hover")
    return f"""
    <style>
    .table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 1em;
    }}
    .table-striped tbody tr:nth-of-type(odd) {{
        background-color: rgba(0, 0, 0, 0.05);
    }}
    .table-hover tbody tr:hover {{
        background-color: rgba(0, 0, 0, 0.075);
    }}
    .table th, .table td {{
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }}
    .table th {{
        background-color: #f2f2f2;
        font-weight: bold;
    }}
    </style>
    {html}
    """

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
            # Extraer datos
            data = extract_tuples_from_text(msg_content)
            
            if data:
                # Crear DataFrame con nombres de columnas apropiados
                columns = None
                if len(data) > 0 and len(data[0]) == 8:
                    columns = [
                        "Categoría", "Cantidad", "Porcentaje", 
                        "Proyectos Internacionales", "Proyectos Nacionales", 
                        "Proyectos Autonómicos", "Total Fondos (K€)", "Porcentaje Fondos"
                    ]
                
                df = pd.DataFrame(data, columns=columns)
                
                # Aplicar formato
                for col in df.columns:
                    if "Porcentaje" in col:
                        df[col] = df[col].apply(lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x)
                    elif "Fondos" in col and "Porcentaje" not in col:
                        df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
                
                # Convertir DataFrame a formato markdown para mostrar directamente
                markdown_table = df_to_markdown(df)
                
                # Mostrar tabla directamente como markdown
                await cl.Message(content=markdown_table).send()
                return
        except Exception as e:
            print(f"Error al procesar tuplas: {str(e)}")
            # Si falla, continuar con el procesamiento normal
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
        try:
            await processing_msg.remove()
        except Exception as e:
            print(f"Error al eliminar mensaje de procesamiento: {str(e)}")
        
        # Verificar si fue una consulta SQL
        is_sql_query = result.get("is_consulta", False)
        sql_query = result.get("sql_query")
        sql_result = result.get("sql_result")
        
        # Si es una consulta SQL con resultados
        if is_sql_query and sql_query and sql_result:
            # Formatear el resultado SQL como DataFrame
            df = format_sql_result(sql_result)
            
            # Construir mensaje solo con la tabla si tenemos datos
            if not df.empty:
                # Convertir a markdown o html para mostrar directamente
                markdown_table = df_to_markdown(df)
                
                # Mostrar los resultados como tabla markdown
                await cl.Message(content=f"### Resultados:\n\n{markdown_table}").send()
            else:
                # Si no pudimos formatear como tabla, mostrar el texto original
                await cl.Message(content=f"### Resultados:\n\n{sql_result}").send()
            
            # Mensaje con tiempo de respuesta (enviar antes de la consulta SQL)
            await cl.Message(
                content=f"_Tiempo de respuesta: {response_time:.2f} segundos_",
                author="Sistema"
            ).send()
            
            # Mensaje con la consulta SQL al final
            await cl.Message(
                content=f"```sql\n{sql_query}\n```",
                author="Consulta SQL"
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
        
        # En caso de error, enviar mensaje de error detallado
        error_message = f"Error al generar respuesta: {str(e)}"
        print(f"Error detallado: {e}")
        
        import traceback
        trace = traceback.format_exc()
        print(f"Traceback: {trace}")
        
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