@echo off
REM Repara icones dos botoes Touch Portal (feche o Touch Portal antes)
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0repair-icons.ps1"
pause
