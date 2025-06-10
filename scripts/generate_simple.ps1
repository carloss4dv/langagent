# Script simplificado para generar diagramas PNG
Write-Host "=== GENERADOR DE DIAGRAMAS RAG ===" -ForegroundColor Green

# Cambiar al directorio raíz del proyecto
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
Set-Location $rootDir

Write-Host "Directorio de trabajo: $rootDir" -ForegroundColor Yellow

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
$plantUMLPath = "tools/plantuml.jar"
if (Test-Path $plantUMLPath) {
    Write-Host "OK PlantUML encontrado en $plantUMLPath" -ForegroundColor Green
    $plantUMLOK = $true
} else {
    Write-Host "ERROR PlantUML no encontrado en $plantUMLPath" -ForegroundColor Red
}

Write-Host ""

# Generar diagramas con Graphviz
if ($graphvizOK) {
    Write-Host "=== GENERANDO CON GRAPHVIZ ===" -ForegroundColor Cyan
    
    # Buscar todos los archivos .dot en el directorio diagrams
    $dotFiles = Get-ChildItem -Path "diagrams" -Filter "*.dot" -ErrorAction SilentlyContinue
    
    if ($dotFiles) {
        foreach ($dotFile in $dotFiles) {
            $baseName = [System.IO.Path]::GetFileNameWithoutExtension($dotFile.Name)
            $outputFile = "img/$baseName.png"
            
            Write-Host "Generando $outputFile desde $($dotFile.Name)..." -ForegroundColor Yellow
            try {
                dot -Tpng -Gdpi=300 -o $outputFile $dotFile.FullName
                if (Test-Path $outputFile) {
                    Write-Host "OK $baseName generado" -ForegroundColor Green
                } else {
                    Write-Host "ERROR al generar $baseName" -ForegroundColor Red
                }
            } catch {
                Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "No se encontraron archivos .dot en el directorio diagrams" -ForegroundColor Yellow
    }
} else {
    Write-Host "Saltando Graphviz (no disponible)" -ForegroundColor Yellow
}

# Generar diagramas con PlantUML
if ($javaOK -and $plantUMLOK) {
    Write-Host "=== GENERANDO CON PLANTUML ===" -ForegroundColor Cyan
    
    # Buscar todos los archivos .puml en el directorio diagrams
    $pumlFiles = Get-ChildItem -Path "diagrams" -Filter "*.puml" -ErrorAction SilentlyContinue
    
    if ($pumlFiles) {
        Write-Host "Encontrados $($pumlFiles.Count) archivos .puml:" -ForegroundColor Yellow
        foreach ($pumlFile in $pumlFiles) {
            Write-Host "  - $($pumlFile.Name)" -ForegroundColor Gray
        }
        
        Write-Host "Generando diagramas PlantUML..." -ForegroundColor Yellow
        try {
            # Generar todos los archivos .puml del directorio diagrams
            java -jar $plantUMLPath -tpng -o "../img" "diagrams/*.puml"
            Write-Host "OK Todos los diagramas PlantUML generados" -ForegroundColor Green
        } catch {
            Write-Host "ERROR PlantUML: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "No se encontraron archivos .puml en el directorio diagrams" -ForegroundColor Yellow
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
        $fileSize = [math]::Round($file.Length / 1KB, 1)
        Write-Host "  - $($file.Name) ($fileSize KB)" -ForegroundColor White
    }
} else {
    Write-Host "No se generaron archivos PNG" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== COMANDOS MANUALES ===" -ForegroundColor Cyan
Write-Host "Si prefieres ejecutar manualmente desde el directorio raíz:" -ForegroundColor Yellow
Write-Host 'dot -Tpng -Gdpi=300 -o "img/nombre_diagrama.png" "diagrams/archivo.dot"' -ForegroundColor Gray
Write-Host "java -jar tools/plantuml.jar -tpng -o img diagrams/*.puml" -ForegroundColor Gray

Write-Host ""
Write-Host "=== ESTRUCTURA DE DIRECTORIOS ===" -ForegroundColor Cyan
Write-Host "diagrams/     - Archivos fuente de diagramas (.puml, .dot, .md)" -ForegroundColor Gray
Write-Host "img/          - Imágenes generadas (.png)" -ForegroundColor Gray
Write-Host "scripts/      - Scripts de PowerShell" -ForegroundColor Gray
Write-Host "tools/        - Herramientas (plantuml.jar)" -ForegroundColor Gray 