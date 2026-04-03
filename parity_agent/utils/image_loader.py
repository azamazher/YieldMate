"""
Image Loader — Load and manage test image sets for tracing.
"""

import os
from pathlib import Path
from typing import List


def get_test_images(
    image_dir: str,
    extensions: tuple = (".jpg", ".jpeg", ".png", ".bmp", ".webp"),
    max_images: int = 0,
) -> List[str]:
    """
    Discover all test images in a directory.

    Args:
        image_dir: Path to the image directory.
        extensions: Accepted image file extensions.
        max_images: Max images to return (0 = all).

    Returns:
        Sorted list of absolute image paths.
    """
    image_dir = Path(image_dir)
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")

    images = []
    for ext in extensions:
        images.extend(image_dir.glob(f"*{ext}"))
        images.extend(image_dir.glob(f"*{ext.upper()}"))

    # Deduplicate and sort
    images = sorted(set(str(p.resolve()) for p in images))

    if max_images > 0:
        images = images[:max_images]

    return images
