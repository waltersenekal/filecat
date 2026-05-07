#!/usr/bin/env python3
"""
Script to mark corrupted/problematic images as corrupted in integrity status
This prevents them from being stuck in the auto-tag loop
"""

from database import get_db_connection, update_image_integrity

def find_and_mark_corrupted_images():
    """Find the 2 problematic images from the error log and mark them as corrupted"""

    problematic_files = [
        "208a.jpg",  # Style24 Design/Free Files/Free Files Original/Separate Files/208a.jpg
        "artzology_mystery_bundle_ (26).jpg"  # Artzology folder
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    marked_count = 0

    for filename in problematic_files:
        # Find the image in database
        cursor.execute("SELECT id, filename, filepath FROM images WHERE filename = ?", (filename,))
        images = cursor.fetchall()

        if images:
            for img in images:
                image_id = img['id']
                print(f"Found: {img['filepath']}")

                # Check current integrity status
                cursor.execute("SELECT integrity_status FROM images WHERE id = ?", (image_id,))
                result = cursor.fetchone()

                if result['integrity_status'] != 'corrupted':
                    # Mark as corrupted in database
                    update_image_integrity(image_id, 'corrupted', 'image file is truncated (7 bytes not processed)')
                    print(f"  ✓ Marked as corrupted in database")
                    marked_count += 1
                else:
                    print(f"  - Already marked as corrupted")
        else:
            print(f"Not found in database: {filename}")

    conn.close()

    print(f"\n✅ Marked {marked_count} corrupted image(s) with integrity status")
    print("These images will no longer be processed by the auto-tagger")
    print("You can manage them via the Integrity page at /integrity")

    return marked_count

if __name__ == "__main__":
    print("FileCat - Fix Corrupted Images")
    print("=" * 60)
    print("This script will mark corrupted images as processed")
    print("so they don't block the auto-tagging loop")
    print("=" * 60)
    print()

    marked = find_and_mark_corrupted_images()

    if marked > 0:
        print("\n" + "=" * 60)
        print("✅ DONE! You can now restart the auto-tagger.")
        print("=" * 60)
