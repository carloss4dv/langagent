"""
Aplicación Chainlit para interactuar con el agente de respuesta a preguntas.
Integra el selector de ámbitos con Rasa.
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

# Importar el cliente de Rasa
from frontend.rasa_integration import RasaClient

# Instanciar el agente
agent = LangChainAgent()

# Instanciar el cliente de Rasa
rasa_client = RasaClient()

def extract_column_names_from_sql(sql_query: str) -> List[str]:
    """
    Extrae los nombres de las columnas de una consulta SQL.
    
    Args:
        sql_query (str): Consulta SQL
        
    Returns:
        List[str]: Lista de nombres de columnas
    """
    try:
        # Si la consulta está en formato JSON, extraer la consulta
        if sql_query.strip().startswith('{') and 'sql' in sql_query:
            try:
                query_data = json.loads(sql_query)
                if "sql" in query_data:
                    sql_query = query_data["sql"]
            except:
                pass  # Si falla el parseo JSON, usar la consulta tal como está
        
        # Intentar encontrar la selección principal de la consulta (ignorando CTE)
        main_select_pattern = r'SELECT\s+(?:DISTINCT\s+)?([^;]*?)(?:FROM|$)'
        
        # Buscar primero después de un 'WITH ... )' o un patrón que indica el final de un CTE
        cte_end_positions = [m.end() for m in re.finditer(r'\)\s*(?:,|\s*SELECT)', sql_query, re.IGNORECASE | re.DOTALL)]
        
        if cte_end_positions:
            # Si hay CTEs, buscar el SELECT después del último CTE
            select_part = re.search(main_select_pattern, sql_query[max(cte_end_positions):], re.IGNORECASE | re.DOTALL)
            if select_part:
                select_part = select_part.group(1)
            else:
                # Si no encuentra el SELECT después del CTE, buscar en toda la consulta
                select_part_match = re.search(main_select_pattern, sql_query, re.IGNORECASE | re.DOTALL)
                select_part = select_part_match.group(1) if select_part_match else ""
        else:
            # Si no hay CTEs, buscar el SELECT directamente
            select_part_match = re.search(main_select_pattern, sql_query, re.IGNORECASE | re.DOTALL)
            select_part = select_part_match.group(1) if select_part_match else ""
        
        if not select_part:
            return []
        
        # Dividir las columnas y limpiar
        columns = []
        
        # Manejar SQL con múltiples líneas y comentarios
        lines = select_part.split('\n')
        clean_lines = []
        for line in lines:
            # Eliminar comentarios de una línea
            line = re.sub(r'--.*$', '', line)
            if line.strip():
                clean_lines.append(line)
        
        select_part = ' '.join(clean_lines)
        
        # Analizar cada columna en la parte SELECT
        level = 0
        current_column = ""
        
        for char in select_part:
            if char == '(':
                level += 1
                current_column += char
            elif char == ')':
                level -= 1
                current_column += char
            elif char == ',' and level == 0:
                columns.append(current_column.strip())
                current_column = ""
            else:
                current_column += char
        
        if current_column.strip():
            columns.append(current_column.strip())
        
        # Extraer los alias (nombres de columna)
        column_names = []
        for col in columns:
            # Buscar un alias explícito con AS
            as_match = re.search(r'(?:AS|as)\s+[\'\"]?([^\s\'\",]*)[\'\"]?$', col.strip())
            if as_match:
                column_names.append(as_match.group(1).strip())
            else:
                # Buscar un alias implícito (sin AS)
                implicit_match = re.search(r'(?:\)|\w|\*)\s+[\'\"]?([^\s\'\",]*)[\'\"]?$', col.strip())
                if implicit_match and implicit_match.group(1) and implicit_match.group(1).lower() not in ['from', 'where', 'group', 'order', 'having']:
                    column_names.append(implicit_match.group(1).strip())
                else:
                    # Si no hay alias, usar el nombre completo o parte final
                    parts = col.strip().split('.')
                    if len(parts) > 1:
                        # Si es como 'tabla.columna', usar 'columna'
                        column_names.append(parts[-1].strip())
                    else:
                        # Usar la columna completa como último recurso
                        simplified = col.strip()
                        # Si es una función como COUNT(*), extraer un nombre más legible
                        func_match = re.match(r'(\w+)\(', simplified)
                        if func_match:
                            column_names.append(func_match.group(1).lower())
                        else:
                            column_names.append(simplified)
        
        # Formatear nombres de columnas para hacerlos más legibles
        formatted_names = []
        for name in column_names:
            # Convertir nombres en snake_case a Title Case
            formatted = ' '.join(word.capitalize() for word in name.split('_'))
            formatted_names.append(formatted)
        
        return formatted_names
    except Exception as e:
        print(f"Error al extraer nombres de columnas: {str(e)}")
        return []

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

def format_sql_result(result_str: Union[str, List[Tuple]], sql_query: str = None) -> pd.DataFrame:
    """
    Formatea el resultado SQL como una tabla.
    
    Args:
        result_str: String con el resultado SQL o lista de tuplas
        sql_query: Consulta SQL para extraer nombres de columnas
        
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
            # Extraer nombres de columnas de la consulta SQL si está disponible
            columns = None
            if sql_query:
                extracted_columns = extract_column_names_from_sql(sql_query)
                if extracted_columns and len(extracted_columns) == len(data[0]):
                    columns = extracted_columns
            
            # Si no podemos extraer columnas de la consulta o no coinciden, usar inferencia
            if not columns:
                if len(data) > 0 and len(data[0]) == 8:
                    # Para el caso específico del ejemplo de personal docente
                    columns = [
                        "Categoría", "Cantidad", "Porcentaje", 
                        "Proyectos Internacionales", "Proyectos Nacionales", 
                        "Proyectos Autonómicos", "Total Fondos (K€)", "Porcentaje Fondos"
                    ]
                    
                    # Verificar si la consulta contiene palabras clave que sugieran otras columnas
                    if sql_query and "horas_impartidas" in sql_query:
                        columns = [
                            "Categoría PDI", "Cantidad", "Porcentaje", 
                            "Profesores Primer Curso", "Sexenios Acumulados", 
                            "Quinquenios Acumulados", "Horas Impartidas", "Porcentaje Horas"
                        ]
            
            # Crear un DataFrame 
            df = pd.DataFrame(data, columns=columns)
            
            # Aplicar formato a los números
            for col in df.columns:
                col_name = str(col).lower()
                # Si la columna parece contener porcentajes
                if "porcentaje" in col_name:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x)
                # Si la columna parece contener valores monetarios
                elif "fondos" in col_name and "porcentaje" not in col_name:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
                # Si contiene valores numéricos pero no son enteros
                elif df[col].dtype == float:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, float) else x)
            
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

