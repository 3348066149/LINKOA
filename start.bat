@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   LINKOA OA - One-Click Start (Windows)
echo ============================================

REM ==== 1. ensure venv exists and works ====
if not exist ".venv\Scripts\python.exe" goto create_venv
".venv\Scripts\python.exe" --version >nul 2>nul
if errorlevel 1 (
    echo [WARN] venv is broken or copied from another machine, recreating ...
    rmdir /s /q ".venv"
    goto create_venv
)
goto install_deps

:create_venv
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)
echo Creating virtual env .venv ...
python -m venv .venv

:install_deps
echo Installing backend dependencies ...
".venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt" -q

REM ==== 2. frontend: ensure node_modules and a HEALTHY dist ====
REM   dist 存在但残缺（index.html 引用的资源缺失）也会被识别并自动重建，
REM   避免上次那种"登录页 404"的问题。
where node >nul 2>nul
if errorlevel 1 (
    echo [INFO] Node not found, skip frontend build. Make sure frontend\dist is complete.
    goto start_backend
)

pushd frontend

REM 2a. install dependencies if node_modules is missing
if not exist "node_modules" (
    echo Installing frontend dependencies ...
    call npm install
    if errorlevel 1 (
        echo [ERROR] npm install failed. Aborting.
        popd
        pause
        exit /b 1
    )
)

REM 2b. check dist completeness; rebuild if missing or broken
call :check_dist_health
if "!DIST_OK!"=="0" (
    echo Building frontend ...
    call npm run build
    if errorlevel 1 (
        echo [WARN] build failed, retrying after npm install ...
        call npm install
        call npm run build
    )
    if errorlevel 1 (
        echo [ERROR] frontend build failed. Aborting.
        popd
        pause
        exit /b 1
    )
    REM verify build output is healthy
    call :check_dist_health
    if "!DIST_OK!"=="0" (
        echo [ERROR] dist is still incomplete after build. Aborting.
        popd
        pause
        exit /b 1
    )
    echo Frontend build done.
) else (
    echo Frontend dist OK, skip build.
)

popd
goto start_backend

REM ---- check_dist_health: sets DIST_OK=1 if dist\index.html is complete, else 0 ----
:check_dist_health
set "DIST_OK=0"
if not exist "dist\index.html" goto :eof
powershell -NoProfile -ExecutionPolicy Bypass -Command "$bad=0; $h=Get-Content -LiteralPath 'dist\index.html' -Raw; foreach($x in [regex]::Matches($h,'/assets/[\w.-]+')){ if(-not (Test-Path -LiteralPath ('dist'+$x.Value))){ $bad=1 } }; if($bad){exit 1}else{exit 0}" >nul 2>nul
if errorlevel 1 (set "DIST_OK=0") else (set "DIST_OK=1")
goto :eof

REM ==== 3. start backend (single port, hosts frontend dist) ====
:start_backend
echo Backend listening on 0.0.0.0:8000
echo Open in browser:  http://localhost:8000  (or http://127.0.0.1:8000)
echo For LAN access:    http://^<this-machine-ip^>:8000   (ipconfig 查看本机 IP)
echo Press Ctrl+C to stop.
cd backend
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

pause
