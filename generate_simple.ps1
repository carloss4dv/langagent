# Script simplificado para generar diagramas PNG
Write-Host "=== GENERADOR DE DIAGRAMAS RAG ===" -ForegroundColor Green

# Crear directorio img si no existe
if (!(Test-Path "img")) {
    Write-Host "Creando directorio img..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "img" -Force | Out-Null
}

# Verificar herramientas
Write-Host "=== VERIFICANDO HERRAMIENTAS ===" -ForegroundColor Cyan

$graphvizOK = $false
if (Get-Command dot -ErrorAction SilentlyContinue) {
    Write-Host "OK Graphviz encontrado" -ForegroundColor Green
    $graphvizOK = $true
} else {
    Write-Host "ERROR Graphviz no encontrado" -ForegroundColor Red
}

$javaOK = $false
if (Get-Command java -ErrorAction SilentlyContinue) {
    Write-Host "OK Java encontrado" -ForegroundColor Green
    $javaOK = $true
} else {
    Write-Host "ERROR Java no encontrado" -ForegroundColor Red
}

$plantUMLOK = $false
if (Test-Path "plantuml.jar") {
    Write-Host "OK PlantUML encontrado" -ForegroundColor Green
    $plantUMLOK = $true
} else {
    Write-Host "ERROR PlantUML no encontrado" -ForegroundColor Red
}

Write-Host ""

# Generar diagramas con Graphviz
if ($graphvizOK) {
    Write-Host "=== GENERANDO CON GRAPHVIZ ===" -ForegroundColor Cyan
    
    # Diagrama 1: Recuperacion
    if (Test-Path "diagrama_recuperacion.dot") {
        Write-Host "Generando fase_recuperacion_rag.png..." -ForegroundColor Yellow
        try {
            dot -Tpng -Gdpi=300 -o "img/fase_recuperacion_rag.png" "diagrama_recuperacion.dot"
            if (Test-Path "img/fase_recuperacion_rag.png") {
                Write-Host "OK Recuperacion generado" -ForegroundColor Green
            } else {
                Write-Host "ERROR al generar recuperacion" -ForegroundColor Red
            }
        } catch {
            Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "ERROR: diagrama_recuperacion.dot no encontrado" -ForegroundColor Red
    }
    
    # Diagrama 2: Generacion
    if (Test-Path "diagrama_generacion.dot") {
        Write-Host "Generando fase_generacion_rag.png..." -ForegroundColor Yellow
        try {
            dot -Tpng -Gdpi=300 -o "img/fase_generacion_rag.png" "diagrama_generacion.dot"
            if (Test-Path "img/fase_generacion_rag.png") {
                Write-Host "OK Generacion generado" -ForegroundColor Green
            } else {
                Write-Host "ERROR al generar generacion" -ForegroundColor Red
            }
        } catch {
            Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "ERROR: diagrama_generacion.dot no encontrado" -ForegroundColor Red
    }
} else {
    Write-Host "Saltando Graphviz (no disponible)" -ForegroundColor Yellow
}

# Generar diagramas con PlantUML
if ($javaOK -and $plantUMLOK) {
    Write-Host "=== GENERANDO CON PLANTUML ===" -ForegroundColor Cyan
    
    if (Test-Path "diagrama_recuperacion.puml") {
        Write-Host "Generando diagrama PlantUML..." -ForegroundColor Yellow
        try {
            java -jar plantuml.jar -tpng -o "img" "diagrama_recuperacion.puml"
            Write-Host "OK PlantUML generado" -ForegroundColor Green
        } catch {
            Write-Host "ERROR PlantUML: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "ERROR: diagrama_recuperacion.puml no encontrado" -ForegroundColor Red
    }
} else {
    Write-Host "Saltando PlantUML (Java o JAR no disponible)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== RESUMEN ===" -ForegroundColor Green

$pngFiles = Get-ChildItem -Path "img" -Filter "*.png" -ErrorAction SilentlyContinue
if ($pngFiles) {
    Write-Host "Archivos generados en img/:" -ForegroundColor Green
    foreach ($file in $pngFiles) {
        Write-Host "  - $($file.Name)" -ForegroundColor White
    }
} else {
    Write-Host "No se generaron archivos PNG" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== COMANDOS MANUALES ===" -ForegroundColor Cyan
Write-Host "Si prefieres ejecutar manualmente:" -ForegroundColor Yellow
Write-Host 'dot -Tpng -Gdpi=300 -o "img/fase_recuperacion_rag.png" "diagrama_recuperacion.dot"' -ForegroundColor Gray
Write-Host 'dot -Tpng -Gdpi=300 -o "img/fase_generacion_rag.png" "diagrama_generacion.dot"' -ForegroundColor Gray
Write-Host 'java -jar plantuml.jar -tpng -o "img" "diagrama_recuperacion.puml"' -ForegroundColor Gray 