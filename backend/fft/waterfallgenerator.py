# Ground Station - Waterfall Generator
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
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger("waterfall-generator")


class WaterfallConfig:
    """Configuration for waterfall generation"""

    # Default configuration
    DEFAULT_CONFIG = {
        "fft_size": 2048,
        "max_height": 2500,
        "window": "hann",
        "overlap": 0.5,
        "db_range": [-80, 0],
        "generate_thumbnail": True,
        "thumbnail_size": [512, 256],
    }

    def __init__(
        self,
        fft_size: int = 2048,
        max_height: int = 2500,
        window: str = "hann",
        overlap: float = 0.5,
        db_range: Tuple[float, float] = (-80, 0),
        generate_thumbnail: bool = True,
        thumbnail_size: Tuple[int, int] = (512, 256),
    ):
        self.fft_size = fft_size
        self.max_height = max_height
        self.window = window
        self.overlap = overlap
        self.db_range = db_range
        self.generate_thumbnail = generate_thumbnail
        self.thumbnail_size = thumbnail_size

    @classmethod
    def load_from_file(cls, config_path: Path) -> "WaterfallConfig":
        """
        Load configuration from JSON file.

        Args:
            config_path: Path to JSON configuration file

        Returns:
            WaterfallConfig instance
        """
        try:
            if config_path.exists():
                with open(config_path, "r") as f:
                    config_data = json.load(f)

                # Filter out comment/documentation fields (starting with _)
                config_data = {k: v for k, v in config_data.items() if not k.startswith("_")}

                # Convert list to tuple for db_range and thumbnail_size
                if "db_range" in config_data and isinstance(config_data["db_range"], list):
                    config_data["db_range"] = tuple(config_data["db_range"])
                if "thumbnail_size" in config_data and isinstance(
                    config_data["thumbnail_size"], list
                ):
                    config_data["thumbnail_size"] = tuple(config_data["thumbnail_size"])

                logger.info(f"Loaded waterfall config from {config_path}")
                return cls(**config_data)
            else:
                logger.info(f"Config file not found at {config_path}, using default configuration")
                return cls()
        except Exception as e:
            logger.warning(
                f"Error loading waterfall config from {config_path}: {e}, using defaults"
            )
            return cls()

    @classmethod
    def save_default_config(cls, config_path: Path):
        """
        Save default configuration to JSON file.

        Args:
            config_path: Path where to save the configuration
        """
        try:
            # Create directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w") as f:
                json.dump(cls.DEFAULT_CONFIG, f, indent=2)

            logger.info(f"Saved default waterfall config to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save default config: {e}")

    @staticmethod
    def get_colormap_lut():
        """
        Generate a 256-entry RGB lookup table for the Cosmic colormap.
        Returns a numpy array of shape (256, 3) with RGB values 0-255.
        Matches the frontend waterfall cosmic colormap.
        """
        # Cosmic colormap - purple/blue to bright colors (from UI)
        t = np.linspace(0, 1, 256)
        r = np.zeros(256)
        g = np.zeros(256)
        b = np.zeros(256)

        for i, val in enumerate(t):
            if val < 0.2:
                # #070208 to #100b56
                factor = val / 0.2
                r[i] = (7 + factor * 9) / 255.0
                g[i] = (2 + factor * 9) / 255.0
                b[i] = (8 + factor * 78) / 255.0
            elif val < 0.4:
                # #100b56 to #170d87
                factor = (val - 0.2) / 0.2
                r[i] = (16 + factor * 7) / 255.0
                g[i] = (11 + factor * 2) / 255.0
                b[i] = (86 + factor * 49) / 255.0
            elif val < 0.6:
                # #170d87 to #7400cd
                factor = (val - 0.4) / 0.2
                r[i] = (23 + factor * 93) / 255.0
                g[i] = (13 + factor * 0) / 255.0
                b[i] = (135 + factor * 70) / 255.0
            elif val < 0.8:
                # #7400cd to #cb5cff
                factor = (val - 0.6) / 0.2
                r[i] = (116 + factor * 87) / 255.0
                g[i] = (0 + factor * 92) / 255.0
                b[i] = (205 + factor * 50) / 255.0
            else:
                # #cb5cff to #f9f9ae
                factor = (val - 0.8) / 0.2
                r[i] = (203 + factor * 46) / 255.0
                g[i] = (92 + factor * 167) / 255.0
                b[i] = (255 - factor * 81) / 255.0

        # Convert to 0-255 range and stack into RGB array
        rgb = np.stack([r, g, b], axis=1)
        return (rgb * 255).astype(np.uint8)


