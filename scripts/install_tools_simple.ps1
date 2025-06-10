# Script simplificado para instalar herramientas de diagramacion
Write-Host "=== INSTALADOR DE HERRAMIENTAS PARA DIAGRAMAS ===" -ForegroundColor Green

# Cambiar al directorio raíz del proyecto
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir
Set-Location $rootDir

Write-Host "Directorio de trabajo: $rootDir" -ForegroundColor Yellow

# Crear directorio tools si no existe
if (!(Test-Path "tools")) {
    Write-Host "Creando directorio tools..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "tools" -Force | Out-Null
}

# Verificar si Chocolatey esta instalado
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Host "Chocolatey instalado correctamente" -ForegroundColor Green
} else {
    Write-Host "Chocolatey ya esta instalado" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== INSTALANDO GRAPHVIZ ===" -ForegroundColor Cyan
try {
    choco install graphviz -y
    Write-Host "Graphviz instalado correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error instalando Graphviz: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== INSTALANDO JAVA ===" -ForegroundColor Cyan
try {
    choco install openjdk11 -y
    Write-Host "Java instalado correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error instalando Java: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== DESCARGANDO PLANTUML ===" -ForegroundColor Cyan
$plantUMLUrl = "https://github.com/plantuml/plantuml/releases/latest/download/plantuml-1.2024.7.jar"
$plantUMLPath = "tools/plantuml.jar"

try {
    if (!(Test-Path $plantUMLPath)) {
        Write-Host "Descargando PlantUML a $plantUMLPath..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $plantUMLUrl -OutFile $plantUMLPath
        Write-Host "PlantUML descargado correctamente" -ForegroundColor Green
    } else {
        Write-Host "PlantUML ya existe en $plantUMLPath" -ForegroundColor Green
    }
} catch {
    Write-Host "Error descargando PlantUML: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Descarga manual desde: https://plantuml.com/download" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== VERIFICANDO INSTALACIONES ===" -ForegroundColor Cyan

# Verificar Graphviz
if (Get-Command dot -ErrorAction SilentlyContinue) {
    $dotVersion = dot -V 2>&1
    Write-Host "OK Graphviz: $dotVersion" -ForegroundColor Green
} else {
    Write-Host "ERROR Graphviz no encontrado" -ForegroundColor Red
    Write-Host "Puede que necesites reiniciar PowerShell" -ForegroundColor Yellow
}

# Verificar Java
if (Get-Command java -ErrorAction SilentlyContinue) {
    $javaVersion = java -version 2>&1 | Select-Object -First 1
    Write-Host "OK Java: $javaVersion" -ForegroundColor Green
} else {
    Write-Host "ERROR Java no encontrado" -ForegroundColor Red
}

# Verificar PlantUML
if (Test-Path $plantUMLPath) {
    $plantUMLSize = [math]::Round((Get-Item $plantUMLPath).Length / 1MB, 1)
    Write-Host "OK PlantUML: $plantUMLPath ($plantUMLSize MB)" -ForegroundColor Green
} else {
    Write-Host "ERROR PlantUML no encontrado en $plantUMLPath" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== INSTALACION COMPLETADA ===" -ForegroundColor Green
Write-Host "Si hay errores, puede que necesites reiniciar PowerShell" -ForegroundColor Yellow
Write-Host ""
Write-Host "=== ESTRUCTURA CREADA ===" -ForegroundColor Cyan
Write-Host "tools/plantuml.jar - Herramienta PlantUML" -ForegroundColor Gray
Write-Host "Para generar diagramas ejecuta: ./generate.ps1" -ForegroundColor Yellow 