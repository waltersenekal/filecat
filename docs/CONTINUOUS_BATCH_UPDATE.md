# Continuous Batch Processing - Auto-Tag Update
## What Changed
The background auto-tagging service now uses **continuous batch processing** for faster handling of large image collections.
## How It Works Now
### Before (Old Behavior)
- Process 50 images
- Wait 5 minutes
- Process next 50 images
- Wait 5 minutes
- Repeat...
**Problem:** If you had 500 images, it would take 50 minutes (10 batches × 5 minutes)
### After (New Behavior) ✅
- Process batch 1 (50 images)
- **Check if more images exist**
  - **Yes:** Start next batch immediately (no wait)
  - **No:** Wait 5 minutes, then scan for new files
- Repeat...
**Benefit:** 500 images now tagged in ~10 minutes (continuous processing), then waits
## Example Scenarios
### Scenario 1: Large Import (500 New Images)
**Timeline:**
```
00:00 - Scan finds 500 untagged images
00:00 - Batch 1: Tag 50 images (450 remain)
00:03 - Batch 2: Tag 50 images (400 remain) ← No wait!
00:06 - Batch 3: Tag 50 images (350 remain) ← No wait!
00:09 - Batch 4: Tag 50 images (300 remain) ← No wait!
...
00:27 - Batch 10: Tag 50 images (0 remain) ← No wait!
00:30 - ✅ All tagged! Wait 5 minutes...
00:35 - Scan for new files → None found
00:40 - Scan for new files → None found
```
**Total time:** ~30 minutes for 500 images (vs 50 minutes with old method)
### Scenario 2: Trickle of New Images
**Timeline:**
```
00:00 - Scan finds 0 untagged → Wait 5 minutes
00:05 - Scan finds 3 new images → Tag them → Wait 5 minutes
00:10 - Scan finds 0 untagged → Wait 5 minutes
00:15 - Scan finds 1 new image → Tag it → Wait 5 minutes
```
**Behavior:** Low overhead when caught up, responsive when new files arrive
### Scenario 3: Ongoing Addition During Processing
**Timeline:**
```
00:00 - Scan finds 100 untagged images
00:00 - Batch 1: Tag 50 images (50 remain)
00:03 - Batch 2: Tag 50 images (0 remain)
00:06 - ✅ All tagged! Wait 5 minutes...
[User adds 200 new images at 00:08]
00:11 - Scan finds 200 new images
00:11 - Batch 1: Tag 50 images (150 remain)
00:14 - Batch 2: Tag 50 images (100 remain) ← Continuous!
00:17 - Batch 3: Tag 50 images (50 remain)
00:20 - Batch 4: Tag 50 images (0 remain)
00:23 - ✅ All tagged! Wait 5 minutes...
```
## Console Output
### Continuous Processing
```
============================================================
[AUTO-TAG] Starting automatic scan and tag cycle at 2026-01-22 14:30:00
============================================================
[AUTO-TAG] Step 1: Scanning for new files...
[AUTO-TAG] Found 3 new file(s)
[AUTO-TAG] Step 2: Finding untagged images (batch #1)...
[AUTO-TAG] Found 150 total untagged, processing batch of 50
[AUTO-TAG] Step 3: AI tagging batch #1...
[AUTO-TAG]   Processing 1/50: image001.jpg
[AUTO-TAG]     ✓ Added 8 tags
...
[AUTO-TAG] Batch #1 complete: 50 images, 456 tags added
[AUTO-TAG] 📋 100 images still to tag, starting next batch immediately...
[AUTO-TAG] Step 2: Finding untagged images (batch #2)...
[AUTO-TAG] Found 100 total untagged, processing batch of 50
[AUTO-TAG] Step 3: AI tagging batch #2...
[AUTO-TAG]   Processing 1/50: image051.jpg
[AUTO-TAG]     ✓ Added 9 tags
...
[AUTO-TAG] Batch #2 complete: 50 images, 478 tags added
[AUTO-TAG] 📋 50 images still to tag, starting next batch immediately...
[AUTO-TAG] Step 2: Finding untagged images (batch #3)...
[AUTO-TAG] Found 50 total untagged, processing batch of 50
[AUTO-TAG] Step 3: AI tagging batch #3...
[AUTO-TAG]   Processing 1/50: image101.jpg
[AUTO-TAG]     ✓ Added 7 tags
...
[AUTO-TAG] Batch #3 complete: 50 images, 412 tags added
[AUTO-TAG] No more untagged images to process
[AUTO-TAG] ✅ All images tagged!
[AUTO-TAG] Run complete: 3 batch(es), 150 images, 1346 tags
============================================================
[AUTO-TAG] All caught up. Next scan in 5.0 minutes...
```
## Performance Comparison
### Processing 500 Images
| Method | Time | Batches | Wait Periods |
|--------|------|---------|--------------|
| **Old (Fixed Intervals)** | 50 minutes | 10 | 9 × 5 min waits |
| **New (Continuous)** | 30 minutes | 10 | 0 waits during processing |
### Processing 50 Images
| Method | Time | Batches | Wait Periods |
|--------|------|---------|--------------|
| **Old** | 3 minutes | 1 | 0 (fits in one batch) |
| **New** | 3 minutes | 1 | 0 (fits in one batch) |
**Conclusion:** Same speed for small batches, much faster for large imports!
## Benefits
### Speed
✅ **2x faster** for large imports  
✅ **Same speed** for small daily additions  
✅ **No unnecessary waits** when work is available
### Efficiency
✅ **Lower CPU usage** when idle  
✅ **Responsive** to new content  
✅ **Smart scheduling** - work hard when needed, rest when done
### User Experience
✅ **Faster onboarding** - bulk imports complete quickly  
✅ **Always current** - new files tagged within 5 minutes  
✅ **Predictable** - clear console output shows progress
## Configuration
No changes needed! The existing settings work perfectly:
```python
AUTO_TAG_ENABLED = True
AUTO_TAG_INTERVAL = 300      # Wait time when all caught up
AUTO_TAG_BATCH_SIZE = 50     # Images per batch
```
**To process faster:**
- Increase `AUTO_TAG_BATCH_SIZE` to 100 (fewer total batches)
- Decrease `AUTO_TAG_INTERVAL` to check more frequently when idle
**To be gentler on system:**
- Decrease `AUTO_TAG_BATCH_SIZE` to 25 (smaller chunks)
- Increase `AUTO_TAG_INTERVAL` to reduce scan frequency
## Technical Details
### Logic Flow
```python
while service_running:
    scan_for_new_files()
    while untagged_images_exist():
        batch = get_next_batch(50)
        process_batch(batch)
        # No sleep here - check immediately for more
    # All caught up
    sleep(5_minutes)
```
### Key Change
**Before:** Sleep after each batch  
**After:** Only sleep when queue is empty
### Thread Safety
- Background thread runs continuously
- Database operations are atomic
- Safe to use UI while processing
- Can stop service anytime
---
**Status:** ✅ Implemented  
**Version:** Enhanced Phase 2  
**Date:** January 22, 2026  
**Feature:** Continuous batch processing for auto-tagging
