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
    create_question_router,
    create_query_rewriter,
    create_context_generator
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
        
        # Configurar el generador de contexto para el vectorstore (si es Milvus)
        if self.vector_db_type.lower() == "milvus" and hasattr(self.vectorstore_handler, "set_context_generator"):
            use_context_generation = VECTORSTORE_CONFIG.get("use_context_generation", False)
            if use_context_generation:
                print("Configurando generador de contexto para Milvus...")
                try:
                    # Primero creamos el generador de contexto con el LLM principal
                    print(f"Usando modelo {self.llm.model} para generación de contexto")
                    context_generator = create_context_generator(self.llm2)
                    
                    # Verificar que se creó correctamente
                    if context_generator is not None:
                        print(f"Generador de contexto creado: {type(context_generator)}")
                        
                        # Hacer una prueba rápida
                        try:
                            test_result = context_generator.invoke({
                                "document": "Documento de prueba.",
                                "chunk": "Chunk de prueba."
                            })
                            print(f"Prueba del generador: {test_result}")
                            
                            # Verificar si es un diccionario con formato JSON
                            if isinstance(test_result, dict) and 'context' in test_result:
                                print(f"Contexto extraído: '{test_result['context']}'")
                            else:
                                print(f"Advertencia: Resultado no tiene el formato JSON esperado: {type(test_result)}")
                        except Exception as test_error:
                            print(f"Error al probar el generador: {str(test_error)}")
                            
                        # Pasarlo al handler de vectorstore
                        self.vectorstore_handler.set_context_generator(context_generator)
                        print("Generador de contexto configurado correctamente")
                    else:
                        print("Error: No se pudo crear el generador de contexto")
                except Exception as e:
                    print(f"Error al configurar el generador de contexto: {str(e)}")
                    import traceback
                    print(f"Traza de error: {traceback.format_exc()}")
        
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
        
        # Verificar si estamos usando Milvus con colección única
        use_single_collection = (
            self.vector_db_type.lower() == "milvus" and 
            VECTORSTORE_CONFIG.get("use_single_collection", True)
        )
        
        if use_single_collection:
            print("Usando Milvus con enfoque de colección única...")
            
            # Diccionario para almacenar todos los documentos procesados
            all_processed_docs = []
            
            # Diccionario para almacenar documentos originales por fuente
            source_documents = {}
            
            # Primero guardar los documentos originales por su ruta de archivo
            for doc in all_documents:
                file_path = doc.metadata.get('source', '')
                if file_path and file_path not in source_documents:
                    source_documents[file_path] = doc
            
            # Procesar documentos por cubo y añadir metadatos
            for doc in all_documents:
                # Extraer el nombre del cubo del nombre del archivo o metadatos
                file_path = doc.metadata.get('source', '')
                file_name = os.path.basename(file_path)
                
                # Buscar el patrón info_cubo_X_vY.md y extraer X como nombre del cubo
                match = re.search(r'info_cubo_([^_]+)_v\d+\.md', file_name)
                cubo_name = match.group(1) if match else "general"
                
                # Añadir metadatos sobre el cubo a los documentos
                doc.metadata["cubo_source"] = cubo_name
                
                # Intentar identificar el ámbito del cubo
                from langagent.models.constants import CUBO_TO_AMBITO
                if cubo_name in CUBO_TO_AMBITO:
                    doc.metadata["ambito"] = CUBO_TO_AMBITO[cubo_name]
                else:
                    # Si no podemos determinar el ámbito, usar "general"
                    doc.metadata["ambito"] = "general"
                
                # Asegurar que todos los campos necesarios estén presentes
                if "is_consulta" not in doc.metadata:
                    doc.metadata["is_consulta"] = "false"  # Por defecto, no es una consulta guardada
                elif isinstance(doc.metadata["is_consulta"], bool):
                    # Convertir booleanos a string para Milvus
                    doc.metadata["is_consulta"] = str(doc.metadata["is_consulta"]).lower()
                
                # Inicializar el campo de context_generation si no existe
                if "context_generation" not in doc.metadata:
                    doc.metadata["context_generation"] = ""
                
                all_processed_docs.append(doc)
            
            # Dividir todos los documentos en chunks
            doc_splits = text_splitter.split_documents(all_processed_docs)
            
            # Procesar consultas guardadas y añadirlas al conjunto de documentos
            for ambito, consultas in consultas_por_ambito.items():
                consulta_splits = text_splitter.split_documents(consultas)
                for doc in consulta_splits:
                    # Asegurar que tiene todos los metadatos necesarios
                    doc.metadata["ambito"] = ambito
                    doc.metadata["is_consulta"] = "true"  # Usar string en lugar de bool
                    doc.metadata["cubo_source"] = f"consultas_{ambito}"  # Asignar un cubo_source basado en el ámbito
                doc_splits.extend(consulta_splits)
            
            # Hacer una verificación final de que todos los documentos tienen los metadatos requeridos
            for doc in doc_splits:
                # Verificar campos obligatorios
                if "ambito" not in doc.metadata or not doc.metadata["ambito"]:
                    doc.metadata["ambito"] = "general"
                if "cubo_source" not in doc.metadata or not doc.metadata["cubo_source"]:
                    doc.metadata["cubo_source"] = "general"
                if "is_consulta" not in doc.metadata:
                    doc.metadata["is_consulta"] = "false"
                elif isinstance(doc.metadata["is_consulta"], bool):
                    doc.metadata["is_consulta"] = str(doc.metadata["is_consulta"]).lower()
            
            # Nombre para la colección única de Milvus
            unified_collection_name = VECTORSTORE_CONFIG.get("unified_collection_name", "UnifiedKnowledgeBase")
            
            try:
                # Intentar cargar la colección unificada existente
                print(f"Intentando cargar vectorstore unificada: {unified_collection_name}...")
                db = self.vectorstore_handler.load_vectorstore(
                    embeddings=self.embeddings,
                    collection_name=unified_collection_name,
                    check_collection_exists=True,  # Verificar si la colección existe antes de crearla
                    always_drop_old=False          # No recrear si ya existe
                )
                print(f"Vectorstore unificada cargada correctamente")
                
                # Verificar si se requiere actualización de documentos
                should_update = VECTORSTORE_CONFIG.get("always_update_collection", False)
                if should_update:
                    print("Actualizando colección unificada con documentos nuevos...")
                    
                    # Si el vectorstore tiene un método para actualizar documentos, usarlo
                    if hasattr(db, "add_documents") and callable(getattr(db, "add_documents")):
                        db.add_documents(doc_splits)
                        print(f"Colección actualizada con {len(doc_splits)} documentos")
                    
                    # O si tiene método en el handler para agregar documentos
                    elif hasattr(self.vectorstore_handler, "add_documents_to_collection"):
                        # Verificar si queremos usar generación de contexto
                        use_context_generation = VECTORSTORE_CONFIG.get("use_context_generation", False)
                        
                        # Si está activada la generación de contexto, incluir los documentos originales
                        if use_context_generation:
                            print(f"Generación de contexto activada para actualización. Pasando {len(source_documents)} documentos originales.")
                            self.vectorstore_handler.add_documents_to_collection(
                                vectorstore=db,
                                documents=doc_splits,
                                source_documents=source_documents
                            )
                        else:
                            print("Generación de contexto desactivada para actualización.")
                            self.vectorstore_handler.add_documents_to_collection(
                                vectorstore=db,
                                documents=doc_splits
                            )
                        
                        print(f"Colección actualizada con {len(doc_splits)} documentos")
                    
                    print("Colección unificada actualizada correctamente")
                
            except Exception as e:
                # Si no existe, crear la colección unificada
                print(f"Creando nueva vectorstore unificada: {unified_collection_name}...")
                print(f"Cargando {len(doc_splits)} documentos en la colección unificada")
                
                # Verificar si queremos usar generación de contexto
                use_context_generation = VECTORSTORE_CONFIG.get("use_context_generation", False)
                
                # Crear argumentos para la creación de la vectorstore
                create_kwargs = {
                    "documents": doc_splits,
                    "embeddings": self.embeddings,
                    "collection_name": unified_collection_name,
                    "drop_old": True,  # Forzar recreación completa
                    "check_collection_exists": True,  # Verificar si existe antes de intentar recrear
                }
                
                # Si está activada la generación de contexto, generar el contexto antes de crear la vectorstore
                if use_context_generation:
                    # Verifica que el generador de contexto esté configurado para el vectorstore_handler
                    if self.vectorstore_handler.context_generator is None and hasattr(self.vectorstore_handler, "set_context_generator"):
                        print("Configurando generador de contexto antes de recrear la colección...")
                        context_generator = create_context_generator(self.llm)
                        if context_generator is not None:
                            self.vectorstore_handler.set_context_generator(context_generator)
                            print("Generador de contexto configurado correctamente para recreación")
                        else:
                            print("Error: No se pudo crear el generador de contexto")
                    
                    # Si tenemos documentos originales y el generador está configurado, generar contexto
                    if source_documents and hasattr(self.vectorstore_handler, "_generate_context_for_chunks"):
                        print(f"Generando contexto para {len(doc_splits)} chunks antes de cargarlos...")
                        print("=== INICIANDO GENERACIÓN DE CONTEXTO ===")
                        doc_splits = self.vectorstore_handler._generate_context_for_chunks(doc_splits, source_documents)
                        print("=== FINALIZADA GENERACIÓN DE CONTEXTO ===")
                        
                        # Contar documentos con contexto generado
                        docs_with_context = sum(1 for doc in doc_splits if doc.metadata.get('context_generation', '').strip())
                        print(f"Documentos con contexto generado: {docs_with_context}/{len(doc_splits)}")
                    else:
                        print("No se puede generar contexto: faltan documentos originales o generador no configurado")
                
                # Crear la vectorstore sin pasar los documentos originales para generación de contexto,
                # ya que el contexto ya fue generado
                try:
                    db = self.vectorstore_handler.create_vectorstore(**create_kwargs)
                    print(f"Nueva vectorstore unificada creada correctamente con {len(doc_splits)} documentos")
                except Exception as e:
                    print(f"Error al crear colección unificada: {str(e)}")
                    db = None
            
            # Guardar la vectorstore y crear un retriever unificado
            self.vectorstores["unified"] = db
            
            try:
                # Crear retriever para la colección unificada
                self.retrievers["unified"] = self.vectorstore_handler.create_retriever(
                    vectorstore=db,
                    k=VECTORSTORE_CONFIG["k_retrieval"],
                    similarity_threshold=VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
                )
                print(f"Retriever unificado creado correctamente")
            except Exception as e:
                print(f"Error al crear retriever unificado: {str(e)}")
                print("La aplicación puede tener un comportamiento inesperado")
            
        else:
            # Enfoque tradicional: múltiples colecciones (compatible con Chroma)
            print("Usando enfoque tradicional con múltiples colecciones...")
            
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
                        persist_directory=os.path.join(self.vectorstore_dir, collection_name),
                        check_collection_exists=True,  # Verificar si la colección existe antes de crearla
                        always_drop_old=False          # No recrear si ya existe
                    )
                    print(f"Vectorstore existente cargada para {cubo_name}")
                except Exception as e:
                    # Si no existe, crear una nueva
                    print(f"Creando nueva vectorstore para {cubo_name}...")
                    db = self.vectorstore_handler.create_vectorstore(
                        documents=doc_splits,
                        embeddings=self.embeddings,
                        collection_name=collection_name,
                        persist_directory=os.path.join(self.vectorstore_dir, collection_name),
                        check_collection_exists=True,  # Verificar si existe antes de intentar recrear
                        drop_old=True  # Recrear solo si es necesario
                    )
                    print(f"Nueva vectorstore creada para {cubo_name}")
                
                # Guardar la vectorstore
                self.vectorstores[cubo_name] = db
                
                # Crear retriever para este cubo
                try:
                    self.retrievers[cubo_name] = self.vectorstore_handler.create_retriever(
                        vectorstore=db,
                        k=VECTORSTORE_CONFIG["k_retrieval"],
                        similarity_threshold=VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
                    )
                    print(f"Retriever creado correctamente para el cubo: {cubo_name}")
                except Exception as e:
                    print(f"Error al crear retriever para el cubo {cubo_name}: {str(e)}")
                    print("Continuando con el siguiente cubo...")
                    # No añadir este retriever si falla la creación para evitar errores posteriores
            
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
                try:
                    self.retrievers[retriever_key] = self.vectorstore_handler.create_retriever(
                        vectorstore=db,
                        k=VECTORSTORE_CONFIG["k_retrieval"],
                        similarity_threshold=VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
                    )
                    print(f"Retriever creado correctamente para consultas de: {ambito}")
                except Exception as e:
                    print(f"Error al crear retriever para consultas de {ambito}: {str(e)}")
                    print("Continuando con el siguiente ámbito...")
                    # No añadir este retriever si falla la creación para evitar errores posteriores
        
        # Crear cadenas
        self.rag_chain = create_rag_chain(self.llm)
        self.retrieval_grader = create_retrieval_grader(self.llm2)
        self.hallucination_grader = create_hallucination_grader(self.llm3)
        self.answer_grader = create_answer_grader(self.llm3)
        
        # Crear un router de preguntas que determine qué cubo usar y si es una consulta
        self.question_router = create_question_router(self.llm2)
        
        # Crear un reescritor de consultas para mejorar la recuperación
        # Usamos el LLM principal para mejor calidad en la reescritura
        self.query_rewriter = create_query_rewriter(self.llm)
        
        # Verificar si tenemos al menos un retriever disponible
        if not self.retrievers:
            print("¡ADVERTENCIA! No se ha creado ningún retriever. Creando un retriever predeterminado...")
            try:
                # Crear un documento vacío y una vectorstore básica para evitar errores
                empty_doc = Document(page_content="Documento predeterminado", metadata={"source": "default"})
                
                # Crear vectorstore predeterminada
                default_collection = "default_collection"
                db = self.vectorstore_handler.create_vectorstore(
                    documents=[empty_doc],
                    embeddings=self.embeddings,
                    collection_name=default_collection,
                    persist_directory=os.path.join(self.vectorstore_dir, default_collection)
                )
                
                # Guardar la vectorstore
                self.vectorstores["default"] = db
                
                # Crear un retriever predeterminado
                self.retrievers["default"] = self.vectorstore_handler.create_retriever(
                    vectorstore=db,
                    k=VECTORSTORE_CONFIG["k_retrieval"],
                    similarity_threshold=VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
                )
                print("Retriever predeterminado creado correctamente")
            except Exception as e:
                print(f"Error al crear retriever predeterminado: {str(e)}")
                print("¡ADVERTENCIA! La aplicación puede fallar debido a la falta de retrievers disponibles")
        
        # Crear flujo de trabajo
        print("Creando flujo de trabajo...")
        self._create_workflow()
        
        # Compilar workflow
        self.app = self.workflow.compile()
    
    def _create_workflow(self):
        """
        Crea el flujo de trabajo del agente utilizando LangGraph.
        """
        # Crear el flujo de trabajo
        self.workflow = create_workflow(
            retrievers=self.retrievers,
            rag_chain=self.rag_chain,
            retrieval_grader=self.retrieval_grader,
            hallucination_grader=self.hallucination_grader,
            answer_grader=self.answer_grader,
            question_router=self.question_router,
            query_rewriter=self.query_rewriter  # Pasar el reescritor de consultas
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

    def recreate_unified_collection(self):
        """
        Recrea la colección unificada desde cero.
        Útil cuando hay problemas con la colección existente.
        
        Returns:
            bool: True si la recreación fue exitosa
        """
        print_title("Recreando colección unificada")
        
        if self.vector_db_type.lower() != "milvus":
            print("Esta función solo está disponible para Milvus")
            return False
            
        # Verificar si estamos usando el enfoque de colección única
        use_single_collection = VECTORSTORE_CONFIG.get("use_single_collection", True)
        if not use_single_collection:
            print("Esta función solo está disponible en modo de colección única")
            return False
            
        # Cargar todos los documentos y consultas
        print("Cargando documentos y consultas...")
        all_documents = load_documents_from_directory(self.data_dir)
        consultas_por_ambito = load_consultas_guardadas(self.consultas_dir)
        
        # Diccionario para almacenar documentos originales por fuente
        source_documents = {}
        
        # Primero guardar los documentos originales por su ruta de archivo
        for doc in all_documents:
            file_path = doc.metadata.get('source', '')
            if file_path and file_path not in source_documents:
                source_documents[file_path] = doc
                
        # Dividir documentos en chunks
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=VECTORSTORE_CONFIG["chunk_size"], 
            chunk_overlap=VECTORSTORE_CONFIG["chunk_overlap"]
        )
        
        # Procesar documentos por cubo y añadir metadatos
        all_processed_docs = []
        for doc in all_documents:
            # Extraer el nombre del cubo del nombre del archivo o metadatos
            file_path = doc.metadata.get('source', '')
            file_name = os.path.basename(file_path)
            
            # Buscar el patrón info_cubo_X_vY.md y extraer X como nombre del cubo
            match = re.search(r'info_cubo_([^_]+)_v\d+\.md', file_name)
            cubo_name = match.group(1) if match else "general"
            
            # Añadir metadatos sobre el cubo a los documentos
            doc.metadata["cubo_source"] = cubo_name
            
            # Intentar identificar el ámbito del cubo
            from langagent.models.constants import CUBO_TO_AMBITO
            if cubo_name in CUBO_TO_AMBITO:
                doc.metadata["ambito"] = CUBO_TO_AMBITO[cubo_name]
            else:
                # Si no podemos determinar el ámbito, usar "general"
                doc.metadata["ambito"] = "general"
            
            # Asegurar que todos los campos necesarios estén presentes
            if "is_consulta" not in doc.metadata:
                doc.metadata["is_consulta"] = "false"  # Por defecto, no es una consulta guardada
            elif isinstance(doc.metadata["is_consulta"], bool):
                # Convertir booleanos a string para Milvus
                doc.metadata["is_consulta"] = str(doc.metadata["is_consulta"]).lower()
                
            # Inicializar el campo de context_generation si no existe
            if "context_generation" not in doc.metadata:
                doc.metadata["context_generation"] = ""
            
            all_processed_docs.append(doc)
        
        # Dividir todos los documentos en chunks
        doc_splits = text_splitter.split_documents(all_processed_docs)
        
        # Procesar consultas guardadas y añadirlas al conjunto de documentos
        for ambito, consultas in consultas_por_ambito.items():
            consulta_splits = text_splitter.split_documents(consultas)
            for doc in consulta_splits:
                # Asegurar que tiene todos los metadatos necesarios
                doc.metadata["ambito"] = ambito
                doc.metadata["is_consulta"] = "true"  # Usar string en lugar de bool
                doc.metadata["cubo_source"] = f"consultas_{ambito}"  # Asignar un cubo_source basado en el ámbito
                # Inicializar el campo de context_generation si no existe
                if "context_generation" not in doc.metadata:
                    doc.metadata["context_generation"] = ""
            doc_splits.extend(consulta_splits)
        
        # Hacer una verificación final de que todos los documentos tienen los metadatos requeridos
        for doc in doc_splits:
            # Verificar campos obligatorios
            if "ambito" not in doc.metadata or not doc.metadata["ambito"]:
                doc.metadata["ambito"] = "general"
            if "cubo_source" not in doc.metadata or not doc.metadata["cubo_source"]:
                doc.metadata["cubo_source"] = "general"
            if "is_consulta" not in doc.metadata:
                doc.metadata["is_consulta"] = "false"
            elif isinstance(doc.metadata["is_consulta"], bool):
                doc.metadata["is_consulta"] = str(doc.metadata["is_consulta"]).lower()
            if "context_generation" not in doc.metadata:
                doc.metadata["context_generation"] = ""
        
        # Nombre para la colección única de Milvus
        unified_collection_name = VECTORSTORE_CONFIG.get("unified_collection_name", "UnifiedKnowledgeBase")
        
        # Forzar la recreación de la colección
        print(f"Creando nueva colección unificada: {unified_collection_name}...")
        print(f"Cargando {len(doc_splits)} documentos en la colección")
        
        try:
            # Verificar si queremos usar generación de contexto
            use_context_generation = VECTORSTORE_CONFIG.get("use_context_generation", False)
            
            # Crear argumentos para la creación de la vectorstore
            create_kwargs = {
                "documents": doc_splits,
                "embeddings": self.embeddings,
                "collection_name": unified_collection_name,
                "drop_old": True,  # Forzar recreación completa
                "check_collection_exists": True,  # Verificar si existe antes de intentar recrear
            }
            
            # Si está activada la generación de contexto, generar el contexto antes de crear la vectorstore
            if use_context_generation:
                # Verifica que el generador de contexto esté configurado para el vectorstore_handler
                if self.vectorstore_handler.context_generator is None and hasattr(self.vectorstore_handler, "set_context_generator"):
                    print("Configurando generador de contexto antes de recrear la colección...")
                    context_generator = create_context_generator(self.llm)
                    if context_generator is not None:
                        self.vectorstore_handler.set_context_generator(context_generator)
                        print("Generador de contexto configurado correctamente para recreación")
                    else:
                        print("Error: No se pudo crear el generador de contexto")
                
                # Si tenemos documentos originales y el generador está configurado, generar contexto
                if source_documents and hasattr(self.vectorstore_handler, "_generate_context_for_chunks"):
                    print(f"Generando contexto para {len(doc_splits)} chunks antes de cargarlos...")
                    print("=== INICIANDO GENERACIÓN DE CONTEXTO ===")
                    doc_splits = self.vectorstore_handler._generate_context_for_chunks(doc_splits, source_documents)
                    print("=== FINALIZADA GENERACIÓN DE CONTEXTO ===")
                    
                    # Contar documentos con contexto generado
                    docs_with_context = sum(1 for doc in doc_splits if doc.metadata.get('context_generation', '').strip())
                    print(f"Documentos con contexto generado: {docs_with_context}/{len(doc_splits)}")
                else:
                    print("No se puede generar contexto: faltan documentos originales o generador no configurado")
            
            # Crear la vectorstore sin pasar los documentos originales para generación de contexto,
            # ya que el contexto ya fue generado
            try:
                db = self.vectorstore_handler.create_vectorstore(**create_kwargs)
                print(f"Nueva vectorstore unificada creada correctamente con {len(doc_splits)} documentos")
            except Exception as e:
                print(f"Error al crear colección unificada: {str(e)}")
                db = None
            
            # Actualizar la vectorstore y retriever
            self.vectorstores["unified"] = db
            
            # Crear retriever para la colección unificada
            self.retrievers["unified"] = self.vectorstore_handler.create_retriever(
                vectorstore=db,
                k=VECTORSTORE_CONFIG["k_retrieval"],
                similarity_threshold=VECTORSTORE_CONFIG.get("similarity_threshold", 0.7)
            )
            print(f"Retriever unificado creado correctamente")
            
            # Recompilar el workflow
            print("Recompilando workflow...")
            self._create_workflow()
            self.app = self.workflow.compile()
            
            print_title("¡Colección recreada con éxito!")
            return True
            
        except Exception as e:
            print(f"Error al recrear la colección: {str(e)}")
            return False 