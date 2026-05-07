"""
File Integrity Checker and Manager
Handles missing files cleanup, corrupted file detection, and new file processing
"""
import os
import shutil
from datetime import datetime
from PIL import Image, ImageFile
from config import SOURCE_FOLDER, SUPPORTED_EXTENSIONS
from database import (
    get_db_connection, delete_image, get_all_images,
    add_image, get_image_by_id, update_image_integrity,
    get_images_with_integrity_issues
)
from thumbnail_generator import generate_thumbnail

# Allow loading truncated images for detection
ImageFile.LOAD_TRUNCATED_IMAGES = True


def check_file_integrity(image_path):
    """
    Check if an image file is valid and can be opened

    Args:
        image_path: Full path to the image file

    Returns:
        dict with keys: 'valid', 'error_message', 'file_size', 'dimensions'
    """
    result = {
        'valid': True,
        'error_message': None,
        'file_size': 0,
        'dimensions': None,
        'format': None
    }

    # Check if file exists
    if not os.path.exists(image_path):
        result['valid'] = False
        result['error_message'] = 'File not found'
        return result

    # Get file size
    try:
        result['file_size'] = os.path.getsize(image_path)
        if result['file_size'] == 0:
            result['valid'] = False
            result['error_message'] = 'File is empty (0 bytes)'
            return result
    except Exception as e:
        result['valid'] = False
        result['error_message'] = f'Cannot read file size: {str(e)}'
        return result

    # Try to open and validate image
    try:
        with Image.open(image_path) as img:
            # Force load to detect truncation
            img.load()
            result['dimensions'] = img.size
            result['format'] = img.format

            # Check for reasonable dimensions
            if img.size[0] < 1 or img.size[1] < 1:
                result['valid'] = False
                result['error_message'] = 'Invalid image dimensions'

    except OSError as e:
        error_msg = str(e).lower()
        if 'truncated' in error_msg:
            result['valid'] = False
            result['error_message'] = f'Image file is truncated or corrupted: {str(e)}'
        elif 'cannot identify' in error_msg:
            result['valid'] = False
            result['error_message'] = 'Cannot identify image file (may be corrupted or unsupported format)'
        else:
            result['valid'] = False
            result['error_message'] = f'Error opening image: {str(e)}'
    except Exception as e:
        result['valid'] = False
        result['error_message'] = f'Unexpected error: {str(e)}'

    return result


def scan_database_integrity(progress_callback=None, mark_in_db=True):
    """
    Scan all images in database and check their integrity

    Args:
        progress_callback: Optional function(current, total, message) for progress updates
        mark_in_db: If True, update integrity status in database

    Returns:
        dict with scan results
    """
    results = {
        'total_checked': 0,
        'missing_files': [],
        'corrupted_files': [],
        'valid_files': 0,
        'errors': []
    }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, filepath, filename FROM images')
    all_images = cursor.fetchall()
    conn.close()

    total = len(all_images)

    for idx, row in enumerate(all_images):
        results['total_checked'] += 1
        image_id = row['id']
        filepath = row['filepath']
        filename = row['filename']

        full_path = os.path.join(SOURCE_FOLDER, filepath)

        if progress_callback:
            progress_callback(idx + 1, total, f"Checking: {filename}")

        # Check if file exists
        if not os.path.exists(full_path):
            results['missing_files'].append({
                'id': image_id,
                'filepath': filepath,
                'filename': filename,
                'error': 'File not found'
            })
            if mark_in_db:
                update_image_integrity(image_id, 'missing', 'File not found')
            continue

        # Check file integrity
        integrity = check_file_integrity(full_path)

        if not integrity['valid']:
            results['corrupted_files'].append({
                'id': image_id,
                'filepath': filepath,
                'filename': filename,
                'error': integrity['error_message'],
                'file_size': integrity['file_size']
            })
            if mark_in_db:
                update_image_integrity(image_id, 'corrupted', integrity['error_message'])
        else:
            results['valid_files'] += 1
            if mark_in_db:
                update_image_integrity(image_id, 'valid')

    return results


def cleanup_missing_files():
    """
    Remove database records for files that no longer exist

    Returns:
        dict with cleanup results
    """
    results = {
        'removed_count': 0,
        'removed_files': []
    }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, filepath, filename FROM images')
    all_images = cursor.fetchall()
    conn.close()

    for row in all_images:
        image_id = row['id']
        filepath = row['filepath']
        filename = row['filename']
        full_path = os.path.join(SOURCE_FOLDER, filepath)

        if not os.path.exists(full_path):
            delete_image(image_id)
            results['removed_count'] += 1
            results['removed_files'].append({
                'id': image_id,
                'filepath': filepath,
                'filename': filename
            })

    return results


