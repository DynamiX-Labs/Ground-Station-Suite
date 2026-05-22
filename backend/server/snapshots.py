"""
Waterfall snapshot management module.

This module handles saving waterfall display snapshots to disk.
"""

import base64
import os
import re
from datetime import datetime

from common.logger import logger


def save_waterfall_snapshot(waterfall_image: str, snapshot_name: str = "") -> dict:
    """
    Save a waterfall snapshot image to disk.

    Args:
        waterfall_image: Base64-encoded image data URL (format: data:image/png;base64,...)
        snapshot_name: Optional base name for the snapshot file (timestamp will be appended)

    Returns:
        dict: Result dictionary with 'success' bool and 'snapshot_path' or 'error' message

    Raises:
        Exception: If image data is invalid or file operations fail
    """
    try:
        if not waterfall_image:
            raise Exception("No waterfall image provided")

        # Generate timestamp
        now = datetime.now()
        date = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        timestamp = f"{date}_{time_str}"

        # Use default name if not provided
        if not snapshot_name or not snapshot_name.strip():
            snapshot_name = "waterfall_snapshot"

        # Append timestamp to snapshot name
        snapshot_name_with_timestamp = f"{snapshot_name}_{timestamp}"

        # Create snapshots directory if it doesn't exist
        # Get the backend directory (2 levels up from this file)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        snapshots_dir = os.path.join(backend_dir, "data", "snapshots")
        os.makedirs(snapshots_dir, exist_ok=True)

        snapshot_path = os.path.join(snapshots_dir, snapshot_name_with_timestamp)

        # Extract base64 data from data URL
        # Format: data:image/png;base64,iVBORw0KG...
        match = re.match(r"data:image/(\w+);base64,(.+)", waterfall_image)
        if match:
            image_data = match.group(2)
            image_bytes = base64.b64decode(image_data)

            # Save the image
            image_path = f"{snapshot_path}.png"
            with open(image_path, "wb") as f:
                f.write(image_bytes)

            logger.info(f"Saved waterfall snapshot: {image_path}")
            return {"success": True, "snapshot_path": image_path}
        else:
            raise Exception("Invalid waterfall image data URL format")

    except Exception as e:
        logger.error(f"Error saving waterfall snapshot: {str(e)}")
        return {"success": False, "error": str(e)}
