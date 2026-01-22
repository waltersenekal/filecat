#!/usr/bin/env python3
"""
Generate favicon files from icon.png
Requires: Pillow (already installed in FileCat)
"""
import os
from PIL import Image

# Paths
STATIC_IMG = os.path.join(os.path.dirname(__file__), 'static', 'img')
SOURCE_ICON = os.path.join(STATIC_IMG, 'icon.png')

# Icon sizes to generate
SIZES = {
    'favicon-16x16.png': (16, 16),
    'favicon-32x32.png': (32, 32),
    'favicon-48x48.png': (48, 48),
    'apple-touch-icon.png': (180, 180),
    'android-chrome-192x192.png': (192, 192),
    'android-chrome-512x512.png': (512, 512),
}

def generate_favicons():
    """Generate all favicon sizes from icon.png"""

    print("=" * 60)
    print("FileCat Favicon Generator")
    print("=" * 60)

    # Check if source icon exists
    if not os.path.exists(SOURCE_ICON):
        print(f"❌ Error: Source icon not found!")
        print(f"   Expected: {SOURCE_ICON}")
        print(f"\n📋 To fix:")
        print(f"   1. Copy your 512x512 icon.png to: {STATIC_IMG}/")
        print(f"   2. Run this script again")
        return False

    print(f"✓ Found source icon: {SOURCE_ICON}")

    # Load source image
    try:
        source = Image.open(SOURCE_ICON)
        print(f"✓ Source size: {source.size}")

        if source.size != (512, 512):
            print(f"⚠️  Warning: Source is {source.size}, recommended 512x512")
            print(f"   Icons will still be generated but may not be optimal quality")

    except Exception as e:
        print(f"❌ Error loading icon: {e}")
        return False

    print(f"\n📦 Generating {len(SIZES)} favicon sizes...")
    print()

    # Generate each size
    generated = 0
    for filename, size in SIZES.items():
        output_path = os.path.join(STATIC_IMG, filename)

        try:
            # Resize with high-quality resampling
            resized = source.resize(size, Image.Resampling.LANCZOS)
            resized.save(output_path, 'PNG', optimize=True)

            print(f"✓ Generated: {filename} ({size[0]}x{size[1]})")
            generated += 1

        except Exception as e:
            print(f"❌ Failed: {filename} - {e}")

    # Generate .ico file (multi-size)
    print()
    print("📦 Generating favicon.ico (multi-size)...")

    try:
        ico_path = os.path.join(STATIC_IMG, 'favicon.ico')

        # Create multiple sizes for .ico
        ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
        ico_images = []

        for size in ico_sizes:
            ico_images.append(source.resize(size, Image.Resampling.LANCZOS))

        # Save as .ico with multiple sizes
        ico_images[0].save(
            ico_path,
            format='ICO',
            sizes=[(img.size[0], img.size[1]) for img in ico_images],
            append_images=ico_images[1:]
        )

        print(f"✓ Generated: favicon.ico (multi-size: {', '.join([f'{s[0]}x{s[1]}' for s in ico_sizes])})")
        generated += 1

    except Exception as e:
        print(f"❌ Failed to generate .ico: {e}")

    print()
    print("=" * 60)
    print(f"✅ Complete! Generated {generated} favicon file(s)")
    print("=" * 60)
    print()
    print("📋 Next steps:")
    print("   1. Restart your Flask server")
    print("   2. Open FileCat in browser")
    print("   3. Check browser tab for favicon")
    print("   4. Hard refresh if needed: Ctrl+Shift+R")
    print()
    print(f"📁 Files saved to: {STATIC_IMG}/")
    print()

    return True


if __name__ == '__main__':
    success = generate_favicons()
    exit(0 if success else 1)
