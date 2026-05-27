#!/usr/bin/env python
"""
Comprehensive validation script for all service files and test files.
Checks syntax, imports, and file existence.
"""

import py_compile
import sys
import os
from pathlib import Path

def check_syntax(filepath):
    """Check Python syntax of a file."""
    try:
        py_compile.compile(filepath, doraise=True)
        return True, "OK"
    except py_compile.PyCompileError as e:
        return False, str(e)

def check_import(import_statement):
    """Check if an import statement works."""
    try:
        exec(import_statement)
        return True, "OK"
    except Exception as e:
        return False, str(e)

def main():
    """Run all validation checks."""
    os.chdir('C:\\Users\\lvfm\\Documents\\2026-1\\trabajo de campo\\CoffeeAndChill-Backend')
    
    print("=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)
    
    # Service files to check
    service_files = [
        'app/services/employee_service.py',
        'app/services/inventory_service.py',
        'app/services/payment_service.py',
        'app/services/workshop_service.py',
    ]
    
    # Test files to check
    test_files = [
        'tests/unit/test_employee_service.py',
        'tests/unit/test_inventory_service.py',
        'tests/unit/test_payment_service.py',
        'tests/unit/test_workshop_service.py',
    ]
    
    # Import statements to check
    imports = [
        'from app.services.employee_service import create_employee',
        'from app.services.inventory_service import get_current_stock',
        'from app.services.payment_service import create_payment',
        'from app.services.workshop_service import create_workshop',
    ]
    
    print("\n1. CHECKING SERVICE FILE SYNTAX")
    print("-" * 80)
    service_ok = True
    for filepath in service_files:
        exists = os.path.exists(filepath)
        if exists:
            status, msg = check_syntax(filepath)
            marker = "✓" if status else "✗"
            print(f"{marker} {filepath}: {msg}")
            if not status:
                service_ok = False
        else:
            print(f"✗ {filepath}: FILE NOT FOUND")
            service_ok = False
    
    print("\n2. CHECKING TEST FILE SYNTAX")
    print("-" * 80)
    test_ok = True
    for filepath in test_files:
        exists = os.path.exists(filepath)
        if exists:
            status, msg = check_syntax(filepath)
            marker = "✓" if status else "✗"
            print(f"{marker} {filepath}: {msg}")
            if not status:
                test_ok = False
        else:
            print(f"✗ {filepath}: FILE NOT FOUND")
            test_ok = False
    
    print("\n3. CHECKING IMPORTS")
    print("-" * 80)
    import_ok = True
    for import_stmt in imports:
        status, msg = check_import(import_stmt)
        marker = "✓" if status else "✗"
        print(f"{marker} {import_stmt}")
        if not status:
            print(f"   Error: {msg}")
            import_ok = False
    
    print("\n4. LISTING FILES IN app/services/")
    print("-" * 80)
    services_dir = Path('app/services')
    if services_dir.exists():
        files = sorted([f.name for f in services_dir.glob('*.py')])
        for f in files:
            print(f"  • {f}")
    else:
        print("✗ app/services directory not found")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    all_ok = service_ok and test_ok and import_ok
    
    if all_ok:
        print("✓ All checks PASSED!")
        print("  • All service files have valid syntax")
        print("  • All test files have valid syntax")
        print("  • All imports work correctly")
        return 0
    else:
        print("✗ Some checks FAILED:")
        if not service_ok:
            print("  • Service files have syntax errors")
        if not test_ok:
            print("  • Test files have syntax errors")
        if not import_ok:
            print("  • Some imports failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
