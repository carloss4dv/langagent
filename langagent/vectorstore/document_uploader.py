from typing import List, Dict
import logging

class VectorStore:
    def add_documents(self, texts: List[str], metadatas: List[Dict], collection_name: str) -> bool:
        # Simulated method for adding documents to a vector store
        return True

class DocumentUploader:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.logger = logging.getLogger(__name__)

    def _upload_chunks_to_collection(self, chunks: List[Dict], collection_name: str) -> bool:
        """Subir chunks a una colección específica con manejo mejorado de IDs."""
        try:
            texts = [chunk['text'] for chunk in chunks]
            metadatas = []
            
            for chunk in chunks:
                metadata = chunk.copy()
                metadata.pop('text', None)  # Remove text from metadata to avoid duplication
                
                # Ensure metadata is JSON serializable
                for key, value in metadata.items():
                    if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        metadata[key] = str(value)
                
                metadatas.append(metadata)
            
            # Add documents with auto-generated IDs
            success = self.vector_store.add_documents(texts, metadatas, collection_name)
            
            if success:
                self.logger.info(f"Successfully uploaded {len(chunks)} chunks to collection '{collection_name}'")
                return True
            else:
                self.logger.error(f"Failed to upload chunks to collection '{collection_name}'")
                return False
                
        except Exception as e:
            self.logger.error(f"Error uploading chunks to collection '{collection_name}': {str(e)}")
            return False