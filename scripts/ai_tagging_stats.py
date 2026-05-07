#!/usr/bin/env python3
"""
Check overall AI tagging statistics
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

print("AI TAGGING STATISTICS")
print("="*60)

# Total images
cursor.execute('SELECT COUNT(*) as count FROM images')
total_images = cursor.fetchone()['count']
print(f"\nTotal images in database: {total_images}")

# Images with AI suggestions (processed)
cursor.execute('SELECT COUNT(DISTINCT image_id) as count FROM ai_suggestions')
processed_images = cursor.fetchone()['count']
print(f"Images with AI suggestions: {processed_images}")

# Images without AI suggestions (unprocessed)
unprocessed = total_images - processed_images
print(f"Images without AI suggestions: {unprocessed}")

# Breakdown by status
print("\nBreakdown of AI suggestions:")
cursor.execute('''
    SELECT status, COUNT(*) as count 
    FROM ai_suggestions 
    GROUP BY status
''')
for row in cursor.fetchall():
    print(f"  {dict(row)['status']}: {dict(row)['count']}")

# Images with NO_SUGGESTIONS marker (corrupted/failed)
cursor.execute('''
    SELECT COUNT(DISTINCT image_id) as count 
    FROM ai_suggestions 
    WHERE tag_name = '__NO_SUGGESTIONS__'
''')
no_suggestions_count = cursor.fetchone()['count']
print(f"\nImages marked as 'no suggestions' (corrupted/failed): {no_suggestions_count}")

# Images with actual tags from AI
cursor.execute('''
    SELECT COUNT(DISTINCT image_id) as count 
    FROM ai_suggestions 
    WHERE tag_name != '__NO_SUGGESTIONS__'
''')
with_tags_count = cursor.fetchone()['count']
print(f"Images with actual AI tags: {with_tags_count}")

# Sample of NO_SUGGESTIONS images
print("\nSample of images with no suggestions (first 5):")
cursor.execute('''
    SELECT DISTINCT i.id, i.filename, i.filepath
    FROM images i
    JOIN ai_suggestions ai ON i.id = ai.image_id
    WHERE ai.tag_name = '__NO_SUGGESTIONS__'
    LIMIT 5
''')
for row in cursor.fetchall():
    row_dict = dict(row)
    print(f"  ID {row_dict['id']}: {row_dict['filename']}")

conn.close()
