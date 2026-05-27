#!/usr/bin/env python3
"""
VALIDADOR AUTOMÁTICO - Reorganización de Routers
Verifica que todos los cambios han sido aplicados correctamente
"""

import os
import re
from pathlib import Path

def validate_main_py():
    """Valida que main.py tenga todos los prefijos correctos"""
    print("\n" + "="*80)
    print("1️⃣  VALIDANDO: main.py")
    print("="*80)
    
    main_path = Path("CoffeeAndChill-Backend/main.py")
    if not main_path.exists():
        print("❌ ERROR: main.py no encontrado")
        return False
    
    content = main_path.read_text()
    
    required_prefixes = [
        ('auth.router', '/auth'),
        ('catalog.router', '/api/v1/catalog'),
        ('inventory.router', '/api/v1/admin/inventory'),
        ('ingredients.router', '/api/v1/admin/ingredients'),
        ('products.router', '/api/v1/admin/products'),
        ('employees.router', '/api/v1/admin/employees'),
        ('tables.router', '/api/v1/admin/tables'),
        ('orders.router', '/api/v1/orders'),
        ('workshops.router', '/api/v1/workshops'),
        ('public.router', '/api/v1/public'),
        ('payments.router', '/api/v1/admin/payments'),
    ]
    
    all_valid = True
    for router, expected_prefix in required_prefixes:
        if f'include_router({router}, prefix="{expected_prefix}"' in content:
            print(f"  ✅ {router:<30} → {expected_prefix}")
        else:
            print(f"  ❌ {router:<30} → {expected_prefix} (NO ENCONTRADO)")
            all_valid = False
    
    return all_valid

def validate_test_urls():
    """Valida que los tests usen URLs correctas"""
    print("\n" + "="*80)
    print("2️⃣  VALIDANDO: URLs en Tests")
    print("="*80)
    
    tests_dir = Path("CoffeeAndChill-Backend/tests")
    if not tests_dir.exists():
        print("❌ ERROR: Carpeta tests no encontrada")
        return False
    
    # Buscar referencias a endpoints antiguos (debería estar vacío)
    old_patterns = [
        (r'client\.get\("\/catalog', "Endpoints de catalog sin prefijo"),
        (r'client\.post\("\/admin\/products', "Admin products sin /api/v1"),
        (r'client\.get\("\/orders', "Endpoints de orders sin prefijo (excepto /api/v1)"),
    ]
    
    found_old = False
    for pattern, description in old_patterns:
        matches = []
        for py_file in tests_dir.rglob("*.py"):
            content = py_file.read_text()
            if re.search(pattern, content):
                # Filtrar matches que sí tienen /api/v1
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line) and '/api/v1' not in line:
                        matches.append(f"  {py_file.name}:{i}")
        
        if matches:
            print(f"  ⚠️  {description}:")
            for match in matches:
                print(match)
            found_old = True
        else:
            print(f"  ✅ No encontradas referencias antiguas: {description}")
    
    return not found_old

def validate_url_consistency():
    """Valida que todas las URLs sean consistentes"""
    print("\n" + "="*80)
    print("3️⃣  VALIDANDO: Consistencia de URLs")
    print("="*80)
    
    tests_dir = Path("CoffeeAndChill-Backend/tests")
    
    # Patrones que deberían encontrarse
    expected_patterns = [
        (r'"/api/v1/catalog/', "URLs de catalog"),
        (r'"/api/v1/admin/products', "URLs de products admin"),
        (r'"/api/v1/admin/employees', "URLs de employees admin"),
        (r'"/api/v1/orders', "URLs de orders"),
        (r'"/api/v1/admin/inventory', "URLs de inventory"),
    ]
    
    all_found = True
    for pattern, description in expected_patterns:
        found = False
        for py_file in tests_dir.rglob("*.py"):
            if re.search(pattern, py_file.read_text()):
                found = True
                break
        
        if found:
            print(f"  ✅ Encontrado: {description}")
        else:
            print(f"  ❌ NO encontrado: {description}")
            all_found = False
    
    return all_found

