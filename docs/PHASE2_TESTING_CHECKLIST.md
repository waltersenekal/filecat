# Phase 2 - Testing Checklist

Use this checklist to verify all Phase 2 features are working correctly.

---

## 🌙 Dark Mode Testing

- [ ] Click the 🌙 button in navigation - UI switches to dark theme
- [ ] Click again (☀️) - UI switches back to light theme
- [ ] Refresh page - theme preference persists
- [ ] Press `Alt+D` - theme toggles
- [ ] Check all pages (Dashboard, Maintenance, Search, Tags, Settings) in dark mode
- [ ] Verify images are slightly dimmed in dark mode
- [ ] Check modals display correctly in both themes
- [ ] Verify text is readable in both themes

**Status:** ___________

---

## 📊 CSV Export Testing

- [ ] Go to Search page
- [ ] Click "📊 Export CSV" button with no images
- [ ] Verify CSV downloads with header row only
- [ ] Add some images to database (scan if needed)
- [ ] Click "📊 Export CSV" again
- [ ] Open CSV in Excel or Google Sheets
- [ ] Verify columns: Filename, File Path, File Size, Date Added, Date Modified, Tags, Is Tagged
- [ ] Check that tags are comma-separated correctly
- [ ] Verify file paths are relative (no absolute paths)
- [ ] Test with 100+ images
- [ ] Test with images having 10+ tags each
- [ ] Verify special characters in filenames display correctly

**Status:** ___________

---

## 🖨️ PDF Print Testing

### Basic Functionality
- [ ] Select 1 image on Search page
- [ ] Click "🖨️ Print Selected" button
- [ ] Verify modal opens with options
- [ ] Choose "1 per page", Letter, Portrait, Include info ✓
- [ ] Click "Generate PDF"
- [ ] Verify PDF downloads
- [ ] Open PDF - verify image displays correctly
- [ ] Check filename and tags appear below image

### Layout Options
- [ ] Test "2 per page" layout - verify 2 images appear
- [ ] Test "4 per page" layout - verify 2x2 grid
- [ ] Test "6 per page" layout - verify 2x3 grid
- [ ] Test "9 per page" layout - verify 3x3 grid
- [ ] Verify images are centered in cells
- [ ] Verify images scale proportionally (no distortion)

### Page Options
- [ ] Test with A4 page size
- [ ] Test with Letter page size
- [ ] Test Portrait orientation
- [ ] Test Landscape orientation
- [ ] Test without "Include info" - no filenames/tags shown

### Edge Cases
- [ ] Generate PDF with 1 image
- [ ] Generate PDF with 10 images
- [ ] Generate PDF with 50+ images (multiple pages)
- [ ] Test with very long filename
- [ ] Test with image having many tags (10+)
- [ ] Test with missing image - verify error handling
- [ ] Test with very tall image (portrait)
- [ ] Test with very wide image (landscape)

**Status:** ___________

---

## 💾 Download with Progress Testing

### Basic Functionality
- [ ] Select 5 images on Search page
- [ ] Click "💾 Download Selected"
- [ ] Verify progress modal appears
- [ ] Watch progress bar fill
- [ ] Verify "X / Y" count updates
- [ ] ZIP downloads automatically when complete
- [ ] Extract ZIP - verify all 5 images present
- [ ] Verify folder structure is preserved

### Progress Tracking
- [ ] Test with 20 images - progress updates smoothly
- [ ] Test with 50 images - no freezing
- [ ] Test with 100+ images - handles large batch
- [ ] Verify progress percentage is accurate
- [ ] Verify modal closes after download

### Edge Cases
- [ ] Click download with 0 images selected - check error handling
- [ ] Try downloading 1 image
- [ ] Try downloading 200+ images
- [ ] Check ZIP filename has timestamp
- [ ] Verify original image quality (not compressed)
- [ ] Test with images in nested subfolders

**Status:** ___________

---

## ⌨️ Keyboard Shortcuts Testing

### Navigation Shortcuts
- [ ] Press `Alt+H` - goes to Dashboard
- [ ] Press `Alt+M` - goes to Maintenance
- [ ] Press `Alt+S` - goes to Search
- [ ] Press `Alt+T` - goes to Tags
- [ ] Test from each page (shortcuts work globally)

### Theme Shortcut
- [ ] Press `Alt+D` - toggles dark mode
- [ ] Press again - toggles back
- [ ] Works from any page

### Help Shortcut
- [ ] Press `Alt+?` - shows keyboard shortcuts modal
- [ ] Verify all shortcuts listed
- [ ] Verify modal displays correctly
- [ ] Click OK or press Esc to close

