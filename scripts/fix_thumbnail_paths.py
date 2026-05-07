#!/usr/bin/env python3
"""
Fix thumbnail paths in the database and regenerate missing thumbnails.
Run this script after updating thumbnail path logic.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database import get_db_connection
from config import SOURCE_FOLDER, THUMBNAIL_FOLDER
from thumbnail_generator import generate_thumbnail


def fix_thumbnail_paths():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, filepath, thumbnail_path FROM images')
    images = cursor.fetchall()
    updated = 0
    regenerated = 0
    for row in images:
        image_id = row['id']
        filepath = row['filepath']
        # Correct thumbnail path (should not start with 'thumbnails/')
        correct_thumb = os.path.splitext(filepath)[0] + '.jpg'
        # If current path is wrong, update it
        if row['thumbnail_path'] and row['thumbnail_path'].startswith('thumbnails/'):
            print(f"Fixing DB path for image {filepath}: {row['thumbnail_path']} -> {correct_thumb}")
            cursor.execute('UPDATE images SET thumbnail_path = ? WHERE id = ?', (correct_thumb, image_id))
            updated += 1
        # Regenerate thumbnail if missing
        thumb_file = os.path.join(THUMBNAIL_FOLDER, correct_thumb)
        if not os.path.exists(thumb_file):
            source_file = os.path.join(SOURCE_FOLDER, filepath)
            if os.path.exists(source_file):
                print(f"Regenerating thumbnail for {filepath}")
                generate_thumbnail(source_file, filepath)
                regenerated += 1
    conn.commit()
    conn.close()
    print(f"Done. Updated {updated} DB paths, regenerated {regenerated} thumbnails.")

if __name__ == '__main__':
    fix_thumbnail_paths()
