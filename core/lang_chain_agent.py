# Archivo: lang_chain_agent.py

"""
Clase LangChainAgent para configurar y ejecutar el agente de respuesta a preguntas.
"""

import re
import os
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langagent.utils.document_loader import (
    load_documents_from_directory,
    load_consultas_guardadas
)
from langagent.vectorstore import (
    VectorStoreFactory,
    create_embeddings
)
from langagent.models.llm import (
    create_llm, 
    create_rag_chain, 
    create_retrieval_grader, 
    create_hallucination_grader, 
    create_answer_grader, 
    create_query_rewriter,
    create_context_generator,
    create_rag_sql_chain
)
from langagent.models.workflow import create_workflow
from langagent.models.ambito_agent import create_ambito_workflow
from langagent.utils.terminal_visualization import (
    print_title, 
    print_documents, 
    print_workflow_result, 
    print_workflow_steps
)
from langagent.config.config import (
    LLM_CONFIG,
    VECTORSTORE_CONFIG,
    PATHS_CONFIG,
    SQL_CONFIG
)

class LangChainAgent:
    def __init__(self, data_dir=None, vectorstore_dir=None, vector_db_type=None, local_llm=None, local_llm2=None, local_llm3=None, consultas_dir=None):
        """
        Inicializa el agente con la configuración especificada.
        
        Args:
            data_dir: Directorio con los documentos de entrada
            vectorstore_dir: Directorio para almacenar las vectorstores
            vector_db_type: Tipo de base de datos vectorial a utilizar
            local_llm: Nombre del modelo de lenguaje local para el agente principal
            local_llm2: Nombre del modelo de lenguaje local para evaluadores
            local_llm3: Nombre del modelo de lenguaje local para el agente de ámbito
            consultas_dir: Directorio con las consultas guardadas
        """
        # Configuración de directorios
        self.data_dir = data_dir or PATHS_CONFIG["default_data_dir"]
        self.vectorstore_dir = vectorstore_dir or PATHS_CONFIG["default_vectorstore_dir"]
        self.vector_db_type = vector_db_type or VECTORSTORE_CONFIG["default_type"]
        self.consultas_dir = consultas_dir
        
        # Configuración de modelos
        self.local_llm = local_llm or LLM_CONFIG["default_model"]
        self.local_llm2 = local_llm2 or LLM_CONFIG["default_model"]
        self.local_llm3 = local_llm3 or LLM_CONFIG["default_model"]
        
        # Componentes del agente
        self.llm = None
        self.llm2 = None
        self.llm3 = None
        self.embeddings = None
        self.vectorstores = {}
        self.retrievers = {}
        self.rag_chain = None
        self.retrieval_grader = None
        self.hallucination_grader = None
        self.answer_grader = None
        self.workflow = None
        self.ambito_workflow = None
        self.app = None
        self.query_rewriter = None
        
        # Obtener la instancia de vectorstore
        self.vectorstore_handler = VectorStoreFactory.get_vectorstore_instance(self.vector_db_type)
        
        self.setup_agent()

    def setup_agent(self):
        """
        Configura el agente con todos sus componentes.
        """
        print_title("Configurando el agente")
        
        # Crear LLMs
        print("Configurando modelos de lenguaje...")
        self.llm = create_llm(model_name=self.local_llm)
        self.llm2 = create_llm(model_name=self.local_llm2)
        self.llm3 = create_llm(model_name=self.local_llm3)
        
        # Crear embeddings
        print("Configurando embeddings...")
        self.embeddings = create_embeddings()
        
        # Configurar generador de contexto si está habilitado
        if VECTORSTORE_CONFIG.get("use_context_generation", False):
            print("Configurando generador de contexto...")
            context_generator = create_context_generator(self.llm)
            self.vectorstore_handler.set_context_generator(context_generator)
        
        # Cargar documentos
        print("Cargando documentos...")
        documents = load_documents_from_directory(self.data_dir)
        chunked_documents = RecursiveCharacterTextSplitter(
            chunk_size=VECTORSTORE_CONFIG["chunk_size"],
            chunk_overlap=VECTORSTORE_CONFIG["chunk_overlap"]
        ).split_documents(documents)
        # Cargar consultas guardadas si existe el directorio
        if self.consultas_dir and os.path.exists(self.consultas_dir):
            print("Cargando consultas guardadas...")
            consultas = load_consultas_guardadas(self.consultas_dir)
            documents.extend(consultas)
            
        if self.vector_db_type == "milvus":
            # Crear diccionario de documentos originales para generación de contexto
            source_documents = {doc.metadata.get('source', str(i)): doc for i, doc in enumerate(documents)}
            
            if self.vectorstore_handler.load_documents(chunked_documents, source_documents=source_documents, embeddings=self.embeddings):
                print("Documentos cargados en vectorstore correctamente")
            else:
                print("Vectorstore no encontrado, creando nueva vectorstore...")
                print("Cargando documentos en vectorstore...")
                self.vectorstore_handler.load_documents(chunked_documents, source_documents=source_documents)
        
        # Crear cadenas
        print("Creando cadenas de procesamiento...")
        self.rag_chain = create_rag_chain(self.llm)
        self.retrieval_grader = create_retrieval_grader(self.llm2)
        self.hallucination_grader = create_hallucination_grader(self.llm2)
        self.answer_grader = create_answer_grader(self.llm2)
        self.query_rewriter = create_query_rewriter(self.llm2)
        
        # Crear flujos de trabajo
        print("Creando flujos de trabajo...")
        self._create_workflows()
        
        # Compilar workflows
        self.app = self.workflow.compile()
        self.ambito_app = self.ambito_workflow.compile()
    
    def _create_workflows(self):
        """
        Crea los flujos de trabajo del agente utilizando LangGraph.
        """
        # Crear el flujo de trabajo principal
        self.workflow = create_workflow(
            retrievers=self.retrievers,
            rag_chain=self.rag_chain,
            retrieval_grader=self.retrieval_grader,
            hallucination_grader=self.hallucination_grader,
            answer_grader=self.answer_grader,
            query_rewriter=self.query_rewriter
        )
        
        # Crear el flujo de trabajo del agente de ámbito
        self.ambito_workflow = create_ambito_workflow(
            retrievers=self.retrievers,
            llm=self.llm3
        )
    
    def run(self, query):
        """
        Ejecuta el agente con una consulta del usuario.
        
        Args:
            query (str): Consulta del usuario.
            
        Returns:
            Dict: Resultado de la ejecución del agente.
        """
        print_title(f"Consulta: {query}")
        
        # Primero, identificar el ámbito
        ambito_result = self.ambito_app.invoke({"question": query})
        
        # Si necesitamos clarificación, devolver la pregunta
        if ambito_result.get("needs_clarification"):
            return {
                "type": "clarification_needed",
                "question": ambito_result["clarification_question"]
            }
        
        # Si tenemos un ámbito identificado, proceder con el workflow principal
        if ambito_result.get("ambito"):
            # Crear el estado inicial para el workflow principal
            initial_state = {
                "question": query,
                "ambito": ambito_result["ambito"],
                "cubos": ambito_result["cubos"],
                "is_visualization": ambito_result.get("is_visualization", False)
            }
            
            # Ejecutar el workflow principal
            result = self.app.invoke(initial_state)
            
            # Añadir información del ámbito al resultado
            result["ambito"] = ambito_result["ambito"]
            result["cubos"] = ambito_result["cubos"]
            result["is_visualization"] = ambito_result.get("is_visualization", False)
            
            return result
        
        # Si no se pudo identificar el ámbito, ejecutar el workflow principal con la consulta original
        return self.app.invoke({"question": query}) 