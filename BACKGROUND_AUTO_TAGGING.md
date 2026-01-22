# Background Auto-Tagging Feature
## Overview
FileCat now includes a **background auto-tagging service** that automatically scans for new images and tags them with AI without any user intervention.
---
## How It Works
### Automatic Process
1. **Background Service Starts** when Flask app launches
2. **Every 5 minutes** (configurable), the service:
   - Scans the source folder for new image files
   - Finds untagged images (up to 50 per cycle)
   - Analyzes each image with STAG/RAM AI
   - Automatically adds suggested tags
   - Marks images as tagged
3. **Runs Continuously** in the background
4. **No User Action Required** - fully automatic
### Manual Control
You can also:
- **Start/Stop** the background service manually
- **Trigger immediate** scan and tag cycle
- **View statistics** (images processed, tags added, errors)
- **Monitor progress** in real-time
---
## Configuration
### Settings in `config.py`
```python
# AI Auto-Tagging Background Settings
AUTO_TAG_ENABLED = True  # Enable/disable automatic background tagging
AUTO_TAG_INTERVAL = 300  # Check every 5 minutes (300 seconds)
AUTO_TAG_ON_STARTUP = True  # Run one cycle when app starts
AUTO_TAG_BATCH_SIZE = 50  # Process max 50 images per cycle
```
### Adjusting Settings
**Change Check Interval:**
```python
AUTO_TAG_INTERVAL = 600  # Every 10 minutes
AUTO_TAG_INTERVAL = 1800  # Every 30 minutes
AUTO_TAG_INTERVAL = 3600  # Every hour
```
**Change Batch Size:**
```python
AUTO_TAG_BATCH_SIZE = 25  # Smaller batches (faster cycles)
AUTO_TAG_BATCH_SIZE = 100  # Larger batches (fewer cycles)
```
**Disable Auto-Tagging:**
```python
AUTO_TAG_ENABLED = False  # Turn off background service
```
---
## Usage
### Via Settings Page UI
**Location:** Settings → AI Auto-Tagging → Background Auto-Tagging section
**Features:**
- **Status Display:**
  - Current status (Active/Stopped/Running)
  - Images processed count
  - Tags added count
  - Last run time
  - Next run time
  - Error count
