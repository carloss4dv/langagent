# Script para generar diagramas en formato PNG
# Asegúrate de ejecutar install_tools.ps1 primero

param(
    [string]$OutputDir = "img",
    [int]$DPI = 300,
    [string]$PlantUMLJar = ".\plantuml.jar"
)

Write-Host "=== GENERADOR DE DIAGRAMAS RAG ===" -ForegroundColor Green
Write-Host ""

# Crear directorio de salida si no existe
if (!(Test-Path $OutputDir)) {
    Write-Host "Creando directorio: $OutputDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Función para verificar herramientas
function Test-Tool {
    param([string]$ToolName, [string]$Command)
    if (Get-Command $Command -ErrorAction SilentlyContinue) {
        Write-Host "✓ $ToolName disponible" -ForegroundColor Green
        return $true
    } else {
        Write-Host "✗ $ToolName no encontrado" -ForegroundColor Red
        return $false
    }
}

# Verificar herramientas
Write-Host "=== VERIFICANDO HERRAMIENTAS ===" -ForegroundColor Cyan
$graphvizOK = Test-Tool "Graphviz" "dot"
$javaOK = Test-Tool "Java" "java"
$plantUMLOK = Test-Path $PlantUMLJar

if ($plantUMLOK) {
    Write-Host "✓ PlantUML JAR encontrado: $PlantUMLJar" -ForegroundColor Green
} else {
    Write-Host "✗ PlantUML JAR no encontrado: $PlantUMLJar" -ForegroundColor Red
}

Write-Host ""

# Lista de archivos a procesar
$dotFiles = @(
    @{Name="Recuperación"; File="diagrama_recuperacion.dot"; Output="fase_recuperacion_rag.png"}
    @{Name="Generación"; File="diagrama_generacion.dot"; Output="fase_generacion_rag.png"}
)

$pumlFiles = @(
    @{Name="Recuperación PlantUML"; File="diagrama_recuperacion.puml"; Output="fase_recuperacion_rag_plantuml.png"}
)

# Procesar archivos DOT con Graphviz
if ($graphvizOK) {
    Write-Host "=== PROCESANDO ARCHIVOS DOT (GRAPHVIZ) ===" -ForegroundColor Cyan
    
    foreach ($file in $dotFiles) {
        $inputFile = $file.File
        $outputFile = Join-Path $OutputDir $file.Output
        
        if (Test-Path $inputFile) {
            Write-Host "Generando: $($file.Name)" -ForegroundColor Yellow
            Write-Host "  Input:  $inputFile" -ForegroundColor Gray
            Write-Host "  Output: $outputFile" -ForegroundColor Gray
            
            try {
                # Comando Graphviz con alta calidad
                $command = "dot -Tpng -Gdpi=$DPI -o `"$outputFile`" `"$inputFile`""
                Write-Host "  Ejecutando: $command" -ForegroundColor DarkGray
                
                Invoke-Expression $command
                
                if (Test-Path $outputFile) {
                    $fileSize = (Get-Item $outputFile).Length
                    Write-Host "  ✓ Generado correctamente ($([math]::Round($fileSize/1KB, 2)) KB)" -ForegroundColor Green
                } else {
                    Write-Host "  ✗ Error: archivo no generado" -ForegroundColor Red
                }
            } catch {
                Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "  ✗ Archivo no encontrado: $inputFile" -ForegroundColor Red
        }
        Write-Host ""
    }
} else {
    Write-Host "Saltando archivos DOT (Graphviz no disponible)" -ForegroundColor Yellow
}

# Procesar archivos PUML con PlantUML
if ($javaOK -and $plantUMLOK) {
    Write-Host "=== PROCESANDO ARCHIVOS PUML (PLANTUML) ===" -ForegroundColor Cyan
    
    foreach ($file in $pumlFiles) {
        $inputFile = $file.File
        $outputFile = Join-Path $OutputDir $file.Output
        
        if (Test-Path $inputFile) {
            Write-Host "Generando: $($file.Name)" -ForegroundColor Yellow
            Write-Host "  Input:  $inputFile" -ForegroundColor Gray
            Write-Host "  Output: $outputFile" -ForegroundColor Gray
            
            try {
                # Comando PlantUML
                $command = "java -jar `"$PlantUMLJar`" -tpng -o `"$OutputDir`" `"$inputFile`""
                Write-Host "  Ejecutando: $command" -ForegroundColor DarkGray
                
                Invoke-Expression $command
                
                # PlantUML genera con el mismo nombre pero extensión .png
                $generatedFile = $inputFile -replace '\.puml$', '.png'
                $generatedPath = Join-Path $OutputDir (Split-Path $generatedFile -Leaf)
                
                if (Test-Path $generatedPath) {
                    # Renombrar si es necesario
                    if ($generatedPath -ne $outputFile) {
                        Move-Item $generatedPath $outputFile -Force
                    }
                    
                    $fileSize = (Get-Item $outputFile).Length
                    Write-Host "  ✓ Generado correctamente ($([math]::Round($fileSize/1KB, 2)) KB)" -ForegroundColor Green
                } else {
                    Write-Host "  ✗ Error: archivo no generado" -ForegroundColor Red
                }
            } catch {
                Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "  ✗ Archivo no encontrado: $inputFile" -ForegroundColor Red
        }
        Write-Host ""
    }
} else {
    Write-Host "Saltando archivos PUML (Java o PlantUML no disponibles)" -ForegroundColor Yellow
}

# Resumen final
Write-Host "=== RESUMEN ===" -ForegroundColor Green
$generatedFiles = Get-ChildItem -Path $OutputDir -Filter "*.png" -ErrorAction SilentlyContinue

if ($generatedFiles) {
    Write-Host "Archivos generados en '$OutputDir':" -ForegroundColor Green
    foreach ($file in $generatedFiles) {
        $size = [math]::Round($file.Length/1KB, 2)
        Write-Host "  • $($file.Name) ($size KB)" -ForegroundColor White
    }
} else {
    Write-Host "No se generaron archivos PNG" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== COMANDOS MANUALES DE RESPALDO ===" -ForegroundColor Cyan
Write-Host "Si el script falla, puedes ejecutar manualmente:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Para Graphviz (.dot):" -ForegroundColor White
Write-Host '  dot -Tpng -Gdpi=300 -o "img\fase_recuperacion_rag.png" "diagrama_recuperacion.dot"' -ForegroundColor Gray
Write-Host '  dot -Tpng -Gdpi=300 -o "img\fase_generacion_rag.png" "diagrama_generacion.dot"' -ForegroundColor Gray
Write-Host ""
Write-Host "Para PlantUML (.puml):" -ForegroundColor White
Write-Host '  java -jar plantuml.jar -tpng -o "img" "diagrama_recuperacion.puml"' -ForegroundColor Gray
Write-Host ""
Write-Host "Parámetros de calidad adicionales:" -ForegroundColor White
Write-Host "  -Gdpi=600     # Mayor resolución" -ForegroundColor Gray
Write-Host "  -Gsize=20,15  # Tamaño específico en pulgadas" -ForegroundColor Gray 