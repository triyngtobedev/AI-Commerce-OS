@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

set "PROJECT_ROOT=C:\Projetos\AI-Commerce-OS"
set "INFRA_DIR=%PROJECT_ROOT%\infra"

echo.
echo === Parando AI-Commerce-OS ===
echo.

REM --- Parar FastAPI (uvicorn na porta 8000) ---
echo Parando FastAPI (uvicorn)...

for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

taskkill /FI "WINDOWTITLE eq AI-Commerce-OS API*" /F >nul 2>&1

powershell -NoProfile -Command ^
    "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*uvicorn api.main_api*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

REM --- Parar containers Docker do n8n ---
set "DOCKER=docker"
where docker >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\Docker\Docker\resources\bin\docker.exe" (
        set "DOCKER=C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    )
)

if exist "%INFRA_DIR%\docker-compose.local.yml" (
    echo Parando containers n8n...
    pushd "%INFRA_DIR%"
    "%DOCKER%" compose -f docker-compose.local.yml down 2>nul
    popd
)

echo.
echo Projeto parado. Pode jogar! 🎮
echo.
pause
