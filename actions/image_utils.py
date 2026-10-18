"""Utilities for image handling and sticker preparation.

Functions:
- convert_image_to_webp(input_path, out_path, quality=80)
- resize_image(input_path, out_path, width=None, height=None)
- prepare_sticker(input_path, out_path, size=512)

Requires Pillow (already in requirements.txt).
"""
from __future__ import annotations
import os
from PIL import Image


def _ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def convert_image_to_webp(input_path: str, out_path: str, quality: int = 80) -> str:
    """Convert an image to WebP format with given quality."""
    _ensure_parent(out_path)
    img = Image.open(input_path).convert("RGBA")
    img.save(out_path, format="WEBP", quality=quality, lossless=False, method=6)
    return out_path


def resize_image(input_path: str, out_path: str, width: int | None = None, height: int | None = None) -> str:
    """Resize image preserving aspect ratio. Provide width or height or both."""
    _ensure_parent(out_path)
    img = Image.open(input_path)
    orig_w, orig_h = img.size
    if width and height:
        new_size = (width, height)
    elif width:
        new_h = int((width / orig_w) * orig_h)
        new_size = (width, new_h)
    elif height:
        new_w = int((height / orig_h) * orig_w)
        new_size = (new_w, height)
    else:
        new_size = img.size
    img = img.resize(new_size, Image.LANCZOS)
    img.save(out_path)
    return out_path


def prepare_sticker(input_path: str, out_path: str, size: int = 512, quality: int = 90) -> str:
    """Prepare a sticker file (WebP) with square dimensions (size x size).

    Will center-crop or pad transparently to make a square, then resize.
    """
    _ensure_parent(out_path)
    img = Image.open(input_path).convert("RGBA")
    w, h = img.size
    # make square by cropping center or padding
    if w != h:
        # crop center
        if w > h:
            left = (w - h) // 2
            img = img.crop((left, 0, left + h, h))
        else:
            top = (h - w) // 2
            img = img.crop((0, top, w, top + w))
    img = img.resize((size, size), Image.LANCZOS)
    img.save(out_path, format="WEBP", quality=quality, lossless=False, method=6)
    return out_path
