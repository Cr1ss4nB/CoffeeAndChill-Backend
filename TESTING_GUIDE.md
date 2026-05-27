# Guía de Cobertura y Testing

Este documento explica cómo ejecutar los tests, generar reportes de cobertura y enviarlos a SonarQube.

## 📋 Requisitos Previos

- Python 3.11+
- (Opcional) Docker para ejecutar SonarQube
- (Opcional) SonarQube corriendo en `http://localhost:9000`

## 🚀 Ejecución Rápida

### Opción 1: Script Batch (Windows) - MÁS FÁCIL

```bash
cd CoffeeAndChill-Backend
run_tests.bat
```

**Qué hace:**
✅ Crea entorno virtual si no existe  
✅ Instala dependencias automáticamente  
✅ Limpia cachés previos  
✅ Ejecuta tests  
✅ Genera `coverage.xml`  
✅ Genera `htmlcov/index.html`  
✅ Ofrece abrir reporte HTML  

### Opción 2: PowerShell (Windows alternativa)

```bash
cd CoffeeAndChill-Backend
powershell -ExecutionPolicy Bypass -File run_tests.ps1
```

### Opción 3: Bash Script (Linux/macOS)

```bash
cd CoffeeAndChill-Backend
bash run_tests.sh
```

### Opción 4: Manual (Si necesitas control total)

```bash
cd CoffeeAndChill-Backend

# Crear venv
python -m venv venv

# Activar (Windows)
venv\Scripts\activate.bat
# O activar (Linux/macOS)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar tests
pytest -v --tb=short

# Generar cobertura
coverage xml
coverage report --omit="*/tests/*"
```

## 📊 Archivos Generados

- **coverage.xml** - Reporte de cobertura en formato XML (para SonarQube)
- **htmlcov/index.html** - Reporte HTML interactivo de cobertura
- **.coverage** - Archivo de datos de coverage (interno)

## 🔧 Configuración

### pytest.ini
Define cómo pytest ejecuta los tests:
- Descubre tests en carpeta `tests/`
- Genera reporte XML de cobertura automáticamente
- Requiere mínimo 70% de cobertura (opcional, se puede deshabilitar)
- Modo async activado para tests asincronos

### .coveragerc
Define qué código incluir/excluir en cobertura:
- Incluye: `app/`
- Excluye: tests, migrations, alembic
- Genera reportes en HTML y XML

### sonar-project.properties
Configuración de SonarQube:
- Apunta a `coverage.xml` para la cobertura
- Define qué archivos analizar
- Conecta con servidor SonarQube

## ✅ Verificar Cobertura

Después de ejecutar los tests:

1. **Navegador**: Abre `htmlcov/index.html` 
   - Click en archivo para ver líneas no cubiertas (rojo)
   - Porcentaje de cobertura por archivo

2. **Terminal**: Mira el resumen de `coverage report`
   ```
   Name                      Stmts   Miss  Cover
   ———————————————————————————————————————————————
   app/core/config.py          48      4    91%
   app/core/security.py        34      2    94%
   ...
   ———————————————————————————————————————————————
   TOTAL                      765     94    88%
   ```

3. **SonarQube**: Abre `http://localhost:9000` para análisis completo
   - Conecta `coverage.xml` automáticamente
   - Muestra análisis de calidad adicional

## 📈 Mejorar la Cobertura

### Identificar qué falta cubrir:

1. Abre `htmlcov/index.html` en el navegador
2. Haz click en un archivo para expandir
3. Líneas **rojas** = no cubiertas
4. Líneas **verdes** = cubiertas
5. Escribe tests para esas funciones

### Ejemplo de test a escribir:
```python
# tests/test_example.py
from app.services.my_service import my_function

def test_my_function_with_valid_input():
    result = my_function("valid_input")
    assert result == "expected_output"

def test_my_function_with_invalid_input():
    result = my_function("invalid_input")
    assert result == "error_output"
```

## 🐛 Troubleshooting

### "pytest: no se reconoce como comando"

**Solución:** Usa uno de los scripts que instalan automáticamente:
```bash
# Windows - Usa esto
run_tests.bat

# O PowerShell
powershell -ExecutionPolicy Bypass -File run_tests.ps1

# O Linux/macOS
bash run_tests.sh
```

### "coverage.xml no se actualiza"
```bash
# Limpia archivos previos
rm coverage.xml
rm -rf .pytest_cache/
rm -rf .coverage

# Ejecuta nuevamente con limpieza
run_tests.bat
```

### "Tests no se encuentran"
Verifica que los archivos de test:
- Están en la carpeta `tests/`
- Empiezan con `test_`
- Contienen funciones que empiezan con `test_`

Ejemplo válido:
```
tests/
├── test_auth.py          ✅
├── test_orders.py        ✅
└── unit/
    ├── test_core_security.py  ✅
    └── test_services_availability.py  ✅
```

### "SonarQube no recibe cobertura"
1. Verifica que `coverage.xml` existe
2. Verifica que `sonar-project.properties` apunta correctamente
3. Verifica conexión a SonarQube:
   ```bash
   curl http://localhost:9000/api/system/health
   ```

### "Entorno virtual no funciona"
```bash
# Elimina venv
rmdir /s venv  # Windows
rm -rf venv    # Linux/macOS

# Ejecuta el script nuevamente - lo recreará
run_tests.bat
```

## 📝 Notas Importantes

- **Tests:** Se ejecutan en una BD SQLite en memoria (no necesita BD real)
- **Fixtures:** Usan fixtures de pytest para setup/teardown automático
- **Mocks:** Los tests reemplazan Redis y otros servicios externos
- **Async:** Los tests async funcionan automáticamente (pytest-asyncio)
- **Venv:** Se crea automáticamente si no existe

## 🔗 Enlaces Útiles

- [Documentación de pytest](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [SonarQube Python](https://docs.sonarqube.org/latest/languages/python/)

