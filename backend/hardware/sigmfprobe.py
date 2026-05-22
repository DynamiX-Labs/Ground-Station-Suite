# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("sigmf-probe")


def probe_sigmf_recording(sdr_details):
    """
    Probe a SigMF recording file and extract its parameters.

    Args:
        sdr_details: Dictionary containing SDR connection details with the following keys:
            - recording_path: Path to the .sigmf-meta file or base path without extension

    Returns:
        Dictionary containing:
            - rates: List with the sample rate from the recording
            - gains: List of gain values (0 for playback, not applicable)
            - has_agc: Always False for playback
            - frequency_ranges: Frequency range based on captures in the file
            - metadata: Full SigMF metadata
            - data_file_size: Size of the data file in bytes
            - total_samples: Total number of samples in the recording
            - duration: Recording duration in seconds
    """

    reply: dict = {"success": None, "data": None, "error": None, "log": []}

    try:
        recording_path = sdr_details.get("recording_path", "")
        if not recording_path:
            raise ValueError("No recording_path provided")

        # If recording_path is just a filename, resolve it to the recordings directory
        if not recording_path.startswith("/") and not recording_path.startswith("."):
            # Relative path - resolve to backend/data/recordings
            backend_dir = Path(__file__).parent.parent  # Go up to backend/
            recordings_dir = backend_dir / "data" / "recordings"
            recording_path = str(recordings_dir / recording_path)

        # Handle path with or without .sigmf-meta extension
        if recording_path.endswith(".sigmf-meta"):
            meta_path = Path(recording_path)
        else:
            meta_path = Path(f"{recording_path}.sigmf-meta")

        if not meta_path.exists():
            raise FileNotFoundError(f"SigMF metadata file not found: {meta_path}")

        reply["log"].append(f"INFO: Reading SigMF metadata from: {meta_path}")

        # Read and parse metadata
        with open(meta_path, "r") as f:
            metadata = json.load(f)

        reply["log"].append("INFO: Successfully parsed SigMF metadata")

        # Extract global metadata
        global_meta = metadata.get("global", {})
        sample_rate = global_meta.get("core:sample_rate", 0)
        datatype = global_meta.get("core:datatype", "cf32_le")

        # Validate datatype
        if datatype != "cf32_le":
            reply["log"].append(
                f"WARNING: Datatype {datatype} may not be fully supported. Expected cf32_le."
            )

        # Check if data file exists
        base_name = str(meta_path).replace(".sigmf-meta", "")
        data_path = Path(f"{base_name}.sigmf-data")

        if not data_path.exists():
            raise FileNotFoundError(f"SigMF data file not found: {data_path}")

        data_file_size = os.path.getsize(data_path)
        reply["log"].append(f"INFO: Data file size: {data_file_size / (1024**2):.2f} MB")

        # Calculate total samples (cf32_le = 8 bytes per sample: 4 bytes I + 4 bytes Q)
        bytes_per_sample = 8  # complex64
        total_samples = data_file_size // bytes_per_sample

        # Calculate duration
        duration = total_samples / sample_rate if sample_rate > 0 else 0
        reply["log"].append(f"INFO: Total samples: {total_samples:,}")
        reply["log"].append(f"INFO: Sample rate: {sample_rate / 1e6:.2f} MS/s")
        reply["log"].append(f"INFO: Recording duration: {duration:.2f} seconds")

        # Extract capture information
        captures = metadata.get("captures", [])
        if not captures:
            reply["log"].append("WARNING: No capture segments found in metadata")

        # Get frequency range from captures
        frequencies = []
        for capture in captures:
            freq = capture.get("core:frequency")
            if freq:
                frequencies.append(freq)

        if frequencies:
            min_freq = min(frequencies)
            max_freq = max(frequencies)
            reply["log"].append(
                f"INFO: Frequency range: {min_freq / 1e6:.3f} - {max_freq / 1e6:.3f} MHz"
            )
        else:
            min_freq = 0
            max_freq = 6000e6  # Default max

        # Build response data
        reply["data"] = {
            "rates": [sample_rate] if sample_rate > 0 else [],
            "gains": [0.0],  # Gain not applicable for playback
            "has_agc": False,
            "frequency_ranges": {
                "rx": {
                    "min": min_freq / 1e6,  # Convert to MHz
                    "max": max_freq / 1e6,
                    "step": 0.1,
                }
            },
            "metadata": metadata,
            "data_file_path": str(data_path),
            "data_file_size": data_file_size,
            "total_samples": total_samples,
            "duration": duration,
            "captures": captures,
        }

        reply["success"] = True
        reply["log"].append("INFO: SigMF probe completed successfully")

    except FileNotFoundError as e:
        error_msg = str(e)
        reply["log"].append(f"ERROR: {error_msg}")
        reply["success"] = False
        reply["error"] = error_msg

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse SigMF metadata: {str(e)}"
        reply["log"].append(f"ERROR: {error_msg}")
        reply["success"] = False
        reply["error"] = error_msg

    except Exception as e:
        error_msg = f"Error probing SigMF recording: {str(e)}"
        reply["log"].append(f"ERROR: {error_msg}")
        reply["success"] = False
        reply["error"] = error_msg

    return reply
