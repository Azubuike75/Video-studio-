@echo off
cd /d "%~dp0"

if not exist venv (
    echo Setting up virtual environment (first run only)...
    python -m venv venv
    venv\Scripts\pip install --upgrade pip
    venv\Scripts\pip install -r requirements.txt
)

venv\Scripts\python app.py
pause