def count_endpoint_changes():
    """Cuenta el número de cambios realizados"""
    print("\n" + "="*80)
    print("4️⃣  CONTANDO: Cambios de Endpoints")
    print("="*80)
    
    tests_dir = Path("CoffeeAndChill-Backend/tests")
    
    api_v1_count = 0
    api_admin_count = 0
    
    for py_file in tests_dir.rglob("*.py"):
        content = py_file.read_text()
        api_v1_count += len(re.findall(r'"/api/v1/', content))
        api_admin_count += len(re.findall(r'"/api/v1/admin/', content))
    
    total = api_v1_count + api_admin_count
    
    print(f"  📊 Endpoints /api/v1/:        {api_v1_count}")
    print(f"  📊 Endpoints /api/v1/admin/:  {api_admin_count}")
    print(f"  📊 TOTAL:                     {total}")
    print(f"\n  ✅ Esperado: ~223 endpoints")
    print(f"  {'✅' if 200 <= total <= 250 else '⚠️'} Rango válido: 200-250")
    
    return 200 <= total <= 250

def validate_file_structure():
    """Valida que la estructura de archivos sea correcta"""
    print("\n" + "="*80)
    print("5️⃣  VALIDANDO: Estructura de Archivos")
    print("="*80)
    
    files_to_check = [
        "CoffeeAndChill-Backend/main.py",
        "CoffeeAndChill-Backend/tests/test_catalog.py",
        "CoffeeAndChill-Backend/tests/test_orders.py",
        "CoffeeAndChill-Backend/tests/test_employees.py",
        "CoffeeAndChill-Backend/tests/integration/test_ingredients.py",
    ]
    
    all_exist = True
    for file in files_to_check:
        path = Path(file)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {file:<60} ({size:,} bytes)")
        else:
            print(f"  ❌ {file:<60} (NO ENCONTRADO)")
            all_exist = False
    
    return all_exist

def check_python_syntax():
    """Verifica que los archivos Python tengan sintaxis válida"""
    print("\n" + "="*80)
    print("6️⃣  VALIDANDO: Sintaxis Python")
    print("="*80)
    
    import py_compile
    import tempfile
    
    files_to_check = [
        Path("CoffeeAndChill-Backend/main.py"),
        Path("CoffeeAndChill-Backend/tests/test_catalog.py"),
        Path("CoffeeAndChill-Backend/tests/test_employees.py"),
    ]
    
    all_valid = True
    for file in files_to_check:
        if not file.exists():
            continue
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.pyc', delete=True) as tmp:
                py_compile.compile(str(file), cfile=tmp.name, doraise=True)
            print(f"  ✅ {file.name:<40} (sintaxis válida)")
        except py_compile.PyCompileError as e:
            print(f"  ❌ {file.name:<40} (ERROR: {str(e)[:50]}...)")
            all_valid = False
    
    return all_valid

def main():
    """Ejecuta todas las validaciones"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "VALIDADOR AUTOMÁTICO - ROUTER REORGANIZATION" + " "*14 + "║")
    print("╚" + "="*78 + "╝")
    
    results = []
    
    try:
        # 1. Validar main.py
        results.append(("main.py", validate_main_py()))
        
        # 2. Validar URLs en tests
        results.append(("URLs en Tests", validate_test_urls()))
        
        # 3. Validar consistencia
        results.append(("Consistencia de URLs", validate_url_consistency()))
        
        # 4. Contar cambios
        results.append(("Conteo de Endpoints", count_endpoint_changes()))
        
        # 5. Validar estructura
        results.append(("Estructura de Archivos", validate_file_structure()))
        
        # 6. Validar sintaxis
        results.append(("Sintaxis Python", check_python_syntax()))
        
    except Exception as e:
        print(f"\n❌ ERROR durante validación: {e}")
        return False
    
    # Resumen final
    print("\n" + "="*80)
    print("📋 RESUMEN DE VALIDACIONES")
    print("="*80)
    
    for check_name, result in results:
        status = "✅ PASADO" if result else "❌ FALLIDO"
        print(f"  {status:<15} {check_name}")
    
    # Conclusión
    print("\n" + "="*80)
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("✅ TODAS LAS VALIDACIONES PASARON")
        print("\n🎉 LA REORGANIZACIÓN DE ROUTERS HA SIDO VERIFICADA EXITOSAMENTE")
        print("\nPróximos pasos:")
        print("  1. Ejecutar: python -m pytest tests/ -v --tb=short")
        print("  2. Revisar: TAREA_COMPLETADA.md")
        print("  3. Actualizar: Frontend")
    else:
        print("❌ ALGUNAS VALIDACIONES FALLARON")
        print("\nRevisa los errores arriba y corrige los problemas encontrados")
    
    print("="*80 + "\n")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
