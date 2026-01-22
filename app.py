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
from ai_tagger import analyze_image, analyze_image_batch, suggest_tags_for_maintenance

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

                    # Find untagged images
                    print(f"[AUTO-TAG] Step 2: Finding untagged images (batch #{batch_number})...")
                    untagged = get_images_without_ai_suggestions()

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

                        try:
                            image_id = img['id']
                            image_path = os.path.join(SOURCE_FOLDER, img['filepath'])

                            if not os.path.exists(image_path):
                                print(f"[AUTO-TAG]   ⚠️ Skipping missing file: {img['filename']}")
                                continue

                            print(f"[AUTO-TAG]   Processing {idx+1}/{len(images_to_process)}: {img['filename']}")

                            # Get existing tags
                            existing_tags = get_image_tags(image_id)
                            existing_tag_names = [tag['tag_name'] for tag in existing_tags]

                            # Analyze with AI
                            suggestions = suggest_tags_for_maintenance(
                                image_path,
                                existing_tags=existing_tag_names,
                                max_suggestions=10
                            )

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
                                print(f"[AUTO-TAG]     ⚠️ No tags suggested")

                        except Exception as e:
                            auto_tag_stats['errors'] += 1
                            print(f"[AUTO-TAG]     ❌ Error processing {img['filename']}: {e}")

                    total_processed_this_run += len(images_to_process)
                    total_tags_this_run += batch_tags_added

                    print(f"[AUTO-TAG] Batch #{batch_number} complete: {len(images_to_process)} images, {batch_tags_added} tags added")

                    # Check if there are more images to process
                    remaining = get_images_without_ai_suggestions()
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


@app.route('/api/tags/bulk-add', methods=['POST'])
def api_bulk_add_tag():
    """Add a tag to multiple images"""
    data = request.json
    image_ids = data.get('image_ids', [])
    tag_name = data.get('tag_name', '')
    added_count = bulk_add_tag_to_images(image_ids, tag_name)
    return jsonify({'success': True, 'added_count': added_count})


@app.route('/api/search')
def api_search_images():
    """Search images by tags, filename, or date range"""
    query = request.args.get('q', '')
    tags = request.args.get('tags', '')
    filename = request.args.get('filename', '')
    match_all = request.args.get('match_all', 'true').lower() == 'true'
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    images = []
    
    if tags:
        # Search by tags
        tag_names = [t.strip().lower() for t in tags.split(',') if t.strip()]
        images = search_images_by_tags(tag_names, match_all=match_all)
    elif filename or query:
        # Search by filename
        search_query = filename or query
        images = search_images_by_filename(search_query)
    elif date_from or date_to:
        # Search by date range
        images = search_images_by_date_range(date_from, date_to)
    else:
        # No search criteria, return empty
        images = []
    
    # If we have date range AND other criteria, filter the results
    if (date_from or date_to) and (tags or filename or query):
        date_filtered = search_images_by_date_range(date_from, date_to)
        date_ids = {img['id'] for img in date_filtered}
        images = [img for img in images if img['id'] in date_ids]
    
    # Add tags to each image
    for img in images:
        img['tags'] = get_image_tags(img['id'])
    
    return jsonify({
        'images': images,
        'total': len(images)
    })


@app.route('/api/download', methods=['POST'])
def api_download_images():
    """Download selected images as ZIP"""
    data = request.json
    image_ids = data.get('image_ids', [])
    
    if not image_ids:
        return jsonify({'error': 'No images selected'}), 400
    
    # Create ZIP file in memory
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for image_id in image_ids:
            image = get_image_by_id(image_id)
            if image:
                source_path = os.path.join(SOURCE_FOLDER, image['filepath'])
                if os.path.exists(source_path):
                    # Add file to ZIP with its relative path
                    zf.write(source_path, image['filepath'])
    
    memory_file.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'filecat_download_{timestamp}.zip'
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=filename
    )


@app.route('/images/<path:filepath>')
def serve_image(filepath):
    """Serve original image file"""
    return send_from_directory(SOURCE_FOLDER, filepath)


@app.route('/thumbnails/<path:filepath>')
def serve_thumbnail(filepath):
    """Serve thumbnail image"""
    return send_from_directory(THUMBNAIL_FOLDER, filepath)


