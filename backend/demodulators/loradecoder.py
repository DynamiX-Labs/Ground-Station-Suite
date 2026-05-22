# Ground Station - LoRa Decoder using GNU Radio gr-lora_sdr
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
# LoRa decoder using GNU Radio gr-lora_sdr blocks for proper LoRa PHY decoding.
# This decoder receives raw IQ samples directly from the SDR process (via iq_queue).

import logging
import os
import queue
import threading
import time
from enum import Enum
from types import SimpleNamespace
from typing import Any, Dict

import numpy as np
import pmt  # noqa: F401
import psutil
import setproctitle

# Configure GNU Radio to use mmap-based buffers instead of shmget
# This prevents shared memory segment exhaustion
os.environ.setdefault("GR_BUFFER_TYPE", "vmcirc_mmap_tmpfile")

from gnuradio import blocks, gr, lora_sdr  # noqa: E402,F401
from scipy import signal  # noqa: E402

from demodulators.basedecoderprocess import BaseDecoderProcess  # noqa: E402
from telemetry.parser import TelemetryParser  # noqa: E402

logger = logging.getLogger("loradecoder")


class DecoderStatus(Enum):
    """Decoder status values."""

    IDLE = "idle"
    LISTENING = "listening"
    DETECTING = "detecting"
    DECODING = "decoding"
    COMPLETED = "completed"
    ERROR = "error"


class LoRaMessageSink(gr.sync_block):
    """Custom GNU Radio sink block to receive decoded LoRa messages"""

    def __init__(
        self,
        callback,
        shm_monitor_interval=10,  # Check SHM every 60 seconds
        shm_restart_threshold=1000,  # Restart when segments exceed this
    ):
        gr.sync_block.__init__(self, name="lora_message_sink", in_sig=None, out_sig=None)
        self.callback = callback
        self.message_port_register_in(gr.pmt.intern("in"))
        self.set_msg_handler(gr.pmt.intern("in"), self.handle_msg)

    def handle_msg(self, msg):
        """Handle incoming LoRa message"""
        logger.debug("LoRa decoder disabled; ignoring message.")
        return


class LoRaFlowgraph(gr.top_block):
    """GNU Radio flowgraph for LoRa decoding using gr-lora_sdr blocks with batch processing"""

    def __init__(
        self,
        samples,
        sample_rate,
        center_freq,
        callback,
        sf=7,
        bw=125000,
        cr=1,
        has_crc=True,
        impl_head=False,
        sync_word=None,
        preamble_len=8,
        fldro=False,
    ):
        """
        Initialize LoRa decoder flowgraph for batch processing

        Args:
            samples: Complex sample array to process (numpy array)
            sample_rate: Input sample rate (Hz)
            center_freq: Center frequency (Hz)
            callback: Function to call when packet is decoded
            sf: Spreading factor (7-12)
            bw: Bandwidth (125000, 250000, or 500000)
            cr: Coding rate (1-4, corresponding to 4/5 through 4/8)
            has_crc: Whether packets have CRC
            impl_head: Implicit header mode
            preamble_len: Preamble length (default: 8)
            fldro: Low Data Rate Optimization (default: False)
        """

        super().__init__("LoRa Decoder")
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.callback = callback
        self.num_samples = len(samples) if samples is not None else 0

    def process_batch_async(self):
        """
        Process the batch of samples asynchronously in a background thread.
        Returns immediately, allowing the main loop to continue consuming from queue.
        """

        def _process():
            return

        # Start processing in background thread
        thread = threading.Thread(target=_process, daemon=True)
        thread.start()
        return thread

    def _on_packet_decoded(self, payload):
        """Called when a LoRa packet is successfully decoded"""
        if self.callback:
            self.callback(payload)


