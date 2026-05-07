# Backup functionality
import shutil
from datetime import datetime

def backup_database(backup_dir=None):
    """
    Backup the SQLite database to a timestamped file in the backups folder.
    Returns the backup file path.
    """
    db_path = DATABASE_PATH
    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(db_path), '..', 'backups')
    backup_dir = os.path.abspath(backup_dir)
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'filecat_backup_{timestamp}.db')
    shutil.copy2(db_path, backup_file)
    return backup_file
"""
Database models and operations for FileCat
"""
import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH


def normalize_db_filepath(filepath):
    """
    Normalize relative paths to a canonical DB format that always uses backslashes.
    """
    if filepath is None:
        return None
    normalized = filepath.replace('/', '\\')
    while '\\\\' in normalized:
        normalized = normalized.replace('\\\\', '\\')
    return normalized.strip()


def db_filepath_to_os_path(filepath):
    """
    Convert DB filepath format to the current OS separator for filesystem access.
    """
    if filepath is None:
        return None
    return filepath.replace('\\', os.sep).replace('/', os.sep)


def get_db_connection():
    """Create and return a database connection"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)  # 30 second timeout to prevent locking
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def init_database():
    """Initialize the database with tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Images table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            file_size INTEGER,
            file_checksum TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date_modified TIMESTAMP,
            thumbnail_path TEXT,
            is_tagged BOOLEAN DEFAULT 0,
            integrity_status TEXT DEFAULT 'unchecked',
            integrity_error TEXT,
            integrity_checked_at TIMESTAMP
        )
    ''')
    
    # Tags table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT UNIQUE NOT NULL,
            usage_count INTEGER DEFAULT 0
        )
    ''')
    
    # ImageTags junction table (many-to-many)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS image_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
            UNIQUE(image_id, tag_id)
        )
    ''')
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # AI Suggestions table - Phase 2 AI Auto-Tagging
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            tag_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
        )
    ''')

    # Migration: add file_checksum column if missing
    cursor.execute("PRAGMA table_info(images)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'file_checksum' not in columns:
        cursor.execute('ALTER TABLE images ADD COLUMN file_checksum TEXT')

    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_filepath ON images(filepath)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_is_tagged ON images(is_tagged)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tag_name ON tags(tag_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_image_tags ON image_tags(image_id, tag_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_suggestions ON ai_suggestions(image_id, status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_checksum ON images(file_checksum)')

    # Folder mtimes table for incremental scanning
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS folder_mtimes (
            folder_path TEXT PRIMARY KEY,
            last_mtime REAL NOT NULL
        )
    ''')

    # Normalize any legacy filepath separators (e.g. old Linux "/" entries)
    cursor.execute('SELECT id, filepath FROM images')
    for row in cursor.fetchall():
        normalized = normalize_db_filepath(row['filepath'])
        if normalized != row['filepath']:
            cursor.execute('UPDATE images SET filepath = ? WHERE id = ?', (normalized, row['id']))

    # Normalize folder_mtimes keys so incremental scanning works cross-platform
    cursor.execute('SELECT folder_path, last_mtime FROM folder_mtimes')
    folder_rows = cursor.fetchall()
    for row in folder_rows:
        normalized_folder = normalize_db_filepath(row['folder_path'])
        if normalized_folder != row['folder_path']:
            cursor.execute('DELETE FROM folder_mtimes WHERE folder_path = ?', (row['folder_path'],))
            cursor.execute(
                'INSERT OR REPLACE INTO folder_mtimes (folder_path, last_mtime) VALUES (?, ?)',
                (normalized_folder, row['last_mtime'])
            )

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


# Image operations
def add_image(filepath, filename, file_size, date_modified, thumbnail_path=None):
    """Add a new image to the database"""
    filepath = normalize_db_filepath(filepath)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO images (filepath, filename, file_size, date_modified, thumbnail_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (filepath, filename, file_size, date_modified, thumbnail_path))
        conn.commit()
        image_id = cursor.lastrowid
        return image_id
    except sqlite3.IntegrityError:
        # Image already exists
        return None
    finally:
        conn.close()


def get_image_by_id(image_id):
    """Get image by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM images WHERE id = ?', (image_id,))
    image = cursor.fetchone()
    conn.close()
    return dict(image) if image else None


def get_all_images(limit=None, offset=0, sort_by='filename', sort_order='ASC', tagged_filter=None):
    """Get all images with pagination and sorting"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    valid_sort_columns = ['filename', 'filepath', 'file_size', 'date_added', 'date_modified']
    if sort_by not in valid_sort_columns:
        sort_by = 'filename'
    
    valid_orders = ['ASC', 'DESC']
    if sort_order.upper() not in valid_orders:
        sort_order = 'ASC'
    
    where_clause = ''
    if tagged_filter == 'true':
        where_clause = ' WHERE is_tagged = 1'
    elif tagged_filter == 'false':
        where_clause = ' WHERE is_tagged = 0'
    
    query = f'SELECT * FROM images{where_clause} ORDER BY {sort_by} {sort_order}'
    
    if limit:
        query += f' LIMIT {limit} OFFSET {offset}'
    
    cursor.execute(query)
    images = cursor.fetchall()
    conn.close()
    return [dict(img) for img in images]


def get_untagged_images(limit=None):
    """Get images that haven't been tagged yet"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM images WHERE is_tagged = 0 ORDER BY filepath'
    if limit:
        query += f' LIMIT {limit}'
    
    cursor.execute(query)
    images = cursor.fetchall()
    conn.close()
    return [dict(img) for img in images]


def update_image_tagged_status(image_id, is_tagged=True):
    """Mark an image as tagged or untagged"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE images SET is_tagged = ? WHERE id = ?', (is_tagged, image_id))
    conn.commit()
    conn.close()


def get_images_count():
    """Get total number of images"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM images')
    count = cursor.fetchone()['count']
    conn.close()
    return count


def get_tagged_images_count():
    """Get number of tagged images"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM images WHERE is_tagged = 1')
    count = cursor.fetchone()['count']
    conn.close()
    return count


def get_untagged_images_count():
    """Get number of untagged images"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM images WHERE is_tagged = 0')
    count = cursor.fetchone()['count']
    conn.close()
    return count


def delete_image(image_id):
    """Delete an image from database (cascade deletes tags)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM images WHERE id = ?', (image_id,))
    conn.commit()
    conn.close()


def fix_tagged_status():
    """Fix inconsistent is_tagged status - mark images with no tags as untagged"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find all images marked as tagged but have no tags
    cursor.execute('''
        SELECT i.id 
        FROM images i 
        WHERE i.is_tagged = 1 
        AND NOT EXISTS (
            SELECT 1 FROM image_tags it WHERE it.image_id = i.id
        )
    ''')
    
    inconsistent_images = cursor.fetchall()
    fixed_count = 0
    
    for row in inconsistent_images:
        cursor.execute('UPDATE images SET is_tagged = 0 WHERE id = ?', (row['id'],))
        fixed_count += 1
    
    conn.commit()
    conn.close()
    
    return fixed_count


# Tag operations
def add_tag(tag_name):
    """Add a new tag or return existing tag ID"""
    tag_name = tag_name.strip().lower()
    if not tag_name:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if tag exists
    cursor.execute('SELECT id FROM tags WHERE tag_name = ?', (tag_name,))
    result = cursor.fetchone()
    
    if result:
        tag_id = result['id']
    else:
        cursor.execute('INSERT INTO tags (tag_name, usage_count) VALUES (?, 0)', (tag_name,))
        conn.commit()
        tag_id = cursor.lastrowid
    
    conn.close()
    return tag_id


def get_all_tags():
    """Get all tags sorted by usage count"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags ORDER BY usage_count DESC, tag_name ASC')
    tags = cursor.fetchall()
    conn.close()
    return [dict(tag) for tag in tags]


def search_tags(query):
    """Search tags by partial match"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tags WHERE tag_name LIKE ? ORDER BY usage_count DESC LIMIT 20', 
                   (f'%{query}%',))
    tags = cursor.fetchall()
    conn.close()
    return [dict(tag) for tag in tags]


def rename_tag(tag_id, new_name):
    """Rename a tag"""
    new_name = new_name.strip().lower()
    if not new_name:
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE tags SET tag_name = ? WHERE id = ?', (new_name, tag_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Tag name already exists
        return False
    finally:
        conn.close()


def merge_tags(source_tag_id, target_tag_id):
    """Merge source tag into target tag"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all images with source tag
    cursor.execute('SELECT image_id FROM image_tags WHERE tag_id = ?', (source_tag_id,))
    image_ids = [row['image_id'] for row in cursor.fetchall()]
    
    # Add target tag to all those images (if not already present)
    for image_id in image_ids:
        try:
            cursor.execute('INSERT INTO image_tags (image_id, tag_id) VALUES (?, ?)', 
                          (image_id, target_tag_id))
        except sqlite3.IntegrityError:
            # Already has this tag, skip
            pass
    
    # Delete all source tag associations
    cursor.execute('DELETE FROM image_tags WHERE tag_id = ?', (source_tag_id,))
    
    # Delete source tag
    cursor.execute('DELETE FROM tags WHERE id = ?', (source_tag_id,))
    
    # Recalculate usage count for target tag
    cursor.execute('SELECT COUNT(*) as count FROM image_tags WHERE tag_id = ?', (target_tag_id,))
    count = cursor.fetchone()['count']
    cursor.execute('UPDATE tags SET usage_count = ? WHERE id = ?', (count, target_tag_id))
    
    conn.commit()
    conn.close()
    return True


def delete_tag(tag_id):
    """Delete a tag and all its associations"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all images that have this tag
    cursor.execute('SELECT DISTINCT image_id FROM image_tags WHERE tag_id = ?', (tag_id,))
    affected_images = [row['image_id'] for row in cursor.fetchall()]
    
    # Delete the tag associations
    cursor.execute('DELETE FROM image_tags WHERE tag_id = ?', (tag_id,))
    cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
    
    # Update is_tagged status for images that now have no tags
    for image_id in affected_images:
        cursor.execute('SELECT COUNT(*) as count FROM image_tags WHERE image_id = ?', (image_id,))
        tag_count = cursor.fetchone()['count']
        if tag_count == 0:
            cursor.execute('UPDATE images SET is_tagged = 0 WHERE id = ?', (image_id,))
    
    conn.commit()
    conn.close()
    return True


def bulk_add_tag_to_images(image_ids, tag_name):
    """Add a tag to multiple images"""
    tag_name = tag_name.strip().lower()
    if not tag_name:
        return False
    
    # Get or create tag
    tag_id = add_tag(tag_name)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    added_count = 0
    for image_id in image_ids:
        try:
            cursor.execute('INSERT INTO image_tags (image_id, tag_id) VALUES (?, ?)', 
                          (image_id, tag_id))
            added_count += 1
        except sqlite3.IntegrityError:
            # Already has this tag
            pass
    
    # Update tag usage count
    cursor.execute('UPDATE tags SET usage_count = usage_count + ? WHERE id = ?', 
                   (added_count, tag_id))
    
    conn.commit()
    conn.close()
    return added_count


# Image-Tag relationship operations
def add_image_tag(image_id, tag_id):
    """Associate a tag with an image"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO image_tags (image_id, tag_id) VALUES (?, ?)', 
                      (image_id, tag_id))
        # Update tag usage count
        cursor.execute('UPDATE tags SET usage_count = usage_count + 1 WHERE id = ?', (tag_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Association already exists
        return False
    finally:
        conn.close()


def remove_image_tag(image_id, tag_id):
    """Remove tag from image"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM image_tags WHERE image_id = ? AND tag_id = ?', 
                  (image_id, tag_id))
    # Update tag usage count
    cursor.execute('UPDATE tags SET usage_count = usage_count - 1 WHERE id = ?', (tag_id,))
    
    # Check if image still has any tags, update is_tagged status
    cursor.execute('SELECT COUNT(*) as count FROM image_tags WHERE image_id = ?', (image_id,))
    tag_count = cursor.fetchone()['count']
    if tag_count == 0:
        cursor.execute('UPDATE images SET is_tagged = 0 WHERE id = ?', (image_id,))
    
    conn.commit()
    conn.close()


def get_image_tags(image_id):
    """Get all tags for an image"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.* FROM tags t
        JOIN image_tags it ON t.id = it.tag_id
        WHERE it.image_id = ?
        ORDER BY t.tag_name
    ''', (image_id,))
    tags = cursor.fetchall()
    conn.close()
    return [dict(tag) for tag in tags]


def search_images_by_tags(tag_names, match_all=True):
    """Search images by tags
    
    Args:
        tag_names: List of tag names to search for
        match_all: If True, image must have ALL tags (AND). If False, ANY tag (OR)
    """
    if not tag_names:
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Convert tag names to IDs
    placeholders = ','.join('?' * len(tag_names))
    cursor.execute(f'SELECT id FROM tags WHERE tag_name IN ({placeholders})', tag_names)
    tag_ids = [row['id'] for row in cursor.fetchall()]
    
    if not tag_ids:
        conn.close()
        return []
    
    if match_all:
        # Must have ALL tags (AND logic)
        # Count how many of the specified tags each image has
        placeholders = ','.join('?' * len(tag_ids))
        query = f'''
            SELECT i.* FROM images i
            JOIN image_tags it ON i.id = it.image_id
            WHERE it.tag_id IN ({placeholders})
            GROUP BY i.id
            HAVING COUNT(DISTINCT it.tag_id) = ?
            ORDER BY i.filename
        '''
        cursor.execute(query, tag_ids + [len(tag_ids)])
    else:
        # Must have ANY tag (OR logic)
        placeholders = ','.join('?' * len(tag_ids))
        query = f'''
            SELECT DISTINCT i.* FROM images i
            JOIN image_tags it ON i.id = it.image_id
            WHERE it.tag_id IN ({placeholders})
            ORDER BY i.filename
        '''
        cursor.execute(query, tag_ids)
    
    images = cursor.fetchall()
    conn.close()
    return [dict(img) for img in images]


def search_images_by_filename(query):
    """Search images by filename"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM images WHERE filename LIKE ? ORDER BY filename', 
                   (f'%{query}%',))
    images = cursor.fetchall()
    conn.close()
    return [dict(img) for img in images]


def search_images_by_date_range(date_from=None, date_to=None):
    """Search images by date range (using date_added)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM images WHERE 1=1'
    params = []
    
    if date_from:
        query += ' AND DATE(date_added) >= ?'
        params.append(date_from)
    
    if date_to:
        query += ' AND DATE(date_added) <= ?'
        params.append(date_to)
    
    query += ' ORDER BY date_added DESC'
    
    cursor.execute(query, params)
    images = cursor.fetchall()
    conn.close()
    return [dict(img) for img in images]


# AI Suggestions operations - Phase 2 Feature
def save_ai_suggestions(image_id, suggestions):
    """
    Save AI-generated tag suggestions for an image

    Args:
        image_id: Image ID
        suggestions: List of tuples (tag_name, confidence)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear old suggestions for this image
    cursor.execute('DELETE FROM ai_suggestions WHERE image_id = ?', (image_id,))

    # Insert new suggestions
    if suggestions:
        for tag_name, confidence in suggestions:
            cursor.execute('''
                INSERT INTO ai_suggestions (image_id, tag_name, confidence, status)
                VALUES (?, ?, ?, 'pending')
            ''', (image_id, tag_name, confidence))
    else:
        # No suggestions - insert a placeholder to mark as processed
        # This prevents the image from appearing as "unprocessed"
        cursor.execute('''
            INSERT INTO ai_suggestions (image_id, tag_name, confidence, status)
            VALUES (?, ?, ?, 'processed')
        ''', (image_id, '__NO_SUGGESTIONS__', 0.0))

    conn.commit()
    conn.close()


def get_ai_suggestions(image_id, status='pending'):
    """
    Get AI suggestions for an image

    Args:
        image_id: Image ID
        status: Filter by status ('pending', 'accepted', 'rejected', or None for all)

    Returns:
        List of suggestion dicts
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if status:
        cursor.execute('''
            SELECT * FROM ai_suggestions 
            WHERE image_id = ? AND status = ?
            ORDER BY confidence DESC
        ''', (image_id, status))
    else:
        cursor.execute('''
            SELECT * FROM ai_suggestions 
            WHERE image_id = ?
            ORDER BY confidence DESC
        ''', (image_id,))

    suggestions = cursor.fetchall()
    conn.close()
    return [dict(s) for s in suggestions]


def accept_ai_suggestion(suggestion_id):
    """
    Accept an AI suggestion and add it as a real tag

    Args:
        suggestion_id: AI suggestion ID

    Returns:
        Success boolean
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get the suggestion
        cursor.execute('SELECT * FROM ai_suggestions WHERE id = ?', (suggestion_id,))
        suggestion = cursor.fetchone()

        if not suggestion:
            conn.close()
            return False

        image_id = suggestion['image_id']
        tag_name = suggestion['tag_name']

        # Add tag to tags table (or get existing)
        tag_id = add_tag(tag_name)

        # Add to image_tags
        add_image_tag(image_id, tag_id)

        # Mark suggestion as accepted
        cursor.execute('''
            UPDATE ai_suggestions 
            SET status = 'accepted' 
            WHERE id = ?
        ''', (suggestion_id,))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"[Database] Error accepting suggestion: {e}")
        conn.close()
        return False


def reject_ai_suggestion(suggestion_id):
    """Mark an AI suggestion as rejected"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE ai_suggestions 
        SET status = 'rejected' 
        WHERE id = ?
    ''', (suggestion_id,))

    conn.commit()
    conn.close()
    return True


def accept_all_ai_suggestions(image_id):
    """
    Accept all pending AI suggestions for an image

    Args:
        image_id: Image ID

    Returns:
        Number of suggestions accepted
    """
    suggestions = get_ai_suggestions(image_id, status='pending')
    count = 0

    for suggestion in suggestions:
        if accept_ai_suggestion(suggestion['id']):
            count += 1

    return count


def clear_ai_suggestions(image_id, status=None):
    """
    Clear AI suggestions for an image

    Args:
        image_id: Image ID
        status: Only clear suggestions with this status (None for all)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if status:
        cursor.execute('DELETE FROM ai_suggestions WHERE image_id = ? AND status = ?', (image_id, status))
    else:
        cursor.execute('DELETE FROM ai_suggestions WHERE image_id = ?', (image_id,))

    conn.commit()
    conn.close()


def get_images_without_ai_suggestions(limit=None):
    """
    Get images that haven't been analyzed by AI yet (no ai_suggestions records)
    Excludes images with integrity issues
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT i.* FROM images i
        LEFT JOIN ai_suggestions ai ON i.id = ai.image_id
        WHERE ai.id IS NULL
        AND (i.integrity_status IS NULL OR i.integrity_status IN ('unchecked', 'valid'))
        ORDER BY i.date_added DESC
    '''

    if limit:
        query += f' LIMIT {limit}'

    cursor.execute(query)
    images = cursor.fetchall()
    conn.close()
    return [dict(img) for img in images]


def get_untagged_images_for_ai(limit=None):
    """
    Get images that need AI tagging (truly untagged images)
    Returns images where:
    - is_tagged = 0 (no tags applied)
    - No integrity issues
    This is what the dashboard should show for "Images that need tags"
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = '''
        SELECT i.* FROM images i
        WHERE i.is_tagged = 0
        AND (i.integrity_status IS NULL OR i.integrity_status IN ('unchecked', 'valid'))
        AND NOT EXISTS (
            SELECT 1 FROM ai_suggestions ai
            WHERE ai.image_id = i.id
            AND ai.status = 'processed'
            AND ai.tag_name = '__NO_SUGGESTIONS__'
        )
        ORDER BY i.date_added DESC
    '''

    if limit:
        query += f' LIMIT {limit}'

    cursor.execute(query)
    images = cursor.fetchall()
    conn.close()
    return [dict(img) for img in images]


def update_image_integrity(image_id, status, error_message=None):
    """
    Update integrity status of an image

    Args:
        image_id: Image ID
        status: 'valid', 'missing', 'corrupted', or 'unchecked'
        error_message: Optional error message
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE images 
        SET integrity_status = ?, 
            integrity_error = ?, 
            integrity_checked_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (status, error_message, image_id))

    conn.commit()
    conn.close()


def get_images_with_integrity_issues():
    """Get all images with integrity issues (missing or corrupted)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM images 
        WHERE integrity_status IN ('missing', 'corrupted')
        ORDER BY integrity_checked_at DESC
    ''')

    images = cursor.fetchall()
    conn.close()
    return [dict(img) for img in images]


def get_integrity_stats():
    """Get statistics on file integrity"""
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}

    # Count by status
    cursor.execute('''
        SELECT integrity_status, COUNT(*) as count 
        FROM images 
        GROUP BY integrity_status
    ''')

    for row in cursor.fetchall():
        status = row['integrity_status'] or 'unchecked'
        stats[status] = row['count']

    conn.close()
    return stats


# Folder mtime operations for incremental scanning

def get_all_folder_mtimes():
    """Get all stored folder mtimes as a dict"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT folder_path, last_mtime FROM folder_mtimes')
    result = {row['folder_path']: row['last_mtime'] for row in cursor.fetchall()}
    conn.close()
    return result


def save_folder_mtimes(folder_mtime_dict):
    """Bulk save folder mtimes"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executemany(
        'INSERT OR REPLACE INTO folder_mtimes (folder_path, last_mtime) VALUES (?, ?)',
        list(folder_mtime_dict.items())
    )
    conn.commit()
    conn.close()


def remove_folder_mtime(folder_path):
    """Remove a folder mtime entry (e.g. folder was deleted)"""
    conn = get_db_connection()
    conn.execute('DELETE FROM folder_mtimes WHERE folder_path = ?', (folder_path,))
    conn.commit()
    conn.close()
