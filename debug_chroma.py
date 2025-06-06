#!/usr/bin/env python3
"""
Script de diagnóstico para Chroma Vector Store

Este script ayuda a diagnosticar problemas con la vectorstore de Chroma
y proporciona información detallada sobre su estado.
"""

import os
import sys
import logging
from langagent.vectorstore import ChromaVectorStore, create_embeddings
from langagent.config.config import VECTORSTORE_CONFIG

# Configurar logging para ver toda la información
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("🔍 DIAGNÓSTICO DE CHROMA VECTOR STORE")
    print("=" * 50)
    
    # 1. Verificar configuración
    print("\n📋 1. VERIFICANDO CONFIGURACIÓN:")
    print(f"   Vector DB Type: {VECTORSTORE_CONFIG.get('vector_db_type')}")
    print(f"   Persist Directory: {VECTORSTORE_CONFIG.get('persist_directory')}")
    print(f"   Collection Name: {VECTORSTORE_CONFIG.get('collection_name')}")
    print(f"   K Retrieval: {VECTORSTORE_CONFIG.get('k_retrieval')}")
    
    # 2. Verificar directorio de persistencia
    persist_dir = VECTORSTORE_CONFIG.get('persist_directory', './vectordb')
    collection_name = VECTORSTORE_CONFIG.get('collection_name', 'default_collection')
    full_path = os.path.join(persist_dir, collection_name)
    
    print(f"\n📁 2. VERIFICANDO DIRECTORIO:")
    print(f"   Directorio base: {persist_dir}")
    print(f"   Directorio completo: {full_path}")
    print(f"   Existe directorio base: {os.path.exists(persist_dir)}")
    print(f"   Existe directorio colección: {os.path.exists(full_path)}")
    
    if os.path.exists(full_path):
        files = os.listdir(full_path)
        print(f"   Archivos en directorio: {files}")
        
        # Mostrar tamaños de archivos
        for file in files:
            file_path = os.path.join(full_path, file)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                print(f"     - {file}: {size} bytes")
    
    # 3. Crear embeddings
    print(f"\n🔤 3. CREANDO EMBEDDINGS:")
    try:
        embeddings = create_embeddings()
        print(f"   ✅ Embeddings creados exitosamente: {type(embeddings)}")
    except Exception as e:
        print(f"   ❌ Error al crear embeddings: {e}")
        return
    
    # 4. Inicializar ChromaVectorStore
    print(f"\n⚙️ 4. INICIALIZANDO CHROMA VECTOR STORE:")
    try:
        chroma_store = ChromaVectorStore()
        print(f"   ✅ ChromaVectorStore inicializado correctamente")
    except Exception as e:
        print(f"   ❌ Error al inicializar ChromaVectorStore: {e}")
        return
    
    # 5. Intentar cargar vectorstore existente
    print(f"\n📂 5. INTENTANDO CARGAR VECTORSTORE EXISTENTE:")
    try:
        vectorstore = chroma_store.load_vectorstore(embeddings, collection_name)
        if vectorstore:
            print(f"   ✅ Vectorstore cargado exitosamente")
            
            # Debug detallado del estado
            chroma_store.debug_vectorstore_status(vectorstore, collection_name)
            
        else:
            print(f"   ⚠️ No se pudo cargar vectorstore existente (puede no existir)")
            
    except Exception as e:
        print(f"   ❌ Error al cargar vectorstore: {e}")
        vectorstore = None
    
    # 6. Si no existe, ofrecer crear una de prueba
    if vectorstore is None:
        print(f"\n🔨 6. CREANDO VECTORSTORE DE PRUEBA:")
        try:
            from langchain_core.documents import Document
            
            # Crear documentos de prueba
            test_docs = [
                Document(page_content="Este es un documento de prueba número 1", metadata={"source": "test1"}),
                Document(page_content="Este es un documento de prueba número 2", metadata={"source": "test2"}),
                Document(page_content="Documento de prueba para SEGEDA sistema DATUZ", metadata={"source": "test3", "cubo": "TEST"})
            ]
            
            print(f"   Creando vectorstore con {len(test_docs)} documentos de prueba...")
            
            vectorstore = chroma_store.create_vectorstore(test_docs, embeddings, collection_name)
            
            if vectorstore:
                print(f"   ✅ Vectorstore de prueba creado exitosamente")
                chroma_store.debug_vectorstore_status(vectorstore, collection_name)
            else:
                print(f"   ❌ Error al crear vectorstore de prueba")
                
        except Exception as e:
            print(f"   ❌ Error al crear vectorstore de prueba: {e}")
    
    # 7. Probar retriever
    if vectorstore:
        print(f"\n🔍 7. PROBANDO RETRIEVER:")
        try:
            retriever = chroma_store.create_retriever(vectorstore, k=3)
            
            if retriever:
                print(f"   ✅ Retriever creado exitosamente")
                
                # Probar varias consultas
                test_queries = [
                    "test",
                    "documento",
                    "SEGEDA",
                    "sistema",
                    "prueba"
                ]
                
                for query in test_queries:
                    try:
                        results = retriever.invoke(query)
                        print(f"   Query '{query}': {len(results)} documentos recuperados")
                        
                        for i, doc in enumerate(results[:2]):  # Mostrar primeros 2
                            print(f"     - Doc {i+1}: {doc.page_content[:50]}...")
                            
                    except Exception as e:
                        print(f"   ❌ Error en query '{query}': {e}")
                        
            else:
                print(f"   ❌ No se pudo crear retriever")
                
        except Exception as e:
            print(f"   ❌ Error al probar retriever: {e}")
    
    # 8. Resumen y recomendaciones
    print(f"\n📋 8. RESUMEN Y RECOMENDACIONES:")
    
    if vectorstore is None:
        print(f"   ❌ PROBLEMA: No se pudo cargar ni crear vectorstore")
        print(f"   💡 RECOMENDACIONES:")
        print(f"      - Verificar que el directorio {persist_dir} tenga permisos de escritura")
        print(f"      - Verificar que langchain-chroma esté instalado correctamente")
        print(f"      - Verificar que los embeddings funcionen correctamente")
        print(f"      - Intentar cambiar vector_db_type a 'chroma' en config.py")
        
    else:
        # Verificar si hay documentos
        try:
            test_results = vectorstore.similarity_search("test", k=1)
            if not test_results:
                print(f"   ⚠️ ADVERTENCIA: Vectorstore existe pero no contiene documentos")
                print(f"   💡 RECOMENDACIONES:")
                print(f"      - Cargar documentos en la vectorstore")
                print(f"      - Verificar que los documentos se indexaron correctamente")
            else:
                print(f"   ✅ ÉXITO: Vectorstore funciona correctamente")
                print(f"   💡 Para usar Chroma en lugar de Milvus:")
                print(f"      - Cambiar 'vector_db_type': 'chroma' en config.py")
                
        except Exception as e:
            print(f"   ⚠️ ADVERTENCIA: Error al verificar documentos: {e}")
    
    print(f"\n🏁 Diagnóstico completado!")

if __name__ == "__main__":
    main() 