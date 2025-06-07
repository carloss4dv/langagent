# 📊 GENERACIÓN DE DIAGRAMAS RAG - GUÍA COMPLETA

## 🎯 Resumen
Este proyecto incluye diagramas detallados de las **Fases de Recuperación y Generación** del sistema RAG adaptativo con múltiples estrategias de chunking y evaluación granular.

## 📁 Archivos Generados

### Diagramas Fuente
- `diagrama_recuperacion.dot` - Fase de Recuperación (Graphviz)
- `diagrama_generacion.dot` - Fase de Generación (Graphviz)  
- `diagrama_recuperacion.puml` - Fase de Recuperación (PlantUML)

### Scripts de Automatización
- `install_tools.ps1` - Instalador automático de herramientas
- `generate_diagrams.ps1` - Generador automático de PNG

## 🚀 INSTALACIÓN RÁPIDA

### Paso 1: Instalar Herramientas
```powershell
# Ejecutar PowerShell como Administrador
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install_tools.ps1
```

### Paso 2: Generar Diagramas
```powershell
# Generar todos los PNG en directorio 'img'
.\generate_diagrams.ps1

# Opciones avanzadas
.\generate_diagrams.ps1 -OutputDir "mi_directorio" -DPI 600
```

## 🛠️ HERRAMIENTAS UTILIZADAS

### 1. **Graphviz** (Recomendado)
- **Ventajas**: Layout automático excelente, alta calidad, control preciso
- **Archivos**: `.dot`
- **Salida**: PNG de alta resolución
- **Instalación**: Automática vía Chocolatey

### 2. **PlantUML**
- **Ventajas**: Sintaxis más simple, buena para diagramas UML
- **Archivos**: `.puml`
- **Requisitos**: Java Runtime Environment
- **Instalación**: JAR descargado automáticamente

### 3. **Alternativas Disponibles**

#### **yEd Live** (Online)
- **URL**: https://www.yworks.com/yed-live/
- **Ventajas**: No requiere instalación, importa GraphML
- **Uso**: Importar archivos .dot convertidos a GraphML

#### **Draw.io / Diagrams.net**
- **URL**: https://app.diagrams.net/
- **Ventajas**: Gratuito, online, muchos formatos
- **Uso**: Recrear manualmente basándose en los diagramas

#### **Visio** (Microsoft)
- **Ventajas**: Integración Office, layouts profesionales
- **Uso**: Importar o recrear diagramas

#### **Lucidchart**
- **URL**: https://www.lucidchart.com/
- **Ventajas**: Colaborativo, templates profesionales
- **Uso**: Recrear con base en los layouts existentes

## 📋 COMANDOS MANUALES

### Graphviz (Archivos .dot)
```bash
# Calidad estándar
dot -Tpng -o img/fase_recuperacion_rag.png diagrama_recuperacion.dot
dot -Tpng -o img/fase_generacion_rag.png diagrama_generacion.dot

# Alta resolución
dot -Tpng -Gdpi=600 -o img/fase_recuperacion_rag_hd.png diagrama_recuperacion.dot

# Tamaño específico
dot -Tpng -Gsize=20,15 -Gdpi=300 -o img/fase_recuperacion_rag_large.png diagrama_recuperacion.dot

# Formato SVG (vectorial)
dot -Tsvg -o img/fase_recuperacion_rag.svg diagrama_recuperacion.dot

# Formato PDF
dot -Tpdf -o img/fase_recuperacion_rag.pdf diagrama_recuperacion.dot
```

### PlantUML (Archivos .puml)
```bash
# PNG básico
java -jar plantuml.jar -tpng diagrama_recuperacion.puml

# PNG en directorio específico
java -jar plantuml.jar -tpng -o img diagrama_recuperacion.puml

# SVG vectorial
java -jar plantuml.jar -tsvg -o img diagrama_recuperacion.puml

# Configuración de calidad
java -jar plantuml.jar -tpng -DPLANTUML_LIMIT_SIZE=8192 -o img diagrama_recuperacion.puml
```

## 🎨 PERSONALIZACIÓN

