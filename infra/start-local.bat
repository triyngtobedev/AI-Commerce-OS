@echo off
cd /d "%~dp0"

if not exist ".env.n8n" (
    echo Arquivo .env.n8n nao encontrado. Copie de .env.n8n.example e preencha os valores.
    exit /b 1
)

set "DOCKER=docker"
where docker >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\Docker\Docker\resources\bin\docker.exe" (
        set "DOCKER=C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    ) else (
        echo Docker nao encontrado. Abra o Docker Desktop e tente novamente.
        exit /b 1
    )
)

echo Subindo n8n (localhost:5678)...
"%DOCKER%" compose -f docker-compose.local.yml up -d

echo.
"%DOCKER%" compose -f docker-compose.local.yml ps
echo.
echo n8n: http://localhost:5678
echo Login: admin@local.dev + senha em infra\.env.n8n
echo.
echo Proximo passo (importar workflows automaticamente):
echo   cd %~dp0
echo   setup_n8n.bat