class WaterfallGenerator:
    """
    Generate waterfall spectrograms from IQ recordings in SigMF format.
    """

    def __init__(self, config: Optional[WaterfallConfig] = None):
        self.config = config or WaterfallConfig()
        self.logger = logging.getLogger("waterfall-generator")

    def _get_sigmf_dtype_info(self, datatype: str) -> Optional[dict]:
        if not datatype:
            return None

        lower = datatype.lower()
        if lower in {"cf32", "cf32_le"}:
            return {"kind": "cf32", "numpy_dtype": np.complex64, "bytes_per_sample": 8}
        if lower in {"ci16", "ci16_le"}:
            return {"kind": "ci16", "numpy_dtype": np.int16, "bytes_per_sample": 4}
        if lower in {"ci8", "ci8_le"}:
            return {"kind": "ci8", "numpy_dtype": np.int8, "bytes_per_sample": 2}
        if lower in {"cu8", "cu8_le"}:
            return {"kind": "cu8", "numpy_dtype": np.uint8, "bytes_per_sample": 2}

        return None

    def _build_sample_reader(self, data_file: Path, dtype_info: dict):
        kind = dtype_info["kind"]
        if kind == "cf32":
            iq_data = np.memmap(data_file, dtype=np.complex64, mode="r")

            def read_samples(start_idx: int, count: int) -> np.ndarray:
                return iq_data[start_idx : start_idx + count]

            return read_samples

        raw = np.memmap(data_file, dtype=dtype_info["numpy_dtype"], mode="r")

        if kind == "ci16":

            def read_samples(start_idx: int, count: int) -> np.ndarray:
                offset = start_idx * 2
                chunk = raw[offset : offset + count * 2]
                if chunk.size < count * 2:
                    count = chunk.size // 2
                    chunk = chunk[: count * 2]
                i_vals = chunk[0::2].astype(np.float32)
                q_vals = chunk[1::2].astype(np.float32)
                return i_vals + 1j * q_vals

        elif kind == "ci8":

            def read_samples(start_idx: int, count: int) -> np.ndarray:
                offset = start_idx * 2
                chunk = raw[offset : offset + count * 2]
                if chunk.size < count * 2:
                    count = chunk.size // 2
                    chunk = chunk[: count * 2]
                i_vals = chunk[0::2].astype(np.float32)
                q_vals = chunk[1::2].astype(np.float32)
                return i_vals + 1j * q_vals

        elif kind == "cu8":

            def read_samples(start_idx: int, count: int) -> np.ndarray:
                offset = start_idx * 2
                chunk = raw[offset : offset + count * 2]
                if chunk.size < count * 2:
                    count = chunk.size // 2
                    chunk = chunk[: count * 2]
                i_vals = chunk[0::2].astype(np.float32) - 128.0
                q_vals = chunk[1::2].astype(np.float32) - 128.0
                return i_vals + 1j * q_vals

        else:
            raise ValueError(f"Unsupported SigMF datatype kind: {kind}")

        return read_samples

    def generate_from_sigmf(self, recording_path: Path) -> bool:
        """
        Generate waterfall images from a SigMF recording.

        Args:
            recording_path: Path to the recording (without extension)

        Returns:
            True if successful, False otherwise
        """
        try:
            recording_path = Path(recording_path)
            recording_base = str(recording_path)
            data_file = Path(f"{recording_base}.sigmf-data")
            meta_file = Path(f"{recording_base}.sigmf-meta")

            # Verify files exist
            if not data_file.exists():
                self.logger.error(f"Data file not found: {data_file}")
                return False

            if not meta_file.exists():
                self.logger.error(f"Metadata file not found: {meta_file}")
                return False

            # Read metadata
            with open(meta_file, "r") as f:
                metadata = json.load(f)

            global_meta = metadata.get("global", {})
            sample_rate = global_meta.get("core:sample_rate")
            if sample_rate is None:
                self.logger.error("Missing sample_rate in metadata")
                return False
            datatype = global_meta.get("core:datatype", "cf32_le")

            dtype_info = self._get_sigmf_dtype_info(datatype)
            if not dtype_info:
                self.logger.error(f"Unsupported SigMF datatype: {datatype}")
                return False

            # Get file size to determine total samples
            file_size = data_file.stat().st_size
            bytes_per_sample = dtype_info["bytes_per_sample"]
            total_samples = file_size // bytes_per_sample
            if file_size % bytes_per_sample != 0:
                self.logger.warning("Data file size is not aligned to sample size for %s", datatype)
            duration_sec = total_samples / sample_rate

            self.logger.info(
                f"Generating waterfall for {recording_path.name}: "
                f"{duration_sec:.1f}s, {total_samples:,} samples, {sample_rate/1e6:.2f} MS/s"
            )

            # Calculate dimensions
            dimensions = self._calculate_dimensions(duration_sec, sample_rate, total_samples)

            sample_reader = self._build_sample_reader(data_file, dtype_info)

            # Create window function for auto-scaling
            fft_size = dimensions["width"]
            if self.config.window == "hann":
                window = np.hanning(fft_size)
            elif self.config.window == "hamming":
                window = np.hamming(fft_size)
            elif self.config.window == "blackman":
                window = np.blackman(fft_size)
            else:
                window = np.ones(fft_size)

            # Auto-scale dB range by sampling FFTs from the recording
            self.config.db_range = self._auto_scale_db_range(
                sample_reader, total_samples, fft_size, window
            )

            # Generate full waterfall
            waterfall_data = self._generate_waterfall_data(sample_reader, total_samples, dimensions)

            # Apply colormap and save
            output_path = Path(f"{recording_base}.png")
            self._save_waterfall_image(waterfall_data, output_path, metadata)

            self.logger.info(
                f"Waterfall saved: {output_path.name} "
                f"({dimensions['width']}x{dimensions['height']})"
            )

            # Generate thumbnail if requested
            if self.config.generate_thumbnail:
                thumbnail_path = recording_path.with_name(
                    f"{recording_path.name}_waterfall_thumb.png"
                )
                self._generate_thumbnail(output_path, thumbnail_path)
                self.logger.info(f"Thumbnail saved: {thumbnail_path.name}")

            return True

        except Exception as e:
            self.logger.error(f"Error generating waterfall: {str(e)}")
            self.logger.exception(e)
            return False

    def _auto_scale_db_range(
        self,
        sample_reader,
        total_samples: int,
        fft_size: int,
        window: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Auto-scale dB range by sampling FFT frames from the recording.
        Uses the same algorithm as the UI waterfall (auto-scaling.js).

        Args:
            iq_data: Memory-mapped IQ data
            sample_rate: Sample rate in Hz
            fft_size: FFT size
            window: Window function

        Returns:
            Tuple of (min_db, max_db)
        """
        # Sample 50 FFT frames scattered throughout the recording to better capture signal dynamics
        num_samples = min(50, total_samples // fft_size)
        if num_samples < 3:
            self.logger.warning("Not enough samples for auto-scaling, using default range")
            return self.config.db_range

        # Calculate evenly spaced sample positions
        total_possible_ffts = total_samples - fft_size
        if total_possible_ffts <= 0:
            self.logger.warning("Not enough samples for auto-scaling, using default range")
            return self.config.db_range
        sample_positions = np.linspace(0, total_possible_ffts, num_samples, dtype=int)

        # Collect FFT power values from sampled frames
        all_values = []

        for pos in sample_positions:
            # Extract samples
            samples = sample_reader(pos, fft_size)
            if len(samples) < fft_size:
                continue

            # Apply window and FFT
            windowed = samples * window
            spectrum = np.fft.fft(windowed)
            spectrum = np.fft.fftshift(spectrum)

            # Convert to power in dB
            power = np.abs(spectrum) ** 2
            with np.errstate(divide="ignore"):
                db_spectrum = 10 * np.log10(power + 1e-20)

            all_values.extend(db_spectrum)

        # Convert to numpy array for analysis
        all_values = np.array(all_values)

        # Sort for percentile calculation
        sorted_values = np.sort(all_values)

        # Use 'medium' preset strategy (matches UI default)
        # Use 5th to 97th percentile with moderate padding
        low_idx = int(len(sorted_values) * 0.05)
        high_idx = int(len(sorted_values) * 0.97)

        min_db = sorted_values[low_idx]
        max_db = sorted_values[high_idx]

        # Apply moderate padding with extra headroom to prevent clipping
        min_db = np.floor(min_db - 5)
        max_db = np.ceil(max_db + 15)  # Increased from +5 to +15 for headroom

        # Calculate statistics for logging
        mean_db = np.mean(all_values)
        median_db = np.median(all_values)

        self.logger.info(
            f"Auto-scaled dB range: [{min_db:.1f}, {max_db:.1f}] "
            f"(mean: {mean_db:.1f}, median: {median_db:.1f}, samples: {len(all_values)})"
        )

        return (min_db, max_db)

    def _calculate_dimensions(
        self, duration_sec: float, sample_rate: float, total_samples: int
    ) -> dict:
        """
        Calculate optimal waterfall dimensions based on recording duration.

        Returns:
            dict with width, height, frames_per_row, time_per_row
        """
        fft_size = self.config.fft_size
        hop_size = int(fft_size * (1 - self.config.overlap))

        # Total possible FFT frames
        total_frames = (total_samples - fft_size) // hop_size + 1

        # Adaptive height based on duration
        if duration_sec < 60:  # < 1 minute
            target_height = min(total_frames, 1200)
        elif duration_sec < 600:  # 1-10 minutes
            target_height = min(total_frames, 1500)
        elif duration_sec < 3600:  # 10-60 minutes
            target_height = min(total_frames, 2000)
        else:  # > 1 hour
            target_height = min(total_frames, self.config.max_height)

        # Ensure we don't exceed available frames
        target_height = min(target_height, total_frames)

        # Calculate how many frames to average per row
        frames_per_row = max(1, total_frames // target_height)
        actual_height = total_frames // frames_per_row

        time_per_row = (frames_per_row * hop_size) / sample_rate

        return {
            "width": fft_size,
            "height": actual_height,
            "frames_per_row": frames_per_row,
            "time_per_row": time_per_row,
            "hop_size": hop_size,
            "total_frames": total_frames,
        }

    def _generate_waterfall_data(
        self, sample_reader, total_samples: int, dimensions: dict
    ) -> np.ndarray:
        """
        Generate waterfall data from IQ samples.

        Returns:
            2D array of shape (height, width) with dB values
        """
        fft_size = dimensions["width"]
        hop_size = dimensions["hop_size"]
        height = dimensions["height"]
        frames_per_row = dimensions["frames_per_row"]

        # Create window function
        if self.config.window == "hann":
            window = np.hanning(fft_size)
        elif self.config.window == "hamming":
            window = np.hamming(fft_size)
        elif self.config.window == "blackman":
            window = np.blackman(fft_size)
        else:
            window = np.ones(fft_size)

        # Allocate output array
        waterfall = np.zeros((height, fft_size), dtype=np.float32)

        self.logger.info(f"Processing {dimensions['total_frames']} FFT frames into {height} rows")

        # Process in chunks to save memory
        row_idx = 0
        frame_idx = 0

        while frame_idx + fft_size <= total_samples and row_idx < height:
            # Accumulate frames_per_row FFT frames
            accumulated_spectrum = np.zeros(fft_size, dtype=np.float32)

            for _ in range(frames_per_row):
                samples = sample_reader(frame_idx, fft_size)
                if len(samples) < fft_size:
                    break

                # Apply window and FFT
                windowed = samples * window
                spectrum = np.fft.fft(windowed)
                spectrum = np.fft.fftshift(spectrum)  # Center DC

                # Convert to power (magnitude squared)
                power = np.abs(spectrum) ** 2
                accumulated_spectrum += power

                frame_idx += hop_size

            # Average and convert to dB
            if frames_per_row > 0:
                accumulated_spectrum /= frames_per_row

            # Convert to dB (avoid log(0))
            with np.errstate(divide="ignore"):
                db_spectrum = 10 * np.log10(accumulated_spectrum + 1e-20)

            waterfall[row_idx] = db_spectrum
            row_idx += 1

            # Progress logging every 10%
            if row_idx % max(1, height // 10) == 0:
                progress = (row_idx / height) * 100
                self.logger.info(f"Progress: {progress:.0f}%")

        # Trim to actual rows processed
        waterfall = waterfall[:row_idx]

        return waterfall

    def _save_waterfall_image(self, waterfall_data: np.ndarray, output_path: Path, metadata: dict):
        """
        Apply colormap and save waterfall as PNG image.
        Clamps out-of-range values to colormap extremes instead of wrapping.
        """
        # Normalize to dB range and clamp to [0, 1]
        db_min, db_max = self.config.db_range
        normalized = np.clip((waterfall_data - db_min) / (db_max - db_min), 0, 1)

        # Convert to 0-255 range (already clamped, so no wrapping/magenta artifacts)
        indexed = (normalized * 255).astype(np.uint8)

        # Get colormap LUT (Cosmic)
        colormap_lut = WaterfallConfig.get_colormap_lut()

        # Apply colormap
        rgb_image = colormap_lut[indexed]

        # Create PIL Image and save
        # Flip vertically so newest is at bottom
        image = Image.fromarray(np.flipud(rgb_image), mode="RGB")
        image.save(output_path, "PNG", optimize=True)

    def _generate_thumbnail(self, source_path: Path, thumbnail_path: Path):
        """
        Generate a thumbnail from the full waterfall image.
        """
        with Image.open(source_path) as img:
            img.thumbnail(self.config.thumbnail_size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, "PNG", optimize=True)
