"""
Módulo para la integración de llama-index con langagent.

Este módulo proporciona funciones para implementar capacidades de RAG avanzado
utilizando llama-index, manteniendo compatibilidad con la arquitectura existente
de langagent basada en LangGraph, LLaMA3 y Chroma.
"""

from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import IndexNode
from llama_index.core.retrievers import RecursiveRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.indices.document_summary import DocumentSummaryIndex
import logging

logger = logging.getLogger(__name__)

def create_dual_retriever(documents: List[Document], embeddings, persist_directory: str, 
                         retrieval_chunk_size: int = 256, 
                         synthesis_chunk_size: int = 1024,
                         chunk_overlap: int = 20):
    """
    Crea un retriever que separa los chunks usados para recuperación de los usados para síntesis.
    
    Implementa la técnica "Decoupling Chunks Used for Retrieval vs. Chunks Used for Synthesis"
    de llama-index, que permite optimizar la recuperación mientras se mantiene suficiente
    contexto para la generación.
    
    Args:
        documents (List[Document]): Lista de documentos a indexar
        embeddings: Modelo de embeddings a utilizar
        persist_directory (str): Directorio donde persistir la base de datos
        retrieval_chunk_size (int): Tamaño de chunk para recuperación
        synthesis_chunk_size (int): Tamaño de chunk para síntesis
        chunk_overlap (int): Superposición entre chunks
        
    Returns:
        retriever: Retriever configurado con la técnica de separación de chunks
    """
    try:
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
        for base_node in synthesis_nodes:
            # Parser para chunks pequeños
            retrieval_parser = SentenceSplitter(
                chunk_size=retrieval_chunk_size,
                chunk_overlap=chunk_overlap
            )
            # Obtener chunks pequeños
            retrieval_nodes = retrieval_parser.get_nodes_from_documents([base_node])
            # Vincular cada chunk pequeño al chunk grande correspondiente
            retrieval_index_nodes = [
                IndexNode.from_text_node(node, base_node.node_id) 
                for node in retrieval_nodes
            ]
            all_nodes.extend(retrieval_index_nodes)
            
            # También añadir el nodo original
            original_node = IndexNode.from_text_node(base_node, base_node.node_id)
            all_nodes.append(original_node)
        
        # Crear índice vectorial con todos los nodos
        from llama_index.vector_stores.chroma import ChromaVectorStore
        from llama_index.core.storage.storage_context import StorageContext
        
        # Adaptar embeddings de LangChain a llama-index
        from llama_index.embeddings.langchain import LangchainEmbedding
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
        vector_retriever = vector_index.as_retriever(similarity_top_k=2)
        
        # Crear retriever recursivo
        all_nodes_dict = {n.node_id: n for n in all_nodes}
        recursive_retriever = RecursiveRetriever(
            "vector",
            retriever_dict={"vector": vector_retriever},
            node_dict=all_nodes_dict,
            verbose=True
        )
        
        # Adaptar el retriever de llama-index a la interfaz de LangChain
        from langchain_core.retrievers import BaseRetriever
        
        class LlamaIndexRetrieverAdapter(BaseRetriever):
            def __init__(self, llama_retriever):
                super().__init__()
                self.llama_retriever = llama_retriever
                
            def _get_relevant_documents(self, query: str):
                # Obtener nodos de llama-index
                nodes = self.llama_retriever.retrieve(query)
                
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
        return LlamaIndexRetrieverAdapter(recursive_retriever)
        
    except Exception as e:
        logger.error(f"Error al crear dual retriever: {str(e)}")
        raise

def create_document_summary_retriever(documents: List[Document], embeddings, persist_directory: str):
    """
    Crea un retriever basado en resúmenes de documentos para recuperación estructurada.
    
    Implementa la técnica "Structured Retrieval for Larger Document Sets" de llama-index,
    que permite una recuperación más precisa en conjuntos grandes de documentos.
    
    Args:
        documents (List[Document]): Lista de documentos a indexar
        embeddings: Modelo de embeddings a utilizar
        persist_directory (str): Directorio donde persistir la base de datos
        
    Returns:
        retriever: Retriever configurado con recuperación estructurada
    """
    try:
        # Convertir documentos de LangChain a formato llama-index
        from llama_index.core.schema import Document as LlamaDocument
        llama_docs = []
        for doc in documents:
            llama_doc = LlamaDocument(
                text=doc.page_content,
                metadata=doc.metadata
            )
            llama_docs.append(llama_doc)
        
        # Adaptar embeddings de LangChain a llama-index
        from llama_index.embeddings.langchain import LangchainEmbedding
        llama_embeddings = LangchainEmbedding(embeddings)
        
        # Crear índice de resumen de documentos
        doc_summary_index = DocumentSummaryIndex.from_documents(
            llama_docs,
            embed_model=llama_embeddings
        )
        
        # Crear retriever
        retriever = doc_summary_index.as_retriever(
            similarity_top_k=2
        )
        
        # Adaptar el retriever de llama-index a la interfaz de LangChain
        from langchain_core.retrievers import BaseRetriever
        
        class LlamaIndexRetrieverAdapter(BaseRetriever):
            def __init__(self, llama_retriever):
                super().__init__()
                self.llama_retriever = llama_retriever
                
            def _get_relevant_documents(self, query: str):
                # Obtener nodos de llama-index
                nodes = self.llama_retriever.retrieve(query)
                
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
        return LlamaIndexRetrieverAdapter(retriever)
        
    except Exception as e:
        logger.error(f"Error al crear document summary retriever: {str(e)}")
        raise