class LoRaDecoder(BaseDecoderProcess):
    """Real-time LoRa decoder using GNU Radio gr-lora_sdr"""

    def __init__(
        self,
        iq_queue,
        data_queue,
        session_id,
        config,  # Pre-resolved DecoderConfig from DecoderConfigService (contains all params + metadata)
        output_dir="data/decoded",
        vfo=None,
        shm_monitor_interval=10,  # Check SHM every 60 seconds
        shm_restart_threshold=1000,  # Restart when segments exceed this
    ):

        # Initialize base process (handles multiprocessing setup)
        super().__init__(
            iq_queue=iq_queue,
            data_queue=data_queue,
            session_id=session_id,
            config=config,
            output_dir=output_dir,
            vfo=vfo,
            shm_monitor_interval=shm_monitor_interval,
            shm_restart_threshold=shm_restart_threshold,
        )

        # LoRa-specific attributes
        self.sample_rate = None  # VFO bandwidth sample rate (after decimation)
        self.sdr_sample_rate = None  # Full SDR sample rate
        self.sdr_center_freq = None  # SDR center frequency
        self.decimation_filter = None  # Filter for decimation

        # Signal power measurement (from BaseDecoder)
        self.power_measurements = []
        self.max_power_history = 100
        self.current_power_dbfs = None

        logger.debug(
            f"LoRaDecoder initialized: packet_count=0, SHM threshold={shm_restart_threshold}"
        )

        # Extract LoRa parameters from config with standard defaults for testing
        self.sf = config.sf if config.sf is not None else 7  # Default: SF7
        self.bw = config.bw if config.bw is not None else 125000  # Default: 125 kHz
        self.cr = config.cr if config.cr is not None else 1  # Default: CR 4/5
        # sync_word: Default to match TX example (converts to network ID)
        self.sync_word = config.sync_word if config.sync_word is not None else [8, 16]
        # TinyGS compatibility parameters
        self.preamble_len = (
            config.preamble_len if config.preamble_len is not None else 8
        )  # Default: 8
        self.fldro = config.fldro if config.fldro is not None else False  # Default: False

        # Cached VFO state (populated from IQ messages)
        self.cached_vfo_state = None

        # Track when we complete a decode to reset status on next churn
        self.just_completed_decode = False

        # Track background processing thread
        self.processing_thread = None

        # Authoritative rate computation (parity with FSK/BPSK)
        self._rates_prev_ts = None
        self._rates_prev_counters = {
            "iq_chunks_in": 0,
            "samples_in": 0,
            "data_messages_out": 0,
        }

        # BaseDecoder required metadata attributes
        self.baudrate = config.baudrate  # Not really used for LoRa, but required by BaseDecoder
        self.framing = "lora"  # LoRa uses its own framing (preamble + header + payload + CRC)
        self.config_source = config.config_source
        self.satellite = config.satellite or {}
        self.transmitter = config.transmitter or {}
        self.norad_id = self.satellite.get("norad_id")
        self.satellite_name = self.satellite.get("name", "")
        self.transmitter_description = self.transmitter.get("description", "")
        self.transmitter_mode = (config.transmitter or {}).get("mode") or "LoRa"
        self.transmitter_downlink_freq = self.transmitter.get("downlink_low")

        # Log debug if downlink frequency not available (not a warning - expected for manual VFO mode)
        if not self.transmitter_downlink_freq:
            logger.debug("Transmitter downlink frequency not available in config (manual VFO mode)")
            logger.debug(f"Config metadata: {config.to_dict()}")

        # Build smart parameter summary - only show non-None optional params
        param_parts = []
        if self.sf is not None:
            param_parts.append(f"SF{self.sf}")
        else:
            param_parts.append("SF=auto")

        if self.bw is not None:
            param_parts.append(f"BW{self.bw/1000:.0f}kHz")
        else:
            param_parts.append("BW=auto")

        if self.cr is not None:
            param_parts.append(f"CR4/{self.cr+4}")
        else:
            param_parts.append("CR=auto")

        if self.sync_word:
            if isinstance(self.sync_word, list):
                sync_hex = "[" + ",".join(f"0x{b:02X}" for b in self.sync_word) + "]"
            else:
                sync_hex = f"0x{self.sync_word:X}"
            param_parts.append(f"sync={sync_hex}")

        params_str = ", ".join(param_parts)

        # Build satellite info (compact format)
        sat_info = f"{self.satellite_name}" if self.satellite_name else "Unknown"
        if self.norad_id:
            sat_info += f" (NORAD {self.norad_id})"

        # Build transmitter info (compact format)
        tx_info = (
            f"TX: {self.transmitter_description}" if self.transmitter_description else "TX: Unknown"
        )
        if self.transmitter_downlink_freq:
            tx_info += f" @ {self.transmitter_downlink_freq/1e6:.3f}MHz"

        # Single consolidated initialization log with all relevant parameters
        logger.info(
            f"LoRa decoder initialized: session={session_id}, VFO {vfo} | {sat_info} | {tx_info} | {params_str} | "
            f"src: {self.config_source}"
        )

        os.makedirs(self.output_dir, exist_ok=True)

        # GNU Radio flowgraph (will be initialized when we know sample rate)
        self.flowgraph = None

    def _get_decoder_type_for_init(self) -> str:
        """Return decoder type for process naming."""
        return "LoRa"

    def _frequency_translate(self, samples, offset_freq, sample_rate):
        """Translate frequency by offset (shift signal in frequency domain)."""
        if offset_freq == 0:
            return samples

        # Generate complex exponential for frequency shift
        t = np.arange(len(samples)) / sample_rate
        shift = np.exp(-2j * np.pi * offset_freq * t)
        return samples * shift

    def _design_decimation_filter(self, decimation_factor, bandwidth, sample_rate):
        """Design low-pass filter for decimation."""
        # Cutoff at bandwidth/2 (Nyquist for target bandwidth)
        cutoff = bandwidth / 2
        # Transition band: 10% of bandwidth
        transition = bandwidth * 0.1
        # Design FIR filter
        numtaps = int(sample_rate / transition) | 1  # Ensure odd
        if numtaps > 1001:  # Limit filter length
            numtaps = 1001
        return signal.firwin(numtaps, cutoff, fs=sample_rate)

    def _decimate_iq(self, samples, decimation_factor):
        """Decimate IQ samples with filtering."""
        if decimation_factor == 1:
            return samples

        # Apply low-pass filter
        filtered = signal.lfilter(self.decimation_filter, 1, samples)
        # Decimate
        return filtered[::decimation_factor]

    def _is_vfo_in_sdr_bandwidth(self, vfo_center, sdr_center, sdr_sample_rate):
        """
        Check if VFO center frequency is within SDR bandwidth.

        Returns:
            tuple: (is_in_band, offset_from_sdr_center, margin_hz)
        """
        offset = vfo_center - sdr_center
        half_sdr_bandwidth = sdr_sample_rate / 2

        # Add small margin (2%) for edge effects and filter roll-off
        usable_bandwidth = half_sdr_bandwidth * 0.98

        is_in_band = abs(offset) <= usable_bandwidth
        margin_hz = usable_bandwidth - abs(offset)

        return is_in_band, offset, margin_hz

    def _on_packet_decoded(self, payload):
        """
        Callback when GNU Radio decodes a LoRa packet.
        Delegates to BaseDecoder's implementation for comprehensive metadata handling.
        """
        # Call BaseDecoder's _on_packet_decoded which handles:
        # - Packet validation
        # - Counting and stats
        # - Telemetry parsing
        # - File saving (binary + JSON metadata)
        # - UI message construction and sending
        # Note: BaseDecoder will log "LORA transmission decoded" which we suppress by not duplicating here
        BaseDecoderProcess._on_packet_decoded(self, payload, callsigns=None)

        # Send status update (LoRa-specific) - no log needed, already logged above
        self._send_status_update(
            DecoderStatus.COMPLETED,
            {"packet_number": self.packet_count, "packet_length": len(payload)},
        )

        # Mark that we just completed a decode so we can reset to LISTENING on next churn
        self.just_completed_decode = True

    def _send_status_update(self, status, info=None):
        """Send status update to UI"""
        # Build decoder configuration info (like other decoders)
        config_info = {
            "spreading_factor": self.sf,
            "bandwidth_hz": self.bw,
            "bandwidth_khz": self.bw / 1000 if self.bw else None,
            "coding_rate": f"4/{self.cr + 4}" if self.cr is not None else None,
            "sync_word": self.sync_word,
            "preamble_len": self.preamble_len,
            "fldro": self.fldro,
            "framing": self.framing,
            "transmitter": self.transmitter_description,
            "transmitter_mode": self.transmitter_mode,
            "transmitter_downlink_mhz": (
                round(self.transmitter_downlink_freq / 1e6, 3)
                if self.transmitter_downlink_freq
                else None
            ),
        }

        # Add power measurements if available
        config_info.update(self._get_power_statistics())

        # Merge with any additional info passed in
        if info:
            config_info.update(info)

        msg = {
            "type": "decoder-status",
            "status": status.value,
            "decoder_type": "lora",
            "decoder_id": self.decoder_id,
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

    def _send_stats_update(self):
        """Send statistics update to UI and performance monitor"""
        # Full performance stats for monitoring (thread-safe copy)
        with self.stats_lock:
            perf_stats = self.stats.copy()

        # Compute authoritative 1 Hz rates at the decoder side
        now_ts = time.time()
        prev_ts = self._rates_prev_ts
        dt = now_ts - prev_ts if prev_ts is not None else None
        try:
            curr_iq_chunks = perf_stats.get("iq_chunks_in", 0)
            curr_samples = (
                perf_stats.get("samples_in", 0) or perf_stats.get("iq_samples_in", 0) or 0
            )
            curr_msgs_out = perf_stats.get("data_messages_out", 0)

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

        # Mirror rates into perf_stats for PerformanceMonitor
        perf_stats["rates"] = rates

        # Update previous snapshot
        self._rates_prev_ts = now_ts
        self._rates_prev_counters = {
            "iq_chunks_in": perf_stats.get("iq_chunks_in", 0),
            "samples_in": perf_stats.get("samples_in", 0)
            or perf_stats.get("iq_samples_in", 0)
            or 0,
            "data_messages_out": perf_stats.get("data_messages_out", 0),
        }

        # UI-friendly stats (add ingest rates and power statistics)
        ui_stats = {
            "packets_decoded": self.packet_count,
            "spreading_factor": self.sf,
            "coding_rate": self.cr,
            "bandwidth": self.bw,
            "ingest_samples_per_sec": round(rates.get("samples_in_per_sec", 0.0), 1),
            "ingest_chunks_per_sec": round(rates.get("iq_chunks_in_per_sec", 0.0), 2),
            "ingest_kSps": round((rates.get("samples_in_per_sec", 0.0) / 1e3), 2),
        }
        ui_stats.update(self._get_power_statistics())

        msg = {
            "type": "decoder-stats",
            "decoder_type": "lora",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": now_ts,
            "stats": ui_stats,
            "perf_stats": perf_stats,
            "rates": rates,
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1
        except queue.Full:
            pass

    def run(self):
        """Main thread loop"""
        # Set process name for visibility in system monitoring tools
        setproctitle.setproctitle(f"DynamiX-Labs - LoRa Decoder (VFO {self.vfo})")

        # Initialize components in subprocess (CRITICAL!)
        self.telemetry_parser = TelemetryParser()

        # Initialize stats in subprocess
        self.stats: Dict[str, Any] = {
            "iq_chunks_in": 0,
            "samples_in": 0,
            "samples_dropped_out_of_band": 0,
            "data_messages_out": 0,
            "queue_timeouts": 0,
            "packets_decoded": 0,
            "last_activity": None,
            "errors": 0,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "memory_percent": 0.0,
        }

        self._send_status_update(DecoderStatus.LISTENING)

        chunks_received = 0
        samples_buffer = np.array([], dtype=np.complex64)
        last_stats_time = time.time()  # Track time for periodic stats updates
        # Buffer enough samples for gr-lora_sdr processing
        # frame_sync needs at least 8200 samples, plus margin for packet length
        # For SF7/125kHz, a packet is ~50-150ms, for SF11/250kHz it can be 200-500ms
        process_interval = 3.0  # Process every 3 seconds

        # Flow rate tracking
        last_process_time = time.time()
        # last_process_samples = 0
        buffer_duration = process_interval + 1.0  # Buffer 1s extra for packet boundaries

        # CPU and memory monitoring
        process = psutil.Process()
        last_cpu_check = time.time()
        cpu_check_interval = 0.5  # Update CPU usage every 0.5 seconds

        # Track parameters to avoid unnecessary flowgraph recreation
        current_params = None  # Track (sf, bw, cr) to detect parameter changes

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

                # Read IQ samples from iq_queue
                try:
                    iq_message = self.iq_queue.get(timeout=0.05)  # 50ms timeout

                    # If we just completed a decode, reset status to LISTENING
                    if self.just_completed_decode:
                        self._send_status_update(DecoderStatus.LISTENING)
                        self.just_completed_decode = False

                    # Extract IQ samples and metadata from message
                    samples = iq_message.get("samples")
                    sdr_center = iq_message.get(
                        "logical_center_freq_hz", iq_message.get("center_freq")
                    )
                    sdr_rate = iq_message.get("sample_rate")

                    if samples is None or len(samples) == 0:
                        continue

                    # Get VFO parameters from IQ message (added by IQBroadcaster)
                    vfo_states = iq_message.get("vfo_states", {})
                    vfo_state_dict = vfo_states.get(self.vfo)

                    if not vfo_state_dict or not vfo_state_dict.get("active", False):
                        continue  # VFO not active, skip

                    # Cache VFO state for metadata purposes
                    self.cached_vfo_state = vfo_state_dict

                    vfo_center = vfo_state_dict.get("center_freq", 0)
                    vfo_bandwidth = vfo_state_dict.get("bandwidth", 10000)

                    # Initialize on first message
                    if self.sdr_sample_rate is None:
                        self.sdr_sample_rate = sdr_rate
                        self.sdr_center_freq = sdr_center

                        # Calculate decimation factor for 4x oversampling of LoRa bandwidth
                        # gr-lora_sdr works best with 4x oversampling
                        # Use a reasonable default bandwidth for initial setup if not specified
                        default_bw = self.bw if self.bw is not None else 250000
                        target_sample_rate = default_bw * 4  # 4x oversampling
                        self.decimation_factor = int(self.sdr_sample_rate / target_sample_rate)
                        if self.decimation_factor < 1:
                            self.decimation_factor = 1
                        self.sample_rate = self.sdr_sample_rate / self.decimation_factor

                        # Design decimation filter
                        self.decimation_filter = self._design_decimation_filter(
                            self.decimation_factor, vfo_bandwidth, self.sdr_sample_rate
                        )

                        if self.bw is not None:
                            logger.info(
                                f"LoRa decoder: BW: {self.bw/1e3:.0f}kHz, target rate: {target_sample_rate/1e6:.2f}MS/s (4x oversample), "
                                f"SDR rate: {self.sdr_sample_rate/1e6:.2f} MS/s, VFO BW: {vfo_bandwidth/1e3:.0f} kHz, "
                                f"decimation: {self.decimation_factor}, output rate: {self.sample_rate/1e6:.2f} MS/s, "
                                f"VFO center: {vfo_center/1e6:.3f} MHz, SDR center: {sdr_center/1e6:.3f} MHz"
                            )
                        else:
                            logger.info(
                                f"LoRa decoder: Using default BW {default_bw/1e3:.0f}kHz for initialization, "
                                f"target rate: {target_sample_rate/1e6:.2f}MS/s (4x oversample), "
                                f"SDR rate: {self.sdr_sample_rate/1e6:.2f} MS/s, VFO BW: {vfo_bandwidth/1e3:.0f} kHz, "
                                f"decimation: {self.decimation_factor}, output rate: {self.sample_rate/1e6:.2f} MS/s"
                            )

                        # Calculate buffer sizes
                        buffer_samples = int(self.sample_rate * buffer_duration)
                        process_samples = int(self.sample_rate * process_interval)
                        logger.info(
                            f"Will buffer {buffer_samples} samples ({buffer_duration}s) "
                            f"and process every {process_samples} samples ({process_interval}s)"
                        )

                    # Step 1: Frequency translation to VFO center
                    offset_freq = vfo_center - sdr_center

                    # Optional out-of-band accounting/parity with FSK
                    try:
                        in_band, _, margin_hz = self._is_vfo_in_sdr_bandwidth(
                            vfo_center, sdr_center, sdr_rate
                        )
                    except Exception:
                        in_band = True
                        margin_hz = 0.0

                    if not in_band:
                        # Count these samples and mark as dropped out-of-band, then skip processing
                        with self.stats_lock:
                            self.stats["iq_chunks_in"] += 1
                            self.stats["samples_in"] += len(samples)
                            self.stats["samples_dropped_out_of_band"] += len(samples)
                            self.stats["last_activity"] = time.time()
                        if chunks_received % 50 == 0:
                            logger.info(
                                f"LoRa: VFO out of SDR band by {abs(margin_hz):.0f} Hz, skipping chunk"
                            )
                        chunks_received += 1
                        # Send stats periodically even if skipping
                        current_time = time.time()
                        if current_time - last_stats_time >= 1.0:
                            self._send_stats_update()
                            last_stats_time = current_time
                        continue

                    # Debug: Log frequency translation details every 100 chunks
                    if chunks_received % 100 == 0:
                        logger.debug(
                            f"Frequency translation: SDR={sdr_center/1e6:.6f}MHz, "
                            f"VFO={vfo_center/1e6:.6f}MHz, offset={offset_freq/1e3:.1f}kHz"
                        )

                    translated = self._frequency_translate(
                        samples, offset_freq, self.sdr_sample_rate
                    )

                    # Measure signal power AFTER frequency translation, BEFORE decimation
                    # This gives the most accurate raw signal strength
                    power_dbfs = self._measure_signal_power(translated)
                    self._update_power_measurement(power_dbfs)

                    # Step 2: Decimate using the fixed decimation factor calculated at init
                    # This ensures consistent sample rate that matches what frame_sync expects
                    decimated = self._decimate_iq(translated, self.decimation_factor)

                    # Add to buffer
                    samples_buffer = np.concatenate([samples_buffer, decimated])

                    # Update stats
                    with self.stats_lock:
                        self.stats["iq_chunks_in"] += 1
                        self.stats["samples_in"] += len(samples)
                        self.stats["last_activity"] = time.time()

                    # Process when we have enough samples
                    if len(samples_buffer) >= process_samples:
                        # Calculate flow rate
                        current_time = time.time()
                        time_elapsed = current_time - last_process_time
                        samples_count = len(samples_buffer)
                        flow_rate_sps = samples_count / time_elapsed if time_elapsed > 0 else 0

                        # Log batch processing stats (consistent with FSK/BPSK decoders)
                        # Build comprehensive LoRa parameter string
                        sf_str = f"SF{self.sf}" if self.sf is not None else "SF=auto"
                        bw_str = f"BW{self.bw/1000:.0f}kHz" if self.bw is not None else "BW=auto"
                        cr_str = f"CR4/{self.cr+4}" if self.cr is not None else "CR=auto"

                        # Format sync word for compact display
                        if self.sync_word:
                            if isinstance(self.sync_word, list):
                                sync_str = f"sync=[{','.join(f'{b:02X}' for b in self.sync_word)}]"
                            else:
                                sync_str = f"sync={self.sync_word:02X}"
                        else:
                            sync_str = "sync=auto"

                        ldro_str = "LDRO" if self.fldro else ""
                        extra_params = f"pre={self.preamble_len}, {sync_str}"
                        if ldro_str:
                            extra_params += f", {ldro_str}"

                        logger.info(
                            f"Batch: {len(samples_buffer)} samp ({time_elapsed:.1f}s, {flow_rate_sps/1e3:.1f}kS/s) | "
                            f"LoRa: {sf_str}, {bw_str}, {cr_str}, {extra_params} | "
                            f"VFO: {vfo_center:.0f}Hz, BW={vfo_bandwidth:.0f}Hz | "
                            f"Packets decoded so far: {self.packet_count}"
                        )

                        # Update tracking for next batch
                        last_process_time = current_time
                        # last_process_samples = samples_count

                        # Auto-detection logic: try multiple parameters if not specified
                        # If parameters are locked in (either from config or found), only try those
                        if self.packet_count > 0:
                            # After first successful decode, lock to those params
                            sfs_to_try = [self.sf]
                            crs_to_try = [self.cr]
                            bws_to_try = [self.bw]
                        elif self.sf is not None and self.bw is not None and self.cr is not None:
                            # All params specified in config
                            sfs_to_try = [self.sf]
                            crs_to_try = [self.cr]
                            bws_to_try = [self.bw]
                        else:
                            # Auto-detect: try most common params only (SF7, BW125k, CR1)
                            sfs_to_try = [self.sf] if self.sf is not None else [7]
                            crs_to_try = [self.cr] if self.cr is not None else [1]
                            bws_to_try = [self.bw] if self.bw is not None else [125000]

                            if (
                                chunks_received % 30 == 0
                            ):  # Every 30 batches (~90s), log what we're trying
                                logger.info(
                                    f"Auto-detection: trying SF{sfs_to_try[0]}, BW{bws_to_try[0]/1000:.0f}kHz, CR4/{crs_to_try[0]+4}"
                                )

                        # Determine parameters to use
                        sf = sfs_to_try[0]
                        bw = bws_to_try[0]
                        cr = crs_to_try[0]
                        impl_head = False
                        params = (sf, bw, cr, impl_head)

                        # Log parameter changes
                        if current_params is not None and current_params != params:
                            logger.info(
                                f"Parameters changed to SF{sf}, BW{bw/1000:.0f}kHz, CR4/{cr+4}"
                            )
                        current_params = params

                        # Wait for previous processing to complete before starting new batch
                        if self.processing_thread is not None and self.processing_thread.is_alive():
                            # Previous batch still processing, skip this one to avoid overwhelming
                            logger.debug("Previous batch still processing, skipping new batch")
                        else:
                            # Ensure buffer has enough samples for frame_sync (needs minimum 8200)
                            # Pad with zeros if needed to avoid GNU Radio buffer underrun
                            MIN_FRAME_SYNC_SAMPLES = 8200
                            if len(samples_buffer) < MIN_FRAME_SYNC_SAMPLES:
                                padding_needed = MIN_FRAME_SYNC_SAMPLES - len(samples_buffer)
                                samples_buffer = np.concatenate(
                                    [samples_buffer, np.zeros(padding_needed, dtype=np.complex64)]
                                )
                                logger.debug(
                                    f"Padded buffer with {padding_needed} zeros for frame_sync"
                                )

                            # Create new flowgraph for this batch
                            # Note: samples are already frequency-translated to baseband (0 Hz)
                            flowgraph = LoRaFlowgraph(
                                samples=samples_buffer,
                                sample_rate=self.sample_rate,
                                center_freq=0,  # Already translated to baseband
                                callback=self._on_packet_decoded,
                                sf=sf,
                                bw=bw,
                                cr=cr,
                                sync_word=self.sync_word,
                                impl_head=impl_head,
                                preamble_len=self.preamble_len,
                                fldro=self.fldro,
                            )

                            # Process batch asynchronously - returns immediately
                            self.processing_thread = flowgraph.process_batch_async()

                            # Note: We don't delete flowgraph here - it will be cleaned up when thread finishes
                            # This is safe because each batch creates its own flowgraph instance

                        # If we decoded a packet, lock in the parameters
                        if self.packet_count > 0:
                            if sf != self.sf or cr != self.cr or bw != self.bw:
                                logger.info(
                                    f"Auto-detected working parameters! SF{sf}, BW{bw/1000:.0f}kHz, CR4/{cr+4}, impl_head={impl_head}"
                                )
                                self.sf = sf
                                self.bw = bw
                                self.cr = cr

                        # Keep overlap for packet boundaries
                        # SF7 packet is ~50-150ms, SF11 can be 200-500ms, so 0.5s is safe
                        if self.sample_rate is not None:
                            overlap_samples = int(self.sample_rate * 0.5)  # 500ms overlap
                            if len(samples_buffer) > overlap_samples:
                                samples_buffer = samples_buffer[-overlap_samples:]
                            else:
                                samples_buffer = np.array([], dtype=np.complex64)
                        else:
                            samples_buffer = np.array([], dtype=np.complex64)

                    chunks_received += 1

                    # Monitor shared memory every 100 chunks
                    if chunks_received % 100 == 0:
                        self._monitor_shared_memory()

                except queue.Empty:
                    pass

                # Send stats periodically based on time (every 1 second) regardless of chunk rate
                current_time = time.time()
                if current_time - last_stats_time >= 1.0:
                    self._send_stats_update()
                    last_stats_time = current_time

        except Exception as e:
            logger.error(f"LoRa decoder error: {e}")
            logger.exception(e)
            self._send_status_update(DecoderStatus.ERROR)
        except KeyboardInterrupt:
            pass
        finally:
            # No persistent flowgraph to clean up - each batch creates/destroys its own
            pass

        logger.info(
            f"LoRa decoder process stopped for {self.session_id}. "
            f"Final SHM segments: {self.get_shm_segment_count()}"
        )

        # stop() method removed - now in BaseDecoderProcess

        # Send final status update
        msg = {
            "type": "decoder-status",
            "status": "closed",
            "decoder_type": "lora",
            "decoder_id": self.decoder_id,
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
        }
        try:
            self.data_queue.put(msg, block=False)
        except queue.Full:
            pass

    # BaseDecoder abstract methods implementation

    def _get_decoder_type(self) -> str:
        """Return decoder type string."""
        return "lora"

    def _get_decoder_specific_metadata(self) -> dict:
        """Return LoRa-specific metadata."""
        return {
            "spreading_factor": self.sf,
            "bandwidth_hz": self.bw,
            "bandwidth_khz": self.bw / 1000 if self.bw else None,
            "coding_rate": f"4/{self.cr + 4}" if self.cr is not None else None,
            "sync_word": self.sync_word,
            "preamble_len": self.preamble_len,
            "fldro": self.fldro,
        }

    def _get_filename_params(self) -> str:
        """Return string for filename parameters."""
        sf_str = f"SF{self.sf}" if self.sf else "SFauto"
        bw_str = f"BW{self.bw//1000}kHz" if self.bw else "BWauto"
        return f"{sf_str}_{bw_str}"

    def _get_parameters_string(self) -> str:
        """Return human-readable parameters string for UI."""
        parts = []
        if self.sf is not None:
            parts.append(f"SF{self.sf}")
        else:
            parts.append("SF:auto")

        if self.bw is not None:
            parts.append(f"BW{self.bw//1000}kHz")
        else:
            parts.append("BW:auto")

        if self.cr is not None:
            parts.append(f"CR4/{self.cr+4}")
        else:
            parts.append("CR:auto")

        return ", ".join(parts)

    def _get_demodulator_params_metadata(self) -> dict:
        """Return demodulator parameters metadata."""
        return {
            "spreading_factor": self.sf,
            "bandwidth_hz": self.bw,
            "coding_rate": self.cr,
            "coding_rate_string": f"4/{self.cr + 4}" if self.cr is not None else None,
            "sync_word": self.sync_word,
            "preamble_len": self.preamble_len,
            "fldro": self.fldro,
        }

    def _get_vfo_state(self):
        """Get cached VFO state for metadata purposes."""
        # Create a simple namespace object from cached dict for backward compatibility
        if self.cached_vfo_state:
            return SimpleNamespace(**self.cached_vfo_state)
        return None

    def _get_payload_protocol(self) -> str:
        """Return payload protocol for LoRa."""
        return "lora"

    def _get_decoder_config_metadata(self) -> dict:
        """Return comprehensive LoRa decoder configuration metadata."""
        # Format sync word for display
        if self.sync_word:
            if isinstance(self.sync_word, list):
                sync_word_display = "[" + ",".join(f"0x{b:02X}" for b in self.sync_word) + "]"
            else:
                sync_word_display = f"0x{self.sync_word:02X}"
        else:
            sync_word_display = None

        return {
            "source": self.config_source,
            "framing": "lora",
            "payload_protocol": "lora",
            "modulation": "LoRa",
            "spreading_factor": self.sf,
            "bandwidth_hz": self.bw,
            "bandwidth_khz": self.bw / 1000 if self.bw else None,
            "coding_rate": self.cr,
            "coding_rate_string": f"4/{self.cr + 4}" if self.cr is not None else None,
            "sync_word": self.sync_word,
            "sync_word_display": sync_word_display,
            "preamble_length": self.preamble_len,
            "low_data_rate_optimization": self.fldro,
            "has_crc": True,  # Always true for our configuration
            "implicit_header": False,  # Always false for our configuration
        }
