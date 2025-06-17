# Script PowerShell para quitar tildes de diagramas PlantUML
# Autor: Script generado automáticamente

param(
    [string]$Action = "process",
    [string]$DiagramsDir = "diagrams",
    [switch]$NoBackup,
    [switch]$Restore,
    [switch]$Help
)

function Show-Help {
    Write-Host "=== Script para quitar tildes de diagramas PlantUML ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USO:" -ForegroundColor Yellow
    Write-Host "  .\remove_accents_diagrams.ps1                    # Procesar con backup"
    Write-Host "  .\remove_accents_diagrams.ps1 -NoBackup         # Procesar sin backup"
    Write-Host "  .\remove_accents_diagrams.ps1 -Restore          # Restaurar desde backup"
    Write-Host "  .\remove_accents_diagrams.ps1 -DiagramsDir 'mi_directorio'"
    Write-Host "  .\remove_accents_diagrams.ps1 -Help             # Mostrar esta ayuda"
    Write-Host ""
    Write-Host "PARÁMETROS:" -ForegroundColor Yellow
    Write-Host "  -DiagramsDir   Directorio con archivos .puml (por defecto: 'diagrams')"
    Write-Host "  -NoBackup      No crear archivos de backup"
    Write-Host "  -Restore       Restaurar archivos desde backup"
    Write-Host "  -Help          Mostrar esta ayuda"
    Write-Host ""
}

function Test-PythonAvailable {
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Python encontrado: $pythonVersion" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "❌ Python no está disponible" -ForegroundColor Red
        Write-Host "   Por favor instale Python desde https://python.org" -ForegroundColor Yellow
        return $false
    }
    return $false
}

function Invoke-RemoveAccents {
    param(
        [string]$Directory,
        [bool]$CreateBackup,
        [bool]$RestoreMode
    )
    
    Write-Host "=== Procesamiento de diagramas PlantUML ===" -ForegroundColor Cyan
    Write-Host "Directorio: $Directory" -ForegroundColor White
    
    # Verificar que Python esté disponible
    if (-not (Test-PythonAvailable)) {
        return
    }
    
    # Verificar que el script Python existe
    $pythonScript = "remove_accents_diagrams.py"
    if (-not (Test-Path $pythonScript)) {
        Write-Host "❌ No se encontró el script: $pythonScript" -ForegroundColor Red
        Write-Host "   Asegúrese de que el archivo está en el directorio actual" -ForegroundColor Yellow
        return
    }
    
    # Construir argumentos para el script Python
    $pythonArgs = @("--dir", $Directory)
    
    if (-not $CreateBackup) {
        $pythonArgs += "--no-backup"
    }
    
    if ($RestoreMode) {
        $pythonArgs += "--restore"
    }
    
    # Ejecutar el script Python
    Write-Host "Ejecutando: python $pythonScript $($pythonArgs -join ' ')" -ForegroundColor Gray
    Write-Host ""
    
    try {
        & python $pythonScript @pythonArgs
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✅ Proceso completado exitosamente!" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "❌ El proceso terminó con errores" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "❌ Error ejecutando el script Python: $_" -ForegroundColor Red
    }
}

# Main script logic
if ($Help) {
    Show-Help
    exit 0
}

# Verificar que el directorio existe
if (-not (Test-Path $DiagramsDir)) {
    Write-Host "❌ El directorio '$DiagramsDir' no existe" -ForegroundColor Red
    Write-Host "   Use -DiagramsDir para especificar la ruta correcta" -ForegroundColor Yellow
    exit 1
}

# Ejecutar la acción solicitada
$createBackup = -not $NoBackup
Invoke-RemoveAccents -Directory $DiagramsDir -CreateBackup $createBackup -RestoreMode $Restore

Write-Host ""
Write-Host "Para más información, use: .\remove_accents_diagrams.ps1 -Help" -ForegroundColor Gray
