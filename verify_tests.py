#!/usr/bin/env python
"""Count and list all test functions in our test files."""
import os
import re
from pathlib import Path

backend_dir = Path(r"c:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend\tests")

test_files = {
    "test_orders.py": backend_dir / "test_orders.py",
    "test_employees.py": backend_dir / "test_employees.py", 
    "test_payments.py": backend_dir / "test_payments.py",
    "test_catalog.py": backend_dir / "test_catalog.py",
}

total_tests = 0
print("=" * 70)
print("TEST COUNT SUMMARY")
print("=" * 70)

for file_name, file_path in test_files.items():
    if not file_path.exists():
        print(f"\n❌ {file_name}: NOT FOUND")
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all test functions
    test_functions = re.findall(r'^def (test_\w+)\(', content, re.MULTILINE)
    
    count = len(test_functions)
    total_tests += count
    
    print(f"\n✅ {file_name}: {count} tests")
    for i, test_name in enumerate(test_functions, 1):
        print(f"   {i:2d}. {test_name}")

print("\n" + "=" * 70)
print(f"TOTAL: {total_tests} tests in modified files")
print("=" * 70)

# Verify imports
print("\n" + "=" * 70)
print("IMPORT VERIFICATION")
print("=" * 70)

imports_ok = True

for file_name, file_path in test_files.items():
    if not file_path.exists():
        print(f"\n⚠️  {file_name}: SKIPPED")
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"\n{file_name}:")
    
    # Check for conftest imports
    if "from tests.conftest import" in content:
        print("  ✅ Uses conftest helpers")
    elif "def _admin_token" in content:
        print("  ⚠️  Has local login function (OK if needed)")
    else:
        print("  ℹ️  No conftest imports")
    
    # Check for helpers
    if "get_admin_headers" in content or "get_customer_headers" in content:
        print("  ✅ Uses centralized helpers")
    
    # Check syntax
    try:
        compile(content, str(file_path), 'exec')
        print("  ✅ Python syntax OK")
    except SyntaxError as e:
        print(f"  ❌ Syntax error: {e}")
        imports_ok = False

print("\n" + "=" * 70)
if imports_ok:
    print("✅ All files have valid Python syntax")
else:
    print("⚠️  Some files have syntax issues - review needed")
print("=" * 70)
