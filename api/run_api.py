#!/usr/bin/env python
"""
Script para ejecutar la API FastAPI del agente.
"""

import uvicorn
from langagent.core.lang_chain_agent import LangChainAgent
from langagent.api.fastapi_app import create_api

if __name__ == "__main__":
    # Crear el agente
    agent = LangChainAgent()
    
    # Crear la aplicación FastAPI
    app = create_api(agent)
    
    # Ejecutar la API con uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 