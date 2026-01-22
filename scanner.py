"""
File scanner for detecting images in Digital Papers folder
Only scans for image files, ignores all non-image content
"""
import os
from datetime import datetime
from config import SOURCE_FOLDER, SUPPORTED_EXTENSIONS, THUMBNAIL_FOLDER
from database import add_image, get_db_connection
from thumbnail_generator import generate_thumbnail


def is_image_file(filename):
    """Check if file is a supported image format"""
    _, ext = os.path.splitext(filename)
    return ext in SUPPORTED_EXTENSIONS


def scan_folder(progress_callback=None):
    """
    Scan the Digital Papers folder for image files only.
    Ignores all non-image content.
    
    Args:
        progress_callback: Optional function to call with progress updates
        
    Returns:
        dict with scan statistics
    """
    from config import DEBUG
    stats = {
        'total_files_found': 0,
        'new_images': 0,
        'existing_images': 0,
        'errors': [],
        'start_time': datetime.now()
    }
    
    if not os.path.exists(SOURCE_FOLDER):
        stats['errors'].append(f"Source folder not found: {SOURCE_FOLDER}")
        return stats
    
    # Get existing image paths from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT filepath FROM images')
    existing_paths = {row['filepath'] for row in cursor.fetchall()}
    conn.close()
    
    # Walk through directory tree
    for root, dirs, files in os.walk(SOURCE_FOLDER):
        for filename in files:
            # Only process image files
            if not is_image_file(filename):
                continue
            stats['total_files_found'] += 1
            full_path = os.path.join(root, filename)
            # Create relative path from SOURCE_FOLDER
            relative_path = os.path.relpath(full_path, SOURCE_FOLDER)
            # Skip if already in database
            if relative_path in existing_paths:
                stats['existing_images'] += 1
                if progress_callback:
                    progress_callback(f"Already in database: {relative_path}")
                if DEBUG:
                    print(f"[SCAN] Already in database: {relative_path}")
                continue
            try:
                # Get file metadata
                file_stat = os.stat(full_path)
                file_size = file_stat.st_size
                date_modified = datetime.fromtimestamp(file_stat.st_mtime)
                # Generate thumbnail
                thumbnail_path = generate_thumbnail(full_path, relative_path)
                # Add to database
                image_id = add_image(
                    filepath=relative_path,
                    filename=filename,
                    file_size=file_size,
                    date_modified=date_modified,
                    thumbnail_path=thumbnail_path
                )
                if image_id:
                    stats['new_images'] += 1
                    if progress_callback:
                        progress_callback(f"Added: {relative_path}")
                    if DEBUG:
                        print(f"[SCAN] Added: {relative_path}")
                else:
                    stats['existing_images'] += 1
                    if DEBUG:
                        print(f"[SCAN] Duplicate (not added): {relative_path}")
            except Exception as e:
                error_msg = f"Error processing {relative_path}: {str(e)}"
                stats['errors'].append(error_msg)
                if progress_callback:
                    progress_callback(error_msg)
                if DEBUG:
                    print(f"[SCAN] ERROR: {error_msg}")
    
    stats['end_time'] = datetime.now()
    stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
    
    return stats


def check_missing_files():
    """
    Check if any files in the database no longer exist on disk
    
    Returns:
        list of missing file paths
    """
    missing_files = []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, filepath FROM images')
    
    for row in cursor.fetchall():
        full_path = os.path.join(SOURCE_FOLDER, row['filepath'])
        if not os.path.exists(full_path):
            missing_files.append({
                'id': row['id'],
                'filepath': row['filepath']
            })
    
    conn.close()
    return missing_files


def get_scan_summary():
    """Get summary of current database state"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as total FROM images')
    total_images = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as tagged FROM images WHERE is_tagged = 1')
    tagged_images = cursor.fetchone()['tagged']
    
    cursor.execute('SELECT COUNT(*) as total FROM tags')
    total_tags = cursor.fetchone()['total']
    
    cursor.execute('SELECT SUM(file_size) as total_size FROM images')
    total_size = cursor.fetchone()['total_size'] or 0
    
    conn.close()
    
    return {
        'total_images': total_images,
        'tagged_images': tagged_images,
        'untagged_images': total_images - tagged_images,
        'total_tags': total_tags,
        'total_size_bytes': total_size,
        'total_size_gb': round(total_size / (1024**3), 2)
    }


if __name__ == '__main__':
    print("Starting file scan...")
    print(f"Scanning folder: {SOURCE_FOLDER}")
    print(f"Looking for image files with extensions: {SUPPORTED_EXTENSIONS}")
    print("=" * 60)
    
    def print_progress(msg):
        print(f"  {msg}")
    
    results = scan_folder(progress_callback=print_progress)
    
    print("=" * 60)
    print("\nScan Results:")
    print(f"  Total image files found: {results['total_files_found']}")
    print(f"  New images added: {results['new_images']}")
    print(f"  Already in database: {results['existing_images']}")
    print(f"  Duration: {results['duration']:.2f} seconds")
    
    if results['errors']:
        print(f"\n  Errors: {len(results['errors'])}")
        for error in results['errors'][:10]:  # Show first 10 errors
            print(f"    - {error}")
    
    print("\nDatabase Summary:")
    summary = get_scan_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
