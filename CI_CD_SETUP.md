# CI/CD y Pre-commit Hooks Setup

## 📋 Resumen

Este documento detalla la configuración de CI/CD y pre-commit hooks para automatizar la calidad del código en el backend.

### Componentes Configurados:

1. **Pre-commit Hooks** - Validan el código antes de hacer commits ✅
2. **GitHub Actions** - Ejecuta tests y análisis en cada push ✅
3. **Azure Pipelines** - Pipeline de CI/CD completo (existente) ✅
4. **SonarQube** - Análisis de código estático ✅

---

## 🚀 Instalación Rápida

### Paso 1: Crear Estructura de Workflows
```bash
# En Windows
python setup_cicd.py

# O crear manualmente
mkdir .github/workflows
copy workflows_backend_ci.yml .github/workflows/backend-ci.yml
```

### Paso 2: Instalar Pre-commit Hooks

#### En Linux/macOS:
```bash
bash CoffeeAndChill-Backend/scripts/setup-hooks.sh
```

#### En Windows:
```cmd
CoffeeAndChill-Backend\scripts\setup-hooks.bat
```

O instalación manual:
```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
```

### Paso 3: Verificar Instalación
```bash
cd CoffeeAndChill-Backend
pre-commit run --all-files
```

---

## 📦 Pre-commit Hooks Configurados

El archivo `.pre-commit-config.yaml` ha sido actualizado con:

### 1. **Black** - Code Formatter
- Formatea el código Python automáticamente
- Línea máxima: 100 caracteres
- Ejecución automática en commits

### 2. **Flake8** - Linter
- Valida PEP8 y estilo de código
- Detecta errores comunes
- Extensiones: flake8-docstrings, flake8-bugbear

### 3. **isort** - Import Sorter
- Organiza imports alfabéticamente
- Compatible con Black
- Línea máxima: 100 caracteres

### 4. **General Hooks**
- `trailing-whitespace`: Elimina espacios en blanco al final
- `end-of-file-fixer`: Asegura salto de línea al final del archivo
- `check-yaml`: Valida sintaxis YAML
- `check-json`: Valida sintaxis JSON
- `check-merge-conflict`: Detecta marcadores de merge
- `detect-private-key`: Detecta claves privadas

### 5. **yamllint** - YAML Validator
- Valida estructura YAML
- Modo estricto activado

---

## 📝 Archivos Creados/Modificados

### Backend (CoffeeAndChill-Backend/)
| Archivo | Estado | Descripción |
|---------|--------|-------------|
| `.pre-commit-config.yaml` | ✅ Actualizado | Hooks de Black, Flake8, isort, general |
| `scripts/setup-hooks.sh` | ✅ Creado | Setup para Linux/macOS |
| `scripts/setup-hooks.bat` | ✅ Creado | Setup para Windows |
| `CI_CD_SETUP.md` | ✅ Creado | Documentación detallada |

### Root
| Archivo | Estado | Descripción |
|---------|--------|-------------|
| `.github/workflows/backend-ci.yml` | ✅ Creado | GitHub Actions workflow |
| `setup_cicd.py` | ✅ Creado | Script de configuración |
| `setup_workflows.sh` | ✅ Creado | Setup workflows (Linux/macOS) |

---

## 🔄 Flujo de Trabajo

### Ciclo Típico de Desarrollo

1. **Hacer cambios en el código**
   ```bash
   git add .
   ```

2. **Los pre-commit hooks se ejecutan automáticamente**
   - Black formatea el código
   - Flake8 valida el código
   - isort organiza imports
   - Otros checks generales

3. **Si hay errores automáticos, el commit se detiene**
   ```
   ❌ [commitizen-branch-name] FAILED
   ❌ [black] FAILED
   ```

4. **Revisa los cambios auto-corregidos**
   ```bash
   git diff
   git add .
   git commit -m "Mensaje"
   ```

5. **El commit se acepta**
   ```
   ✅ Todos los hooks pasaron
   ```

6. **Al hacer push, GitHub Actions ejecuta**
   - Lint & Format
   - Tests (pytest)
   - Coverage (>70%)
   - SonarQube Analysis
   - Security Scan
   - Docker Build

---

## 🔍 Pipelines de CI/CD

