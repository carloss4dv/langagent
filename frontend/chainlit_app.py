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

def df_to_markdown(df):
    """
    Convierte un DataFrame a formato markdown para mostrar como tabla.
    La tabla se formatea para ocupar el ancho completo disponible.
    
    Args:
        df: DataFrame de pandas
        
    Returns:
        str: Tabla en formato markdown
    """
    if df.empty:
        return "No hay datos disponibles."
    
    # Determinar si la tabla es lo suficientemente amplia para necesitar scroll horizontal
    needs_scroll = len(df.columns) > 5 or df.shape[1] * df.shape[0] > 50
    
    # Iniciar la tabla con un contenedor de overflow cuando sea necesario
    if needs_scroll:
        markdown = '<div class="overflow-container">\n\n'
    else:
        markdown = ""
    
    # Convertir DataFrame a tabla markdown
    markdown += "| " + " | ".join(str(col) for col in df.columns) + " |\n"
    markdown += "| " + " | ".join(["---"] * len(df.columns)) + " |\n"
    
    # Añadir filas y truncar contenido muy largo
    for _, row in df.iterrows():
        row_values = []
        for val in row.values:
            # Convertir el valor a string y truncar si es muy largo
            str_val = str(val)
            if len(str_val) > 50:  # Limitar longitud para evitar celdas muy anchas
                str_val = str_val[:47] + "..."
            row_values.append(str_val)
        
        markdown += "| " + " | ".join(row_values) + " |\n"
    
    # Cerrar el div si se abrió
    if needs_scroll:
        markdown += "\n</div>"
    
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
    
    # Determinar si la tabla es lo suficientemente amplia para necesitar scroll horizontal
    needs_scroll = len(df.columns) > 5 or df.shape[1] * df.shape[0] > 50
    
    # Contenedor con scroll si es necesario
    container_start = '<div class="overflow-container">' if needs_scroll else ''
    container_end = '</div>' if needs_scroll else ''
    
    # Usar el método to_html de pandas con estilo personalizado
    html = df.to_html(index=False, border=0, classes="data-table")
    
    return f"{container_start}{html}{container_end}"

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
    
    # Verificar si el mensaje contiene una consulta SQL en JSON
    sql_query = None
    if "{" in msg_content and "sql" in msg_content:
        try:
            # Intentar extraer la consulta SQL
            match = re.search(r'\{[^}]*"sql"\s*:\s*"([^"]*)"[^}]*\}', msg_content)
            if match:
                sql_query = match.group(1)
        except:
            pass
    
    # Detectar si el mensaje tiene un formato específico que podría ser datos
    if "[(" in msg_content and ")]" in msg_content:
        try:
            # Extraer datos
            data = extract_tuples_from_text(msg_content)
            
            if data:
                # Crear DataFrame con nombres de columnas apropiados
                columns = None
                
                # Si tenemos una consulta SQL, intentar extraer los nombres de columnas
                if sql_query:
                    columns = extract_column_names_from_sql(sql_query)
                    if columns and len(columns) != len(data[0]):
                        columns = None  # Descartar si no coincide el número de columnas
                
                # Si no tenemos columnas de la consulta, usar nombres inferidos
                if not columns and len(data) > 0:
                    if len(data[0]) == 8:
                        # Detectar si la consulta contiene palabras clave específicas
                        if sql_query and "horas_impartidas" in sql_query:
                            columns = [
                                "Categoría PDI", "Cantidad", "Porcentaje", 
                                "Profesores Primer Curso", "Sexenios Acumulados", 
                                "Quinquenios Acumulados", "Horas Impartidas", "Porcentaje Horas"
                            ]
                        else:
                            columns = [
                                "Categoría", "Cantidad", "Porcentaje", 
                                "Proyectos Internacionales", "Proyectos Nacionales", 
                                "Proyectos Autonómicos", "Total Fondos (K€)", "Porcentaje Fondos"
                            ]
                
                # Crear DataFrame
                df = pd.DataFrame(data, columns=columns)
                
                # Aplicar formato
                for col in df.columns:
                    col_name = str(col).lower()
                    if "porcentaje" in col_name:
                        df[col] = df[col].apply(lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else x)
                    elif "fondos" in col_name and "porcentaje" not in col_name:
                        df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)
                    elif df[col].dtype == float:
                        df[col] = df[col].apply(lambda x: f"{x:.2f}" if isinstance(x, float) else x)
                
                # Convertir DataFrame a formato markdown para mostrar directamente
                markdown_table = df_to_markdown(df)
                
                # Mostrar tabla directamente como markdown
                await cl.Message(content=markdown_table).send()
                
                # Si hay una consulta SQL, mostrarla
                if sql_query:
                    await cl.Message(
                        content=f"```sql\n{sql_query}\n```",
                        author="Consulta SQL"
                    ).send()
                
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
            # Formatear el resultado SQL como DataFrame usando los nombres de columnas de la consulta
            df = format_sql_result(sql_result, sql_query)
            
            # Construir mensaje solo con la tabla si tenemos datos
            if not df.empty:
                # Convertir a markdown para mostrar directamente
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