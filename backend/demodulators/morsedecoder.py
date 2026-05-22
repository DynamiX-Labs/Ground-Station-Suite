# Ground Station - Morse Code Decoder
# Developed by Claude (Anthropic AI) for the Ground Station project
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
#
# Morse decoding logic based on pqcd by jvestman
# https://github.com/jvestman/pqcd
# Copyright (c) jvestman
# SPDX-License-Identifier: GPL-3.0

import logging
import os
import queue
import threading
import time
import uuid
from collections import deque
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np
from scipy.signal import butter, sosfilt

from vfos.state import VFOManager

logger = logging.getLogger("morsedecoder")


class DecoderStatus(Enum):
    """Decoder status values."""

    IDLE = "idle"
    LISTENING = "listening"
    DECODING = "decoding"
    ERROR = "error"


class MorseDecoder(threading.Thread):
    """Real-time Morse code decoder thread using simplified pqcd-style state machine"""

    # International Morse Code table
    MORSE_CODE = {
        ".-": "A",
        "-...": "B",
        "-.-.": "C",
        "-..": "D",
        ".": "E",
        "..-.": "F",
        "--.": "G",
        "....": "H",
        "..": "I",
        ".---": "J",
        "-.-": "K",
        ".-..": "L",
        "--": "M",
        "-.": "N",
        "---": "O",
        ".--.": "P",
        "--.-": "Q",
        ".-.": "R",
        "...": "S",
        "-": "T",
        "..-": "U",
        "...-": "V",
        ".--": "W",
        "-..-": "X",
        "-.--": "Y",
        "--..": "Z",
        "-----": "0",
        ".----": "1",
        "..---": "2",
        "...--": "3",
        "....-": "4",
        ".....": "5",
        "-....": "6",
        "--...": "7",
        "---..": "8",
        "----.": "9",
        "..--..": "?",
        ".-.-.-": ".",
        "--..--": ",",
        "-.-.--": "!",
        "-..-.": "/",
        "-.--.": "(",
        "-.--.-": ")",
        ".-...": "&",
        "---...": ":",
        "-.-.-.": ";",
        "-...-": "=",
        ".-.-.": "+",
        "-....-": "-",
        "..--.-": "_",
        ".-..-.": '"',
        "...-..-": "$",
        ".--.-.": "@",
    }

    def __init__(
        self,
        audio_queue,
        data_queue,
        session_id,
        config=None,  # Pre-resolved DecoderConfig (unused for Morse, kept for compatibility)
        sample_rate=44100,
        output_dir="data/decoded",
        vfo=None,
        target_freq=800,  # Default CW tone frequency (Hz)
        bandwidth=500,  # Bandwidth for tone detection (Hz)
    ):
        super().__init__(daemon=True, name=f"MorseDecoder-{session_id}")

        # Generate unique decoder instance ID for tracking across restarts
        self.decoder_id = str(uuid.uuid4())

        self.audio_queue = audio_queue
        self.data_queue = data_queue
        self.session_id = session_id
        self.sample_rate = sample_rate
        self.running = True
        self.output_dir = output_dir
        self.vfo = vfo
        self.vfo_manager = VFOManager()
        self.target_freq = target_freq
        self.bandwidth = bandwidth
        self.auto_tune = (
            False  # Disabled: auto-tune chases noise, use fixed frequency from SSB demod
        )

        # Signal processing parameters
        self.audio_buffer: deque = deque(maxlen=int(sample_rate * 0.1))  # 100ms buffer
        self.envelope_buffer: deque = deque(maxlen=int(sample_rate * 0.5))  # 500ms envelope buffer
        self.last_auto_tune: float = 0.0

        # Morse state machine (pqcd-style counter approach)
        self.state_counter = 0  # Positive = tone on, negative = tone off
        self.current_symbol = ""  # Current morse sequence (dots/dashes)
        self.decoded_text = ""  # Accumulated decoded text
        self.character_count = 0
        self.max_decoded_length = 300  # Keep only last 300 characters

        # Adaptive thresholds (pqcd-style)
        # Based on observed values:
        # - Dit counters: 5-10
        # - Silence gaps: -1 to -6
        self.value_threshold = 0.0  # Will be calculated adaptively
        self.dit_threshold = 4  # Minimum counter for dit (observed: 5-10)
        self.dat_threshold = 15  # Minimum counter for dash (must be > typical dit)
        self.break_threshold = -5  # Negative counter for character break (observed: -1 to -6)
        self.space_threshold = 15  # Negative counter for word space (3x break)

        # WPM tracking
        self.wpm: Optional[int] = None
        self.last_dit_duration: Optional[float] = None
        self.dit_start_time: Optional[float] = None

        # Status and output
        self.status = DecoderStatus.IDLE
        self.last_update_time = time.time()
        self.signal_strength: float = 0.0
        self.last_output_time: float = 0
        self.output_update_interval = 0.5  # Send updates every 0.5 seconds
        self.last_threshold_log: float = 0  # Last time we logged threshold info

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Performance monitoring stats
        self.stats: Dict[str, Any] = {
            "audio_chunks_in": 0,
            "audio_samples_in": 0,
            "data_messages_out": 0,
            "queue_timeouts": 0,
            "last_activity": None,
            "errors": 0,
        }
        self.stats_lock = threading.Lock()

        # Design bandpass filter
        self._design_bandpass_filter()

        logger.info(
            f"Morse decoder initialized: session {session_id}, VFO {vfo}, "
            f"target freq: {target_freq}Hz, bandwidth: {bandwidth}Hz, "
            f"sample_rate: {sample_rate}Hz, auto_tune: {self.auto_tune}"
        )
        logger.info(
            f"Thresholds: dit={self.dit_threshold}, dat={self.dat_threshold}, "
            f"break={self.break_threshold}, space={self.space_threshold}"
        )

    def _design_bandpass_filter(self):
        """Design a bandpass filter for CW tone extraction"""
        low = (self.target_freq - self.bandwidth / 2) / (self.sample_rate / 2)
        high = (self.target_freq + self.bandwidth / 2) / (self.sample_rate / 2)

        # Ensure frequencies are in valid range (0, 1)
        low = max(0.001, min(0.999, low))
        high = max(0.001, min(0.999, high))

        if low >= high:
            low = 0.1
            high = 0.3

        self.sos = butter(4, [low, high], btype="band", output="sos")
        logger.debug(
            f"Designed bandpass filter: {low*self.sample_rate/2:.1f}-{high*self.sample_rate/2:.1f}Hz"
        )

    def _auto_detect_tone_frequency(self, signal):
        """Automatically detect the CW tone frequency using FFT (disabled by default)"""
        # DISABLED: Auto-tune causes instability by chasing noise/harmonics
        # The tone should be set correctly by the SSB demodulator's center frequency
        # If needed, user can manually adjust the target_freq parameter
        return

        # Original auto-tune code kept for reference but unreachable:
        current_time = time.time()
        if current_time - self.last_auto_tune < 30.0:  # Increased from 5s to 30s
            return

        if len(signal) < 4096:  # Increased from 2048 for better frequency resolution
            return

        # Use a window to reduce spectral leakage
        window = np.hanning(len(signal))
        windowed = signal * window

        # FFT
        fft = np.fft.rfft(windowed)
        freqs = np.fft.rfftfreq(len(windowed), 1.0 / self.sample_rate)
        magnitudes = np.abs(fft)

        # Look for peak in CW range (300Hz - 3000Hz)
        cw_range_mask = (freqs >= 300) & (freqs <= 3000)
        cw_freqs = freqs[cw_range_mask]
        cw_mags = magnitudes[cw_range_mask]

        if len(cw_mags) == 0:
            return

        # Find peak with much stricter threshold
        peak_idx = np.argmax(cw_mags)
        detected_freq = cw_freqs[peak_idx]
        peak_strength = cw_mags[peak_idx]

        # Only retune if peak is VERY strong (10x average, not 3x)
        # and significantly different (200Hz, not 50Hz)
        if peak_strength > np.mean(cw_mags) * 10:
            freq_diff = abs(detected_freq - self.target_freq)
            if freq_diff > 200:
                logger.info(
                    f"Auto-tune: Detected CW tone at {detected_freq:.0f}Hz (was {self.target_freq:.0f}Hz), "
                    f"peak strength: {peak_strength:.2f}, avg: {np.mean(cw_mags):.2f}"
                )
                self.target_freq = detected_freq
                self._design_bandpass_filter()
                self.last_auto_tune = current_time

    def _process_audio(self, audio_chunk):
        """Process incoming audio and extract envelope"""
        logger.debug("Morse decoder disabled; ignoring audio chunk.")
        return None

        # Add to buffer
        if isinstance(audio_chunk, np.ndarray):
            self.audio_buffer.extend(audio_chunk.flatten())
        else:
            self.audio_buffer.extend(np.array(audio_chunk, dtype=np.float32).flatten())

        # Need enough samples to process
        if len(self.audio_buffer) < 512:
            return None

        # Convert to numpy array
        signal = np.array(list(self.audio_buffer), dtype=np.float32)

        # Auto-detect tone frequency if enabled
        if self.auto_tune and len(signal) >= 2048:
            self._auto_detect_tone_frequency(signal)

        # Apply bandpass filter
        filtered = sosfilt(self.sos, signal)

        # Envelope detection using RMS
        squared = np.power(filtered, 2)
        window_size = int(self.sample_rate * 0.005)  # 5ms window

        if len(squared) >= window_size:
            window = np.hanning(window_size)
            window = window / np.sum(window)
            envelope = np.sqrt(np.convolve(squared, window, mode="valid"))
            current_level = np.mean(envelope[-window_size:])
        else:
            envelope = np.sqrt(squared)
            current_level = np.mean(envelope)

        # Update signal strength
        self.signal_strength = float(current_level)

        # Store envelope for threshold calculation
        self.envelope_buffer.extend(envelope)

        return current_level

    def _calculate_adaptive_threshold(self):
        """Calculate adaptive threshold using simple percentile method"""
        if len(self.envelope_buffer) < 100:
            return None

        envelope_array = np.array(list(self.envelope_buffer))

        # Use simple percentile-based threshold
        # 50th percentile (median) works well for CW: half signal is tone, half is silence
        # This is much simpler and more reliable than MAD for on/off signals
        threshold = np.percentile(envelope_array, 50)  # Use median as threshold

        return threshold

    def _decode_morse_symbol(self, state_counter, current_level):
        """
        Process morse state machine using pqcd-style counter approach

        Based on morse.py from pqcd by jvestman
        Counter-based state tracking:
        - Positive counter: tone is ON, increment each sample
        - Negative counter: tone is OFF, decrement (silence)
        - Thresholds determine dit/dash and character/word breaks
        """
        return

        threshold = self._calculate_adaptive_threshold()
        if threshold is None:
            return

        # Update value threshold for params reporting
        self.value_threshold = threshold

        # Periodic logging of threshold and signal level for debugging
        current_time = time.time()
        if current_time - self.last_threshold_log > 5.0:
            logger.info(
                f"Signal level: {current_level:.6f}, Threshold: {threshold:.6f}, "
                f"Ratio: {current_level/threshold:.2f}x, Tone: {current_level > threshold}"
            )
            self.last_threshold_log = current_time

        # Check if tone is present (matches pqcd line 60)
        if current_level > threshold:
            # Tone detected - increment counter (pqcd line 61-64)
            if self.state_counter < 0:
                self.state_counter = 0
            self.state_counter += 1

            # Track dit timing for WPM calculation
            if self.dit_start_time is None:
                self.dit_start_time = time.time()

        elif self.state_counter > self.dat_threshold:
            # Counter high enough for DASH (pqcd line 65-71)
            duration = self.state_counter
            self.state_counter = 0
            self.current_symbol += "-"
            logger.info(f"DASH detected (counter: {duration})")

        elif self.state_counter > self.dit_threshold:
            # Counter high enough for DIT (pqcd line 72-78)
            duration = self.state_counter
            self.state_counter = 0
            self.current_symbol += "."
            logger.info(f"DIT detected (counter: {duration})")

            # Update WPM estimate from dit duration
            if self.dit_start_time:
                dit_duration = time.time() - self.dit_start_time
                self.last_dit_duration = dit_duration
                # Standard: dit length = 1.2 / WPM
                self.wpm = int(max(5, min(50, 1.2 / dit_duration)))
                self.dit_start_time = None

        elif self.state_counter == self.break_threshold:
            # Character break detected (pqcd line 79-91)
            self.state_counter -= 1

            if self.current_symbol:
                char = self.MORSE_CODE.get(self.current_symbol)
                if char:
                    logger.info(f"Decoded '{self.current_symbol}' -> '{char}'")
                    self._add_character(char)
                else:
                    logger.info(f"Unknown morse: '{self.current_symbol}'")
                    self._add_character("?")
                self.current_symbol = ""

        else:
            # Silence continues - decrement (pqcd line 93-99)
            self.state_counter -= 1

            # Check for word space
            if self.state_counter == -self.space_threshold:
                logger.info("WORD SPACE detected")
                self._add_character(" ")

    def _add_character(self, char):
        """Add a character to decoded text"""
        logger.info(f"Adding character: '{char}'")
        self.decoded_text += char

        # Trim if too long
        if len(self.decoded_text) > self.max_decoded_length:
            self.decoded_text = self.decoded_text[-self.max_decoded_length :]

        if char != " ":
            self.character_count += 1

    def _send_status_update(self, status):
        """Send status update to UI"""
        # Build decoder configuration info (clear FSK-specific fields)
        config_info = {
            "baudrate": None,  # Morse doesn't use baudrate
            "deviation_hz": None,  # Morse doesn't use deviation
            "framing": None,  # Morse doesn't use framing
            "transmitter": "VFO Signal",
            "transmitter_mode": "MORSE",
            "transmitter_downlink_mhz": None,
            "packets_decoded": None,  # Morse decodes characters, not packets
            "signal_power_dbfs": None,
            "signal_power_avg_dbfs": None,
            "signal_power_max_dbfs": None,
            "signal_power_min_dbfs": None,
            "buffer_samples": None,
            "wpm": self.wpm if hasattr(self, "wpm") else None,
            "character_count": self.character_count if hasattr(self, "character_count") else 0,
        }

        msg = {
            "type": "decoder-status",
            "decoder_id": self.decoder_id,
            "status": status.value,
            "decoder_type": "morse",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
            "info": config_info,
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1
        except queue.Full:
            logger.warning("Data queue full, dropping status update")

    def _send_decoded_output(self):
        """Send decoded text output to UI (rate-limited)"""
        current_time = time.time()

        if current_time - self.last_output_time < self.output_update_interval:
            return

        self.last_output_time = current_time

        msg = {
            "type": "decoder-output",
            "decoder_type": "morse",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": current_time,
            "output": {
                "text": self.decoded_text,
                "character_count": self.character_count,
                "wpm": self.wpm,
            },
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1
        except queue.Full:
            logger.warning("Data queue full, dropping decoded output")

    def _send_stats_update(self):
        """Send statistics update to UI"""
        msg = {
            "type": "decoder-stats",
            "decoder_type": "morse",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
            "stats": {
                "character_count": self.character_count,
                "wpm": self.wpm,
                "signal_strength": self.signal_strength,
            },
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1
        except queue.Full:
            pass

    def run(self):
        """Main thread loop"""
        logger.info(f"Morse decoder started for {self.session_id}")
        self._send_status_update(DecoderStatus.LISTENING)

        try:
            while self.running:
                # Get audio from queue
                try:
                    audio_chunk = self.audio_queue.get(timeout=0.1)

                    # Update stats
                    with self.stats_lock:
                        self.stats["audio_chunks_in"] += 1
                        self.stats["last_activity"] = time.time()

                    # Extract audio from dict wrapper if needed
                    if isinstance(audio_chunk, dict):
                        if "audio" in audio_chunk:
                            audio_chunk = audio_chunk["audio"]
                        else:
                            continue

                    # Ensure audio_chunk is proper array
                    if isinstance(audio_chunk, (int, float)):
                        audio_chunk = np.array([audio_chunk], dtype=np.float32)
                    elif not isinstance(audio_chunk, np.ndarray):
                        audio_chunk = np.array(audio_chunk, dtype=np.float32)
                    elif audio_chunk.ndim == 0:
                        audio_chunk = audio_chunk.reshape(1)

                    # Update sample count
                    with self.stats_lock:
                        self.stats["audio_samples_in"] += len(audio_chunk)

                    # Process audio and get current level
                    current_level = self._process_audio(audio_chunk)

                    if current_level is not None:
                        # Run morse state machine
                        self._decode_morse_symbol(self.state_counter, current_level)

                        # Update status
                        current_time = time.time()
                        tone_present = current_level > (self.value_threshold or 0)

                        if self.status == DecoderStatus.LISTENING and tone_present:
                            self.status = DecoderStatus.DECODING
                            self._send_status_update(DecoderStatus.DECODING)
                        elif self.status == DecoderStatus.DECODING and not tone_present:
                            if self.state_counter < -100:  # Long silence
                                self.status = DecoderStatus.LISTENING
                                self._send_status_update(DecoderStatus.LISTENING)

                        # Send periodic updates
                        if current_time - self.last_update_time > 1.0:
                            self._send_stats_update()
                            self._send_decoded_output()
                            self.last_update_time = current_time

                except queue.Empty:
                    with self.stats_lock:
                        self.stats["queue_timeouts"] += 1
                    continue

        except Exception as e:
            logger.error(f"Morse decoder error: {e}")
            logger.exception(e)
            with self.stats_lock:
                self.stats["errors"] += 1
            self._send_status_update(DecoderStatus.ERROR)

        logger.info(f"Morse decoder stopped for {self.session_id}")

    def stop(self):
        """Stop the decoder"""
        self.running = False

        # Save decoded text to file if any
        if self.decoded_text.strip():
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"cw_{timestamp}.txt"
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "w") as f:
                f.write(self.decoded_text)
            logger.info(f"Saved decoded CW text: {filepath}")

        # Send final status update
        msg = {
            "type": "decoder-status",
            "decoder_id": self.decoder_id,
            "status": "closed",
            "decoder_type": "morse",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1
        except queue.Full:
            pass
