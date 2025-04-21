"""
Módulo para evaluar el agente LangChain usando TruLens con Ollama como proveedor vía LiteLLM.
"""

from trulens.core import  TruSession
from trulens.apps.langchain import TruChain

from trulens.core.feedback.feedback import Feedback
from trulens.core.feedback import Groundedness
from trulens.providers.litellm.provider import LiteLLM
import numpy as np
from langagent.lang_chain_agent import LangChainAgent
from langagent.config.config import LLM_CONFIG
from trulens.core.database.connector.default import DefaultDBConnector

class TruLensEvaluator:
    def init(self, langchain_agent: LangChainAgent):
        """
        Inicializa el evaluador TruLens para el agente LangChain.

            Args:
                langchain_agent (LangChainAgent): Instancia del agente a evaluar.
                
        """
        self.agent = langchain_agent
        connector = DefaultDBConnector()
        self.tru = TruSession(connector=connector)

        # Configurar LiteLLM con Ollama como proveedor
        self.provider = LiteLLM(model_engine="ollama/" + LLM_CONFIG["default_model3"])

        # Feedback functions básicas
        self.f_relevance = Feedback(self.provider.relevance).on_input_output()
        self.f_groundedness = Feedback(Groundedness(groundedness_provider=self.provider).groundedness_measure).on(
            TruChain._get_selector().context.collect()
        ).on_output()

        # Feedback functions personalizadas
        self.f_no_answer = Feedback(self._no_answer_feedback).on_input_output()
        self.f_response_completeness = Feedback(self._response_completeness).on_input_output()
        self.f_context_relevance = Feedback(self._context_relevance).on(
            TruChain._get_selector().question
        ).on(
            TruChain._get_selector().context.collect()
        ).aggregate(np.mean)

    def _no_answer_feedback(self, question: str, response: str) -> float:
        """
        Evalúa si la respuesta proporciona una respuesta a la pregunta.
        
        Args:
            question (str): Pregunta realizada.
            response (str): Respuesta generada.
            
        Returns:
            float: Puntuación entre 0 y 1.
        """
        completion = self.provider.client.chat.completions.create(
            model="ollama/" + LLM_CONFIG["default_model2"],
            messages=[
                {
                    "role": "system",
                    "content": "Does the RESPONSE provide an answer to the QUESTION? Rate on a scale of 1 to 10. Respond with the number only.",
                },
                {
                    "role": "user",
                    "content": f"QUESTION: {question}; RESPONSE: {response}",
                },
            ],
        )

        try:
            score = float(completion.choices[0].message.content) / 10
            return max(0.0, min(1.0, score))  # Asegurar que está entre 0 y 1
        except (ValueError, AttributeError):
            return 0.5  # Valor por defecto si hay error

    def _response_completeness(self, question: str, response: str) -> float:
        """
        Evalúa la completitud de la respuesta en relación a la pregunta.
        
        Args:
            question (str): Pregunta realizada.
            response (str): Respuesta generada.
            
        Returns:
            float: Puntuación entre 0 y 1.
        """
        completion = self.provider.client.chat.completions.create(
            model="ollama/" + LLM_CONFIG["default_model2"],
            messages=[
                {
                    "role": "system",
                    "content": "How complete is the RESPONSE in addressing all aspects of the QUESTION? Rate on a scale of 1 to 10. Respond with the number only.",
                },
                {
                    "role": "user",
                    "content": f"QUESTION: {question}; RESPONSE: {response}",
                },
            ],
        )

        try:
            score = float(completion.choices[0].message.content) / 10
            return max(0.0, min(1.0, score))
        except (ValueError, AttributeError):
            return 0.5

    def _context_relevance(self, question: str, context: str) -> float:
        """
        Evalúa la relevancia del contexto recuperado para la pregunta.
        
        Args:
            question (str): Pregunta realizada.
            context (str): Contexto recuperado.
            
        Returns:
            float: Puntuación entre 0 y 1.
        """
        completion = self.provider.client.chat.completions.create(
            model="ollama/" + LLM_CONFIG["default_model2"],
            messages=[
                {
                    "role": "system",
                    "content": "How relevant is the CONTEXT for answering the QUESTION? Rate on a scale of 1 to 10. Respond with the number only.",
                },
                {
                    "role": "user",
                    "content": f"QUESTION: {question}; CONTEXT: {context}",
                },
            ],
        )

        try:
            score = float(completion.choices[0].message.content) / 10
            return max(0.0, min(1.0, score))
        except (ValueError, AttributeError):
            return 0.5

    def evaluate_question(self, question: str):
        """
        Ejecuta una pregunta a través del agente y evalúa los resultados con TruLens.
        
        Args:
            question (str): Pregunta a evaluar.
            
        Returns:
            dict: Resultados de la evaluación.
        """
        # Configurar TruChain para el agente
        tru_chain = TruChain(
            self.agent.workflow,
            app_id=f"LangChainAgent-{LLM_CONFIG['default_model']}",
            feedbacks=[
                self.f_relevance,
                self.f_groundedness,
                self.f_no_answer,
                self.f_response_completeness,
                self.f_context_relevance
            ]
        )

        # Ejecutar la evaluación
        with self.tru as recording:
            response = tru_chain(question)
            print(f"Respuesta: {response}")
            print(f"Recording keys: {recording.keys()}")
            print("\nDatos capturados:")
            print(f"- Pregunta: {recording.get('question')}")
            print(f"- Respuesta: {recording.get('output')}")
            print(f"- Contexto: {recording.get('context')}")  

        # Obtener los registros de evaluación
        records = self.tru.get_records_and_feedback(app_ids=[tru_chain.app_id])[0]

        return {
            "question": question,
            "response": response,
            "evaluation": records
        }

    def evaluate_test_questions(self, questions: list):
        """
        Evalúa una lista de preguntas y devuelve los resultados consolidados.
        
        Args:
            questions (list): Lista de preguntas a evaluar.
            
        Returns:
            dict: Resultados consolidados de la evaluación.
        """
        results = []

        for question in questions:
            result = self.evaluate_question(question)
            results.append(result)

        # Calcular promedios
        avg_scores = {
            "relevance": np.mean([r['evaluation']['relevance'] for r in results]),
            "groundedness": np.mean([r['evaluation']['groundedness'] for r in results]),
            "no_answer": np.mean([r['evaluation']['no_answer_feedback'] for r in results]),
            "completeness": np.mean([r['evaluation']['response_completeness'] for r in results]),
            "context_relevance": np.mean([r['evaluation']['context_relevance'] for r in results])
        }

        return {
            "individual_results": results,
            "average_scores": avg_scores
        }

    def generate_evaluation_report(self, evaluation_results: dict):
        """
        Genera un informe de evaluación basado en los resultados.
        
        Args:
            evaluation_results (dict): Resultados de la evaluación.
            
        Returns:
            str: Informe de evaluación formateado.
        """
        report = "## Evaluación RAG con TruLens\n\n"
        report += f"Modelo: {LLM_CONFIG['default_model']}\n"
        report += f"Total preguntas evaluadas: {len(evaluation_results['individual_results'])}\n\n"

        # Resumen de puntuaciones
        report += "### Puntuaciones Promedio\n"
        report += f"- Relevancia respuesta: {evaluation_results['average_scores']['relevance']:.2f}\n"
        report += f"- Groundedness: {evaluation_results['average_scores']['groundedness']:.2f}\n"
        report += f"- Respuesta a pregunta: {evaluation_results['average_scores']['no_answer']:.2f}\n"
        report += f"- Completitud respuesta: {evaluation_results['average_scores']['completeness']:.2f}\n"
        report += f"- Relevancia contexto: {evaluation_results['average_scores']['context_relevance']:.2f}\n\n"

        # Detalle por pregunta
        report += "### Detalle por Pregunta\n"
        for i, result in enumerate(evaluation_results['individual_results']):
            report += f"#### Pregunta {i+1}: {result['question']}\n"
            report += f"- **Respuesta**: {result['response']}\n"
            report += "- **Puntuaciones**:\n"
            report += f"  - Relevancia: {result['evaluation']['relevance']:.2f}\n"
            report += f"  - Groundedness: {result['evaluation']['groundedness']:.2f}\n"
            report += f"  - Respuesta a pregunta: {result['evaluation']['no_answer_feedback']:.2f}\n"
            report += f"  - Completitud: {result['evaluation']['response_completeness']:.2f}\n"
            report += f"  - Relevancia contexto: {result['evaluation']['context_relevance']:.2f}\n\n"

        return report

if __name__ == "__main__":
    import sys
    import json

    # Verificar si se proporcionó un archivo de preguntas
    if len(sys.argv) < 2:
        print("Uso: python evaluate.py <archivo_de_preguntas.json>")
        sys.exit(1)

    # Leer preguntas desde un archivo JSON
    preguntas_file = sys.argv[1]
    with open(preguntas_file, 'r', encoding='utf-8') as f:
        preguntas = json.load(f)

    # Crear una instancia del agente LangChain
    langchain_agent = LangChainAgent()  # Asegúrate de que esté correctamente inicializado

    # Crear una instancia del evaluador
    evaluador = TruLensEvaluator(langchain_agent)

    # Evaluar las preguntas
    resultados = evaluador.evaluate_test_questions(preguntas)

    # Generar y mostrar el informe
    informe = evaluador.generate_evaluation_report(resultados)
    print(informe)