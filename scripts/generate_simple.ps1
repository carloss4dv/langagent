# Script para generar diagramas en formato SVG desde archivos PlantUML

param(
    [string]$InputDir = "diagrams",
    [string]$OutputDir = "img/svg",
    [string]$PlantUMLJar = "./tools/plantuml.jar"
)

Write-Host "=== GENERADOR DE DIAGRAMAS SVG (SIMPLE) ====" -ForegroundColor Green
Write-Host ""

# Crear directorio de salida si no existe
if (!(Test-Path $OutputDir)) {
    Write-Host "Creando directorio: $OutputDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Verificar herramientas
Write-Host "=== VERIFICANDO HERRAMIENTAS ====" -ForegroundColor Cyan
$javaOK = Get-Command java -ErrorAction SilentlyContinue
$plantUMLOK = Test-Path $PlantUMLJar

if ($javaOK) {
    Write-Host "[OK] Java disponible" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Java no encontrado. Asegurate de que este en el PATH." -ForegroundColor Red
}

if ($plantUMLOK) {
    Write-Host "[OK] PlantUML JAR encontrado: $PlantUMLJar" -ForegroundColor Green
} else {
    Write-Host "[ERROR] PlantUML JAR no encontrado en la raiz del proyecto." -ForegroundColor Red
    Write-Host "  Puedes descargarlo desde https://plantuml.com/download"
}
Write-Host ""

if (-not ($javaOK -and $plantUMLOK)) {
    Write-Host "Faltan herramientas necesarias. Abortando." -ForegroundColor Red
    exit 1
}

# Obtener lista de archivos .puml
$pumlFiles = Get-ChildItem -Path $InputDir -Filter *.puml

if ($pumlFiles.Count -eq 0) {
    Write-Host "No se encontraron archivos .puml en el directorio '$InputDir'" -ForegroundColor Yellow
    exit
}

Write-Host "=== PROCESANDO ARCHIVOS PUML (PLANTUML) ====" -ForegroundColor Cyan
Write-Host "Se encontraron $($pumlFiles.Count) archivos para procesar."
Write-Host ""

foreach ($file in $pumlFiles) {
    $inputFile = $file.FullName
    $outputFileName = $file.BaseName + ".svg"
    $outputFilePath = Join-Path $OutputDir $outputFileName

    Write-Host "Generando: $($file.Name)" -ForegroundColor Yellow
    Write-Host "  Input:  $inputFile" -ForegroundColor Gray
    Write-Host "  Output: $outputFilePath" -ForegroundColor Gray

    try {
        # Usar .NET Process para un control más robusto de la salida
        $pinfo = New-Object System.Diagnostics.ProcessStartInfo
        $pinfo.FileName = "java"
        $pinfo.RedirectStandardError = $true
        $pinfo.RedirectStandardOutput = $true
        $pinfo.UseShellExecute = $false
        $pinfo.CreateNoWindow = $true # Ocultar la ventana de la consola
        $pinfo.Arguments = "-jar `"$PlantUMLJar`" -tsvg -verbose `"$inputFile`" -o `"$OutputDir`""
        
        Write-Host "  Ejecutando: $($pinfo.FileName) $($pinfo.Arguments)" -ForegroundColor DarkGray

        $p = New-Object System.Diagnostics.Process
        $p.StartInfo = $pinfo
        $p.Start() | Out-Null
          # Aplicar un timeout de 60 segundos
        $timeoutReached = $false
        if (-not $p.WaitForExit(60000)) {
            Write-Host "  [WARNING] Timeout alcanzado (60s). Terminando proceso..." -ForegroundColor Yellow
            $p.Kill()
            $timeoutReached = $true
        }

        $plantUMLOutput = ""
        $plantUMLError = ""
        $fullOutput = ""
        
        if (-not $timeoutReached) {
            try {
                $plantUMLOutput = $p.StandardOutput.ReadToEnd()
                $plantUMLError = $p.StandardError.ReadToEnd()
                $fullOutput = $plantUMLOutput + $plantUMLError
            } catch {
                Write-Host "  [WARNING] Error al leer la salida del proceso: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }

        # Analizar la salida para encontrar el archivo que PlantUML realmente creó
        $createdFilePath = $null
        if ($fullOutput -match "Creating file: (.*)") {
            $createdFilePath = $matches[1].Trim()
        }        if ($timeoutReached) {
            Write-Host "  [ERROR] Proceso terminado por timeout. Saltando al siguiente archivo." -ForegroundColor Red
            continue
        } elseif ($createdFilePath -and (Test-Path $createdFilePath)) {
             $fileSize = (Get-Item $createdFilePath).Length
             Write-Host "  [OK] Generado correctamente: $createdFilePath ($([math]::Round($fileSize/1024, 2)) KB)" -ForegroundColor Green
        } else {
            # Intentar encontrar el archivo por nombre si el regex falló
            $expectedSVGPath = Join-Path $OutputDir ($file.BaseName + ".svg")
            if (Test-Path $expectedSVGPath) {
                $fileSize = (Get-Item $expectedSVGPath).Length
                Write-Host "  [OK] Generado correctamente: $expectedSVGPath ($([math]::Round($fileSize/1024, 2)) KB)" -ForegroundColor Green
            } else {
                Write-Host "  [ERROR] Error: PlantUML finalizó pero no se encontró el archivo de salida." -ForegroundColor Red
                if (-not [string]::IsNullOrWhiteSpace($fullOutput)) {
                    Write-Host "--- Salida de PlantUML ---" -ForegroundColor DarkGray
                    Write-Host $fullOutput -ForegroundColor DarkGray
                    Write-Host "--------------------------" -ForegroundColor DarkGray
                }
                Write-Host "Continuando con el siguiente archivo..." -ForegroundColor Yellow
                continue
            }
        }
    } catch {
        Write-Host "  [ERROR] Error al ejecutar el proceso: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Continuando con el siguiente archivo..." -ForegroundColor Yellow
        continue
    }
    Write-Host ""
}

Write-Host "=== PROCESO COMPLETADO ====" -ForegroundColor Green
