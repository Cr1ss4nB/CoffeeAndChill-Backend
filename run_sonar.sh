#!/bin/bash
# Script para ejecutar tests, generar cobertura y enviar a SonarQube

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📦 Iniciando proceso de análisis y cobertura..."
echo "   Directorio: $SCRIPT_DIR"

# Cambiar al directorio del backend
cd "$SCRIPT_DIR"

# Ejecutar tests y generar cobertura
echo ""
echo "================================"
echo "1️⃣  Ejecutando tests..."
echo "================================"
pytest -v --tb=short

echo ""
echo "================================"
echo "2️⃣  Generando cobertura XML..."
echo "================================"
coverage xml
coverage report --omit="*/tests/*" --precision=2

# Verificar que coverage.xml se generó
if [ ! -f coverage.xml ]; then
    echo "❌ Error: coverage.xml no fue generado"
    exit 1
fi

echo ""
echo "✅ Archivos generados:"
ls -lh coverage.xml

echo ""
echo "================================"
echo "3️⃣  Enviando a SonarQube..."
echo "================================"

# Ejecutar SonarQube Scanner
docker run --rm \
  -v "${PWD}:/usr/src" \
  -e SONAR_HOST_URL="http://host.docker.internal:9000" \
  -e SONAR_LOGIN="squ_d6c7176ec8a1ee14adfbe13e5658db3bab08ec1b" \
  sonarsource/sonar-scanner-cli \
  -Dsonar.projectBaseDir=/usr/src \
  -Dsonar.python.coverage.reportPaths=/usr/src/coverage.xml

echo ""
echo "================================"
echo "✅ Análisis completado!"
echo "================================"
