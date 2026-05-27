#!/usr/bin/env python
"""Minimal test to check if tests can run."""
import os
import sys

# Set up paths
backend_dir = r"c:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend"
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

# Import pytest
import pytest

# Run specific tests
if __name__ == "__main__":
    # Run a subset of tests first to verify
    exit_code = pytest.main([
        "tests/test_orders.py::test_checkout_success",
        "tests/test_employees.py::test_list_employees_includes_admin",
        "-v",
        "--tb=short",
    ])
    
    if exit_code == 0:
        print("\n✅ Basic tests passed!")
        print("\nNow running full test suite with coverage...")
        
        exit_code = pytest.main([
            "tests/",
            "-v",
            "--tb=short",
            "--cov=app",
            "--cov-report=term-missing",
        ])
    
    sys.exit(exit_code)
