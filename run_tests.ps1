# Script de PowerShell para ejecutar tests y generar cobertura
# Uso: powershell -ExecutionPolicy Bypass -File run_tests.ps1

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Coffee & Chill - Test Runner" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Verificar requisitos
if (-not (Test-Path "requirements.txt")) {
    Write-Host "❌ Error: requirements.txt no encontrado" -ForegroundColor Red
    Write-Host "Ejecuta este script desde la carpeta CoffeeAndChill-Backend" -ForegroundColor Red
    exit 1
}

# Crear venv si no existe
if (-not (Test-Path "venv")) {
    Write-Host "================================" -ForegroundColor Yellow
    Write-Host "Creando entorno virtual..." -ForegroundColor Yellow
    Write-Host "================================" -ForegroundColor Yellow
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error al crear venv" -ForegroundColor Red
        exit 1
    }
}

# Activar venv
Write-Host "================================" -ForegroundColor Yellow
Write-Host "Activando entorno virtual..." -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Instalar dependencias
Write-Host "================================" -ForegroundColor Yellow
Write-Host "Instalando dependencias..." -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow
& pip install -q --upgrade pip setuptools
& pip install -q -r requirements.txt

# Limpiar cachés previos
Write-Host "================================" -ForegroundColor Yellow
Write-Host "Limpiando archivos previos..." -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Yellow
Remove-Item -Force -Path "coverage.xml" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -Path "htmlcov" -ErrorAction SilentlyContinue
Remove-Item -Force -Path ".coverage" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force -Path ".pytest_cache" -ErrorAction SilentlyContinue

# Ejecutar tests
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Ejecutando tests con pytest..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
& pytest -v --tb=short
$testStatus = $LASTEXITCODE

# Generar cobertura
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Generando reporte de cobertura..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
& coverage xml
& coverage report --omit="*/tests/*" --precision=2

# Mostrar resultados
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Resultados:" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

if (Test-Path "coverage.xml") {
    $size = (Get-Item "coverage.xml").Length
    Write-Host "✅ coverage.xml - $size bytes" -ForegroundColor Green
}
if (Test-Path "htmlcov\index.html") {
    Write-Host "✅ htmlcov\index.html generado" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Abrir reporte HTML:" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  htmlcov\index.html" -ForegroundColor Yellow
Write-Host ""

# Ofrecer abrir el reporte
if (Test-Path "htmlcov\index.html") {
    $open = Read-Host "¿Abrir reporte HTML? (s/n)"
    if ($open -eq "s" -or $open -eq "S") {
        Start-Process "htmlcov\index.html"
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "✅ Completado!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

exit $testStatus
