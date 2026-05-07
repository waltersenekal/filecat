@echo off
REM FileCat - Start the application and open in browser

cd /d "%~dp0"
set "VENV_DIR=%USERPROFILE%\.venvs\filecat"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"

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

set "PORT=5000"
set "PID_LIST="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    set "PID_LIST=%%p"
    call :KILLPID %%p
)
if not defined PID_LIST (
    echo Port %PORT% is free.
)

echo Starting FileCat on http://localhost:%PORT%
start "" http://localhost:%PORT%

"%PYTHON%" -u app.py

exit /b

:KILLPID
    echo Port %PORT% is in use by process %1
    echo Stopping process %1 using port %PORT%...
    taskkill /PID %1 /F >nul 2>&1
    goto :eof
