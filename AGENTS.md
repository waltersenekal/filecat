# AGENTS.md

## Project Overview
FileCat is a Flask web app for cataloging, tagging, and searching images stored in a local `Digital Papers/` folder. SQLite database at `data/filecat.db`. AI auto-tagging uses STAG/RAM model via a background threading service.

## Architecture
- **`app.py`** — Single-file Flask app with all routes and API endpoints. Background tasks (AI tagging, thumbnail regen, downloads) run in `threading.Thread` with progress tracked via module-level dicts and SSE streams.
- **`database.py`** — All SQLite operations. Uses `sqlite3.Row` for dict-like access. Every function opens/closes its own connection (no shared connection). 30s timeout for lock avoidance.
- **`ai_tagger.py`** — Lazy-loads RAM Plus model on first call. Requires external `stag` repo on `STAG_PATH`. Thread-safe via `_model_lock`.
- **`scanner.py`** — Walks `SOURCE_FOLDER`, registers new images in DB, generates thumbnails.
- **`file_integrity.py`** — Validates images on disk vs DB records, handles corrupted/missing files.
- **`config.py`** — All constants imported via `from config import *`. Change settings here, not in app.py.

## Database Schema (5 tables)
`images` (filepath, filename, file_size, is_tagged, integrity_status) → `image_tags` ← `tags` (tag_name, usage_count). Also: `settings` (key/value), `ai_suggestions` (image_id, tag_name, confidence, status=pending/accepted/rejected).

## Key Patterns
- **Wildcard imports**: `from config import *` and `from database import *` are used in `app.py`. New config values or DB functions are automatically available.
- **Tags are lowercase**: All tag input is normalized via `t.strip().lower()` before storage.
- **AI processing marks completion**: `save_ai_suggestions(image_id, [])` with empty list marks an image as "processed" to prevent infinite retry loops in background auto-tagging.
- **Background auto-tag only runs in main Werkzeug process**: Checked via `os.environ.get('WERKZEUG_RUN_MAIN') == 'true'` to avoid duplicate threads from Flask reloader.
- **SSE for progress**: Thumbnail regen, AI batch analysis, and downloads stream progress via `text/event-stream` responses.

## Running
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python init_db.py   # first time only
python app.py       # starts on 0.0.0.0:5000, debug=True
```
Images go in `Digital Papers/` directory relative to project root.

## Testing
No test framework configured. Test files (`test_ai_tagger.py`, `test_file_integrity.py`, `tag_test.py`) are standalone scripts run directly with `python <file>`.

## File Conventions
- Templates in `templates/` extend `base.html` (includes dark mode toggle, keyboard shortcuts).
- Static assets in `static/css/` and `static/img/`.
- Utility scripts in `scripts/` are one-off maintenance tools, not part of the app runtime.
- Many `.md` files document specific fixes/features — check them before modifying related code.

