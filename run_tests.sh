#!/bin/bash
# Script para ejecutar tests y generar cobertura para SonarQube
# Con soporte para crear venv automáticamente

set -e

echo "================================"
echo "Coffee & Chill - Test Runner"
echo "================================"
echo ""

# Verificar si estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt no encontrado"
    echo "Ejecuta este script desde la carpeta CoffeeAndChill-Backend"
    exit 1
fi

# Crear venv si no existe
if [ ! -d "venv" ]; then
    echo "================================"
    echo "Creando entorno virtual..."
    echo "================================"
    python3 -m venv venv
fi

# Activar venv
echo "================================"
echo "Activando entorno virtual..."
echo "================================"
source venv/bin/activate

# Instalar/actualizar dependencias
echo "================================"
echo "Instalando dependencias..."
echo "================================"
pip install -q --upgrade pip setuptools
pip install -q -r requirements.txt

# Limpiar archivos previos
echo "================================"
echo "Limpiando archivos previos..."
echo "================================"
rm -f coverage.xml
rm -rf htmlcov/
rm -rf .coverage
rm -rf .pytest_cache/

echo ""
echo "================================"
echo "Ejecutando tests con pytest..."
echo "================================"
pytest -v --tb=short || true

echo ""
echo "================================"
echo "Generando reporte de cobertura..."
echo "================================"
coverage xml
coverage report --omit="*/tests/*" --precision=2

echo ""
echo "================================"
echo "Resultados:"
echo "================================"
if [ -f coverage.xml ]; then
    SIZE=$(du -h coverage.xml | cut -f1)
    echo "✅ coverage.xml - $SIZE"
fi
if [ -f htmlcov/index.html ]; then
    echo "✅ htmlcov/index.html generado"
fi

echo ""
echo "================================"
echo "Abrir reporte HTML:"
echo "================================"
echo "  open htmlcov/index.html  (macOS)"
echo "  xdg-open htmlcov/index.html  (Linux)"
echo "  start htmlcov/index.html  (Windows desde WSL)"
echo ""

echo "================================"
echo "✅ Completado!"
echo "================================"
