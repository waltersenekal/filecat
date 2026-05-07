"""
FileCat - Image Cataloging System
Main Flask Application
"""
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, Response
import os
import json
import csv
from datetime import datetime
import zipfile
import io
import threading
import time
import atexit
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from config import *
from database import *
from scanner import scan_folder, check_missing_files, get_scan_summary
from thumbnail_generator import generate_thumbnail, regenerate_all_thumbnails
try:
    from ai_tagger import analyze_image, analyze_image_batch, suggest_tags_for_maintenance
    AI_TAGGER_AVAILABLE = True
except Exception as e:
    print(f"[WARNING] AI tagger not available: {e}")
    AI_TAGGER_AVAILABLE = False
    def analyze_image(*args, **kwargs): return []
    def analyze_image_batch(*args, **kwargs): return []
    def suggest_tags_for_maintenance(*args, **kwargs): return []
from file_integrity import (
    scan_database_integrity, cleanup_missing_files, check_file_integrity,
    handle_corrupted_file, scan_for_new_files, add_new_file
)

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# Ensure required directories exist
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Progress data for thumbnail regeneration
progress_data = {'current': 0, 'total': 1, 'done': False, 'success': 0, 'failed': 0}

# Progress data for download operations
download_progress = {'current': 0, 'total': 1, 'done': False, 'filename': '', 'error': None}

# Progress data for AI analysis - Phase 2 Feature
ai_analysis_progress = {'current': 0, 'total': 1, 'done': False, 'current_file': '', 'error': None, 'tags_added': 0}

# Background auto-tagging state
auto_tag_running = False
auto_tag_thread = None
auto_tag_stop_event = threading.Event()
auto_tag_stats = {
    'enabled': AUTO_TAG_ENABLED,
    'last_run': None,
    'next_run': None,
    'images_processed': 0,
    'tags_added': 0,
    'errors': 0,
    'is_running': False
}


