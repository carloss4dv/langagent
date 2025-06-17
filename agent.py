from .vectorstore.document_uploader import DocumentUploader

class Agent:
    def __init__(self, name, config_file='config.json'):
        # ...existing code...
        self.document_uploader = None
        # ...existing code...
        
        # Remove document loading logic from here
        # self._load_documents() # Remove this line
        
        # Initialize document uploader after vector store is ready
        if self.vector_store:
            self.document_uploader = DocumentUploader(self.vector_store)
    
    def _generate_context_if_enabled(self):
        """Generate context for documents if context generator is enabled."""
        if not self.config.get('generate_context', False):
            return
            
        try:
            logger.info('Generating context for documents...')
            context_generator = ContextGenerator(self.llm, self.config.get('context_config', {}))
            
            # Generate context for documents in output_md directory
            md_dir = Path('output_md')
            if md_dir.exists():
                md_files = list(md_dir.glob('*.md'))
                for md_file in md_files:
                    try:
                        context_generator.generate_context_for_file(str(md_file))
                        logger.info(f'Context generated for {md_file.name}')
                    except Exception as e:
                        logger.error(f'Error generating context for {md_file.name}: {e}')
            
        except Exception as e:
            logger.error(f'Error in context generation: {e}')
    