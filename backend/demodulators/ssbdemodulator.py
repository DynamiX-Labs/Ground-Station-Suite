# Ground Station - SSB Demodulator
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


import logging
import queue
import threading
import time
from typing import Any, Dict, Optional, Tuple

import numpy as np
from scipy import signal

from common.audio_queue_config import get_audio_queue_config
from vfos.state import VFOManager

logger = logging.getLogger("ssb-demodulator")


class SSBDemodulator(threading.Thread):
    """
    SSB (Single Sideband) demodulator that consumes IQ data and produces audio samples.

    This demodulator:
    1. Reads IQ samples from iq_queue (a subscriber queue from IQBroadcaster)
    2. Translates frequency based on VFO center frequency
    3. Decimates to appropriate bandwidth
    4. Demodulates SSB (USB/LSB) by filtering and extracting real component
    5. Applies audio filtering
    6. Resamples to 44.1kHz audio
    7. Puts audio in audio_queue

    Note: Multiple demodulators can run simultaneously, each with its own
    subscriber queue from the IQBroadcaster. This allows multiple VFOs to
    process the same IQ samples without gaps.
    """

    def __init__(
        self,
        iq_queue,
        audio_queue,
        session_id,
        mode="usb",
        vfo_number=None,
        internal_mode=False,
        center_freq=None,
        bandwidth=None,
        **kwargs,
    ):
        super().__init__(daemon=True, name=f"SSBDemodulator-{session_id}-VFO{vfo_number or ''}")
        self.iq_queue = iq_queue
        self.audio_queue = audio_queue
        self.session_id = session_id
        self.vfo_number = vfo_number  # VFO number for multi-VFO mode
        self.running = True
        self.vfo_manager = VFOManager()
        self.audio_cfg = get_audio_queue_config()
        self.mode = mode  # "usb", "lsb", or "cw"

        # Internal mode: bypasses VFO checks and uses provided parameters
        self.internal_mode = internal_mode
        self.internal_center_freq = center_freq  # Used if internal_mode=True
        self.internal_bandwidth = bandwidth or 2500  # Default to 2.5 kHz for CW/SSB

        # Audio output parameters
        self.audio_sample_rate = 44100  # 44.1 kHz audio output
        self.target_chunk_size = 1024  # Minimum viable chunks for lowest latency (~23ms)

        # Audio buffer to accumulate samples
        self.audio_buffer = np.array([], dtype=np.float32)

        # Squelch state (for hysteresis)
        self.squelch_open = False  # Track if squelch is open (signal present)

        # Power measurement settings
        self.power_update_rate = 4.0  # Hz - send power measurements 4 times per second
        self.last_power_time = 0.0
        self.last_rf_power_db = None  # Cache last measured power

        # Processing state
        self.sdr_sample_rate = None
        self.current_center_freq = None
        self.current_bandwidth = None
        self.current_mode = None

        # Filters (will be initialized when we know sample rates)
        self.decimation_filter: Optional[Tuple[np.ndarray, int]] = None
        self.audio_filter: Optional[np.ndarray] = None

        # Performance monitoring stats
        self.stats: Dict[str, Any] = {
            "iq_chunks_in": 0,
            "iq_samples_in": 0,
            "audio_chunks_out": 0,
            "audio_samples_out": 0,
            "queue_timeouts": 0,
            "last_activity": None,
            "errors": 0,
            # Ingest-side flow metrics (updated every ~1s)
            "ingest_samples_per_sec": 0.0,
            "ingest_chunks_per_sec": 0.0,
            # Out-of-band accounting
            "samples_dropped_out_of_band": 0,
            # Sleeping state (VFO out of SDR bandwidth)
            "is_sleeping": False,
        }
        self.stats_lock = threading.Lock()

        # Track sleeping state (mirror in stats["is_sleeping"])
        self.is_sleeping = False
        self.sleep_reason = None

    def _get_active_vfo(self):
        """Get the VFO state for this demodulator's VFO."""
        if self.vfo_number is None:
            logger.error(f"vfo_number is required for SSBDemodulator (session {self.session_id})")
            return None

        vfo_state = self.vfo_manager.get_vfo_state(self.session_id, self.vfo_number)
        if vfo_state and vfo_state.active:
            return vfo_state
        return None

    def _resize_filter_state(self, old_state, b_coeffs, initial_value, a_coeffs=None):
        """
        Resize filter state vector when filter coefficients change.

        This prevents clicks by smoothly transitioning filter states instead of
        resetting to None when bandwidth changes.

        Args:
            old_state: Previous filter state (or None)
            b_coeffs: New numerator coefficients
            initial_value: Value to use for initialization if needed
            a_coeffs: Denominator coefficients (for IIR filters)

        Returns:
            Resized filter state appropriate for the new filter
        """
        if a_coeffs is None:
            # FIR filter: state length is len(b) - 1
            new_len = len(b_coeffs) - 1
        else:
            # IIR filter: state length is max(len(b), len(a)) - 1
            new_len = max(len(b_coeffs), len(a_coeffs)) - 1

        if old_state is None or len(old_state) == 0:
            # No previous state, initialize fresh
            if a_coeffs is None:
                return signal.lfilter_zi(b_coeffs, 1) * initial_value
            else:
                return signal.lfilter_zi(b_coeffs, a_coeffs) * initial_value

        old_len = len(old_state)

        if old_len == new_len:
            # Same size, keep the state as-is
            return old_state
        elif new_len > old_len:
            # Need more state - pad with zeros or the last value
            # Use the last state value to avoid discontinuities
            pad_value = old_state[-1] if old_len > 0 else 0
            padding = np.full(new_len - old_len, pad_value)
            return np.concatenate([old_state, padding])
        else:
            # Need less state - truncate
            return old_state[:new_len]

    def _design_decimation_filter(self, sdr_rate, bandwidth):
        """Design a decimation filter to reduce sample rate to appropriate level for SSB processing.

        Uses IIR Butterworth filter for ~100-250x better performance than FIR at high sample rates.
        """
        # Target intermediate rate: ~48 kHz (sufficient for SSB bandwidth up to 22 kHz)
        # If bandwidth is higher, increase the target rate to accommodate it
        min_required_rate = bandwidth * 2.5  # Nyquist + some margin
        target_rate = max(48e3, min_required_rate)

        decimation = int(sdr_rate / target_rate)
        decimation = max(1, decimation)  # At least 1

        # Simple lowpass filter for decimation
        # We'll do sideband selection separately
        nyquist = sdr_rate / 2.0

        # For complex signals centered at DC, we need to pass the full bandwidth
        # not just bandwidth/2. The bandwidth parameter is the full single-sideband width.
        cutoff = min(bandwidth, 22000)
        cutoff = max(cutoff, 1500)  # At least 1.5 kHz

        normalized_cutoff = cutoff / nyquist
        normalized_cutoff = min(0.45, max(0.01, normalized_cutoff))

        # Design IIR Butterworth filter
        # 6th order filter provides good selectivity with minimal computational cost
        b, a = signal.butter(6, normalized_cutoff, btype="low")

        return (b, a), decimation

    def _design_audio_filter(self, intermediate_rate, vfo_bandwidth):
        """Design audio low-pass filter based on VFO bandwidth.

        For SSB, the audio bandwidth can range from voice (300 Hz - 3 kHz)
        to wide bandwidth for data/music (up to 22 kHz).
        """
        # SSB audio cutoff (high-pass and low-pass)
        low_cutoff = 300  # Hz - remove DC and low frequency noise
        high_cutoff = min(vfo_bandwidth, 22000)  # Hz - use requested bandwidth, cap at 22 kHz

        # Ensure minimum bandwidth
        if high_cutoff < low_cutoff + 100:
            low_cutoff = 100
            high_cutoff = 3000  # Default to 3 kHz if bandwidth is too small

        nyquist = intermediate_rate / 2.0
        normalized_low = low_cutoff / nyquist
        normalized_high = high_cutoff / nyquist

        # Ensure normalized cutoffs are valid (0 < f < 1) and in order
        normalized_low = min(0.45, max(0.01, normalized_low))
        normalized_high = min(0.45, max(normalized_low + 0.01, normalized_high))

        numtaps = 201
        # Design bandpass filter for SSB audio
        filter_taps = signal.firwin(
            numtaps, [normalized_low, normalized_high], pass_zero=False, window="hamming"
        )

        return filter_taps

    def _frequency_translate(self, samples, offset_freq, sample_rate):
        """Translate frequency by offset (shift signal in frequency domain)."""
        if offset_freq == 0:
            return samples

        # Generate complex exponential for frequency shift
        t = np.arange(len(samples)) / sample_rate
        shift = np.exp(-2j * np.pi * offset_freq * t)
        return samples * shift

    def _ssb_demodulate(self, samples):
        """
        Demodulate SSB by selecting one sideband and taking the real component.

        Uses FFT to properly select only the desired sideband (USB, LSB, or CW).
        This ensures the opposite sideband is completely rejected.
        CW is treated as narrowband USB.
        """
        # Perform FFT to work in frequency domain
        fft_data = np.fft.fft(samples)
        freqs = np.fft.fftfreq(len(samples))

        # Zero out the unwanted sideband
        if self.mode.lower() in ["usb", "cw"]:
            # USB/CW: keep positive frequencies (indices where freq >= 0)
            # Zero out negative frequencies
            fft_data[freqs < 0] = 0
        else:  # LSB
            # LSB: keep negative frequencies (indices where freq < 0)
            # Zero out positive frequencies
            fft_data[freqs > 0] = 0

        # Transform back to time domain
        filtered = np.fft.ifft(fft_data)

        # Extract real component (the audio signal)
        demodulated = np.real(filtered)

        return demodulated

    def run(self):
        """Main demodulator loop."""
        logger.info(f"SSB demodulator started for session {self.session_id} (mode: {self.mode})")

        # State for filter applications
        decimation_state = None
        audio_filter_state = None

        # Ingest-rate tracking and stats heartbeat
        ingest_window_start = time.time()
        ingest_samples_accum = 0
        ingest_chunks_accum = 0
        last_stats_time = time.time()

        while self.running:
            try:

                # CRITICAL: Always drain iq_queue to prevent buffer buildup
                # Even if VFO is inactive, we must consume samples to avoid lag
                if self.iq_queue.empty():
                    time.sleep(0.01)
                    continue

                iq_message = self.iq_queue.get(timeout=0.1)

                # Update stats
                with self.stats_lock:
                    self.stats["iq_chunks_in"] += 1
                    self.stats["last_activity"] = time.time()

                # Extract samples and metadata first
                samples = iq_message.get("samples")
                sdr_center_freq = iq_message.get(
                    "logical_center_freq_hz", iq_message.get("center_freq")
                )
                sdr_sample_rate = iq_message.get("sample_rate")

                if samples is None or len(samples) == 0:
                    continue

                # Update sample count
                with self.stats_lock:
                    self.stats["iq_samples_in"] += len(samples)
                # Update ingest accumulators regardless of DSP path
                ingest_samples_accum += len(samples)
                ingest_chunks_accum += 1

                # Determine VFO parameters based on mode
                if self.internal_mode:
                    # Internal mode: use provided parameters but still get VFO state for volume/squelch/bandwidth/frequency
                    vfo_state = self._get_active_vfo()
                    # Use VFO center frequency if available (allows dynamic tuning), otherwise fallback to internal/SDR center
                    if vfo_state and vfo_state.center_freq:
                        vfo_center_freq = vfo_state.center_freq
                    elif self.internal_center_freq is not None:
                        vfo_center_freq = self.internal_center_freq
                    else:
                        vfo_center_freq = sdr_center_freq
                    # Use VFO bandwidth if available (allows dynamic bandwidth adjustment), otherwise fallback to internal
                    vfo_bandwidth = vfo_state.bandwidth if vfo_state else self.internal_bandwidth
                    # Keep the mode as set during init (e.g., "cw" for CW decoder)
                else:
                    # Normal mode: check VFO state
                    vfo_state = self._get_active_vfo()
                    if not vfo_state:
                        # VFO inactive - discard these samples and continue
                        continue

                    # Check if modulation is SSB (USB, LSB, or CW)
                    vfo_modulation = vfo_state.modulation.lower()
                    if vfo_modulation not in ["usb", "lsb", "cw"]:
                        # Wrong modulation - discard these samples and continue
                        continue

                    # Update mode if VFO changed
                    if vfo_modulation != self.mode.lower():
                        self.mode = vfo_modulation
                        logger.info(f"Switched SSB mode to {self.mode.upper()}")

                    vfo_center_freq = vfo_state.center_freq
                    vfo_bandwidth = vfo_state.bandwidth

                # Check if we need to reinitialize filters
                if (
                    self.sdr_sample_rate != sdr_sample_rate
                    or self.current_bandwidth != vfo_bandwidth
                    or self.current_mode != self.mode.lower()
                    or self.decimation_filter is None
                ):
                    self.sdr_sample_rate = sdr_sample_rate
                    self.current_bandwidth = vfo_bandwidth
                    self.current_mode = self.mode.lower()

                    # Design filters
                    iir_coeffs, decimation = self._design_decimation_filter(
                        sdr_sample_rate, vfo_bandwidth
                    )
                    self.decimation_filter = (iir_coeffs, decimation)

                    intermediate_rate = sdr_sample_rate / decimation
                    self.audio_filter = self._design_audio_filter(intermediate_rate, vfo_bandwidth)

                    # Smooth filter state transitions instead of resetting to None
                    initial_value = samples[0] if len(samples) > 0 else 0
                    b, a = iir_coeffs
                    decimation_state = self._resize_filter_state(
                        decimation_state, b, initial_value, a
                    )
                    audio_filter_state = self._resize_filter_state(
                        audio_filter_state, self.audio_filter, 0
                    )

                    logger.info(
                        f"Filters initialized (internal_mode={self.internal_mode}): SDR rate={sdr_sample_rate/1e6:.2f} MHz, "
                        f"decimation={decimation}, intermediate={intermediate_rate/1e3:.1f} kHz, mode={self.mode.upper()}"
                    )

                # Step 1: Frequency translation (tune to VFO frequency)
                if vfo_center_freq == 0:
                    logger.debug("VFO frequency not set, skipping frame")
                    continue

                # Validate VFO center is within SDR bandwidth (with edge margin)
                offset = vfo_center_freq - sdr_center_freq
                half_bw = sdr_sample_rate / 2.0
                usable = half_bw * 0.98
                is_in_band = abs(offset) <= usable
                margin = usable - abs(offset)

                if not is_in_band:
                    # VFO is outside SDR bandwidth - enter sleeping state and skip DSP
                    with self.stats_lock:
                        self.stats["samples_dropped_out_of_band"] += len(samples)
                        self.stats["is_sleeping"] = True
                    if not self.is_sleeping:
                        self.is_sleeping = True
                        self.sleep_reason = (
                            f"VFO out of SDR bandwidth: VFO={vfo_center_freq/1e6:.3f}MHz, "
                            f"SDR={sdr_center_freq/1e6:.3f}MHz±{(sdr_sample_rate/2)/1e6:.2f}MHz, "
                            f"offset={offset/1e3:.1f}kHz, exceeded by {abs(margin)/1e3:.1f}kHz"
                        )
                        logger.warning(self.sleep_reason)
                    continue

                # If we were sleeping and now back in band, resume
                if self.is_sleeping:
                    self.is_sleeping = False
                    with self.stats_lock:
                        self.stats["is_sleeping"] = False
                    logger.info(
                        f"VFO back in SDR bandwidth, resuming SSB demodulation: VFO={vfo_center_freq/1e6:.3f}MHz, "
                        f"SDR={sdr_center_freq/1e6:.3f}MHz, offset={offset/1e3:.1f}kHz"
                    )

                offset_freq = vfo_center_freq - sdr_center_freq
                if abs(offset_freq) > sdr_sample_rate / 2:
                    logger.debug(
                        f"VFO frequency {vfo_center_freq} Hz is outside SDR bandwidth "
                        f"(SDR center: {sdr_center_freq} Hz, rate: {sdr_sample_rate} Hz)"
                    )
                    continue

                translated = self._frequency_translate(samples, offset_freq, sdr_sample_rate)

                # Step 2: Decimate and filter to bandwidth (sideband selection done by filter)
                iir_coeffs, decimation = self.decimation_filter
                b, a = iir_coeffs

                if decimation_state is None:
                    # Initialize filter state on first run
                    decimation_state = signal.lfilter_zi(b, a) * translated[0]

                filtered, decimation_state = signal.lfilter(b, a, translated, zi=decimation_state)
                decimated = filtered[::decimation]

                # Measure RF signal power for squelch AFTER filtering
                # Calculate on every chunk for accurate squelch operation
                signal_power = np.mean(np.abs(filtered) ** 2)
                rf_power_db = 10 * np.log10(signal_power + 1e-10)

                # Update cached power value periodically for UI updates (throttled to N Hz)
                current_time = time.time()
                should_update_ui_power = (current_time - self.last_power_time) >= (
                    1.0 / self.power_update_rate
                )

                if should_update_ui_power:
                    self.last_rf_power_db = rf_power_db
                    self.last_power_time = current_time

                intermediate_rate = sdr_sample_rate / decimation

                # Step 3: SSB demodulation
                demodulated = self._ssb_demodulate(decimated)

                # Step 4: Audio filtering
                if audio_filter_state is None:
                    # Initialize filter state on first run
                    audio_filter_state = signal.lfilter_zi(self.audio_filter, 1) * demodulated[0]

                audio_filtered, audio_filter_state = signal.lfilter(
                    self.audio_filter, 1, demodulated, zi=audio_filter_state
                )

                # Step 5: Resample to audio rate (44.1 kHz)
                num_output_samples = int(
                    len(audio_filtered) * self.audio_sample_rate / intermediate_rate
                )
                if num_output_samples > 0:
                    audio = signal.resample(audio_filtered, num_output_samples)

                    # Apply amplification based on VFO volume setting
                    # Get volume from VFO state if available, otherwise use default
                    if vfo_state and hasattr(vfo_state, "volume"):
                        # VFO volume is typically 0-100, normalize to gain factor
                        # Map 0-100 to 0.0-10.0 gain (with 50 = 3.0x as default)
                        audio_gain = (vfo_state.volume / 50.0) * 3.0
                        audio_gain = max(0.1, min(10.0, audio_gain))  # Clamp to reasonable range
                    else:
                        audio_gain = 3.0  # Default 3x amplification

                    audio = audio * audio_gain

                    # Normalize and soft clipping
                    # SSB typically has less dynamic range than FM
                    max_val = np.max(np.abs(audio)) + 1e-10
                    audio = audio / max_val * 0.5  # Scale to 50% to leave headroom
                    audio = np.clip(audio, -0.95, 0.95)

                    # Apply squelch based on RF signal strength (measured earlier)
                    # Get squelch from VFO state
                    if vfo_state and hasattr(vfo_state, "squelch"):
                        squelch_threshold_db = vfo_state.squelch
                    else:
                        # If no VFO state (shouldn't happen), disable squelch
                        squelch_threshold_db = -200

                    squelch_hysteresis_db = 3  # 3 dB hysteresis to prevent flutter

                    # Apply squelch with hysteresis
                    if self.squelch_open:
                        # Squelch is open - close if RF power drops below threshold
                        if rf_power_db < (squelch_threshold_db - squelch_hysteresis_db):
                            self.squelch_open = False
                            audio = np.zeros_like(audio)  # Mute
                    else:
                        # Squelch is closed - open if RF power rises above threshold
                        if rf_power_db > (squelch_threshold_db + squelch_hysteresis_db):
                            self.squelch_open = True
                            # Let audio through
                        else:
                            audio = np.zeros_like(audio)  # Keep muted

                    # Convert to float32
                    audio = audio.astype(np.float32)

                    # Buffer audio samples to create consistent chunk sizes
                    self.audio_buffer = np.concatenate([self.audio_buffer, audio])

                    # CRITICAL: Limit buffer size to prevent unbounded growth
                    # If buffer grows too large (>10 chunks), drop oldest data
                    max_buffer_samples = (
                        self.target_chunk_size * self.audio_cfg.demod_audio_internal_buffer_chunks
                    )
                    if len(self.audio_buffer) > max_buffer_samples:
                        # Keep only the most recent data
                        self.audio_buffer = self.audio_buffer[-max_buffer_samples:]
                        # Only log warning if not in internal mode (used by decoders like CW)
                        if not self.internal_mode:
                            logger.warning(
                                f"Audio buffer overflow ({len(self.audio_buffer)} samples), "
                                f"dropping old audio to prevent lag buildup"
                            )
                        else:
                            logger.debug(
                                f"Audio buffer overflow ({len(self.audio_buffer)} samples), "
                                f"dropping old audio (internal mode)"
                            )

                    # Send chunks of target size when buffer is full enough
                    while len(self.audio_buffer) >= self.target_chunk_size:
                        # Extract a chunk
                        chunk = self.audio_buffer[: self.target_chunk_size]
                        self.audio_buffer = self.audio_buffer[self.target_chunk_size :]

                        # Prepare audio message
                        audio_message = {
                            "session_id": self.session_id,
                            "audio": chunk,
                            "vfo_number": self.vfo_number,  # Add VFO number for multi-VFO support
                            "rf_power_db": self.last_rf_power_db,  # Include latest power measurement
                        }

                        # Always output audio (UI handles muting, transcription always active)
                        # Put audio chunk in queue (single output point)
                        # In internal mode, this feeds AudioBroadcaster which distributes to decoder/UI
                        # In normal mode, this goes directly to audio consumers
                        try:
                            self.audio_queue.put_nowait(audio_message)
                            # Update stats
                            with self.stats_lock:
                                self.stats["audio_chunks_out"] += 1
                                self.stats["audio_samples_out"] += len(chunk)
                        except queue.Full:
                            # Queue is full - drop this chunk to prevent lag accumulation
                            logger.debug(
                                f"Audio queue full, dropping chunk for session {self.session_id}"
                            )
                            break  # Exit while loop to process next IQ samples
                        except Exception as e:
                            logger.warning(f"Could not queue audio: {str(e)}")
                            break

            except Exception as e:
                if self.running:
                    logger.error(f"Error in SSB demodulator: {str(e)}")
                    logger.exception(e)
                    with self.stats_lock:
                        self.stats["errors"] += 1
                time.sleep(0.1)
            finally:
                # Time-based stats tick (every ~1s), compute ingest rates regardless of processing state
                now = time.time()
                if now - last_stats_time >= 1.0:
                    dt = now - ingest_window_start
                    if dt > 0:
                        ingest_sps = ingest_samples_accum / dt
                        ingest_cps = ingest_chunks_accum / dt
                    else:
                        ingest_sps = 0.0
                        ingest_cps = 0.0

                    with self.stats_lock:
                        self.stats["ingest_samples_per_sec"] = ingest_sps
                        self.stats["ingest_chunks_per_sec"] = ingest_cps
                        self.stats["is_sleeping"] = self.is_sleeping

                    # Reset window
                    ingest_window_start = now
                    ingest_samples_accum = 0
                    ingest_chunks_accum = 0

                    # Advance the stats tick reference to ensure ~1s cadence
                    last_stats_time = now

        logger.info(f"SSB demodulator stopped for session {self.session_id}")

    def stop(self):
        """Stop the demodulator thread."""
        self.running = False
