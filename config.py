"""
Configuration settings for FileCat
"""
import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Source folder containing images (configurable path)
SOURCE_FOLDER = os.environ.get('FILECAT_SOURCE_FOLDER', r'D:\Clipart and Digital Paper')

# Thumbnail storage
THUMBNAIL_FOLDER = os.path.join(BASE_DIR, 'thumbnails')

# Database
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'filecat.db')

# Supported image extensions (only these files will be scanned)
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.JPG', '.JPEG', '.PNG', '.GIF', '.BMP', '.WEBP'}

# Thumbnail settings
THUMBNAIL_MAX_SIZE = (300, 300)  # Max width/height in pixels
THUMBNAIL_QUALITY = 85  # JPEG quality for thumbnails

# Display settings
DEFAULT_ITEMS_PER_PAGE = 50
ITEMS_PER_PAGE_OPTIONS = [25, 50, 100, 200]
THUMBNAIL_SIZES = {
    'small': 150,
    'medium': 250,
    'large': 350
}

# Flask settings
SECRET_KEY = 'dev-secret-key-change-in-production'
HOST = '0.0.0.0'  # Listen on all interfaces (allows network access)
PORT = 5000
DEBUG = True

# AI Auto-Tagging Background Settings - Phase 2
AUTO_TAG_ENABLED = True  # Enable automatic background tagging
AUTO_TAG_INTERVAL = 300  # Check for new images every 5 minutes (300 seconds)
AUTO_TAG_ON_STARTUP = True  # Run auto-tag on application startup
AUTO_TAG_BATCH_SIZE = 50  # Process this many images per batch (to avoid overload)

