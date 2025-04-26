# Frontend para SEGEDA

Este directorio contiene los frontends para interactuar con el agente de SEGEDA.

## Frontends disponibles

Actualmente hay dos frontends disponibles:

1. **Streamlit**: Frontend original con autenticación y comunicación a través de FastAPI
2. **Chainlit**: Nuevo frontend más moderno y sin necesidad de API FastAPI

## Chainlit (Recomendado)

Chainlit proporciona una interfaz de chat moderna y fácil de usar que se comunica directamente con el agente de SEGEDA sin necesidad de FastAPI.

### Características principales

- Interfaz de chat moderna y reactiva
- Soporte para visualización de tablas y dataframes
- Manejo directo del agente sin pasar por API
- Mejor formato para resultados SQL

### Instalación

Asegúrate de haber instalado las dependencias:

```bash
pip install -r requirements.txt
```

### Ejecución

Para ejecutar el frontend Chainlit:

```bash
python frontend/run_chainlit.py
```

Por defecto se ejecutará en el puerto 8000. Puedes especificar otro puerto:

```bash
python frontend/run_chainlit.py --port 8080
```

### Acceso

Una vez iniciado, abre en tu navegador:

```
http://localhost:8000
```

## Streamlit (Frontend original)

El frontend de Streamlit requiere la API FastAPI en ejecución para funcionar.

### Ejecución

1. Primero, inicia la API:

```bash
python api/run_api.py
```

2. Luego, inicia Streamlit:

```bash
python frontend/streamlit/run_streamlit.py
```

### Acceso

Abre en tu navegador:

```
http://localhost:8501
```

## Comparación

| Característica | Chainlit | Streamlit |
|----------------|----------|-----------|
| Diseño | Chat moderno | Formulario tradicional |
| Autenticación | No incluida | Integrada |
| Requiere API | No | Sí |
| Tablas | Mejor formato | Formato básico |
| Tiempo de respuesta | Muestra tiempo | No muestra | 