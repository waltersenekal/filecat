#!/bin/bash
# FileCat - Start the application and open in browser

cd "$(dirname "$0")"

VENV_DIR="$HOME/.venvs/filecat"
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "ERROR: Virtual environment not found at $VENV_DIR"
    echo "Run ./setup.sh first."
    exit 1
fi

source "$VENV_DIR/bin/activate"

# Initialize database if needed
if [ ! -f "data/filecat.db" ]; then
    echo "Initializing database..."
    python init_db.py
fi

PORT=5000
PID_LIST=""
if command -v lsof >/dev/null 2>&1; then
    PID_LIST=$(lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
elif command -v ss >/dev/null 2>&1; then
    PID_LIST=$(ss -ltnp 2>/dev/null | awk -v port=":$PORT" '$4 ~ port {gsub(/.*pid=/,"",$7); gsub(/,.*/,"",$7); print $7}')
fi

if [ -n "$PID_LIST" ]; then
    echo "Port $PORT is in use by process(es): $PID_LIST"
    echo "Stopping process(es) using port $PORT..."
    for PID in $PID_LIST; do
        if [ "$PID" != "" ]; then
            kill "$PID" 2>/dev/null || true
        fi
    done
    sleep 1
    # Force kill if still present
    if command -v lsof >/dev/null 2>&1; then
        PID_LIST=$(lsof -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
    elif command -v ss >/dev/null 2>&1; then
        PID_LIST=$(ss -ltnp 2>/dev/null | awk -v port=":$PORT" '$4 ~ port {gsub(/.*pid=/,"",$7); gsub(/,.*/,"",$7); print $7}')
    fi
    if [ -n "$PID_LIST" ]; then
        echo "Force killing remaining process(es): $PID_LIST"
        for PID in $PID_LIST; do
            if [ "$PID" != "" ]; then
                kill -9 "$PID" 2>/dev/null || true
            fi
        done
    fi
fi

echo "Starting FileCat on http://localhost:$PORT"
xdg-open "http://localhost:$PORT" 2>/dev/null || open "http://localhost:$PORT" 2>/dev/null &

python -u app.py

