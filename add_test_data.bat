@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   LINKOA - Add Test Data (idempotent: re-run = restore)
echo ============================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Please run start.bat first to init.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "backend\scripts\test_data.py"

echo.
pause
