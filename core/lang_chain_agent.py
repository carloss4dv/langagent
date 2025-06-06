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
    create_granular_evaluator, 
    create_query_rewriter,
    create_context_generator,
    create_rag_sql_chain,
    create_sql_interpretation
)
from langagent.models.workflow import create_workflow
from langagent.core.ambito_agent import create_ambito_workflow
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

# Usar el sistema de logging centralizado
from langagent.config.logging_config import get_logger
logger = get_logger(__name__)

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
        self.vector_db_type = vector_db_type or VECTORSTORE_CONFIG["vector_db_type"]
        self.consultas_dir = consultas_dir
        
        # Configuración de modelos - Usar los modelos por defecto específicos para cada rol
        self.local_llm = local_llm or LLM_CONFIG["default_model"]  # Modelo principal
        self.local_llm2 = local_llm2 or LLM_CONFIG["default_model2"]  # Modelo secundario
        self.local_llm3 = local_llm3 or LLM_CONFIG["default_model3"]  # Modelo terciario
        
        # Componentes del agente
        self.llm = None
        self.llm2 = None
        self.llm3 = None
        self.embeddings = None
        self.vectorstore = None
        self.retriever = None
        self.rag_chain = None
        self.retrieval_grader = None
        self.granular_evaluator = None
        self.workflow = None
        self.ambito_workflow = None
        self.app = None
        self.query_rewriter = None
        self.sql_interpretation_chain = None
        
        # Nuevos componentes para recuperación adaptativa
        self.adaptive_retrievers = {}  # Diccionario de retrievers por estrategia
        self.adaptive_vectorstores = {}  # Diccionario de vectorstores por estrategia
        
        # Obtener la instancia de vectorstore
        self.vectorstore_handler = VectorStoreFactory.get_vectorstore_instance(self.vector_db_type)
        
        self.setup_agent()

    def setup_agent(self):
        """
        Configura el agente con todos sus componentes.
        """
        print_title("Configurando el agente")
        
        # Crear LLMs
        logger.info("Configurando modelos de lenguaje...")
        logger.info(f"Modelo principal (generación): {self.local_llm}")
        logger.info(f"Modelo secundario (routing): {self.local_llm2}")
        logger.info(f"Modelo terciario (evaluación): {self.local_llm3}")
        
        self.llm = create_llm(model_name=self.local_llm)
        self.llm2 = create_llm(model_name=self.local_llm2)
        self.llm3 = create_llm(model_name=self.local_llm3)
        
        # Crear embeddings
        logger.info("Configurando embeddings...")
        self.embeddings = create_embeddings()
        
        # Configurar generador de contexto si está habilitado
        if VECTORSTORE_CONFIG.get("use_context_generation", False):
            logger.info("Configurando generador de contexto...")
            context_generator = create_context_generator(self.llm)
            self.vectorstore_handler.set_context_generator(context_generator)
        
        # Cargar documentos
        logger.info("Cargando documentos...")
        documents = load_documents_from_directory(self.data_dir)
        chunked_documents = RecursiveCharacterTextSplitter(
            chunk_size=VECTORSTORE_CONFIG["chunk_size"],
            chunk_overlap=VECTORSTORE_CONFIG["chunk_overlap"]
        ).split_documents(documents)
        
        # Cargar consultas guardadas si existe el directorio
        if self.consultas_dir and os.path.exists(self.consultas_dir):
            logger.info("Cargando consultas guardadas...")
            consultas = load_consultas_guardadas(self.consultas_dir)
            documents.extend(consultas)
        
        # Crear diccionario de documentos originales para generación de contexto
        source_documents = {doc.metadata.get('source', str(i)): doc for i, doc in enumerate(documents)}
        
        # Cargar o crear vectorstore
        if self.vector_db_type == "milvus":
            self.vectorstore = self.vectorstore_handler.load_vectorstore(self.embeddings, VECTORSTORE_CONFIG["collection_name"])
            if self.vectorstore:
                logger.info("Vectorstore existente cargado correctamente - no se cargarán documentos")
            else:
                logger.info("Vectorstore no encontrado, creando nueva vectorstore...")
                logger.info("Cargando documentos en vectorstore...")
                if self.vectorstore_handler.load_documents(chunked_documents, source_documents=source_documents, embeddings=self.embeddings):
                    logger.info("Documentos cargados en vectorstore correctamente")
                    # Cargar el vectorstore recién creado
                    self.vectorstore = self.vectorstore_handler.load_vectorstore(self.embeddings, VECTORSTORE_CONFIG["collection_name"])
                else:
                    logger.error("Error al cargar documentos en vectorstore")
        elif self.vector_db_type == "chroma":
            # Agregar lógica para Chroma
            collection_name = VECTORSTORE_CONFIG.get("collection_name", "default_collection")
            logger.info(f"Intentando cargar vectorstore Chroma: {collection_name}")
            self.vectorstore = self.vectorstore_handler.load_vectorstore(self.embeddings, collection_name)
            if self.vectorstore:
                logger.info("Vectorstore Chroma existente cargado correctamente - no se cargarán documentos")
            else:
                logger.info("Vectorstore Chroma no encontrado, creando nueva vectorstore...")
                self.vectorstore = self.vectorstore_handler.create_vectorstore(
                    documents=chunked_documents,
                    embeddings=self.embeddings,
                    collection_name=collection_name
                )
                if self.vectorstore:
                    logger.info("Vectorstore Chroma creado correctamente")
                else:
                    logger.error("Error al crear vectorstore Chroma")
        
        # Crear el retriever principal (mantener compatibilidad)
        self.retriever = self.vectorstore_handler.create_retriever(self.vectorstore)
        
        # Crear retrievers adaptativos si está habilitado
        if VECTORSTORE_CONFIG.get("use_adaptive_retrieval", False):
            self._setup_adaptive_retrievers()
        
        # Crear cadenas
        logger.info("Creando cadenas de procesamiento...")
        logger.info("Usando modelo principal para RAG y SQL...")
        self.rag_sql_chain = create_rag_sql_chain(self.llm)
        
        logger.info("Usando modelo secundario para evaluación de relevancia...")
        self.retrieval_grader = create_retrieval_grader(self.llm2)
        
        logger.info("Usando modelo terciario para evaluación granular...")
        self.granular_evaluator = create_granular_evaluator(self.llm3)
        
        logger.info("Usando modelo secundario para reescritura de consultas...")
        self.query_rewriter = create_query_rewriter(self.llm2)
        
        logger.info("Usando modelo principal para interpretación de resultados SQL...")
        self.sql_interpretation_chain = create_sql_interpretation(self.llm)
        
        # Crear flujos de trabajo
        logger.info("Creando flujos de trabajo...")
        self._create_workflows()
        
        # Compilar workflows - ya están compilados en create_workflow
        self.app = self.workflow
        self.ambito_app = self.ambito_workflow.compile()
    
    def _create_workflows(self):
        """
        Crea los flujos de trabajo del agente utilizando LangGraph.
        """
        # Crear el flujo de trabajo principal
        self.workflow = create_workflow(
            retriever=self.retriever,
            rag_sql_chain=self.rag_sql_chain,
            retrieval_grader=self.retrieval_grader,
            granular_evaluator=self.granular_evaluator,
            query_rewriter=self.query_rewriter,
            sql_interpretation_chain=self.sql_interpretation_chain,
            adaptive_retrievers=self.adaptive_retrievers  # Pasar retrievers adaptativos
        )
        
        # Crear el flujo de trabajo del agente de ámbito
        self.ambito_workflow = create_ambito_workflow(
            retriever=self.retriever,
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
                "is_consulta": ambito_result.get("is_consulta", False),
                "chunk_strategy": "512",  # Estrategia inicial por defecto
                "retry_count": 0,
                "evaluation_metrics": {}
            }
            
            # Ejecutar el workflow principal con métricas
            result = self.app.invoke_with_metrics(initial_state)
            
            # Añadir información del ámbito al resultado
            result["ambito"] = ambito_result["ambito"]
            result["cubos"] = ambito_result["cubos"]
            result["is_consulta"] = ambito_result.get("is_consulta", False)
            
            return result
        
        # Si no se pudo identificar el ámbito, ejecutar el workflow principal con la consulta original
        default_state = {
            "question": query,
            "chunk_strategy": "512",
            "retry_count": 0,
            "evaluation_metrics": {}
        }
        return self.app.invoke_with_metrics(default_state)

    def _setup_adaptive_retrievers(self):
        """
        Configura los retrievers adaptativos para diferentes estrategias de chunk.
        Crea vectorstores y retrievers para chunks de 256, 512 y 1024 tokens.
        """
        logger.info("Configurando retrievers adaptativos...")
        
        adaptive_collections = VECTORSTORE_CONFIG.get("adaptive_collections", {})
        
        for strategy, collection_name in adaptive_collections.items():
            logger.info(f"Configurando retriever para estrategia {strategy} tokens...")
            
            try:
                # Intentar cargar vectorstore existente para esta estrategia
                vectorstore = self.vectorstore_handler.load_vectorstore(self.embeddings, collection_name)
                
                if vectorstore:
                    logger.info(f"Vectorstore {collection_name} cargado correctamente")
                    self.adaptive_vectorstores[strategy] = vectorstore
                    # Crear retriever para esta estrategia
                    self.adaptive_retrievers[strategy] = self.vectorstore_handler.create_retriever(vectorstore)
                else:
                    logger.warning(f"No se pudo cargar vectorstore {collection_name} para estrategia {strategy}")
                    # Usar el vectorstore principal como fallback
                    self.adaptive_vectorstores[strategy] = self.vectorstore
                    self.adaptive_retrievers[strategy] = self.retriever
                    
            except Exception as e:
                logger.error(f"Error al configurar retriever para estrategia {strategy}: {str(e)}")
                # Usar el vectorstore principal como fallback
                self.adaptive_vectorstores[strategy] = self.vectorstore
                self.adaptive_retrievers[strategy] = self.retriever
        
        logger.info(f"Retrievers adaptativos configurados: {list(self.adaptive_retrievers.keys())}")
    
    def get_retriever_for_strategy(self, strategy):
        """
        Obtiene el retriever apropiado para la estrategia especificada.
        
        Args:
            strategy (str): Estrategia de chunk ("256", "512", "1024")
            
        Returns:
            Retriever: Retriever configurado para la estrategia o retriever principal como fallback
        """
        if strategy in self.adaptive_retrievers:
            return self.adaptive_retrievers[strategy]
        else:
            logger.warning(f"Estrategia {strategy} no encontrada, usando retriever principal")
            return self.retriever 