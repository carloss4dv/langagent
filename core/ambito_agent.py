"""
Agente especializado en la identificación de ámbitos y cubos relevantes.
Utiliza LangGraph para manejar el flujo de conversación y recuperación de información.
"""

from typing import Dict, List, Optional, Tuple, TypedDict
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from langagent.models.constants import (
    AMBITOS_CUBOS, 
    CUBO_TO_AMBITO, 
    AMBITO_KEYWORDS,
    AMBITO_EN_ES
)
from langagent.models.llm import create_clarification_generator
import re

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

class AmbitoState(TypedDict):
    """Estado del agente de ámbito."""
    question: str
    ambito: Optional[str]
    cubos: List[str]
    confidence: float
    context: List[Document]
    needs_clarification: bool
    clarification_question: Optional[str]
    is_visualization: bool

def create_ambito_workflow(retriever: any, llm: any):
    """
    Crea un workflow para identificar el ámbito y cubos relevantes.
    
    Args:
        retriever: Retriever para recuperar documentos
        llm: Modelo de lenguaje a utilizar
        
    Returns:
        StateGraph: Grafo de estado configurado
    """
    workflow = StateGraph(AmbitoState)
    
    # Crear el generador de clarificación usando las prompts mejoradas
    clarification_generator = create_clarification_generator(llm)
    
    def identify_ambito(state: AmbitoState) -> AmbitoState:
        """
        Identifica el ámbito y cubos relevantes basados en la pregunta.
        """
        question = state["question"]
        question_lower = question.lower()
        
        # Inicializar is_visualization y needs_clarification
        state["is_visualization"] = False
        state["needs_clarification"] = False
        state["clarification_question"] = None
        
        # Palabras clave para identificar visualizaciones
        visualization_keywords = [
            "gráfico", "grafico", "gráfica", "grafica", "visualizar", "mostrar gráficamente",
            "diagrama", "tabla", "estadística", "estadistica", "distribución", "distribucion",
            "tendencia", "evolución", "evolucion", "comparar", "comparación", "comparacion"
        ]
        
        # Verificar si es una solicitud de visualización
        if any(keyword in question_lower for keyword in visualization_keywords):
            state["is_visualization"] = True
        
        # Buscar referencias explícitas a ámbitos
        explicit_ambito_pattern = r"(?:ámbito|ambito)\s+(\w+)"
        ambito_matches = re.findall(explicit_ambito_pattern, question_lower)
        
        # Verificar ámbitos explícitos
        for match in ambito_matches:
            ambito_key = match.lower().replace(" ", "_")
            if ambito_key in AMBITOS_CUBOS:
                state["ambito"] = ambito_key
                state["cubos"] = AMBITOS_CUBOS[ambito_key]["cubos"]
                state["confidence"] = 1.0
                return state
        
        # Buscar keywords de ámbitos
        ambito_scores = {}
        for ambito, keywords in AMBITO_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > 0:
                ambito_scores[ambito] = score
        
        if ambito_scores:
            # Seleccionar el ámbito con mayor puntuación
            selected_ambito = max(ambito_scores.items(), key=lambda x: x[1])[0]
            state["ambito"] = selected_ambito
            state["cubos"] = AMBITOS_CUBOS[selected_ambito]["cubos"]
            state["confidence"] = max(ambito_scores.values()) / len(AMBITO_KEYWORDS[selected_ambito])
            return state
        
        # Si no se encuentra un ámbito claro, buscar en la base de conocimiento
        state["needs_clarification"] = True
        state["confidence"] = 0.0  # Añadir confidence cuando no se puede identificar el ámbito
        state["clarification_question"] = "No he podido identificar claramente el ámbito. ¿Podrías especificar en qué ámbito te gustaría consultar información?"
        return state
    
    def retrieve_context(state: AmbitoState) -> AmbitoState:
        """
        Recupera contexto relevante para ayudar a identificar el ámbito.
        """
            
        question = state["question"]
        logger.info(f"---RETRIEVE CONTEXT FOR AMBITO---")
        logger.info(f"Pregunta: {question}")
        
        try:
            # Recuperar documentos usando el retriever
            docs = retriever.invoke(question)
            
            if docs:
                # LÓGICA MEJORADA: Analizar documentos con priorización
                ambito_counts = {}
                relevance_scores = {}
                
                for i, doc in enumerate(docs[:5]):  # Analizar más documentos
                    
                    # Extraer ámbito del metadata
                    if 'ambito' in doc.metadata:
                        ambito = doc.metadata['ambito']
                        
                        # Calcular puntuación de relevancia basada en la posición del documento
                        relevance_weight = 1.0 / (i + 1)  # Documentos más arriba tienen más peso
                        
                        # Si ya teníamos un ámbito identificado, darle prioridad
                        if state.get("ambito") == ambito:
                            relevance_weight *= 2.0  # Doble peso si coincide con ámbito previo
                        
                        # Verificar keywords específicas en el contenido
                        content_lower = doc.page_content.lower()
                        if ambito in AMBITO_KEYWORDS:
                            keyword_matches = sum(1 for keyword in AMBITO_KEYWORDS[ambito] 
                                                if keyword in content_lower)
                            if keyword_matches > 0:
                                relevance_weight *= (1 + keyword_matches * 0.2)
                        
                        ambito_counts[ambito] = ambito_counts.get(ambito, 0) + 1
                        relevance_scores[ambito] = relevance_scores.get(ambito, 0) + relevance_weight
                
                logger.info(f"Ámbitos encontrados: {ambito_counts}")
                logger.info(f"Puntuaciones de relevancia: {relevance_scores}")
                
                # Seleccionar ámbito basado en relevancia, no solo frecuencia
                if relevance_scores:
                    # Si ya teníamos un ámbito y aparece en los resultados, mantenerlo
                    if state.get("ambito") and state["ambito"] in relevance_scores:
                        selected_ambito = state["ambito"]
                        logger.info(f"Manteniendo ámbito previo: {selected_ambito}")
                    else:
                        # Seleccionar el de mayor puntuación de relevancia
                        selected_ambito = max(relevance_scores.items(), key=lambda x: x[1])[0]
                        logger.info(f"Ámbito seleccionado por relevancia: {selected_ambito}")
                    
                    # Verificar que el ámbito existe en nuestras constantes
                    if selected_ambito in AMBITOS_CUBOS:
                        state["ambito"] = selected_ambito
                        state["cubos"] = AMBITOS_CUBOS[selected_ambito]["cubos"]
                        
                        # Calcular confianza basada en relevancia y frecuencia
                        max_relevance = max(relevance_scores.values())
                        confidence = min(0.9, 0.6 + (max_relevance / 5.0))  # Entre 0.6 y 0.9
                        
                        state["confidence"] = confidence
                        state["needs_clarification"] = False
                        state["clarification_question"] = None
                        logger.info(f"Ámbito actualizado: {selected_ambito}, Cubos: {state['cubos']}, Confianza: {confidence}")
            
            state["context"] = docs if docs else []
            
        except Exception as e:
            logger.error(f"Error al recuperar contexto: {str(e)}")
            logger.error(f"Tipo de retriever: {type(retriever)}")
            state["context"] = []
            
        return state
    
    def generate_clarification(state: AmbitoState) -> AmbitoState:
        """
        Genera una pregunta de clarificación si es necesario.
        """
        if not state["needs_clarification"]:
            return state
            
        # Generar pregunta de clarificación usando el generador mejorado
        try:
            # Preparar el contexto para el generador
            context_text = ""
            if state.get("context"):
                context_text = "\n".join([doc.page_content for doc in state["context"][:3]])  # Limitar a 3 documentos
            
            # Usar el generador de clarificación con las prompts mejoradas
            response = clarification_generator.invoke({
                "question": state["question"],
                "context": context_text
            })
            
            # Extraer el contenido de la respuesta
            if hasattr(response, 'content'):
                state["clarification_question"] = response.content
            else:
                state["clarification_question"] = str(response)
                
        except Exception as e:
            logger.error(f"Error al generar clarificación: {str(e)}")
            # Fallback a pregunta genérica
            state["clarification_question"] = "No he podido identificar claramente el ámbito. ¿Podrías especificar en qué ámbito te gustaría consultar información?"
            
        return state
    
    # Añadir nodos al grafo
    workflow.add_node("identify_ambito", identify_ambito)
    workflow.add_node("retrieve_context", retrieve_context)
    workflow.add_node("generate_clarification", generate_clarification)
    
    # Definir el flujo
    workflow.set_entry_point("identify_ambito")
    
    def should_retrieve_context(state: AmbitoState) -> str:
        """Determina si se necesita recuperar contexto."""
        return "retrieve_context" if state["confidence"] < 0.7 else "END"
    
    def should_generate_clarification(state: AmbitoState) -> str:
        """Determina si se necesita generar una pregunta de clarificación."""
        return "generate_clarification" if state["needs_clarification"] else "END"
    
    # Añadir bordes condicionales
    workflow.add_conditional_edges(
        "identify_ambito",
        should_retrieve_context,
        {
            "retrieve_context": "retrieve_context",
            "END": END
        }
    )
    
    workflow.add_conditional_edges(
        "retrieve_context",
        should_generate_clarification,
        {
            "generate_clarification": "generate_clarification",
            "END": END
        }
    )
    
    workflow.add_edge("generate_clarification", END)
    
    return workflow 