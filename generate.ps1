# Script de acceso rápido para generar diagramas
Write-Host "=== GENERADOR RÁPIDO DE DIAGRAMAS ===" -ForegroundColor Green
Write-Host "Ejecutando el generador principal..." -ForegroundColor Yellow

# Ejecutar el script principal
& "scripts/generate_simple.ps1"

Write-Host ""
Write-Host "=== COMANDOS ÚTILES ===" -ForegroundColor Cyan
Write-Host "Para instalar herramientas: scripts/install_tools_simple.ps1" -ForegroundColor Gray
Write-Host "Para generar diagramas: scripts/generate_simple.ps1" -ForegroundColor Gray
Write-Host "Para acceso rápido: ./generate.ps1" -ForegroundColor Gray 