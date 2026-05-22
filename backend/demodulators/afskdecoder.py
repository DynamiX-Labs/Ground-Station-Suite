# Ground Station - AFSK Decoder using GNU Radio
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
# AFSK decoder implementation based on gr-satellites by Daniel Estevez
# https://github.com/daniestevez/gr-satellites
# Copyright 2019 Daniel Estevez <daniel@destevez.net>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# AFSK (Audio Frequency Shift Keying) decoder for satellite packet radio.
# Uses FM audio as input (chained after FM demodulator).
#
# ARCHITECTURE NOTES:
# ==================
# 1. TWO-STAGE DEMODULATION (FM audio input):
#    - Stage 1: FM demodulation (IQ → audio) - handled by FMDemodulator
#    - Stage 2: AFSK demodulation (audio → data) - handled by this decoder
#    - Audio queue connects the two stages (same as SSTV decoder)
#
# 2. AFSK SIGNAL CHAIN:
#    - FM-demodulated audio input (from FMDemodulator)
#    - Frequency translation (shift af_carrier to baseband)
#    - Low-pass filter (Carson's bandwidth)
#    - FSK demodulation (quadrature demod)
#    - Clock recovery
#    - Binary slicer, NRZI decode, G3RUH descrambler, HDLC deframing
#
# 3. COMMON PARAMETERS:
#    - Baudrate: 1200 bps (Bell 202 APRS), 9600 bps (G3RUH)
#    - AF carrier: 1700 Hz (APRS), 1200 Hz (packet radio)
#    - Deviation: ±500 Hz (1200 baud), ±2400 Hz (9600 baud)
#    - Audio sample rate: 44100 Hz (from FMDemodulator)
#
# 4. TYPICAL USE CASES:
#    - APRS (Automatic Packet Reporting System): 1200 baud Bell 202
#    - VHF/UHF packet radio: 1200/9600 baud AX.25
#    - Amateur radio satellites with FM transponders

import argparse
import gc
import logging
import multiprocessing
import os
import queue
import time
import traceback
from enum import Enum
from typing import Any, Dict

import numpy as np
import psutil

# Add setproctitle import for process naming
try:
    import setproctitle

    HAS_SETPROCTITLE = True
except ImportError:
    HAS_SETPROCTITLE = False

# Configure GNU Radio to use mmap-based buffers instead of shmget
# This prevents shared memory segment exhaustion
os.environ.setdefault("GR_BUFFER_TYPE", "vmcirc_mmap_tmpfile")

from gnuradio import blocks, gr  # noqa: E402
from satellites.components.deframers.ax25_deframer import ax25_deframer  # noqa: E402
from satellites.components.demodulators.afsk_demodulator import afsk_demodulator  # noqa: E402

from demodulators.basedecoderprocess import BaseDecoderProcess  # noqa: E402
from telemetry.parser import TelemetryParser  # noqa: E402
from vfos.state import VFOManager  # noqa: E402

logger = logging.getLogger("afskdecoder")


class DecoderStatus(Enum):
    """Decoder status values."""

    IDLE = "idle"
    LISTENING = "listening"
    DETECTING = "detecting"
    DECODING = "decoding"
    COMPLETED = "completed"
    ERROR = "error"


