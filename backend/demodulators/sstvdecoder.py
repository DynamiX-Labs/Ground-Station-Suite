# Ground Station - SSTV Decoder v2 (Process-based with integrated FM demodulation)
# Developed by Claude (Anthropic AI) for the Ground Station project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import base64
import io
import json
import logging
import os
import queue
import time
from enum import Enum
from typing import Any, Dict

import numpy as np
import psutil
from PIL import Image
from scipy import signal
from scipy.signal.windows import hann

# Optional process title support (parity with other decoders)
try:
    import setproctitle

    HAS_SETPROCTITLE = True
except Exception:
    HAS_SETPROCTITLE = False

from demodulators.basedecoderprocess import BaseDecoderProcess

logger = logging.getLogger("sstvdecoder")


class DecoderStatus(Enum):
    """Decoder status values."""

    IDLE = "idle"
    LISTENING = "listening"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    SLEEPING = "sleeping"  # VFO out of SDR bandwidth
    COMPLETED = "completed"
    ERROR = "error"


class SSTVMode(Enum):
    """SSTV mode definitions"""

    SCOTTIE_S1 = {
        "vis_code": 60,
        "name": "Scottie 1",
        "width": 320,
        "height": 256,
        "sync_pulse": 0.009,
        "sync_porch": 0.0015,
        "sep_pulse": 0.0015,
        "scan_time": 0.138240,
        "pixel_time": 0.138240 / 320,
        "chan_count": 3,
        "chan_sync": 2,
        "color_mode": "GBR",
        "window_factor": 3.82,
        "line_time": 0.009 + 3 * (0.0015 + 0.138240),
    }

    MARTIN_M1 = {
        "vis_code": 44,
        "name": "Martin 1",
        "width": 320,
        "height": 256,
        "sync_pulse": 0.004862,
        "sync_porch": 0.000572,
        "sep_pulse": 0.000572,
        "scan_time": 0.146432,
        "pixel_time": 0.146432 / 320,
        "chan_count": 3,
        "chan_sync": 0,
        "color_mode": "GBR",
        "window_factor": 3.82,
        "line_time": 0.004862 + 0.000572 + 3 * (0.000572 + 0.146432),
    }

    ROBOT_36 = {
        "vis_code": 8,
        "name": "Robot 36",
        "width": 320,
        "height": 240,
        "sync_pulse": 0.009,
        "sync_porch": 0.003,
        "sep_pulse": 0.004500,
        "sep_porch": 0.001500,
        "scan_time": 0.088,
        "half_scan_time": 0.044,
        "pixel_time": 0.088 / 320,
        "chan_count": 2,
        "chan_sync": 0,
        "color_mode": "YUV",
        "window_factor": 7.70,
        "line_time": 0.009 + 0.003 + (0.004500 + 0.088) + 0.001500 + 0.044,
    }

    SCOTTIE_S2 = {
        "vis_code": 56,
        "name": "Scottie 2",
        "width": 320,
        "height": 256,
        "sync_pulse": 0.009,
        "sync_porch": 0.0015,
        "sep_pulse": 0.0015,
        "scan_time": 0.088064,
        "pixel_time": 0.088064 / 320,
        "chan_count": 3,
        "chan_sync": 2,
        "color_mode": "GBR",
        "window_factor": 3.82,
        "line_time": 0.009 + 3 * (0.0015 + 0.088064),
    }

    SCOTTIE_DX = {
        "vis_code": 76,
        "name": "Scottie DX",
        "width": 320,
        "height": 256,
        "sync_pulse": 0.009,
        "sync_porch": 0.0015,
        "sep_pulse": 0.0015,
        "scan_time": 0.345600,
        "pixel_time": 0.345600 / 320,
        "chan_count": 3,
        "chan_sync": 2,
        "color_mode": "GBR",
        "window_factor": 3.82,
        "line_time": 0.009 + 3 * (0.0015 + 0.345600),
    }

    WRAASE_SC2_180 = {
        "vis_code": 55,
        "name": "Wraase SC2-180",
        "width": 320,
        "height": 256,
        "sync_pulse": 0.009,
        "sync_porch": 0.0015,
        "sep_pulse": 0.0015,
        "scan_time": 0.235,
        "pixel_time": 0.235 / 320,
        "chan_count": 3,
        "chan_sync": 2,
        "color_mode": "GBR",
        "window_factor": 3.82,
        "line_time": 0.009 + 3 * (0.0015 + 0.235),
    }

    MARTIN_M2 = {
        "vis_code": 40,
        "name": "Martin 2",
        "width": 320,
        "height": 256,
        "sync_pulse": 0.004862,
        "sync_porch": 0.000572,
        "sep_pulse": 0.000572,
        "scan_time": 0.073216,
        "pixel_time": 0.073216 / 320,
        "chan_count": 3,
        "chan_sync": 0,
        "color_mode": "GBR",
        "window_factor": 3.82,
        "line_time": 0.004862 + 0.000572 + 3 * (0.000572 + 0.073216),
    }


# VIS code constants
VIS_BIT_SIZE = 0.030
BREAK_OFFSET = 0.300
LEADER_OFFSET = 0.010 + BREAK_OFFSET
VIS_START_OFFSET = 0.300 + LEADER_OFFSET
HDR_SIZE = 0.030 + VIS_START_OFFSET
HDR_WINDOW_SIZE = 0.010


def calc_lum(freq):
    """Converts SSTV pixel frequency range into 0-255 luminance byte"""
    lum = int(round((freq - 1500) / 3.1372549))
    return min(max(lum, 0), 255)


