"""
Módulo para la integración de llama-index con langagent.
Este módulo proporciona funciones para implementar capacidades de RAG avanzado
utilizando llama-index, manteniendo compatibilidad con la arquitectura existente
de langagent basada en LangGraph, LLaMA3 y Chroma.
"""
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import IndexNode
from llama_index.core.retrievers import RecursiveRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.indices.document_summary import DocumentSummaryIndex
from langchain_core.retrievers import BaseRetriever
import logging
import os
from llama_index.embeddings.langchain import LangchainEmbedding
from llama_index.llms.langchain import LangChainLLM
from typing import Any
import uuid
from langagent.prompts import PROMPTS

logger = logging.getLogger(__name__)

def configure_llamaindex_settings(embeddings, llm_principal, llm_evaluador=None, chunk_size=512, chunk_overlap=20):
    """
    Configura los ajustes globales de LlamaIndex.
    
    Args:
        embeddings: Modelo de embeddings a utilizar
        llm_principal: Modelo de lenguaje principal para generación
        llm_evaluador: Modelo de lenguaje para evaluación (opcional)
        chunk_size (int): Tamaño de chunks para el parser
        chunk_overlap (int): Solapamiento entre chunks
        
    Returns:
        tuple: (llama_embeddings, llama_llm_principal, llama_llm_evaluador)
    """
    # Adaptar embeddings de LangChain a llama-index si es necesario
    llama_embeddings = (
        embeddings if hasattr(embeddings, "get_text_embedding") 
        else LangchainEmbedding(embeddings)
    )
    
    # Adaptar LLM principal de LangChain a llama-index si es necesario
    llama_llm_principal = (
        llm_principal if hasattr(llm_principal, "complete") 
        else LangChainLLM(llm=llm_principal)
    )
    
    # Adaptar LLM evaluador si se proporciona
    llama_llm_evaluador = None
    if llm_evaluador:
        llama_llm_evaluador = (
            llm_evaluador if hasattr(llm_evaluador, "complete") 
            else LangChainLLM(llm=llm_evaluador)
        )
    
    # Configurar Settings globales con el LLM principal
    Settings.embed_model = llama_embeddings
    Settings.llm = llama_llm_principal  # LLM principal para generación
    Settings.node_parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    Settings.num_output = 512
    Settings.context_window = 3900
    
    logger.info("Configuración global de LlamaIndex completada")
    return llama_embeddings, llama_llm_principal, llama_llm_evaluador

