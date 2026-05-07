# Favicon and Icon Setup
## Quick Setup Instructions
### Step 1: Prepare Your Icon
You have a 512x512 icon.png. We need to create multiple sizes for best browser compatibility:
**Place your icon.png in:** `/home/walter/dev/FileCat/static/img/`
### Step 2: Generate Multiple Icon Sizes
Run this command to generate different sizes from your 512x512 icon:
```bash
cd /home/walter/dev/FileCat/static/img/
# Copy your icon.png here first
cp /path/to/your/icon.png ./icon.png
# Generate favicon sizes using ImageMagick (if installed)
convert icon.png -resize 16x16 favicon-16x16.png
convert icon.png -resize 32x32 favicon-32x32.png
convert icon.png -resize 48x48 favicon-48x48.png
convert icon.png -resize 180x180 apple-touch-icon.png
convert icon.png -resize 192x192 android-chrome-192x192.png
convert icon.png -resize 512x512 android-chrome-512x512.png
# Create .ico file (multi-size)
convert icon.png -define icon:auto-resize=16,32,48,64,256 favicon.ico
```
**Don't have ImageMagick?** Use Python with Pillow (already installed):
```bash
cd /home/walter/dev/FileCat
python generate_favicons.py
```
### Step 3: Files Added to FileCat
**Code changes:**
- ✅ `app.py` - Added favicon route and icon serving
- ✅ `templates/base.html` - Added favicon links to header
- ✅ `generate_favicons.py` - Script to generate all icon sizes
**Icon files to create in `static/img/`:**
- `icon.png` (512x512) - Your main icon
- `favicon.ico` (multi-size) - Classic favicon
- `favicon-16x16.png` - Small favicon
- `favicon-32x32.png` - Medium favicon
- `apple-touch-icon.png` (180x180) - iOS home screen
- `android-chrome-192x192.png` - Android icon
- `android-chrome-512x512.png` - High-res Android icon
### Step 4: Using the Icon in Pages
The icon is automatically included in all pages via `base.html`.
**To use the icon elsewhere in your app:**
```html
<!-- In any template -->
<img src="{{ url_for('static', filename='img/icon.png') }}" alt="FileCat" width="32" height="32">
```
**In navbar or header:**
```html
<div class="navbar">
    <img src="{{ url_for('static', filename='img/icon.png') }}" alt="FileCat" width="24" height="24">
    <span>FileCat</span>
</div>
```
### Step 5: What You'll See
After setup:
- ✅ Favicon appears in browser tabs
- ✅ Icon shows in bookmarks
- ✅ iOS users can add to home screen with icon
- ✅ Android users see icon in app drawer
- ✅ Icon available throughout the app
### Testing
1. **Place your icon.png** in `/home/walter/dev/FileCat/static/img/`
2. **Run the generator:** `python generate_favicons.py`
3. **Restart Flask server**
4. **Open FileCat in browser**
5. **Check browser tab** - you should see your icon!
6. **Force refresh:** Ctrl+Shift+R (browsers cache favicons heavily)
### Troubleshooting
**Favicon not showing?**
- Clear browser cache (Ctrl+Shift+Delete)
- Hard refresh (Ctrl+Shift+R)
- Check browser dev tools → Network tab for 404 errors
- Verify files exist in `static/img/`
**Icon looks blurry?**
- Make sure source is high quality 512x512 PNG
- Check generated files are correct sizes
- Use PNG format (better than JPG for icons)
---
**Status:** ✅ Code ready, waiting for icon.png file  
**Next:** Place your icon.png in static/img/ and run generator  
**Date:** January 22, 2026
