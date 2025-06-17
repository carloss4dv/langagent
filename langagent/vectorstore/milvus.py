import uuid
import hashlib
from typing import List, Dict, Any, Optional
from pymilvus import Collection, utility
from pymilvus.orm import FieldSchema, CollectionSchema
from pymilvus import DataType

class MilvusVectorStore:
    def __init__(self, embedding_model, logger, embedding_dim=768):
        self.embedding_model = embedding_model
        self.logger = logger
        self.embedding_dim = embedding_dim

    def _ensure_collection_schema(self, collection_name: str) -> None:
        """Ensure collection exists with proper schema including auto_id configuration."""
        try:
            if not utility.has_collection(collection_name):
                # Define schema with auto_id enabled
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=65535),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="metadata", dtype=DataType.JSON)
                ]
                schema = CollectionSchema(fields=fields, description="Document embeddings collection")
                collection = Collection(name=collection_name, schema=schema)
                
                # Create index
                index_params = {
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024}
                }
                collection.create_index(field_name="embedding", index_params=index_params)
                self.logger.info(f"Colección '{collection_name}' creada con esquema actualizado")
            else:
                collection = Collection(collection_name)
                
            collection.load()
            
        except Exception as e:
            self.logger.error(f"Error configurando esquema de colección: {str(e)}")
            raise

    def _generate_document_id(self, text: str, metadata: Dict[str, Any]) -> str:
        """Generate a unique ID for a document based on content and metadata."""
        # Create a deterministic ID based on content hash
        content_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        
        # Include relevant metadata in ID generation
        if 'source' in metadata:
            source_hash = hashlib.md5(str(metadata['source']).encode('utf-8')).hexdigest()[:8]
            return f"{source_hash}_{content_hash}"
        
        return f"doc_{content_hash}"

    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]], collection_name: str) -> bool:
        """Añadir documentos a la colección con IDs generados automáticamente."""
        try:
            self._ensure_collection_schema(collection_name)
            
            if len(texts) != len(metadatas):
                raise ValueError("El número de textos debe coincidir con el número de metadatos")

            # Generate embeddings
            embeddings = self.embedding_model.embed_documents(texts)
            
            # Generate unique IDs for each document
            document_ids = [self._generate_document_id(text, metadata) 
                          for text, metadata in zip(texts, metadatas)]
            
            # Prepare data for insertion
            entities = [
                document_ids,           # ids
                embeddings,            # embeddings
                texts,                 # texts
                metadatas             # metadata
            ]

            collection = Collection(collection_name)
            
            # Insert data with explicit IDs
            insert_result = collection.insert(entities)
            collection.flush()
            
            self.logger.info(f"Añadidos {len(texts)} documentos a la colección '{collection_name}'")
            self.logger.info(f"IDs generados: {insert_result.primary_keys[:5]}..." if len(insert_result.primary_keys) > 5 else f"IDs: {insert_result.primary_keys}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error al añadir documentos a la colección: {str(e)}")
            return False

    # ...existing code...