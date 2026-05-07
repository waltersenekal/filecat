# FileCat - Image Cataloging System
## Project Specification Document

**Project Name:** FileCat  
**Version:** 1.0  
**Last Updated:** 21 January 2026  
**Image Source Folder:** `Digital Papers/` (~24GB)

---

## Executive Summary

A cross-platform web-based application for cataloging, searching, and managing a large collection of images. The system will allow users to tag images with keywords, search by tags, view images, and download/print selections. Accessible from Windows, Linux, and Android devices.

---

## Technical Stack

- **Backend:** Python Flask
- **Database:** SQLite
- **Frontend:** HTML5, CSS3, JavaScript (Bootstrap for responsive design)
- **Image Processing:** Pillow (PIL) for thumbnails
- **Optional AI:** BLIP/CLIP for auto-tagging (Phase 2)

---

## System Architecture

```
FileCat/
├── app.py                 # Flask application
├── database.py            # Database models and queries
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── Digital Papers/        # Source image folder (read-only)
├── data/
│   └── filecat.db        # SQLite database
├── thumbnails/           # Generated thumbnails
└── static/
    ├── css/
    ├── js/
    └── uploads/
└── templates/            # HTML templates
    ├── index.html
    ├── maintenance.html
    ├── search.html
    └── download.html
```

---

## Database Schema

### Images Table
```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    file_size INTEGER,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modified TIMESTAMP,
    thumbnail_path TEXT,
    is_tagged BOOLEAN DEFAULT 0
);
```

