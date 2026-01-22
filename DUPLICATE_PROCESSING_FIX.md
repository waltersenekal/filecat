# Duplicate Processing Fix
## Problem Identified
Your logs showed **duplicate processing** of the same images:
```
[AUTO-TAG]   Processing 35/50: UNICORN-CUPCAKE-01.png
[AUTO-TAG]     ✓ Added 0 tags
[AUTO-TAG]   Processing 36/50: UNICORN-CUPCAKE-01.png  ← DUPLICATE!
[AUTO-TAG]     ✓ Added 10 tags
```
## Root Cause
**Flask's debug mode reloader** was starting the background service **twice**:
1. **First process (main):** Starts background thread
2. **Second process (reloader):** Starts ANOTHER background thread
3. **Result:** Two threads processing the same batch simultaneously
This is a known Flask behavior when `debug=True` - it runs your code twice.
## The Fix
Added check to only start background service in the **main process**:
```python
# Only start in main process (not reloader)
if AUTO_TAG_ENABLED and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    start_auto_tag_service()
elif AUTO_TAG_ENABLED:
    print("[AUTO-TAG] Skipping background service in reloader process")
```
**How it works:**
- Flask sets `WERKZEUG_RUN_MAIN='true'` ONLY in the main process
- Reloader process doesn't have this env var
- Background service only starts once
## Expected Behavior After Fix
**Before (Duplicate Processing):**
```
[AUTO-TAG]   Processing 35/50: image.png
[AUTO-TAG]     ✓ Added 0 tags
[AUTO-TAG]   Processing 36/50: image.png  ← Duplicate!
[AUTO-TAG]     ✓ Added 10 tags
```
**After (Single Processing):**
```
[AUTO-TAG]   Processing 35/50: image.png
[AUTO-TAG]     ✓ Added 10 tags
[AUTO-TAG]   Processing 36/50: next_image.png  ← Different image!
[AUTO-TAG]     ✓ Added 8 tags
```
## Why "Added 0 tags" on First Pass
When two threads process the same image:
1. **Thread 1:** Gets existing tags (none) → AI suggests 10 tags → Tries to add them
2. **Thread 2:** Gets existing tags (none) → AI suggests 10 tags → Tries to add them
3. **Race condition:** One thread adds tags first, other sees "already exists" → 0 tags added
## Console Output After Fix
**On Startup:**
```
Starting FileCat on http://0.0.0.0:5000
Source folder: /home/walter/dev/FileCat/Digital Papers
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Restarting with stat
[AUTO-TAG] Skipping background service in reloader process (prevents duplicates)
Starting FileCat on http://0.0.0.0:5000
Source folder: /home/walter/dev/FileCat/Digital Papers
 * Debugger is active!
============================================================
[AUTO-TAG] Auto-tagging is ENABLED
[AUTO-TAG] Interval: 300 seconds (5.0 minutes)
[AUTO-TAG] Batch size: 50 images per cycle
[AUTO-TAG] Starting background service...
============================================================
[AUTO-TAG] Background auto-tagging service started
```
**Key indicator:** You'll see "Skipping background service in reloader process" on the first startup, then the actual service starts on the second (main) process.
## Testing
After restarting:
1. **Check console** - Should see "Skipping... in reloader process" once
2. **Monitor processing** - Each image should appear only once
3. **Check tag counts** - Should be consistent (not 0 then X)
4. **Watch batch numbers** - Should increment properly (35, 36, 37... not 35, 36, 36...)
## Alternative: Disable Debug Mode
If you don't need debug features, you can also:
```python
# In config.py
DEBUG = False
```
This prevents the reloader entirely, but you lose:
- Auto-reload on code changes
- Better error pages
- Interactive debugger
**Recommendation:** Keep debug mode, use the fix above.
---
**Status:** ✅ Fixed  
**File Modified:** `app.py`  
**Restart Required:** Yes  
**Date:** January 22, 2026
