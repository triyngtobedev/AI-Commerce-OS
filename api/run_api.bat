@echo off
cd /d "%~dp0.."

echo Starting AI-Commerce-OS Pipeline API on 127.0.0.1:8000
python -m uvicorn api.main_api:app --host 127.0.0.1 --port 8000 --workers 1 --log-level info