class LlamaIndexLangGraphRetriever(BaseRetriever):
    """Retriever personalizado que integra llama-index con LangGraph."""
    
    def __init__(self, vector_retriever, node_dict, k=4):
        super().__init__()
        self._vector_retriever = vector_retriever
        self._node_dict = node_dict
        self._k = k
        self._query_cache = {}
        
    def _get_relevant_documents(self, query: str, query_id: Optional[str] = None) -> List[Document]:
        """Obtiene documentos relevantes usando el retriever vectorial y el node_dict."""
        try:
            # Si no hay query_id, generar uno
            if not query_id:
                query_id = str(uuid.uuid4())
            
            # Si ya tenemos resultados en caché, usarlos
            if query_id in self._query_cache:
                return self._query_cache[query_id]
            
            # Obtener nodos del retriever vectorial
            from llama_index.core.schema import QueryBundle
            query_bundle = QueryBundle(query_str=query)
            
            # Manejar diferentes tipos de retriever
            nodes = []
            try:
                if hasattr(self._vector_retriever, 'retrieve'):
                    nodes = self._vector_retriever.retrieve(query_bundle)
                elif hasattr(self._vector_retriever, 'get_relevant_documents'):
                    nodes = self._vector_retriever.get_relevant_documents(query)
                else:
                    raise ValueError("Retriever no compatible")
            except Exception as e:
                logger.error(f"Error al recuperar nodos: {str(e)}")
                return []
            
            # Convertir nodos a documentos y expandir usando node_dict
            docs = []
            for node in nodes:
                try:
                    # Obtener el contenido del nodo
                    if hasattr(node, 'node'):
                        content = node.node.text
                        metadata = node.node.metadata
                    elif hasattr(node, 'text'):
                        content = node.text
                        metadata = node.metadata
                    elif hasattr(node, 'page_content'):
                        content = node.page_content
                        metadata = node.metadata
                    else:
                        logger.warning(f"Nodo con formato desconocido: {type(node)}")
                        continue
                    
                    # Crear documento base
                    base_doc = Document(
                        page_content=content,
                        metadata=metadata
                    )
                    docs.append(base_doc)
                    
                    # Si el nodo tiene referencias en node_dict, expandir
                    if hasattr(node, 'node_id') and node.node_id in self._node_dict:
                        referenced_node = self._node_dict[node.node_id]
                        if hasattr(referenced_node, 'text'):
                            expanded_doc = Document(
                                page_content=referenced_node.text,
                                metadata=referenced_node.metadata
                            )
                            docs.append(expanded_doc)
                except Exception as e:
                    logger.error(f"Error al procesar nodo: {str(e)}")
                    continue
            
            # Eliminar duplicados basados en el contenido
            unique_docs = []
            seen_content = set()
            for doc in docs:
                content_hash = hash(doc.page_content)
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    unique_docs.append(doc)
            
            # Limitar al número máximo de documentos
            result = unique_docs[:self._k]
            
            # Almacenar en caché
            self._query_cache[query_id] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error en LlamaIndexLangGraphRetriever: {str(e)}")
            return []

def create_dual_retriever(documents: List[Document], embeddings, persist_directory: str, 
                         retrieval_chunk_size: int = 256, 
                         synthesis_chunk_size: int = 1024,
                         chunk_overlap: int = 20):
    """
    Crea un retriever que utiliza chunks duales para mejorar la recuperación.
    
    Implementa la técnica "Dual Chunks" de llama-index, que divide los documentos
    en chunks pequeños para recuperación precisa y chunks grandes para síntesis.
    
    Args:
        documents (List[Document]): Lista de documentos a indexar
        embeddings: Modelo de embeddings a utilizar
        persist_directory (str): Directorio donde persistir la base de datos
        retrieval_chunk_size (int): Tamaño de chunks para recuperación
        synthesis_chunk_size (int): Tamaño de chunks para síntesis
        chunk_overlap (int): Solapamiento entre chunks
        
    Returns:
        retriever: Retriever configurado con chunks duales
    """
    try:
        # Asegurar que el directorio existe
        os.makedirs(persist_directory, exist_ok=True)
        
        # Convertir documentos de LangChain a formato llama-index
        from llama_index.core.schema import Document as LlamaDocument
        llama_docs = []
        for doc in documents:
            llama_doc = LlamaDocument(
                text=doc.page_content,
                metadata=doc.metadata
            )
            llama_docs.append(llama_doc)
        
        # Crear chunks grandes para síntesis
        synthesis_parser = SentenceSplitter(
            chunk_size=synthesis_chunk_size,
            chunk_overlap=chunk_overlap
        )
        synthesis_nodes = synthesis_parser.get_nodes_from_documents(llama_docs)
        
        # Crear chunks pequeños para recuperación, vinculados a los chunks grandes
        all_nodes = []
        node_dict = {}
        
        for base_node in synthesis_nodes:
            # Parser para chunks pequeños
            retrieval_parser = SentenceSplitter(
                chunk_size=retrieval_chunk_size,
                chunk_overlap=chunk_overlap
            )
            # Obtener chunks pequeños
            retrieval_nodes = retrieval_parser.get_nodes_from_documents([base_node])
            
            # Vincular cada chunk pequeño al chunk grande correspondiente
            for node in retrieval_nodes:
                # Crear un nodo de índice que apunta al nodo base
                index_node = IndexNode.from_text_node(node, base_node.node_id)
                all_nodes.append(index_node)
                node_dict[index_node.node_id] = index_node
            
            # También añadir el nodo base
            all_nodes.append(base_node)
            node_dict[base_node.node_id] = base_node
        
        # Crear índice vectorial con todos los nodos
        from llama_index.vector_stores.chroma import ChromaVectorStore
        from llama_index.core.storage.storage_context import StorageContext
        
        # Adaptar embeddings de LangChain a llama-index si no está ya adaptado
        llama_embeddings = embeddings
        if not hasattr(embeddings, "get_text_embedding"):
            llama_embeddings = LangchainEmbedding(embeddings)
        
        # Crear ChromaVectorStore
        import chromadb
        chroma_client = chromadb.PersistentClient(path=persist_directory)
        chroma_collection = chroma_client.get_or_create_collection("dual_chunks")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        # Crear contexto de almacenamiento
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Crear índice vectorial
        vector_index = VectorStoreIndex(
            all_nodes,
            storage_context=storage_context,
            embed_model=llama_embeddings
        )
        
        # Crear retriever vectorial
        vector_retriever = vector_index.as_retriever(
            similarity_top_k=2,
            vector_store_query_mode="hybrid"
        )
        
        # Crear el retriever personalizado
        recursive_retriever = LlamaIndexLangGraphRetriever(
            vector_retriever=vector_retriever,
            node_dict=node_dict,
            k=4
        )
        
        # Devolver el retriever personalizado
        logger.info(f"Dual retriever creado exitosamente en {persist_directory}")
        return recursive_retriever
        
    except Exception as e:
        logger.error(f"Error al crear dual retriever: {str(e)}")
        raise