@app.route('/api/thumbnails/regenerate', methods=['POST'])
def api_regenerate_thumbnails():
    """Regenerate all thumbnails with progress tracking"""
    def run_regeneration():
        def progress_callback(msg):
            if msg.startswith("Progress:"):
                parts = msg.split()
                idx = int(parts[1].split('/')[0])
                total = int(parts[1].split('/')[1])
                progress_data['current'] = idx
                progress_data['total'] = total
            elif msg.startswith("File not found"):
                progress_data['failed'] += 1
        result = regenerate_all_thumbnails(progress_callback=progress_callback)
        progress_data['done'] = True
        progress_data['success'] = result.get('success', 0)
        progress_data['failed'] = result.get('failed', 0)
    
    # Reset progress
    progress_data.update({'current': 0, 'total': 1, 'done': False, 'success': 0, 'failed': 0})
    thread = threading.Thread(target=run_regeneration)
    thread.start()
    return jsonify({'started': True})


@app.route('/api/thumbnails/progress')
def api_thumbnails_progress():
    """Stream progress updates for thumbnail regeneration"""
    def event_stream():
        last_sent = -1
        while not progress_data['done']:
            if progress_data['current'] != last_sent:
                yield f"data: {{\"current\": {progress_data['current']}, \"total\": {progress_data['total']}}}\n\n"
                last_sent = progress_data['current']
        # Send final result
        yield f"data: {{\"current\": {progress_data['current']}, \"total\": {progress_data['total']}, \"done\": true, \"success\": {progress_data['success']}, \"failed\": {progress_data['failed']}}}\n\n"
    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/database/backup', methods=['POST'])
