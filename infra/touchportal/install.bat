@echo off
REM Instala o painel Touch Portal (contorna ExecutionPolicy do PowerShell)
cd /d "%~dp0..\.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
