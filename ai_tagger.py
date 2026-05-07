"""
AI Auto-Tagging Module using STAG (Stephan's Automatic Image Tagger)
Uses RAM (Recognize Anything Model) for superior tagging
Phase 2 Feature - Updated to use STAG
"""
import os
import sys
import threading
import warnings
from PIL import Image, ImageFile

# Suppress FutureWarning from timm library (used by RAM model)
warnings.filterwarnings('ignore', category=FutureWarning, module='timm')

# Increase PIL's decompression bomb limit for large digital art files
# Default is ~178MP, we increase to 1000MP (1 gigapixel) for safety
Image.MAX_IMAGE_PIXELS = 1000000000  # 1 gigapixel limit

# Allow PIL to load truncated/corrupted images (load as much as possible)
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Add STAG to path
# Set this to your STAG installation directory
STAG_PATH = os.environ.get('STAG_PATH', os.path.join(os.path.dirname(__file__), 'stag'))
if STAG_PATH not in sys.path:
    sys.path.insert(0, STAG_PATH)

# Import STAG components
try:
    import torch
    from ram import get_transform, inference_ram as inference
    from ram.models import ram_plus
    from huggingface_hub import hf_hub_download
    STAG_AVAILABLE = True
except ImportError as e:
    print(f"[AI Tagger] Warning: STAG dependencies not available: {e}")
    STAG_AVAILABLE = False

# Model will be loaded lazily on first use
_model = None
_transform = None
_device = None
_model_lock = threading.Lock()


def get_model():
    """Lazy load the STAG/RAM model"""
    global _model, _transform, _device
    
    if not STAG_AVAILABLE:
        raise RuntimeError(f"STAG dependencies not installed. Please install from {STAG_PATH}/requirements.txt or set STAG_PATH environment variable")

    with _model_lock:
        if _model is None:
            print("[AI Tagger] Loading STAG/RAM model (this may take a moment)...")
            try:
                # Set device
                _device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                print(f"[AI Tagger] Using device: {_device}")
                
                # Download model from HuggingFace
                model_path = hf_hub_download(
                    repo_id='xinyu1205/recognize-anything-plus-model', 
                    filename='ram_plus_swin_large_14m.pth'
                )
                
                # Initialize transform and model
                image_size = 384
                _transform = get_transform(image_size=image_size)
                _model = ram_plus(pretrained=model_path, image_size=image_size, vit='swin_l')
                _model.eval()
                _model = _model.to(_device)
                
                print("[AI Tagger] STAG/RAM model loaded successfully!")
            except Exception as e:
                print(f"[AI Tagger] Error loading model: {e}")
                raise
    
    return _model, _transform, _device


def analyze_image(image_path, tag_candidates=None, threshold=0.0, max_tags=20, image_id=None):
    """
    Analyze an image and return suggested tags using STAG/RAM
    
    Args:
        image_path: Path to the image file
        tag_candidates: Not used with STAG (model generates its own tags)
        threshold: Not used with STAG (model handles confidence internally)
        max_tags: Maximum number of tags to return (default: 20)
        image_id: Optional database ID to mark corrupted images

    Returns:
        List of tuples: (tag_name, confidence_score)
        Returns None if image is corrupted and image_id provided (marks in DB)
        Returns empty list if image is corrupted and no image_id provided
    """
    import time
    start_time = time.time()

    print(f"[AI DEBUG] Starting analysis for: {os.path.basename(image_path)}")

    try:
        # Load model
        print(f"[AI DEBUG] Loading model...")
        model_start = time.time()
        model, transform, device = get_model()
        model_time = time.time() - model_start
        print(f"[AI DEBUG] Model loaded in {model_time:.2f}s")

        # Load and preprocess image
        print(f"[AI DEBUG] Loading image from disk...")
        load_start = time.time()
        try:
            pil_image = Image.open(image_path).convert('RGB')
        except (OSError, IOError) as img_error:
            # Handle corrupted or truncated images
            load_time = time.time() - load_start
            print(f"[AI DEBUG] ❌ Image file corrupted or truncated after {load_time:.2f}s: {img_error}")

            # Mark in database if image_id provided
            if image_id is not None:
                from database import update_image_integrity
                error_msg = str(img_error)
                update_image_integrity(image_id, 'corrupted', error_msg)
                print(f"[AI DEBUG] 🗄️ Marked image ID {image_id} as corrupted in database")
                return None  # Return None to signal corruption when ID provided

            # Try to load what we can with LOAD_TRUNCATED_IMAGES enabled
            try:
                from PIL import ImageFile
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                img = Image.open(image_path)
                pil_image = img.convert('RGB')
                print(f"[AI DEBUG] ⚠️ Loaded truncated image successfully")
            except Exception as recovery_error:
                # Cannot recover - return empty list (or None if tracking)
                print(f"[AI DEBUG] ❌ Cannot recover corrupted image: {recovery_error}")
                total_time = time.time() - start_time
                return None if image_id else []  # Return None if tracking, empty list otherwise

        load_time = time.time() - load_start
        print(f"[AI DEBUG] Image loaded in {load_time:.2f}s - Size: {pil_image.size}")

        # Transform and run inference
        print(f"[AI DEBUG] Running AI inference...")
        inference_start = time.time()
        torch_image = transform(pil_image).unsqueeze(0).to(device)
        
        with torch.no_grad():
            result = inference(torch_image, model)
        
        inference_time = time.time() - inference_start
        print(f"[AI DEBUG] Inference completed in {inference_time:.2f}s")

        # Parse results - STAG returns pipe-separated tags
        if result and len(result) > 0:
            tags_str = result[0]
            print(f"[AI DEBUG] Raw AI response: {tags_str[:200]}..." if len(tags_str) > 200 else f"[AI DEBUG] Raw AI response: {tags_str}")

            if tags_str:
                # Split tags and clean them
                tags = [tag.strip() for tag in tags_str.split('|') if tag.strip()]
                print(f"[AI DEBUG] Parsed {len(tags)} tags from AI response")

                # Limit to max_tags
                tags = tags[:max_tags]
                
                # Return as tuples with confidence (decreasing based on position)
                results = []
                for i, tag in enumerate(tags):
                    # Confidence decreases slightly with position (0.95 to 0.70)
                    confidence = max(0.70, 0.95 - (i * 0.02))
                    results.append((tag, confidence))
                
                total_time = time.time() - start_time
                print(f"[AI DEBUG] ✅ Analysis complete in {total_time:.2f}s - Returning {len(results)} tags")
                print(f"[AI DEBUG] Top tags: {', '.join([f'{tag}({conf:.0%})' for tag, conf in results[:5]])}")

                return results
        
        print(f"[AI DEBUG] ⚠️ No tags generated by AI")
        return []
    
    except Exception as e:
        total_time = time.time() - start_time
        print(f"[AI DEBUG] ❌ Error after {total_time:.2f}s analyzing {image_path}: {e}")
        import traceback
        traceback.print_exc()
        return []  # CRITICAL: Must return empty list to mark image as processed


