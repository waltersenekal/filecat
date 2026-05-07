@echo off
REM FileCat - Setup virtual environment and install dependencies
REM Venv stored in project .venv folder
REM Run this once, or again to update packages (won't recreate .venv)

cd /d "%~dp0"
set UV_LINK_MODE=copy
set VENV_DIR=%~dp0.venv

where uv >nul 2>nul
if errorlevel 1 (
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    echo Please restart this script after uv is installed.
    pause
    exit /b
)

if not exist "%VENV_DIR%" (
    echo Creating virtual environment at %VENV_DIR% with Python 3.12...
    uv venv "%VENV_DIR%" --python 3.12
) else (
    echo Virtual environment already exists at %VENV_DIR%, skipping creation.
)

echo Installing dependencies...
uv pip install --python "%VENV_DIR%\Scripts\python.exe" -r requirements.txt

REM Install PyTorch with CUDA support for NVIDIA GPU
echo Installing PyTorch with CUDA support...
uv pip install --python "%VENV_DIR%\Scripts\python.exe" torch torchvision --index-url https://download.pytorch.org/whl/cu121

REM Install RAM (recognize-anything) from GitHub - requires git
echo Installing RAM (recognize-anything model)...
where git >nul 2>nul
if errorlevel 1 (
    echo ERROR: git is not installed. Please install Git for Windows from https://git-scm.com/download/win
    echo Then re-run this script.
    pause
    exit /b
)
uv pip install --python "%VENV_DIR%\Scripts\python.exe" git+https://github.com/xinyu1205/recognize-anything.git

REM Patch RAM model for transformers compatibility
echo Patching RAM for transformers compatibility...
"%VENV_DIR%\Scripts\python.exe" patch_ram.py

echo.
echo Setup complete! Run start.bat to launch FileCat.
pause
