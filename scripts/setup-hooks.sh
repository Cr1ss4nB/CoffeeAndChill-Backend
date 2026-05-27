#!/bin/bash
# Setup pre-commit hooks para Linux/macOS

set -e

echo "=========================================="
echo "Instalando pre-commit hooks..."
echo "=========================================="

# Verificar si pip está instalado
if ! command -v pip &> /dev/null; then
    echo "❌ pip no está instalado. Instálalo primero."
    exit 1
fi

# Instalar pre-commit
echo "📦 Instalando pre-commit..."
pip install pre-commit

# Instalar los hooks
echo "🔗 Configurando hooks..."
pre-commit install
pre-commit install --hook-type pre-push

# Información adicional
echo ""
echo "✅ Pre-commit hooks instalados correctamente"
echo ""
echo "=========================================="
echo "Próximos pasos:"
echo "=========================================="
echo "1. Los hooks se ejecutarán automáticamente en cada commit"
echo "2. Para ejecutar todos los checks manualmente:"
echo "   pre-commit run --all-files"
echo "3. Para saltarse los hooks temporalmente:"
echo "   git commit --no-verify"
echo ""
