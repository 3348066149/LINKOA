@echo off
cd /d "%~dp0"

echo ============================================
echo   LINKOA OA - Stop Services (Windows)
echo ============================================

set "FOUND="

echo.
echo Checking backend port 8000 and frontend port 5173 ...

for %%c in (8000 5173) do (
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr /c:":%%c" ^| findstr "LISTENING"') do (
        echo   Port %%c : found PID %%p, killing ...
        taskkill /F /PID %%p >nul 2>nul
        set "FOUND=1"
    )
)

echo.
if defined FOUND (
    echo All services stopped.
) else (
    echo No running service found (ports 8000 / 5173 are not listening).
)

echo.
pause
