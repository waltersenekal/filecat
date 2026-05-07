# File Integrity Management Guide

## Overview

The File Integrity Management system helps you maintain a clean and accurate database by:
- **Detecting missing files** - Files that are in the database but no longer exist on disk
- **Detecting corrupted files** - Files that exist but cannot be opened or are truncated
- **Finding new files** - Files that exist on disk but are not yet in the database
- **Managing problematic files** - Options to skip, delete, or quarantine corrupted files

## How to Use

### 1. Access File Integrity Management

Navigate to **Settings** page in FileCat and find the **🔍 File Integrity Management** section.

### 2. Running an Integrity Scan

Click **"🔎 Full Integrity Scan"** to check all files in your database.

The scan will report:
- **Total Checked**: Number of files in database
- **Valid Files**: Files that exist and can be opened
- **Missing Files**: Files in database but not on disk
- **Corrupted Files**: Files that exist but cannot be properly opened

### 3. Handling Missing Files

**Missing files** are entries in your database where the actual file no longer exists.

**Options:**
- Click **"Remove All from Database"** to clean up all missing file records at once
- This will remove the database records and any associated tags

### 4. Handling Corrupted Files

**Corrupted files** exist on disk but have issues (truncated, invalid format, etc.).

**For each corrupted file, you can:**

1. **⏭️ Skip** - Leave the file as-is (do nothing)
2. **🗑️ Delete File** - Permanently delete the file and remove from database
3. **📦 Move to Quarantine** - Move the file to a quarantine folder for later review

**Quarantine Folder:**
- When you choose "Move to Quarantine", you'll be prompted for a folder path
- Default: `/home/walter/dev/FileCat/quarantine`
- Files are moved with their directory structure preserved
- Database record is removed

### 5. Scanning for New Files

Click **"➕ Scan for New Files"** to find image files on disk that aren't in the database.

The scan will show:
- **Valid New Files**: Images that can be added to the database
- **Invalid/Corrupted New Files**: Files found but appear to be corrupted

**For valid new files:**
- Click **"➕ Add All to Database"** to import them
- Thumbnails will be automatically generated
- Files can then be tagged normally

**For invalid new files:**
- These are shown for information only
- Consider moving them to quarantine or deleting them manually

## API Endpoints

The following API endpoints are available:

### Scan Database Integrity
```
POST /api/integrity/scan
```
Returns: Missing and corrupted files

### Cleanup Missing Files
```
POST /api/integrity/cleanup-missing
```
Removes all missing file records from database

### Check Specific File
```
GET /api/integrity/check-file/<image_id>
```
Returns: Integrity check result for one file

### Handle Corrupted File
```
POST /api/integrity/handle-corrupted/<image_id>
Body: { "action": "skip|delete|quarantine", "quarantine_folder": "/path/to/quarantine" }
```

### Scan for New Files
```
POST /api/integrity/scan-new
```
Returns: List of files not in database

### Add Single File
```
POST /api/integrity/add-file
Body: { "filepath": "relative/path/to/file.jpg", "auto_thumbnail": true }
```

### Add Multiple Files
```
POST /api/integrity/batch-add-files
Body: { "filepaths": ["file1.jpg", "file2.jpg"], "auto_thumbnail": true }
```

## Common Use Cases

### Case 1: Files Were Deleted Outside FileCat
If you deleted files directly from the filesystem:
1. Run **Full Integrity Scan**
2. Review missing files list
3. Click **Remove All from Database** to clean up

### Case 2: Found Corrupted Files During AI Tagging
If AI tagging fails on certain files:
1. Run **Full Integrity Scan** to identify all corrupted files
2. For each corrupted file:
   - **Skip** if you want to try fixing it manually later
   - **Quarantine** to move it out of the way for investigation
   - **Delete** if the file is not needed

### Case 3: Added New Files to Source Folder
If you copied new image files into your Digital Papers folder:
1. Click **Scan for New Files**
2. Review the list of new files
3. Click **Add All to Database** to import them
4. Use AI tagging to automatically tag the new files

### Case 4: Database Cleanup Before Backup
Before backing up your database:
1. Run **Full Integrity Scan**
2. Remove all missing files
3. Handle any corrupted files
4. Run **Fix Tag Status** to clean up tag inconsistencies
5. Create database backup

## Error Messages

### "File not found"
The file exists in the database but not on disk. Remove from database or restore the file.

### "Image file is truncated or corrupted"
The file was not completely downloaded/copied. Try re-downloading or quarantine it.

### "Cannot identify image file"
The file may have wrong extension or is not actually an image. Check the file type.

### "File is empty (0 bytes)"
The file has no content. Delete or quarantine it.

### "Invalid image dimensions"
The image format is recognized but the content is invalid. Quarantine or delete.

## Best Practices

1. **Run integrity scans regularly** - Weekly or monthly checks help catch issues early

2. **Use quarantine instead of delete** - Quarantine lets you investigate files before permanent deletion

3. **Check quarantine folder periodically** - Review quarantined files and decide whether to delete or restore

4. **Scan for new files after bulk imports** - After copying many files, scan to ensure all are added

5. **Fix corrupted files before AI tagging** - Corrupted files will cause AI tagging to fail/loop

6. **Backup before major cleanups** - Always backup your database before removing many files

## Troubleshooting

### Scan is slow
- The scan checks every file in the database
- For large collections, this may take several minutes
- The scan runs in the foreground, so be patient

### Can't add new files
- Check that the files are in supported formats (jpg, jpeg, png, gif, bmp, webp, tiff, tif)
- Check file permissions
- Check that files aren't corrupted

### Quarantine folder error
- Ensure you have write permissions to the quarantine folder
- Create the folder manually if needed
- Use absolute paths (e.g., `/home/user/quarantine`)

### Files keep appearing as corrupted
- The files may be genuinely corrupted from download/transfer
- Try opening them in an image viewer
- Consider re-downloading from original source

## Integration with AI Tagging

The integrity management system works well with AI tagging:

1. **Before AI tagging**: Run integrity scan to remove corrupted files that would cause errors
2. **After finding new files**: Add them to database, then run AI tagging to auto-tag them
3. **Handle AI tagging errors**: If AI tagging gets stuck on files, check if they're corrupted

## Files Created

- **file_integrity.py** - Core integrity checking and management functions
- **API Endpoints in app.py** - `/api/integrity/*` endpoints
- **Settings UI** - File Integrity Management section in settings.html

## Related Features

- **Missing Files Check** (Database Management) - Quick check for missing files only
- **AI Auto-Tagging** - Automatically tag new files after adding them
- **Database Backup** - Backup before major cleanups
- **Fix Tag Status** - Fix tag inconsistencies after removing files
