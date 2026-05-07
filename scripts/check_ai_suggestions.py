#!/usr/bin/env python3
"""
Check AI suggestions for specific image IDs
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# Check both images
for image_id in [7314, 743]:
    cursor.execute('SELECT * FROM ai_suggestions WHERE image_id = ?', (image_id,))
    suggestions = cursor.fetchall()
    print(f'\nImage ID {image_id}:')
    if suggestions:
        for s in suggestions:
            print(f'  Tag: {dict(s)["tag_name"]}, Confidence: {dict(s)["confidence"]}, Status: {dict(s)["status"]}')
    else:
        print('  No suggestions found')

# Also check the get_images_without_ai_suggestions query
print("\n" + "="*60)
print("Checking which images are considered 'unprocessed'...")
cursor.execute('''
    SELECT i.id, i.filename FROM images i
    LEFT JOIN ai_suggestions ai ON i.id = ai.image_id
    WHERE ai.id IS NULL
    ORDER BY i.date_added DESC
    LIMIT 10
''')
unprocessed = cursor.fetchall()
print(f"Found {cursor.execute('SELECT COUNT(*) FROM images i LEFT JOIN ai_suggestions ai ON i.id = ai.image_id WHERE ai.id IS NULL').fetchone()[0]} total unprocessed images")
print("\nFirst 10:")
for img in unprocessed:
    print(f"  ID {dict(img)['id']}: {dict(img)['filename']}")

conn.close()
