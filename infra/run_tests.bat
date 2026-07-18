@echo off
cd /d "%~dp0.."
if not exist "run_tests.py" (
    echo.
    echo ERRO: run_tests.py nao encontrado em %CD%
    echo Faca git pull na branch cursor/lofi-dark-template-1dee
    exit /b 1
)
python run_tests.py %*
