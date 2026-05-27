#!/usr/bin/env python
"""Execute pytest using runpy."""
import runpy
import sys
import os

# Set up environment
backend_dir = r"c:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend"
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

# Set argv for pytest
sys.argv = [
    "pytest",
    "tests/",
    "-v",
    "--tb=short",
    "--cov=app",
    "--cov-report=term-missing",
]

# Run pytest
try:
    runpy.run_module("pytest", run_name="__main__")
except SystemExit as e:
    sys.exit(e.code)
