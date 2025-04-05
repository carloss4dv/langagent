"""
Módulo para la autenticación en la API.

Este módulo proporciona funciones para la autenticación y autorización
en la API utilizando tokens JWT.
"""

from datetime import datetime, timedelta
from authlib.jose import jwt, JoseError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from langagent.config.config import SECURITY_CONFIG, API_CONFIG

# Configuración de seguridad
security = HTTPBearer()

def create_token(data: dict, expires_delta: timedelta = None):
    """
    Crea un token JWT para autenticación.
    
    Args:
        data (dict): Datos a incluir en el token.
        expires_delta (timedelta, optional): Tiempo de expiración del token.
        
    Returns:
        str: Token JWT generado.
    """
    # Usar valor de configuración si no se proporciona expires_delta
    if expires_delta is None:
        expires_delta = timedelta(minutes=API_CONFIG["token_expiration_minutes"])
        
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    header = {"alg": SECURITY_CONFIG["algorithm"]}
    encoded_jwt = jwt.encode(header, to_encode, SECURITY_CONFIG["secret_key"])
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifica un token JWT.
    
    Args:
        credentials (HTTPAuthorizationCredentials): Credenciales de autorización.
        
    Returns:
        dict: Payload del token si es válido.
        
    Raises:
        HTTPException: Si el token es inválido o ha expirado.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECURITY_CONFIG["secret_key"])
        return payload
    except JoseError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