### Help Button
- [ ] Click ❓ button in navigation
- [ ] Verify same help modal appears
- [ ] Check tooltip shows on hover

### Lightbox Shortcuts (from Phase 1)
- [ ] Open image in lightbox
- [ ] Press `→` (right arrow) - next image
- [ ] Press `←` (left arrow) - previous image
- [ ] Press `Esc` - closes lightbox
- [ ] Verify wraps around (last → first, first → last)

### Input Field Test
- [ ] Click in search box
- [ ] Type something
- [ ] Press `Alt+S` - should NOT navigate (disabled in inputs)
- [ ] Click outside input
- [ ] Press `Alt+S` - now works

**Status:** ___________

---

## 📱 Responsive Design Testing

### Desktop (>1024px)
- [ ] All buttons visible in one row
- [ ] Grid layout displays correctly
- [ ] Modals centered and readable

### Tablet (768px - 1024px)
- [ ] Buttons may wrap to multiple rows
- [ ] Grid adjusts to fewer columns
- [ ] Navigation bar still usable

### Mobile (<768px)
- [ ] Buttons stack vertically or wrap
- [ ] Images display in 1-2 column grid
- [ ] Navigation menu accessible
- [ ] Touch targets large enough
- [ ] Modals fit on screen
- [ ] Keyboard shortcuts work (if keyboard attached)

**Test Browsers:**
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Edge
- [ ] Safari (if available)
- [ ] Mobile Chrome (Android)
- [ ] Mobile Safari (iOS)

**Status:** ___________

---

## 🔄 Integration Testing

### Workflow 1: Export Tagged Images
- [ ] Search for tag "example"
- [ ] Results appear
- [ ] Click "Export CSV"
- [ ] Open CSV - tagged images listed with tags
- [ ] Success!

### Workflow 2: Print Contact Sheet
- [ ] Search for tag "family"
- [ ] Select 9 images
- [ ] Click "Print Selected"
- [ ] Choose 9 per page, A4, Portrait, Include info
- [ ] Generate PDF
- [ ] PDF has 1 page with 3x3 grid
- [ ] Each image shows filename and tags
- [ ] Success!

### Workflow 3: Download Collection
- [ ] Go to Search page
- [ ] Enter multiple tags
- [ ] Select all results (use Select All checkbox)
- [ ] Click "Download Selected"
- [ ] Watch progress (e.g., "45 / 120")
- [ ] ZIP downloads
- [ ] Extract - all images present
- [ ] Success!

### Workflow 4: Dark Mode Throughout
- [ ] Toggle dark mode on
- [ ] Navigate to each page
- [ ] Perform a search
- [ ] Tag an image
- [ ] Export CSV
- [ ] Print PDF
- [ ] Download ZIP
- [ ] Everything works in dark mode
- [ ] Success!

**Status:** ___________

---

## 🐛 Error Handling Testing

### CSV Export Errors
- [ ] Export with 0 images - creates empty CSV or shows message
- [ ] Export with database error - graceful error message

### PDF Generation Errors
- [ ] Select 0 images - shows error message
- [ ] Generate PDF with all missing images - shows error placeholders
- [ ] Generate PDF with invalid options - handles gracefully

### Download Errors
- [ ] Select 0 images - shows error message
- [ ] Download with file system error - shows error in modal
- [ ] Server restart during download - recovers gracefully

### Keyboard Shortcut Errors
- [ ] Invalid key combo - ignored (no error)
- [ ] Shortcut while input focused - ignored (correct behavior)

**Status:** ___________

---

## ✅ Final Verification

- [ ] All Phase 2 features tested
- [ ] No critical bugs found
- [ ] Documentation reviewed
- [ ] README files accurate
- [ ] Server runs without errors
- [ ] All endpoints respond correctly
- [ ] UI looks professional
- [ ] Dark mode polished
- [ ] Ready for production use

---

## 📝 Notes

**Issues Found:**
_List any bugs or issues discovered during testing_

**Improvements Suggested:**
_List any enhancement ideas_

**Performance Notes:**
_Note any performance issues with large datasets_

---

**Tester:** ___________________  
**Date:** ___________________  
**Environment:** ___________________ (OS, Browser, Python version)  
**Database Size:** ___________ images

**Overall Status:** ⬜ Pass  ⬜ Fail  ⬜ Needs Work

---

## 🎯 Sign-off

Once all tests pass:

- [ ] Update PHASE2_PROGRESS.md with test results
- [ ] Mark features as "✅ Tested & Working"
- [ ] Document any known issues
- [ ] Decide on next phase (complete Phase 2 or move to Phase 3)

**Phase 2 Testing Complete!** ✅
