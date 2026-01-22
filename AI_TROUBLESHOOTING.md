# AI Auto-Tagging Troubleshooting Guide

## Problem: Getting 0 Suggestions

If the AI is analyzing images but returning "Found 0 suggestions", try these solutions:

### Solution 1: Lower the Threshold (RECOMMENDED)
The default threshold has been set to 15% (0.15). If you still get 0 suggestions:

**Edit `ai_tagger.py`:**
```python
# Find the analyze_image function
def analyze_image(image_path, tag_candidates=None, threshold=0.10, max_tags=10):
    # Change threshold from 0.15 to 0.10 (10%)
```

**Also update `app.py`:**
```python
# Find both occurrences and change:
threshold=0.10  # Lower threshold for better results (10%)
```

### Solution 2: Add More Relevant Tag Candidates

If your images are specialized (e.g., technical diagrams, digital art), add custom tags:

**Edit `ai_tagger.py` - Add to `DEFAULT_TAG_CANDIDATES`:**
```python
DEFAULT_TAG_CANDIDATES = [
    # ...existing tags...
    
    # Add your custom categories
    "document", "diagram", "chart", "graph", "screenshot",
    "digital", "graphic design", "vector", "pattern",
    "texture", "wallpaper", "background",
    # Add more relevant to your collection
]
```

### Solution 3: Check Image Quality

CLIP works best with:
- ✅ Clear, well-lit photos
- ✅ Standard JPG/PNG images
- ✅ Images with recognizable subjects
- ❌ Very abstract images
- ❌ Heavily compressed images
- ❌ Pure text documents

### Solution 4: Test with Different Images

Try analyzing a simple test image:
```python
cd /home/walter/dev/FileCat
python -c "
from ai_tagger import analyze_image
import os

# Find any image in your collection
test_image = 'Digital Papers/2025 Sune Labels 9C.docx'  # Replace with actual image
if os.path.exists(test_image):
    results = analyze_image(test_image, threshold=0.10, max_tags=10)
    print(f'Found {len(results)} tags:')
    for tag, conf in results:
        print(f'  {tag}: {conf:.2%}')
else:
    print('Image not found')
"
```

### Solution 5: Check Model Loading

Verify the CLIP model loaded correctly:
```python
cd /home/walter/dev/FileCat
python -c "
from ai_tagger import get_model
try:
    model, processor = get_model()
    print('✅ Model loaded successfully!')
    print(f'Model type: {type(model)}')
    print(f'Processor type: {type(processor)}')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

### Solution 6: Restart the Server

After making changes:
```bash
# Kill the server
pkill -f "python.*app.py"

# Restart
cd /home/walter/dev/FileCat
python app.py
```

### Solution 7: Verbose Logging

Add debug output to see what's happening:

**Edit `ai_tagger.py` in the `analyze_image` function:**
```python
# After getting probs, add:
print(f"[DEBUG] Top 10 scores:")
for idx in range(min(10, len(probs))):
    print(f"  {tag_candidates[idx]}: {probs[idx].item():.4f}")
```

This will show the actual confidence scores in the console.

## Expected Behavior

### Good Results
```
Found 8 suggestions
outdoor (0.45)      # 45% confidence
nature (0.32)       # 32% confidence
landscape (0.28)    # 28% confidence
trees (0.22)        # 22% confidence
sky (0.19)          # 19% confidence
beautiful (0.17)    # 17% confidence
photo (0.16)        # 16% confidence
colorful (0.15)     # 15% confidence
```

### Low Confidence (but still useful)
```
Found 3 suggestions
art (0.18)          # 18% confidence
digital art (0.14)  # 14% confidence
modern (0.12)       # 12% confidence
```

### Zero Suggestions (needs adjustment)
```
Found 0 suggestions
Click "Analyze with AI" to get suggestions
```
**Action:** Lower threshold to 0.10 or add relevant tag candidates

## Current Configuration

**Default Settings:**
- Threshold: 0.15 (15%)
- Max suggestions: 8
- Tag candidates: 60+ categories
- Model: CLIP ViT-B/32

**Recommended for Digital Art/Graphics:**
- Threshold: 0.10 (10%)
- Add custom tags: "digital", "graphic design", "pattern", "vector", "illustration"

**Recommended for Photos:**
- Threshold: 0.15 (15%)
- Default tag candidates work well

**Recommended for Documents:**
- Threshold: 0.10 (10%)
- Add custom tags: "document", "text", "scan", "page", "paper"

## Quick Fix Commands

### Test Current Setup
```bash
cd /home/walter/dev/FileCat
python ai_tagger.py
# Enter a test image path when prompted
```

### Lower Threshold Globally
```bash
cd /home/walter/dev/FileCat
# Backup first
cp ai_tagger.py ai_tagger.py.backup
cp app.py app.py.backup

# Edit files (change 0.15 to 0.10)
sed -i 's/threshold=0.15/threshold=0.10/g' ai_tagger.py
sed -i 's/threshold=0.15/threshold=0.10/g' app.py

# Restart server
pkill -f "python.*app.py"
python app.py
```

## Still Not Working?

1. **Check the console output** when analyzing - look for errors
2. **Try with a simple photo** (e.g., outdoor scene, portrait)
3. **Verify image file is valid** (open it in an image viewer)
4. **Check file path** is correct and accessible
5. **Review server logs** for any Python errors

## Contact/Support

If issues persist:
1. Check server console for error messages
2. Look at browser console (F12) for JavaScript errors
3. Verify PyTorch and Transformers are installed correctly:
   ```bash
   pip list | grep -E "torch|transformers"
   ```

---

**Last Updated:** January 21, 2026  
**Current Threshold:** 0.15 (15%)  
**Recommended Action:** If getting 0 suggestions, lower to 0.10