class SSTVDecoder(BaseDecoderProcess):
    """Process-based SSTV decoder with integrated FM demodulation"""

    def __init__(
        self,
        iq_queue,
        data_queue,
        session_id,
        config,  # Pre-resolved DecoderConfig from DecoderConfigService (contains all params + metadata)
        vfo=None,
        sample_rate=44100,
        output_dir="data/decoded",
        **kwargs,
    ):
        super().__init__(
            iq_queue=iq_queue,
            data_queue=data_queue,
            session_id=session_id,
            config=config,
            output_dir=output_dir,
            vfo=vfo,
        )

        self.audio_sample_rate = sample_rate
        self.audio_buffer = np.array([], dtype=np.float32)
        self.mode = None

        # Extract satellite and transmitter metadata from config (same pattern as FSKDecoder)
        self.satellite = config.satellite or {}
        self.transmitter = config.transmitter or {}

        # FM demodulator state
        self.last_sample = 0 + 0j
        self.sdr_sample_rate = None
        self.decimation_filter = None
        self.audio_filter = None
        self.deemphasis_filter = None
        self.deemphasis_tau = 75e-6

        # Cached VFO state from IQ messages
        self.cached_vfo_state = None

        # Sleeping state when VFO is out of SDR bandwidth
        self.is_sleeping = False
        self.sleep_reason = None

        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"SSTV decoder v2 initialized for session {session_id}, VFO {vfo}")

        # Log satellite and transmitter details for testing/debugging
        if self.satellite:
            logger.info(f"Satellite details: {self.satellite}")
        else:
            logger.info("No satellite details provided")

        if self.transmitter:
            logger.info(f"Transmitter details: {self.transmitter}")
        else:
            logger.info("No transmitter details provided")

    def _get_decoder_type_for_init(self) -> str:
        return "SSTV"

    # ========== FM Demodulation Methods (copied from FMDemodulator) ==========

    def _frequency_translate(self, samples, offset_freq, sample_rate):
        """Translate frequency by offset (shift signal in frequency domain)."""
        if offset_freq == 0:
            return samples
        t = np.arange(len(samples)) / sample_rate
        shift = np.exp(-2j * np.pi * offset_freq * t)
        return samples * shift

    def _design_decimation_filter(self, sdr_rate, bandwidth):
        """Design cascaded decimation filters for efficient multi-stage decimation."""
        target_rate = 200e3
        total_decimation = int(sdr_rate / target_rate)
        total_decimation = max(1, total_decimation)

        stages = []

        if total_decimation <= 10:
            nyquist = sdr_rate / 2.0
            cutoff = bandwidth / 2.0
            normalized_cutoff = min(0.4, max(0.01, cutoff / nyquist))
            b, a = signal.butter(4, normalized_cutoff, btype="low")
            stages.append(((b, a), total_decimation))
        else:
            stage1_decimation = 5
            nyquist1 = sdr_rate / 2.0
            cutoff1 = (sdr_rate / stage1_decimation) * 0.4
            normalized_cutoff1 = min(0.4, max(0.01, cutoff1 / nyquist1))
            b1, a1 = signal.butter(4, normalized_cutoff1, btype="low")
            stages.append(((b1, a1), stage1_decimation))

            stage2_decimation = total_decimation // stage1_decimation
            if stage2_decimation > 1:
                rate_after_stage1 = sdr_rate / stage1_decimation
                nyquist2 = rate_after_stage1 / 2.0
                cutoff2 = min(bandwidth / 2.0, (rate_after_stage1 / stage2_decimation) * 0.4)
                normalized_cutoff2 = min(0.4, max(0.01, cutoff2 / nyquist2))
                b2, a2 = signal.butter(4, normalized_cutoff2, btype="low")
                stages.append(((b2, a2), stage2_decimation))

        return stages, total_decimation

    def _design_audio_filter(self, intermediate_rate, vfo_bandwidth):
        """Design audio low-pass filter based on VFO bandwidth."""
        if vfo_bandwidth < 25e3:
            cutoff = min(3e3, vfo_bandwidth * 0.3)
        elif vfo_bandwidth < 100e3:
            cutoff = vfo_bandwidth * 0.15
        else:
            cutoff = min(15e3, vfo_bandwidth * 0.15)

        # Keep SSTV tone range (1200-2300 Hz) intact even if VFO BW is small.
        cutoff = max(cutoff, 3000)
        nyquist = intermediate_rate / 2.0
        normalized_cutoff = cutoff / nyquist
        normalized_cutoff = min(0.45, max(0.01, normalized_cutoff))

        numtaps = 101
        filter_taps = signal.firwin(numtaps, normalized_cutoff, window="hamming")
        return filter_taps

    def _design_deemphasis_filter(self, sample_rate):
        """Design de-emphasis filter for FM broadcast."""
        tau = self.deemphasis_tau
        omega = 1.0 / tau
        b, a = signal.bilinear([1], [1 / omega, 1], sample_rate)
        return (b, a)

    def _is_vfo_in_sdr_bandwidth(self, vfo_center, sdr_center, sdr_sample_rate):
        """
        Check if VFO center frequency is within SDR bandwidth (with small edge margin).

        Returns tuple: (is_in_band, offset_from_sdr_center, margin_hz)
        """
        offset = vfo_center - sdr_center
        half_sdr_bandwidth = sdr_sample_rate / 2
        usable_bandwidth = half_sdr_bandwidth * 0.98  # 2% margin for roll-off
        is_in_band = abs(offset) <= usable_bandwidth
        margin_hz = usable_bandwidth - abs(offset)
        return is_in_band, offset, margin_hz

    def _fm_demodulate(self, samples):
        """Demodulate FM using phase differentiation."""
        diff = samples[1:] * np.conj(samples[:-1])
        demodulated = np.angle(diff)

        if self.last_sample is not None:
            first_diff = samples[0] * np.conj(self.last_sample)
            demodulated = np.concatenate(([np.angle(first_diff)], demodulated))
        else:
            demodulated = np.concatenate(([0], demodulated))

        self.last_sample = samples[-1]
        return demodulated

    def _send_status_update(self, status, mode_name=None, info=None):
        """Send status update to UI"""
        # Build decoder configuration info (clear FSK-specific fields)
        config_info = {
            "baudrate": None,  # SSTV doesn't use baudrate
            "deviation_hz": None,  # SSTV doesn't use deviation
            "framing": None,  # SSTV doesn't use framing
            "transmitter": (
                self.cached_vfo_state.get("transmitter_description", "VFO Signal")
                if self.cached_vfo_state
                else "VFO Signal"
            ),
            "transmitter_mode": "SSTV",
            "transmitter_downlink_mhz": (
                round(self.cached_vfo_state.get("center_freq", 0) / 1e6, 3)
                if self.cached_vfo_state
                else None
            ),
            "packets_decoded": None,  # SSTV decodes images, not packets
            "signal_power_dbfs": None,
            "signal_power_avg_dbfs": None,
            "signal_power_max_dbfs": None,
            "signal_power_min_dbfs": None,
            "buffer_samples": None,
        }

        # Merge with any additional info passed in
        if info:
            config_info.update(info)

        msg = {
            "type": "decoder-status",
            "decoder_id": self.decoder_id,
            "status": status.value,
            "mode": mode_name,
            "decoder_type": "sstv",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
            "info": config_info,
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1  # type: ignore[operator]
        except queue.Full:
            logger.warning("Data queue full, dropping status update")

    def _send_stats_update(self):
        """Send statistics update to UI and performance monitor"""
        # Full performance stats for monitoring (thread-safe copy)
        with self.stats_lock:
            perf_stats: Dict[str, Any] = self.stats.copy()
            ingest_sps = perf_stats.get("ingest_samples_per_sec", 0.0)
            ingest_cps = perf_stats.get("ingest_chunks_per_sec", 0.0)

        # UI-friendly stats (include ingest rates so UI can display flow even when sleeping)
        ui_stats = {
            "images_decoded": self.stats.get("images_decoded", 0),
            "audio_sample_rate": self.audio_sample_rate,
            "is_sleeping": getattr(self, "is_sleeping", False),
            # Coerce possibly None values to float before rounding/dividing for mypy safety
            "ingest_samples_per_sec": round(float(ingest_sps or 0.0), 1),
            "ingest_chunks_per_sec": round(float(ingest_cps or 0.0), 2),
            "ingest_kSps": round(float(ingest_sps or 0.0) / 1e3, 2),
        }

        # Add sleeping state to performance stats
        perf_stats["is_sleeping"] = getattr(self, "is_sleeping", False)

        # Compute authoritative 1 Hz rates at the decoder side (no smoothing)
        # Initialize prev holders on first use
        if not hasattr(self, "_rates_prev_ts"):
            self._rates_prev_ts = None
            self._rates_prev_counters = {
                "iq_chunks_in": 0,
                # SSTVDecoder tracks iq_samples_in
                "samples_in": 0,
                "data_messages_out": 0,
            }

        now_ts = time.time()
        prev_ts = self._rates_prev_ts
        dt: float | None
        if prev_ts is None:
            dt = None
        else:
            dt = now_ts - float(prev_ts)
        try:
            curr_iq_chunks = int(perf_stats.get("iq_chunks_in", 0) or 0)
            curr_samples = int(
                perf_stats.get("samples_in", 0) or perf_stats.get("iq_samples_in", 0) or 0
            )
            curr_msgs_out = int(perf_stats.get("data_messages_out", 0) or 0)

            if dt and dt > 0:
                rates = {
                    "iq_chunks_in_per_sec": (
                        curr_iq_chunks - self._rates_prev_counters.get("iq_chunks_in", 0)
                    )
                    / dt,
                    "samples_in_per_sec": (
                        curr_samples - self._rates_prev_counters.get("samples_in", 0)
                    )
                    / dt,
                    "data_messages_out_per_sec": (
                        curr_msgs_out - self._rates_prev_counters.get("data_messages_out", 0)
                    )
                    / dt,
                }
            else:
                rates = {
                    "iq_chunks_in_per_sec": 0.0,
                    "samples_in_per_sec": 0.0,
                    "data_messages_out_per_sec": 0.0,
                }
        except Exception:
            rates = {
                "iq_chunks_in_per_sec": 0.0,
                "samples_in_per_sec": 0.0,
                "data_messages_out_per_sec": 0.0,
            }

        # Mirror rates into perf_stats for persistence/consumers
        perf_stats["rates"] = rates

        # Update previous snapshot for next tick
        self._rates_prev_ts = now_ts
        self._rates_prev_counters = {
            "iq_chunks_in": int(perf_stats.get("iq_chunks_in", 0) or 0),
            "samples_in": int(
                perf_stats.get("samples_in", 0) or perf_stats.get("iq_samples_in", 0) or 0
            ),
            "data_messages_out": int(perf_stats.get("data_messages_out", 0) or 0),
        }

        msg = {
            "type": "decoder-stats",
            "decoder_type": "sstv",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
            "stats": ui_stats,  # UI-friendly stats
            "perf_stats": perf_stats,  # Full performance stats for PerformanceMonitor
            "rates": rates,  # Authoritative rates computed at decoder side
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1  # type: ignore[operator]
        except queue.Full:
            pass

    # ========== SSTV Decode Methods (from original sstvdecoder.py) ==========

    def _barycentric_peak_interp(self, bins, x):
        """Interpolate between frequency bins"""
        y1 = bins[x] if x <= 0 else bins[x - 1]
        y3 = bins[x] if x + 1 >= len(bins) else bins[x + 1]
        denom = y3 + bins[x] + y1
        if denom == 0:
            return 0
        return (y3 - y1) / denom + x

    def _peak_fft_freq(self, data):
        """Find peak frequency using FFT"""
        windowed_data = data * hann(len(data))
        fft = np.abs(np.fft.rfft(windowed_data))
        x = np.argmax(fft)
        peak = self._barycentric_peak_interp(fft, x)
        return peak * self.audio_sample_rate / len(windowed_data)

    def _find_header(self):
        """Find SSTV calibration header"""
        header_size = round(HDR_SIZE * self.audio_sample_rate)
        window_size = round(HDR_WINDOW_SIZE * self.audio_sample_rate)

        leader_1_search = window_size
        break_sample = round(BREAK_OFFSET * self.audio_sample_rate)
        break_search = break_sample + window_size
        leader_2_sample = round(LEADER_OFFSET * self.audio_sample_rate)
        leader_2_search = leader_2_sample + window_size
        vis_start_sample = round(VIS_START_OFFSET * self.audio_sample_rate)
        vis_start_search = vis_start_sample + window_size

        jump_size = round(0.002 * self.audio_sample_rate)

        for current_sample in range(0, len(self.audio_buffer) - header_size, jump_size):
            search_end = current_sample + header_size
            search_area = self.audio_buffer[current_sample:search_end]

            leader_1_area = search_area[0:leader_1_search]
            break_area = search_area[break_sample:break_search]
            leader_2_area = search_area[leader_2_sample:leader_2_search]
            vis_start_area = search_area[vis_start_sample:vis_start_search]

            if (
                abs(self._peak_fft_freq(leader_1_area) - 1900) < 25
                and abs(self._peak_fft_freq(break_area) - 1200) < 25
                and abs(self._peak_fft_freq(leader_2_area) - 1900) < 25
                and abs(self._peak_fft_freq(vis_start_area) - 1200) < 25
            ):
                return current_sample + header_size
        return None

    def _decode_vis(self, vis_start):
        """Decode VIS code"""
        bit_size = round(VIS_BIT_SIZE * self.audio_sample_rate)
        vis_bits = []
        vis_freqs = []

        for bit_idx in range(8):
            bit_offset = vis_start + bit_idx * bit_size
            section = self.audio_buffer[bit_offset : bit_offset + bit_size]
            freq = self._peak_fft_freq(section)
            vis_freqs.append(freq)
            vis_bits.append(int(freq < 1200))

        parity = sum(vis_bits) % 2 == 0
        if not parity:
            logger.warning(f"VIS parity error, bits: {vis_bits}")

        vis_value = 0
        for bit in vis_bits[6::-1]:
            vis_value = (vis_value << 1) | bit

        for mode in SSTVMode:
            if mode.value["vis_code"] == vis_value:
                mode_spec = mode.value
                logger.info(f"Detected: {mode_spec['name']} (VIS: {vis_value})")
                return mode

        logger.error(f"Unsupported VIS: {vis_value}")
        return None

    def _align_sync(self, align_start, start_of_sync=True):
        """Find sync pulse position"""
        if self.mode is None:
            return None
        sync_window = round(self.mode.value["sync_pulse"] * 1.4 * self.audio_sample_rate)
        align_stop = len(self.audio_buffer) - sync_window

        if align_stop <= align_start:
            return None

        current_sample = align_start
        for current_sample in range(align_start, align_stop):
            section_end = current_sample + sync_window
            search_section = self.audio_buffer[current_sample:section_end]
            if self._peak_fft_freq(search_section) > 1350:
                break

        end_sync = current_sample + (sync_window // 2)

        if start_of_sync:
            return end_sync - round(self.mode.value["sync_pulse"] * self.audio_sample_rate)
        else:
            return end_sync

    def _send_progress_update(self, current_line, total_lines, mode_name):
        """Send decoding progress update to UI"""
        progress = int((current_line / total_lines) * 100)
        msg = {
            "type": "decoder-progress",
            "progress": progress,
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
            "info": {"current_line": current_line, "total_lines": total_lines, "mode": mode_name},
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1  # type: ignore[operator]
        except queue.Full:
            logger.warning("Data queue full, dropping progress update")

    def _decode_image_data(self, image_start):
        """Decode image data"""
        if self.mode is None:
            return None
        mode = self.mode.value
        pixel_time = mode["pixel_time"]
        window_factor = mode["window_factor"]
        centre_window_time = (pixel_time * window_factor) / 2
        pixel_window = round(centre_window_time * 2 * self.audio_sample_rate)

        height = mode["height"]
        width = mode["width"]
        channels = mode["chan_count"]
        chan_sync = mode["chan_sync"]
        color_mode = mode.get("color_mode", "GBR")

        is_robot = color_mode == "YUV"
        uv_width = width // 2 if is_robot else width

        if is_robot:
            image_data = [
                [[0 for i in range(width if j == 0 else uv_width)] for j in range(channels)]
                for k in range(height)
            ]
        else:
            image_data = [
                [[0 for i in range(width)] for j in range(channels)] for k in range(height)
            ]

        seq_start = image_start

        if chan_sync == 2:
            seq_start = self._align_sync(image_start, start_of_sync=False)
            if seq_start is None:
                logger.error("Could not find first sync pulse after VIS code")
                seq_start = image_start

        sync_pulse = mode["sync_pulse"]
        sync_porch = mode["sync_porch"]
        sep_pulse = mode["sep_pulse"]
        scan_time = mode["scan_time"]
        chan_time = sep_pulse + scan_time

        if is_robot:
            half_scan_time = mode.get("half_scan_time", scan_time / 2)
            sep_porch = mode.get("sep_porch", 0.0015)
            chan_offsets = [
                sync_pulse + sync_porch,
                sync_pulse + sync_porch + chan_time + sep_porch,
            ]
            uv_pixel_time = half_scan_time / uv_width
            uv_centre_window_time = (uv_pixel_time * window_factor) / 2
            uv_pixel_window = round(uv_centre_window_time * 2 * self.audio_sample_rate)
        elif chan_sync == 0:
            chan_offsets = [
                sync_pulse + sync_porch,
                sync_pulse + sync_porch + chan_time,
                sync_pulse + sync_porch + 2 * chan_time,
            ]
        else:
            chan_offsets = [
                sync_pulse + sync_porch + chan_time,
                sync_pulse + sync_porch + 2 * chan_time,
                sync_pulse + sync_porch,
            ]

        for line in range(height):
            if line % 5 == 0:
                self._send_progress_update(line, height, mode["name"])

            if chan_sync == 2 and line == 0:
                sync_offset = chan_offsets[chan_sync]
                seq_start -= round((sync_offset + scan_time) * self.audio_sample_rate)

            for chan in range(channels):
                if chan == chan_sync:
                    if line > 0 or chan > 0:
                        seq_start += round(mode["line_time"] * self.audio_sample_rate)

                    seq_start = self._align_sync(seq_start, start_of_sync=True)
                    if seq_start is None:
                        logger.info(f"End of audio at line {line}")
                        return image_data

                chan_width = uv_width if (is_robot and chan == 1) else width
                chan_pixel_time = uv_pixel_time if (is_robot and chan == 1) else pixel_time
                chan_centre_window = (
                    uv_centre_window_time if (is_robot and chan == 1) else centre_window_time
                )
                chan_pixel_window = uv_pixel_window if (is_robot and chan == 1) else pixel_window

                guard_pixels = 0
                if is_robot and chan == 1:
                    guard_time = 0.001
                    guard_pixels = int(round(guard_time / chan_pixel_time))

                for px in range(chan_width):
                    if guard_pixels > 0 and px >= chan_width - guard_pixels:
                        image_data[line][chan][px] = 128
                        continue
                    chan_offset = chan_offsets[chan]
                    px_pos = round(
                        seq_start
                        + (chan_offset + px * chan_pixel_time - chan_centre_window)
                        * self.audio_sample_rate
                    )
                    px_end = px_pos + chan_pixel_window

                    if px_end >= len(self.audio_buffer):
                        logger.info(f"End of audio at line {line}")
                        return image_data

                    pixel_area = self.audio_buffer[px_pos:px_end]
                    freq = self._peak_fft_freq(pixel_area)
                    image_data[line][chan][px] = calc_lum(freq)

        return image_data

    def _draw_image(self, image_data):
        """Render final image"""
        if self.mode is None or image_data is None:
            return None
        mode = self.mode.value
        width = mode["width"]
        height = mode["height"]
        color_mode = mode.get("color_mode", "GBR")
        uv_width = width // 2 if color_mode == "YUV" else width

        image = Image.new("RGB", (width, height))
        pixel_data = image.load()

        for y in range(height):
            for x in range(width):
                if color_mode == "YUV":
                    y_val = image_data[y][0][x]
                    uv_x = x // 2
                    chroma_val = (
                        image_data[y][1][uv_x]
                        if len(image_data[y]) > 1 and uv_x < len(image_data[y][1])
                        else 128
                    )
                    if uv_x >= uv_width - 3:
                        chroma_val = 128

                    if y % 2 == 0:
                        r_y = chroma_val - 128
                        if (
                            y + 1 < height
                            and len(image_data[y + 1]) > 1
                            and uv_x < len(image_data[y + 1][1])
                        ):
                            b_y = image_data[y + 1][1][uv_x] - 128
                        elif (
                            y > 0
                            and len(image_data[y - 1]) > 1
                            and uv_x < len(image_data[y - 1][1])
                        ):
                            b_y = image_data[y - 1][1][uv_x] - 128
                        else:
                            b_y = 0
                    else:
                        b_y = chroma_val - 128
                        if (
                            y > 0
                            and len(image_data[y - 1]) > 1
                            and uv_x < len(image_data[y - 1][1])
                        ):
                            r_y = image_data[y - 1][1][uv_x] - 128
                        elif (
                            y + 1 < height
                            and len(image_data[y + 1]) > 1
                            and uv_x < len(image_data[y + 1][1])
                        ):
                            r_y = image_data[y + 1][1][uv_x] - 128
                        else:
                            r_y = 0

                    # Use BT.601-style YUV->RGB coefficients for better chroma fidelity.
                    v = r_y
                    u = b_y
                    r = int(y_val + 1.402 * v)
                    b = int(y_val + 1.772 * u)
                    g = int(y_val - 0.344136 * u - 0.714136 * v)

                    pixel = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
                else:
                    pixel = (
                        image_data[y][2][x],
                        image_data[y][0][x],
                        image_data[y][1][x],
                    )
                pixel_data[x, y] = pixel

        return image

    def _send_completed_image(self, image, mode_name):
        """Save and send completed image to UI"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"sstv_{mode_name.replace(' ', '_')}_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        image.save(filepath)
        logger.info(f"Saved: {filepath}")

        filesize = os.path.getsize(filepath)
        decode_timestamp = time.time()

        # Build metadata from cached VFO state
        metadata = {
            "image": {
                "filename": filename,
                "filepath": filepath,
                "format": "image/png",
                "width": image.width,
                "height": image.height,
                "mode": mode_name,
                "filesize": filesize,
                "timestamp": decode_timestamp,
                "timestamp_iso": time.strftime(
                    "%Y-%m-%dT%H:%M:%S%z", time.localtime(decode_timestamp)
                ),
            },
            "decoder": {
                "type": "sstv",
                "session_id": self.session_id,
                "mode": mode_name,
            },
            "signal": {
                "frequency_hz": (
                    self.cached_vfo_state.get("center_freq") if self.cached_vfo_state else None
                ),
                "frequency_mhz": (
                    self.cached_vfo_state.get("center_freq") / 1e6
                    if self.cached_vfo_state
                    else None
                ),
                "sample_rate_hz": self.audio_sample_rate,
            },
            "vfo": {
                "id": self.vfo,
                "center_freq_hz": (
                    self.cached_vfo_state.get("center_freq") if self.cached_vfo_state else None
                ),
                "center_freq_mhz": (
                    self.cached_vfo_state.get("center_freq") / 1e6
                    if self.cached_vfo_state
                    else None
                ),
                "bandwidth_hz": (
                    self.cached_vfo_state.get("bandwidth") if self.cached_vfo_state else None
                ),
                "bandwidth_khz": (
                    self.cached_vfo_state.get("bandwidth") / 1e3 if self.cached_vfo_state else None
                ),
                "active": self.cached_vfo_state.get("active") if self.cached_vfo_state else None,
            },
            "satellite": self.satellite if self.satellite else None,
            "transmitter": self.transmitter if self.transmitter else None,
        }

        metadata_filename = filename.replace(".png", ".json")
        metadata_filepath = os.path.join(self.output_dir, metadata_filename)
        with open(metadata_filepath, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata: {metadata_filepath}")

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        msg = {
            "type": "decoder-output",
            "decoder_type": "sstv",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": decode_timestamp,
            "output": {
                "format": "image/png",
                "filename": filename,
                "filepath": filepath,
                "metadata_filename": metadata_filename,
                "metadata_filepath": metadata_filepath,
                "image_data": img_base64,
                "mode": mode_name,
                "width": image.width,
                "height": image.height,
                "filesize": filesize,
            },
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1  # type: ignore[operator]
        except queue.Full:
            pass

    def run(self):
        """Main process loop - receives IQ, demodulates FM, decodes SSTV"""
        # Set process title for easier discovery via `ps`/`pgrep`
        if HAS_SETPROCTITLE:
            try:
                setproctitle.setproctitle(f"DynamiX-Labs - SSTV Decoder (VFO {self.vfo})")
            except Exception:
                pass
        logger.info(f"SSTV decoder v2 process started for {self.session_id}")

        # Initialize stats in subprocess
        self.stats = {
            "iq_chunks_in": 0,
            "iq_samples_in": 0,
            "audio_samples_generated": 0,
            "images_decoded": 0,
            "data_messages_out": 0,
            "queue_timeouts": 0,
            "last_activity": None,
            "errors": 0,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "memory_percent": 0.0,
            # Ingest-side flow metrics (updated every stats tick)
            "ingest_samples_per_sec": 0.0,
            "ingest_chunks_per_sec": 0.0,
            # Out-of-band accounting
            "samples_dropped_out_of_band": 0,
        }

        self._send_status_update(DecoderStatus.LISTENING)

        # CPU and memory monitoring
        process = psutil.Process()
        last_cpu_check = time.time()
        cpu_check_interval = 0.5  # Update CPU usage every 0.5 seconds

        # Stats tracking
        last_stats_time = time.time()
        stats_interval = 1.0  # Send stats every 1 second

        # Track ingest rates regardless of decoding state (in-band or out-of-band)
        ingest_window_start = time.time()
        ingest_samples_accum = 0
        ingest_chunks_accum = 0

        # FM demodulator filter states
        decimation_state = None
        audio_filter_state = None
        deemph_state = None

        # SSTV processing state
        processing = False
        next_decode_buffer = np.array([], dtype=np.float32)
        min_buffer_size = int(self.audio_sample_rate * 1.0)

        try:
            while self.running.value == 1:
                # Update CPU and memory usage periodically
                current_time = time.time()
                if current_time - last_cpu_check >= cpu_check_interval:
                    try:
                        cpu_percent = process.cpu_percent()
                        mem_info = process.memory_info()
                        memory_mb = mem_info.rss / (1024 * 1024)
                        memory_percent = process.memory_percent()

                        with self.stats_lock:
                            self.stats["cpu_percent"] = cpu_percent
                            self.stats["memory_mb"] = memory_mb
                            self.stats["memory_percent"] = memory_percent
                        last_cpu_check = current_time
                    except Exception as e:
                        logger.debug(f"Error updating CPU/memory usage: {e}")
                # Per-iteration work; ensure stats tick executes even on `continue`
                try:
                    # Read IQ samples from iq_queue
                    try:
                        iq_message = self.iq_queue.get(timeout=0.1)
                    except queue.Empty:
                        with self.stats_lock:
                            self.stats["queue_timeouts"] += 1  # type: ignore[operator]
                        iq_message = None

                    if iq_message is None:
                        # nothing to process this iteration
                        pass
                    else:
                        with self.stats_lock:
                            self.stats["iq_chunks_in"] += 1  # type: ignore[operator]
                            self.stats["last_activity"] = time.time()

                        # Extract IQ samples and metadata
                        samples = iq_message.get("samples")
                        sdr_center = iq_message.get(
                            "logical_center_freq_hz", iq_message.get("center_freq")
                        )
                        sdr_rate = iq_message.get("sample_rate")

                        if samples is None or len(samples) == 0:
                            continue

                        with self.stats_lock:
                            self.stats["iq_samples_in"] += len(samples)  # type: ignore[operator]

                        # Update ingest accumulators (count what we pull, even if we skip processing)
                        ingest_samples_accum += len(samples)
                        ingest_chunks_accum += 1

                        # Get VFO parameters from IQ message
                        vfo_states = iq_message.get("vfo_states", {})
                        vfo_state_dict = vfo_states.get(self.vfo)

                        if not vfo_state_dict or not vfo_state_dict.get("active", False):
                            continue  # VFO not active

                        # Cache VFO state for metadata
                        self.cached_vfo_state = vfo_state_dict

                        vfo_center = vfo_state_dict.get("center_freq", 0)
                        vfo_bandwidth = vfo_state_dict.get("bandwidth", 12500)  # 12.5kHz for SSTV

                        # Validate VFO center is within SDR bandwidth
                        is_in_band, vfo_offset, margin = self._is_vfo_in_sdr_bandwidth(
                            vfo_center, sdr_center, sdr_rate
                        )

                        if not is_in_band:
                            # VFO is outside SDR bandwidth - enter sleeping state
                            with self.stats_lock:
                                # Safely increment (mypy-safe in case initial value is None)
                                current_dropped = int(
                                    (self.stats.get("samples_dropped_out_of_band", 0) or 0)
                                )
                                self.stats["samples_dropped_out_of_band"] = current_dropped + len(
                                    samples
                                )

                            if not self.is_sleeping:
                                self.is_sleeping = True
                                sdr_bw_mhz = sdr_rate / 1e6
                                self.sleep_reason = (
                                    f"VFO out of SDR bandwidth: VFO={vfo_center/1e6:.3f}MHz, "
                                    f"SDR={sdr_center/1e6:.3f}MHz±{sdr_bw_mhz/2:.2f}MHz, "
                                    f"offset={vfo_offset/1e3:.1f}kHz, exceeded by {abs(margin)/1e3:.1f}kHz"
                                )
                                logger.warning(self.sleep_reason)
                                self._send_status_update(
                                    DecoderStatus.SLEEPING,
                                    mode_name=None,
                                    info={
                                        "reason": "vfo_out_of_sdr_bandwidth",
                                        "vfo_center_mhz": round(vfo_center / 1e6, 3),
                                        "sdr_center_mhz": round(sdr_center / 1e6, 3),
                                        "sdr_bandwidth_mhz": round(sdr_rate / 1e6, 2),
                                        "vfo_offset_khz": round(vfo_offset / 1e3, 1),
                                        "exceeded_by_khz": round(abs(margin) / 1e3, 1),
                                        "samples_dropped": self.stats[
                                            "samples_dropped_out_of_band"
                                        ],
                                    },
                                )
                            continue  # Skip DSP for this chunk

                        # If we were sleeping and now back in band, resume
                        if self.is_sleeping:
                            self.is_sleeping = False
                            logger.info(
                                f"VFO back in SDR bandwidth, resuming: VFO={vfo_center/1e6:.3f}MHz, "
                                f"SDR={sdr_center/1e6:.3f}MHz, offset={vfo_offset/1e3:.1f}kHz"
                            )
                            # For SSTV, LISTENING is the idle state
                            self._send_status_update(
                                DecoderStatus.LISTENING,
                                mode_name=None,
                                info={
                                    "resumed_from_sleep": True,
                                    "vfo_center_mhz": round(vfo_center / 1e6, 3),
                                    "sdr_center_mhz": round(sdr_center / 1e6, 3),
                                },
                            )

                        # Initialize on first message
                        if self.sdr_sample_rate is None:
                            self.sdr_sample_rate = sdr_rate

                            # Design filters
                            stages, total_decimation = self._design_decimation_filter(
                                sdr_rate, vfo_bandwidth
                            )
                            self.decimation_filter = (stages, total_decimation)

                            intermediate_rate = sdr_rate / total_decimation
                            self.audio_filter = self._design_audio_filter(
                                intermediate_rate, vfo_bandwidth
                            )
                            self.deemphasis_filter = self._design_deemphasis_filter(
                                intermediate_rate
                            )

                            # Initialize filter states
                            initial_value = samples[0] if len(samples) > 0 else 0
                            decimation_state = []
                            for (b, a), _ in stages:
                                state = signal.lfilter_zi(b, a) * initial_value
                                decimation_state.append(state)

                            audio_filter_state = signal.lfilter_zi(self.audio_filter, 1) * 0
                            b_deemph, a_deemph = self.deemphasis_filter
                            deemph_state = signal.lfilter_zi(b_deemph, a_deemph) * 0

                            logger.info(
                                f"SSTV decoder initialized: SDR={sdr_rate / 1e6:.2f}MS/s, "
                                f"VFO={vfo_center / 1e6:.3f}MHz, BW={vfo_bandwidth / 1e3:.0f}kHz, "
                                f"decimation={total_decimation}, intermediate={intermediate_rate / 1e3:.1f}kHz"
                            )

                        # Step 1: Frequency translation
                        offset_freq = vfo_center - sdr_center
                        translated = self._frequency_translate(samples, offset_freq, sdr_rate)

                        # Step 2: Multi-stage decimation
                        stages, total_decimation = self.decimation_filter  # type: ignore[misc]
                        decimated = translated
                        for stage_idx, ((b, a), stage_decimation) in enumerate(stages):
                            if decimation_state is None or stage_idx >= len(decimation_state):
                                if decimation_state is None:
                                    decimation_state = []
                                decimation_state.append(signal.lfilter_zi(b, a) * decimated[0])

                            filtered, decimation_state[stage_idx] = signal.lfilter(
                                b, a, decimated, zi=decimation_state[stage_idx]
                            )
                            decimated = filtered[::stage_decimation]

                        intermediate_rate = sdr_rate / total_decimation

                        # Step 3: FM demodulation
                        demodulated = self._fm_demodulate(decimated)

                        # Step 4: Audio filtering
                        if audio_filter_state is None:
                            audio_filter_state = (
                                signal.lfilter_zi(self.audio_filter, 1) * demodulated[0]
                            )
                        audio_filtered, audio_filter_state = signal.lfilter(
                            self.audio_filter, 1, demodulated, zi=audio_filter_state
                        )

                        # Step 5: De-emphasis
                        b, a = self.deemphasis_filter  # type: ignore[misc]
                        if deemph_state is None:
                            deemph_state = signal.lfilter_zi(b, a) * audio_filtered[0]
                        deemphasized, deemph_state = signal.lfilter(
                            b, a, audio_filtered, zi=deemph_state
                        )

                        # Step 6: Resample to audio rate (44.1 kHz)
                        num_output_samples = int(
                            len(deemphasized) * self.audio_sample_rate / intermediate_rate
                        )
                        if num_output_samples > 0:
                            audio = signal.resample(deemphasized, num_output_samples)
                            audio = audio.astype(np.float32)

                            with self.stats_lock:
                                self.stats["audio_samples_generated"] += len(audio)  # type: ignore[operator]

                            # Step 7: SSTV processing
                            if processing:
                                next_decode_buffer = np.concatenate([next_decode_buffer, audio])
                                max_next_buffer = int(self.audio_sample_rate * 5.0)
                                if len(next_decode_buffer) > max_next_buffer:
                                    next_decode_buffer = next_decode_buffer[-max_next_buffer:]
                            else:
                                self.audio_buffer = np.concatenate([self.audio_buffer, audio])
                finally:
                    # Time-based stats tick (every ~1s), compute ingest rates regardless of processing state
                    current_time = time.time()
                    if current_time - last_stats_time >= stats_interval:
                        dt = current_time - ingest_window_start
                        if dt > 0:
                            ingest_sps = ingest_samples_accum / dt
                            ingest_cps = ingest_chunks_accum / dt
                        else:
                            ingest_sps = 0.0
                            ingest_cps = 0.0

                        with self.stats_lock:
                            self.stats["ingest_samples_per_sec"] = ingest_sps
                            self.stats["ingest_chunks_per_sec"] = ingest_cps

                        # Reset window
                        ingest_window_start = current_time
                        ingest_samples_accum = 0
                        ingest_chunks_accum = 0

                        self._send_stats_update()
                        last_stats_time = current_time

                # SSTV decode logic
                if len(self.audio_buffer) < min_buffer_size:
                    continue

                if self.mode is None:
                    header_end = self._find_header()
                    if header_end is None:
                        max_buffer = int(self.audio_sample_rate * 2.0)
                        if len(self.audio_buffer) > max_buffer:
                            self.audio_buffer = self.audio_buffer[-max_buffer:]
                        continue

                    vis_end = header_end + round(VIS_BIT_SIZE * 9 * self.audio_sample_rate)
                    if vis_end > len(self.audio_buffer):
                        continue

                    logger.info("Found SSTV header, decoding VIS...")
                    self.mode = self._decode_vis(header_end)
                    if self.mode is None:
                        self.audio_buffer = self.audio_buffer[vis_end:]
                        continue

                    self._send_status_update(DecoderStatus.CAPTURING, self.mode.value["name"])
                    mode_spec = self.mode.value
                    self._send_progress_update(0, mode_spec["height"], mode_spec["name"])

                    self.decode_start_pos = vis_end
                    self.header_found_time = time.time()

                # Mode detected, wait for enough audio to decode image
                if self.mode is not None:
                    mode_spec = self.mode.value

                    image_duration = mode_spec["height"] * mode_spec["sync_pulse"]
                    image_duration += (
                        mode_spec["height"]
                        * mode_spec["chan_count"]
                        * (mode_spec["sep_pulse"] + mode_spec["scan_time"])
                    )
                    required_samples = round((image_duration + 5.0) * self.audio_sample_rate)

                    if len(self.audio_buffer) - self.decode_start_pos < required_samples:
                        if time.time() - self.header_found_time > image_duration + 10.0:
                            logger.warning("Timeout waiting for full image data, decoding partial")
                        else:
                            continue

                    self._send_status_update(DecoderStatus.PROCESSING, mode_spec["name"])
                    processing = True

                    logger.info(f"Starting image decode, buffer: {len(self.audio_buffer)} samples")
                    image_data = self._decode_image_data(self.decode_start_pos)
                    image = self._draw_image(image_data)

                    self._send_progress_update(
                        mode_spec["height"], mode_spec["height"], mode_spec["name"]
                    )
                    self._send_completed_image(image, mode_spec["name"])

                    with self.stats_lock:
                        self.stats["images_decoded"] += 1  # type: ignore[operator]

                    self.mode = None
                    self.audio_buffer = next_decode_buffer
                    next_decode_buffer = np.array([], dtype=np.float32)
                    processing = False
                    logger.info(
                        f"Finished processing, starting next decode with {len(self.audio_buffer)} buffered samples"
                    )
                    self._send_status_update(DecoderStatus.LISTENING)

        except Exception as e:
            logger.error(f"SSTV decoder error: {e}")
            logger.exception(e)
            with self.stats_lock:
                self.stats["errors"] += 1  # type: ignore[operator]
            self._send_status_update(DecoderStatus.ERROR)

        logger.info(f"SSTV decoder v2 process stopped for {self.session_id}")

        # Send final status with restart flag if applicable (parity with FSK decoder)
        try:
            final_status = "restart_requested" if self.should_restart() else "closed"
            msg = {
                "type": "decoder-status",
                "status": final_status,
                "decoder_type": "sstv",
                "decoder_id": self.decoder_id,
                "session_id": self.session_id,
                "vfo": self.vfo,
                "timestamp": time.time(),
                "shm_segments": self.get_shm_segment_count(),
                "restart_requested": self.should_restart(),
            }
            self.data_queue.put(msg, block=False)
        except queue.Full:
            pass