def create_markdown_table(df):
    """
    Crea una tabla en formato markdown a partir de un DataFrame
    
    Args:
        df: DataFrame de pandas
        
    Returns:
        str: Tabla en formato markdown
    """
    if df.empty:
        return "No hay datos disponibles."
    
    # Crear encabezados
    markdown = "| " + " | ".join(str(col) for col in df.columns) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(df.columns)) + " |\n"
    
    # Añadir filas
    for _, row in df.iterrows():
        row_values = []
        for val in row.values:
            # Convertir el valor a string
            str_val = str(val)
            row_values.append(str_val)
        
        markdown += "| " + " | ".join(row_values) + " |\n"
    
    return markdown

def parse_tabulated_data(text):
    """
    Parsea datos en formato de tabla con separación por tabulaciones.
    
    Args:
        text: Texto con datos tabulados
        
    Returns:
        pd.DataFrame: DataFrame con los datos parseados
    """
    lines = text.strip().split('\n')
    if len(lines) < 2:
        return pd.DataFrame()
    
    # Primera línea como cabecera
    headers = [h.strip() for h in lines[0].split('\t')]
    
    # Resto de líneas como datos
    data = []
    for i in range(1, len(lines)):
        if lines[i].strip():
            cells = [c.strip() for c in lines[i].split('\t')]
            # Asegurar que la fila tiene el mismo número de columnas que los encabezados
            if len(cells) < len(headers):
                cells.extend([''] * (len(headers) - len(cells)))
            elif len(cells) > len(headers):
                cells = cells[:len(headers)]
            data.append(cells)
    
    # Crear DataFrame
    df = pd.DataFrame(data, columns=headers)
    
    # Convertir columnas numéricas
    for col in df.columns:
        try:
            # Verificar si la columna contiene valores numéricos
            if df[col].str.replace('.', '', 1).str.replace('%', '', 1).str.isdigit().all():
                # Si la columna contiene porcentajes
                if df[col].str.contains('%').any():
                    df[col] = df[col].str.replace('%', '').astype(float)
                    df[col] = df[col].apply(lambda x: f"{x:.2f}%")
                else:
                    # Convertir a numérico
                    df[col] = pd.to_numeric(df[col], errors='ignore')
                    
                    # Si es decimal, formatear con 2 decimales
                    if df[col].dtype == float:
                        df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, float) else x)
        except:
            # Si hay error, mantener como está
            pass
    
    return df

@cl.on_chat_start
async def on_chat_start():
    """Inicializa la conversación y muestra los ámbitos disponibles."""
    # Obtener los ámbitos disponibles
    ambitos = rasa_client.get_ambitos()
    
    if not ambitos:
        await cl.Message(
            content="No se pudieron obtener los ámbitos disponibles. Por favor, intente más tarde."
        ).send()
        return
    
    # Crear el mensaje con los ámbitos
    message = "Bienvenido al selector de ámbitos. Los ámbitos disponibles son:\n\n"
    for ambito, descripcion in ambitos.items():
        message += f"- **{ambito}**: {descripcion}\n"
    message += "\n¿Qué ámbito te interesa consultar?"
    
    await cl.Message(content=message).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Procesa los mensajes del usuario y maneja la selección de ámbitos y cubos."""
    user_message = message.content
    
    # Verificar si es una selección de ámbito
    if user_message.upper() in ["ACADÉMICO", "ADMISIÓN", "DOCTORADO", "ESTUDIOS PROPIOS", 
                              "DOCENCIA", "I+D+i", "MOVILIDAD", "RRHH"]:
        ambito = user_message.upper()
        cubos = rasa_client.get_cubos(ambito)
        
        if not cubos:
            await cl.Message(
                content=f"No se encontraron cubos para el ámbito {ambito}. Por favor, intente con otro ámbito."
            ).send()
            return
        
        # Mostrar los cubos disponibles
        response = f"Has seleccionado el ámbito {ambito}. Los cubos disponibles son:\n\n"
        for cubo, descripcion in cubos.items():
            response += f"- **{cubo}**: {descripcion}\n"
        response += "\n¿Qué cubo te interesa consultar?"
        
        await cl.Message(content=response).send()
        return
    
    # Verificar si es una selección de cubo
    # Aquí deberíamos mantener un estado de la conversación para saber si estamos
    # en la selección de cubos o en otra parte del flujo
    # Por ahora, asumimos que cualquier mensaje que no sea un ámbito es una consulta
    # que se enviará a Rasa
    
    response = rasa_client.send_message(user_message)
    if response and len(response) > 0:
        await cl.Message(content=response[0].get("text", "")).send()
    else:
        await cl.Message(
            content="Lo siento, no pude procesar tu mensaje. Por favor, intenta de nuevo."
        ).send()

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