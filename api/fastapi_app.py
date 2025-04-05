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

# Modelos de datos para la API
class QuestionRequest(BaseModel):
    """Modelo para solicitudes de preguntas."""
    question: str

class TokenRequest(BaseModel):
    """Modelo para solicitudes de token."""
    username: str

# Configuración de seguridad
security = HTTPBearer()

def create_api(workflow):
    """
    Crea una aplicación FastAPI con las rutas necesarias.
    
    Args:
        workflow: Flujo de trabajo del agente.
        
    Returns:
        FastAPI: Aplicación FastAPI configurada.
    """
    app = FastAPI()
    
    @app.post("/token")
    async def get_token(request: TokenRequest):
        """
        Genera un token de autenticación.
        
        Args:
            request (TokenRequest): Solicitud con nombre de usuario.
            
        Returns:
            dict: Token generado.
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
            # Ejecutar el flujo de trabajo
            inputs = {"question": request.question}
            result = None
            
            # Capturar el último resultado del flujo
            for output in workflow.stream(inputs):
                result = output
            
            # Extraer la generación final
            final_output = list(result.values())[0]
            
            # Si después de 3 intentos no hay una respuesta satisfactoria, devolver la pregunta
            if final_output.get("retry_count", 0) >= 3:
                return {
                    "answer": f"No pude encontrar una respuesta satisfactoria a: {request.question}",
                    "retry_count": final_output.get("retry_count", 0)
                }
            
            return {
                "answer": final_output.get("generation", ""),
                "retry_count": final_output.get("retry_count", 0)
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al generar respuesta: {str(e)}"
            )
    
    return app
