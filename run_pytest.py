#!/usr/bin/env python
"""Simple script to run pytest with coverage."""
import subprocess
import sys
import os

os.chdir(r"c:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend")

# Run pytest with coverage
result = subprocess.run([
    sys.executable, "-m", "pytest",
    "tests/",
    "-v",
    "--tb=short",
    "--cov=app",
    "--cov-report=term-missing",
], capture_output=False)

sys.exit(result.returncode)
