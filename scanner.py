"""
File scanner for detecting images in Digital Papers folder
Only scans for image files, ignores all non-image content.
Uses directory mtime tracking for incremental scanning - only checks
folders whose modification time has changed since the last scan.
"""
import os
import sys
import hashlib
from datetime import datetime
from config import SOURCE_FOLDER, SUPPORTED_EXTENSIONS, THUMBNAIL_FOLDER
from database import add_image, get_db_connection, get_all_folder_mtimes, save_folder_mtimes
from thumbnail_generator import generate_thumbnail


def is_image_file(filename):
    """Check if file is a supported image format"""
    _, ext = os.path.splitext(filename)
    return ext in SUPPORTED_EXTENSIONS


def compute_file_checksum(filepath):
    """Compute MD5 checksum of a file"""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def scan_folder(progress_callback=None, full_scan=False):
    """
    Scan the Digital Papers folder for image files only.
    Uses incremental scanning based on directory modification times.
    Only directories whose mtime has changed since the last scan are checked.

    Args:
        progress_callback: Optional function to call with progress updates
        full_scan: If True, ignore cached mtimes and scan everything

    Returns:
        dict with scan statistics
    """
    from config import DEBUG
    stats = {
        'total_files_found': 0,
        'new_images': 0,
        'existing_images': 0,
        'skipped_folders': 0,
        'scanned_folders': 0,
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
    
    # Load cached folder mtimes for incremental scanning
    cached_mtimes = {} if full_scan else get_all_folder_mtimes()
    updated_mtimes = {}

    # Walk through directory tree (alphabetical order)
    for root, dirs, files in os.walk(SOURCE_FOLDER):
        dirs.sort()

        # Check if this directory has changed since last scan
        rel_dir = os.path.relpath(root, SOURCE_FOLDER)
        try:
            current_mtime = os.stat(root).st_mtime
        except OSError:
            continue

        cached_mtime = cached_mtimes.get(rel_dir)
        updated_mtimes[rel_dir] = current_mtime

        # Skip this directory if mtime unchanged (contents haven't changed)
        if cached_mtime is not None and current_mtime == cached_mtime:
            stats['skipped_folders'] += 1
            continue

        stats['scanned_folders'] += 1
        image_files_in_dir = [f for f in files if is_image_file(f)]
        if DEBUG:
            print(f"[SCAN] Scanning changed folder: {rel_dir} ({len(image_files_in_dir)} images)", flush=True)

        new_in_dir = 0
        existing_in_dir = 0
        for file_idx, filename in enumerate(sorted(files)):
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
                existing_in_dir += 1
                continue
            try:
                # Get file metadata
                file_stat = os.stat(full_path)
                file_size = file_stat.st_size
                date_modified = datetime.fromtimestamp(file_stat.st_mtime)
                # Compute checksum
                file_checksum = compute_file_checksum(full_path)
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
                    # Store checksum
                    conn2 = get_db_connection()
                    conn2.execute('UPDATE images SET file_checksum = ? WHERE id = ?', (file_checksum, image_id))
                    conn2.commit()
                    conn2.close()
                    stats['new_images'] += 1
                    new_in_dir += 1
                    if progress_callback:
                        progress_callback(f"Added: {relative_path}")
                    if DEBUG:
                        print(f"[SCAN]   Added ({new_in_dir}/{len(image_files_in_dir)}): {filename}", flush=True)
                else:
                    stats['existing_images'] += 1
                    if DEBUG:
                        print(f"[SCAN] Duplicate (not added): {relative_path}", flush=True)
            except Exception as e:
                error_msg = f"Error processing {relative_path}: {str(e)}"
                stats['errors'].append(error_msg)
                if progress_callback:
                    progress_callback(error_msg)
                if DEBUG:
                    print(f"[SCAN] ERROR: {error_msg}", flush=True)

        if DEBUG and new_in_dir > 0:
            print(f"[SCAN] Folder done: {new_in_dir} new, {existing_in_dir} already existed", flush=True)
        elif DEBUG and stats['scanned_folders'] % 50 == 0:
            print(f"[SCAN] Progress: {stats['scanned_folders']} folders scanned, "
                  f"{stats['new_images']} new images so far...", flush=True)

    # Save updated folder mtimes
    if updated_mtimes:
        save_folder_mtimes(updated_mtimes)

    stats['end_time'] = datetime.now()
    stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
    
    if DEBUG or (stats['skipped_folders'] > 0):
        print(f"[SCAN] Incremental scan: {stats['scanned_folders']} folders scanned, "
              f"{stats['skipped_folders']} unchanged folders skipped, "
              f"{stats['duration']:.2f}s")

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
