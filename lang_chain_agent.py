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
from langagent.utils.vectorstore import (
    create_embeddings, 
    create_vectorstore, 
    load_vectorstore, 
    create_retriever
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
    def __init__(self, data_dir=None, chroma_base_dir=None, local_llm=None, local_llm2=None, consultas_dir=None):
        """
        Inicializa el agente con todos sus componentes, creando una vectorstore separada
        para cada cubo identificado en los documentos.
        
        Args:
            data_dir (str, optional): Directorio con los documentos markdown.
            chroma_base_dir (str, optional): Directorio base para las bases de datos vectoriales.
            local_llm (str, optional): Nombre del modelo LLM principal.
            local_llm2 (str, optional): Nombre del segundo modelo LLM.
            consultas_dir (str, optional): Directorio con las consultas guardadas.
        """
        self.data_dir = data_dir or PATHS_CONFIG["default_data_dir"]
        self.chroma_base_dir = chroma_base_dir or PATHS_CONFIG["default_chroma_dir"]
        self.local_llm = local_llm or LLM_CONFIG["default_model"]
        self.local_llm2 = local_llm2 or LLM_CONFIG["default_model2"]
        self.consultas_dir = consultas_dir or os.path.join(os.path.dirname(self.data_dir), "consultas_guardadas")
        
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
            
            # Crear directorio para vectorstore de este cubo
            cubo_chroma_dir = os.path.join(self.chroma_base_dir, f"Cubo{cubo_name}")
            
            # Crear o cargar vectorstore para este cubo
            if not os.path.exists(cubo_chroma_dir):
                print(f"Creando nueva base de datos vectorial para {cubo_name}...")
                db = create_vectorstore(doc_splits, self.embeddings, cubo_chroma_dir)
            else:
                print(f"Cargando base de datos vectorial existente para {cubo_name}...")
                db = load_vectorstore(cubo_chroma_dir, self.embeddings)
            
            # Guardar la vectorstore
            self.vectorstores[cubo_name] = db
            
            # Crear retriever para este cubo
            self.retrievers[cubo_name] = create_retriever(db, k=VECTORSTORE_CONFIG["k_retrieval"])
        
        # Procesar consultas guardadas por ámbito
        for ambito, consultas in consultas_por_ambito.items():
            print(f"Procesando consultas guardadas para el ámbito: {ambito}")
            
            # Dividir consultas en chunks
            consulta_splits = text_splitter.split_documents(consultas)
            
            # Crear directorio para vectorstore de consultas de este ámbito
            consultas_chroma_dir = os.path.join(self.chroma_base_dir, f"Consultas_{ambito}")
            
            # Crear o cargar vectorstore para las consultas de este ámbito
            if not os.path.exists(consultas_chroma_dir):
                print(f"Creando nueva base de datos vectorial para consultas de {ambito}...")
                db = create_vectorstore(consulta_splits, self.embeddings, consultas_chroma_dir)
            else:
                print(f"Cargando base de datos vectorial existente para consultas de {ambito}...")
                db = load_vectorstore(consultas_chroma_dir, self.embeddings)
            
            # Guardar la vectorstore de consultas
            self.consultas_vectorstores[ambito] = db
            
            # Crear retriever para las consultas de este ámbito y agregarlo a los retrievers
            retriever_key = f"consultas_{ambito}"
            self.retrievers[retriever_key] = create_retriever(db, k=VECTORSTORE_CONFIG["k_retrieval"])
        
        # Crear LLMs
        print("Configurando modelos de lenguaje...")
        self.llm = create_llm(model_name=self.local_llm)
        self.llm2 = create_llm(model_name=self.local_llm2)
        
        # Crear cadenas
        self.rag_chain = create_rag_chain(self.llm)
        self.retrieval_grader = create_retrieval_grader(self.llm2)
        self.hallucination_grader = create_hallucination_grader(self.llm2)
        self.answer_grader = create_answer_grader(self.llm2)
        
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

    def run(self, question):
        """
        Ejecuta el agente con una pregunta.
        
        Args:
            question (str): Pregunta a responder.
            
        Returns:
            dict: Resultado final del workflow.
        """
        print_title(f"Procesando pregunta: {question}")
        
        # Ejecutar workflow
        inputs = {"question": question}
        state_transitions = []
        
        for output in self.app.stream(inputs):
            state_transitions.append(output)
            for key, value in output.items():
                print(f"Completado: {key}")
        
        # Imprimir pasos del workflow
        print_workflow_steps(state_transitions)
        
        # Imprimir resultado final
        final_output = state_transitions[-1]
        print_workflow_result(final_output)
        
        return final_output 