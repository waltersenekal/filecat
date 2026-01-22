# FileCat - Image Cataloging System

A web-based image cataloging system for organizing, tagging, and searching your photo collection.

## Features

- **Image Scanning**: Automatically scans folders for image files (JPG, PNG, GIF, BMP, WEBP)
- **Tagging System**: Add custom tags to images for easy organization
- **Search**: Find images by tags or filename
- **Thumbnails**: Fast loading with automatically generated thumbnails
- **Multi-platform**: Access from Windows, Linux, or Android via web browser
- **Download**: Select and download multiple images as ZIP
- **Phase 1 Complete**: Core functionality ready to use

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Navigate to project directory:**
   ```bash
   cd /home/walter/dev/FileCat
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database:**
   ```bash
   python init_db.py
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

6. **Access FileCat:**
   - Local: http://localhost:5000
   - Network: http://[YOUR-IP]:5000 (from other devices)

## Usage

### First Time Setup

1. **Start the application** (see Installation step 5)
2. **Scan for images**: Go to Dashboard → Click "Scan for New Images"
3. **Start tagging**: Go to Maintenance → Add tags to each image
4. **Search**: Use the Search page to find images by tags

### Daily Workflow

1. **Add new photos**: Drop them in the `Digital Papers/` folder
2. **Scan**: Click "Scan for New Images" on Dashboard
3. **Tag new images**: Go to Maintenance mode
4. **Search & Download**: Use Search page to find and download images

## Configuration

Edit `config.py` to customize:
- Source folder path
- Thumbnail size
- Items per page
- Supported file extensions

## File Structure

```
FileCat/
├── app.py                    # Main Flask application
├── config.py                 # Configuration settings
├── database.py               # Database operations
├── scanner.py                # File scanner
├── thumbnail_generator.py    # Thumbnail creation
├── init_db.py               # Database initialization
├── requirements.txt          # Python dependencies
├── Digital Papers/           # Your images go here
├── data/
│   └── filecat.db           # SQLite database
├── thumbnails/              # Generated thumbnails
├── static/
│   └── css/
│       └── style.css        # Stylesheet
└── templates/               # HTML templates
    ├── base.html
    ├── index.html
    ├── maintenance.html
    ├── search.html
    └── settings.html
```

## Features by Phase

### Phase 1 ✓ (Current)
- [x] Database setup
- [x] File scanner (images only)
- [x] Thumbnail generation
- [x] Manual tagging interface
- [x] Search by tags and filename
- [x] Image viewer with lightbox
- [x] Download selected images
- [x] Responsive web interface
- [x] Configurable pagination

### Phase 2 ✓ (90% Complete)
**AI & Enhanced Features**
- [x] AI-assisted auto-tagging (STAG/RAM model)
- [x] Background auto-tagging service with continuous batch processing
- [x] Single image and batch AI analysis
- [x] AI suggestions UI (accept/reject/review)
- [x] Enhanced debug logging for AI operations
- [x] Dark mode theme toggle with persistence
- [x] Keyboard shortcuts (Alt+H/M/S/T/D/?)
- [x] Favicon and icon support
- [x] Responsive mobile/tablet design
- [x] ZIP download with progress tracking
- [x] CSV export with metadata
- [x] PDF generation with multiple layouts (1/2/4/6/9 per page)
- [ ] Advanced search (AND/OR/NOT tag logic) - **Moved to Phase 3**
- [ ] Search by file size range - **Moved to Phase 3**
- [ ] Drag-and-drop tag assignment - **Moved to Phase 3**

**Outstanding:** Advanced search features moved to Phase 3. Core Phase 2 functionality complete.

### Phase 3 (Planned)
- [ ] Multi-user support
- [ ] Duplicate detection
- [ ] Collections/Albums
- [ ] Backup/Export tools

## Important Notes

- **Only image files are scanned** - All non-image content in `Digital Papers/` is automatically ignored
- Original images are never modified
- Database and thumbnails are portable
- Recommended to backup database weekly during active tagging

## Troubleshooting

**Images not showing:**
- Check that files are in `Digital Papers/` folder
- Run a scan from Dashboard
- Verify file extensions are supported

**Slow performance:**
- Reduce items per page in Search
- Thumbnails are generated on first scan (one-time process)

**Network access not working:**
- Check firewall settings
- Ensure port 5000 is not blocked
- Use http://[YOUR-IP]:5000 from other devices

## Development

This project was developed with AI assistance using **GitHub Copilot** (powered by OpenAI's GPT-4 and Claude 3.5 Sonnet models). The AI helped with:
- Code architecture and implementation
- Database schema design
- UI/UX templates and styling
- Background service implementation
- API endpoint development
- Documentation generation

While AI-assisted, all code has been reviewed, tested, and customized for the specific requirements of FileCat.

## License

Personal use project - See PROJECT_SPEC.md for full documentation

## Support

For issues or questions, refer to the PROJECT_SPEC.md file for detailed documentation.
