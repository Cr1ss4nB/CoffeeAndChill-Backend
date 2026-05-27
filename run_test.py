#!/usr/bin/env python
"""Simple script to run pytest"""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    cwd="c:\\Users\\lvfm\\Documents\\2026-1\\trabajo de campo\\CoffeeAndChill-Backend"
)
sys.exit(result.returncode)
