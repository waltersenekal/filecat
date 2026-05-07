#!/bin/bash
# FileCat - Setup virtual environment and install dependencies
# Venv stored in project .venv folder
cd "$(dirname "$0")"

export PATH="$HOME/.local/bin:$PATH"
VENV_DIR="$(pwd)/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment with Python 3.12 at $VENV_DIR..."
    uv venv "$VENV_DIR" --python 3.12
else
    echo "Virtual environment already exists at $VENV_DIR, skipping creation."
fi

echo "Installing dependencies..."
uv pip install --python "$VENV_DIR/bin/python" -r requirements.txt

# Install PyTorch (CPU for Linux testing; use setup.bat for CUDA on Windows)
echo "Installing PyTorch..."
uv pip install --python "$VENV_DIR/bin/python" torch torchvision

# Install RAM (recognize-anything) from GitHub
echo "Installing RAM (recognize-anything model)..."
uv pip install --python "$VENV_DIR/bin/python" "git+https://github.com/xinyu1205/recognize-anything.git"

# Patch RAM model for transformers compatibility
echo "Patching RAM for transformers compatibility..."
"$VENV_DIR/bin/python" patch_ram.py

echo ""
echo "Setup complete! Run ./start.sh to launch FileCat."

