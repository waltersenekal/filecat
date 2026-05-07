#!/usr/bin/env python3
"""
Mark specific corrupted images as processed to prevent infinite retry loop
"""
import sys
import os

# Add parent directory to path to import database module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_connection, save_ai_suggestions

def mark_corrupted_images_as_processed():
    """Mark known corrupted images as processed"""

    corrupted_filenames = [
        '208a.jpg',
        'artzology_mystery_bundle_ (26).jpg'
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    print("Finding corrupted images in database...")
    for filename in corrupted_filenames:
        # Find image by filename pattern
        cursor.execute('SELECT id, filename, filepath FROM images WHERE filename = ?', (filename,))
        image = cursor.fetchone()

        if image:
            image_id = image['id']
            print(f"\nFound: {image['filename']}")
            print(f"  Path: {image['filepath']}")
            print(f"  ID: {image_id}")

            # Check if already has AI suggestions
            cursor.execute('SELECT COUNT(*) as count FROM ai_suggestions WHERE image_id = ?', (image_id,))
            suggestion_count = cursor.fetchone()['count']

            if suggestion_count > 0:
                print(f"  Already has {suggestion_count} AI suggestion record(s) - GOOD!")
            else:
                print(f"  No AI suggestions - marking as processed...")
                try:
                    save_ai_suggestions(image_id, [])
                    print(f"  ✅ Marked as processed successfully")
                except Exception as e:
                    print(f"  ❌ Error marking as processed: {e}")
        else:
            print(f"\n❌ Not found in database: {filename}")

    conn.close()
    print("\n" + "="*60)
    print("Done!")

if __name__ == '__main__':
    mark_corrupted_images_as_processed()
