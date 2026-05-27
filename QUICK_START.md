# ⚡ SOLUCIÓN RÁPIDA: Coverage en SonarQube

## 🎯 Tu Problema
Coverage.xml no se actualiza aunque agregues nuevos tests.

## ✅ Solución (1 línea)
```bash
cd CoffeeAndChill-Backend && run_tests.bat
```

**Eso es todo.**

El script:
1. Crea venv automáticamente
2. Instala dependencias
3. Ejecuta tests
4. **Genera coverage.xml actualizado**
5. Abre reporte visual

## 📚 Documentación Completa
- `CoffeeAndChill-Backend/TESTING_GUIDE.md` - Guía detallada
- `CoffeeAndChill-Backend/pytest.ini` - Configuración de tests
- `CoffeeAndChill-Backend/.coveragerc` - Configuración de cobertura

## 🚀 Opciones Alternativas

**PowerShell (Windows):**
```bash
powershell -ExecutionPolicy Bypass -File CoffeeAndChill-Backend/run_tests.ps1
```

**Linux/macOS:**
```bash
bash CoffeeAndChill-Backend/run_tests.sh
```

**Manual:**
```bash
cd CoffeeAndChill-Backend
python -m venv venv
venv\Scripts\activate.bat  # o: source venv/bin/activate
pip install -r requirements.txt
pytest --cov=app --cov-report=xml
```

---

Listo. Ya no tendrás problemas con coverage.xml. ✨
