#!/usr/bin/env python
"""Run pytest commands and generate a summary report."""
import subprocess
import sys
import os
from pathlib import Path

backend_dir = r"C:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend"
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

results = {}

# Test 1: Employee Service
print("=" * 70)
print("TEST 1: Employee Service Tests")
print("=" * 70)
result1 = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit/test_employee_service.py", "-v"],
    capture_output=True,
    text=True
)
print(result1.stdout)
if result1.stderr:
    print("STDERR:", result1.stderr)
results["Employee Service"] = {
    "code": result1.returncode,
    "passed": result1.returncode == 0
}

# Test 2: Inventory Service
print("\n" + "=" * 70)
print("TEST 2: Inventory Service Tests")
print("=" * 70)
result2 = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit/test_inventory_service.py", "-v"],
    capture_output=True,
    text=True
)
print(result2.stdout)
if result2.stderr:
    print("STDERR:", result2.stderr)
results["Inventory Service"] = {
    "code": result2.returncode,
    "passed": result2.returncode == 0
}

# Test 3: Payment Service
print("\n" + "=" * 70)
print("TEST 3: Payment Service Tests")
print("=" * 70)
result3 = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit/test_payment_service.py", "-v"],
    capture_output=True,
    text=True
)
print(result3.stdout)
if result3.stderr:
    print("STDERR:", result3.stderr)
results["Payment Service"] = {
    "code": result3.returncode,
    "passed": result3.returncode == 0
}

# Test 4: Workshop Service
print("\n" + "=" * 70)
print("TEST 4: Workshop Service Tests")
print("=" * 70)
result4 = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/unit/test_workshop_service.py", "-v"],
    capture_output=True,
    text=True
)
print(result4.stdout)
if result4.stderr:
    print("STDERR:", result4.stderr)
results["Workshop Service"] = {
    "code": result4.returncode,
    "passed": result4.returncode == 0
}

# Test 5: All Services with Coverage
print("\n" + "=" * 70)
print("TEST 5: All Services with Coverage Report")
print("=" * 70)
result5 = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        "tests/unit/test_employee_service.py",
        "tests/unit/test_inventory_service.py",
        "tests/unit/test_payment_service.py",
        "tests/unit/test_workshop_service.py",
        "--cov=app.services",
        "--cov-report=term-missing",
        "-v"
    ],
    capture_output=True,
    text=True
)
print(result5.stdout)
if result5.stderr:
    print("STDERR:", result5.stderr)
results["All Services with Coverage"] = {
    "code": result5.returncode,
    "passed": result5.returncode == 0,
    "output": result5.stdout
}

# Print summary
print("\n" + "=" * 70)
print("TEST EXECUTION SUMMARY")
print("=" * 70)
for test_name, result in results.items():
    status = "✓ PASSED" if result["passed"] else "✗ FAILED"
    print(f"{test_name}: {status} (exit code: {result['code']})")

print("\n" + "=" * 70)
print("COVERAGE INFORMATION")
print("=" * 70)
# Extract coverage info from last result
if "output" in results["All Services with Coverage"]:
    lines = results["All Services with Coverage"]["output"].split("\n")
    in_coverage = False
    for line in lines:
        if "coverage" in line.lower() or "Name" in line or "app/services" in line or "TOTAL" in line:
            print(line)

# Overall result
all_passed = all(r["passed"] for r in results.values())
print("\n" + "=" * 70)
print(f"OVERALL RESULT: {'ALL TESTS PASSED ✓' if all_passed else 'SOME TESTS FAILED ✗'}")
print("=" * 70)

sys.exit(0 if all_passed else 1)
