#!/usr/bin/env python3
"""
Script to manually mark corrupted/problematic images as processed
This helps recover from infinite loop situations where images can't be tagged
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_connection, save_ai_suggestions

def mark_image_as_processed_by_filename(filename):
    """Mark an image as processed by filename"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Find image by filename
    cursor.execute('SELECT id, filepath, filename FROM images WHERE filename = ?', (filename,))
    result = cursor.fetchone()

    if not result:
        print(f"❌ Image not found: {filename}")
        conn.close()
        return False

    image_id = result['id']
    filepath = result['filepath']

    print(f"Found image: {filename}")
    print(f"  ID: {image_id}")
    print(f"  Path: {filepath}")

    # Check if already processed
    cursor.execute('SELECT COUNT(*) as count FROM ai_suggestions WHERE image_id = ?', (image_id,))
    already_processed = cursor.fetchone()['count'] > 0

    if already_processed:
        print(f"  ⚠️ Already has ai_suggestions record")

    conn.close()

    # Mark as processed
    try:
        save_ai_suggestions(image_id, [])
        print(f"  ✓ Marked as processed (no tags)")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def mark_all_unprocessed_as_processed():
    """Mark ALL unprocessed images as processed (use with caution!)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Find all unprocessed images
    cursor.execute('''
        SELECT i.id, i.filename FROM images i
        LEFT JOIN ai_suggestions ai ON i.id = ai.image_id
        WHERE ai.id IS NULL
        ORDER BY i.filename
    ''')

    unprocessed = cursor.fetchall()
    conn.close()

    if not unprocessed:
        print("✓ No unprocessed images found")
        return

    print(f"Found {len(unprocessed)} unprocessed images")
    print("\nWARNING: This will mark ALL of them as processed!")
    response = input("Continue? (yes/no): ").strip().lower()

    if response != 'yes':
        print("Cancelled")
        return

    success = 0
    failed = 0

    for img in unprocessed:
        try:
            save_ai_suggestions(img['id'], [])
            print(f"  ✓ {img['filename']}")
            success += 1
        except Exception as e:
            print(f"  ❌ {img['filename']}: {e}")
            failed += 1

    print(f"\nComplete: {success} marked, {failed} failed")


def list_unprocessed_images():
    """List all images that haven't been processed by AI"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT i.id, i.filename, i.filepath FROM images i
        LEFT JOIN ai_suggestions ai ON i.id = ai.image_id
        WHERE ai.id IS NULL
        ORDER BY i.filename
    ''')

    unprocessed = cursor.fetchall()
    conn.close()

    if not unprocessed:
        print("✓ No unprocessed images found")
        return

    print(f"Found {len(unprocessed)} unprocessed images:\n")
    for img in unprocessed:
        print(f"  ID {img['id']:5d}: {img['filename']}")
        print(f"           {img['filepath']}")


if __name__ == '__main__':
    print("=" * 70)
    print("Mark Corrupted Images as Processed")
    print("=" * 70)

    if len(sys.argv) > 1:
        if sys.argv[1] == '--list':
            list_unprocessed_images()
        elif sys.argv[1] == '--all':
            mark_all_unprocessed_as_processed()
        else:
            # Mark specific image by filename
            filename = sys.argv[1]
            mark_image_as_processed_by_filename(filename)
    else:
        # Interactive mode
        print("\nOptions:")
        print("  1. List unprocessed images")
        print("  2. Mark specific image as processed")
        print("  3. Mark ALL unprocessed images as processed")
        print("  4. Mark known corrupted images")

        choice = input("\nChoice (1-4): ").strip()

        if choice == '1':
            list_unprocessed_images()
        elif choice == '2':
            filename = input("Enter filename: ").strip()
            mark_image_as_processed_by_filename(filename)
        elif choice == '3':
            mark_all_unprocessed_as_processed()
        elif choice == '4':
            # The two corrupted images from the error log
            corrupted_files = [
                '208a.jpg',
                'artzology_mystery_bundle_ (26).jpg'
            ]
            print(f"Marking {len(corrupted_files)} known corrupted images...\n")
            for filename in corrupted_files:
                mark_image_as_processed_by_filename(filename)
        else:
            print("Invalid choice")
