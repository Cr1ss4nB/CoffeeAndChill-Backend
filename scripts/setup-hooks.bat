@echo off
REM Setup pre-commit hooks para Windows

setlocal enabledelayedexpansion

echo ==========================================
echo Instalando pre-commit hooks...
echo ==========================================

REM Verificar si pip está instalado
pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ❌ pip no está instalado. Instálalo primero.
    exit /b 1
)

REM Instalar pre-commit
echo 📦 Instalando pre-commit...
pip install pre-commit

REM Instalar los hooks
echo 🔗 Configurando hooks...
pre-commit install
pre-commit install --hook-type pre-push

REM Información adicional
echo.
echo ✅ Pre-commit hooks instalados correctamente
echo.
echo ==========================================
echo Próximos pasos:
echo ==========================================
echo 1. Los hooks se ejecutarán automáticamente en cada commit
echo 2. Para ejecutar todos los checks manualmente:
echo    pre-commit run --all-files
echo 3. Para saltarse los hooks temporalmente:
echo    git commit --no-verify
echo.
