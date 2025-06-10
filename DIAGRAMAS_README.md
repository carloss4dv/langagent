# 📊 Generador de Diagramas RAG

Sistema organizado para generar diagramas de arquitecturas RAG utilizando Graphviz y PlantUML.

## 🏗️ Estructura de Directorios

```
.
├── diagrams/           # 📁 Archivos fuente de diagramas
│   ├── *.puml         # Diagramas PlantUML
│   ├── *.dot          # Diagramas Graphviz
│   └── *.md           # Diagramas Mermaid
├── img/               # 🖼️ Imágenes generadas (.png)
├── scripts/           # 🔧 Scripts de PowerShell
│   ├── generate_simple.ps1      # Generador principal
│   ├── install_tools_simple.ps1 # Instalador de herramientas
│   ├── generate_diagrams.ps1    # Generador avanzado
│   └── install_tools.ps1        # Instalador avanzado
├── tools/             # 🛠️ Herramientas
│   └── plantuml.jar   # PlantUML JAR
├── generate.ps1       # 🚀 Acceso rápido al generador
└── install.ps1        # 🚀 Acceso rápido al instalador
```

## 🚀 Uso Rápido

### 1. Instalar Herramientas
```powershell
./install.ps1
```

### 2. Generar Diagramas
```powershell
./generate.ps1
```

## 📋 Herramientas Requeridas

- **Graphviz**: Para diagramas .dot
- **Java**: Para ejecutar PlantUML
- **PlantUML**: Para diagramas .puml

## 📊 Tipos de Diagramas Soportados

### PlantUML (.puml)
- `adaptive_rag.puml` - Diagrama RAG Adaptativo
- `crag.puml` - Diagrama CRAG
- `naive_rag.puml` - Diagrama RAG Naive
- `rag_triad.puml` - Tríada RAG
- `diagrama_recuperacion.puml` - Fase de Recuperación
- `diagrama_generacion.puml` - Fase de Generación
- `recuperacion_rag.puml` - Recuperación RAG
- `generacion_rag.puml` - Generación RAG

### Graphviz (.dot)
- `diagrama_recuperacion.dot` - Recuperación detallada
- `diagrama_generacion.dot` - Generación detallada

### Mermaid (.md)
- `recuperacion_mermaid.md` - Diagrama de recuperación
- `generacion_mermaid.md` - Diagrama de generación

## 🔧 Comandos Manuales

### Graphviz
```powershell
dot -Tpng -Gdpi=300 -o "img/nombre_diagrama.png" "diagrams/archivo.dot"
```

### PlantUML
```powershell
java -jar tools/plantuml.jar -tpng -o img diagrams/*.puml
```

## 📈 Características

- ✅ Procesamiento automático de todos los archivos .puml
- ✅ Procesamiento automático de todos los archivos .dot
- ✅ Estructura organizada de directorios
- ✅ Scripts de acceso rápido
- ✅ Verificación de herramientas
- ✅ Información detallada de archivos generados
- ✅ Comandos manuales de respaldo

## 🐛 Solución de Problemas

### Error "Java no encontrado"
1. Ejecuta `./install.ps1`
2. Reinicia PowerShell
3. Verifica con `java -version`

### Error "Graphviz no encontrado"
1. Ejecuta `./install.ps1`
2. Reinicia PowerShell
3. Verifica con `dot -V`

### Error "PlantUML no encontrado"
1. Verifica que existe `tools/plantuml.jar`
2. Si no existe, ejecuta `./install.ps1`

## 📝 Notas

- Los archivos PNG se generan en el directorio `img/`
- El script detecta automáticamente todos los archivos de diagramas
- Se muestran los tamaños de los archivos generados
- La estructura está optimizada para facilitar el mantenimiento 