class AFSKMessageHandler(gr.basic_block):
    """Message handler to receive PDU messages from HDLC deframer"""

    def __init__(
        self,
        callback,
        shm_monitor_interval=10,  # Check SHM every 60 seconds
        shm_restart_threshold=1000,  # Restart when segments exceed this
    ):
        gr.basic_block.__init__(self, name="afsk_message_handler", in_sig=None, out_sig=None)
        self.callback = callback
        self.message_port_register_in(gr.pmt.intern("in"))
        self.set_msg_handler(gr.pmt.intern("in"), self.handle_msg)
        self.packets_decoded = 0

    def handle_msg(self, msg):
        """Handle incoming PDU messages from HDLC deframer"""
        try:
            # Extract packet data from PDU
            if gr.pmt.is_pair(msg):
                packet_data = gr.pmt.to_python(gr.pmt.cdr(msg))
            else:
                packet_data = gr.pmt.to_python(msg)

            # Convert numpy array to bytes
            if isinstance(packet_data, np.ndarray):
                packet_data = bytes(packet_data)

            if isinstance(packet_data, bytes):
                # Parse AX.25 callsigns
                callsigns = None
                try:
                    if len(packet_data) >= 14:
                        dest_call = "".join(
                            chr((packet_data[i] >> 1) & 0x7F) for i in range(6)
                        ).strip()
                        dest_ssid = (packet_data[6] >> 1) & 0x0F
                        src_call = "".join(
                            chr((packet_data[i] >> 1) & 0x7F) for i in range(7, 13)
                        ).strip()
                        src_ssid = (packet_data[13] >> 1) & 0x0F
                        callsigns = {
                            "from": f"{src_call}-{src_ssid}",
                            "to": f"{dest_call}-{dest_ssid}",
                        }
                except Exception as parse_err:
                    logger.debug(f"Could not parse callsigns: {parse_err}")

                # Add HDLC flags for compatibility
                packet_with_flags = bytes([0x7E]) + packet_data + bytes([0x7E])

                if self.callback:
                    self.callback(packet_with_flags, callsigns)
            else:
                logger.warning(f"Unexpected packet data type: {type(packet_data)}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            traceback.print_exc()


class AFSKFlowgraph(gr.top_block):
    """
    AFSK flowgraph using gr-satellites AFSK demodulator components

    Based on gr-satellites afsk_demodulator and ax25_deframer.
    """

    def __init__(
        self,
        sample_rate,
        callback,
        status_callback=None,
        baudrate=1200,
        af_carrier=1700,
        deviation=500,
        use_agc=True,
        dc_block=True,
        clk_bw=0.06,
        clk_limit=0.004,
        batch_interval=5.0,
        framing="ax25",  # 'ax25' (default for AFSK)
    ):
        """
        Initialize AFSK decoder flowgraph using gr-satellites AFSK demodulator

        Args:
            sample_rate: Audio sample rate (Hz) - typically 44100
            callback: Function to call when packet is decoded
            status_callback: Function to call for status updates (status, info)
            baudrate: Symbol rate / baud rate (symbols/sec) - 1200 or 9600 typical
            af_carrier: Audio frequency carrier in Hz (1700 for APRS, 1200 for packet)
            deviation: Deviation in Hz (negative inverts sidebands)
            use_agc: Use automatic gain control
            dc_block: Use DC blocker
            clk_bw: Clock recovery bandwidth (relative to baudrate)
            clk_limit: Clock recovery limit (relative to baudrate)
            batch_interval: Batch processing interval in seconds (default: 5.0)
            framing: Framing protocol - 'ax25' (G3RUH, default for AFSK)
        """
        super().__init__("AFSK Decoder")

        self.sample_rate = sample_rate
        self.baudrate = baudrate
        self.af_carrier = af_carrier
        self.callback = callback
        self.status_callback = status_callback
        self.deviation = deviation
        self.batch_interval = batch_interval
        self.use_agc = use_agc
        self.dc_block = dc_block
        self.clk_bw = clk_bw
        self.clk_limit = clk_limit
        self.framing = framing

        # Accumulate samples in a buffer
        self.sample_buffer = np.array([], dtype=np.float32)
        self.sample_lock = multiprocessing.Lock()
        self.current_mode = "decoding"  # Track current mode

    def process_samples(self, samples):
        """
        Process audio samples through the flowgraph

        Accumulates samples in a buffer and processes them periodically.

        Args:
            samples: numpy array of float32 audio samples
        """
        should_process = False
        buffer_size = 0
        with self.sample_lock:
            self.sample_buffer = np.concatenate([self.sample_buffer, samples])
            buffer_size = len(self.sample_buffer)

            # Process when we have enough samples (batch_interval seconds worth)
            min_process_samples = int(self.sample_rate * self.batch_interval)

            if buffer_size >= min_process_samples:
                should_process = True
            elif self.current_mode != "decoding":
                # Transition back to decoding mode (accumulating samples)
                self.current_mode = "decoding"
                if self.status_callback:
                    self.status_callback(DecoderStatus.DECODING, {"buffer_samples": buffer_size})

        # Process outside the lock so incoming samples don't block
        if should_process:
            # Transition to decoding mode (processing batch)
            with self.sample_lock:
                self.current_mode = "decoding"
            if self.status_callback:
                self.status_callback(DecoderStatus.DECODING, {"buffer_samples": buffer_size})

            self._process_buffer()

    def _process_buffer(self):
        """Process accumulated samples through the flowgraph"""
        # Copy buffer outside the lock to allow incoming samples to continue
        with self.sample_lock:
            if len(self.sample_buffer) == 0:
                return
            samples_to_process = self.sample_buffer.copy()
            # Clear the buffer completely - no tail overlap to avoid duplicate decodes
            self.sample_buffer = np.array([], dtype=np.float32)

        tb = None
        try:
            # Create a NEW flowgraph for each batch to avoid connection conflicts
            # This is necessary because hierarchical blocks can't be easily disconnected

            # Create a temporary top_block
            tb = gr.top_block("AFSK Batch Processor")

            # Create vector source with accumulated samples (float, not complex)
            source = blocks.vector_source_f(samples_to_process.tolist(), repeat=False)

            # Create options namespace for gr-satellites components
            # Note: gr-satellites expects fm_deviation (with underscore), not fm-deviation
            options = argparse.Namespace(
                clk_bw=self.clk_bw,
                clk_limit=self.clk_limit,
                deviation=self.deviation,
                use_agc=self.use_agc,
                disable_dc_block=not self.dc_block,
                fm_deviation=3000,  # Default FM deviation in Hz (only used for IQ input with iq=True)
            )

            # Create AFSK demodulator
            # iq=False because we're feeding real audio samples (already FM demodulated)
            demod = afsk_demodulator(
                baudrate=self.baudrate,
                samp_rate=self.sample_rate,
                iq=False,  # Audio input (real), not IQ
                af_carrier=self.af_carrier,
                deviation=self.deviation,
                dump_path=None,
                options=options,
            )

            # Create AX.25 deframer (AFSK typically uses AX.25)
            deframer = ax25_deframer(g3ruh_scrambler=True, options=options)

            logger.info(
                f"Batch: {len(samples_to_process)} samp ({self.batch_interval}s) | "
                f"AFSK: {self.baudrate}bd, {self.sample_rate:.0f}sps, af_carrier={self.af_carrier}, dev={self.deviation} | "
                f"Frame: AX25(G3RUH)"
            )

            # Create message handler for this batch
            msg_handler = AFSKMessageHandler(self.callback)

            # Build flowgraph
            tb.connect(source, demod, deframer)
            tb.msg_connect((deframer, "out"), (msg_handler, "in"))

            # Run the flowgraph
            tb.start()
            tb.wait()

            # Explicitly stop
            try:
                tb.stop()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error processing buffer: {e}")
            traceback.print_exc()
            # Clear buffer on error to avoid repeated failures
            with self.sample_lock:
                self.sample_buffer = np.array([], dtype=np.float32)
        finally:
            # Explicit cleanup to prevent shared memory leaks
            if "tb" in locals() and tb is not None:
                try:
                    # Ensure flowgraph is stopped
                    tb.stop()
                    tb.wait()
                except Exception:
                    pass

                # Disconnect all blocks
                try:
                    tb.disconnect_all()
                except Exception:
                    pass

                # Delete references to allow garbage collection
                try:
                    del msg_handler
                    del deframer
                    del demod
                    del source
                except Exception:
                    pass

                # Delete the top_block to release resources
                del tb

            # Force garbage collection to clean up GNU Radio objects
            # and release shared memory segments
            gc.collect()

            # Longer delay to allow system to clean up shared memory
            # GNU Radio 3.10+ has issues with rapid flowgraph creation/destruction
            time.sleep(0.1)

    def flush_buffer(self):
        """Process any remaining samples in the buffer"""
        should_process = False
        buffer_size = 0
        with self.sample_lock:
            if len(self.sample_buffer) > 0:
                buffer_size = len(self.sample_buffer)
                should_process = True
        # CRITICAL: Call _process_buffer() OUTSIDE the lock to avoid blocking the entire app.
        # _process_buffer() runs GNU Radio flowgraph synchronously (tb.wait()) and sleeps 100ms,
        # which would freeze all threads trying to acquire sample_lock if called inside the lock.
        if should_process:
            logger.info(f"Flushing {buffer_size} remaining samples from AFSK flowgraph")
            self._process_buffer()


class AFSKDecoder(BaseDecoderProcess):
    """Real-time AFSK decoder using GNU Radio - consumes FM audio"""

    def __init__(
        self,
        audio_queue,
        data_queue,
        session_id,
        config,  # Pre-resolved DecoderConfig from DecoderConfigService (contains all params + metadata)
        output_dir="data/decoded",
        vfo=None,
        batch_interval=5.0,  # Batch processing interval in seconds
        shm_monitor_interval=10,  # Check SHM every 60 seconds
        shm_restart_threshold=1000,  # Restart when segments exceed this
    ):
        # AFSK uses audio_queue, not iq_queue - pass audio_queue as iq_queue for compatibility
        super().__init__(
            iq_queue=audio_queue,  # AFSK uses audio queue instead of IQ queue
            data_queue=data_queue,
            session_id=session_id,
            config=config,
            output_dir=output_dir,
            vfo=vfo,
            shm_monitor_interval=shm_monitor_interval,
            shm_restart_threshold=shm_restart_threshold,
        )
        # Note: audio_queue is stored as self.iq_queue by BaseDecoderProcess
        # We set self.audio_queue as an alias for clarity in AFSK-specific code
        self.audio_queue = self.iq_queue  # Alias to the queue stored by base class
        self.audio_sample_rate = 44100  # Standard audio rate from FMDemodulator
        self.batch_interval = batch_interval

        logger.debug(
            f"AFSKDecoder initialized: packet_count=0, SHM threshold={shm_restart_threshold}"
        )

        # Extract all parameters from resolved config (including metadata)
        self.baudrate = config.baudrate
        self.af_carrier = config.af_carrier
        self.deviation = config.deviation
        self.framing = config.framing
        self.config_source = config.config_source

        # Extract satellite and transmitter metadata from config
        self.satellite = config.satellite or {}
        self.transmitter = config.transmitter or {}

        # Extract commonly used fields for convenience
        self.norad_id = self.satellite.get("norad_id")
        self.satellite_name = self.satellite.get("name") or "Unknown"
        self.transmitter_description = self.transmitter.get("description") or "Unknown"
        self.transmitter_mode = self.transmitter.get("mode") or "AFSK"
        self.transmitter_downlink_freq = self.transmitter.get("downlink_low")

        # Log debug if downlink frequency not available (not a warning - expected for manual VFO mode)
        if not self.transmitter_downlink_freq:
            logger.debug("Transmitter downlink frequency not available in config (manual VFO mode)")
            logger.debug(f"Config metadata: {config.to_dict()}")

        # Build smart parameter summary - only show non-None optional params
        param_parts = [
            f"{self.baudrate}bd",
            f"af_carrier={self.af_carrier}Hz",
            f"dev={self.deviation}Hz",
            f"{self.framing.upper()}",
        ]

        params_str = ", ".join(param_parts)

        # Build satellite info (compact format)
        sat_info = f"{self.satellite_name}"
        if self.norad_id:
            sat_info += f" (NORAD {self.norad_id})"

        # Build transmitter info (compact format)
        tx_info = f"TX: {self.transmitter_description}"
        if self.transmitter_downlink_freq:
            tx_info += f" @ {self.transmitter_downlink_freq/1e6:.3f}MHz"

        # Single consolidated initialization log with all relevant parameters
        logger.info(
            f"AFSK decoder initialized: session={session_id}, VFO {vfo} | {sat_info} | {tx_info} | {params_str} | "
            f"batch={self.batch_interval}s | src: {self.config_source}"
        )

        os.makedirs(self.output_dir, exist_ok=True)

        # GNU Radio flowgraph (will be initialized when we start processing)
        self.flowgraph = None

        # Performance monitoring stats
        self.stats: Dict[str, Any] = {
            "audio_chunks_in": 0,
            "samples_in": 0,
            "data_messages_out": 0,
            "queue_timeouts": 0,
            "packets_decoded": 0,
            "last_activity": None,
            "errors": 0,
        }

    def _get_decoder_type_for_init(self) -> str:
        """Return decoder type for process naming."""
        return "AFSK"

    def _get_vfo_state(self):
        """Get VFO state for this decoder."""
        if self.vfo is not None:
            return self.vfo_manager.get_vfo_state(self.session_id, self.vfo)
        return None

    def _should_accept_packet(self, payload, callsigns):
        """AFSK requires valid callsigns"""
        if not callsigns or not callsigns.get("from") or not callsigns.get("to"):
            logger.debug("Packet rejected: no valid callsigns found")
            return False
        return True

    def _get_decoder_type(self):
        """Return decoder type string"""
        return "afsk"

    def _get_decoder_specific_metadata(self):
        """Return AFSK-specific metadata"""
        return {
            "af_carrier": self.af_carrier,
            "deviation": self.deviation,
            "batch_interval": self.batch_interval,
        }

    def _get_filename_params(self):
        """Return filename parameters"""
        return f"{self.baudrate}baud"

    def _get_parameters_string(self):
        """Return human-readable parameters string"""
        return f"{self.baudrate}baud, {self.af_carrier}Hz carrier, {abs(self.deviation)}Hz dev"

    def _get_demodulator_params_metadata(self):
        """Return AFSK demodulator parameters"""
        return {
            "af_carrier_hz": self.af_carrier,
            "deviation_hz": self.deviation,
            "clock_recovery_bandwidth": 0.06,
            "clock_recovery_limit": 0.004,
        }

    def _get_decoder_config_metadata(self):
        """AFSK always uses AX.25"""
        return {
            "source": self.config_source,
            "framing": self.framing,
            "payload_protocol": "ax25",
        }

    def _get_signal_metadata(self, vfo_state):
        """AFSK uses audio sample rate instead of IQ sample rate"""
        return {
            "frequency_hz": vfo_state.center_freq if vfo_state else None,
            "frequency_mhz": vfo_state.center_freq / 1e6 if vfo_state else None,
            "audio_sample_rate_hz": self.audio_sample_rate,
        }

    def _on_flowgraph_status(self, status, info=None):
        """Callback when flowgraph status changes"""
        self._send_status_update(status, info)

    def _send_status_update(self, status, info=None):
        """Send status update to UI"""
        # Build decoder configuration info
        config_info = {
            "baudrate": self.baudrate,
            "af_carrier_hz": self.af_carrier,
            "deviation_hz": self.deviation,
            "framing": self.framing,
            "transmitter": self.transmitter_description,
            "transmitter_mode": self.transmitter_mode,
            "transmitter_downlink_mhz": (
                round(self.transmitter_downlink_freq / 1e6, 3)
                if self.transmitter_downlink_freq
                else None
            ),
        }

        # Merge with any additional info passed in
        if info:
            config_info.update(info)

        msg = {
            "type": "decoder-status",
            "status": status.value,
            "decoder_type": "afsk",
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
        # UI-friendly stats
        ui_stats = {
            "packets_decoded": self.packet_count,
            "baudrate": self.baudrate,
            "af_carrier": self.af_carrier,
            "deviation": self.deviation,
        }

        # Full performance stats for monitoring (thread-safe copy)
        with self.stats_lock:
            perf_stats = self.stats.copy()

        msg = {
            "type": "decoder-stats",
            "decoder_type": "afsk",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
            "stats": ui_stats,  # UI-friendly stats
            "perf_stats": perf_stats,  # Full performance stats for PerformanceMonitor
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1
        except queue.Full:
            pass

    def run(self):
        """Main thread loop - processes audio samples continuously"""
        # Set process name for visibility in system monitoring tools
        if HAS_SETPROCTITLE:
            setproctitle.setproctitle(f"DynamiX-Labs - AFSK Decoder (VFO {self.vfo})")

        # Initialize components in subprocess (CRITICAL!)
        self.telemetry_parser = TelemetryParser()
        self.vfo_manager = VFOManager()

        # Initialize stats in subprocess (AFSK uses audio, not IQ) - update existing dict
        self.stats.update(
            {
                "audio_chunks_in": 0,
                "samples_in": 0,
                "data_messages_out": 0,
                "queue_timeouts": 0,
                "packets_decoded": 0,
                "last_activity": None,
                "errors": 0,
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "memory_percent": 0.0,
            }
        )

        logger.info(f"AFSK decoder started for {self.session_id}")
        self._send_status_update(DecoderStatus.LISTENING)

        chunks_received = 0
        flowgraph_started = False
        last_stats_time = time.time()  # Track time for periodic stats updates

        # CPU and memory monitoring
        process = psutil.Process()
        last_cpu_check = time.time()
        cpu_check_interval = 0.5  # Update CPU usage every 0.5 seconds

        try:
            # Initialize flowgraph (before consolidated log to avoid duplicate messages)
            self.flowgraph = AFSKFlowgraph(
                sample_rate=self.audio_sample_rate,
                callback=self._on_packet_decoded,
                status_callback=self._on_flowgraph_status,
                baudrate=self.baudrate,
                af_carrier=self.af_carrier,
                deviation=self.deviation,
                use_agc=True,
                dc_block=True,
                batch_interval=self.batch_interval,
                framing=self.framing,
            )
            flowgraph_started = True

            # Consolidated initialization log (replaces "AFSK decoder process started" and "AFSK flowgraph initialized" logs)
            tx_info = (
                f", TX={self.transmitter_downlink_freq/1e6:.3f}MHz"
                if self.transmitter_downlink_freq
                else ""
            )
            logger.info(
                f"AFSK decoder started: session={self.session_id} | "
                f"{self.baudrate}bd, af_carrier={self.af_carrier}Hz, dev={self.deviation}Hz, {self.framing.upper()} | "
                f"audio_rate={self.audio_sample_rate}Hz | batch={self.batch_interval}s{tx_info}"
            )

            while self.running.value == 1:  # Changed from self.running
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

                # Read audio samples from audio_queue
                try:
                    audio_message = self.audio_queue.get(timeout=0.05)  # 50ms timeout

                    # Update stats
                    with self.stats_lock:
                        self.stats["audio_chunks_in"] += 1
                        self.stats["last_activity"] = time.time()

                    # Extract audio samples from message
                    # FM demodulator uses "audio" key, not "samples"
                    samples = audio_message.get("audio")

                    if samples is None or len(samples) == 0:
                        continue

                    # Update sample count
                    with self.stats_lock:
                        self.stats["samples_in"] += len(samples)

                    # Process samples through flowgraph
                    if flowgraph_started and self.flowgraph is not None:
                        self.flowgraph.process_samples(samples)

                    # Send periodic status updates
                    if chunks_received % 50 == 0:
                        self._send_status_update(
                            DecoderStatus.DECODING,
                            {
                                "packets_decoded": self.packet_count,
                            },
                        )

                    chunks_received += 1

                    # Monitor shared memory every 100 chunks
                    if chunks_received % 100 == 0:
                        self._monitor_shared_memory()

                except queue.Empty:
                    with self.stats_lock:
                        self.stats["queue_timeouts"] += 1

                # Send stats periodically based on time (every 1 second) regardless of chunk rate
                current_time = time.time()
                if current_time - last_stats_time >= 1.0:
                    self._send_stats_update()
                    last_stats_time = current_time

        except Exception as e:
            logger.error(f"AFSK decoder error: {e}")
            logger.exception(e)
            with self.stats_lock:
                self.stats["errors"] += 1
            self._send_status_update(DecoderStatus.ERROR)
        except KeyboardInterrupt:
            pass
        finally:
            # Flush any remaining samples
            if flowgraph_started and self.flowgraph:
                try:
                    self.flowgraph.flush_buffer()
                except Exception as e:
                    logger.error(f"Error flushing buffer: {e}")

        logger.info(
            f"AFSK decoder process stopped for {self.session_id}. "
            f"Final SHM segments: {self.get_shm_segment_count()}"
        )

        # stop() method removed - now in BaseDecoderProcess

        # Send final status update
        msg = {
            "type": "decoder-status",
            "status": "closed",
            "decoder_type": "afsk",
            "decoder_id": self.decoder_id,
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


# Export all necessary components
__all__ = [
    "DecoderStatus",
    "AFSKFlowgraph",
    "AFSKMessageHandler",
    "AFSKDecoder",
]
