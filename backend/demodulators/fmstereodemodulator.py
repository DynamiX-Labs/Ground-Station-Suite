# Ground Station - FM Stereo Demodulator
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

logger = logging.getLogger("fm-stereo-demodulator")


class FMStereoDemodulator(threading.Thread):
    """
    FM Stereo demodulator that consumes IQ data and produces stereo audio samples.

    This demodulator:
    1. Reads IQ samples from iq_queue (a subscriber queue from IQBroadcaster)
    2. Translates frequency based on VFO center frequency
    3. Decimates to appropriate bandwidth (preserving full MPX signal up to 53 kHz)
    4. Demodulates FM using phase differentiation
    5. Decodes stereo multiplex (MPX) signal:
       - Extracts L+R (mono sum) at baseband
       - Locks to 19 kHz pilot tone
       - Demodulates L-R at 38 kHz (DSB-SC)
       - Combines to produce L and R channels
    6. Applies de-emphasis filter to each channel
    7. Resamples to 44.1kHz audio
    8. Puts stereo audio in audio_queue

    Note: Multiple demodulators can run simultaneously, each with its own
    subscriber queue from the IQBroadcaster. This allows multiple VFOs to
    process the same IQ samples without gaps.
    """

    def __init__(self, iq_queue, audio_queue, session_id, vfo_number=None):
        super().__init__(
            daemon=True, name=f"FMStereoDemodulator-{session_id}-VFO{vfo_number or ''}"
        )
        self.iq_queue = iq_queue
        self.audio_queue = audio_queue
        self.session_id = session_id
        self.vfo_number = vfo_number  # VFO number for multi-VFO mode
        self.running = True
        self.vfo_manager = VFOManager()
        self.audio_cfg = get_audio_queue_config()

        # Audio output parameters
        self.audio_sample_rate = 44100  # 44.1 kHz audio output
        self.target_chunk_size = 1024  # Minimum viable chunks for lowest latency (~23ms)

        # Audio buffer to accumulate samples
        self.audio_buffer = np.array([], dtype=np.float32)

        # Processing state
        self.last_sample = 0 + 0j
        self.sdr_sample_rate = None
        self.current_center_freq = None
        self.current_bandwidth = None

        # Filters (will be initialized when we know sample rates)
        self.decimation_filter: Optional[Tuple[np.ndarray, int]] = None
        self.audio_filter_left: Optional[np.ndarray] = None
        self.audio_filter_right: Optional[np.ndarray] = None
        self.pilot_filter: Optional[np.ndarray] = None
        self.subcarrier_filter: Optional[np.ndarray] = None
        self.deemphasis_filter: Optional[Tuple[np.ndarray, np.ndarray]] = None

        # Filter states (will be initialized when filters are created)
        self.audio_filter_left_state: Optional[np.ndarray] = None
        self.audio_filter_right_state: Optional[np.ndarray] = None
        self.pilot_filter_state: Optional[np.ndarray] = None
        self.subcarrier_filter_state: Optional[np.ndarray] = None

        # De-emphasis time constant (75 microseconds for US, 50 for EU)
        self.deemphasis_tau = 50e-6

        # Power measurement settings
        self.power_update_rate = 4.0  # Hz - send power measurements 4 times per second
        self.last_power_time = 0.0
        self.last_rf_power_db = None  # Cache last measured power

        # PLL state for pilot tone tracking
        self.pll_phase = 0.0
        self.pll_freq = 19000.0  # 19 kHz pilot tone

        # Performance monitoring stats
        self.stats: Dict[str, Any] = {
            "iq_chunks_in": 0,
            "iq_samples_in": 0,
            "audio_chunks_out": 0,
            "audio_samples_out": 0,
            "queue_timeouts": 0,
            "last_activity": None,
            "errors": 0,
        }
        self.stats_lock = threading.Lock()

    def _get_active_vfo(self):
        """Get VFO state for this demodulator's VFO."""
        if self.vfo_number is None:
            logger.error(
                f"vfo_number is required for FMStereoDemodulator (session {self.session_id})"
            )
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
        """Design cascaded decimation filters for efficient multi-stage decimation.

        For FM stereo, we need to preserve the full MPX signal up to 53 kHz:
        - L+R: 0-15 kHz (baseband)
        - Pilot: 19 kHz
        - L-R: 23-53 kHz (38 kHz ± 15 kHz DSB-SC)

        Uses cascaded low-order (4th) IIR filters to avoid numerical instability
        while providing good anti-aliasing at high decimation ratios.
        """
        # Calculate decimation factor to get to ~200 kHz intermediate rate
        # This preserves the full stereo MPX signal (0-53 kHz)
        target_rate = 200e3
        total_decimation = int(sdr_rate / target_rate)
        total_decimation = max(1, total_decimation)

        # For stereo, ensure we preserve at least 60 kHz bandwidth
        min_bandwidth = 60e3
        effective_bandwidth = max(bandwidth, min_bandwidth)

        # For high decimation ratios, use 2-stage cascaded decimation
        # This avoids numerical instability and provides better anti-aliasing
        stages = []

        if total_decimation <= 10:
            # Single stage for low decimation
            nyquist = sdr_rate / 2.0
            cutoff = effective_bandwidth / 2.0
            normalized_cutoff = min(0.4, max(0.01, cutoff / nyquist))
            b, a = signal.butter(4, normalized_cutoff, btype="low")
            stages.append(((b, a), total_decimation))
        else:
            # Two-stage cascaded decimation for better anti-aliasing
            # Stage 1: Decimate by 5
            stage1_decimation = 5
            nyquist1 = sdr_rate / 2.0
            # Cutoff at 80% of post-stage1 Nyquist for anti-aliasing
            cutoff1 = (sdr_rate / stage1_decimation) * 0.4
            normalized_cutoff1 = min(0.4, max(0.01, cutoff1 / nyquist1))
            b1, a1 = signal.butter(4, normalized_cutoff1, btype="low")
            stages.append(((b1, a1), stage1_decimation))

            # Stage 2: Decimate by remaining factor
            stage2_decimation = total_decimation // stage1_decimation
            if stage2_decimation > 1:
                rate_after_stage1 = sdr_rate / stage1_decimation
                nyquist2 = rate_after_stage1 / 2.0
                # Final cutoff preserves stereo bandwidth
                cutoff2 = min(
                    effective_bandwidth / 2.0, (rate_after_stage1 / stage2_decimation) * 0.4
                )
                normalized_cutoff2 = min(0.4, max(0.01, cutoff2 / nyquist2))
                b2, a2 = signal.butter(4, normalized_cutoff2, btype="low")
                stages.append(((b2, a2), stage2_decimation))

        return stages, total_decimation

    def _design_audio_filters(self, intermediate_rate):
        """Design audio low-pass filters for L and R channels.

        For FM stereo broadcast, audio bandwidth is 15 kHz.
        """
        # Audio cutoff at 15 kHz for broadcast FM
        cutoff = 15e3

        nyquist = intermediate_rate / 2.0
        normalized_cutoff = cutoff / nyquist

        # Ensure normalized cutoff is valid (0 < f < 1)
        normalized_cutoff = min(0.45, max(0.01, normalized_cutoff))

        numtaps = 101
        filter_taps = signal.firwin(numtaps, normalized_cutoff, window="hamming")

        return filter_taps

    def _design_pilot_filter(self, intermediate_rate):
        """Design bandpass filter to extract 19 kHz pilot tone."""
        # Narrow bandpass around 19 kHz (±500 Hz)
        center = 19000.0
        bandwidth = 1000.0  # ±500 Hz

        nyquist = intermediate_rate / 2.0
        low = (center - bandwidth / 2) / nyquist
        high = (center + bandwidth / 2) / nyquist

        # Ensure valid range
        low = max(0.01, min(0.99, low))
        high = max(0.01, min(0.99, high))

        numtaps = 101
        filter_taps = signal.firwin(numtaps, [low, high], pass_zero=False, window="hamming")

        return filter_taps

    def _design_subcarrier_filter(self, intermediate_rate):
        """Design bandpass filter to extract 38 kHz subcarrier (L-R signal)."""
        # Bandpass around 38 kHz (±15 kHz for audio bandwidth)
        center = 38000.0
        bandwidth = 30000.0  # ±15 kHz

        nyquist = intermediate_rate / 2.0
        low = (center - bandwidth / 2) / nyquist
        high = (center + bandwidth / 2) / nyquist

        # Ensure valid range
        low = max(0.01, min(0.99, low))
        high = max(0.01, min(0.99, high))

        numtaps = 101
        filter_taps = signal.firwin(numtaps, [low, high], pass_zero=False, window="hamming")

        return filter_taps

    def _design_deemphasis_filter(self, sample_rate):
        """Design de-emphasis filter for FM broadcast."""
        # De-emphasis filter: H(s) = 1 / (1 + s * tau)
        # Bilinear transform to digital filter
        tau = self.deemphasis_tau
        omega = 1.0 / tau
        b, a = signal.bilinear([1], [1 / omega, 1], sample_rate)
        return (b, a)

    def _frequency_translate(self, samples, offset_freq, sample_rate):
        """Translate frequency by offset (shift signal in frequency domain)."""
        if offset_freq == 0:
            return samples

        # Generate complex exponential for frequency shift
        t = np.arange(len(samples)) / sample_rate
        shift = np.exp(-2j * np.pi * offset_freq * t)
        return samples * shift

    def _fm_demodulate(self, samples):
        """
        Demodulate FM using phase differentiation.

        The instantaneous frequency is the derivative of the phase.
        For complex samples: angle(s[n] * conj(s[n-1]))
        """
        # Compute phase difference
        diff = samples[1:] * np.conj(samples[:-1])
        demodulated = np.angle(diff)

        # Prepend last sample state for continuity
        if self.last_sample is not None:
            first_diff = samples[0] * np.conj(self.last_sample)
            demodulated = np.concatenate(([np.angle(first_diff)], demodulated))
        else:
            demodulated = np.concatenate(([0], demodulated))

        # Save last sample for next iteration
        self.last_sample = samples[-1]

        return demodulated

    def _pll_lock_pilot(self, pilot_signal, sample_rate):
        """
        Phase-locked loop to track 19 kHz pilot tone.

        Returns the 38 kHz carrier (pilot × 2) for demodulating L-R.
        """
        # Simple PLL implementation
        # Generate local oscillator at current estimate
        t = np.arange(len(pilot_signal)) / sample_rate
        local_osc = np.cos(2 * np.pi * self.pll_freq * t + self.pll_phase)

        # Phase detector: multiply signal with local oscillator
        phase_error = pilot_signal * local_osc

        # Low-pass filter the phase error (simple moving average)
        # This gives us the phase error signal
        window_size = max(1, int(sample_rate / 1000))  # 1 ms window
        if len(phase_error) >= window_size:
            phase_error_filtered = np.convolve(
                phase_error, np.ones(window_size) / window_size, mode="same"
            )
        else:
            phase_error_filtered = phase_error

        # Update PLL frequency and phase based on error
        # Simple proportional control
        pll_gain = 0.01
        freq_correction = np.mean(phase_error_filtered) * pll_gain

        # Update state
        self.pll_freq = 19000.0 + freq_correction * 100
        self.pll_phase += 2 * np.pi * self.pll_freq * len(pilot_signal) / sample_rate
        self.pll_phase = self.pll_phase % (2 * np.pi)

        # Generate 38 kHz carrier (double the pilot frequency)
        carrier_38k = np.cos(2 * 2 * np.pi * self.pll_freq * t + 2 * self.pll_phase)

        return carrier_38k

    def _decode_stereo(self, mpx_signal, sample_rate):
        """
        Decode stereo multiplex signal into L and R channels.

        MPX signal structure:
        - L+R: 0-15 kHz (baseband mono)
        - Pilot: 19 kHz
        - L-R: 23-53 kHz (38 kHz ± 15 kHz, DSB-SC)

        Returns:
            (left_channel, right_channel) audio signals
        """
        # Extract L+R (baseband, 0-15 kHz)
        # Use the audio filter which is already designed for 15 kHz cutoff
        if self.audio_filter_left is None:
            # Fallback if not initialized
            logger.warning("Audio filter not initialized, using MPX directly")
            l_plus_r = mpx_signal
        else:
            l_plus_r, filter_state = signal.lfilter(
                self.audio_filter_left, 1, mpx_signal, zi=self.audio_filter_left_state
            )
            self.audio_filter_left_state = filter_state

        # Extract pilot tone (19 kHz)
        if self.pilot_filter is None:
            logger.warning("Pilot filter not initialized, stereo decoding disabled")
            # Fall back to mono
            return l_plus_r, l_plus_r

        pilot, filter_state = signal.lfilter(
            self.pilot_filter, 1, mpx_signal, zi=self.pilot_filter_state
        )
        self.pilot_filter_state = filter_state

        # Lock to pilot and generate 38 kHz carrier
        carrier_38k = self._pll_lock_pilot(pilot, sample_rate)

        # Extract L-R subcarrier (around 38 kHz)
        if self.subcarrier_filter is None:
            logger.warning("Subcarrier filter not initialized, stereo decoding disabled")
            # Fall back to mono
            return l_plus_r, l_plus_r

        subcarrier, filter_state = signal.lfilter(
            self.subcarrier_filter, 1, mpx_signal, zi=self.subcarrier_filter_state
        )
        self.subcarrier_filter_state = filter_state

        # Demodulate L-R by multiplying with 38 kHz carrier
        l_minus_r_raw = subcarrier * carrier_38k

        # Low-pass filter to extract audio (remove 76 kHz component from mixing)
        if self.audio_filter_right is None:
            l_minus_r = l_minus_r_raw
        else:
            l_minus_r, filter_state = signal.lfilter(
                self.audio_filter_right, 1, l_minus_r_raw, zi=self.audio_filter_right_state
            )
            self.audio_filter_right_state = filter_state

        # Combine to get L and R
        # L+R contains the mono sum, L-R contains the stereo difference
        # L = (L+R) + (L-R) / 2 simplifies to: L = L+R + L-R gives 2L, so divide by 2
        # R = (L+R) - (L-R) / 2 simplifies to: L+R - L-R gives 2R, so divide by 2
        # But L-R signal is already at half amplitude in FM stereo, so:
        left = l_plus_r + l_minus_r
        right = l_plus_r - l_minus_r

        return left, right

    def run(self):
        """Main demodulator loop."""
        logger.info(f"FM Stereo demodulator started for session {self.session_id}")

        # State for filter applications
        decimation_state = None
        deemph_left_state = None
        deemph_right_state = None

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

                # Check if there's an active VFO AFTER getting samples
                vfo_state = self._get_active_vfo()
                if not vfo_state:
                    # VFO inactive - discard these samples and continue
                    continue

                # Check if modulation is FM_STEREO
                if vfo_state.modulation.lower() != "fm_stereo":
                    # Wrong modulation - discard these samples and continue
                    logger.debug(f"Wrong modulation: {vfo_state.modulation}, expecting FM_STEREO")
                    continue

                # Extract samples and metadata
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

                logger.debug(
                    f"Processing {len(samples)} IQ samples at {sdr_sample_rate/1e6:.2f} MHz"
                )

                # Check if we need to reinitialize filters
                if (
                    self.sdr_sample_rate != sdr_sample_rate
                    or self.current_bandwidth != vfo_state.bandwidth
                    or self.decimation_filter is None
                ):
                    self.sdr_sample_rate = sdr_sample_rate
                    self.current_bandwidth = vfo_state.bandwidth

                    # Design filters
                    stages, total_decimation = self._design_decimation_filter(
                        sdr_sample_rate, vfo_state.bandwidth
                    )
                    self.decimation_filter = (stages, total_decimation)

                    intermediate_rate = sdr_sample_rate / total_decimation
                    self.audio_filter_left = self._design_audio_filters(intermediate_rate)
                    self.audio_filter_right = self._design_audio_filters(intermediate_rate)
                    self.pilot_filter = self._design_pilot_filter(intermediate_rate)
                    self.subcarrier_filter = self._design_subcarrier_filter(intermediate_rate)
                    self.deemphasis_filter = self._design_deemphasis_filter(intermediate_rate)

                    # Initialize filter states for each stage
                    initial_value = samples[0] if len(samples) > 0 else 0
                    decimation_state = []
                    for (b, a), _ in stages:
                        state = signal.lfilter_zi(b, a) * initial_value
                        decimation_state.append(state)

                    # Initialize audio filter states
                    self.audio_filter_left_state = self._resize_filter_state(
                        self.audio_filter_left_state, self.audio_filter_left, 0
                    )
                    self.audio_filter_right_state = self._resize_filter_state(
                        self.audio_filter_right_state, self.audio_filter_right, 0
                    )
                    self.pilot_filter_state = self._resize_filter_state(
                        self.pilot_filter_state, self.pilot_filter, 0
                    )
                    self.subcarrier_filter_state = self._resize_filter_state(
                        self.subcarrier_filter_state, self.subcarrier_filter, 0
                    )

                    b_deemph, a_deemph = self.deemphasis_filter  # type: ignore[misc]
                    deemph_left_state = self._resize_filter_state(
                        deemph_left_state, b_deemph, 0, a_deemph
                    )
                    deemph_right_state = self._resize_filter_state(
                        deemph_right_state, b_deemph, 0, a_deemph
                    )

                    logger.info(
                        f"Filters initialized: SDR rate={sdr_sample_rate/1e6:.2f} MHz, "
                        f"stages={len(stages)}, total_decimation={total_decimation}, "
                        f"intermediate={intermediate_rate/1e3:.1f} kHz"
                    )

                # Step 1: Frequency translation (tune to VFO frequency)
                # Skip if VFO frequency is not set (0 or invalid)
                if vfo_state.center_freq == 0:
                    logger.debug("VFO frequency not set, skipping frame")
                    continue

                offset_freq = vfo_state.center_freq - sdr_center_freq
                if abs(offset_freq) > sdr_sample_rate / 2:
                    logger.debug(
                        f"VFO frequency {vfo_state.center_freq} Hz is outside SDR bandwidth "
                        f"(SDR center: {sdr_center_freq} Hz, rate: {sdr_sample_rate} Hz)"
                    )
                    continue

                translated = self._frequency_translate(samples, offset_freq, sdr_sample_rate)

                # Step 2: Multi-stage cascaded decimation
                stages, total_decimation = self.decimation_filter

                # Apply each stage sequentially
                decimated = translated
                for stage_idx, ((b, a), stage_decimation) in enumerate(stages):
                    # Initialize state if needed
                    if decimation_state is None or stage_idx >= len(decimation_state):
                        # Should not happen if properly initialized, but safety check
                        if decimation_state is None:
                            decimation_state = []
                        decimation_state.append(signal.lfilter_zi(b, a) * decimated[0])

                    # Apply IIR filter
                    filtered, decimation_state[stage_idx] = signal.lfilter(
                        b, a, decimated, zi=decimation_state[stage_idx]
                    )

                    # Decimate
                    decimated = filtered[::stage_decimation]

                # Measure RF signal power AFTER filtering (within VFO bandwidth)
                # Calculate on every chunk for accurate squelch operation (if added later)
                signal_power = np.mean(np.abs(decimated) ** 2)
                rf_power_db = 10 * np.log10(signal_power + 1e-10)

                # Update cached power value periodically for UI updates (throttled to N Hz)
                current_time = time.time()
                should_update_ui_power = (current_time - self.last_power_time) >= (
                    1.0 / self.power_update_rate
                )

                if should_update_ui_power:
                    self.last_rf_power_db = rf_power_db
                    self.last_power_time = current_time

                # Calculate intermediate rate for processing
                intermediate_rate = sdr_sample_rate / total_decimation

                # Step 3: FM demodulation (produces MPX signal)
                mpx_signal = self._fm_demodulate(decimated)

                # Step 4: Stereo decoding
                left_audio, right_audio = self._decode_stereo(mpx_signal, intermediate_rate)

                # Step 5: De-emphasis (apply to both channels)
                b, a = self.deemphasis_filter  # type: ignore[misc]

                if deemph_left_state is None:
                    deemph_left_state = signal.lfilter_zi(b, a) * left_audio[0]
                if deemph_right_state is None:
                    deemph_right_state = signal.lfilter_zi(b, a) * right_audio[0]

                left_deemph, deemph_left_state = signal.lfilter(
                    b, a, left_audio, zi=deemph_left_state
                )
                right_deemph, deemph_right_state = signal.lfilter(
                    b, a, right_audio, zi=deemph_right_state
                )

                # Step 6: Resample to audio rate (44.1 kHz)
                num_output_samples = int(
                    len(left_deemph) * self.audio_sample_rate / intermediate_rate
                )
                if num_output_samples > 0:
                    left_resampled = signal.resample(left_deemph, num_output_samples)
                    right_resampled = signal.resample(right_deemph, num_output_samples)

                    # Apply moderate amplification (much lower than mono version)
                    audio_gain = 1.2  # 1.2x amplification
                    left_resampled = left_resampled * audio_gain
                    right_resampled = right_resampled * audio_gain

                    # Soft clipping using tanh for smooth saturation
                    # This is much gentler than hard clipping
                    left_resampled = np.tanh(left_resampled * 0.9) * 0.95
                    right_resampled = np.tanh(right_resampled * 0.9) * 0.95

                    # Interleave L and R channels for stereo output
                    # Format: [L0, R0, L1, R1, L2, R2, ...]
                    audio_stereo = np.empty(num_output_samples * 2, dtype=np.float32)
                    audio_stereo[0::2] = left_resampled
                    audio_stereo[1::2] = right_resampled

                    # NOTE: Volume is applied by WebAudioStreamer, not here
                    # This allows per-session volume control

                    # No squelch for FM Stereo - let all audio through
                    # FM broadcast signals are typically strong and don't need squelch

                    # Convert to float32
                    audio_stereo = audio_stereo.astype(np.float32)

                    # Buffer audio samples to create consistent chunk sizes
                    self.audio_buffer = np.concatenate([self.audio_buffer, audio_stereo])

                    # CRITICAL: Limit buffer size to prevent unbounded growth
                    # If buffer grows too large (>10 chunks), drop oldest data
                    # Note: chunk size is doubled for stereo (L+R interleaved)
                    max_buffer_samples = (
                        self.target_chunk_size
                        * 2
                        * self.audio_cfg.demod_audio_internal_buffer_chunks
                    )
                    if len(self.audio_buffer) > max_buffer_samples:
                        # Keep only the most recent data
                        self.audio_buffer = self.audio_buffer[-max_buffer_samples:]
                        logger.warning(
                            f"Audio buffer overflow ({len(self.audio_buffer)} samples), "
                            f"dropping old audio to prevent lag buildup"
                        )

                    # Send chunks of target size when buffer is full enough
                    # For stereo, chunk size is doubled (L+R samples)
                    stereo_chunk_size = self.target_chunk_size * 2
                    while len(self.audio_buffer) >= stereo_chunk_size:
                        # Extract a chunk
                        chunk = self.audio_buffer[:stereo_chunk_size]
                        self.audio_buffer = self.audio_buffer[stereo_chunk_size:]

                        # Always output audio (UI handles muting, transcription always active)
                        # Put audio chunk in queue - use put_nowait to avoid blocking
                        # If queue is full, skip this chunk to prevent buffer buildup
                        try:
                            self.audio_queue.put_nowait(
                                {
                                    "session_id": self.session_id,
                                    "audio": chunk,
                                    "vfo_number": self.vfo_number,  # Tag audio with VFO number
                                    "audio_type": "stereo",  # Explicitly mark as stereo (interleaved L/R)
                                    "rf_power_db": self.last_rf_power_db,  # Include latest power measurement
                                }
                            )
                            # Update stats
                            with self.stats_lock:
                                self.stats["audio_chunks_out"] += 1
                                self.stats["audio_samples_out"] += len(chunk)
                            logger.debug(f"Queued {len(chunk)} stereo samples")
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
                    logger.error(f"Error in FM Stereo demodulator: {str(e)}")
                    logger.exception(e)
                    with self.stats_lock:
                        self.stats["errors"] += 1
                time.sleep(0.1)

        logger.info(f"FM Stereo demodulator stopped for session {self.session_id}")

    def stop(self):
        """Stop the demodulator thread."""
        self.running = False
