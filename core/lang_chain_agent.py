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
    create_question_router
)
from langagent.models.workflow import create_workflow
from langagent.utils.terminal_visualization import (
    print_title, 
    print_documents, 
    print_workflow_result, 
    print_workflow_steps
)
from langagent.config.config import (
    LLM_CONFIG,
    VECTORSTORE_CONFIG,
    PATHS_CONFIG
)

class LangChainAgent:
    def __init__(self, data_dir=None, vectorstore_dir=None, vector_db_type=None, local_llm=None, local_llm2=None, local_llm3=None, consultas_dir=None):
        """
        Inicializa el agente con todos sus componentes, creando una vectorstore separada
        para cada cubo identificado en los documentos.
        
        Args:
            data_dir (str, optional): Directorio con los documentos markdown.
            vectorstore_dir (str, optional): Directorio base para las bases de datos vectoriales.
            vector_db_type (str, optional): Tipo de vectorstore a utilizar ('chroma' o 'milvus').
            local_llm (str, optional): Nombre del modelo LLM principal.
            local_llm2 (str, optional): Nombre del segundo modelo LLM.
            local_llm3 (str, optional): Nombre del tercer modelo LLM.
            consultas_dir (str, optional): Directorio con las consultas guardadas.
        """
        self.data_dir = data_dir or PATHS_CONFIG["default_data_dir"]
        self.vectorstore_dir = vectorstore_dir or PATHS_CONFIG["default_vectorstore_dir"]
        self.vector_db_type = vector_db_type or VECTORSTORE_CONFIG.get("vector_db_type", "chroma")
        self.local_llm = local_llm or LLM_CONFIG["default_model"]
        self.local_llm2 = local_llm2 or LLM_CONFIG["default_model2"]
        self.local_llm3 = local_llm3 or LLM_CONFIG["default_model3"]
        self.consultas_dir = consultas_dir or os.path.join(os.path.dirname(self.data_dir), "consultas_guardadas")
        
        # Para compatibilidad con código existente
        if self.vector_db_type == "chroma":
            self.chroma_base_dir = PATHS_CONFIG.get("default_chroma_dir", "./chroma")
        
        self.embeddings = None
        self.retrievers = {}
        self.vectorstores = {}
        self.consultas_vectorstores = {}
        self.llm = None
        self.llm2 = None
        self.rag_chain = None
        self.retrieval_grader = None
        self.hallucination_grader = None
        self.answer_grader = None
        self.question_router = None
        self.workflow = None
        self.app = None
        
        # Obtener la instancia de vectorstore
        self.vectorstore_handler = VectorStoreFactory.get_vectorstore_instance(self.vector_db_type)
        
        self.setup_agent()

    def setup_agent(self):
        """
        Configura el agente con todos sus componentes.
        """
        print_title("Configurando el agente")
        
        # Crear embeddings (compartidos por todas las vectorstores)
        print("Creando embeddings...")
        self.embeddings = create_embeddings()
        
        # Cargar documentos y agruparlos por cubo
        print("Cargando documentos y agrupándolos por cubo...")
        all_documents = load_documents_from_directory(self.data_dir)
        
        # Cargar consultas guardadas
        print("Cargando consultas guardadas...")
        consultas_por_ambito = load_consultas_guardadas(self.consultas_dir)
        
        # Dividir documentos en chunks más pequeños
        print("Dividiendo documentos...")
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=VECTORSTORE_CONFIG["chunk_size"], 
            chunk_overlap=VECTORSTORE_CONFIG["chunk_overlap"]
        )
        
        # Diccionario para agrupar los documentos por cubo
        cubo_documents = {}
        
        # Extraer y agrupar por nombre de cubo
        for doc in all_documents:
            # Extraer el nombre del cubo del nombre del archivo o metadatos
            file_path = doc.metadata.get('source', '')
            file_name = os.path.basename(file_path)
            
            # Buscar el patrón info_cubo_X_vY.md y extraer X como nombre del cubo
            match = re.search(r'info_cubo_([^_]+)_v\d+\.md', file_name)
            if match:
                cubo_name = match.group(1)
                if cubo_name not in cubo_documents:
                    cubo_documents[cubo_name] = []
                cubo_documents[cubo_name].append(doc)
            else:
                # Si no sigue el patrón, usar un grupo por defecto
                if "general" not in cubo_documents:
                    cubo_documents["general"] = []
                cubo_documents["general"].append(doc)
        
        # Procesar cada cubo y crear su vectorstore
        for cubo_name, docs in cubo_documents.items():
            print(f"Procesando documentos para el cubo: {cubo_name}")
            
            # Dividir documentos en chunks
            doc_splits = text_splitter.split_documents(docs)
            
            # Añadir metadatos sobre el cubo a los documentos
            for doc in doc_splits:
                doc.metadata["cubo_source"] = cubo_name
                # Intentar identificar el ámbito del cubo
                from langagent.models.constants import CUBO_TO_AMBITO
                if cubo_name in CUBO_TO_AMBITO:
                    doc.metadata["ambito"] = CUBO_TO_AMBITO[cubo_name]
            
            # Nombre de la colección para el cubo
            collection_name = f"Cubo{cubo_name}"
            
            try:
                # Intentar cargar una vectorstore existente
                print(f"Intentando cargar vectorstore existente para {cubo_name}...")
                db = self.vectorstore_handler.load_vectorstore(
                    embeddings=self.embeddings,
                    collection_name=collection_name,
                    persist_directory=os.path.join(self.vectorstore_dir, collection_name)
                )
                print(f"Vectorstore existente cargada para {cubo_name}")
            except Exception as e:
                # Si no existe, crear una nueva
                print(f"Creando nueva vectorstore para {cubo_name}...")
                db = self.vectorstore_handler.create_vectorstore(
                    documents=doc_splits,
                    embeddings=self.embeddings,
                    collection_name=collection_name,
                    persist_directory=os.path.join(self.vectorstore_dir, collection_name)
                )
                print(f"Nueva vectorstore creada para {cubo_name}")
            
            # Guardar la vectorstore
            self.vectorstores[cubo_name] = db
            
            # Crear retriever para este cubo
            self.retrievers[cubo_name] = self.vectorstore_handler.create_retriever(
                vectorstore=db,
                k=VECTORSTORE_CONFIG["k_retrieval"],
                similarity_threshold=VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
            )
        
        # Procesar consultas guardadas por ámbito
        for ambito, consultas in consultas_por_ambito.items():
            print(f"Procesando consultas guardadas para el ámbito: {ambito}")
            
            # Dividir consultas en chunks
            consulta_splits = text_splitter.split_documents(consultas)
            
            # Añadir metadatos sobre el ámbito a los documentos
            for doc in consulta_splits:
                doc.metadata["ambito"] = ambito
                doc.metadata["is_consulta"] = True
            
            # Nombre de la colección para las consultas de este ámbito
            collection_name = f"Consultas_{ambito}"
            
            try:
                # Intentar cargar una vectorstore existente
                print(f"Intentando cargar vectorstore existente para consultas de {ambito}...")
                db = self.vectorstore_handler.load_vectorstore(
                    embeddings=self.embeddings,
                    collection_name=collection_name,
                    persist_directory=os.path.join(self.vectorstore_dir, collection_name)
                )
                print(f"Vectorstore existente cargada para consultas de {ambito}")
            except Exception as e:
                # Si no existe, crear una nueva
                print(f"Creando nueva vectorstore para consultas de {ambito}...")
                db = self.vectorstore_handler.create_vectorstore(
                    documents=consulta_splits,
                    embeddings=self.embeddings,
                    collection_name=collection_name,
                    persist_directory=os.path.join(self.vectorstore_dir, collection_name)
                )
                print(f"Nueva vectorstore creada para consultas de {ambito}")
            
            # Guardar la vectorstore de consultas
            self.consultas_vectorstores[ambito] = db
            
            # Crear retriever para las consultas de este ámbito y agregarlo a los retrievers
            retriever_key = f"consultas_{ambito}"
            self.retrievers[retriever_key] = self.vectorstore_handler.create_retriever(
                vectorstore=db,
                k=VECTORSTORE_CONFIG["k_retrieval"],
                similarity_threshold=VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
            )
        
        # Crear LLMs
        print("Configurando modelos de lenguaje...")
        self.llm = create_llm(model_name=self.local_llm)
        self.llm2 = create_llm(model_name=self.local_llm2)
        self.llm3 = create_llm(model_name=self.local_llm3)
        
        # Crear cadenas
        self.rag_chain = create_rag_chain(self.llm)
        self.retrieval_grader = create_retrieval_grader(self.llm2)
        self.hallucination_grader = create_hallucination_grader(self.llm3)
        self.answer_grader = create_answer_grader(self.llm3)
        
        # Crear un router de preguntas que determine qué cubo usar y si es una consulta
        self.question_router = create_question_router(self.llm2)
        
        # Modificar create_workflow para manejar múltiples retrievers
        print("Creando flujo de trabajo con múltiples vectorstores...")
        self.workflow = create_workflow(
            self.retrievers, 
            self.rag_chain, 
            self.retrieval_grader, 
            self.hallucination_grader, 
            self.answer_grader, 
            self.question_router
        )
        
        # Compilar workflow
        self.app = self.workflow.compile()
    
    def run(self, query):
        """
        Ejecuta el agente con una consulta del usuario.
        
        Args:
            query (str): Consulta del usuario.
            
        Returns:
            Dict: Resultado de la ejecución del agente.
        """
        print_title(f"Consulta: {query}")
        
        # Ejecutar el workflow
        result = self.app.invoke({"question": query})
        
        # Mostrar documentos recuperados
        if "documents" in result:
            print_documents(result["documents"])
        
        # Mostrar resultados
        print_workflow_result(result)
        
        # Mostrar pasos del workflow si están disponibles
        if "workflow_trace" in result:
            print_workflow_steps(result["workflow_trace"])
        
        return result 