def api_backup_database():
    """Backup the database"""
    try:
        backup_file = backup_database()
        return jsonify({'success': True, 'backup_file': backup_file, 'message': 'Database backed up successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/database/fix-tagged-status', methods=['POST'])
def api_fix_tagged_status():
    """Fix inconsistent is_tagged status"""
    try:
        fixed_count = fix_tagged_status()
        return jsonify({
            'success': True, 
            'fixed_count': fixed_count,
            'message': f'Fixed {fixed_count} image(s) with inconsistent tag status'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/export')
def api_export_settings():
    """Export settings as JSON"""
    settings_data = {
        'source_folder': SOURCE_FOLDER,
        'thumbnail_folder': THUMBNAIL_FOLDER,
        'database_path': DATABASE_PATH,
        'supported_extensions': list(SUPPORTED_EXTENSIONS),
        'thumbnail_max_size': THUMBNAIL_MAX_SIZE,
        'thumbnail_quality': THUMBNAIL_QUALITY,
        'default_items_per_page': DEFAULT_ITEMS_PER_PAGE,
        'items_per_page_options': ITEMS_PER_PAGE_OPTIONS,
        'thumbnail_sizes': THUMBNAIL_SIZES,
        'host': HOST,
        'port': PORT,
        'debug': DEBUG
    }
    
    memory_file = io.BytesIO()
    memory_file.write(json.dumps(settings_data, indent=2).encode('utf-8'))
    memory_file.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'filecat_settings_{timestamp}.json'
    
    return send_file(
        memory_file,
        mimetype='application/json',
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/export/csv', methods=['POST'])
def api_export_csv():
    """Export image metadata to CSV - Phase 2 Feature"""
    data = request.json
    image_ids = data.get('image_ids', [])
    export_all = data.get('export_all', False)

    # Get images
    if export_all:
        images = get_all_images(limit=None, offset=0)
    else:
        images = [get_image_by_id(img_id) for img_id in image_ids if get_image_by_id(img_id)]

    # Create CSV in memory
    memory_file = io.StringIO()
    writer = csv.writer(memory_file)

    # Write header
    writer.writerow(['Filename', 'File Path', 'File Size (bytes)', 'Date Added', 'Date Modified', 'Tags', 'Is Tagged'])

    # Write data
    for img in images:
        tags = get_image_tags(img['id'])
        tag_names = ', '.join([tag['tag_name'] for tag in tags])

        writer.writerow([
            img['filename'],
            img['filepath'],
            img['file_size'],
            img['date_added'],
            img['date_modified'],
            tag_names,
            'Yes' if img['is_tagged'] else 'No'
        ])

    # Convert to bytes
    memory_file.seek(0)
    output = io.BytesIO()
    output.write(memory_file.getvalue().encode('utf-8'))
    output.seek(0)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'filecat_export_{timestamp}.csv'

    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/print/pdf', methods=['POST'])
def api_generate_pdf():
    """Generate PDF for printing images - Phase 2 Feature"""
    data = request.json
    image_ids = data.get('image_ids', [])
    layout = data.get('layout', '1')  # 1, 2, 4, 6, 9 images per page
    page_size = data.get('page_size', 'letter')  # letter or a4
    orientation = data.get('orientation', 'portrait')  # portrait or landscape
    include_info = data.get('include_info', True)  # Include filename and tags

    if not image_ids:
        return jsonify({'error': 'No images selected'}), 400

    # Get page size
    if page_size.lower() == 'a4':
        pagesize = A4
    else:
        pagesize = letter

    # Handle orientation
    if orientation == 'landscape':
        pagesize = (pagesize[1], pagesize[0])

    # Create PDF in memory
    memory_file = io.BytesIO()
    c = canvas.Canvas(memory_file, pagesize=pagesize)
    page_width, page_height = pagesize

    # Define layout configurations
    layout_configs = {
        '1': {'cols': 1, 'rows': 1},
        '2': {'cols': 1, 'rows': 2},
        '4': {'cols': 2, 'rows': 2},
        '6': {'cols': 2, 'rows': 3},
        '9': {'cols': 3, 'rows': 3}
    }

    config = layout_configs.get(layout, {'cols': 1, 'rows': 1})
    cols = config['cols']
    rows = config['rows']
    images_per_page = cols * rows

    # Calculate cell dimensions
    margin = 0.5 * inch
    cell_width = (page_width - 2 * margin) / cols
    cell_height = (page_height - 2 * margin) / rows

    # Space for info text
    info_height = 0.3 * inch if include_info else 0
    available_height = cell_height - info_height

    # Process images
    images = []
    for img_id in image_ids:
        img = get_image_by_id(img_id)
        if img:
            images.append(img)

    # Generate PDF
    for page_start in range(0, len(images), images_per_page):
        page_images = images[page_start:page_start + images_per_page]

        for idx, img in enumerate(page_images):
            row = idx // cols
            col = idx % cols

            x = margin + col * cell_width
            y = page_height - margin - (row + 1) * cell_height

            # Get image path
            source_path = os.path.join(SOURCE_FOLDER, img['filepath'])

            if os.path.exists(source_path):
                try:
                    # Draw image
                    img_reader = ImageReader(source_path)
                    img_width, img_height = img_reader.getSize()

                    # Calculate scaling to fit in cell
                    scale_w = (cell_width - 0.2 * inch) / img_width
                    scale_h = available_height / img_height
                    scale = min(scale_w, scale_h)

                    scaled_w = img_width * scale
                    scaled_h = img_height * scale

                    # Center image in cell
                    img_x = x + (cell_width - scaled_w) / 2
                    img_y = y + info_height + (available_height - scaled_h) / 2

                    c.drawImage(source_path, img_x, img_y, scaled_w, scaled_h, preserveAspectRatio=True)

                    # Draw info if requested
                    if include_info:
                        tags = get_image_tags(img['id'])
                        tag_names = ', '.join([tag['tag_name'] for tag in tags[:5]])  # Limit to 5 tags
                        if len(tags) > 5:
                            tag_names += '...'

                        c.setFont("Helvetica", 8)
                        c.drawString(x + 0.1 * inch, y + 0.15 * inch, img['filename'][:50])
                        if tag_names:
                            c.setFont("Helvetica-Oblique", 7)
                            c.drawString(x + 0.1 * inch, y + 0.05 * inch, tag_names[:60])

                except Exception as e:
                    # Draw error placeholder
                    c.setFont("Helvetica", 10)
                    c.drawString(x + 0.1 * inch, y + cell_height / 2, f"Error loading: {img['filename']}")
            else:
                # Draw missing placeholder
                c.setFont("Helvetica", 10)
                c.drawString(x + 0.1 * inch, y + cell_height / 2, f"Missing: {img['filename']}")

        c.showPage()

    c.save()
    memory_file.seek(0)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'filecat_print_{timestamp}.pdf'

    return send_file(
        memory_file,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/download/progress', methods=['POST'])
def api_download_with_progress():
    """Download images with progress tracking - Phase 2 Feature"""
    data = request.json
    image_ids = data.get('image_ids', [])

    if not image_ids:
        return jsonify({'error': 'No images selected'}), 400

    def create_zip():
        try:
            download_progress.update({'current': 0, 'total': len(image_ids), 'done': False, 'error': None})

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'filecat_download_{timestamp}.zip'
            download_progress['filename'] = filename

            # Create downloads directory if it doesn't exist
            downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
            os.makedirs(downloads_dir, exist_ok=True)

            zip_path = os.path.join(downloads_dir, filename)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for idx, image_id in enumerate(image_ids):
                    image = get_image_by_id(image_id)
                    if image:
                        source_path = os.path.join(SOURCE_FOLDER, image['filepath'])
                        if os.path.exists(source_path):
                            zf.write(source_path, image['filepath'])
                    download_progress['current'] = idx + 1

            download_progress['done'] = True
        except Exception as e:
            download_progress['error'] = str(e)
            download_progress['done'] = True

    # Start download in background
    thread = threading.Thread(target=create_zip)
    thread.start()

    return jsonify({'started': True})


@app.route('/api/download/status')
def api_download_status():
    """Stream download progress - Phase 2 Feature"""
    def event_stream():
        last_sent = -1
        while not download_progress['done']:
            if download_progress['current'] != last_sent or download_progress['error']:
                yield f"data: {json.dumps(download_progress)}\n\n"
                last_sent = download_progress['current']
                if download_progress['error']:
                    break
        # Send final result
        yield f"data: {json.dumps(download_progress)}\n\n"

    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/download/file/<filename>')
def api_download_file(filename):
    """Download the generated ZIP file - Phase 2 Feature"""
    downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
    file_path = os.path.join(downloads_dir, filename)

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    else:
        return jsonify({'error': 'File not found'}), 404


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
        image_path = os.path.join(SOURCE_FOLDER, image['filepath'])
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
                image_path = os.path.join(SOURCE_FOLDER, image['filepath'])

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

        # Get statistics
        unanalyzed = get_images_without_ai_suggestions()

        return jsonify({
            'success': True,
            'model_loaded': model_loaded,
            'model_name': 'STAG/RAM Plus',
            'unanalyzed_count': len(unanalyzed),
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
                untagged = get_images_without_ai_suggestions()
                images_to_process = untagged[:AUTO_TAG_BATCH_SIZE]
                print(f"[AUTO-TAG] Processing {len(images_to_process)} images")

                if images_to_process:
                    for idx, img in enumerate(images_to_process):
                        try:
                            image_id = img['id']
                            image_path = os.path.join(SOURCE_FOLDER, img['filepath'])

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

    # Start background auto-tagging service ONLY in main process
    # (not in Flask's reloader process to avoid duplicate threads)
    if AUTO_TAG_ENABLED and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print(f"\n{'='*60}")
        print(f"[AUTO-TAG] Auto-tagging is ENABLED")
        print(f"[AUTO-TAG] Interval: {AUTO_TAG_INTERVAL} seconds ({AUTO_TAG_INTERVAL/60:.1f} minutes)")
        print(f"[AUTO-TAG] Batch size: {AUTO_TAG_BATCH_SIZE} images per cycle")
        print(f"[AUTO-TAG] Starting background service...")
        print(f"{'='*60}\n")
        start_auto_tag_service()

        # Optionally run one cycle on startup
        if AUTO_TAG_ON_STARTUP:
            print("[AUTO-TAG] AUTO_TAG_ON_STARTUP is enabled, triggering initial scan...")
            # Give the server a moment to start, then trigger
            def startup_tag():
                time.sleep(5)  # Wait for server to be ready
                import requests
                try:
                    requests.post(f'http://localhost:{PORT}/api/ai/auto-tag/trigger')
                except:
                    pass  # Server might not be ready yet
            threading.Thread(target=startup_tag, daemon=True).start()
    elif AUTO_TAG_ENABLED:
        print("[AUTO-TAG] Skipping background service in reloader process (prevents duplicates)")
    else:
        print("[AUTO-TAG] Auto-tagging is DISABLED (set AUTO_TAG_ENABLED=True in config.py to enable)")

    app.run(host=HOST, port=PORT, debug=DEBUG)


