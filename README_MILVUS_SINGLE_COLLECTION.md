# Milvus con Colección Única para Zilliz Cloud

## Descripción

Este documento explica la implementación de una arquitectura de **colección única** para Milvus/Zilliz Cloud en el sistema LangAgent. Esta aproximación es necesaria debido a la limitación de Zilliz Cloud que permite un máximo de 5 colecciones en su plan gratuito.

En lugar de usar múltiples colecciones (una por cubo de conocimiento), esta implementación almacena todos los documentos en una única colección y utiliza los metadatos y el filtrado para simular la separación por ámbitos y cubos.

## Ventajas

- **Compatible con Zilliz Cloud Free Tier**: permite usar el servicio gratuito que limita a 5 colecciones.
- **Reduce la complejidad de gestión**: una sola colección es más fácil de mantener y actualizar.
- **Mantiene la separación lógica**: a través de metadatos, mantenemos la separación por cubos y ámbitos.
- **Búsqueda eficiente**: gracias al filtrado de metadatos, las búsquedas siguen siendo precisas.

## Configuración

Para habilitar el modo de colección única, ajusta los siguientes parámetros en `config/config.py`:

```python
VECTORSTORE_CONFIG = {
    # Otras configuraciones...
    
    "vector_db_type": "milvus",  # Debe ser "milvus"
    
    # Configuración para enfoque de colección única
    "use_single_collection": True,  # Habilitar uso de colección única
    "unified_collection_name": "UnifiedKnowledgeBase",  # Nombre de la colección
    "always_update_collection": False,  # Si actualizar documentos en colecciones existentes
    "filter_by_metadata": True,  # Habilitar filtrado por metadatos en consultas
}
```

### Parámetros importantes:

- **use_single_collection**: cuando es `True`, todo el contenido se indexa en una sola colección.
- **unified_collection_name**: nombre de la colección única que se creará en Milvus.
- **always_update_collection**: si es `True`, los documentos se actualizarán en la colección existente al iniciar el sistema.
- **filter_by_metadata**: si es `True`, las consultas utilizarán filtrado por metadatos al buscar documentos.

## Configuración de Zilliz Cloud

Para conectar con Zilliz Cloud, debes configurar las siguientes variables de entorno:

```
ZILLIZ_CLOUD_URI=https://tu-instancia.api.gcp-us-west1.zillizcloud.com
ZILLIZ_CLOUD_TOKEN=tu_api_token
ZILLIZ_CLOUD_SECURE=True
```

Estas variables pueden configurarse en un archivo `.env` en la raíz del proyecto o como variables de entorno del sistema.

## Funcionamiento interno

### Indexación de documentos

1. Todos los documentos de todos los cubos y ámbitos se procesan y se les añaden metadatos clave:
   - **cubo_source**: identifica el cubo de origen del documento
   - **ambito**: identifica el ámbito al que pertenece el documento
   - **is_consulta**: booleano que indica si es una consulta guardada

2. Todos los documentos se almacenan en una única colección de Milvus.

### Recuperación de documentos

1. **Ruta de pregunta**: El sistema identifica el ámbito relevante para la pregunta.
2. **Filtrado por metadatos**: Se crea un filtro de metadatos basado en el ámbito identificado.
3. **Búsqueda semántica**: Se realiza una búsqueda vectorial con filtrado para encontrar los documentos más relevantes.
4. **Evaluación de relevancia**: Los documentos recuperados se evalúan para confirmar su relevancia.

## Modificaciones en el código

La implementación modifica principalmente tres archivos:

1. **models/workflow.py**: 
   - Función `retrieve()` modificada para soportar el modo de colección única.
   - Detección automática del tipo de vectorstore y ajuste del comportamiento.

2. **core/lang_chain_agent.py**: 
   - Método `setup_agent()` modificado para procesar todos los documentos en una sola colección.
   - Lógica condicional para usar enfoque tradicional o colección única.

3. **vectorstore/milvus.py**: 
   - Implementación del `MilvusFilterRetriever` que soporta filtrado por metadatos.
   - Ajustes para optimizar la búsqueda en Milvus con filtros.

## Compatibilidad

Esta implementación mantiene compatibilidad con:

- El modo tradicional multi-colección de Chroma DB.
- Instalaciones locales de Milvus sin limitaciones de colecciones.

Para volver al modo tradicional, simplemente configura `use_single_collection` a `False` en la configuración.

## Consideraciones de rendimiento

- Las búsquedas con filtrado pueden ser ligeramente más lentas que las búsquedas en colecciones separadas.
- La indexación inicial puede tardar más al procesar todos los documentos juntos.
- Para bases de conocimiento muy grandes (>100K documentos), puede ser necesario ajustar los parámetros de búsqueda.

## Limitaciones actuales

- No se implementa particionamiento explícito en Milvus (aunque se podría añadir en futuras versiones).
- La actualización de documentos requiere reiniciar el sistema cuando `always_update_collection` está habilitado. 