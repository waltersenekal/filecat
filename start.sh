#!/bin/bash
# FileCat - Start the application and open in browser

cd "$(dirname "$0")"

VENV_DIR="$(pwd)/.venv"
source "$VENV_DIR/bin/activate"

# Initialize database if needed
if [ ! -f "data/filecat.db" ]; then
    echo "Initializing database..."
    python init_db.py
fi

echo "Starting FileCat on http://localhost:5000"
xdg-open http://localhost:5000 2>/dev/null || open http://localhost:5000 2>/dev/null &

python -u app.py