### GitHub Actions - Backend CI/CD
**Ubicación**: `.github/workflows/backend-ci.yml`

**Etapas Ejecutadas**:

1. **Lint and Format** 
   - Pre-commit hooks
   - Black, Flake8, isort

2. **Unit Tests & Coverage**
   - pytest
   - Cobertura mínima: 70%
   - Sube resultados a Codecov

3. **SonarQube Analysis**
   - Análisis estático
   - Detección de vulnerabilidades
   - Métricas de calidad

4. **Security Scan**
   - Bandit: vulnerabilidades
   - Safety: dependencias

5. **Build Docker**
   - Solo en main/develop

### Azure Pipelines (Existente)
**Ubicación**: `azure-pipelines.yml`

Mantiene:
- Tests con cobertura
- SonarCloud analysis
- Build y Push de Docker
- Integración Frontend-Backend

---

## ⚙️ Configuración Detallada

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3.11
        args: [--line-length=100]

  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --extend-ignore=E203,W503]
        additional_dependencies: [flake8-docstrings, flake8-bugbear]

  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: [--profile=black, --line-length=100]

  # ... hooks generales ...
```

### Scripts de Setup

#### Linux/macOS (`scripts/setup-hooks.sh`)
```bash
#!/bin/bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
echo "✅ Pre-commit hooks instalados"
```

#### Windows (`scripts/setup-hooks.bat`)
```batch
@echo off
pip install pre-commit
pre-commit install
pre-commit install --hook-type pre-push
echo ✅ Pre-commit hooks instalados
```

---

## 🛠️ Troubleshooting

### "pre-commit: command not found"
```bash
pip install pre-commit
```

### "Hook failed with exit code 1"
Revisa el mensaje de error específico y ejecuta el linter manualmente:
```bash
cd CoffeeAndChill-Backend
flake8 app/
black app/
isort app/
```

### "Hooks no se ejecutan automáticamente"
```bash
cd CoffeeAndChill-Backend
pre-commit install
pre-commit install --hook-type pre-push
```

### "Coverage is below 70%"
```bash
cd CoffeeAndChill-Backend
pytest --cov=app --cov-report=html
# Abre coverage_html_report/index.html para ver detalles
```

### "SonarQube token inválido"
1. Verifica que `SONAR_TOKEN` esté en GitHub Secrets
2. El token debe ser de tipo USER, no PROJECT
3. Regenera el token en SonarCloud si es necesario

### "GitHub Actions workflow no se dispara"
1. Verifica que el archivo esté en `.github/workflows/backend-ci.yml`
2. Espera unos minutos
3. Fuerza un nuevo push: `git commit --allow-empty && git push`

---

## 📊 Requisitos de Cobertura

- **Cobertura Mínima**: 70%
- **Archivos Cubiertos**: `app/*`
- **Exclusiones**: 
  - `venv/*`
  - `tests/*`
  - `alembic/*`

---

## 🚦 Checklist de Verificación

- [ ] `.pre-commit-config.yaml` actualizado
- [ ] Scripts `setup-hooks.sh` y `setup-hooks.bat` creados
- [ ] `.github/workflows/backend-ci.yml` creado
- [ ] Pre-commit hooks instalados: `bash scripts/setup-hooks.sh`
- [ ] Tests pasando: `pytest --cov=app --cov-fail-under=70`
- [ ] Linting pasando: `pre-commit run --all-files`
- [ ] Git add y push de cambios
- [ ] GitHub Actions workflow dispara correctamente
- [ ] Coverage >70%
- [ ] SonarQube análisis completado

---

## 📚 Referencias

- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Documentation](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure Pipelines Documentation](https://docs.microsoft.com/en-us/azure/devops/pipelines/)
- [SonarQube Documentation](https://docs.sonarqube.org/)

---

## 🎯 Beneficios

✅ **Código consistente**: Black formatea automáticamente
✅ **Menos bugs**: Flake8 detecta errores temprano
✅ **Imports limpios**: isort organiza automáticamente
✅ **Tests obligatorios**: CI/CD bloquea PRs sin tests
✅ **Seguridad**: Bandit y Safety escanean dependencias
✅ **Análisis de calidad**: SonarQube genera métricas
✅ **Automatización**: Todo sucede sin intervención manual

---

**Última actualización**: 2024
**Versión**: 1.0

