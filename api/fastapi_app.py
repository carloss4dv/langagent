"""
Módulo para la API FastAPI.

Este módulo implementa la API REST utilizando FastAPI para exponer
las funcionalidades del agente de respuesta a preguntas.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Dict, Any

from langagent.auth.authentication import verify_token, create_token
from langagent.core.lang_chain_agent import LangChainAgent

# Modelos de datos para la API
class QuestionRequest(BaseModel):
    """Modelo para solicitudes de preguntas."""
    question: str

class TokenRequest(BaseModel):
    """Modelo para solicitudes de token."""
    username: str

# Configuración de seguridad
security = HTTPBearer()

def create_api(agent=None):
    """
    Crea una aplicación FastAPI con las rutas necesarias.
    
    Args:
        agent: Instancia de LangChainAgent. Si es None, se creará uno nuevo.
        
    Returns:
        FastAPI: Aplicación FastAPI configurada.
    """
    app = FastAPI()
    
    # Si no se proporciona un agente, crear uno
    if agent is None:
        agent = LangChainAgent()
    
    @app.post("/token")
    async def get_token(request: TokenRequest):
        """
        Genera un token de autenticación.
        
        Args:
            request (TokenRequest): Solicitud con nombre de usuario.
            
        Returns:
            dict: Token generado correctmanete.
        """
        # En un entorno real, verificaríamos credenciales aquí
        token = create_token(data={"sub": request.username})
        return {"access_token": token, "token_type": "bearer"}
    
    @app.post("/generate")
    async def generate(request: QuestionRequest, payload: Dict = Depends(verify_token)):
        """
        Genera una respuesta a una pregunta utilizando el agente.
        
        Args:
            request (QuestionRequest): Solicitud con la pregunta.
            payload (Dict): Payload del token verificado.
            
        Returns:
            dict: Respuesta generada.
        """
        try:
            # Ejecutar el agente con la pregunta
            result = agent.run(request.question)
            
            # Extraer la respuesta de la generación
            answer = None
            
            # Intentar extraer la respuesta del campo generation
            if "generation" in result:
                generation = result["generation"]
                
                # Si generation es un diccionario con el campo answer
                if isinstance(generation, dict) and "answer" in generation:
                    answer = generation["answer"]
                # Si generation es un string en formato JSON con el campo answer
                elif isinstance(generation, str) and '"answer":' in generation:
                    try:
                        import json
                        import re
                        
                        # Intenta encontrar el JSON que contiene el campo answer
                        json_match = re.search(r'\{.*"answer":\s*"([^"]*)".*\}', generation)
                        if json_match:
                            answer = json_match.group(1)
                        else:
                            # Intenta parsear como JSON completo
                            try:
                                if generation.strip().startswith('{') and generation.strip().endswith('}'):
                                    json_data = json.loads(generation)
                                    if "answer" in json_data:
                                        answer = json_data["answer"]
                            except:
                                pass
                    except:
                        # Si hay algún error en el parsing, usar la generación completa
                        answer = generation
                else:
                    # Si generation no tiene un formato reconocible, usarlo directamente
                    answer = generation
            
            # Si no se pudo extraer la respuesta del campo generation, intentar con response
            if answer is None and "response" in result:
                answer = result["response"]
                
            # Si tampoco se encontró en response, devolver un mensaje por defecto
            if answer is None:
                answer = "No se pudo generar una respuesta."
            
            # Devolver solamente la respuesta como solicitado
            return answer
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al generar respuesta: {str(e)}"
            )
    
    return app
