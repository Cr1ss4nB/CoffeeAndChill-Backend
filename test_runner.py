#!/usr/bin/env python
"""Run pytest tests with coverage."""
import subprocess
import sys
import os

# Change to backend directory
backend_dir = r"c:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend"
os.chdir(backend_dir)

# Get Python executable from venv
venv_python = os.path.join(backend_dir, "venv", "Scripts", "python.exe")
if not os.path.exists(venv_python):
    print(f"❌ venv Python not found: {venv_python}")
    sys.exit(1)

print(f"✅ Using Python: {venv_python}\n")

# First validate imports
print("=" * 70)
print("VALIDATING IMPORTS")
print("=" * 70)

validate_result = subprocess.run([
    venv_python, "-c", """
import sys
sys.path.insert(0, '.')
from tests.conftest import get_admin_headers
from tests import test_orders, test_employees, test_payments, test_catalog
print('✅ All imports OK')
"""
], capture_output=True, text=True)

print(validate_result.stdout)
if validate_result.returncode != 0:
    print(validate_result.stderr)
    sys.exit(1)

# Run pytest
print("\n" + "=" * 70)
print("RUNNING PYTEST")
print("=" * 70 + "\n")

pytest_result = subprocess.run([
    venv_python, "-m", "pytest",
    "tests/",
    "-v",
    "--tb=short",
    "--cov=app",
    "--cov-report=term-missing",
    "--co-fail-under=50",
], capture_output=False, text=True)

sys.exit(pytest_result.returncode)
