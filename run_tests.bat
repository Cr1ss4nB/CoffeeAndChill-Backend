@echo off
REM Script para ejecutar tests y generar cobertura para SonarQube
REM Con soporte para crear venv automáticamente

setlocal enabledelayedexpansion

echo ================================
echo Coffee & Chill - Test Runner
echo ================================
echo.

REM Verificar si estamos en el directorio correcto
if not exist "requirements.txt" (
    echo Error: requirements.txt no encontrado
    echo Ejecuta este script desde la carpeta CoffeeAndChill-Backend
    pause
    exit /b 1
)

REM Crear venv si no existe
if not exist "venv" (
    echo ================================
    echo Creando entorno virtual...
    echo ================================
    python -m venv venv
    if errorlevel 1 (
        echo Error al crear venv
        pause
        exit /b 1
    )
)

REM Activar venv
echo ================================
echo Activando entorno virtual...
echo ================================
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error al activar venv
    pause
    exit /b 1
)

REM Instalar/actualizar dependencias
echo ================================
echo Instalando dependencias...
echo ================================
pip install -q --upgrade pip setuptools
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Error al instalar dependencias
    pause
    exit /b 1
)

REM Limpiar archivos previos
echo ================================
echo Limpiando archivos previos...
echo ================================
if exist coverage.xml del coverage.xml
if exist htmlcov rmdir /s /q htmlcov 2>nul
if exist .coverage del .coverage
if exist .pytest_cache rmdir /s /q .pytest_cache 2>nul

REM Ejecutar tests
echo.
echo ================================
echo Ejecutando tests con pytest...
echo ================================
pytest -v --tb=short
if errorlevel 1 (
    echo.
    echo ⚠️  Algunos tests fallaron - verificando cobertura de todas formas
    REM No salimos, seguimos para generar coverage
)

REM Generar cobertura XML
echo.
echo ================================
echo Generando reporte de cobertura...
echo ================================
coverage xml
coverage report --omit="*/tests/*" --precision=2

REM Mostrar resultados
echo.
echo ================================
echo Resultados:
echo ================================
if exist coverage.xml (
    for %%A in (coverage.xml) do (
        echo [OK] coverage.xml - %%~zA bytes
    )
)
if exist htmlcov\index.html (
    echo [OK] htmlcov\index.html generado
)

echo.
echo ================================
echo Abrir reporte HTML:
echo ================================
echo   htmlcov\index.html
echo.

REM Ofrecer abrir el reporte
if exist htmlcov\index.html (
    set /p OPEN_REPORT="¿Abrir reporte HTML? (s/n): "
    if /i "!OPEN_REPORT!"=="s" (
        start htmlcov\index.html
    )
)

echo.
echo ================================
echo ✅ Completado!
echo ================================
pause