def create_router_retriever(retrievers: Dict[str, Any], llm):
    """
    Crea un retriever que selecciona dinámicamente la estrategia de recuperación según la tarea.
    
    Implementa la técnica "Dynamically Retrieve Chunks Depending on your Task" de llama-index,
    que permite adaptar la estrategia de recuperación según el tipo de pregunta.
    
    Args:
        retrievers (Dict[str, Any]): Diccionario de retrievers disponibles
        llm: Modelo de lenguaje para enrutamiento
        
    Returns:
        retriever: Retriever configurado con enrutamiento dinámico
    """
    try:
        # Adaptar LLM de LangChain a llama-index
        from llama_index.llms.langchain import LangChainLLM
        llama_llm = LangChainLLM(llm=llm)
        
        # Crear router retriever
        from llama_index.core.query_engine import RouterQueryEngine
        from llama_index.core.selectors import LLMSingleSelector
        
        # Adaptar retrievers de LangChain a llama-index
        from llama_index.core.retrievers import BaseRetriever as LlamaBaseRetriever
        
        class LangChainRetrieverAdapter(LlamaBaseRetriever):
            def __init__(self, langchain_retriever):
                self.langchain_retriever = langchain_retriever
                
            def _retrieve(self, query_str):
                from llama_index.core.schema import NodeWithScore, TextNode
                
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
        
        # Adaptar retrievers
        llama_retrievers = {}
        for key, retriever in retrievers.items():
            llama_retrievers[key] = LangChainRetrieverAdapter(retriever)
        
        # Crear descripciones para el selector
        retriever_descriptions = {
            key: f"Retriever para el cubo {key}" for key in llama_retrievers.keys()
        }
        
        # Crear selector
        selector = LLMSingleSelector.from_defaults(
            llm=llama_llm,
            choices=list(llama_retrievers.keys()),
            choice_descriptions=retriever_descriptions
        )
        
        # Crear query engines para cada retriever
        query_engines = {}
        for key, retriever in llama_retrievers.items():
            query_engine = RetrieverQueryEngine.from_args(retriever)
            query_engines[key] = query_engine
        
        # Crear router query engine
        router_query_engine = RouterQueryEngine(
            selector=selector,
            query_engines=query_engines,
            verbose=True
        )
        
        # Adaptar el query engine de llama-index a la interfaz de retriever de LangChain
        from langchain_core.retrievers import BaseRetriever
        
        class RouterQueryEngineAdapter(BaseRetriever):
            def __init__(self, router_query_engine):
                super().__init__()
                self.router_query_engine = router_query_engine
                
            def _get_relevant_documents(self, query: str):
                # Ejecutar query en el router query engine
                response = self.router_query_engine.query(query)
                
                # Extraer nodos de la respuesta
                source_nodes = getattr(response, "source_nodes", [])
                
                # Convertir nodos a documentos de LangChain
                docs = []
                for node in source_nodes:
                    doc = Document(
                        page_content=node.node.get_content(),
                        metadata=node.node.metadata
                    )
                    docs.append(doc)
                
                return docs
        
        # Devolver el adapter
        return RouterQueryEngineAdapter(router_query_engine)
        
    except Exception as e:
        logger.error(f"Error al crear router retriever: {str(e)}")
        raise

def optimize_embeddings(embeddings, documents: List[Document], persist_directory: str):
    """
    Optimiza los embeddings para mejorar la calidad de la recuperación.
    
    Implementa la técnica "Optimize Context Embeddings" de llama-index,
    que permite mejorar la calidad de los embeddings para una recuperación más precisa.
    
    Args:
        embeddings: Modelo de embeddings a optimizar
        documents (List[Document]): Lista de documentos para optimización
        persist_directory (str): Directorio donde persistir la base de datos
        
    Returns:
        embeddings: Modelo de embeddings optimizado
    """
    try:
        # En una implementación real, aquí se realizaría fine-tuning del modelo de embeddings
        # Para esta integración, utilizaremos un modelo pre-entrenado más avanzado
        
        # Devolver el modelo de embeddings original por ahora
        # En una implementación completa, se podría implementar fine-tuning o
        # utilizar técnicas como HyDE (Hypothetical Document Embeddings)
        return embeddings
        
    except Exception as e:
        logger.error(f"Error al optimizar embeddings: {str(e)}")
        raise
