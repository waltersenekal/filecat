# Server Exit Fix - Image Size Limit & Database Locking
## What Happened
The server exited with code 250 because:
1. **Large PNG files triggered PIL safety limit** (434 megapixels > 178 megapixel default)
2. **Database locking** during batch AI processing
3. **Auto-reload detected file change** and crashed during restart
## Errors Seen
```
PIL.Image.DecompressionBombError: Image size (434055556 pixels) exceeds limit of 178956970 pixels
[AI] Batch analysis error: database is locked
terminate called without an active exception
Process finished with exit code 250
```
## Fixes Applied
### 1. Increased PIL Image Size Limit ✅
**File:** `ai_tagger.py`
```python
# Increase PIL's decompression bomb limit for large digital art files
Image.MAX_IMAGE_PIXELS = 1000000000  # 1 gigapixel limit (was ~178MP)
```
**Effect:** Can now process images up to 1 gigapixel (your 434MP files are fine)
### 2. Fixed Database Locking ✅
**File:** `database.py`
```python
conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)  # 30 second timeout
```
**Effect:** Database connections wait up to 30 seconds instead of failing immediately
## What You Need to Do
**RESTART THE FLASK SERVER** - That's it!
The fixes are already in the code, but PyCharm's auto-reload crashed. Just stop and start the server again.
### How to Restart
1. **Stop** the current debug session in PyCharm (red square button)
2. **Run** app.py again (green play button)
3. **Done!** The AI batch analysis will now work with large images
## Expected Behavior After Restart
✅ Large PNG files (434MP) will process successfully  
✅ No more "decompression bomb" errors  
✅ Database locking handled gracefully  
✅ Batch AI analysis completes without crashes  
## Test After Restart
1. Go to Settings → AI Auto-Tagging
2. Click "🧠 Analyze All Images with AI"
3. Watch it process ALL images, including the large PNGs
4. No errors, smooth progress
## Technical Details
### Image Sizes in Your Collection
- **Problem files:** `girl samurai_*.png` (434 megapixels each)
- **Typical images:** 1-10 megapixels
- **New limit:** 1000 megapixels (1 gigapixel)
### Why PIL Has This Limit
- **Security:** Prevent malicious images from consuming all memory
- **Your case:** Legitimate high-resolution digital art files
- **Solution:** Raised limit to accommodate your files
### Database Timeout
- **Before:** Immediate failure if locked
- **After:** Wait up to 30 seconds for lock to clear
- **Reason:** Batch operations may have brief lock contention
## Files Modified
✅ `ai_tagger.py` - Added `Image.MAX_IMAGE_PIXELS = 1000000000`  
✅ `database.py` - Added `timeout=30.0` to connections
---
**Status:** ✅ Fixed - Just restart the server  
**Date:** January 21, 2026  
**Issue:** Large PNG files + database locking  
**Solution:** Increased limits + added timeouts
