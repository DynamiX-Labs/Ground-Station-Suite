# Ground Station - FM Demodulator
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
from collections import deque
from math import ceil
from typing import Any, Dict, Optional, Tuple

import numpy as np
try:
    import webrtcvad
except ImportError:
    webrtcvad = None
from scipy import signal

from common.audio_queue_config import get_audio_queue_config
from vfos.state import VFOManager

logger = logging.getLogger("fm-demodulator")


class FMDemodulator(threading.Thread):
    """
    FM demodulator that consumes IQ data and produces audio samples.

    This demodulator:
    1. Reads IQ samples from iq_queue (a subscriber queue from IQBroadcaster)
    2. Translates frequency based on VFO center frequency
    3. Decimates to appropriate bandwidth
    4. Demodulates FM using phase differentiation
    5. Applies de-emphasis filter
    6. Resamples to 44.1kHz audio
    7. Puts audio in audio_queue

    Note: Multiple demodulators can run simultaneously, each with its own
    subscriber queue from the IQBroadcaster. This allows multiple VFOs to
    process the same IQ samples without gaps.
    """

    VALID_SQUELCH_MODES = {"carrier", "voice", "hybrid"}
    VALID_VAD_SENSITIVITIES = {"low", "medium", "high"}

    def __init__(
        self,
        iq_queue,
        audio_queue,
        session_id,
        internal_mode=False,
        center_freq=None,
        bandwidth=None,
        vfo_number=None,
    ):
        super().__init__(daemon=True, name=f"FMDemodulator-{session_id}-VFO{vfo_number or ''}")
        self.iq_queue = iq_queue
        self.audio_queue = audio_queue
        self.session_id = session_id
        self.vfo_number = vfo_number  # VFO number for multi-VFO mode
        self.running = True
        self.vfo_manager = VFOManager()
        self.audio_cfg = get_audio_queue_config()

        # Internal mode: bypasses VFO checks and uses provided parameters
        self.internal_mode = internal_mode
        self.internal_center_freq = center_freq  # Used if internal_mode=True
        self.internal_bandwidth = bandwidth or 12500  # Default to 12.5 kHz for SSTV

        # Audio output parameters
        self.audio_sample_rate = 44100  # 44.1 kHz audio output
        self.target_chunk_size = 1024  # Minimum viable chunks for lowest latency (~23ms)

        # Audio buffer to accumulate samples
        self.audio_buffer = np.array([], dtype=np.float32)

        # Carrier squelch state (RF-power/hysteresis gate)
        self.squelch_open = False

        # Voice squelch state (post-demod audio VAD gate)
        self.voice_squelch_open = False
        self.current_squelch_mode = "carrier"

        # Processing state
        self.last_sample = 0 + 0j
        self.sdr_sample_rate = None
        self.current_center_freq = None
        self.current_bandwidth = None

        # Filters (will be initialized when we know sample rates)
        self.decimation_filter: Optional[Tuple[np.ndarray, int]] = None
        self.audio_filter: Optional[np.ndarray] = None
        self.deemphasis_filter: Optional[Tuple[np.ndarray, np.ndarray]] = None

        # De-emphasis time constant (75 microseconds for US, 50 for EU)
        self.deemphasis_tau = 75e-6

        # Power measurement settings
        self.power_update_rate = 4.0  # Hz - send power measurements 4 times per second
        self.last_power_time = 0.0
        self.last_rf_power_db = None  # Cache last measured power

        # Voice squelch/VAD settings
        self.vad_sample_rate = 16000
        self.vad_frame_ms = 20
        self.vad_frame_samples = int(self.vad_sample_rate * self.vad_frame_ms / 1000.0)
        self.vad_freq_bins = np.fft.rfftfreq(self.vad_frame_samples, d=1.0 / self.vad_sample_rate)
        self.vad_open_window_ms = 200
        self.vad_open_window_frames = max(1, self.vad_open_window_ms // self.vad_frame_ms)
        self.vad_preroll_ms = 200
        self.vad_preroll_samples = int(self.audio_sample_rate * self.vad_preroll_ms / 1000.0)
        self.vad_frame_buffer = np.array([], dtype=np.float32)
        self.vad_recent_voiced: deque[bool] = deque(maxlen=self.vad_open_window_frames)
        self.vad_recent_rms: deque[float] = deque(maxlen=50)  # ~1s at 20ms frames
        self.vad_hangover_frames_remaining = 0
        self.vad_preroll_buffer = np.array([], dtype=np.float32)
        self.vad_noise_rms = 0.003
        self.vad_last_frame_voiced = False
        self.vad_recent_voiced_ratio = 0.0
        self.vad_modulation_index = 0.0
        self.vad_last_stationary_noise = False
        self.vad_low_modulation_frames = 0
        self.vad_high_modulation_frames = 0
        self.vad_last_frame_rms = 0.0
        self.vad_last_frame_flatness = 1.0
        self.vad_last_frame_band_ratio_db = 0.0
        self.vad_last_frame_zcr = 0.0
        self.vad_last_webrtc_speech = False
        if webrtcvad is not None:
            self.webrtc_vad = webrtcvad.Vad(2)
        else:
            self.webrtc_vad = None
        self.last_squelch_debug_log_time = 0.0
        self.last_audio_overflow_warning_time = 0.0
        self.last_squelch_debug: Dict[str, Any] = {
            "mode": "carrier",
            "gate_open": False,
            "carrier_open": False,
            "voice_open": False,
        }

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
        """Get VFO state for this demodulator's VFO."""
        if self.vfo_number is None:
            logger.error(f"vfo_number is required for FMDemodulator (session {self.session_id})")
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

        Uses cascaded low-order (4th) IIR filters to avoid numerical instability
        while providing good anti-aliasing at high decimation ratios.
        """
        # Calculate decimation factor to get to ~200 kHz intermediate rate
        target_rate = 200e3
        total_decimation = int(sdr_rate / target_rate)
        total_decimation = max(1, total_decimation)

        # For high decimation ratios, use 2-stage cascaded decimation
        # This avoids numerical instability and provides better anti-aliasing
        stages = []

        if total_decimation <= 10:
            # Single stage for low decimation
            nyquist = sdr_rate / 2.0
            cutoff = bandwidth / 2.0
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
                # Final cutoff is bandwidth-limited
                cutoff2 = min(bandwidth / 2.0, (rate_after_stage1 / stage2_decimation) * 0.4)
                normalized_cutoff2 = min(0.4, max(0.01, cutoff2 / nyquist2))
                b2, a2 = signal.butter(4, normalized_cutoff2, btype="low")
                stages.append(((b2, a2), stage2_decimation))

        return stages, total_decimation

    def _design_audio_filter(self, intermediate_rate, vfo_bandwidth):
        """Design audio low-pass filter based on VFO bandwidth.

        For FM, the audio bandwidth is derived from the RF bandwidth:
        - Narrow FM (< 25 kHz): ~3-5 kHz audio (voice)
        - Medium FM (25-100 kHz): scaled proportionally
        - Wide FM (> 100 kHz): ~15 kHz audio (broadcast/music)
        """
        # Calculate audio cutoff based on VFO bandwidth
        # Use a reasonable fraction of the RF bandwidth for audio
        if vfo_bandwidth < 25e3:
            # Narrowband FM: limit to voice bandwidth
            cutoff = min(3e3, vfo_bandwidth * 0.3)
        elif vfo_bandwidth < 100e3:
            # Medium bandwidth: scale proportionally
            cutoff = vfo_bandwidth * 0.15
        else:
            # Wideband FM: allow up to 15 kHz for music
            cutoff = min(15e3, vfo_bandwidth * 0.15)

        # Ensure minimum cutoff frequency
        cutoff = max(cutoff, 500)  # At least 500 Hz

        nyquist = intermediate_rate / 2.0
        normalized_cutoff = cutoff / nyquist

        # Ensure normalized cutoff is valid (0 < f < 1)
        normalized_cutoff = min(0.45, max(0.01, normalized_cutoff))

        numtaps = 101
        filter_taps = signal.firwin(numtaps, normalized_cutoff, window="hamming")

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

    def _is_vfo_in_sdr_bandwidth(
        self, vfo_center: float, sdr_center: float, sdr_sample_rate: float
    ):
        """
        Check if VFO center frequency is within SDR bandwidth (with small edge margin).

        Returns tuple: (is_in_band, offset_from_sdr_center, margin_hz)
        """
        offset = vfo_center - sdr_center
        half_sdr_bandwidth = sdr_sample_rate / 2.0
        usable_bandwidth = half_sdr_bandwidth * 0.98  # 2% margin for roll-off
        is_in_band = abs(offset) <= usable_bandwidth
        margin_hz = usable_bandwidth - abs(offset)
        return is_in_band, offset, margin_hz

    def _normalize_squelch_mode(self, squelch_mode: Optional[str]) -> str:
        if squelch_mode is None:
            return "carrier"
        normalized_mode = str(squelch_mode).lower().strip()
        if normalized_mode not in self.VALID_SQUELCH_MODES:
            return "carrier"
        return normalized_mode

    def _normalize_vad_sensitivity(self, vad_sensitivity: Optional[str]) -> str:
        if vad_sensitivity is None:
            return "medium"
        normalized_sensitivity = str(vad_sensitivity).lower().strip()
        if normalized_sensitivity not in self.VALID_VAD_SENSITIVITIES:
            return "medium"
        return normalized_sensitivity

    def _normalize_vad_close_delay(self, close_delay_ms: Optional[int]) -> int:
        if close_delay_ms is None:
            return 300
        try:
            parsed_close_delay = int(close_delay_ms)
        except (TypeError, ValueError):
            parsed_close_delay = 300
        return max(50, min(500, parsed_close_delay))

    def _get_vad_profile(self, sensitivity: str) -> Dict[str, float]:
        # "high" means more sensitive voice opening from the user's perspective.
        profiles = {
            "low": {
                # Previous "medium" behavior.
                "aggressiveness": 1,
                "open_ratio": 0.45,
                "close_ratio": 0.15,
                "mod_open_min": 0.14,
                "mod_keep_min": 0.08,
                "mod_stationary_max": 0.09,
                "rms_multiplier": 2.0,
                "flatness_max": 0.70,
                "band_ratio_db_min": 0.5,
                "zcr_max": 0.35,
            },
            "medium": {
                # Previous "high" behavior.
                "aggressiveness": 0,
                "open_ratio": 0.30,
                "close_ratio": 0.10,
                "mod_open_min": 0.12,
                "mod_keep_min": 0.07,
                "mod_stationary_max": 0.08,
                "rms_multiplier": 1.7,
                "flatness_max": 0.80,
                "band_ratio_db_min": -1.0,
                "zcr_max": 0.42,
            },
            "high": {
                # New most-sensitive profile.
                "aggressiveness": 0,
                "open_ratio": 0.22,
                "close_ratio": 0.08,
                "mod_open_min": 0.10,
                "mod_keep_min": 0.06,
                "mod_stationary_max": 0.08,
                "rms_multiplier": 1.5,
                "flatness_max": 0.86,
                "band_ratio_db_min": -2.0,
                "zcr_max": 0.50,
            },
        }
        return profiles.get(sensitivity, profiles["medium"])

    def _apply_carrier_squelch(self, rf_power_db: float, squelch_threshold_db: float) -> bool:
        squelch_hysteresis_db = 3.0
        if self.squelch_open:
            if rf_power_db < (squelch_threshold_db - squelch_hysteresis_db):
                self.squelch_open = False
        else:
            if rf_power_db > (squelch_threshold_db + squelch_hysteresis_db):
                self.squelch_open = True
        return self.squelch_open

    def _reset_voice_squelch_state(self) -> None:
        self.voice_squelch_open = False
        self.vad_hangover_frames_remaining = 0
        self.vad_frame_buffer = np.array([], dtype=np.float32)
        self.vad_recent_voiced.clear()
        self.vad_recent_rms.clear()
        self.vad_preroll_buffer = np.array([], dtype=np.float32)
        self.vad_last_frame_voiced = False
        self.vad_recent_voiced_ratio = 0.0
        self.vad_modulation_index = 0.0
        self.vad_last_stationary_noise = False
        self.vad_low_modulation_frames = 0
        self.vad_high_modulation_frames = 0
        self.vad_last_frame_rms = 0.0
        self.vad_last_frame_flatness = 1.0
        self.vad_last_frame_band_ratio_db = 0.0
        self.vad_last_frame_zcr = 0.0
        self.vad_last_webrtc_speech = False

    def _update_vad_noise_floor(self, frame_rms: float, frame_voiced: bool) -> None:
        if frame_voiced:
            return
        alpha = 0.95
        self.vad_noise_rms = (alpha * self.vad_noise_rms) + ((1.0 - alpha) * frame_rms)
        self.vad_noise_rms = max(1e-4, min(0.2, self.vad_noise_rms))

    def _compute_vad_frame_features(self, frame: np.ndarray) -> Dict[str, float]:
        frame_rms = float(np.sqrt(np.mean(frame * frame) + 1e-12))

        windowed = frame * np.hanning(len(frame))
        spectrum = np.abs(np.fft.rfft(windowed)) + 1e-12
        power_spectrum = spectrum * spectrum
        flatness = float(np.exp(np.mean(np.log(spectrum))) / np.mean(spectrum))

        speech_mask = (self.vad_freq_bins >= 300.0) & (self.vad_freq_bins <= 3000.0)
        high_mask = (self.vad_freq_bins > 3500.0) & (self.vad_freq_bins <= 7000.0)
        speech_energy = float(np.sum(power_spectrum[speech_mask]) + 1e-12)
        high_energy = float(np.sum(power_spectrum[high_mask]) + 1e-12)
        band_ratio_db = 10.0 * np.log10(speech_energy / high_energy)

        zero_crossings = np.count_nonzero(np.diff(np.signbit(frame)))
        zcr = zero_crossings / max(1, len(frame) - 1)

        return {
            "rms": frame_rms,
            "flatness": flatness,
            "band_ratio_db": float(band_ratio_db),
            "zcr": float(zcr),
        }

    def _detect_voice_frame(self, frame: np.ndarray, profile: Dict[str, float]) -> bool:
        frame_features = self._compute_vad_frame_features(frame)
        frame_rms = frame_features["rms"]
        flatness = frame_features["flatness"]
        band_ratio_db = frame_features["band_ratio_db"]
        zcr = frame_features["zcr"]
        self.vad_last_frame_rms = frame_rms
        self.vad_last_frame_flatness = flatness
        self.vad_last_frame_band_ratio_db = band_ratio_db
        self.vad_last_frame_zcr = zcr

        dynamic_rms_threshold = max(0.0035, self.vad_noise_rms * float(profile["rms_multiplier"]))

        try:
            pcm = np.clip(frame, -1.0, 1.0)
            pcm16 = (pcm * 32767.0).astype(np.int16)
            if self.webrtc_vad is not None:
                webrtc_is_speech = bool(
                    self.webrtc_vad.is_speech(pcm16.tobytes(), self.vad_sample_rate)
                )
            else:
                webrtc_is_speech = frame_rms > dynamic_rms_threshold
            self.vad_last_webrtc_speech = webrtc_is_speech

            # Noise-rejection guard for repeater hiss:
            # broadband noise often gets occasional false positives from WebRTC VAD.
            looks_like_broadband_noise = flatness > 0.80 and band_ratio_db < 0.0 and zcr > 0.30
            is_loud_enough = frame_rms > dynamic_rms_threshold
            final_voiced = webrtc_is_speech and is_loud_enough and not looks_like_broadband_noise

            self._update_vad_noise_floor(frame_rms, final_voiced)
            return final_voiced
        except Exception:
            # Keep decoder resilient to occasional VAD-frame runtime issues.
            self.vad_last_webrtc_speech = False
            self._update_vad_noise_floor(frame_rms, False)
            return False

    def _update_voice_squelch_state(
        self, audio_44k: np.ndarray, vad_sensitivity: str, vad_close_delay_ms: int
    ) -> bool:
        profile = self._get_vad_profile(vad_sensitivity)
        if self.webrtc_vad is not None:
            self.webrtc_vad.set_mode(int(profile["aggressiveness"]))

        hangover_frames = max(1, ceil(vad_close_delay_ms / self.vad_frame_ms))
        open_modulation_frames_required_by_sensitivity = {
            "low": max(3, ceil(self.vad_open_window_frames * 0.50)),
            "medium": max(3, ceil(self.vad_open_window_frames * 0.35)),
            "high": max(2, ceil(self.vad_open_window_frames * 0.25)),
        }
        close_low_modulation_ratio_by_sensitivity = {
            "low": 0.45,
            "medium": 0.35,
            "high": 0.30,
        }
        force_close_voiced_ratio_max_by_sensitivity = {
            "low": 0.28,
            "medium": 0.25,
            "high": 0.20,
        }
        open_modulation_frames_required = open_modulation_frames_required_by_sensitivity.get(
            vad_sensitivity, open_modulation_frames_required_by_sensitivity["medium"]
        )
        close_low_modulation_frames_required = max(
            3,
            ceil(
                hangover_frames
                * close_low_modulation_ratio_by_sensitivity.get(
                    vad_sensitivity, close_low_modulation_ratio_by_sensitivity["medium"]
                )
            ),
        )
        force_close_voiced_ratio_max = force_close_voiced_ratio_max_by_sensitivity.get(
            vad_sensitivity, force_close_voiced_ratio_max_by_sensitivity["medium"]
        )
        # Use a shorter modulation-history window for low close-delay settings so
        # noise closure reacts quickly after speech ends.
        if vad_close_delay_ms <= 100:
            modulation_window_frames = 8  # ~160 ms
            modulation_min_frames = 6
        elif vad_close_delay_ms <= 250:
            modulation_window_frames = 12  # ~240 ms
            modulation_min_frames = 8
        else:
            modulation_window_frames = 16  # ~320 ms
            modulation_min_frames = 10
        # For very short close delays, prioritize fast closure on stationary/noise-like
        # audio over voiced-ratio smoothing so the control feels responsive.
        enforce_force_close_voiced_ratio = vad_close_delay_ms >= 200
        stationary_frames_required = max(3, ceil(self.vad_open_window_frames * 0.30))

        audio_16k = signal.resample_poly(audio_44k, up=160, down=441).astype(np.float32)
        self.vad_frame_buffer = np.concatenate([self.vad_frame_buffer, audio_16k])

        while len(self.vad_frame_buffer) >= self.vad_frame_samples:
            frame = self.vad_frame_buffer[: self.vad_frame_samples]
            self.vad_frame_buffer = self.vad_frame_buffer[self.vad_frame_samples :]

            frame_voiced = self._detect_voice_frame(frame, profile)
            frame_rms = self.vad_last_frame_rms
            self.vad_recent_rms.append(frame_rms)
            if len(self.vad_recent_rms) >= modulation_min_frames:
                recent_rms_tail = list(self.vad_recent_rms)[-modulation_window_frames:]
                recent_rms_arr = np.array(recent_rms_tail, dtype=np.float32)
                rms_mean = float(np.mean(recent_rms_arr) + 1e-12)
                rms_std = float(np.std(recent_rms_arr))
                self.vad_modulation_index = rms_std / rms_mean
            else:
                self.vad_modulation_index = 0.0

            modulation_ready = len(self.vad_recent_rms) >= modulation_min_frames
            stationary_modulation_max = float(profile["mod_stationary_max"])
            stationary_modulation = (
                modulation_ready and self.vad_modulation_index <= stationary_modulation_max
            )
            low_modulation = modulation_ready and self.vad_modulation_index <= float(
                profile["mod_keep_min"]
            )
            high_modulation = modulation_ready and self.vad_modulation_index >= float(
                profile["mod_open_min"]
            )
            # Track sustained stationary/low modulation for close decisions.
            if stationary_modulation:
                self.vad_low_modulation_frames += 1
            else:
                self.vad_low_modulation_frames = 0

            if high_modulation and frame_voiced:
                self.vad_high_modulation_frames += 1
            else:
                self.vad_high_modulation_frames = 0

            # Reject persistent stationary "always voiced" noise.
            tentative_voiced_ratio = (
                sum(self.vad_recent_voiced) + (1 if frame_voiced else 0)
            ) / max(1, len(self.vad_recent_voiced) + 1)
            stationary_noise = (
                modulation_ready
                and tentative_voiced_ratio >= 0.45
                and self.vad_low_modulation_frames >= stationary_frames_required
                and stationary_modulation
            )
            self.vad_last_stationary_noise = bool(stationary_noise)
            if stationary_noise or stationary_modulation or low_modulation:
                frame_voiced = False

            self.vad_last_frame_voiced = frame_voiced
            self.vad_recent_voiced.append(frame_voiced)
            voiced_ratio = sum(self.vad_recent_voiced) / len(self.vad_recent_voiced)
            self.vad_recent_voiced_ratio = voiced_ratio

            if frame_voiced:
                self.vad_hangover_frames_remaining = hangover_frames
            elif self.vad_hangover_frames_remaining > 0:
                self.vad_hangover_frames_remaining -= 1

            if not self.voice_squelch_open:
                if (
                    len(self.vad_recent_voiced) >= self.vad_open_window_frames
                    and modulation_ready
                    and voiced_ratio >= float(profile["open_ratio"])
                    and self.vad_high_modulation_frames >= open_modulation_frames_required
                ):
                    self.voice_squelch_open = True
                    self.vad_hangover_frames_remaining = hangover_frames
            else:
                force_low_modulation_close = (
                    modulation_ready
                    and self.vad_low_modulation_frames >= close_low_modulation_frames_required
                )
                if enforce_force_close_voiced_ratio:
                    force_low_modulation_close = (
                        force_low_modulation_close and voiced_ratio <= force_close_voiced_ratio_max
                    )
                natural_close = (
                    self.vad_hangover_frames_remaining == 0
                    and voiced_ratio <= float(profile["close_ratio"])
                    and self.vad_modulation_index < float(profile["mod_open_min"])
                )
                if force_low_modulation_close or natural_close:
                    self.voice_squelch_open = False
                    self.vad_hangover_frames_remaining = 0

        return self.voice_squelch_open

    def _append_preroll(self, audio: np.ndarray) -> None:
        if self.vad_preroll_samples <= 0:
            return
        self.vad_preroll_buffer = np.concatenate([self.vad_preroll_buffer, audio])
        if len(self.vad_preroll_buffer) > self.vad_preroll_samples:
            self.vad_preroll_buffer = self.vad_preroll_buffer[-self.vad_preroll_samples :]

    def _apply_voice_squelch(
        self, audio: np.ndarray, vad_sensitivity: str, vad_close_delay_ms: int
    ) -> np.ndarray:
        was_open = self.voice_squelch_open
        is_open = self._update_voice_squelch_state(audio, vad_sensitivity, vad_close_delay_ms)

        if is_open:
            if not was_open and len(self.vad_preroll_buffer) > 0:
                audio_with_preroll = np.concatenate([self.vad_preroll_buffer, audio])
                self.vad_preroll_buffer = np.array([], dtype=np.float32)
                return audio_with_preroll
            self.vad_preroll_buffer = np.array([], dtype=np.float32)
            return audio

        self._append_preroll(audio)
        return np.zeros_like(audio)

    def _build_squelch_debug(
        self,
        squelch_mode: str,
        carrier_open: bool,
        voice_open: bool,
        gate_open: bool,
    ) -> Dict[str, Any]:
        return {
            "mode": squelch_mode,
            "gate_open": bool(gate_open),
            "carrier_open": bool(carrier_open),
            "voice_open": bool(voice_open),
        }

    def run(self):
        """Main demodulator loop."""
        logger.info(f"FM demodulator started for session {self.session_id}")

        # State for filter applications
        decimation_state = None
        audio_filter_state = None
        deemph_state = None

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

                # Update sample count and ingest accumulators
                with self.stats_lock:
                    self.stats["iq_samples_in"] += len(samples)
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
                else:
                    # Normal mode: check VFO state
                    vfo_state = self._get_active_vfo()
                    if not vfo_state:
                        # VFO inactive - discard these samples and continue
                        continue

                    # Check if modulation is FM
                    if vfo_state.modulation.lower() != "fm":
                        # Wrong modulation - discard these samples and continue
                        continue

                    vfo_center_freq = vfo_state.center_freq
                    vfo_bandwidth = vfo_state.bandwidth

                # Check if we need to reinitialize filters
                if (
                    self.sdr_sample_rate != sdr_sample_rate
                    or self.current_bandwidth != vfo_bandwidth
                    or self.decimation_filter is None
                ):
                    self.sdr_sample_rate = sdr_sample_rate
                    self.current_bandwidth = vfo_bandwidth

                    # Design filters
                    stages, total_decimation = self._design_decimation_filter(
                        sdr_sample_rate, vfo_bandwidth
                    )
                    self.decimation_filter = (stages, total_decimation)

                    intermediate_rate = sdr_sample_rate / total_decimation
                    self.audio_filter = self._design_audio_filter(intermediate_rate, vfo_bandwidth)
                    self.deemphasis_filter = self._design_deemphasis_filter(intermediate_rate)

                    # Initialize filter states for each stage
                    initial_value = samples[0] if len(samples) > 0 else 0
                    decimation_state = []
                    for (b, a), _ in stages:
                        state = signal.lfilter_zi(b, a) * initial_value
                        decimation_state.append(state)

                    # Initialize audio filter states
                    audio_filter_state = self._resize_filter_state(
                        audio_filter_state, self.audio_filter, 0
                    )
                    b_deemph, a_deemph = self.deemphasis_filter  # type: ignore[misc]
                    deemph_state = self._resize_filter_state(deemph_state, b_deemph, 0, a_deemph)

                    logger.info(
                        f"Filters initialized (internal_mode={self.internal_mode}): SDR rate={sdr_sample_rate/1e6:.2f} MHz, "
                        f"stages={len(stages)}, total_decimation={total_decimation}, "
                        f"intermediate={intermediate_rate/1e3:.1f} kHz"
                    )

                # Step 1: Frequency translation (tune to VFO frequency)
                # Skip if VFO frequency is not set (0 or invalid)
                if vfo_center_freq == 0:
                    logger.debug("VFO frequency not set, skipping frame")
                    continue

                # Validate VFO center is within SDR bandwidth (with edge margin)
                is_in_band, vfo_offset, margin = self._is_vfo_in_sdr_bandwidth(
                    vfo_center_freq, sdr_center_freq, sdr_sample_rate
                )

                if not is_in_band:
                    # VFO is outside SDR bandwidth - enter sleeping state, skip DSP for this chunk
                    with self.stats_lock:
                        self.stats["samples_dropped_out_of_band"] += len(samples)
                    if not self.is_sleeping:
                        self.is_sleeping = True
                        self.sleep_reason = (
                            f"VFO out of SDR bandwidth: VFO={vfo_center_freq/1e6:.3f}MHz, "
                            f"SDR={sdr_center_freq/1e6:.3f}MHz±{(sdr_sample_rate/2)/1e6:.2f}MHz, "
                            f"offset={vfo_offset/1e3:.1f}kHz, exceeded by {abs(margin)/1e3:.1f}kHz"
                        )
                        logger.warning(self.sleep_reason)
                    # Mirror sleeping state into stats
                    with self.stats_lock:
                        self.stats["is_sleeping"] = True
                    continue

                # If we were sleeping and now back in band, resume
                if self.is_sleeping:
                    self.is_sleeping = False
                    with self.stats_lock:
                        self.stats["is_sleeping"] = False
                    logger.info(
                        f"VFO back in SDR bandwidth, resuming FM demodulation: VFO={vfo_center_freq/1e6:.3f}MHz, "
                        f"SDR={sdr_center_freq/1e6:.3f}MHz, offset={vfo_offset/1e3:.1f}kHz"
                    )

                offset_freq = vfo_center_freq - sdr_center_freq

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

                # Measure RF signal power for squelch AFTER filtering (within VFO bandwidth)
                # Calculate on every chunk for accurate squelch operation
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

                intermediate_rate = sdr_sample_rate / total_decimation

                # Step 3: FM demodulation
                demodulated = self._fm_demodulate(decimated)

                # Step 4: Audio filtering
                if audio_filter_state is None:
                    # Initialize filter state on first run
                    audio_filter_state = signal.lfilter_zi(self.audio_filter, 1) * demodulated[0]

                audio_filtered, audio_filter_state = signal.lfilter(
                    self.audio_filter, 1, demodulated, zi=audio_filter_state
                )

                # Step 5: De-emphasis
                b, a = self.deemphasis_filter  # type: ignore[misc]

                if deemph_state is None:
                    # Initialize filter state on first run
                    deemph_state = signal.lfilter_zi(b, a) * audio_filtered[0]

                deemphasized, deemph_state = signal.lfilter(b, a, audio_filtered, zi=deemph_state)

                # Step 6: Resample to audio rate (44.1 kHz)
                num_output_samples = int(
                    len(deemphasized) * self.audio_sample_rate / intermediate_rate
                )
                if num_output_samples > 0:
                    audio = signal.resample(deemphasized, num_output_samples)

                    # NOTE: Volume is applied by WebAudioStreamer, not here
                    # This allows per-session volume control

                    # Resolve squelch settings from active VFO. Internal mode still reads live VFO
                    # values so automation can tune squelch behavior without restarting demod.
                    if self.internal_mode:
                        vfo_state_for_squelch = self._get_active_vfo()
                    else:
                        vfo_state_for_squelch = vfo_state

                    if vfo_state_for_squelch:
                        squelch_threshold_db = vfo_state_for_squelch.squelch
                        squelch_mode = self._normalize_squelch_mode(
                            getattr(vfo_state_for_squelch, "squelch_mode", "carrier")
                        )
                        vad_sensitivity = self._normalize_vad_sensitivity(
                            getattr(vfo_state_for_squelch, "vad_sensitivity", "medium")
                        )
                        vad_close_delay_ms = self._normalize_vad_close_delay(
                            getattr(vfo_state_for_squelch, "vad_close_delay_ms", 300)
                        )
                    else:
                        squelch_threshold_db = -200
                        squelch_mode = "carrier"
                        vad_sensitivity = "medium"
                        vad_close_delay_ms = 300

                    if squelch_mode != self.current_squelch_mode:
                        # Avoid stale frame/hangover state when switching squelch strategies.
                        self._reset_voice_squelch_state()
                        self.current_squelch_mode = squelch_mode

                    carrier_open = self._apply_carrier_squelch(rf_power_db, squelch_threshold_db)
                    voice_open = self.voice_squelch_open

                    if squelch_mode == "carrier":
                        voice_open = False
                        if not carrier_open:
                            audio = np.zeros_like(audio)
                        gate_open = carrier_open
                    elif squelch_mode == "voice":
                        audio = self._apply_voice_squelch(
                            audio,
                            vad_sensitivity=vad_sensitivity,
                            vad_close_delay_ms=vad_close_delay_ms,
                        )
                        voice_open = self.voice_squelch_open
                        gate_open = voice_open
                    else:  # hybrid
                        audio = self._apply_voice_squelch(
                            audio,
                            vad_sensitivity=vad_sensitivity,
                            vad_close_delay_ms=vad_close_delay_ms,
                        )
                        voice_open = self.voice_squelch_open
                        if not carrier_open:
                            audio = np.zeros_like(audio)
                        gate_open = carrier_open and voice_open

                    if should_update_ui_power:
                        self.last_squelch_debug = self._build_squelch_debug(
                            squelch_mode=squelch_mode,
                            carrier_open=carrier_open,
                            voice_open=voice_open,
                            gate_open=gate_open,
                        )

                    with self.stats_lock:
                        self.stats["squelch_mode"] = squelch_mode
                        self.stats["squelch_gate_open"] = gate_open
                        self.stats["carrier_squelch_open"] = carrier_open
                        self.stats["voice_squelch_open"] = voice_open

                    if (
                        logger.isEnabledFor(logging.DEBUG)
                        and current_time - self.last_squelch_debug_log_time >= 1.0
                    ):
                        self.last_squelch_debug_log_time = current_time
                        logger.debug(
                            "Squelch[%s:%s] mode=%s gate=%s carrier=%s voice=%s rf=%.1fdB thr=%.1fdB",
                            self.session_id,
                            self.vfo_number,
                            squelch_mode,
                            gate_open,
                            carrier_open,
                            voice_open,
                            rf_power_db,
                            squelch_threshold_db,
                        )

                    # Apply amplification and clipping AFTER squelch, so VAD sees
                    # unclipped audio and doesn't over-trigger on broadband hiss.
                    audio_gain = 3.0  # 3x amplification (adjustable)
                    audio = np.clip(audio * audio_gain, -0.95, 0.95)

                    # Convert to float32
                    audio = audio.astype(np.float32)

                    # Buffer audio samples to create consistent chunk sizes
                    self.audio_buffer = np.concatenate([self.audio_buffer, audio])

                    # CRITICAL: Limit buffer size to prevent unbounded growth
                    # Base cap for low-latency steady-state operation.
                    base_max_buffer_samples = (
                        self.target_chunk_size * self.audio_cfg.demod_audio_internal_buffer_chunks
                    )
                    # Voice/hybrid squelch can release a burst that includes pre-roll.
                    # Allow enough bounded headroom so a normal squelch transition
                    # does not immediately trigger overflow warnings.
                    voice_burst_headroom_samples = max(
                        self.vad_preroll_samples + (self.target_chunk_size * 2),
                        len(audio) + self.target_chunk_size,
                    )
                    voice_burst_headroom_samples = min(
                        base_max_buffer_samples * 3,
                        voice_burst_headroom_samples,
                    )
                    if self.current_squelch_mode in {"voice", "hybrid"}:
                        max_buffer_samples = max(
                            base_max_buffer_samples, voice_burst_headroom_samples
                        )
                    else:
                        max_buffer_samples = base_max_buffer_samples

                    if len(self.audio_buffer) > max_buffer_samples:
                        # Keep only the most recent data
                        self.audio_buffer = self.audio_buffer[-max_buffer_samples:]
                        # Only log warning if not in internal mode (used by decoders like SSTV)
                        if not self.internal_mode:
                            now = time.time()
                            if now - self.last_audio_overflow_warning_time >= 5.0:
                                self.last_audio_overflow_warning_time = now
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

                        # Prepare audio message with RF power measurement
                        audio_message = {
                            "session_id": self.session_id,
                            "audio": chunk,
                            "vfo_number": self.vfo_number,  # Tag audio with VFO number
                            "rf_power_db": self.last_rf_power_db,  # Include latest power measurement
                            "squelch_debug": dict(self.last_squelch_debug),
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
                            # Also collapse any queued backlog so we don't repeatedly
                            # overflow internal buffering while the consumer catches up.
                            self.audio_buffer = self.audio_buffer[-self.target_chunk_size :]
                            break  # Exit while loop to process next IQ samples
                        except Exception as e:
                            logger.warning(f"Could not queue audio: {str(e)}")
                            break

            except Exception as e:
                if self.running:
                    logger.error(f"Error in FM demodulator: {str(e)}")
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
                        # Keep stats["is_sleeping"] in sync with attribute
                        self.stats["is_sleeping"] = self.is_sleeping

                    # Reset window
                    ingest_window_start = now
                    ingest_samples_accum = 0
                    ingest_chunks_accum = 0

                    # Advance the stats tick reference to avoid re-triggering every loop
                    last_stats_time = now

        logger.info(f"FM demodulator stopped for session {self.session_id}")

    def stop(self):
        """Stop the demodulator thread."""
        self.running = False
