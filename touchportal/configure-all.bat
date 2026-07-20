@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0configure-all.ps1" %*
pause