def analyze_image_batch(image_paths, tag_candidates=None, threshold=0.0, max_tags=20, progress_callback=None):
    """
    Analyze multiple images in batch
    
    Args:
        image_paths: List of image file paths
        tag_candidates: Not used with STAG
        threshold: Not used with STAG
        max_tags: Maximum tags per image
        progress_callback: Optional callback function(current, total, image_path)
    
    Returns:
        Dict mapping image_path -> list of (tag, score) tuples
    """
    results = {}
    total = len(image_paths)
    
    for idx, image_path in enumerate(image_paths):
        if progress_callback:
            progress_callback(idx + 1, total, image_path)
        
        tags = analyze_image(image_path, threshold=threshold, max_tags=max_tags)
        results[image_path] = tags
    
    return results


def get_top_tags(image_path, top_n=10, threshold=0.0):
    """
    Get the top N most confident tags for an image
    
    Args:
        image_path: Path to image
        top_n: Number of top tags to return
        threshold: Not used with STAG
    
    Returns:
        List of tag names (without scores)
    """
    tags_with_scores = analyze_image(image_path, threshold=threshold, max_tags=top_n)
    return [tag for tag, score in tags_with_scores]


def suggest_tags_for_maintenance(image_path, existing_tags=None, threshold=0.0, max_suggestions=10, image_id=None):
    """
    Suggest tags for an image in maintenance mode
    Filters out tags that are already applied
    
    Args:
        image_path: Path to image
        existing_tags: List of tag names already applied to this image
        threshold: Not used with STAG
        max_suggestions: Maximum number of suggestions
        image_id: Optional database ID for corruption tracking

    Returns:
        List of tuples: (tag_name, confidence_score)
        Returns None if image is corrupted
    """
    if existing_tags is None:
        existing_tags = []
    
    # Normalize existing tags to lowercase for comparison
    existing_tags_lower = [tag.lower() for tag in existing_tags]
    
    # Get AI suggestions (STAG typically returns 10-30 tags)
    # Pass image_id for corruption tracking
    all_suggestions = analyze_image(image_path, threshold=threshold, max_tags=max_suggestions * 2, image_id=image_id)

    # Check for corruption (None return value indicates corrupted and marked)
    if all_suggestions is None:
        return None

    # Filter out existing tags
    new_suggestions = [
        (tag, score) for tag, score in all_suggestions
        if tag.lower() not in existing_tags_lower
    ]
    
    return new_suggestions[:max_suggestions]


# For backward compatibility - not used with STAG but kept for API consistency
DEFAULT_TAG_CANDIDATES = [
    "STAG/RAM generates its own tags - this list is not used"
]


if __name__ == "__main__":
    # Test the AI tagger
    print("Testing STAG AI Auto-Tagger...")
    print("This will download the RAM model on first run (~5GB)")
    print()
    
    # You can test with any image
    test_image = input("Enter path to test image (or press Enter to skip): ").strip()
    if test_image and os.path.exists(test_image):
        print(f"\nAnalyzing: {test_image}")
        tags = analyze_image(test_image, max_tags=15)
        
        print("\nSuggested tags:")
        if tags:
            for tag, confidence in tags:
                print(f"  {tag:30s} - {confidence:.2%}")
        else:
            print("  No tags generated")
    else:
        print("No test image provided or file not found.")