def auto_tag_background_task():
    """Background task that periodically scans and tags new images"""
    global auto_tag_stats

    print("[AUTO-TAG] Background auto-tagging service started")
    print(f"[AUTO-TAG] Interval: {AUTO_TAG_INTERVAL} seconds ({AUTO_TAG_INTERVAL/60:.1f} minutes)")
    print(f"[AUTO-TAG] Batch size: {AUTO_TAG_BATCH_SIZE} images per run")

    while not auto_tag_stop_event.is_set():
        try:
            if AUTO_TAG_ENABLED:
                if not AI_TAGGER_AVAILABLE:
                    print("[AUTO-TAG] AI tagger not available (STAG dependencies missing). Disabling auto-tag.")
                    break

                auto_tag_stats['is_running'] = True
                auto_tag_stats['last_run'] = datetime.now().isoformat()

                print(f"\n[AUTO-TAG] {'='*60}")
                print(f"[AUTO-TAG] Starting automatic scan and tag cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"[AUTO-TAG] {'='*60}")

                # Step 1: Scan for new files
                print(f"[AUTO-TAG] Step 1: Scanning for new files...")
                scan_result = scan_folder()
                new_files = scan_result.get('added', 0)
                print(f"[AUTO-TAG] Found {new_files} new file(s)")

                # Step 2: Process batches continuously until all images are tagged
                batch_number = 0
                total_processed_this_run = 0
                total_tags_this_run = 0

                while not auto_tag_stop_event.is_set():
                    batch_number += 1

                    # Find untagged images (that need AI tagging)
                    print(f"[AUTO-TAG] Step 2: Finding untagged images (batch #{batch_number})...")
                    from database import get_untagged_images_for_ai
                    untagged = get_untagged_images_for_ai()

                    # Limit to batch size
                    images_to_process = untagged[:AUTO_TAG_BATCH_SIZE]

                    if not images_to_process:
                        print(f"[AUTO-TAG] No more untagged images to process")
                        break

                    print(f"[AUTO-TAG] Found {len(untagged)} total untagged, processing batch of {len(images_to_process)}")

                    # Step 3: Auto-tag images
                    print(f"[AUTO-TAG] Step 3: AI tagging batch #{batch_number}...")

                    batch_tags_added = 0
                    for idx, img in enumerate(images_to_process):
                        if auto_tag_stop_event.is_set():
                            print(f"[AUTO-TAG] Stop requested, exiting...")
                            break

                        image_id = img['id']  # Set this first, before try block

                        try:
                            image_path = os.path.join(SOURCE_FOLDER, db_filepath_to_os_path(img['filepath']))

                            if not os.path.exists(image_path):
                                print(f"[AUTO-TAG]   ⚠️ Skipping missing file: {img['filename']}")
                                # Mark as processed even though file is missing
                                save_ai_suggestions(image_id, [])
                                auto_tag_stats['images_processed'] += 1
                                continue

                            print(f"[AUTO-TAG]   Processing {idx+1}/{len(images_to_process)}: {img['filename']}", flush=True)

                            # Get existing tags
                            existing_tags = get_image_tags(image_id)
                            existing_tag_names = [tag['tag_name'] for tag in existing_tags]

                            # Analyze with AI - pass image_id for corruption tracking
                            suggestions = suggest_tags_for_maintenance(
                                image_path,
                                existing_tags=existing_tag_names,
                                max_suggestions=10,
                                image_id=image_id  # Pass ID for corruption tracking
                            )

                            if suggestions is None:
                                # Image is corrupted - marked in DB, skip it
                                print(f"[AUTO-TAG]     ❌ Image corrupted (marked in database)")
                                auto_tag_stats['errors'] += 1
                                auto_tag_stats['images_processed'] += 1
                                # Don't save AI suggestions - let integrity status handle it
                                continue

                            if suggestions:
                                # Auto-add tags
                                tags_added = 0
                                for tag_name, confidence in suggestions:
                                    tag_id = add_tag(tag_name)
                                    if tag_id and add_image_tag(image_id, tag_id):
                                        tags_added += 1

                                # Mark as tagged
                                update_image_tagged_status(image_id, True)

                                # Save suggestions for review
                                save_ai_suggestions(image_id, suggestions)

                                auto_tag_stats['images_processed'] += 1
                                auto_tag_stats['tags_added'] += tags_added
                                batch_tags_added += tags_added

                                print(f"[AUTO-TAG]     ✓ Added {tags_added} tags")
                            else:
                                # No suggestions - save empty list to mark as processed
                                save_ai_suggestions(image_id, [])
                                auto_tag_stats['images_processed'] += 1
                                print(f"[AUTO-TAG]     ⚠️ No tags suggested (marked as processed)")

                        except Exception as e:
                            # Mark as processed even on error to prevent infinite retry
                            auto_tag_stats['errors'] += 1
                            print(f"[AUTO-TAG]     ❌ Error processing {img['filename']}: {e}")

                            try:
                                # CRITICAL: Always mark as processed to avoid infinite loop
                                save_ai_suggestions(image_id, [])
                                auto_tag_stats['images_processed'] += 1
                                print(f"[AUTO-TAG]     ✓ Marked as processed to prevent retry loop")
                            except Exception as save_error:
                                # This is BAD - we couldn't save the error marker
                                print(f"[AUTO-TAG]     ❌❌ CRITICAL: Failed to mark as processed: {save_error}")
                                print(f"[AUTO-TAG]     ❌❌ Image {image_id} ({img['filename']}) may loop forever!")
                                import traceback
                                traceback.print_exc()

                    total_processed_this_run += len(images_to_process)
                    total_tags_this_run += batch_tags_added

                    print(f"[AUTO-TAG] Batch #{batch_number} complete: {len(images_to_process)} images, {batch_tags_added} tags added")

                    # Check if there are more images to process
                    remaining = get_untagged_images_for_ai()
                    if remaining:
                        print(f"[AUTO-TAG] 📋 {len(remaining)} images still to tag, starting next batch immediately...")
                        # No sleep - continue immediately to next batch
                    else:
                        print(f"[AUTO-TAG] ✅ All images tagged!")
                        break

                print(f"[AUTO-TAG] Run complete: {batch_number} batch(es), {total_processed_this_run} images, {total_tags_this_run} tags")
                print(f"[AUTO-TAG] {'='*60}\n")

            auto_tag_stats['is_running'] = False

            # Only wait the interval if we're done with all images
            if not auto_tag_stop_event.is_set():
                next_run = datetime.now().timestamp() + AUTO_TAG_INTERVAL
                auto_tag_stats['next_run'] = datetime.fromtimestamp(next_run).isoformat()

                print(f"[AUTO-TAG] All caught up. Next scan in {AUTO_TAG_INTERVAL/60:.1f} minutes...")

                # Sleep but check for stop event periodically
                for _ in range(AUTO_TAG_INTERVAL):
                    if auto_tag_stop_event.is_set():
                        break
                    time.sleep(1)

        except Exception as e:
            print(f"[AUTO-TAG] ❌ Background task error: {e}")
            import traceback
            traceback.print_exc()
            auto_tag_stats['errors'] += 1
            # Wait a bit before retrying
            time.sleep(60)

    print("[AUTO-TAG] Background auto-tagging service stopped")


def start_auto_tag_service():
    """Start the background auto-tagging service"""
    global auto_tag_thread, auto_tag_running

    if not AUTO_TAG_ENABLED:
        print("[AUTO-TAG] Auto-tagging is disabled in config")
        return

    if auto_tag_running:
        print("[AUTO-TAG] Service already running")
        return

    auto_tag_running = True
    auto_tag_stop_event.clear()
    auto_tag_thread = threading.Thread(target=auto_tag_background_task, daemon=True)
    auto_tag_thread.start()

    print("[AUTO-TAG] Background service started successfully")


def stop_auto_tag_service():
    """Stop the background auto-tagging service"""
    global auto_tag_running

    if not auto_tag_running:
        return

    print("[AUTO-TAG] Stopping background service...")
    auto_tag_stop_event.set()

    if auto_tag_thread:
        auto_tag_thread.join(timeout=10)

    auto_tag_running = False
    print("[AUTO-TAG] Background service stopped")


# Register cleanup on exit
atexit.register(stop_auto_tag_service)


@app.route('/')
def index():
    """Main dashboard"""
    summary = get_scan_summary()
    return render_template('index.html', summary=summary)


@app.route('/maintenance')
def maintenance():
    """Maintenance mode for tagging images"""
    return render_template('maintenance.html')


@app.route('/search')
def search():
    """Search and browse images"""
    return render_template('search.html', 
                         items_per_page_options=ITEMS_PER_PAGE_OPTIONS,
                         default_items_per_page=DEFAULT_ITEMS_PER_PAGE)


@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_from_directory(
        os.path.join(app.root_path, 'static', 'img'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """Serve thumbnail images"""
    return send_from_directory(THUMBNAIL_FOLDER, filename)


@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve original source images"""
    normalized = db_filepath_to_os_path(filename)
    normalized = os.path.normpath(normalized)
    source_abs = os.path.abspath(SOURCE_FOLDER)
    file_abs = os.path.abspath(os.path.join(source_abs, normalized))
    if os.path.commonpath([source_abs, file_abs]) != source_abs:
        return jsonify({'error': 'Invalid path'}), 403
    rel_to_source = os.path.relpath(file_abs, source_abs)
    return send_from_directory(SOURCE_FOLDER, rel_to_source)


@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html', config={
        'source_folder': SOURCE_FOLDER,
        'thumbnail_folder': THUMBNAIL_FOLDER,
        'supported_extensions': list(SUPPORTED_EXTENSIONS),
        'default_items_per_page': DEFAULT_ITEMS_PER_PAGE
    })


@app.route('/tags')
def tags():
    """Tag management page"""
    return render_template('tags.html')


@app.route('/browse')
def browse():
    """Browse folders page"""
    return render_template('browse.html')


@app.route('/integrity')
def integrity():
    """File integrity management page"""
    return render_template('integrity.html', config={
        'source_folder': SOURCE_FOLDER
    })


# API Endpoints

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """Scan for new images"""
    results = scan_folder()
    return jsonify(results)


@app.route('/api/scan/summary')
def api_scan_summary():
    """Get scan summary"""
    summary = get_scan_summary()
    return jsonify(summary)


@app.route('/api/scan/missing')
def api_scan_missing():
    """Check for missing files"""
    missing = check_missing_files()
    return jsonify({'missing_files': missing})


@app.route('/api/images')
def api_get_images():
    """Get images with pagination and sorting"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', DEFAULT_ITEMS_PER_PAGE))
    sort_by = request.args.get('sort_by', 'filename')
    sort_order = request.args.get('sort_order', 'ASC')
    tagged_filter = request.args.get('tagged', None)
    
    offset = (page - 1) * per_page
    images = get_all_images(limit=per_page, offset=offset, sort_by=sort_by, sort_order=sort_order, tagged_filter=tagged_filter)
    
    # Get total count based on filter
    if tagged_filter == 'true':
        total_count = get_tagged_images_count()
    elif tagged_filter == 'false':
        total_count = get_untagged_images_count()
    else:
        total_count = get_images_count()
    
    # Add tags to each image
    for img in images:
        img['tags'] = get_image_tags(img['id'])
    
    return jsonify({
        'images': images,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    })


@app.route('/api/images/<int:image_id>', methods=['GET'])
def api_get_single_image(image_id):
    """Get a single image with its tags"""
    image = get_image_by_id(image_id)
    if not image:
        return jsonify({'error': 'Image not found'}), 404
    
    image['tags'] = get_image_tags(image_id)
    return jsonify(image)


@app.route('/api/images/<int:image_id>', methods=['DELETE'])
def api_delete_image(image_id):
    """Delete an image from the database"""
    try:
        delete_image(image_id)
        return jsonify({'success': True, 'message': 'Image deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/images/cleanup-missing', methods=['POST'])
def api_cleanup_missing_images():
    """Remove all missing files from database"""
    try:
        missing = check_missing_files()
        removed_count = 0
        
        for file in missing:
            delete_image(file['id'])
            removed_count += 1
        
        return jsonify({
            'success': True,
            'removed_count': removed_count,
            'message': f'Removed {removed_count} missing file(s) from database'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/images/untagged')
def api_get_untagged_images():
    """Get untagged images"""
    limit = request.args.get('limit', type=int)
    images = get_untagged_images(limit=limit)
    
    for img in images:
        img['tags'] = get_image_tags(img['id'])
    
    return jsonify({'images': images})


@app.route('/api/images/<int:image_id>')
def api_get_image(image_id):
    """Get single image details"""
    image = get_image_by_id(image_id)
    if image:
        image['tags'] = get_image_tags(image_id)
        return jsonify(image)
    return jsonify({'error': 'Image not found'}), 404


@app.route('/api/images/<int:image_id>/tags', methods=['POST'])
def api_add_image_tags(image_id):
    """Add tags to an image"""
    data = request.json
    tags_input = data.get('tags', '')
    
    # Parse comma-separated tags
    tag_names = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
    
    added_tags = []
    for tag_name in tag_names:
        tag_id = add_tag(tag_name)
        if tag_id:
            if add_image_tag(image_id, tag_id):
                added_tags.append(tag_name)
    
    # Mark image as tagged
    update_image_tagged_status(image_id, True)
    
    return jsonify({
        'success': True,
        'added_tags': added_tags,
        'image_id': image_id
    })


@app.route('/api/images/<int:image_id>/tags/<int:tag_id>', methods=['DELETE'])
def api_remove_image_tag(image_id, tag_id):
    """Remove a tag from an image"""
    remove_image_tag(image_id, tag_id)
    return jsonify({'success': True})


@app.route('/api/tags')
def api_get_tags():
    """Get all tags"""
    tags = get_all_tags()
    return jsonify({'tags': tags})


@app.route('/api/tags/search')
def api_search_tags():
    """Search tags"""
    query = request.args.get('q', '')
    tags = search_tags(query)
    return jsonify({'tags': tags})


@app.route('/api/tags/<int:tag_id>/rename', methods=['POST'])
def api_rename_tag(tag_id):
    """Rename a tag"""
    data = request.json
    new_name = data.get('new_name', '')
    success = rename_tag(tag_id, new_name)
    return jsonify({'success': success})


@app.route('/api/tags/merge', methods=['POST'])
def api_merge_tags():
    """Merge two tags"""
    data = request.json
    source_id = data.get('source_id')
    target_id = data.get('target_id')
    success = merge_tags(source_id, target_id)
    return jsonify({'success': success})


@app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
def api_delete_tag(tag_id):
    """Delete a tag"""
    success = delete_tag(tag_id)
    return jsonify({'success': success})


@app.route('/api/search')
def api_search():
    """
    Search images by tags, filename, and/or date range

    Query parameters:
    - tags: comma-separated tag names
    - match_all: 'true' or 'false' (default: true) - whether to match all tags or any tag
    - filename: search by filename (partial match)
    - q: alias for filename
    - date_from: start date (YYYY-MM-DD)
    - date_to: end date (YYYY-MM-DD)
    """
    try:
        tags_param = request.args.get('tags', '')
        match_all = request.args.get('match_all', 'true').lower() == 'true'
        filename = request.args.get('filename') or request.args.get('q', '')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        results = []

        # Search by tags
        if tags_param:
            tag_names = [t.strip().lower() for t in tags_param.split(',') if t.strip()]
            if tag_names:
                results = search_images_by_tags(tag_names, match_all=match_all)

        # Search by filename
        elif filename:
            results = search_images_by_filename(filename)

        # Search by date range
        elif date_from or date_to:
            results = search_images_by_date_range(date_from=date_from, date_to=date_to)

        # Add tags to each result
        for img in results:
            img['tags'] = get_image_tags(img['id'])

        return jsonify({
            'success': True,
            'images': results,
            'total': len(results)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/browse')
def api_browse():
    """
    Browse folder structure and get images in a specific folder

    Query parameters:
    - path: relative path from SOURCE_FOLDER (empty string for root)
    """
    try:
        rel_path = request.args.get('path', '')

        # Build absolute path
        if rel_path:
            abs_path = os.path.join(SOURCE_FOLDER, rel_path)
        else:
            abs_path = SOURCE_FOLDER

        # Security check: ensure path is within SOURCE_FOLDER
        abs_path = os.path.abspath(abs_path)
        source_folder_abs = os.path.abspath(SOURCE_FOLDER)
        if not abs_path.startswith(source_folder_abs):
            return jsonify({'error': 'Invalid path'}), 403

        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return jsonify({'error': 'Path not found'}), 404

        # Get subfolders
        folders = []
        images_in_folder = []

        try:
            for item in sorted(os.listdir(abs_path)):
                item_path = os.path.join(abs_path, item)

                if os.path.isdir(item_path):
                    # Count items in subfolder
                    try:
                        item_count = len(os.listdir(item_path))
                    except:
                        item_count = 0

                    folders.append({
                        'name': item,
                        'count': item_count
                    })
                elif os.path.isfile(item_path):
                    # Check if it's a supported image
                    _, ext = os.path.splitext(item)
                    if ext.lower() in SUPPORTED_EXTENSIONS:
                        # Get relative path for database lookup
                        rel_file_path = normalize_db_filepath(os.path.relpath(item_path, SOURCE_FOLDER))

                        # Look up in database to get tags and ID
                        from database import get_db_connection
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute('SELECT * FROM images WHERE filepath = ?', (rel_file_path,))
                        img_data = cursor.fetchone()

                        if img_data:
                            img_dict = dict(img_data)
                            img_dict['tags'] = get_image_tags(img_dict['id'])
                            images_in_folder.append(img_dict)

                        conn.close()
        except Exception as e:
            print(f"Error reading directory {abs_path}: {e}")

        return jsonify({
            'success': True,
            'path': rel_path,
            'folders': folders,
            'images': images_in_folder
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# AI Auto-Tagging Endpoints - Phase 2 Feature

@app.route('/api/ai/analyze/<int:image_id>', methods=['POST'])
def api_analyze_single_image(image_id):
    """Analyze a single image with AI and save suggestions"""
    import time
    request_start = time.time()

    print(f"\n{'='*60}")
    print(f"[API DEBUG] 📥 Received AI analysis request for image ID: {image_id}")
    print(f"[API DEBUG] Request from: {request.remote_addr}")
    print(f"{'='*60}")

    try:
        print(f"[API DEBUG] Step 1: Fetching image from database...")
        image = get_image_by_id(image_id)
        if not image:
            print(f"[API DEBUG] ❌ Image not found in database")
            return jsonify({'error': 'Image not found'}), 404

        print(f"[API DEBUG] ✓ Image found: {image['filename']}")
        print(f"[API DEBUG] Image path: {image['filepath']}")

        # Get full image path
        image_path = os.path.join(SOURCE_FOLDER, db_filepath_to_os_path(image['filepath']))
        print(f"[API DEBUG] Full path: {image_path}")

        if not os.path.exists(image_path):
            print(f"[API DEBUG] ❌ Image file not found on disk")
            return jsonify({'error': 'Image file not found'}), 404

        print(f"[API DEBUG] ✓ Image file exists on disk")

        # Get existing tags to filter suggestions
        print(f"[API DEBUG] Step 2: Fetching existing tags...")
        existing_tags = get_image_tags(image_id)
        existing_tag_names = [tag['tag_name'] for tag in existing_tags]
        print(f"[API DEBUG] Existing tags ({len(existing_tags)}): {', '.join(existing_tag_names) if existing_tags else 'none'}")

        # Analyze image with STAG/RAM
        print(f"[API DEBUG] Step 3: Sending to AI for analysis...")
        ai_start = time.time()

        suggestions = suggest_tags_for_maintenance(
            image_path,
            existing_tags=existing_tag_names,
            max_suggestions=10  # STAG can handle more tags
        )

        ai_time = time.time() - ai_start
        print(f"[API DEBUG] ✓ AI analysis completed in {ai_time:.2f}s")
        print(f"[API DEBUG] AI returned {len(suggestions)} suggestions")

        # Save suggestions to database
        print(f"[API DEBUG] Step 4: Saving suggestions to database...")
        save_ai_suggestions(image_id, suggestions)
        print(f"[API DEBUG] ✓ Suggestions saved to database")

        total_time = time.time() - request_start
        print(f"[API DEBUG] 📤 Sending response with {len(suggestions)} suggestions")
        print(f"[API DEBUG] ✅ Total request time: {total_time:.2f}s")
        print(f"{'='*60}\n")

        return jsonify({
            'success': True,
            'image_id': image_id,
            'suggestions': [{'tag': tag, 'confidence': conf} for tag, conf in suggestions]
        })

    except Exception as e:
        error_time = time.time() - request_start
        print(f"[API DEBUG] ❌ Error after {error_time:.2f}s analyzing image {image_id}: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/analyze-batch', methods=['POST'])
def api_analyze_batch():
    """Analyze multiple images with AI in background and automatically add tags"""
    import time

    data = request.json
    image_ids = data.get('image_ids', [])
    auto_tag = data.get('auto_tag', True)  # By default, automatically add tags

    print(f"\n{'='*60}")
    print(f"[BATCH DEBUG] 📥 Received batch AI analysis request")
    print(f"[BATCH DEBUG] Request from: {request.remote_addr}")
    print(f"[BATCH DEBUG] Auto-tag enabled: {auto_tag}")
    print(f"{'='*60}")

    if not image_ids:
        # Analyze all images without AI suggestions
        print(f"[BATCH DEBUG] No specific image IDs provided, finding unanalyzed images...")
        images = get_images_without_ai_suggestions()
        image_ids = [img['id'] for img in images]
        print(f"[BATCH DEBUG] Found {len(image_ids)} unanalyzed images")

    if not image_ids:
        print(f"[BATCH DEBUG] No images to analyze")
        return jsonify({'success': True, 'message': 'No images to analyze'})

    print(f"[BATCH DEBUG] Starting batch analysis of {len(image_ids)} images")
    print(f"[BATCH DEBUG] Launching background thread...")

    def run_analysis():
        batch_start = time.time()

        try:
            print(f"[BATCH DEBUG] Background thread started")

            ai_analysis_progress.update({
                'current': 0,
                'total': len(image_ids),
                'done': False,
                'current_file': '',
                'error': None,
                'tags_added': 0
            })

            tags_added_count = 0

            for idx, image_id in enumerate(image_ids):
                image_start = time.time()

                print(f"\n[BATCH DEBUG] --- Processing image {idx + 1}/{len(image_ids)} (ID: {image_id}) ---")

                image = get_image_by_id(image_id)
                if not image:
                    print(f"[BATCH DEBUG] ⚠️ Image not found, skipping")
                    continue

                ai_analysis_progress['current'] = idx + 1
                ai_analysis_progress['current_file'] = image['filename']

                print(f"[BATCH DEBUG] Processing: {image['filename']}")

                # Get full path
                image_path = os.path.join(SOURCE_FOLDER, db_filepath_to_os_path(image['filepath']))

                if not os.path.exists(image_path):
                    print(f"[BATCH DEBUG] ⚠️ File not found on disk, skipping")
                    continue

                # Get existing tags
                existing_tags = get_image_tags(image_id)
                existing_tag_names = [tag['tag_name'] for tag in existing_tags]
                print(f"[BATCH DEBUG] Existing tags: {len(existing_tags)}")

                # Analyze with STAG/RAM
                print(f"[BATCH DEBUG] Calling AI for analysis...")
                ai_start = time.time()

                suggestions = suggest_tags_for_maintenance(
                    image_path,
                    existing_tags=existing_tag_names,
                    max_suggestions=10  # STAG can handle more tags
                )

                ai_time = time.time() - ai_start
                print(f"[BATCH DEBUG] AI returned {len(suggestions)} suggestions in {ai_time:.2f}s")

                if auto_tag and suggestions:
                    print(f"[BATCH DEBUG] Auto-tagging enabled, adding {len(suggestions)} tags...")
                    # Automatically add all AI-generated tags to the image
                    for tag_name, confidence in suggestions:
                        tag_id = add_tag(tag_name)
                        if tag_id and add_image_tag(image_id, tag_id):
                            tags_added_count += 1
                            print(f"[BATCH DEBUG]   ✓ Added tag: {tag_name} ({confidence:.0%})")

                    # Mark image as tagged
                    update_image_tagged_status(image_id, True)
                    print(f"[BATCH DEBUG] ✓ Image marked as tagged")

                # Also save as suggestions for review (optional)
                save_ai_suggestions(image_id, suggestions)

                ai_analysis_progress['tags_added'] = tags_added_count

                image_time = time.time() - image_start
                print(f"[BATCH DEBUG] Image processed in {image_time:.2f}s (total tags added so far: {tags_added_count})")

            ai_analysis_progress['done'] = True
            batch_time = time.time() - batch_start

            print(f"\n{'='*60}")
            print(f"[BATCH DEBUG] ✅ Batch analysis complete!")
            print(f"[BATCH DEBUG] Total images: {len(image_ids)}")
            print(f"[BATCH DEBUG] Total tags added: {tags_added_count}")
            print(f"[BATCH DEBUG] Total time: {batch_time:.2f}s")
            print(f"[BATCH DEBUG] Average time per image: {batch_time/len(image_ids):.2f}s")
            print(f"{'='*60}\n")

        except Exception as e:
            error_time = time.time() - batch_start
            print(f"[BATCH DEBUG] ❌ Batch analysis error after {error_time:.2f}s: {e}")
            import traceback
            traceback.print_exc()
            ai_analysis_progress['error'] = str(e)
            ai_analysis_progress['done'] = True

    # Start analysis in background
    thread = threading.Thread(target=run_analysis)
    thread.start()

    print(f"[BATCH DEBUG] ✓ Background thread launched successfully")
    print(f"[BATCH DEBUG] 📤 Sending response: started=True, total={len(image_ids)}")
    print(f"{'='*60}\n")

    return jsonify({'started': True, 'total': len(image_ids)})


@app.route('/api/ai/analysis-progress')
def api_ai_analysis_progress():
    """Stream AI analysis progress - Phase 2 Feature"""
    def event_stream():
        last_sent = -1
        while not ai_analysis_progress['done']:
            if ai_analysis_progress['current'] != last_sent or ai_analysis_progress['error']:
                yield f"data: {json.dumps(ai_analysis_progress)}\n\n"
                last_sent = ai_analysis_progress['current']
                if ai_analysis_progress['error']:
                    break
        # Send final result
        yield f"data: {json.dumps(ai_analysis_progress)}\n\n"

    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/ai/suggestions/<int:image_id>')
def api_get_suggestions(image_id):
    """Get AI suggestions for an image"""
    try:
        suggestions = get_ai_suggestions(image_id, status='pending')
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/suggestion/<int:suggestion_id>/accept', methods=['POST'])
def api_accept_suggestion(suggestion_id):
    """Accept an AI suggestion and add as tag"""
    try:
        success = accept_ai_suggestion(suggestion_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/suggestion/<int:suggestion_id>/reject', methods=['POST'])
def api_reject_suggestion(suggestion_id):
    """Reject an AI suggestion"""
    try:
        success = reject_ai_suggestion(suggestion_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/suggestions/<int:image_id>/accept-all', methods=['POST'])
def api_accept_all_suggestions(image_id):
    """Accept all pending AI suggestions for an image"""
    try:
        count = accept_all_ai_suggestions(image_id)
        return jsonify({'success': True, 'accepted': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/settings', methods=['GET'])
def api_get_ai_settings():
    """Get AI tagging settings and status"""
    try:
        # Check if model is available
        from ai_tagger import _model
        model_loaded = _model is not None

        # Get statistics - show untagged images that need AI processing
        from database import get_untagged_images_for_ai
        untagged_for_ai = get_untagged_images_for_ai()

        return jsonify({
            'success': True,
            'model_loaded': model_loaded,
            'model_name': 'STAG/RAM Plus',
            'unanalyzed_count': len(untagged_for_ai),
            'auto_tag': auto_tag_stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/auto-tag/start', methods=['POST'])
def api_start_auto_tag():
    """Start the background auto-tagging service"""
    try:
        start_auto_tag_service()
        return jsonify({'success': True, 'message': 'Auto-tagging service started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/auto-tag/stop', methods=['POST'])
def api_stop_auto_tag():
    """Stop the background auto-tagging service"""
    try:
        stop_auto_tag_service()
        return jsonify({'success': True, 'message': 'Auto-tagging service stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/auto-tag/trigger', methods=['POST'])
def api_trigger_auto_tag():
    """Manually trigger an auto-tag cycle immediately"""
    global auto_tag_stats

    try:
        if not AUTO_TAG_ENABLED:
            return jsonify({'error': 'Auto-tagging is disabled in config'}), 400

        print(f"\n[AUTO-TAG] Manual trigger requested")

        # Don't interrupt if already running
        if auto_tag_stats['is_running']:
            return jsonify({'error': 'Auto-tagging is already running'}), 400

        # Run one cycle immediately in background
        def run_one_cycle():
            auto_tag_stats['is_running'] = True
            auto_tag_stats['last_run'] = datetime.now().isoformat()

            try:
                print(f"[AUTO-TAG] Running manual cycle...")

                # Scan for new files
                scan_result = scan_folder()
                new_files = scan_result.get('added', 0)
                print(f"[AUTO-TAG] Found {new_files} new file(s)")

                # Find untagged images
                from database import get_untagged_images_for_ai
                untagged = get_untagged_images_for_ai()
                images_to_process = untagged[:AUTO_TAG_BATCH_SIZE]
                print(f"[AUTO-TAG] Processing {len(images_to_process)} images")

                if images_to_process:
                    for idx, img in enumerate(images_to_process):
                        try:
                            image_id = img['id']
                            image_path = os.path.join(SOURCE_FOLDER, db_filepath_to_os_path(img['filepath']))

                            if not os.path.exists(image_path):
                                continue

                            print(f"[AUTO-TAG]   {idx+1}/{len(images_to_process)}: {img['filename']}")

                            existing_tags = get_image_tags(image_id)
                            existing_tag_names = [tag['tag_name'] for tag in existing_tags]

                            suggestions = suggest_tags_for_maintenance(
                                image_path,
                                existing_tags=existing_tag_names,
                                max_suggestions=10
                            )

                            if suggestions:
                                tags_added = 0
                                for tag_name, confidence in suggestions:
                                    tag_id = add_tag(tag_name)
                                    if tag_id and add_image_tag(image_id, tag_id):
                                        tags_added += 1

                                update_image_tagged_status(image_id, True)
                                save_ai_suggestions(image_id, suggestions)

                                auto_tag_stats['images_processed'] += 1
                                auto_tag_stats['tags_added'] += tags_added

                                print(f"[AUTO-TAG]     ✓ Added {tags_added} tags")

                        except Exception as e:
                            auto_tag_stats['errors'] += 1
                            print(f"[AUTO-TAG]     ❌ Error: {e}")

                    print(f"[AUTO-TAG] Manual cycle complete")

            except Exception as e:
                print(f"[AUTO-TAG] ❌ Manual cycle error: {e}")
                auto_tag_stats['errors'] += 1

            finally:
                auto_tag_stats['is_running'] = False

        thread = threading.Thread(target=run_one_cycle)
        thread.start()

        return jsonify({'success': True, 'message': 'Manual auto-tag cycle started'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/auto-tag/stats', methods=['GET'])
def api_auto_tag_stats():
    """Get auto-tagging statistics"""
    return jsonify(auto_tag_stats)


# ===== File Integrity Management API =====

@app.route('/api/integrity/scan', methods=['POST'])
def api_integrity_scan():
    """
    Scan database for file integrity issues
    Marks corrupted/missing files in database
    """
    try:
        def progress(current, total, message):
            # Could be enhanced to use SSE or websockets for real-time updates
            pass

        results = scan_database_integrity(progress_callback=progress, mark_in_db=True)

        return jsonify({
            'success': True,
            'results': {
                'total_checked': results['total_checked'],
                'valid_files': results['valid_files'],
                'missing_count': len(results['missing_files']),
                'corrupted_count': len(results['corrupted_files']),
                'missing_files': results['missing_files'],
                'corrupted_files': results['corrupted_files']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/integrity/issues', methods=['GET'])
def api_integrity_issues():
    """Get all files with integrity issues"""
    try:
        from database import get_images_with_integrity_issues, get_integrity_stats

        issues = get_images_with_integrity_issues()
        stats = get_integrity_stats()

        return jsonify({
            'success': True,
            'issues': issues,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/integrity/cleanup-missing', methods=['POST'])
def api_integrity_cleanup_missing():
    """Remove database records for missing files"""
    try:
        results = cleanup_missing_files()

        return jsonify({
            'success': True,
            'removed_count': results['removed_count'],
            'removed_files': results['removed_files']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/integrity/handle-corrupted', methods=['POST'])
def api_integrity_handle_corrupted():
    """
    Handle corrupted file
    Actions: 'skip', 'delete', or 'quarantine'
    """
    try:
        data = request.json
        image_id = data.get('image_id')
        action = data.get('action', 'skip')
        quarantine_folder = data.get('quarantine_folder')

        if not image_id:
            return jsonify({'error': 'image_id required'}), 400

        result = handle_corrupted_file(image_id, action, quarantine_folder)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['message']}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/integrity/scan-new-files', methods=['POST'])
def api_integrity_scan_new_files():
    """Scan for new files not in database"""
    try:
        results = scan_for_new_files()

        return jsonify({
            'success': True,
            'total_found': results['total_found'],
            'new_files': results['new_files']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/integrity/add-new-file', methods=['POST'])
def api_integrity_add_new_file():
    """Add a new file to database with integrity check"""
    try:
        data = request.json
        filepath = data.get('filepath')

        if not filepath:
            return jsonify({'error': 'filepath required'}), 400

        result = add_new_file(filepath)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['message']}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== Thumbnail Management API =====

@app.route('/api/duplicates', methods=['GET'])
def api_find_duplicates():
    """Find duplicate images by file checksum (content-based, not filename)"""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Find duplicates by checksum where checksum has been computed
        cursor.execute('''
            SELECT file_checksum, COUNT(*) as count
            FROM images
            WHERE file_checksum IS NOT NULL AND file_checksum != ''
            GROUP BY file_checksum
            HAVING COUNT(*) > 1
            ORDER BY count DESC
        ''')
        duplicate_groups = cursor.fetchall()

        results = []
        for group in duplicate_groups:
            cursor.execute('''
                SELECT id, filepath, filename, file_size, date_added, is_tagged
                FROM images
                WHERE file_checksum = ?
                ORDER BY filepath
            ''', (group['file_checksum'],))
            files = [dict(row) for row in cursor.fetchall()]
            results.append({
                'checksum': group['file_checksum'],
                'count': group['count'],
                'file_size': files[0]['file_size'] if files else 0,
                'files': files
            })

        # Also check how many images still need checksums computed
        cursor.execute('SELECT COUNT(*) as cnt FROM images WHERE file_checksum IS NULL OR file_checksum = ""')
        missing_checksums = cursor.fetchone()['cnt']

        conn.close()

        total_duplicates = sum(g['count'] - 1 for g in results)
        return jsonify({
            'success': True,
            'groups': results,
            'total_groups': len(results),
            'total_duplicates': total_duplicates,
            'missing_checksums': missing_checksums
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/duplicates/compute-checksums', methods=['POST'])
def api_compute_checksums():
    """Compute checksums for all images that don't have one yet"""
    import hashlib

    try:
        from database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id, filepath FROM images WHERE file_checksum IS NULL OR file_checksum = ""')
        images = cursor.fetchall()
        total = len(images)
        computed = 0
        errors = 0

        for row in images:
            full_path = os.path.join(SOURCE_FOLDER, db_filepath_to_os_path(row['filepath']))
            if os.path.exists(full_path):
                try:
                    h = hashlib.md5()
                    with open(full_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            h.update(chunk)
                    checksum = h.hexdigest()
                    cursor.execute('UPDATE images SET file_checksum = ? WHERE id = ?', (checksum, row['id']))
                    computed += 1
                except Exception:
                    errors += 1
            else:
                errors += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'total': total,
            'computed': computed,
            'errors': errors
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/thumbnails/regenerate', methods=['POST'])
def api_regenerate_thumbnails():
    """Regenerate all thumbnails in background"""
    try:
        # Reset progress data
        progress_data.update({
            'current': 0,
            'total': 1,
            'done': False,
            'success': 0,
            'failed': 0
        })

        def run_regeneration():
            """Background task to regenerate thumbnails"""
            try:
                # Get all images
                from database import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT id, filepath FROM images')
                images = cursor.fetchall()

                total = len(images)
                progress_data['total'] = total
                success_count = 0
                failed_count = 0

                for idx, row in enumerate(images):
                    source_path = os.path.join(SOURCE_FOLDER, db_filepath_to_os_path(row['filepath']))

                    if not os.path.exists(source_path):
                        failed_count += 1
                    else:
                        thumbnail_path = generate_thumbnail(source_path, row['filepath'])

                        if thumbnail_path:
                            cursor.execute('UPDATE images SET thumbnail_path = ? WHERE id = ?',
                                          (thumbnail_path, row['id']))
                            success_count += 1
                        else:
                            failed_count += 1

                    # Update progress
                    progress_data.update({
                        'current': idx + 1,
                        'success': success_count,
                        'failed': failed_count
                    })

                conn.commit()
                conn.close()

                # Mark as complete
                progress_data['done'] = True

            except Exception as e:
                print(f"[Thumbnail] Error during regeneration: {e}")
                import traceback
                traceback.print_exc()
                progress_data['done'] = True

        # Start regeneration in background
        thread = threading.Thread(target=run_regeneration)
        thread.start()

        return jsonify({'success': True, 'message': 'Thumbnail regeneration started'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/thumbnails/progress')
def api_thumbnails_progress():
    """Stream thumbnail regeneration progress via Server-Sent Events"""
    def event_stream():
        last_sent_current = -1
        while not progress_data['done']:
            if progress_data['current'] != last_sent_current:
                yield f"data: {json.dumps(progress_data)}\n\n"
                last_sent_current = progress_data['current']
            time.sleep(0.1)  # Check every 100ms
        # Send final result
        yield f"data: {json.dumps(progress_data)}\n\n"

    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/init_db', methods=['POST'])
def api_init_db():
    """Initialize database"""
    init_database()
    return jsonify({'success': True, 'message': 'Database initialized'})


if __name__ == '__main__':
    # Initialize database on startup if it doesn't exist
    if not os.path.exists(DATABASE_PATH):
        print("Initializing database...")
        init_database()
    
    print(f"Starting FileCat on http://{HOST}:{PORT}")
    print(f"Source folder: {SOURCE_FOLDER}")

    # Determine if we should start the auto-tag service
    # In debug mode with reloader, only start in the child process (WERKZEUG_RUN_MAIN=true)
    # When running without reloader (e.g. IDE debugger), always start
    use_reloader = DEBUG  # Flask uses reloader when debug=True
    is_main_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    should_start_autotag = AUTO_TAG_ENABLED and AI_TAGGER_AVAILABLE and (is_main_process or not use_reloader)

    if should_start_autotag:
        print(f"\n{'='*60}")
        print(f"[AUTO-TAG] Auto-tagging is ENABLED")
        print(f"[AUTO-TAG] Interval: {AUTO_TAG_INTERVAL} seconds ({AUTO_TAG_INTERVAL/60:.1f} minutes)")
        print(f"[AUTO-TAG] Batch size: {AUTO_TAG_BATCH_SIZE} images per cycle")
        print(f"[AUTO-TAG] Starting background service...")
        print(f"{'='*60}\n")
        start_auto_tag_service()

        if AUTO_TAG_ON_STARTUP:
            print("[AUTO-TAG] AUTO_TAG_ON_STARTUP is enabled, triggering initial scan...")
    elif AUTO_TAG_ENABLED and not AI_TAGGER_AVAILABLE:
        print("[AUTO-TAG] Auto-tagging is ENABLED but AI tagger failed to load (check dependencies)")
    elif AUTO_TAG_ENABLED:
        print("[AUTO-TAG] Skipping background service in reloader process (prevents duplicates)")
    else:
        print("[AUTO-TAG] Auto-tagging is DISABLED (set AUTO_TAG_ENABLED=True in config.py to enable)")

    app.run(host=HOST, port=PORT, debug=DEBUG)




