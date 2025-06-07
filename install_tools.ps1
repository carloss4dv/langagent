# Script para instalar herramientas de diagramación en Windows
# Ejecutar como administrador: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

Write-Host "=== INSTALADOR DE HERRAMIENTAS PARA DIAGRAMAS ===" -ForegroundColor Green
Write-Host ""

# Verificar si Chocolatey está instalado
if (!(Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "Instalando Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Host "Chocolatey instalado correctamente" -ForegroundColor Green
} else {
    Write-Host "Chocolatey ya está instalado" -ForegroundColor Green
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
Write-Host "=== INSTALANDO JAVA (necesario para PlantUML) ===" -ForegroundColor Cyan
try {
    choco install openjdk11 -y
    Write-Host "Java instalado correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error instalando Java: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== DESCARGANDO PLANTUML ===" -ForegroundColor Cyan
$plantUMLUrl = "https://github.com/plantuml/plantuml/releases/latest/download/plantuml-1.2024.7.jar"
$plantUMLPath = ".\plantuml.jar"

try {
    if (!(Test-Path $plantUMLPath)) {
        Write-Host "Descargando PlantUML..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $plantUMLUrl -OutFile $plantUMLPath
        Write-Host "PlantUML descargado correctamente" -ForegroundColor Green
    } else {
        Write-Host "PlantUML ya existe en el directorio" -ForegroundColor Green
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
    Write-Host "✓ Graphviz: $dotVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Graphviz no encontrado" -ForegroundColor Red
    Write-Host "  Puede que necesites reiniciar PowerShell o añadir a PATH" -ForegroundColor Yellow
}

# Verificar Java
if (Get-Command java -ErrorAction SilentlyContinue) {
    $javaVersion = java -version 2>&1 | Select-Object -First 1
    Write-Host "✓ Java: $javaVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Java no encontrado" -ForegroundColor Red
}

# Verificar PlantUML
if (Test-Path $plantUMLPath) {
    Write-Host "✓ PlantUML: $plantUMLPath" -ForegroundColor Green
} else {
    Write-Host "✗ PlantUML no encontrado" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== INSTALACIÓN COMPLETADA ===" -ForegroundColor Green
Write-Host "Si hay errores, puede que necesites:" -ForegroundColor Yellow
Write-Host "1. Reiniciar PowerShell para actualizar PATH" -ForegroundColor Yellow
Write-Host "2. Ejecutar como administrador" -ForegroundColor Yellow
Write-Host "3. Instalar manualmente desde los sitios oficiales" -ForegroundColor Yellow
Write-Host ""
Write-Host "Sitios oficiales:" -ForegroundColor Cyan
Write-Host "- Graphviz: https://graphviz.org/download/" -ForegroundColor White
Write-Host "- PlantUML: https://plantuml.com/download" -ForegroundColor White
Write-Host "- Java: https://adoptium.net/" -ForegroundColor White 