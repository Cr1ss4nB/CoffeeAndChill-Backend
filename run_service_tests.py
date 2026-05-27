#!/usr/bin/env python
"""
Service Layer Test Runner
Executes all service layer unit tests and generates coverage report.
"""

import subprocess
import sys
import os

os.chdir(r"c:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend")

test_files = [
    "tests/unit/test_employee_service.py",
    "tests/unit/test_inventory_service.py",
    "tests/unit/test_payment_service.py",
    "tests/unit/test_workshop_service.py",
]

print("=" * 80)
print("SERVICE LAYER TEST SUITE")
print("=" * 80)
print()

# Run individual test files
for test_file in test_files:
    print(f"Running {test_file}...")
    print("-" * 80)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print()

# Run all service tests with coverage
print("=" * 80)
print("RUNNING ALL SERVICE TESTS WITH COVERAGE")
print("=" * 80)
print()

result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        *test_files,
        "--cov=app.services",
        "--cov-report=term-missing",
        "-v",
    ],
    capture_output=False,
)

sys.exit(result.returncode)