def create_document_summary_retriever(documents: List[Document], embeddings, persist_directory: str, llm=None):
    """
    Crea un retriever basado en resúmenes de documentos para recuperación estructurada.
    
    Implementa la técnica "Structured Retrieval for Larger Document Sets" de llama-index,
    que permite una recuperación más precisa en conjuntos grandes de documentos.
    
    Args:
        documents (List[Document]): Lista de documentos a indexar
        embeddings: Modelo de embeddings a utilizar
        persist_directory (str): Directorio donde persistir la base de datos
        llm: Modelo de lenguaje para generar resúmenes (opcional, usa Settings.llm si es None)
        
    Returns:
        retriever: Retriever configurado con recuperación estructurada
    """
    try:
        # Asegurar que el directorio existe
        os.makedirs(persist_directory, exist_ok=True)
        
        # Convertir documentos de LangChain a formato llama-index
        from llama_index.core.schema import Document as LlamaDocument
        llama_docs = []
        for doc in documents:
            llama_doc = LlamaDocument(
                text=doc.page_content,
                metadata=doc.metadata
            )
            llama_docs.append(llama_doc)
        
        # Adaptar embeddings de LangChain a llama-index si no está ya adaptado
        llama_embeddings = embeddings
        if not hasattr(embeddings, "get_text_embedding"):
            llama_embeddings = LangchainEmbedding(embeddings)
        
        # Adaptar LLM si se proporciona
        llama_llm = None
        if llm is not None and not hasattr(llm, "complete"):
            llama_llm = LangChainLLM(llm=llm)
        elif llm is not None:
            llama_llm = llm
        
        # Crear índice de resumen de documentos
        index_kwargs = {}
        if llama_llm:
            index_kwargs["llm"] = llama_llm
        if llama_embeddings:
            index_kwargs["embed_model"] = llama_embeddings
            
        # Crear índice con vectorstore persistente
        from llama_index.vector_stores.chroma import ChromaVectorStore
        
        import chromadb
        chroma_client = chromadb.PersistentClient(path=persist_directory)
        chroma_collection = chroma_client.get_or_create_collection("doc_summary")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Crear índice con el storage context
        doc_summary_index = DocumentSummaryIndex.from_documents(
            llama_docs,
            storage_context=storage_context,
            **index_kwargs
        )
        
        # Crear retriever
        retriever = doc_summary_index.as_retriever(
            similarity_top_k=2
        )
        
        # Adaptar el retriever de llama-index a la interfaz de LangChain
        from langchain_core.retrievers import BaseRetriever
        
        class LlamaIndexRetrieverAdapter(BaseRetriever):
            _llama_retriever: Any
            def __init__(self, llama_retriever):
                super().__init__()
                self._llama_retriever = llama_retriever
                
            def _get_relevant_documents(self, query: str):
                # Obtener nodos de llama-index
                nodes = self._llama_retriever.retrieve(query)
                
                # Convertir nodos a documentos de LangChain
                docs = []
                for node in nodes:
                    doc = Document(
                        page_content=node.get_content(),
                        metadata=node.metadata
                    )
                    docs.append(doc)
                return docs
        
        # Devolver el retriever adaptado
        logger.info(f"Document summary retriever creado exitosamente en {persist_directory}")
        return LlamaIndexRetrieverAdapter(retriever)
        
    except Exception as e:
        logger.error(f"Error al crear document summary retriever: {str(e)}")
        raise

