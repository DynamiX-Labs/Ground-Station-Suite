# Ground Station - GNSS-SDR Decoder
# SPDX-License-Identifier: GPL-3.0-or-later

import glob
import logging
import os
import queue
import re
import shutil
import signal as py_signal
import subprocess
import tempfile
import threading
import time
from enum import Enum
from types import SimpleNamespace
from typing import Any, Dict, Optional, Tuple

import numpy as np
import psutil
import setproctitle
from scipy import signal as sp_signal

try:
    import zmq
except Exception:  # pragma: no cover - optional runtime dependency
    zmq = None

from demodulators.basedecoderprocess import BaseDecoderProcess
from demodulators.gnssmonitorudp import GnssUdpMonitorReceiver
from telemetry.parser import TelemetryParser

logger = logging.getLogger("gnsssdrdecoder")


class DecoderStatus(Enum):
    STARTING = "starting"
    IDLE = "idle"
    LISTENING = "listening"
    ACQUIRING = "acquiring"
    TRACKING = "tracking"
    ERROR = "error"
    CLOSED = "closed"


class GNSSSdrDecoder(BaseDecoderProcess):
    """
    GNSS decoder that streams centered IQ samples into an external gnss-sdr process.

    It reuses the existing raw-IQ decoder path:
    - reads IQ chunks from iq_queue
    - uses VFO center to frequency-translate within the current SDR stream
    - publishes IQ to a ZMQ endpoint consumed by gnss-sdr
    - emits decoder-status / decoder-stats through the existing data queue
    """

    def __init__(
        self,
        iq_queue,
        data_queue,
        session_id,
        config,
        output_dir="data/decoded",
        vfo=None,
        shm_monitor_interval=10,
        shm_restart_threshold=1000,
    ):
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

        # Runtime / IO
        self.gnss_process: Optional[subprocess.Popen[str]] = None
        self.gnss_stdout_thread: Optional[threading.Thread] = None
        self.zmq_context = None
        self.zmq_socket = None
        self.zmq_endpoint: Optional[str] = None
        self.runtime_dir: Optional[str] = None
        self.config_path: Optional[str] = None
        self.nmea_path: Optional[str] = None
        self.nmea_read_offset = 0
        self.last_gnss_log_line = ""
        self._last_log_status_emit_ts = 0.0
        self.gnss_info_log_path: Optional[str] = None
        self.gnss_log_read_offset = 0
        self._last_output_event_ts = 0.0
        self._last_output_event_line = ""
        self._last_input_drop_log_ts = 0.0
        self.monitor_receiver: Optional[GnssUdpMonitorReceiver] = None
        self.monitor_client_addresses = os.environ.get(
            "GNSS_SDR_MONITOR_CLIENT_ADDRESSES", "127.0.0.1"
        )
        self.monitor_bind_host = os.environ.get("GNSS_SDR_MONITOR_BIND_HOST", "0.0.0.0")
        self.monitor_ports: Dict[str, int] = {}
        self._last_udp_event_emit_ts: Dict[Tuple[str, str, int, int], float] = {}
        self._udp_tracking_min_emit_interval_s = float(
            os.environ.get("GNSS_SDR_MONITOR_EVENT_INTERVAL_S", "1.0")
        )
        self._activity_heartbeat_interval_s = float(
            os.environ.get("GNSS_ACTIVITY_HEARTBEAT_INTERVAL_S", "1.0")
        )
        self._last_activity_heartbeat_ts = 0.0
        self._last_activity_packets_total = 0
        self._last_activity_monitor_obs_total = 0
        self._last_activity_loss_of_lock_total = 0
        self._last_status = DecoderStatus.IDLE
        self.gnss_input_transport = "zmq"
        self.zmq_startup_delay_s = float(os.environ.get("GNSS_ZMQ_STARTUP_DELAY_S", "0.2"))
        self.zmq_write_timeout_s = float(os.environ.get("GNSS_ZMQ_WRITE_TIMEOUT_S", "1.0"))

        # DSP state
        self.sdr_sample_rate: Optional[float] = None
        self.sdr_center_freq: Optional[float] = None
        self.output_sample_rate: Optional[float] = None
        self.decimation_factor = 1
        self.decimation_filter = None
        self.cached_vfo_state = None

        # GNSS parameters (from DecoderConfig)
        self.gnss_sample_rate = int(config.gnss_sample_rate or 4_000_000)
        self.gnss_total_channels = int(config.gnss_total_channels or 24)
        self.gnss_output_rate_ms = int(config.gnss_output_rate_ms or 500)
        self.gnss_doppler_max = int(config.gnss_doppler_max or 6000)
        self.enable_gps = bool(
            config.gnss_enable_gps if config.gnss_enable_gps is not None else True
        )
        self.enable_galileo = bool(
            config.gnss_enable_galileo if config.gnss_enable_galileo is not None else True
        )
        self.enable_glonass = bool(
            config.gnss_enable_glonass if config.gnss_enable_glonass is not None else True
        )
        self.enable_beidou = bool(
            config.gnss_enable_beidou if config.gnss_enable_beidou is not None else True
        )
        self.enable_qzss = bool(
            config.gnss_enable_qzss if config.gnss_enable_qzss is not None else True
        )

        # Ensure we always have at least one enabled constellation.
        if not any(
            [
                self.enable_gps,
                self.enable_galileo,
                self.enable_glonass,
                self.enable_beidou,
                self.enable_qzss,
            ]
        ):
            self.enable_gps = True

        # BaseDecoder metadata compatibility
        self.baudrate = config.baudrate
        self.framing = "gnss"
        self.config_source = config.config_source
        self.satellite = config.satellite or {}
        self.transmitter = config.transmitter or {}
        self.norad_id = self.satellite.get("norad_id")
        self.satellite_name = self.satellite.get("name", "")
        self.transmitter_description = self.transmitter.get("description", "")
        self.transmitter_mode = (config.transmitter or {}).get("mode") or "GNSS"
        self.transmitter_downlink_freq = self.transmitter.get("downlink_low")

    def _get_decoder_type_for_init(self) -> str:
        return "GNSS"

    def _get_decoder_type(self) -> str:
        return "gnss"

    def _get_decoder_specific_metadata(self) -> dict:
        return {
            "gnss_sample_rate": self.gnss_sample_rate,
            "gnss_total_channels": self.gnss_total_channels,
            "gps": self.enable_gps,
            "galileo": self.enable_galileo,
            "glonass": self.enable_glonass,
            "beidou": self.enable_beidou,
            "qzss": self.enable_qzss,
        }

    def _get_filename_params(self) -> str:
        return f"GNSS_{self.gnss_sample_rate//1000}kSps"

    def _get_parameters_string(self) -> str:
        enabled = []
        if self.enable_gps:
            enabled.append("GPS")
        if self.enable_galileo:
            enabled.append("GAL")
        if self.enable_glonass:
            enabled.append("GLO")
        if self.enable_beidou:
            enabled.append("BDS")
        if self.enable_qzss:
            enabled.append("QZS")
        return f"{'/'.join(enabled)} @ {self.gnss_sample_rate/1e6:.2f} MS/s"

    def _get_demodulator_params_metadata(self) -> dict:
        return {
            "sample_rate_hz": self.gnss_sample_rate,
            "total_channels": self.gnss_total_channels,
            "doppler_max_hz": self.gnss_doppler_max,
        }

    def _get_payload_protocol(self) -> str:
        return "gnss"

    def _get_decoder_config_metadata(self) -> dict:
        return {
            "source": self.config_source,
            "framing": "gnss",
            "payload_protocol": "gnss",
            "constellations": {
                "gps": self.enable_gps,
                "galileo": self.enable_galileo,
                "glonass": self.enable_glonass,
                "beidou": self.enable_beidou,
                "qzss": self.enable_qzss,
            },
            "sample_rate_hz": self.gnss_sample_rate,
            "total_channels": self.gnss_total_channels,
            "output_rate_ms": self.gnss_output_rate_ms,
        }

    def _get_vfo_state(self):
        if self.cached_vfo_state:
            return SimpleNamespace(**self.cached_vfo_state)
        return None

    def _send_status_update(
        self, status: DecoderStatus, info: Optional[Dict[str, Any]] = None
    ) -> None:
        self._last_status = status
        enabled = []
        if self.enable_gps:
            enabled.append("GPS")
        if self.enable_galileo:
            enabled.append("Galileo")
        if self.enable_glonass:
            enabled.append("GLONASS")
        if self.enable_beidou:
            enabled.append("BeiDou")
        if self.enable_qzss:
            enabled.append("QZSS")

        status_info = {
            "transmitter_mode": "GNSS",
            "framing": "gnss",
            "sample_rate_hz": self.output_sample_rate or self.gnss_sample_rate,
            "requested_sample_rate_hz": self.gnss_sample_rate,
            "total_channels": self.gnss_total_channels,
            "constellations": enabled,
            "doppler_max_hz": self.gnss_doppler_max,
        }
        if info:
            status_info.update(info)

        msg = {
            "type": "decoder-status",
            "status": status.value,
            "decoder_type": "gnss",
            "decoder_id": self.decoder_id,
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
            "info": status_info,
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1
        except queue.Full:
            pass

    def _send_stats_update(self):
        with self.stats_lock:
            perf_stats = self.stats.copy()

        ui_stats = {
            "iq_chunks_in": perf_stats.get("iq_chunks_in", 0),
            "samples_in": perf_stats.get("samples_in", 0),
            "samples_written": perf_stats.get("samples_written_to_input", 0),
            "input_write_drops": perf_stats.get("input_write_drops", 0),
            "input_blocking_retries": perf_stats.get("input_blocking_retries", 0),
            "input_partial_write_events": perf_stats.get("input_partial_write_events", 0),
            "input_write_errors": perf_stats.get("input_write_errors", 0),
            "queue_timeouts": perf_stats.get("queue_timeouts", 0),
            "udp_packets_total": perf_stats.get("udp_packets_total", 0),
            "udp_packets_monitor": perf_stats.get("udp_packets_monitor", 0),
            "udp_packets_acquisition": perf_stats.get("udp_packets_acquisition", 0),
            "udp_packets_tracking": perf_stats.get("udp_packets_tracking", 0),
            "udp_packets_pvt": perf_stats.get("udp_packets_pvt", 0),
            "udp_monitor_observations": perf_stats.get("udp_monitor_observations", 0),
            "udp_parse_errors": perf_stats.get("udp_parse_errors", 0),
            "udp_events_emitted": perf_stats.get("udp_events_emitted", 0),
            "udp_events_suppressed": perf_stats.get("udp_events_suppressed", 0),
            "activity_heartbeats_emitted": perf_stats.get("activity_heartbeats_emitted", 0),
            "loss_of_lock_total": perf_stats.get("loss_of_lock_total", 0),
            "gnss_input_transport": self.gnss_input_transport,
            "gnss_zmq_endpoint": self.zmq_endpoint,
            "last_gnss_log": self.last_gnss_log_line,
        }

        msg = {
            "type": "decoder-stats",
            "decoder_type": "gnss",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
            "stats": ui_stats,
            "perf_stats": perf_stats,
            "rates": {},
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1
        except queue.Full:
            pass

    def _send_output_update(self, output_data: Dict[str, Any]) -> None:
        payload = dict(output_data)
        payload.setdefault("format", "application/json")
        payload.setdefault("parameters", self._get_parameters_string())
        payload.setdefault("decoder_config", self._get_decoder_config_metadata())

        vfo_state = self._get_vfo_state()
        if vfo_state:
            payload.setdefault("signal", self._get_signal_metadata(vfo_state))

        msg = {
            "type": "decoder-output",
            "decoder_type": "gnss",
            "session_id": self.session_id,
            "vfo": self.vfo,
            "timestamp": time.time(),
            "output": payload,
        }
        try:
            self.data_queue.put(msg, block=False)
            with self.stats_lock:
                self.stats["data_messages_out"] += 1
        except queue.Full:
            pass

    @staticmethod
    def _frequency_translate(
        samples: np.ndarray, offset_freq: float, sample_rate: float
    ) -> np.ndarray:
        if offset_freq == 0:
            return samples
        t = np.arange(len(samples), dtype=np.float64) / sample_rate
        shift = np.exp(-2j * np.pi * offset_freq * t)
        return samples * shift

    @staticmethod
    def _is_vfo_in_sdr_bandwidth(
        vfo_center: float, sdr_center: float, sdr_sample_rate: float
    ) -> Tuple[bool, float, float]:
        offset = vfo_center - sdr_center
        half_bw = sdr_sample_rate / 2
        usable_bw = half_bw * 0.98
        in_band = abs(offset) <= usable_bw
        margin_hz = usable_bw - abs(offset)
        return in_band, offset, margin_hz

    @staticmethod
    def _design_decimation_filter(decimation_factor: int, bandwidth: float, sample_rate: float):
        cutoff = max(200_000.0, min((bandwidth / 2.0), sample_rate * 0.45))
        transition = max(50_000.0, cutoff * 0.1)
        numtaps = int(sample_rate / transition) | 1
        numtaps = min(numtaps, 1001)
        return sp_signal.firwin(numtaps, cutoff, fs=sample_rate)

    def _configure_sample_rate_path(self, sdr_rate: float, vfo_bandwidth: float) -> None:
        # Prefer an integer decimation path for predictable, low-overhead runtime behavior.
        if self.gnss_sample_rate <= 0:
            self.gnss_sample_rate = int(sdr_rate)

        decimation = (
            int(round(sdr_rate / self.gnss_sample_rate)) if self.gnss_sample_rate > 0 else 1
        )
        if decimation < 1:
            decimation = 1

        self.decimation_factor = decimation
        self.output_sample_rate = sdr_rate / self.decimation_factor
        if self.decimation_factor > 1:
            self.decimation_filter = self._design_decimation_filter(
                self.decimation_factor, vfo_bandwidth, sdr_rate
            )
        else:
            self.decimation_filter = None

    def _decimate_iq(self, samples: np.ndarray) -> np.ndarray:
        if self.decimation_factor <= 1:
            return samples
        filtered = sp_signal.lfilter(self.decimation_filter, 1, samples)
        return filtered[:: self.decimation_factor]

    def _enabled_signal_ids(self):
        signal_ids = []
        if self.enable_gps:
            signal_ids.append("1C")
        if self.enable_galileo:
            signal_ids.append("1B")
        if self.enable_glonass:
            signal_ids.append("1G")
        if self.enable_beidou:
            signal_ids.append("B1")
        if self.enable_qzss:
            signal_ids.append("J1")
        return signal_ids

    def _allocate_channel_counts(self) -> Dict[str, int]:
        enabled = self._enabled_signal_ids()
        if not enabled:
            enabled = ["1C"]
        total = max(len(enabled), self.gnss_total_channels)
        counts = {signal_id: 1 for signal_id in enabled}
        remaining = total - len(enabled)
        idx = 0
        while remaining > 0:
            key = enabled[idx % len(enabled)]
            counts[key] += 1
            idx += 1
            remaining -= 1
        return counts

    def _build_gnss_sdr_config(self) -> str:
        channel_counts = self._allocate_channel_counts()
        nmea_filename = os.path.basename(self.nmea_path) if self.nmea_path else "gnss_sdr_pvt.nmea"
        input_sample_rate = int(self.output_sample_rate or self.gnss_sample_rate)
        lines = [
            "; Auto-generated by Ground Station GNSSSdrDecoder",
            "[GNSS-SDR]",
            f"GNSS-SDR.internal_fs_sps={input_sample_rate}",
            "",
            "SignalSource.implementation=ZMQ_Signal_Source",
            f"SignalSource.endpoint={self.zmq_endpoint}",
            "SignalSource.item_type=gr_complex",
            "SignalSource.vlen=1",
            "SignalSource.pass_tags=false",
            "SignalSource.timeout_ms=100",
            f"SignalSource.sampling_frequency={input_sample_rate}",
            "SignalSource.dump=false",
            "",
            "SignalConditioner.implementation=Pass_Through",
            "",
        ]

        for signal_id, count in channel_counts.items():
            lines.append(f"Channels_{signal_id}.count={count}")
        lines.append(f"Channels.in_acquisition={max(1, min(4, len(channel_counts)))}")
        lines.append("")

        if "1C" in channel_counts:
            lines.extend(
                [
                    "Acquisition_1C.implementation=GPS_L1_CA_PCPS_Acquisition",
                    "Acquisition_1C.item_type=gr_complex",
                    "Acquisition_1C.pfa=0.015",
                    f"Acquisition_1C.doppler_max={self.gnss_doppler_max}",
                    "Acquisition_1C.doppler_step=200",
                    "Acquisition_1C.max_dwells=4",
                    "Tracking_1C.implementation=GPS_L1_CA_DLL_PLL_Tracking",
                    "Tracking_1C.item_type=gr_complex",
                    "Tracking_1C.pll_bw_hz=30.0",
                    "Tracking_1C.dll_bw_hz=2.0",
                    "Tracking_1C.fll_bw_hz=10",
                    "Tracking_1C.enable_fll_pull_in=true",
                    "Tracking_1C.enable_fll_steady_state=false",
                    "TelemetryDecoder_1C.implementation=GPS_L1_CA_Telemetry_Decoder",
                    "",
                ]
            )

        if "1B" in channel_counts:
            lines.extend(
                [
                    "Acquisition_1B.implementation=Galileo_E1_PCPS_Ambiguous_Acquisition",
                    "Acquisition_1B.pfa=0.025",
                    f"Acquisition_1B.doppler_max={self.gnss_doppler_max}",
                    "Acquisition_1B.doppler_step=200",
                    "Acquisition_1B.max_dwells=4",
                    "Acquisition_1B.cboc=true",
                    "Tracking_1B.implementation=Galileo_E1_DLL_PLL_VEML_Tracking",
                    "Tracking_1B.item_type=gr_complex",
                    "Tracking_1B.pll_bw_hz=30.0",
                    "Tracking_1B.dll_bw_hz=2.0",
                    "Tracking_1B.fll_bw_hz=20",
                    "Tracking_1B.enable_fll_pull_in=true",
                    "Tracking_1B.enable_fll_steady_state=false",
                    "TelemetryDecoder_1B.implementation=Galileo_E1B_Telemetry_Decoder",
                    "",
                ]
            )

        if "1G" in channel_counts:
            lines.extend(
                [
                    "Acquisition_1G.implementation=GLONASS_L1_CA_PCPS_Acquisition",
                    "Acquisition_1G.item_type=gr_complex",
                    "Acquisition_1G.pfa=0.02",
                    f"Acquisition_1G.doppler_max={self.gnss_doppler_max}",
                    "Acquisition_1G.doppler_step=100",
                    "Acquisition_1G.max_dwells=4",
                    "Tracking_1G.implementation=GLONASS_L1_CA_DLL_PLL_Tracking",
                    "Tracking_1G.item_type=gr_complex",
                    "Tracking_1G.pll_bw_hz=40",
                    "Tracking_1G.dll_bw_hz=2.5",
                    "TelemetryDecoder_1G.implementation=GLONASS_L1_CA_Telemetry_Decoder",
                    "",
                ]
            )

        if "B1" in channel_counts:
            lines.extend(
                [
                    "Acquisition_B1.implementation=BEIDOU_B1I_PCPS_Acquisition",
                    "Acquisition_B1.item_type=gr_complex",
                    "Acquisition_B1.pfa=0.000002",
                    f"Acquisition_B1.doppler_max={self.gnss_doppler_max}",
                    "Acquisition_B1.doppler_step=100",
                    "Tracking_B1.implementation=BEIDOU_B1I_DLL_PLL_Tracking",
                    "Tracking_B1.item_type=gr_complex",
                    "Tracking_B1.pll_bw_hz=50.0",
                    "Tracking_B1.dll_bw_hz=2.0",
                    "TelemetryDecoder_B1.implementation=BEIDOU_B1I_Telemetry_Decoder",
                    "",
                ]
            )

        if "J1" in channel_counts:
            lines.extend(
                [
                    "Acquisition_J1.implementation=QZSS_L1_PCPS_Acquisition",
                    "Acquisition_J1.item_type=gr_complex",
                    "Acquisition_J1.pfa=0.02",
                    f"Acquisition_J1.doppler_max={self.gnss_doppler_max}",
                    "Acquisition_J1.doppler_step=200",
                    "Acquisition_J1.max_dwells=4",
                    "Tracking_J1.implementation=QZSS_L1_CA_DLL_PLL_Tracking",
                    "Tracking_J1.item_type=gr_complex",
                    "Tracking_J1.pll_bw_hz=30.0",
                    "Tracking_J1.dll_bw_hz=2.0",
                    "TelemetryDecoder_J1.implementation=QZSS_L1_Telemetry_Decoder",
                    "",
                ]
            )

        lines.extend(
            [
                "Observables.implementation=Hybrid_Observables",
                "Observables.dump=false",
                "",
                "PVT.implementation=RTKLIB_PVT",
                "PVT.positioning_mode=Single",
                "PVT.iono_model=Broadcast",
                "PVT.trop_model=Saastamoinen",
                f"PVT.output_rate_ms={self.gnss_output_rate_ms}",
                f"PVT.display_rate_ms={self.gnss_output_rate_ms}",
                "PVT.output_enabled=true",
                f"PVT.output_path={self.runtime_dir}",
                "PVT.nmea_output_file_enabled=true",
                f"PVT.nmea_output_file_path={self.runtime_dir}",
                f"PVT.nmea_rate_ms={self.gnss_output_rate_ms}",
                "PVT.flag_nmea_tty_port=false",
                f"PVT.nmea_dump_filename={nmea_filename}",
                "PVT.gpx_output_enabled=false",
                "PVT.geojson_output_enabled=false",
                "PVT.kml_output_enabled=false",
                "PVT.dump=false",
                "",
                # Use GNSS-SDR UDP monitor streams as the default event transport.
                "Monitor.enable_monitor=true",
                f"Monitor.client_addresses={self.monitor_client_addresses}",
                f"Monitor.udp_port={self.monitor_ports.get('monitor', 0)}",
                "Monitor.enable_protobuf=true",
                "",
                "AcquisitionMonitor.enable_monitor=true",
                f"AcquisitionMonitor.client_addresses={self.monitor_client_addresses}",
                f"AcquisitionMonitor.udp_port={self.monitor_ports.get('acquisition', 0)}",
                "AcquisitionMonitor.enable_protobuf=true",
                "",
                "TrackingMonitor.enable_monitor=true",
                f"TrackingMonitor.client_addresses={self.monitor_client_addresses}",
                f"TrackingMonitor.udp_port={self.monitor_ports.get('tracking', 0)}",
                "TrackingMonitor.enable_protobuf=true",
                "",
                "PVT.enable_monitor=true",
                f"PVT.monitor_client_addresses={self.monitor_client_addresses}",
                f"PVT.monitor_udp_port={self.monitor_ports.get('pvt', 0)}",
                "PVT.enable_protobuf=true",
            ]
        )
        return "\n".join(lines) + "\n"

    def _prepare_runtime(self):
        self.runtime_dir = tempfile.mkdtemp(prefix=f"gnss_sdr_{self.session_id}_vfo{self.vfo}_")
        self.zmq_endpoint = None
        self.config_path = os.path.join(self.runtime_dir, "gnss-sdr.conf")
        self.nmea_path = os.path.join(self.runtime_dir, "gnss_sdr_pvt.nmea")
        self._last_udp_event_emit_ts = {}
        self._last_activity_heartbeat_ts = 0.0
        self._last_activity_packets_total = 0
        self._last_activity_monitor_obs_total = 0
        self._last_activity_loss_of_lock_total = 0
        if self.monitor_receiver is not None:
            self.monitor_receiver.close()
        self.monitor_receiver = GnssUdpMonitorReceiver(bind_host=self.monitor_bind_host)
        self.monitor_ports = dict(self.monitor_receiver.ports)

        if zmq is None:
            raise RuntimeError("GNSS ZMQ input selected but pyzmq is not available")
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.PUB)
        self.zmq_socket.setsockopt(zmq.LINGER, 0)
        sndhwm = int(os.environ.get("GNSS_ZMQ_SNDHWM", "0") or 0)
        if sndhwm > 0:
            self.zmq_socket.setsockopt(zmq.SNDHWM, sndhwm)
        configured_endpoint = os.environ.get("GNSS_ZMQ_ENDPOINT", "").strip()
        if configured_endpoint:
            self.zmq_socket.bind(configured_endpoint)
            self.zmq_endpoint = configured_endpoint
        else:
            self.zmq_socket.bind("tcp://127.0.0.1:*")
            self.zmq_endpoint = self.zmq_socket.getsockopt_string(zmq.LAST_ENDPOINT)

        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(self._build_gnss_sdr_config())

    def _read_gnss_stdout(self):
        if not self.gnss_process or not self.gnss_process.stdout:
            return
        for raw_line in self.gnss_process.stdout:
            if self.running.value != 1:
                break
            line = raw_line.strip()
            if not line:
                continue
            # Keep the latest GNSS-SDR line for status/debug visibility.
            # Decoder outputs now come from UDP monitor streams.
            self.last_gnss_log_line = line[:300]

    def _discover_gnss_log_file(self) -> Optional[str]:
        if self.gnss_info_log_path:
            return self.gnss_info_log_path
        if not self.gnss_process or not self.gnss_process.pid:
            return None

        pid = self.gnss_process.pid
        candidates = sorted(glob.glob(f"/tmp/gnss-sdr.*.{pid}"))
        if not candidates:
            return None

        info_candidates = [path for path in candidates if ".INFO." in path]
        self.gnss_info_log_path = info_candidates[0] if info_candidates else candidates[0]
        self.gnss_log_read_offset = 0
        return self.gnss_info_log_path

    def _parse_satellite_from_log_line(self, line: str) -> Dict[str, Any]:
        parsed: Dict[str, Any] = {}

        acq_match = re.search(
            r"Successful acquisition in channel\s+(\d+)\s+for satellite\s+([A-Z])\s+(\d+)",
            line,
        )
        if acq_match:
            parsed["channel"] = int(acq_match.group(1))
            parsed["satellite_system"] = acq_match.group(2)
            parsed["satellite_prn"] = int(acq_match.group(3))
            return parsed

        # GNSS-SDR loss/tracking lines appear in both of these orders:
        #   "for satellite ... in channel N"
        #   "in channel N for satellite ..."
        satellite_desc = None
        channel = None

        satellite_first_match = re.search(
            r"for satellite\s+(.+?)\s+in channel\s+(\d+)",
            line,
            flags=re.IGNORECASE,
        )
        if satellite_first_match:
            satellite_desc = satellite_first_match.group(1).strip()
            channel = int(satellite_first_match.group(2))
        else:
            channel_first_match = re.search(
                r"(?:in|on)\s+channel\s+(\d+)\s+for satellite\s+(.+)$",
                line,
                flags=re.IGNORECASE,
            )
            if channel_first_match:
                channel = int(channel_first_match.group(1))
                satellite_desc = channel_first_match.group(2).strip()

        if satellite_desc:
            parsed["satellite"] = satellite_desc
        if channel is not None:
            parsed["channel"] = channel

        if satellite_desc:
            # Normalize known line formats:
            #   "GPS PRN 04 ..."
            #   "Galileo PRN E29 ..."
            #   "G 04"
            #   "E 29"
            tracking_sat_match = re.search(
                r"([A-Za-z]+)\s+PRN\s+([A-Za-z]?\d+)",
                satellite_desc,
                flags=re.IGNORECASE,
            )
            if tracking_sat_match:
                system_name = tracking_sat_match.group(1).strip().upper()
                prn_token = tracking_sat_match.group(2).strip().upper()
                prn_match = re.search(r"(\d+)", prn_token)
                if prn_match:
                    parsed["satellite_prn"] = int(prn_match.group(1))

                system_map = {
                    "GPS": "G",
                    "GALILEO": "E",
                    "GLONASS": "R",
                    "BEIDOU": "C",
                    "BDS": "C",
                    "QZSS": "J",
                }
                if system_name in system_map:
                    parsed["satellite_system"] = system_map[system_name]
                elif len(system_name) == 1:
                    parsed["satellite_system"] = system_name
            else:
                short_sat_match = re.search(
                    r"\b([A-Za-z])\s*(\d+)\b",
                    satellite_desc,
                    flags=re.IGNORECASE,
                )
                if short_sat_match:
                    parsed["satellite_system"] = short_sat_match.group(1).upper()
                    parsed["satellite_prn"] = int(short_sat_match.group(2))

        return parsed

    def _handle_gnss_log_line(self, line: str) -> None:
        message = line.strip()
        if not message:
            return

        self.last_gnss_log_line = message[:300]
        now = time.time()

        status = None
        event_type = None
        normalized_message = message.lower()
        if "Successful acquisition" in message:
            status = DecoderStatus.ACQUIRING
            event_type = "acquisition"
        elif "Pull-in:" in message or "Tracking" in message:
            status = DecoderStatus.TRACKING
            event_type = "tracking"
        elif "First NMEA message" in message:
            status = DecoderStatus.TRACKING
            event_type = "nmea"
        elif "loss of lock" in normalized_message:
            # Explicitly emit lock-loss events so the UI can mark satellites as lost.
            event_type = "lost"

        if status is not None and (now - self._last_log_status_emit_ts) >= 0.25:
            self._last_log_status_emit_ts = now
            self._send_status_update(status, {"gnss_log": self.last_gnss_log_line})

        if event_type is None:
            return
        if message == self._last_output_event_line and (now - self._last_output_event_ts) < 1.0:
            return

        self._last_output_event_line = message
        self._last_output_event_ts = now
        event = {
            "event": event_type,
            "message": self.last_gnss_log_line,
        }
        event.update(self._parse_satellite_from_log_line(message))
        if event_type == "lost":
            with self.stats_lock:
                self.stats["loss_of_lock_total"] = int(self.stats.get("loss_of_lock_total", 0)) + 1
        self._send_output_update(event)

    def _poll_gnss_log_updates(self) -> None:
        log_path = self._discover_gnss_log_file()
        if not log_path or not os.path.exists(log_path):
            return

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self.gnss_log_read_offset)
                new_lines = f.readlines()
                self.gnss_log_read_offset = f.tell()
        except Exception:
            return

        # Keep log parsing strictly scoped to lock-loss lines.
        # Acquisition/tracking events are already sourced from UDP monitor streams.
        for line in new_lines[-50:]:
            if "loss of lock" in line.lower():
                self._handle_gnss_log_line(line)

    def _write_zmq_payload(
        self, payload: bytes, sample_count: int
    ) -> Tuple[int, int, int, int, int]:
        if sample_count <= 0:
            return 0, 0, 0, 0, 0
        if self.zmq_socket is None or zmq is None:
            return 0, sample_count, 0, 0, 1

        retries = 0
        deadline = time.time() + self.zmq_write_timeout_s
        while self.running.value == 1:
            try:
                self.zmq_socket.send(payload, flags=zmq.NOBLOCK)
                return sample_count, 0, retries, 0, 0
            except zmq.Again:
                retries += 1
                if time.time() >= deadline:
                    break
                time.sleep(0.001)
            except Exception:
                break
        return 0, sample_count, retries, 0, 1

    def _parse_nmea_lat_lon(self, value: str, hemisphere: str) -> Optional[float]:
        if not value:
            return None
        try:
            # ddmm.mmmm (lat) or dddmm.mmmm (lon)
            if "." not in value:
                return None
            dot_index = value.index(".")
            deg_len = 2 if dot_index <= 4 else 3
            degrees = float(value[:deg_len])
            minutes = float(value[deg_len:])
            decimal = degrees + minutes / 60.0
            if hemisphere in ("S", "W"):
                decimal = -decimal
            return decimal
        except Exception:
            return None

    def _poll_nmea_updates(self):
        if not self.nmea_path or not os.path.exists(self.nmea_path):
            return
        try:
            with open(self.nmea_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self.nmea_read_offset)
                new_lines = f.readlines()
                self.nmea_read_offset = f.tell()
        except Exception:
            return

        for line in new_lines[-10:]:
            sentence = line.strip()
            if not sentence.startswith("$"):
                continue
            parts = sentence.split(",")
            if not parts:
                continue

            info: Dict[str, Any] = {"nmea_sentence": sentence[:120]}
            if parts[0].endswith("GGA") and len(parts) >= 10:
                lat = self._parse_nmea_lat_lon(parts[2], parts[3])
                lon = self._parse_nmea_lat_lon(parts[4], parts[5])
                fix_quality = parts[6] if len(parts) > 6 else ""
                sats = parts[7] if len(parts) > 7 else ""
                alt = parts[9] if len(parts) > 9 else ""
                info.update(
                    {
                        "fix_quality": fix_quality,
                        "satellites": int(sats) if sats.isdigit() else None,
                        "latitude": lat,
                        "longitude": lon,
                        "altitude_m": float(alt) if alt else None,
                    }
                )
                self._send_status_update(DecoderStatus.TRACKING, info)
                self._send_output_update(
                    {
                        "event": "nmea_gga",
                        "nmea_sentence": sentence[:120],
                        "fix_quality": info.get("fix_quality"),
                        "satellites": info.get("satellites"),
                        "latitude": info.get("latitude"),
                        "longitude": info.get("longitude"),
                        "altitude_m": info.get("altitude_m"),
                    }
                )
            elif parts[0].endswith("RMC") and len(parts) >= 7:
                lat = self._parse_nmea_lat_lon(parts[3], parts[4])
                lon = self._parse_nmea_lat_lon(parts[5], parts[6])
                info.update({"latitude": lat, "longitude": lon})
                self._send_status_update(DecoderStatus.TRACKING, info)
                self._send_output_update(
                    {
                        "event": "nmea_rmc",
                        "nmea_sentence": sentence[:120],
                        "latitude": info.get("latitude"),
                        "longitude": info.get("longitude"),
                    }
                )

    @staticmethod
    def _normalize_satellite_system(value: Any) -> str:
        raw = str(value or "").strip().upper()
        if not raw:
            return ""
        mapping = {
            "GPS": "G",
            "G": "G",
            "GALILEO": "E",
            "E": "E",
            "GLONASS": "R",
            "R": "R",
            "BEIDOU": "C",
            "BDS": "C",
            "B": "C",
            "C": "C",
            "QZSS": "J",
            "QZS": "J",
            "J": "J",
        }
        return mapping.get(raw, raw[:1])

    def _should_emit_udp_event(
        self, event_type: str, system: str, prn: int, channel: Optional[int]
    ) -> bool:
        channel_id = int(channel) if channel is not None else -1
        key = (event_type, system, int(prn), channel_id)
        now = time.time()
        last = self._last_udp_event_emit_ts.get(key, 0.0)
        if (now - last) < self._udp_tracking_min_emit_interval_s:
            with self.stats_lock:
                self.stats["udp_events_suppressed"] += 1
            return False
        self._last_udp_event_emit_ts[key] = now
        return True

    def _emit_udp_satellite_event(self, event_type: str, observation: Dict[str, Any]) -> None:
        system = self._normalize_satellite_system(observation.get("system"))
        prn_raw = observation.get("prn")
        if prn_raw is None:
            return
        try:
            prn = int(str(prn_raw))
        except (TypeError, ValueError):
            return
        if not system or prn <= 0:
            return

        channel_raw = observation.get("channel_id")
        channel: Optional[int]
        try:
            channel = int(channel_raw) if channel_raw is not None else None
        except (TypeError, ValueError):
            channel = None

        if not self._should_emit_udp_event(event_type, system, prn, channel):
            return

        cn0 = observation.get("cn0_db_hz")
        doppler = observation.get("carrier_doppler_hz")
        payload: Dict[str, Any] = {
            "event": event_type,
            "satellite_system": system,
            "satellite_prn": prn,
            "channel": channel,
            "message": f"{event_type.upper()} {system}{prn:02d}",
        }
        if cn0 is not None:
            payload["cn0_db_hz"] = cn0
        if doppler is not None:
            payload["carrier_doppler_hz"] = doppler

        self._send_output_update(payload)
        with self.stats_lock:
            self.stats["udp_events_emitted"] += 1

    def _emit_udp_pvt_event(self, pvt: Dict[str, Any]) -> None:
        latitude = pvt.get("latitude")
        longitude = pvt.get("longitude")
        altitude = pvt.get("height")
        valid_sats = pvt.get("valid_sats")
        solution_status = pvt.get("solution_status")

        has_coords = latitude is not None and longitude is not None
        has_solution = solution_status is not None
        if not has_coords and not has_solution:
            return

        if not self._should_emit_udp_event("nmea_gga", "P", 0, 0):
            return

        payload: Dict[str, Any] = {
            "event": "nmea_gga",
            "message": "PVT update",
            "latitude": latitude,
            "longitude": longitude,
            "altitude_m": altitude,
            "satellites": valid_sats,
            "fix_quality": str(solution_status) if solution_status is not None else "0",
        }
        utc_time = pvt.get("utc_time")
        if utc_time:
            payload["utc_time"] = utc_time

        self._send_output_update(payload)
        self._send_status_update(
            DecoderStatus.TRACKING,
            {
                "latitude": latitude,
                "longitude": longitude,
                "altitude_m": altitude,
                "satellites": valid_sats,
                "fix_quality": payload["fix_quality"],
                "utc_time": utc_time,
            },
        )
        with self.stats_lock:
            self.stats["udp_events_emitted"] += 1

    def _poll_monitor_updates(self) -> None:
        if not self.monitor_receiver:
            return

        polled = self.monitor_receiver.poll()
        monitor_messages = polled.get("monitor", [])
        acquisition_messages = polled.get("acquisition", [])
        tracking_messages = polled.get("tracking", [])
        snapshot = self.monitor_receiver.snapshot_stats()
        observable_count = (
            len(monitor_messages) + len(acquisition_messages) + len(tracking_messages)
        )
        with self.stats_lock:
            self.stats["udp_packets_total"] = snapshot.get("packets_total", 0)
            self.stats["udp_packets_monitor"] = snapshot.get("packets_monitor", 0)
            self.stats["udp_packets_acquisition"] = snapshot.get("packets_acquisition", 0)
            self.stats["udp_packets_tracking"] = snapshot.get("packets_tracking", 0)
            self.stats["udp_packets_pvt"] = snapshot.get("packets_pvt", 0)
            self.stats["udp_monitor_observations"] += observable_count
            self.stats["udp_parse_errors"] = snapshot.get("parse_errors", 0)

        saw_acquisition = False
        saw_tracking = False

        for obs in monitor_messages:
            if bool(obs.get("flag_valid_word")) or bool(obs.get("flag_valid_symbol_output")):
                self._emit_udp_satellite_event("tracking", obs)
                saw_tracking = True
            elif bool(obs.get("flag_valid_acquisition")):
                self._emit_udp_satellite_event("acquisition", obs)
                saw_acquisition = True

        for obs in acquisition_messages:
            self._emit_udp_satellite_event("acquisition", obs)
            saw_acquisition = True

        for obs in tracking_messages:
            self._emit_udp_satellite_event("tracking", obs)
            saw_tracking = True

        for pvt in polled.get("pvt", []):
            self._emit_udp_pvt_event(pvt)
            saw_tracking = True

        # Backward-compatible state updates for the decoder lifecycle panel.
        now = time.time()
        if saw_tracking and (now - self._last_log_status_emit_ts) >= 0.25:
            self._last_log_status_emit_ts = now
            self._send_status_update(DecoderStatus.TRACKING, {"source": "udp_monitor"})
        elif saw_acquisition and (now - self._last_log_status_emit_ts) >= 0.25:
            self._last_log_status_emit_ts = now
            self._send_status_update(DecoderStatus.ACQUIRING, {"source": "udp_monitor"})

    def _emit_activity_heartbeat(self, now: Optional[float] = None) -> None:
        current_time = now if now is not None else time.time()
        with self.stats_lock:
            packets_total = int(self.stats.get("udp_packets_total", 0))
            monitor_packets = int(self.stats.get("udp_packets_monitor", 0))
            acquisition_packets = int(self.stats.get("udp_packets_acquisition", 0))
            tracking_packets = int(self.stats.get("udp_packets_tracking", 0))
            pvt_packets = int(self.stats.get("udp_packets_pvt", 0))
            monitor_obs_total = int(self.stats.get("udp_monitor_observations", 0))
            input_write_drops = int(self.stats.get("input_write_drops", 0))
            queue_timeouts = int(self.stats.get("queue_timeouts", 0))
            loss_of_lock_total = int(self.stats.get("loss_of_lock_total", 0))

        elapsed = current_time - self._last_activity_heartbeat_ts
        if elapsed <= 0:
            elapsed = self._activity_heartbeat_interval_s

        packets_delta = max(0, packets_total - self._last_activity_packets_total)
        monitor_obs_delta = max(0, monitor_obs_total - self._last_activity_monitor_obs_total)
        loss_of_lock_delta = max(0, loss_of_lock_total - self._last_activity_loss_of_lock_total)
        packets_per_sec = packets_delta / elapsed
        monitor_obs_per_sec = monitor_obs_delta / elapsed
        has_activity = packets_delta > 0 or monitor_obs_delta > 0
        has_pvt = pvt_packets > 0

        self._send_output_update(
            {
                "event": "gnss_activity",
                "message": "GNSS monitor heartbeat",
                "has_activity": has_activity,
                "has_pvt": has_pvt,
                "udp_packets_total": packets_total,
                "udp_packets_monitor": monitor_packets,
                "udp_packets_acquisition": acquisition_packets,
                "udp_packets_tracking": tracking_packets,
                "udp_packets_pvt": pvt_packets,
                "udp_packets_delta": packets_delta,
                "udp_packets_per_sec": packets_per_sec,
                "monitor_observations_total": monitor_obs_total,
                "monitor_observations_delta": monitor_obs_delta,
                "monitor_observations_per_sec": monitor_obs_per_sec,
                "loss_of_lock_total": loss_of_lock_total,
                "loss_of_lock_delta": loss_of_lock_delta,
                "input_write_drops": input_write_drops,
                "queue_timeouts": queue_timeouts,
            }
        )
        self._send_status_update(
            self._last_status,
            {
                "gnss_has_activity": has_activity,
                "gnss_has_pvt": has_pvt,
                "gnss_udp_packets_per_sec": packets_per_sec,
                "gnss_monitor_obs_per_sec": monitor_obs_per_sec,
                "gnss_loss_of_lock_total": loss_of_lock_total,
                "gnss_loss_of_lock_delta": loss_of_lock_delta,
            },
        )
        with self.stats_lock:
            self.stats["activity_heartbeats_emitted"] += 1

        self._last_activity_heartbeat_ts = current_time
        self._last_activity_packets_total = packets_total
        self._last_activity_monitor_obs_total = monitor_obs_total
        self._last_activity_loss_of_lock_total = loss_of_lock_total

    def _cleanup_runtime(self):
        if self.monitor_receiver is not None:
            try:
                self.monitor_receiver.close()
            except Exception:
                pass
            self.monitor_receiver = None
            self.monitor_ports = {}

        if self.zmq_socket is not None:
            try:
                self.zmq_socket.close()
            except Exception:
                pass
            self.zmq_socket = None

        if self.zmq_context is not None:
            try:
                self.zmq_context.term()
            except Exception:
                pass
            self.zmq_context = None

        if self.gnss_process:
            self._stop_gnss_process()
            self.gnss_process = None

        if self.runtime_dir and os.path.isdir(self.runtime_dir):
            shutil.rmtree(self.runtime_dir, ignore_errors=True)
            self.runtime_dir = None

    def _stop_gnss_process(self) -> None:
        """
        Stop `gnss-sdr` and any children it may have spawned.

        `start_new_session=True` gives the process its own group, so we can
        terminate/kill the entire GNSS subtree in one call.
        """
        if not self.gnss_process:
            return

        proc = self.gnss_process
        pid = getattr(proc, "pid", None)

        if pid:
            try:
                os.killpg(pid, py_signal.SIGTERM)
            except ProcessLookupError:
                pass
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
        else:
            try:
                proc.terminate()
            except Exception:
                pass

        try:
            proc.wait(timeout=5)
        except Exception:
            if pid:
                try:
                    os.killpg(pid, py_signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            else:
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                proc.wait(timeout=1)
            except Exception:
                pass

    def run(self):
        setproctitle.setproctitle(f"DynamiX-Labs - GNSS Decoder (VFO {self.vfo})")
        self.telemetry_parser = TelemetryParser()

        self.stats: Dict[str, Any] = {
            "iq_chunks_in": 0,
            "samples_in": 0,
            "samples_written_to_input": 0,
            "input_write_drops": 0,
            "input_blocking_retries": 0,
            "input_partial_write_events": 0,
            "input_write_errors": 0,
            "samples_dropped_out_of_band": 0,
            "queue_timeouts": 0,
            "udp_packets_total": 0,
            "udp_packets_monitor": 0,
            "udp_packets_acquisition": 0,
            "udp_packets_tracking": 0,
            "udp_packets_pvt": 0,
            "udp_monitor_observations": 0,
            "udp_parse_errors": 0,
            "udp_events_emitted": 0,
            "udp_events_suppressed": 0,
            "activity_heartbeats_emitted": 0,
            "loss_of_lock_total": 0,
            "data_messages_out": 0,
            "last_activity": None,
            "errors": 0,
            "cpu_percent": 0.0,
            "memory_mb": 0.0,
            "memory_percent": 0.0,
        }

        process = psutil.Process()
        last_cpu_check = time.time()
        last_stats_time = time.time()
        last_monitor_poll = time.time()

        try:
            # Emit an explicit startup status so the VFO marker secondary label can
            # show "STARTING" while GNSS-SDR runtime/config bootstrapping is in progress.
            self._send_status_update(
                DecoderStatus.STARTING,
                {
                    "phase": "initializing",
                },
            )

            if shutil.which("gnss-sdr") is None:
                self._send_status_update(
                    DecoderStatus.ERROR,
                    {"error": "gnss-sdr binary not found in PATH"},
                )
                return

            # Wait for the first valid IQ chunk to define sample-rate-dependent config.
            first_chunk = None
            while self.running.value == 1 and first_chunk is None:
                try:
                    candidate = self.iq_queue.get(timeout=0.2)
                    samples = candidate.get("samples")
                    if samples is not None and len(samples) > 0:
                        first_chunk = candidate
                except queue.Empty:
                    continue

            if first_chunk is None:
                return

            sdr_rate = float(first_chunk.get("sample_rate") or 0.0)
            if sdr_rate <= 0:
                self._send_status_update(
                    DecoderStatus.ERROR, {"error": "Invalid SDR sample rate in IQ stream"}
                )
                return

            vfo_states = first_chunk.get("vfo_states", {})
            vfo_state = vfo_states.get(self.vfo, {})
            vfo_bandwidth = float(vfo_state.get("bandwidth", sdr_rate))
            self._configure_sample_rate_path(sdr_rate, vfo_bandwidth)
            self._prepare_runtime()

            self.gnss_process = subprocess.Popen(
                ["gnss-sdr", f"--config_file={self.config_path}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                cwd=self.runtime_dir,
                start_new_session=True,
            )
            self.gnss_stdout_thread = threading.Thread(
                target=self._read_gnss_stdout, daemon=True, name=f"gnss-sdr-log-{self.vfo}"
            )
            self.gnss_stdout_thread.start()

            if self.zmq_startup_delay_s > 0.0:
                time.sleep(self.zmq_startup_delay_s)

            self._send_status_update(
                DecoderStatus.LISTENING,
                {
                    "gnss_config_file": self.config_path,
                    "gnss_runtime_dir": self.runtime_dir,
                    "gnss_input_transport": self.gnss_input_transport,
                    "gnss_zmq_endpoint": self.zmq_endpoint,
                    "monitor_udp_ports": dict(self.monitor_ports),
                },
            )

            pending_chunk = first_chunk

            while self.running.value == 1:
                now = time.time()

                if now - last_cpu_check >= 0.5:
                    try:
                        with self.stats_lock:
                            self.stats["cpu_percent"] = process.cpu_percent()
                            self.stats["memory_mb"] = process.memory_info().rss / (1024 * 1024)
                            self.stats["memory_percent"] = process.memory_percent()
                    except Exception:
                        pass
                    last_cpu_check = now

                if now - last_stats_time >= 1.0:
                    if (
                        now - self._last_activity_heartbeat_ts
                    ) >= self._activity_heartbeat_interval_s:
                        self._emit_activity_heartbeat(now)
                    self._send_stats_update()
                    last_stats_time = now

                if now - last_monitor_poll >= 0.2:
                    self._poll_monitor_updates()
                    self._poll_gnss_log_updates()
                    last_monitor_poll = now

                if self.gnss_process and self.gnss_process.poll() is not None:
                    self._send_status_update(
                        DecoderStatus.ERROR,
                        {"error": f"gnss-sdr exited with code {self.gnss_process.returncode}"},
                    )
                    break

                if pending_chunk is not None:
                    iq_message = pending_chunk
                    pending_chunk = None
                else:
                    try:
                        iq_message = self.iq_queue.get(timeout=0.1)
                    except queue.Empty:
                        with self.stats_lock:
                            self.stats["queue_timeouts"] += 1
                        continue

                samples = iq_message.get("samples")
                if samples is None or len(samples) == 0:
                    continue

                sdr_center = float(
                    iq_message.get("logical_center_freq_hz", iq_message.get("center_freq", 0.0))
                )
                sdr_rate = float(iq_message.get("sample_rate") or self.sdr_sample_rate or 0.0)
                if sdr_rate <= 0:
                    continue

                vfo_states = iq_message.get("vfo_states", {})
                vfo_state_dict = vfo_states.get(self.vfo)
                if not vfo_state_dict or not vfo_state_dict.get("active", False):
                    continue

                self.cached_vfo_state = vfo_state_dict
                vfo_center = float(vfo_state_dict.get("center_freq", sdr_center))
                vfo_bandwidth = float(vfo_state_dict.get("bandwidth", sdr_rate))

                in_band, _, _ = self._is_vfo_in_sdr_bandwidth(vfo_center, sdr_center, sdr_rate)
                if not in_band:
                    with self.stats_lock:
                        self.stats["iq_chunks_in"] += 1
                        self.stats["samples_in"] += len(samples)
                        self.stats["samples_dropped_out_of_band"] += len(samples)
                        self.stats["last_activity"] = time.time()
                    continue

                if self.sdr_sample_rate is None:
                    self.sdr_sample_rate = sdr_rate
                    self.sdr_center_freq = sdr_center

                centered = self._frequency_translate(samples, vfo_center - sdr_center, sdr_rate)
                decimated = self._decimate_iq(centered)

                payload = np.ascontiguousarray(decimated, dtype=np.complex64).tobytes()
                (
                    wrote_samples,
                    dropped_samples,
                    input_retries,
                    partial_write_events,
                    input_write_errors,
                ) = self._write_zmq_payload(payload, int(decimated.size))

                with self.stats_lock:
                    self.stats["iq_chunks_in"] += 1
                    self.stats["samples_in"] += len(samples)
                    self.stats["samples_written_to_input"] += wrote_samples
                    self.stats["input_write_drops"] += dropped_samples
                    self.stats["input_blocking_retries"] += input_retries
                    self.stats["input_partial_write_events"] += partial_write_events
                    self.stats["input_write_errors"] += input_write_errors
                    self.stats["last_activity"] = time.time()

                # Periodic warning keeps runtime visibility when IQ continuity degrades.
                if dropped_samples > 0 and (now - self._last_input_drop_log_ts) >= 2.0:
                    self._last_input_drop_log_ts = now
                    logger.warning(
                        "GNSS ZMQ input dropped %d samples (retries=%d, partial=%d, errors=%d, vfo=%s)",
                        dropped_samples,
                        input_retries,
                        partial_write_events,
                        input_write_errors,
                        self.vfo,
                    )

                # Shared-memory monitor hook from BaseDecoderProcess.
                if self.stats["iq_chunks_in"] % 200 == 0:
                    self._monitor_shared_memory()

        except Exception as e:
            logger.error(f"GNSS decoder error: {e}")
            logger.exception(e)
            try:
                with self.stats_lock:
                    self.stats["errors"] += 1
            except Exception:
                pass
            self._send_status_update(DecoderStatus.ERROR, {"error": str(e)})
        finally:
            self._cleanup_runtime()
            self._send_status_update(DecoderStatus.CLOSED)