### Tags Table
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag_name TEXT UNIQUE NOT NULL,
    usage_count INTEGER DEFAULT 0
);
```

### ImageTags Table (Many-to-Many)
```sql
CREATE TABLE image_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER,
    tag_id INTEGER,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(image_id, tag_id)
);
```

### Settings Table
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

---

## Phase 1: Core Functionality
**Goal:** Basic working system with manual tagging, search, and view capabilities

### Features

#### 1.1 Database Setup ⬜
- [ ] Create SQLite database schema
- [ ] Implement database connection handler
- [ ] Create CRUD operations for images, tags, and relationships
- [ ] Add database initialization script
- [ ] Implement database backup functionality

#### 1.2 File Scanner ⬜
- [ ] Recursive scan of `Digital Papers/` folder
- [ ] **Only detect image files** (.jpg, .jpeg, .png, .gif, .bmp, .webp)
- [ ] **Ignore all non-image content** (documents, videos, etc.)
- [ ] Extract file metadata (size, modified date)
- [ ] Check for new files not in database
- [ ] Check for deleted/moved files
- [ ] Display scan summary (X new files, Y missing files)

#### 1.3 Thumbnail Generator ⬜
- [ ] Generate thumbnails on first scan (max 300px width/height)
- [ ] Store thumbnails in `thumbnails/` folder
- [ ] Preserve aspect ratio
- [ ] Handle thumbnail regeneration if source updated
- [ ] Progress indicator during generation

#### 1.4 Maintenance Mode (Manual Tagging) ⬜
- [ ] List all untagged images
- [ ] Display current image (responsive size)
- [ ] Show image filename and path
- [ ] Text input for comma-separated tags
- [ ] "Save & Next" button
- [ ] "Skip" button
- [ ] Progress counter (Image 5 of 234)
- [ ] Ability to go back to previous image
- [ ] Tag suggestions from existing tags (autocomplete)
- [ ] Mark image as "tagged" even if no tags added

#### 1.5 Search/List Mode ⬜
- [ ] Display images in grid layout
- [ ] Thumbnail size selector (Small: 150px, Medium: 250px, Large: 350px)
- [ ] Configurable items per page (25/50/100/200)
- [ ] Pagination controls (Previous/Next, page numbers)
- [ ] Checkbox for each image (multi-select)
- [ ] "Select All" / "Deselect All" buttons
- [ ] Lightbox viewer for full-size image view
- [ ] Navigation in lightbox (previous/next)
- [ ] Display filename, file size, tags below each image
- [ ] Sort options:
  - [ ] Alphabetically (A-Z, Z-A)
  - [ ] Date added (newest/oldest)
  - [ ] File size (largest/smallest)
  - [ ] Recently tagged

#### 1.6 Search Functionality ⬜
- [ ] Search by single tag
- [ ] Search by multiple tags (AND logic: must have all tags)
- [ ] Search by multiple tags (OR logic: must have any tag)
- [ ] Search by filename
- [ ] Filter by date range
- [ ] Show result count
- [ ] Clear filters button

#### 1.7 Tag Management ⬜
- [ ] View all tags with usage count
- [ ] Rename tags
- [ ] Merge duplicate tags
- [ ] Delete unused tags
- [ ] Bulk tag operations (add tag to selected images)

#### 1.8 Configuration ⬜
- [ ] Settings page
- [ ] Configure source folder path (default: `Digital Papers/`)
- [ ] Set default items per page
- [ ] Set default thumbnail size
- [ ] Set supported file extensions
- [ ] Export settings to file
- [ ] Import settings from file

---

## Phase 2: Enhanced Features
**Goal:** Improve user experience and add AI-assisted tagging

### Features

#### 2.1 AI Auto-Tagging ⬜
- [ ] Integrate BLIP or CLIP model
- [ ] Run AI analysis during file scan (optional toggle)
- [ ] Generate suggested tags for each image
- [ ] Display AI suggestions in maintenance mode
- [ ] User can accept/reject/modify suggestions
- [ ] Track AI suggestion accuracy
- [ ] Batch processing with progress bar

#### 2.2 Improved UI/UX ⬜
- [ ] Responsive design for mobile/tablet
- [ ] Dark mode toggle
- [ ] Drag-and-drop tag assignment
- [ ] Keyboard shortcuts (arrow keys for navigation)
- [ ] Image comparison view (side-by-side)
- [ ] Recently viewed images
- [ ] Favorites/starred images
- [ ] Image statistics dashboard

#### 2.3 Download/Export ⬜
- [ ] Download selected images as ZIP
- [ ] Show ZIP creation progress
- [ ] Handle large selections (split into multiple ZIPs if >2GB)
- [ ] Download options:
  - [ ] Original quality
  - [ ] Compressed/resized
- [ ] Export image list as CSV/Excel
- [ ] Export metadata (filename, tags, path)

#### 2.4 Print Functionality ⬜
- [ ] Generate PDF from selected images
- [ ] Layout options:
  - [ ] 1 per page (full size)
  - [ ] 2 per page
  - [ ] 4 per page (grid)
  - [ ] 6 per page (grid)
  - [ ] 9 per page (contact sheet)
- [ ] Include filename and tags below each image
- [ ] Page orientation (portrait/landscape)
- [ ] Paper size selection (A4, Letter)

#### 2.5 Advanced Search ⬜
- [ ] Exclude tags (NOT logic)
- [ ] Tag combinations: (baby AND outdoor) OR (toddler AND park)
- [ ] Search by file size range
- [ ] Search untagged images only
- [ ] Saved search queries
- [ ] Search history

---

## Phase 3: Advanced Features
**Goal:** Power user features and multi-device support

### Features

#### 3.1 Batch Operations ⬜
- [ ] Batch tag addition/removal
- [ ] Batch delete images from database (not files)
- [ ] Batch re-scan specific folders
- [ ] Batch thumbnail regeneration
- [ ] Bulk import tags from CSV

#### 3.2 Collections/Albums ⬜
- [ ] Create custom collections
- [ ] Add images to multiple collections
- [ ] Share collection as link
- [ ] Export collection

#### 3.3 Duplicate Detection ⬜
- [ ] Find duplicate images (by hash)
- [ ] Find similar images (by visual similarity)
- [ ] Compare duplicates side-by-side
- [ ] Keep/delete workflow

#### 3.4 Performance Optimization ⬜
- [ ] Lazy loading of images
- [ ] Database indexing
- [ ] Cache frequently accessed data
- [ ] Async thumbnail generation
- [ ] Progressive image loading

#### 3.5 Network Access ⬜
- [ ] Secure with username/password
- [ ] Access from multiple devices on network
- [ ] Mobile-optimized interface
- [ ] Offline mode for mobile
- [ ] Sync status indicator

#### 3.6 Backup & Import/Export ⬜
- [ ] Auto-backup database daily
- [ ] Manual backup trigger
- [ ] Export entire catalog (database + thumbnails)
- [ ] Import catalog from backup
- [ ] Restore from backup

---

## Configuration Options

### settings.ini or UI-based settings
```ini
[Paths]
source_folder = Digital Papers
thumbnail_folder = thumbnails
database_path = data/filecat.db

[Display]
default_items_per_page = 50
default_thumbnail_size = medium
theme = light

[Performance]
max_thumbnails_per_batch = 100
enable_caching = true

[Features]
enable_ai_tagging = false
ai_confidence_threshold = 0.7