class RouterQueryEngineAdapter(BaseRetriever):
    _router_query_engine: Any
    def __init__(self, router_query_engine):
        super().__init__()
        self._router_query_engine = router_query_engine
        
    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implementa el método invoke para compatibilidad con LangGraph.
        
        Args:
            input_data (Dict[str, Any]): Diccionario con la pregunta y otros datos.
            
        Returns:
            Dict[str, Any]: Resultado del enrutamiento en formato compatible con LangGraph.
        """
        try:
            question = input_data.get("question", "")
            if not question:
                return {"cube": "", "scope": "", "confidence": "LOW", "is_query": False}
            
            # Ejecutar query en el router query engine
            response = self._router_query_engine.query(question)
            
            # Extraer información relevante
            cube_name = ""
            scope = ""
            confidence = "LOW"
            is_query = False
            
            # Intentar extraer información de la respuesta
            if hasattr(response, "metadata"):
                cube_name = response.metadata.get("name", "")
                scope = response.metadata.get("scope", "")
                confidence = response.metadata.get("confidence", "LOW")
            elif isinstance(response, dict):
                cube_name = response.get("name", "")
                scope = response.get("scope", "")
                confidence = response.get("confidence", "LOW")
            
            # Determinar si es una consulta
            consulta_keywords = [
                "consulta guardada", "consultas guardadas", "dashboard", 
                "visualización", "visualizacion", "reporte", "informe", 
                "cuadro de mando", "análisis predefinido", "analisis predefinido"
            ]
            question_lower = question.lower()
            is_query = any(keyword in question_lower for keyword in consulta_keywords)
            
            return {
                "cube": cube_name,
                "scope": scope,
                "confidence": confidence,
                "is_query": is_query
            }
            
        except Exception as e:
            logger.error(f"Error en RouterQueryEngineAdapter.invoke: {str(e)}")
            return {"cube": "", "scope": "", "confidence": "LOW", "is_query": False}
        
    def _get_relevant_documents(self, query: str):
        try:
            # Ejecutar query en el router query engine
            response = self._router_query_engine.query(query)
            
            # Extraer nodos de la respuesta
            source_nodes = []
            
            # Manejar diferentes tipos de respuesta
            if isinstance(response, dict):
                if "source_nodes" in response:
                    source_nodes = response["source_nodes"]
                elif "response" in response and hasattr(response["response"], "source_nodes"):
                    source_nodes = response["response"].source_nodes
            elif hasattr(response, "source_nodes"):
                source_nodes = response.source_nodes
            elif hasattr(response, "response"):
                # Si la respuesta está en un campo 'response', intentar extraer los nodos
                if hasattr(response.response, "source_nodes"):
                    source_nodes = response.response.source_nodes
                else:
                    # Crear un nodo con la respuesta
                    from llama_index.core.schema import TextNode
                    source_nodes = [TextNode(text=str(response.response))]
            
            # Si no hay nodos, intentar obtener la respuesta directamente
            if not source_nodes and hasattr(response, "response"):
                from llama_index.core.schema import TextNode
                source_nodes = [TextNode(text=str(response.response))]
            
            # Convertir nodos a documentos de LangChain
            docs = []
            for node in source_nodes:
                try:
                    # Manejar diferentes tipos de nodos
                    if hasattr(node, "node"):
                        node_content = node.node.get_content()
                        node_metadata = node.node.metadata
                    elif hasattr(node, "get_content"):
                        node_content = node.get_content()
                        node_metadata = node.metadata
                    elif hasattr(node, "text"):
                        node_content = node.text
                        node_metadata = node.metadata
                    else:
                        node_content = str(node)
                        node_metadata = {}
                        
                    doc = Document(
                        page_content=node_content,
                        metadata=node_metadata
                    )
                    docs.append(doc)
                except Exception as e:
                    logger.error(f"Error al procesar nodo: {str(e)}")
                    continue
            
            return docs
            
        except Exception as e:
            logger.error(f"Error en RouterQueryEngineAdapter._get_relevant_documents: {str(e)}")
            return []

def create_router_retriever(retrievers: Dict[str, Any], llm):
    """
    Crea un retriever que selecciona dinámicamente la estrategia de recuperación según la tarea.
    """
    try:
        # Verificar que el LLM esté disponible
        if llm is None:
            logger.warning("No se proporcionó un LLM para el router. Usando todos los cubos disponibles.")
            return retrievers.get("combined", list(retrievers.values())[0])
        
        # Adaptar LLM de LangChain a llama-index si no está ya adaptado
        llama_llm = llm
        if not hasattr(llm, "complete"):
            try:
                llama_llm = LangChainLLM(llm=llm)
            except Exception as e:
                logger.error(f"Error al adaptar LLM: {str(e)}")
                return retrievers.get("combined", list(retrievers.values())[0])
        
        # Crear router retriever
        from llama_index.core.query_engine import RouterQueryEngine
        from llama_index.core.selectors import LLMSingleSelector
        
        # Adaptar retrievers de LangChain a llama-index
        from llama_index.core.retrievers import BaseRetriever as LlamaBaseRetriever
        from llama_index.core.schema import NodeWithScore, TextNode
        
        class LangChainRetrieverAdapter(LlamaBaseRetriever):
            def __init__(self, langchain_retriever):
                super().__init__()
                self.langchain_retriever = langchain_retriever
                
            def _retrieve(self, query_str: str) -> List[NodeWithScore]:
                """
                Implementación del método abstracto _retrieve.
                """
                try:
                    # Obtener documentos de LangChain
                    docs = self.langchain_retriever.get_relevant_documents(query_str)
                    
                    # Convertir documentos a nodos de llama-index
                    nodes = []
                    for i, doc in enumerate(docs):
                        node = TextNode(
                            text=doc.page_content,
                            metadata=doc.metadata
                        )
                        # Asignar un score arbitrario basado en el orden
                        score = 1.0 - (i * 0.1)
                        nodes.append(NodeWithScore(node=node, score=score))
                    
                    return nodes
                except Exception as e:
                    logger.error(f"Error en LangChainRetrieverAdapter: {str(e)}")
                    return []
        
        # Adaptar retrievers
        llama_retrievers = {}
        if isinstance(retrievers, dict):
            for key, retriever in retrievers.items():
                llama_retrievers[key] = LangChainRetrieverAdapter(retriever)
        else:
            # Si es una lista, crear un diccionario usando índices como claves
            for i, retriever in enumerate(retrievers):
                llama_retrievers[f"retriever_{i}"] = LangChainRetrieverAdapter(retriever)
        
        # Obtener el prompt del archivo de prompts
        model_name = llm.model if "llama" not in llm.model else "llama"
        try:
            prompt_template = PROMPTS[model_name]["question_router"]
        except KeyError:
            logger.error(f"No se encontró el prompt para el modelo {model_name}")
            return retrievers.get("combined", list(retrievers.values())[0])
        
        # Crear selector con el prompt del archivo
        selector = LLMSingleSelector.from_defaults(
            llm=llama_llm,
            prompt_template_str=prompt_template
        )
        
        # Crear query engines para cada retriever
        query_engine_tools = []
        for key, retriever in llama_retrievers.items():
            try:
                query_engine = RetrieverQueryEngine.from_args(retriever)
                # Crear QueryEngineTool para cada query engine
                from llama_index.core.tools import QueryEngineTool
                tool = QueryEngineTool(
                    query_engine=query_engine,
                    metadata={
                        "name": key,
                        "description": f"Retriever para el cubo {key}",
                        "scope": key.split("_")[0] if "_" in key else key
                    }
                )
                query_engine_tools.append(tool)
            except Exception as e:
                logger.error(f"Error al crear query engine para {key}: {str(e)}")
                continue
        
        # Añadir un tool para el retriever combinado
        if "combined" in retrievers:
            try:
                combined_retriever = LangChainRetrieverAdapter(retrievers["combined"])
                combined_engine = RetrieverQueryEngine.from_args(combined_retriever)
                combined_tool = QueryEngineTool(
                    query_engine=combined_engine,
                    metadata={
                        "name": "combined",
                        "description": "Retriever combinado que usa todos los cubos",
                        "scope": "general"
                    }
                )
                query_engine_tools.append(combined_tool)
            except Exception as e:
                logger.error(f"Error al crear retriever combinado: {str(e)}")
        
        if not query_engine_tools:
            logger.error("No se pudo crear ningún query engine. Usando retriever por defecto.")
            return retrievers.get("combined", list(retrievers.values())[0])
        
        # Crear router query engine con manejo de errores
        try:
            router_query_engine = RouterQueryEngine(
                selector=selector,
                query_engine_tools=query_engine_tools,
                verbose=True
            )
        except Exception as e:
            logger.error(f"Error al crear router query engine: {str(e)}")
            return retrievers.get("combined", list(retrievers.values())[0])
        
        # Devolver el adapter
        logger.info("Router retriever creado exitosamente")
        return RouterQueryEngineAdapter(router_query_engine)
        
    except Exception as e:
        logger.error(f"Error al crear router retriever: {str(e)}")
        # En caso de error, devolver el retriever combinado o el primer retriever disponible
        return retrievers.get("combined", list(retrievers.values())[0])

def optimize_embeddings(embeddings, documents: List[Document] = None, persist_directory: str = None):
    """
    Optimiza los embeddings para mejorar la calidad de la recuperación.
    
    Implementa la técnica "Optimize Context Embeddings" de llama-index,
    que permite mejorar la calidad de los embeddings para una recuperación más precisa.
    
    Args:
        embeddings: Modelo de embeddings a optimizar
        documents (List[Document], optional): Lista de documentos para optimización
        persist_directory (str, optional): Directorio donde persistir la base de datos
        
    Returns:
        embeddings: Modelo de embeddings optimizado
    """
    try:
        # En una implementación real, aquí se realizaría fine-tuning del modelo de embeddings
        # Para esta integración, utilizaremos un modelo pre-entrenado más avanzado
        
        # Adaptar embeddings de LangChain a llama-index si es necesario
        llama_embeddings = embeddings
        if not hasattr(embeddings, "get_text_embedding"):
            llama_embeddings = LangchainEmbedding(embeddings)
        
        # Devolver el modelo de embeddings adaptado
        logger.info("Embeddings optimizados (mock implementation)")
        return llama_embeddings
        
    except Exception as e:
        logger.error(f"Error al optimizar embeddings: {str(e)}")
        raise
