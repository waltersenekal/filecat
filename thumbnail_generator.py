"""
Thumbnail generator for FileCat
Creates optimized thumbnails for faster loading
"""
import os
from PIL import Image
from config import SOURCE_FOLDER, THUMBNAIL_FOLDER, THUMBNAIL_MAX_SIZE, THUMBNAIL_QUALITY


def generate_thumbnail(source_path, relative_path):
    """
    Generate a thumbnail for an image
    
    Args:
        source_path: Full path to source image
        relative_path: Relative path from SOURCE_FOLDER (used for thumbnail naming)
        
    Returns:
        Relative path to thumbnail file
    """
    try:
        # Create thumbnail folder structure matching source (relative to THUMBNAIL_FOLDER)
        thumbnail_rel_path = relative_path  # e.g. '2025/Anguscolorcraft/Quirky Zombie Girl/1.jpg'
        thumbnail_full_path = os.path.join(THUMBNAIL_FOLDER, thumbnail_rel_path)
        # Create thumbnail directory if needed
        os.makedirs(os.path.dirname(thumbnail_full_path), exist_ok=True)
        # Open and process image
        with Image.open(source_path) as img:
            # Convert RGBA to RGB if needed (for JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            # Generate thumbnail
            img.thumbnail(THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)
            # Save as JPEG
            thumbnail_path = os.path.splitext(thumbnail_full_path)[0] + '.jpg'
            img.save(thumbnail_path, 'JPEG', quality=THUMBNAIL_QUALITY, optimize=True)
        # Return relative path from thumbnails folder (not prefixed with 'thumbnails/')
        return os.path.splitext(thumbnail_rel_path)[0] + '.jpg'
    except Exception as e:
        print(f"Error generating thumbnail for {relative_path}: {e}")
        return None


def regenerate_all_thumbnails(progress_callback=None):
    """Regenerate all thumbnails for images in database"""
    from database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, filepath FROM images')
    images = cursor.fetchall()
    
    total = len(images)
    success_count = 0
    
    for idx, row in enumerate(images):
        source_path = os.path.join(SOURCE_FOLDER, row['filepath'])
        
        if not os.path.exists(source_path):
            if progress_callback:
                progress_callback(f"File not found: {row['filepath']}")
            continue
        
        thumbnail_path = generate_thumbnail(source_path, row['filepath'])
        
        if thumbnail_path:
            cursor.execute('UPDATE images SET thumbnail_path = ? WHERE id = ?', 
                          (thumbnail_path, row['id']))
            success_count += 1
        
        if progress_callback:
            progress_callback(f"Progress: {idx + 1}/{total} - {row['filepath']}")
    
    conn.commit()
    conn.close()
    
    return {
        'total': total,
        'success': success_count,
        'failed': total - success_count
    }


if __name__ == '__main__':
    print("Testing thumbnail generator...")
    # This would need an actual image to test
    print("Use scanner.py to generate thumbnails during scan")
