from ..vectorstore.document_uploader import DocumentUploader

class LangAgent:
    def __init__(self, config_path: str):
        # ...existing code...
        
        # Inicializar DocumentUploader
        context_generator = None
        if self.config.get('context_generation', {}).get('enabled', False):
            # Inicializar generador de contexto si está habilitado
            context_generator = self._init_context_generator()
        
        self.document_uploader = DocumentUploader(
            self.vector_store, 
            context_generator
        )
        
        # Cargar documentos usando el uploader
        self._load_initial_documents()
    
    def _load_initial_documents(self):
        """Carga inicial de documentos usando DocumentUploader"""
        try:
            # Cargar colección por defecto
            default_source = self.config.get('data_sources', {}).get('default', 'output_md')
            if os.path.exists(default_source):
                self.document_uploader.upload_documents(default_source, "default")
            
            # Cargar colecciones adaptativas
            adaptive_collections = self.config.get('adaptive_collections', {})
            for collection_name, collection_config in adaptive_collections.items():
                source_folder = collection_config.get('source_folder')
                if source_folder and os.path.exists(source_folder):
                    self.document_uploader.upload_documents(source_folder, collection_name)
                    
        except Exception as e:
            logger.error(f"Error en carga inicial de documentos: {e}")
    
    def _init_context_generator(self):
        """Inicializa el generador de contexto si está configurado"""
        # Implementar según tu generador de contexto existente
        pass
    
    def add_documents_to_collection(self, source_folder: str, collection_name: str = "default") -> bool:
        """
        Añade nuevos documentos a una colección existente
        
        Args:
            source_folder: Carpeta con los nuevos documentos
            collection_name: Nombre de la colección
            
        Returns:
            bool: True si se añadieron exitosamente
        """
        return self.document_uploader.upload_documents(source_folder, collection_name)
    
    def reload_collection(self, source_folder: str, collection_name: str = "default", force: bool = False) -> bool:
        """
        Recarga una colección, opcionalmente forzando recarga completa
        
        Args:
            source_folder: Carpeta con los documentos
            collection_name: Nombre de la colección
            force: Si True, fuerza recarga completa
            
        Returns:
            bool: True si se recargó exitosamente
        """
        if force:
            return self.document_uploader.force_reload_collection(source_folder, collection_name)
        else:
            return self.document_uploader.upload_documents(source_folder, collection_name)