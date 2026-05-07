@echo off
REM FileCat - Setup virtual environment and install dependencies
REM Venv stored in %USERPROFILE%\.venvs\filecat

cd /d "%~dp0"
set "VENV_DIR=%USERPROFILE%\.venvs\filecat"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"
set "UV_LINK_MODE=copy"

where uv >nul 2>nul
if errorlevel 1 (
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo Please restart this script after uv is installed.
    pause
    exit /b
)

if not exist "%PYTHON%" (
    echo Creating virtual environment at %VENV_DIR% with Python 3.12...
    uv venv "%VENV_DIR%" --python 3.12
) else (
    echo Virtual environment already exists at %VENV_DIR%, skipping creation.
)

echo Installing/updating FileCat dependencies...
uv pip install --upgrade --python "%PYTHON%" -r requirements.txt

echo Installing/updating transformers for compatibility ^(MUST be less than 5 for STAG^)...
uv pip install --upgrade --python "%PYTHON%" "transformers<5"

echo Installing/updating STAG dependencies...
uv pip install --upgrade --python "%PYTHON%" -r stag\requirements.txt

echo Re-locking transformers to less than 5 ^(STAG may have pulled newer version^)...
uv pip install --upgrade --python "%PYTHON%" "transformers<5" --force-reinstall

echo Installing PyTorch with CUDA support...
uv pip install --upgrade --python "%PYTHON%" torch torchvision --index-url https://download.pytorch.org/whl/cu121

echo Installing/updating RAM (recognize-anything) package...
where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: git is not installed. Please install Git for Windows from https://git-scm.com/download/win
    echo Then re-run this script.
    pause
    exit /b
)
uv pip install --upgrade --python "%PYTHON%" git+https://github.com/xinyu1205/recognize-anything.git

echo.
echo Setup complete! Run start.bat to launch FileCat.
pause
