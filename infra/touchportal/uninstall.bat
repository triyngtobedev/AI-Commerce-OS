@echo off
REM Remove plugin AI-Commerce-OS do Touch Portal (emergencia)
set "PLUGIN=%APPDATA%\TouchPortal\plugins\AI-Commerce-OS"
if exist "%PLUGIN%" (
    rmdir /s /q "%PLUGIN%"
    echo Plugin removido: %PLUGIN%
) else (
    echo Plugin nao encontrado.
)
echo Reinicie o Touch Portal.
pause
