# Frontend Streamlit para SEGEDA

<div align="center">
  <img src="../../logos/NEAT-AMBIENCE-logo.png" alt="NEAT-AMBIENCE Logo" width="300"/>
  <br>
  <em>Interfaz web para el sistema de respuesta a preguntas SEGEDA</em>
</div>

Este módulo proporciona una interfaz web construida con Streamlit para interactuar con el agente de respuesta a preguntas SEGEDA, facilitando el acceso a la información de la Universidad de Zaragoza.

## 🌟 Descripción

El frontend Streamlit ofrece una interfaz gráfica intuitiva para interactuar con el agente de respuesta a preguntas. Permite a los usuarios formular preguntas naturales sobre la Universidad de Zaragoza y recibir respuestas detalladas basadas en los documentos procesados por el sistema.

## 📋 Requisitos

```
streamlit>=1.32.0
requests>=2.31.0
```

## 🚀 Instalación

1. Asegúrate de tener instaladas las dependencias:

```bash
pip install streamlit requests
```

2. El módulo está listo para usarse.

## 💻 Uso

### Método 1: Ejecutar con el script auxiliar

Usa el script `run_streamlit.py` para iniciar la aplicación:

```bash
python frontend/streamlit/run_streamlit.py
```

Opciones disponibles:

- `--api-url`: URL de la API del agente (predeterminado: http://localhost:8000)
- `--port`: Puerto para ejecutar Streamlit (predeterminado: 8501)

Ejemplo:

```bash
python frontend/streamlit/run_streamlit.py --api-url http://localhost:8000 --port 8502
```

### Método 2: Ejecutar directamente con Streamlit

También puedes ejecutar la aplicación directamente con Streamlit:

```bash
streamlit run frontend/streamlit/app.py
```

En este caso, asegúrate de configurar la variable de entorno `API_URL` si la API no se ejecuta en la URL predeterminada:

```bash
# En Linux/Mac:
export API_URL=http://localhost:8000
streamlit run frontend/streamlit/app.py

# En Windows:
set API_URL=http://localhost:8000
streamlit run frontend/streamlit/app.py
```

## 🔄 Funcionamiento

1. La aplicación solicitará un nombre de usuario para autenticarse y obtener un token
2. Una vez autenticado, se mostrará la interfaz de consulta
3. Puedes escribir preguntas directamente o usar los ejemplos disponibles en la barra lateral
4. El backend procesará la pregunta y devolverá una respuesta
5. La respuesta se mostrará en la interfaz

## 📊 Características principales

- **Autenticación integrada**: Sistema de login con generación de tokens JWT
- **Interfaz amigable**: Diseño intuitivo y responsive para facilitar las consultas
- **Ejemplos predefinidos**: Colección de preguntas de ejemplo para probar el sistema
- **Visualización de respuestas**: Formato claro para las respuestas del agente
- **Gestión de sesiones**: Mantenimiento del estado de la sesión entre interacciones

## 🔍 Integración con bases de datos vectoriales

El frontend Streamlit se comunica con el backend del agente, que puede utilizar diferentes bases de datos vectoriales:

### Chroma DB
- Base de datos vectorial para entornos locales o de desarrollo
- Óptima para despliegues rápidos y prototipado
- Almacenamiento local de embeddings (carpeta física)
- Más sencilla de configurar y mantener
- Idónea para conjuntos de datos más pequeños

### Milvus
- Base de datos vectorial escalable y distribuida
- Optimizada para entornos de producción y grandes conjuntos de datos
- Soporte para búsqueda semántica avanzada
- Mayor rendimiento con grandes volúmenes de documentos
- Permite colecciones unificadas para búsqueda multidimensional

El frontend funciona de manera transparente con ambas opciones, ya que se comunica con la API independientemente de la base de datos vectorial que esté utilizando el backend.

## ⚙️ Configuración avanzada

### Personalización de la interfaz
El código de la aplicación Streamlit permite personalizar:
- Colores y estilos mediante CSS personalizado
- Título y subtítulo de la aplicación
- Mensajes de la interfaz
- Lista de preguntas de ejemplo

### Variables de entorno
La aplicación utiliza las siguientes variables de entorno:
- `API_URL`: URL base de la API del agente

## ⚠️ Notas importantes

- La API debe estar en ejecución antes de iniciar la aplicación Streamlit
- Para iniciar la API, ejecuta:
  ```
  python api/run_api.py
  ```
- Si cambias el puerto de la API, asegúrate de actualizar también la configuración de Streamlit
- Para entornos de producción, considera usar un servidor proxy como Nginx frente a Streamlit

<div align="center">
  <img src="../../logos/cosmos-logo.png" alt="Cosmos Logo" width="100"/>
  <p>Desarrollado por Carlos de Vera Sanz</p>
  <p>Universidad de Zaragoza - COSMOS</p>
</div> 