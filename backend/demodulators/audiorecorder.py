# Ground Station - Audio Recorder
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
import threading
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import numpy as np

logger = logging.getLogger("audio-recorder")


class AudioRecorder(threading.Thread):
    """
    Audio recorder that subscribes to demodulated audio and writes to WAV format.
    Records audio from a specific VFO's demodulator output.
    """

    def __init__(
        self,
        audio_queue,
        _unused_audio_queue,
        session_id,
        recording_path,
        vfo_number,
        sample_rate=48000,
        target_satellite_norad_id="",
        target_satellite_name="",
        center_frequency=0,
        vfo_frequency=0,
        demodulator_type="",
    ):
        super().__init__(daemon=True, name=f"AudioRecorder-{session_id}-VFO{vfo_number}")
        self.audio_queue = audio_queue
        self.recording_path = Path(recording_path)
        self.session_id = session_id
        self.vfo_number = vfo_number
        self.running = True

        # Metadata
        self.sample_rate = sample_rate
        self.target_satellite_norad_id = target_satellite_norad_id
        self.target_satellite_name = target_satellite_name
        self.center_frequency = center_frequency
        self.vfo_frequency = vfo_frequency
        self.demodulator_type = demodulator_type

        # Recording stats
        self.total_samples = 0
        self.start_datetime = None
        self.start_time_iso = (
            datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + "Z"
        )

        # Performance monitoring
        self.stats: Dict[str, Any] = {
            "audio_chunks_in": 0,
            "audio_samples_in": 0,
            "samples_written": 0,
            "bytes_written": 0,
            "last_activity": None,
            "errors": 0,
        }
        self.stats_lock = threading.Lock()

        # Open WAV file for writing (16-bit PCM, mono)
        self.wav_file = wave.open(f"{recording_path}.wav", "wb")
        self.wav_file.setnchannels(1)  # Mono
        self.wav_file.setsampwidth(2)  # 16-bit
        self.wav_file.setframerate(sample_rate)

        # Create preliminary metadata file
        self._write_preliminary_metadata()

        logger.info(f"Audio recorder started: VFO{vfo_number} -> {recording_path}.wav")

    def run(self):
        """Main recording loop."""
        while self.running:
            try:
                if self.audio_queue.empty():
                    time.sleep(0.01)
                    continue

                audio_message = self.audio_queue.get(timeout=0.1)

                # Update stats
                with self.stats_lock:
                    self.stats["audio_chunks_in"] += 1
                    self.stats["last_activity"] = time.time()

                audio_data = audio_message.get("audio")
                timestamp = audio_message.get("timestamp")

                if audio_data is None or len(audio_data) == 0:
                    continue

                # Update sample count
                with self.stats_lock:
                    self.stats["audio_samples_in"] += len(audio_data)

                if self.start_datetime is None:
                    self.start_datetime = timestamp

                # Write audio samples to WAV file
                # audio_data is float32 numpy array from demodulator, convert to int16
                audio_int16 = np.clip(audio_data * 32767, -32768, 32767).astype(np.int16)
                self.wav_file.writeframes(audio_int16.tobytes())
                self.total_samples += len(audio_int16)

                # Update stats
                with self.stats_lock:
                    self.stats["samples_written"] += len(audio_data)
                    self.stats["bytes_written"] += len(audio_data) * 2  # 16-bit = 2 bytes

            except Exception as e:
                if self.running:
                    logger.error(f"Error in audio recorder: {str(e)}")
                    logger.exception(e)
                    with self.stats_lock:
                        self.stats["errors"] += 1
                time.sleep(0.1)

        logger.info(f"Audio recorder stopped: {self.total_samples} samples written")

    def _write_preliminary_metadata(self):
        """Write preliminary metadata file to mark recording as in progress."""
        metadata = {
            "status": "recording",
            "format": "wav",
            "sample_rate": self.sample_rate,
            "channels": 1,
            "bit_depth": 16,
            "vfo_number": self.vfo_number,
            "demodulator_type": self.demodulator_type,
            "center_frequency": self.center_frequency,
            "vfo_frequency": self.vfo_frequency,
            "start_time": self.start_time_iso,
            "session_id": self.session_id,
        }

        if self.target_satellite_norad_id:
            metadata["target_satellite_norad_id"] = self.target_satellite_norad_id

        if self.target_satellite_name:
            metadata["target_satellite_name"] = self.target_satellite_name

        with open(f"{self.recording_path}.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Preliminary metadata written: {self.recording_path}.json")

    def stop(self):
        """Stop recording and finalize files."""
        self.running = False
        self.join(timeout=2.0)

        # Close WAV file properly
        self.wav_file.close()

        # Calculate duration
        duration_seconds = self.total_samples / self.sample_rate if self.sample_rate > 0 else 0

        # Write final metadata
        metadata = {
            "status": "finished",
            "format": "wav",
            "sample_rate": self.sample_rate,
            "channels": 1,
            "bit_depth": 16,
            "vfo_number": self.vfo_number,
            "demodulator_type": self.demodulator_type,
            "center_frequency": self.center_frequency,
            "vfo_frequency": self.vfo_frequency,
            "start_time": self.start_time_iso,
            "end_time": datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat()
            + "Z",
            "duration_seconds": duration_seconds,
            "total_samples": self.total_samples,
            "session_id": self.session_id,
        }

        if self.target_satellite_norad_id:
            metadata["target_satellite_norad_id"] = self.target_satellite_norad_id

        if self.target_satellite_name:
            metadata["target_satellite_name"] = self.target_satellite_name

        with open(f"{self.recording_path}.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(
            f"Audio recording finalized: {duration_seconds:.2f}s, " f"{self.total_samples} samples"
        )
