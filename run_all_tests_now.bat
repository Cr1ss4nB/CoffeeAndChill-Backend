@echo off
cd /d "C:\Users\lvfm\Documents\2026-1\trabajo de campo\CoffeeAndChill-Backend"

echo.
echo ======================================================================
echo TEST 1: Employee Service Tests
echo ======================================================================
py -m pytest tests/unit/test_employee_service.py -v
set RESULT1=%ERRORLEVEL%

echo.
echo ======================================================================
echo TEST 2: Inventory Service Tests
echo ======================================================================
py -m pytest tests/unit/test_inventory_service.py -v
set RESULT2=%ERRORLEVEL%

echo.
echo ======================================================================
echo TEST 3: Payment Service Tests
echo ======================================================================
py -m pytest tests/unit/test_payment_service.py -v
set RESULT3=%ERRORLEVEL%

echo.
echo ======================================================================
echo TEST 4: Workshop Service Tests
echo ======================================================================
py -m pytest tests/unit/test_workshop_service.py -v
set RESULT4=%ERRORLEVEL%

echo.
echo ======================================================================
echo TEST 5: All Services with Coverage Report
echo ======================================================================
py -m pytest tests/unit/test_employee_service.py tests/unit/test_inventory_service.py tests/unit/test_payment_service.py tests/unit/test_workshop_service.py --cov=app.services --cov-report=term-missing -v
set RESULT5=%ERRORLEVEL%

echo.
echo ======================================================================
echo TEST EXECUTION SUMMARY
echo ======================================================================
if %RESULT1% equ 0 (echo Employee Service Tests: PASSED) else (echo Employee Service Tests: FAILED - Code: %RESULT1%)
if %RESULT2% equ 0 (echo Inventory Service Tests: PASSED) else (echo Inventory Service Tests: FAILED - Code: %RESULT2%)
if %RESULT3% equ 0 (echo Payment Service Tests: PASSED) else (echo Payment Service Tests: FAILED - Code: %RESULT3%)
if %RESULT4% equ 0 (echo Workshop Service Tests: PASSED) else (echo Workshop Service Tests: FAILED - Code: %RESULT4%)
if %RESULT5% equ 0 (echo All Services with Coverage: PASSED) else (echo All Services with Coverage: FAILED - Code: %RESULT5%)

echo ======================================================================