[Server]
host = 0.0.0.0
port = 5000
debug = false
```

---

## User Workflows

### Workflow 1: Initial Setup
1. Install Python and dependencies
2. Run application
3. Access via browser (http://localhost:5000)
4. Go to Settings → Verify "Digital Papers" path
5. Run initial scan (Maintenance → Scan for Files)
6. Wait for thumbnail generation
7. Begin tagging images

### Workflow 2: Tagging Images
1. Navigate to Maintenance mode
2. View current image
3. Add comma-separated tags (e.g., "baby, outdoor, summer, 2024")
4. Click "Save & Next"
5. Repeat until complete
6. View progress counter

### Workflow 3: Searching & Downloading
1. Navigate to Search page
2. Enter tags in search box (e.g., "baby")
3. View filtered results
4. Select desired images (checkboxes)
5. Click "Download Selected"
6. Wait for ZIP creation
7. Download ZIP file

### Workflow 4: Printing Contact Sheet
1. Search for images
2. Select images to print
3. Click "Print"
4. Choose layout (e.g., 9 per page)
5. Generate PDF
6. Print or save PDF

---

## Non-Functional Requirements

### Performance
- Scan 1000 images in < 2 minutes
- Thumbnail generation: 10-20 images/second
- Search results: < 1 second for any query
- Page load: < 2 seconds

### Compatibility
- **Desktop Browsers:** Chrome 90+, Firefox 88+, Edge 90+, Safari 14+
- **Mobile Browsers:** Chrome Android, Safari iOS
- **Operating Systems:** Windows 10+, Linux (Ubuntu 20.04+), Android 10+

### Security
- Local network access only (Phase 1)
- Optional password protection (Phase 3)
- No internet connection required

### Scalability
- Support up to 100,000 images
- Database size: < 500MB for 50,000 images
- Thumbnail folder: ~10% of original size

---

## Development Milestones

| Milestone | Target Features | Estimated Completion |
|-----------|----------------|---------------------|
| M1: Foundation | Database, Scanner, Basic UI | Week 2 |
| M2: Core Features | Tagging, Search, View | Week 4 |
| M3: Phase 1 Complete | Download, Config, Tag Mgmt | Week 6 |
| M4: Phase 2 Start | AI Integration, Enhanced UI | Week 10 |
| M5: Phase 2 Complete | Print, Advanced Search | Week 12 |
| M6: Phase 3 | All Advanced Features | Week 16 |

---

## Testing Checklist

### Phase 1 Testing
- [ ] Scan folder with 1000+ images successfully
- [ ] All thumbnails generated correctly
- [ ] Tag images and verify in database
- [ ] Search by tag returns correct results
- [ ] Multi-select and download works
- [ ] Pagination works correctly
- [ ] Settings persist after restart
- [ ] Handle missing/moved files gracefully
- [ ] Test on Windows, Linux, Android browser

### Phase 2 Testing
- [ ] AI suggestions are relevant
- [ ] PDF generation works with various layouts
- [ ] ZIP download handles large selections
- [ ] UI responsive on mobile devices
- [ ] Dark mode displays correctly

### Phase 3 Testing
- [ ] Network access from other devices
- [ ] Duplicate detection accuracy
- [ ] Backup and restore functionality
- [ ] Performance with 50,000+ images

---

## Installation & Deployment

### Prerequisites
```bash
Python 3.8+
pip
```

### Installation Steps
```bash
# Clone/navigate to project
cd FileCat

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Run application
python app.py
```

### Access
- **Local:** http://localhost:5000
- **Network:** http://[YOUR-IP]:5000 (from other devices)

---

## Future Enhancements (Beyond Phase 3)

- [ ] Mobile native app (React Native)
- [ ] Cloud storage integration (Google Photos, Dropbox)
- [ ] Video support
- [ ] Face recognition
- [ ] GPS/location-based tagging
- [ ] Automatic organization suggestions
- [ ] Machine learning for tag suggestions based on user patterns
- [ ] Multi-user support with separate libraries
- [ ] Comments/notes on images
- [ ] Rating system (1-5 stars)

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-21 | 1.0 | Initial specification document |

---

## Notes
**Only image files are scanned and cataloged** - all non-image content in `Digital Papers/` is ignored
- All file paths stored in database are relative to `Digital Papers/` folder
- Original images are never modified or moved
- Database and thumbnails are portable (can move to different computer)
- Recommended to backup database weekly during active tagging
- Supported image formats: JPG, JPEG, PNG, GIF, BMP, WEBP computer)
- Recommended to backup database weekly during active tagging
