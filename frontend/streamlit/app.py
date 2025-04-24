"""
Aplicación Streamlit para interactuar con el agente de respuesta a preguntas.
"""

import streamlit as st
import requests
import json
import os

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
            return response.text  # La API ya devuelve directamente la respuesta
        else:
            st.error(f"Error en la consulta: {response.status_code}")
            try:
                error_detail = response.json().get("detail", "Sin detalles")
                return f"Error: {error_detail}"
            except:
                return f"Error: Código {response.status_code}"
    except Exception as e:
        return f"Error de conexión: {str(e)}"

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
                answer = query_agent(question, st.session_state.token)
                
                # Mostrar la respuesta
                st.markdown("<div class='answer-container'>", unsafe_allow_html=True)
                st.markdown("### Respuesta:")
                st.write(answer)
                st.markdown("</div>", unsafe_allow_html=True)
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
            answer = query_agent(question, st.session_state.token)
            
            # Mostrar la respuesta
            st.markdown("<div class='answer-container'>", unsafe_allow_html=True)
            st.markdown(f"### Pregunta: {question}")
            st.markdown("### Respuesta:")
            st.write(answer)
            st.markdown("</div>", unsafe_allow_html=True) 