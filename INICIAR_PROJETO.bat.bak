@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

set "PROJECT_ROOT=C:\Projetos\AI-Commerce-OS"
set "INFRA_DIR=%PROJECT_ROOT%\infra"

echo.
echo === Iniciando AI-Commerce-OS ===
echo.

cd /d "%PROJECT_ROOT%" 2>nul
if errorlevel 1 (
    echo Erro: pasta do projeto nao encontrada em %PROJECT_ROOT%
    pause
    exit /b 1
)

REM --- Localizar executavel do Docker ---
set "DOCKER=docker"
where docker >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\Docker\Docker\resources\bin\docker.exe" (
        set "DOCKER=C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    )
)

REM --- Iniciar Docker Desktop se necessario ---
"%DOCKER%" info >nul 2>&1
if errorlevel 1 (
    echo Iniciando Docker Desktop...
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo Docker Desktop nao encontrado. Instale em https://www.docker.com/products/docker-desktop/
        pause
        exit /b 1
    )

    echo Aguardando Docker inicializar...
    set /a WAIT=0
    :wait_docker
    timeout /t 5 /nobreak >nul
    set /a WAIT+=5
    "%DOCKER%" info >nul 2>&1
    if not errorlevel 1 goto docker_ready
    if !WAIT! geq 120 (
        echo Timeout aguardando Docker. Abra o Docker Desktop manualmente e tente novamente.
        pause
        exit /b 1
    )
    echo   ... !WAIT! s
    goto wait_docker
)
:docker_ready
echo Docker pronto!

REM --- Validar configuracao do n8n ---
if not exist "%INFRA_DIR%\.env.n8n" (
    echo Arquivo infra\.env.n8n nao encontrado.
    echo Copie infra\.env.n8n.example para infra\.env.n8n e preencha os valores.
    pause
    exit /b 1
)

REM --- Subir containers n8n ---
echo Subindo containers n8n...
pushd "%INFRA_DIR%"
"%DOCKER%" compose -f docker-compose.local.yml up -d
if errorlevel 1 (
    popd
    echo Erro ao subir containers n8n.
    pause
    exit /b 1
)
popd

echo Aguardando n8n ficar pronto...
set /a WAIT=0
:wait_n8n
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:5678/healthz' -UseBasicParsing -TimeoutSec 5; exit ([int]($r.StatusCode -ne 200)) } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 goto n8n_ready
timeout /t 5 /nobreak >nul
set /a WAIT+=5
if !WAIT! geq 90 goto n8n_ready
echo   ... !WAIT! s
goto wait_n8n
:n8n_ready

REM --- Iniciar FastAPI (uvicorn) em background ---
set "PYTHON=python"
if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" (
    set "PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"
)

netstat -ano 2>nul | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo FastAPI ja esta rodando na porta 8000.
) else (
    echo Iniciando FastAPI (uvicorn)...
    start "AI-Commerce-OS API" /MIN cmd /c "cd /d \"%PROJECT_ROOT%\" && \"%PYTHON%\" -m uvicorn api.main_api:app --host 127.0.0.1 --port 8000 --workers 1 --log-level info"
    timeout /t 2 /nobreak >nul
)

REM --- Abrir n8n no navegador ---
start "" "http://localhost:5678"

echo.
echo Projeto rodando! 🚀
echo.
echo   n8n:     http://localhost:5678
echo   FastAPI: http://127.0.0.1:8000
echo.
pause
