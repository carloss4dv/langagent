# Script de acceso rápido para instalar herramientas
Write-Host "=== INSTALADOR RÁPIDO DE HERRAMIENTAS ===" -ForegroundColor Green
Write-Host "Ejecutando el instalador principal..." -ForegroundColor Yellow

# Ejecutar el script principal de instalación
& "scripts/install_tools_simple.ps1"

Write-Host ""
Write-Host "=== PRÓXIMOS PASOS ===" -ForegroundColor Cyan
Write-Host "1. Reinicia PowerShell si es necesario" -ForegroundColor Yellow
Write-Host "2. Ejecuta ./generate.ps1 para generar diagramas" -ForegroundColor Yellow 