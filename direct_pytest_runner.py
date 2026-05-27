#!/usr/bin/env python3
"""
Direct pytest runner - bypasses PowerShell issues
"""
import os
import sys

# Change to backend directory
backend_dir = r"C:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend"
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

# Now run pytest via runpy to avoid subprocess issues
import runpy

print("="*70)
print("Running pytest tests from execute_tests.py")
print("="*70)
print()

# Test 1: Employee Service
print("="*70)
print("TEST 1: Employee Service Tests")
print("="*70)
sys.argv = ["pytest", "tests/unit/test_employee_service.py", "-v"]
try:
    runpy.run_module("pytest", run_name="__main__")
except SystemExit as e:
    print(f"Exit code: {e.code}")

# Test 2: Inventory Service
print("\n" + "="*70)
print("TEST 2: Inventory Service Tests")
print("="*70)
sys.argv = ["pytest", "tests/unit/test_inventory_service.py", "-v"]
try:
    runpy.run_module("pytest", run_name="__main__")
except SystemExit as e:
    print(f"Exit code: {e.code}")

# Test 3: Payment Service
print("\n" + "="*70)
print("TEST 3: Payment Service Tests")
print("="*70)
sys.argv = ["pytest", "tests/unit/test_payment_service.py", "-v"]
try:
    runpy.run_module("pytest", run_name="__main__")
except SystemExit as e:
    print(f"Exit code: {e.code}")

# Test 4: Workshop Service
print("\n" + "="*70)
print("TEST 4: Workshop Service Tests")
print("="*70)
sys.argv = ["pytest", "tests/unit/test_workshop_service.py", "-v"]
try:
    runpy.run_module("pytest", run_name="__main__")
except SystemExit as e:
    print(f"Exit code: {e.code}")

# Test 5: All Services with Coverage
print("\n" + "="*70)
print("TEST 5: All Services with Coverage Report")
print("="*70)
sys.argv = [
    "pytest",
    "tests/unit/test_employee_service.py",
    "tests/unit/test_inventory_service.py",
    "tests/unit/test_payment_service.py",
    "tests/unit/test_workshop_service.py",
    "--cov=app.services",
    "--cov-report=term-missing",
    "-v"
]
try:
    runpy.run_module("pytest", run_name="__main__")
except SystemExit as e:
    print(f"Exit code: {e.code}")

print("\n" + "="*70)
print("All tests complete!")
print("="*70)
