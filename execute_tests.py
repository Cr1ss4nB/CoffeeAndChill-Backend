import subprocess
import sys
import os

os.chdir(r"C:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend")

commands = [
    ("Employee Service Tests", 
     [sys.executable, "-m", "pytest", "tests/unit/test_employee_service.py", "-v"]),
    ("Inventory Service Tests", 
     [sys.executable, "-m", "pytest", "tests/unit/test_inventory_service.py", "-v"]),
    ("Payment Service Tests", 
     [sys.executable, "-m", "pytest", "tests/unit/test_payment_service.py", "-v"]),
    ("Workshop Service Tests", 
     [sys.executable, "-m", "pytest", "tests/unit/test_workshop_service.py", "-v"]),
    ("All Services with Coverage", 
     [sys.executable, "-m", "pytest", 
      "tests/unit/test_employee_service.py", "tests/unit/test_inventory_service.py",
      "tests/unit/test_payment_service.py", "tests/unit/test_workshop_service.py",
      "--cov=app.services", "--cov-report=term-missing", "-v"]),
]

results = {}
for name, cmd in commands:
    print(f"\n{'='*70}")
    print(f"{name}")
    print(f"{'='*70}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    results[name] = result.returncode

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
for name, code in results.items():
    status = "✓ PASSED" if code == 0 else "✗ FAILED"
    print(f"{name}: {status} (code: {code})")
