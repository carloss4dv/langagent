"""
Aplicación Streamlit para interactuar con el agente de respuesta a preguntas.
"""

import streamlit as st
import requests
import json
import os
import pandas as pd

# Configuración de la API
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Configurar la página
st.set_page_config(
    page_title="SEGEDA - Asistente Inteligente",
    page_icon="🤖",
    layout="wide"
)

# Estilos personalizados
st.markdown("""
<style>
    .title {
        text-align: center;
        color: #1E88E5;
        font-size: 2.5rem;
    }
    .subtitle {
        text-align: center;
        color: #424242;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .stTextInput>div>div>input {
        font-size: 18px;
    }
    .answer-container {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
    }
    .sql-container {
        background-color: #e9f5e9;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
    }
    .sql-query {
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 10px;
        font-family: monospace;
        overflow-x: auto;
    }
</style>
""", unsafe_allow_html=True)

# Título de la aplicación
st.markdown("<h1 class='title'>SEGEDA - Asistente Inteligente</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Consulta información de la Universidad de Zaragoza</p>", unsafe_allow_html=True)

# Función para obtener token
def get_token(username):
    try:
        response = requests.post(
            f"{API_URL}/token",
            json={"username": username}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            st.error(f"Error al obtener token: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error de conexión: {str(e)}")
        return None

# Función para hacer consulta
def query_agent(question, token):
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.post(
            f"{API_URL}/generate",
            headers=headers,
            json={"question": question}
        )
        
        if response.status_code == 200:
            try:
                # Intentar parsear como JSON primero
                return response.json()
            except:
                # Si no es JSON, devolver el texto directamente (retrocompatibilidad)
                return {"type": "text", "answer": response.text}
        else:
            st.error(f"Error en la consulta: {response.status_code}")
            try:
                error_detail = response.json().get("detail", "Sin detalles")
                return {"type": "error", "message": f"Error: {error_detail}"}
            except:
                return {"type": "error", "message": f"Error: Código {response.status_code}"}
    except Exception as e:
        return {"type": "error", "message": f"Error de conexión: {str(e)}"}

# Función para mostrar la respuesta según su tipo
def display_response(response):
    if not response:
        return
    
    # Si la respuesta es un string, asumimos que es texto plano (retrocompatibilidad)
    if isinstance(response, str):
        st.markdown("<div class='answer-container'>", unsafe_allow_html=True)
        st.markdown("### Respuesta:")
        st.write(response)
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # Obtener el tipo de respuesta
    response_type = response.get("type", "text")
    
    if response_type == "sql":
        # Mostrar resultado SQL
        sql_query = response.get("query", "")
        sql_result = response.get("result", "")
        explanation = response.get("explanation", "")
        
        st.markdown("<div class='sql-container'>", unsafe_allow_html=True)
        
        # Mostrar explicación si está disponible
        if explanation:
            st.markdown("### Explicación:")
            st.write(explanation)
        
        st.markdown("### Consulta SQL generada:")
        st.markdown(f"<div class='sql-query'>{sql_query}</div>", unsafe_allow_html=True)
        
        st.markdown("### Resultado:")
        
        # Intentar convertir el resultado a un dataframe si es posible
        try:
            # Verificar si es un string que parece una tabla
            if isinstance(sql_result, str) and "|" in sql_result and "\n" in sql_result:
                # Intentar convertir a dataframe
                lines = sql_result.strip().split('\n')
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
                    st.dataframe(df)
                else:
                    st.write(sql_result)  # Mostrar como texto si no se puede parsear
            else:
                # Si no tiene formato de tabla, mostrar como texto
                st.write(sql_result)
        except Exception as e:
            # Si falla la conversión, mostrar como texto plano
            st.write(sql_result)
            st.caption(f"No se pudo formatear como tabla: {str(e)}")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    elif response_type == "error":
        # Mostrar mensaje de error
        st.error(response.get("message", "Error desconocido"))
    
    else:
        # Mostrar respuesta de texto normal
        st.markdown("<div class='answer-container'>", unsafe_allow_html=True)
        st.markdown("### Respuesta:")
        st.write(response.get("answer", "No se pudo obtener una respuesta"))
        st.markdown("</div>", unsafe_allow_html=True)

# Verificar si ya hay un token en la sesión
if "token" not in st.session_state:
    # Solicitar nombre de usuario para obtener token
    with st.form("login_form"):
        username = st.text_input("Nombre de usuario", value="demo")
        submit = st.form_submit_button("Iniciar sesión")
        
        if submit:
            token = get_token(username)
            if token:
                st.session_state.token = token
                st.success("¡Sesión iniciada correctamente!")
                st.experimental_rerun()

# Si ya hay un token, mostrar la interfaz de consulta
if "token" in st.session_state:
    # Input para la pregunta
    question = st.text_input("¿Qué quieres saber sobre la Universidad de Zaragoza?", 
                           placeholder="Ej: ¿Qué tipos de programas de movilidad existen para estudiantes?")
    
    # Botón para enviar la pregunta
    if st.button("Consultar") or question:
        if question:
            with st.spinner("Generando respuesta..."):
                # Hacer la consulta al agente
                response = query_agent(question, st.session_state.token)
                
                # Mostrar la respuesta según su tipo
                display_response(response)
        else:
            st.warning("Por favor, introduce una pregunta.")
    
    # Botón para cerrar sesión
    if st.sidebar.button("Cerrar sesión"):
        del st.session_state.token
        st.experimental_rerun()
    
    # Mostrar algunas preguntas de ejemplo
    with st.sidebar:
        st.markdown("### Preguntas de ejemplo")
        example_questions = [
            "¿Cuántos tipos de programas de movilidad existen para estudiantes de la Universidad de Zaragoza?",
            "¿Cómo puedo saber si una universidad de destino pertenece a la alianza UNITA?",
            "¿Qué métricas permiten evaluar el rendimiento de los estudiantes?",
            "¿Qué información se recoge sobre los estudiantes extranjeros que vienen a la Universidad de Zaragoza?",
            "¿Cómo se contabilizan las renuncias a movilidad en el sistema?"
        ]
        
        for q in example_questions:
            if st.button(q, key=f"q_{q[:20]}"):
                st.session_state.last_question = q
                st.experimental_rerun()
        
    # Si hay una pregunta seleccionada, ejecutarla
    if "last_question" in st.session_state:
        question = st.session_state.last_question
        del st.session_state.last_question
        with st.spinner("Generando respuesta..."):
            response = query_agent(question, st.session_state.token)
            
            # Mostrar la pregunta
            st.markdown(f"### Pregunta: {question}")
            
            # Mostrar la respuesta según su tipo
            display_response(response) 