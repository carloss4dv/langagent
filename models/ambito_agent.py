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
import re

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

def create_ambito_workflow(retrievers: Dict[str, any], llm: any):
    """
    Crea un workflow para identificar el ámbito y cubos relevantes.
    
    Args:
        retrievers: Diccionario de retrievers por cubo
        llm: Modelo de lenguaje a utilizar
        
    Returns:
        StateGraph: Grafo de estado configurado
    """
    workflow = StateGraph(AmbitoState)
    
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
        state["clarification_question"] = "No he podido identificar claramente el ámbito. ¿Podrías especificar en qué ámbito te gustaría consultar información?"
        return state
    
    def retrieve_context(state: AmbitoState) -> AmbitoState:
        """
        Recupera contexto relevante para ayudar a identificar el ámbito.
        """
        if state["needs_clarification"]:
            return state
            
        question = state["question"]
        relevant_docs = []
        
        # Buscar en todos los retrievers disponibles
        for retriever in retrievers.values():
            docs = retriever.get_relevant_documents(question)
            relevant_docs.extend(docs)
        
        state["context"] = relevant_docs
        return state
    
    def generate_clarification(state: AmbitoState) -> AmbitoState:
        """
        Genera una pregunta de clarificación si es necesario.
        """
        if not state["needs_clarification"]:
            return state
            
        # Generar pregunta de clarificación usando el LLM
        prompt = f"""
        Basado en la pregunta del usuario: "{state['question']}"
        Y el contexto recuperado: {state['context']}
        
        Genera una pregunta de clarificación para ayudar al usuario a identificar el ámbito correcto.
        """
        
        response = llm.invoke(prompt)
        state["clarification_question"] = response
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