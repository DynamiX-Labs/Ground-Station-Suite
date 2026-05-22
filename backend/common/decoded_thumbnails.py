"""
Shared thumbnail helpers for SatDump decoded folders.
"""

from multiprocessing import Queue
from pathlib import Path
from typing import Optional

from PIL import Image

THUMBNAIL_FILENAME = "thumbnail.jpg"


def select_decoded_thumbnail_source(decoded_folder: Path) -> Optional[Path]:
    """
    Pick one deterministic PNG source image from a SatDump output folder.
    """
    png_files = sorted(
        (path for path in decoded_folder.rglob("*.png") if path.is_file()),
        key=lambda path: str(path).lower(),
    )
    if not png_files:
        return None

    filled_pngs = [path for path in png_files if "filled" in [part.lower() for part in path.parts]]

    exact_preferred = [
        path
        for path in png_files
        if path.name.lower() == "rgb_msu_mr_rgb_avhrr_3a21_false_color_projected.png"
    ]
    exact_preferred_filled = [
        path for path in exact_preferred if "filled" in [part.lower() for part in path.parts]
    ]
    if exact_preferred_filled:
        return exact_preferred_filled[0]
    if exact_preferred:
        return exact_preferred[0]

    projected = [path for path in png_files if "_projected" in path.name.lower()]
    projected_filled = [
        path for path in projected if "filled" in [part.lower() for part in path.parts]
    ]
    if projected_filled:
        return projected_filled[0]
    if projected:
        return projected[0]

    map_images = [path for path in png_files if path.name.lower().endswith("_map.png")]
    map_images_filled = [
        path for path in map_images if "filled" in [part.lower() for part in path.parts]
    ]
    if map_images_filled:
        return map_images_filled[0]
    if map_images:
        return map_images[0]

    rgb_images = [path for path in png_files if "rgb" in str(path).lower()]
    rgb_images_filled = [
        path for path in rgb_images if "filled" in [part.lower() for part in path.parts]
    ]
    if rgb_images_filled:
        return rgb_images_filled[0]
    if rgb_images:
        return rgb_images[0]

    if filled_pngs:
        return filled_pngs[0]

    return png_files[0]


def generate_decoded_thumbnail(
    decoded_folder: Path, progress_queue: Optional[Queue] = None, force: bool = False
) -> Optional[Path]:
    """
    Create a lightweight decoded-folder thumbnail and return its path.
    """
    thumb_path = decoded_folder / THUMBNAIL_FILENAME
    if thumb_path.exists() and thumb_path.is_file() and not force:
        return thumb_path

    source = select_decoded_thumbnail_source(decoded_folder)
    if not source:
        return None

    tmp_thumb_path = decoded_folder / f".{THUMBNAIL_FILENAME}.tmp"
    try:
        with Image.open(source) as image:
            target_w, target_h = 960, 540
            rgb = image.convert("RGB")
            rgb.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (target_w, target_h), color=(10, 10, 10))
            x_offset = (target_w - rgb.width) // 2
            y_offset = (target_h - rgb.height) // 2
            canvas.paste(rgb, (x_offset, y_offset))
            canvas.save(tmp_thumb_path, format="JPEG", quality=88, optimize=True)

        # Atomic replace keeps lazy generation safe if multiple listings run concurrently.
        tmp_thumb_path.replace(thumb_path)
        if progress_queue:
            progress_queue.put(
                {
                    "type": "output",
                    "output": f"Generated folder thumbnail from: {source.name}",
                    "stream": "stdout",
                }
            )
        return thumb_path
    except Exception as exc:
        if progress_queue:
            progress_queue.put(
                {
                    "type": "output",
                    "output": f"Warning: thumbnail generation failed: {exc}",
                    "stream": "stderr",
                }
            )
        try:
            if tmp_thumb_path.exists():
                tmp_thumb_path.unlink()
        except Exception:
            pass
        return None


def get_decoded_thumbnail_url(decoded_folder: Path, lazy_generate: bool = True) -> Optional[str]:
    """
    Return decoded-folder thumbnail URL with mtime cache-busting query param.
    """
    thumb_path = (
        generate_decoded_thumbnail(decoded_folder)
        if lazy_generate
        else decoded_folder / THUMBNAIL_FILENAME
    )
    if not thumb_path or not thumb_path.exists() or not thumb_path.is_file():
        return None

    thumb_version = int(thumb_path.stat().st_mtime)
    return f"/decoded/{decoded_folder.name}/{THUMBNAIL_FILENAME}?v={thumb_version}"
