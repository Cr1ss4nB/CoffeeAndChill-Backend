@echo off
cd /d "C:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend"

REM Activate venv if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run tests for all service modules
echo Running Employee Service Tests...
python -m pytest tests/unit/test_employee_service.py -v --tb=short 2>&1

echo.
echo Running Inventory Service Tests...
python -m pytest tests/unit/test_inventory_service.py -v --tb=short 2>&1

echo.
echo Running Payment Service Tests...
python -m pytest tests/unit/test_payment_service.py -v --tb=short 2>&1

echo.
echo Running Workshop Service Tests...
python -m pytest tests/unit/test_workshop_service.py -v --tb=short 2>&1

echo.
echo Running all services coverage...
python -m pytest tests/unit/test_employee_service.py tests/unit/test_inventory_service.py tests/unit/test_payment_service.py tests/unit/test_workshop_service.py --cov=app.services --cov-report=term-missing 2>&1

pause