### Modificar Resolución
```powershell
# Cambiar DPI en generate_diagrams.ps1
.\generate_diagrams.ps1 -DPI 600  # Mayor calidad
.\generate_diagrams.ps1 -DPI 150  # Menor tamaño archivo
```

### Cambiar Colores (Graphviz)
Editar archivos `.dot` y modificar `fillcolor`:
```dot
node [fillcolor="#TU_COLOR_AQUI"]
```

### Cambiar Estilo (PlantUML)
Añadir temas en archivos `.puml`:
```plantuml
!theme aws-orange
!theme cerulean-outline
```

## 📊 ESPECIFICACIONES TÉCNICAS

### Diagramas Incluidos

#### 1. **Fase de Recuperación**
- **Query Rewriting Condicional**: Solo si viene de clarificación
- **Retrievers Adaptativos**: 256, 512, 1024 tokens
- **LLMs Utilizados**: 
  - `mistral-small-3.1:24b` (rewriting)
  - `llama3.2:3bm` (grading)
- **Vector Store**: Milvus/Zilliz Cloud
- **Parámetros**: k_retrieval=6, max_docs=15, threshold=0.7

#### 2. **Fase de Generación**
- **Dual Path**: RAG estándar + SQL queries
- **Evaluación Granular**: 4 métricas principales
- **Recuperación Adaptativa**: Cambio inteligente de estrategias
- **LLMs Utilizados**:
  - `mistral-small-3.1:24b` (generation)
  - `llama3.2:3bm` (evaluation)
- **Reintentos**: MAX_RETRIES=3 con lógica anti-bucle

### Métricas de Evaluación
- **Faithfulness** ≥ 0.7: Fidelidad a documentos fuente
- **Context Precision** ≥ 0.7: Precisión del contexto recuperado
- **Context Recall** ≥ 0.7: Completitud del contexto
- **Answer Relevance** ≥ 0.7: Relevancia de la respuesta

## 🔧 RESOLUCIÓN DE PROBLEMAS

### Error: "Graphviz no encontrado"
```powershell
# Reinstalar y actualizar PATH
choco install graphviz -y --force
refreshenv
# O reiniciar PowerShell
```

### Error: "Java no encontrado"
```powershell
# Verificar instalación
java -version
# Si falla, reinstalar
choco install openjdk11 -y
```

### PlantUML no descarga
1. Descargar manualmente: https://plantuml.com/download
2. Colocar `plantuml.jar` en el directorio del proyecto
3. Ejecutar: `.\generate_diagrams.ps1 -PlantUMLJar "ruta\a\plantuml.jar"`

### Archivos PNG corruptos o vacíos
- Verificar que los archivos fuente (.dot, .puml) no tienen errores de sintaxis
- Probar con resolución menor: `.\generate_diagrams.ps1 -DPI 150`
- Usar comandos manuales para depuración

## 📐 FORMATOS DE SALIDA DISPONIBLES

### Graphviz Soporta:
- **PNG**: Imágenes raster para documentos
- **SVG**: Vectorial, escalable infinitamente  
- **PDF**: Documentos profesionales
- **EPS**: PostScript para LaTeX
- **DOT**: Código fuente editable

### PlantUML Soporta:
- **PNG**: Imágenes estándar
- **SVG**: Vectorial
- **LaTeX**: Integración con documentos científicos
- **ASCII**: Texto plano para documentación

## 🎓 USO EN LATEX

Para incluir en documentos LaTeX:
```latex
\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{img/fase_recuperacion_rag.png}
\caption{Fase de Recuperación - Sistema RAG Adaptativo}
\label{fig:recuperacion_rag}
\end{figure}
```

Para máxima calidad en LaTeX:
```bash
# Generar PDF directamente
dot -Tpdf -o img/fase_recuperacion_rag.pdf diagrama_recuperacion.dot
```

---

## 📞 SOPORTE

Si encuentras problemas:
1. Verifica que PowerShell se ejecuta como Administrador
2. Ejecuta `.\install_tools.ps1` nuevamente
3. Prueba comandos manuales paso a paso
4. Verifica que los archivos fuente no tienen errores de sintaxis

**Nota**: Los diagramas incluyen todos los parámetros técnicos extraídos del código fuente real del sistema RAG. 