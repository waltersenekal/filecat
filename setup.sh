#!/bin/bash
# FileCat - Setup virtual environment and install dependencies
# Venv stored in ~/.venvs/filecat
cd "$(dirname "$0")"

export PATH="$HOME/.local/bin:$PATH"
VENV_DIR="$HOME/.venvs/filecat"
mkdir -p "$(dirname "$VENV_DIR")"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment with Python 3.12 at $VENV_DIR..."
    uv venv "$VENV_DIR" --python 3.12
else
    echo "Virtual environment already exists at $VENV_DIR, skipping creation."
fi

PYTHON="$VENV_DIR/bin/python"

echo "Installing/updating FileCat dependencies..."
uv pip install --upgrade --python "$PYTHON" -r requirements.txt

echo "Installing/updating transformers for compatibility (MUST be < 5 for STAG)..."
uv pip install --upgrade --python "$PYTHON" "transformers<5"

echo "Installing/updating STAG dependencies..."
uv pip install --upgrade --python "$PYTHON" -r stag/requirements.txt

echo "Re-locking transformers to <5 (STAG may have pulled newer version)..."
uv pip install --upgrade --python "$PYTHON" "transformers<5" --force-reinstall

echo "Installing/updating PyTorch (CPU)..."
uv pip install --upgrade --python "$PYTHON" torch torchvision

echo "Installing/updating RAM (recognize-anything) package..."
uv pip install --upgrade --python "$PYTHON" "git+https://github.com/xinyu1205/recognize-anything.git"

echo ""
echo "Setup complete! Run ./start.sh to launch FileCat."

