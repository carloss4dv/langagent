"""
Módulo para la integración con Rasa y el selector de ámbitos.
"""

import requests
from typing import Dict, Any, Optional, List
import time

class RasaClient:
    def __init__(self, rasa_url: str = "http://localhost:5005"):
        self.rasa_url = rasa_url
        self.session_id = None

    def send_message(self, message: str) -> Dict[str, Any]:
        """
        Envía un mensaje a Rasa y obtiene la respuesta.
        
        Args:
            message (str): Mensaje del usuario
            
        Returns:
            Dict[str, Any]: Respuesta de Rasa
        """
        if not self.session_id:
            self.session_id = f"chainlit_{int(time.time())}"
            
        response = requests.post(
            f"{self.rasa_url}/webhooks/rest/webhook",
            json={"sender": self.session_id, "message": message}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error al comunicarse con Rasa: {response.status_code}")

    def get_ambitos(self) -> Dict[str, str]:
        """
        Obtiene la lista de ámbitos disponibles.
        
        Returns:
            Dict[str, str]: Diccionario con los ámbitos y sus descripciones
        """
        response = self.send_message("mostrar ámbitos")
        if response and len(response) > 0:
            # Extraer los ámbitos del mensaje de respuesta
            message = response[0].get("text", "")
            ambitos = {}
            for line in message.split("\n"):
                if line.startswith("- "):
                    parts = line[2:].split(": ", 1)
                    if len(parts) == 2:
                        ambitos[parts[0]] = parts[1]
            return ambitos
        return {}

    def get_cubos(self, ambito: str) -> Dict[str, str]:
        """
        Obtiene los cubos disponibles para un ámbito específico.
        
        Args:
            ambito (str): Ámbito seleccionado
            
        Returns:
            Dict[str, str]: Diccionario con los cubos y sus descripciones
        """
        response = self.send_message(f"mostrar cubos de {ambito}")
        if response and len(response) > 0:
            message = response[0].get("text", "")
            cubos = {}
            for line in message.split("\n"):
                if line.startswith("- "):
                    parts = line[2:].split(": ", 1)
                    if len(parts) == 2:
                        cubos[parts[0]] = parts[1]
            return cubos
        return {}

    def get_dimensiones(self, cubo: str) -> List[str]:
        """
        Obtiene las dimensiones disponibles para un cubo específico.
        
        Args:
            cubo (str): Cubo seleccionado
            
        Returns:
            List[str]: Lista de dimensiones disponibles
        """
        response = self.send_message(f"mostrar dimensiones de {cubo}")
        if response and len(response) > 0:
            message = response[0].get("text", "")
            dimensiones = []
            for line in message.split("\n"):
                if line.startswith("- "):
                    dimensiones.append(line[2:])
            return dimensiones
        return [] 