- **Controls:**
  - **Start Service** - Start the background service
  - **Stop Service** - Stop the background service
  - **Run Now** - Trigger immediate cycle (doesn't wait for interval)
### Via API Endpoints
**Get Status:**
```bash
curl http://localhost:5000/api/ai/auto-tag/stats
```
**Start Service:**
```bash
curl -X POST http://localhost:5000/api/ai/auto-tag/start
```
**Stop Service:**
```bash
curl -X POST http://localhost:5000/api/ai/auto-tag/stop
```
**Trigger Immediate Run:**
```bash
curl -X POST http://localhost:5000/api/ai/auto-tag/trigger
```
---
## Console Output
### Service Start
```
============================================================
[AUTO-TAG] Auto-tagging is ENABLED
[AUTO-TAG] Interval: 300 seconds (5.0 minutes)
[AUTO-TAG] Batch size: 50 images per cycle
[AUTO-TAG] Starting background service...
============================================================
[AUTO-TAG] Background auto-tagging service started
```
### Automatic Cycle
```
============================================================
[AUTO-TAG] Starting automatic scan and tag cycle at 2026-01-22 14:30:00
============================================================
[AUTO-TAG] Step 1: Scanning for new files...
[AUTO-TAG] Found 3 new file(s)
[AUTO-TAG] Step 2: Finding untagged images...
[AUTO-TAG] Found 25 untagged images, processing 25 this cycle
[AUTO-TAG] Step 3: AI tagging 25 images...
[AUTO-TAG]   Processing 1/25: beach_sunset.jpg
[AUTO-TAG]     ✓ Added 8 tags
[AUTO-TAG]   Processing 2/25: mountain_view.jpg
[AUTO-TAG]     ✓ Added 10 tags
...
[AUTO-TAG] Cycle complete: 25 images processed, 234 tags added
============================================================
```
---
## Workflow Examples
### Typical Workflow
1. **Setup Once:**
   - Configure settings in `config.py`
   - Start Flask app
   - Background service starts automatically
2. **Add New Images:**
   - Copy images to `Digital Papers` folder
   - Wait up to 5 minutes (or trigger manually)
   - Images are automatically scanned and tagged
3. **Review Results:**
   - Go to Search → Filter by "Tagged"
   - See newly tagged images with AI-generated tags
   - Edit/refine tags if needed
### Large Import Workflow
**Scenario:** You copy 500 new images to the folder
**What Happens:**
1. **First cycle (5 min):** Scans folder, finds 500 new images, tags 50
2. **Second cycle (10 min):** Tags next 50 images (100 total)
3. **Third cycle (15 min):** Tags next 50 images (150 total)
4. **...**
5. **Tenth cycle (50 min):** All 500 images tagged
**To Speed Up:**
- Click "Run Now" button to trigger cycles immediately
- Or increase `AUTO_TAG_BATCH_SIZE` to 100 or more
- Or use manual "Analyze All Images Now" for one-time bulk processing
---
## Benefits
### Fully Automatic
✅ No need to remember to tag new images  
✅ No manual triggering required  
✅ Runs in background while you work  
✅ Always up-to-date
### Incremental Processing
✅ Processes images in small batches  
✅ Doesn't overload system  
✅ Can stop/start anytime  
✅ Resumes where it left off
### Flexible Control
✅ Enable/disable in config  
✅ Start/stop via UI  
✅ Trigger on-demand  
✅ Adjust interval and batch size
### Monitoring
✅ Real-time status display  
✅ Console logging  
✅ Statistics tracking  
✅ Error reporting
---
## Technical Details
### Threading Model
- **Main Thread:** Flask web server
- **Background Thread:** Auto-tag service (daemon thread)
- **Worker Threads:** Individual analysis tasks
### Resource Usage
- **CPU:** 2-4 seconds per image (during AI inference)
- **Memory:** ~2GB for AI model (loaded once, cached)
- **Disk I/O:** Minimal (reads images, writes to database)
### Startup Behavior
1. Flask app starts
2. Database initialized (if needed)
3. Background service thread launched
4. Optional: Initial scan/tag cycle runs after 5 seconds
5. Normal operation: Cycles every 5 minutes
### Shutdown Behavior
1. Stop signal received (Ctrl+C or app exit)
2. Background service thread notified
3. Current cycle completes (if running)
4. Service stops gracefully
5. App exits
---
## Troubleshooting
### Service Not Starting
**Check console:**
```
[AUTO-TAG] Auto-tagging is DISABLED
```
**Solution:** Set `AUTO_TAG_ENABLED = True` in `config.py`
### No Images Being Processed
**Check:**
1. Are there untagged images? (Settings → AI Info)
2. Is service active? (Settings → Background Auto-Tagging)
3. Check console for errors
### Service Crashes
**Console shows:**
```
[AUTO-TAG] ❌ Background task error: ...
```
**Solutions:**
- Check AI model is installed
- Verify sufficient memory (~2GB)
- Check file permissions
- Review error traceback
### Too Slow
**Current:** Processing 50 images every 5 minutes
**Speed up:**
1. Increase batch size: `AUTO_TAG_BATCH_SIZE = 100`
2. Decrease interval: `AUTO_TAG_INTERVAL = 60` (1 minute)
3. Use manual batch for one-time imports
4. Consider GPU if available (10x faster)
### Too Aggressive
**Current:** Checking every 5 minutes, high CPU usage
**Slow down:**
1. Decrease batch size: `AUTO_TAG_BATCH_SIZE = 25`
2. Increase interval: `AUTO_TAG_INTERVAL = 1800` (30 minutes)
3. Disable startup run: `AUTO_TAG_ON_STARTUP = False`
---
## API Reference
### GET `/api/ai/auto-tag/stats`
Returns current statistics:
```json
{
  "enabled": true,
  "is_running": false,
  "last_run": "2026-01-22T14:30:00",
  "next_run": "2026-01-22T14:35:00",
  "images_processed": 250,
  "tags_added": 2340,
  "errors": 2
}
```
### POST `/api/ai/auto-tag/start`
Start the background service:
```json
{
  "success": true,
  "message": "Auto-tagging service started"
}
```
### POST `/api/ai/auto-tag/stop`
Stop the background service:
```json
{
  "success": true,
  "message": "Auto-tagging service stopped"
}
```
### POST `/api/ai/auto-tag/trigger`
Run one cycle immediately:
```json
{
  "success": true,
  "message": "Manual auto-tag cycle started"
}
```
---
## Files Modified
✅ `config.py` - Added auto-tag configuration  
✅ `app.py` - Added background service and API endpoints  
✅ `templates/settings.html` - Added UI controls and status display  
---
## Comparison: Manual vs Background
| Feature | Manual Batch | Background Auto-Tag |
|---------|--------------|---------------------|
| **Trigger** | User clicks button | Automatic every 5 min |
| **Processing** | All images at once | Incremental batches |
| **User Action** | Required | None |
| **Best For** | One-time bulk import | Ongoing daily use |
| **CPU Impact** | High (short burst) | Low (spread over time) |
| **Monitoring** | Progress bar | Statistics display |
**Recommendation:** Use both!
- **Background:** For daily automatic tagging
- **Manual:** For large one-time imports
---
**Status:** ✅ Implemented and ready to use  
**Version:** Phase 2  
**Date:** January 22, 2026  
**Feature:** Fully automatic background AI tagging
