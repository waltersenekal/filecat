@echo off
REM FileCat - Start the application and open in browser

cd /d "%~dp0"
set VENV_DIR=%~dp0.venv
set PYTHON=%VENV_DIR%\Scripts\python.exe

REM Verify venv exists
if not exist "%PYTHON%" (
    echo ERROR: Virtual environment not found at %VENV_DIR%
    echo Please run setup.bat first.
    pause
    exit /b
)

REM Clear bytecode cache to avoid stale imports
if exist "__pycache__" rmdir /s /q "__pycache__"

REM Initialize database if needed
if not exist "data\filecat.db" (
    echo Initializing database...
    "%PYTHON%" init_db.py
)

echo Starting FileCat on http://localhost:5000
start "" http://localhost:5000

"%PYTHON%" -u app.py