def handle_corrupted_file(image_id, action='skip', quarantine_folder=None):
    """
    Handle a corrupted file by skipping, deleting, or moving to quarantine

    Args:
        image_id: Database ID of the image
        action: 'skip', 'delete', or 'quarantine'
        quarantine_folder: Path to quarantine folder (required if action='quarantine')

    Returns:
        dict with result
    """
    result = {
        'success': False,
        'action': action,
        'message': ''
    }

    # Get image info
    image = get_image_by_id(image_id)
    if not image:
        result['message'] = 'Image not found in database'
        return result

    filepath = image['filepath']
    full_path = os.path.join(SOURCE_FOLDER, filepath)

    if action == 'skip':
        result['success'] = True
        result['message'] = f'Skipped {filepath}'

    elif action == 'delete':
        # Delete file and database record
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
            delete_image(image_id)
            result['success'] = True
            result['message'] = f'Deleted {filepath}'
        except Exception as e:
            result['message'] = f'Error deleting: {str(e)}'

    elif action == 'quarantine':
        if not quarantine_folder:
            result['message'] = 'Quarantine folder not specified'
            return result

        try:
            # Create quarantine folder if needed
            os.makedirs(quarantine_folder, exist_ok=True)

            # Create subdirectory structure in quarantine
            rel_dir = os.path.dirname(filepath)
            quarantine_subdir = os.path.join(quarantine_folder, rel_dir)
            os.makedirs(quarantine_subdir, exist_ok=True)

            # Move file
            dest_path = os.path.join(quarantine_folder, filepath)
            if os.path.exists(full_path):
                shutil.move(full_path, dest_path)

            # Remove from database
            delete_image(image_id)

            result['success'] = True
            result['message'] = f'Moved to quarantine: {filepath}'
            result['quarantine_path'] = dest_path
        except Exception as e:
            result['message'] = f'Error moving to quarantine: {str(e)}'
    else:
        result['message'] = f'Unknown action: {action}'

    return result


def scan_for_new_files(progress_callback=None):
    """
    Scan source folder for new image files not in database

    Args:
        progress_callback: Optional function(message) for progress updates

    Returns:
        dict with scan results
    """
    results = {
        'new_files': [],
        'total_found': 0,
        'errors': []
    }

    # Get existing files from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT filepath FROM images')
    existing_paths = {row['filepath'] for row in cursor.fetchall()}
    conn.close()

    # Scan filesystem
    for root, dirs, files in os.walk(SOURCE_FOLDER):
        for filename in files:
            # Check if it's an image file
            _, ext = os.path.splitext(filename)
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, SOURCE_FOLDER)

            # Check if already in database
            if relative_path in existing_paths:
                continue

            results['total_found'] += 1

            # Check integrity before adding
            integrity = check_file_integrity(full_path)

            results['new_files'].append({
                'filepath': relative_path,
                'filename': filename,
                'full_path': full_path,
                'valid': integrity['valid'],
                'error': integrity['error_message'],
                'file_size': integrity['file_size'],
                'dimensions': integrity['dimensions']
            })

            if progress_callback:
                progress_callback(f"Found new file: {relative_path}")

    return results


def add_new_file(filepath, auto_generate_thumbnail=True):
    """
    Add a new file to the database with integrity checking

    Args:
        filepath: Relative path from SOURCE_FOLDER
        auto_generate_thumbnail: Whether to generate thumbnail automatically

    Returns:
        dict with result
    """
    result = {
        'success': False,
        'image_id': None,
        'message': ''
    }

    full_path = os.path.join(SOURCE_FOLDER, filepath)

    # Check if file exists
    if not os.path.exists(full_path):
        result['message'] = 'File not found'
        return result

    # Check integrity
    integrity = check_file_integrity(full_path)
    if not integrity['valid']:
        result['message'] = f"Invalid file: {integrity['error_message']}"
        result['error'] = integrity['error_message']
        return result

    try:
        # Get file metadata
        file_stat = os.stat(full_path)
        file_size = file_stat.st_size
        date_modified = datetime.fromtimestamp(file_stat.st_mtime)
        filename = os.path.basename(filepath)

        # Generate thumbnail
        thumbnail_path = None
        if auto_generate_thumbnail:
            try:
                thumbnail_path = generate_thumbnail(full_path, filepath)
            except Exception as e:
                result['message'] = f"Warning: Could not generate thumbnail: {str(e)}"

        # Add to database
        image_id = add_image(
            filepath=filepath,
            filename=filename,
            file_size=file_size,
            date_modified=date_modified,
            thumbnail_path=thumbnail_path
        )

        if image_id:
            result['success'] = True
            result['image_id'] = image_id
            result['message'] = f'Successfully added: {filepath}'
        else:
            result['message'] = 'File already exists in database'

    except Exception as e:
        result['message'] = f'Error adding file: {str(e)}'

    return result


if __name__ == '__main__':
    """Test integrity checking"""
    print("Running file integrity check...")
    print("=" * 60)

    def progress(current, total, message):
        print(f"[{current}/{total}] {message}")

    results = scan_database_integrity(progress_callback=progress)

    print("=" * 60)
    print("\nIntegrity Check Results:")
    print(f"  Total checked: {results['total_checked']}")
    print(f"  Valid files: {results['valid_files']}")
    print(f"  Missing files: {len(results['missing_files'])}")
    print(f"  Corrupted files: {len(results['corrupted_files'])}")

    if results['missing_files']:
        print("\nMissing Files:")
        for f in results['missing_files'][:10]:
            print(f"  - {f['filepath']}")

    if results['corrupted_files']:
        print("\nCorrupted Files:")
        for f in results['corrupted_files'][:10]:
            print(f"  - {f['filepath']}: {f['error']}")
