# Ground Station - GNSS monitor UDP receiver
# SPDX-License-Identifier: GPL-3.0-or-later

import socket
import struct
from typing import Any, Dict, List, Optional, Tuple


class ProtobufParseError(ValueError):
    """Raised when a protobuf datagram cannot be parsed safely."""


def _read_varint(data: bytes, index: int) -> Tuple[int, int]:
    value = 0
    shift = 0
    while index < len(data):
        byte = data[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            return value, index
        shift += 7
        if shift > 63:
            break
    raise ProtobufParseError("Invalid or truncated protobuf varint")


def _skip_wire_value(data: bytes, index: int, wire_type: int) -> int:
    if wire_type == 0:
        _, index = _read_varint(data, index)
        return index
    if wire_type == 1:
        if index + 8 > len(data):
            raise ProtobufParseError("Truncated 64-bit wire value")
        return index + 8
    if wire_type == 2:
        length, index = _read_varint(data, index)
        end = index + length
        if end > len(data):
            raise ProtobufParseError("Truncated length-delimited value")
        return end
    if wire_type == 5:
        if index + 4 > len(data):
            raise ProtobufParseError("Truncated 32-bit wire value")
        return index + 4
    raise ProtobufParseError(f"Unsupported protobuf wire type: {wire_type}")


def _read_double(data: bytes, index: int) -> Tuple[float, int]:
    end = index + 8
    if end > len(data):
        raise ProtobufParseError("Truncated protobuf double")
    return struct.unpack("<d", data[index:end])[0], end


def _read_string(data: bytes, index: int) -> Tuple[str, int]:
    length, index = _read_varint(data, index)
    end = index + length
    if end > len(data):
        raise ProtobufParseError("Truncated protobuf string")
    return data[index:end].decode("utf-8", errors="ignore"), end


def parse_observables_packet(data: bytes) -> List[Dict[str, Any]]:
    """
    Parse gnss_sdr.Observables protobuf payload.

    Observables contains repeated GnssSynchro entries in field #1.
    We parse only fields needed by Ground Station UI/telemetry.
    """
    observations: List[Dict[str, Any]] = []
    index = 0
    while index < len(data):
        key, index = _read_varint(data, index)
        field_number = key >> 3
        wire_type = key & 0x7

        if field_number == 1 and wire_type == 2:
            msg_len, index = _read_varint(data, index)
            end = index + msg_len
            if end > len(data):
                raise ProtobufParseError("Truncated GnssSynchro message")
            obs = parse_gnss_synchro_message(data[index:end])
            index = end
            if obs:
                observations.append(obs)
            continue

        index = _skip_wire_value(data, index, wire_type)

    return observations


def parse_observable_datagram(data: bytes) -> List[Dict[str, Any]]:
    """
    Parse a UDP datagram carrying observable content.

    GNSS-SDR builds may emit either:
    1) `Observables` with repeated GnssSynchro entries, or
    2) a single raw GnssSynchro message.
    """
    observations = parse_observables_packet(data)
    if observations:
        return observations

    # Fallback for builds that publish bare GnssSynchro payloads.
    single = parse_gnss_synchro_message(data)
    if single and (
        single.get("prn") is not None
        or single.get("channel_id") is not None
        or single.get("flag_valid_acquisition") is not None
        or single.get("flag_valid_symbol_output") is not None
        or single.get("flag_valid_word") is not None
    ):
        return [single]
    return []


def parse_gnss_synchro_message(data: bytes) -> Dict[str, Any]:
    index = 0
    obs: Dict[str, Any] = {}

    while index < len(data):
        key, index = _read_varint(data, index)
        field_number = key >> 3
        wire_type = key & 0x7

        if field_number == 1 and wire_type == 2:
            obs["system"], index = _read_string(data, index)
        elif field_number == 2 and wire_type == 2:
            obs["signal"], index = _read_string(data, index)
        elif field_number == 3 and wire_type == 0:
            obs["prn"], index = _read_varint(data, index)
        elif field_number == 4 and wire_type == 0:
            channel, index = _read_varint(data, index)
            # int32 over varint, keep positive channel IDs as-is.
            if channel >= 2**31:
                channel -= 2**32
            obs["channel_id"] = channel
        elif field_number == 9 and wire_type == 0:
            value, index = _read_varint(data, index)
            obs["flag_valid_acquisition"] = bool(value)
        elif field_number == 13 and wire_type == 1:
            obs["cn0_db_hz"], index = _read_double(data, index)
        elif field_number == 14 and wire_type == 1:
            obs["carrier_doppler_hz"], index = _read_double(data, index)
        elif field_number == 18 and wire_type == 0:
            value, index = _read_varint(data, index)
            obs["flag_valid_symbol_output"] = bool(value)
        elif field_number == 20 and wire_type == 0:
            value, index = _read_varint(data, index)
            obs["flag_valid_word"] = bool(value)
        else:
            index = _skip_wire_value(data, index, wire_type)

    return obs


def parse_monitor_pvt_packet(data: bytes) -> Dict[str, Any]:
    """
    Parse gnss_sdr.MonitorPvt protobuf payload.

    Only fields currently used by backend/UI are extracted.
    """
    index = 0
    pvt: Dict[str, Any] = {}

    while index < len(data):
        key, index = _read_varint(data, index)
        field_number = key >> 3
        wire_type = key & 0x7

        if field_number == 17 and wire_type == 1:
            pvt["latitude"], index = _read_double(data, index)
        elif field_number == 18 and wire_type == 1:
            pvt["longitude"], index = _read_double(data, index)
        elif field_number == 19 and wire_type == 1:
            pvt["height"], index = _read_double(data, index)
        elif field_number == 20 and wire_type == 0:
            pvt["valid_sats"], index = _read_varint(data, index)
        elif field_number == 21 and wire_type == 0:
            pvt["solution_status"], index = _read_varint(data, index)
        elif field_number == 30 and wire_type == 2:
            pvt["utc_time"], index = _read_string(data, index)
        else:
            index = _skip_wire_value(data, index, wire_type)

    return pvt


class GnssUdpMonitorReceiver:
    """Non-blocking UDP receiver for GNSS-SDR monitor streams."""

    STREAM_MONITOR = "monitor"
    STREAM_ACQUISITION = "acquisition"
    STREAM_TRACKING = "tracking"
    STREAM_PVT = "pvt"

    def __init__(self, bind_host: str = "0.0.0.0", port_map: Optional[Dict[str, int]] = None):
        self.bind_host = bind_host
        requested = port_map or {}

        self.sockets: Dict[str, socket.socket] = {}
        self.ports: Dict[str, int] = {}
        self.stats: Dict[str, int] = {
            "packets_total": 0,
            "packets_monitor": 0,
            "packets_acquisition": 0,
            "packets_tracking": 0,
            "packets_pvt": 0,
            "parse_errors": 0,
        }

        self._open_socket(self.STREAM_MONITOR, requested.get(self.STREAM_MONITOR, 0))
        self._open_socket(self.STREAM_ACQUISITION, requested.get(self.STREAM_ACQUISITION, 0))
        self._open_socket(self.STREAM_TRACKING, requested.get(self.STREAM_TRACKING, 0))
        self._open_socket(self.STREAM_PVT, requested.get(self.STREAM_PVT, 0))

    def _open_socket(self, stream: str, port: int) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.bind_host, int(port)))
        sock.setblocking(False)
        self.sockets[stream] = sock
        self.ports[stream] = int(sock.getsockname()[1])

    def close(self) -> None:
        for sock in self.sockets.values():
            try:
                sock.close()
            except OSError:
                pass
        self.sockets.clear()

    def snapshot_stats(self) -> Dict[str, int]:
        return dict(self.stats)

    def poll(self, max_packets_per_stream: int = 200) -> Dict[str, List[Dict[str, Any]]]:
        messages: Dict[str, List[Dict[str, Any]]] = {
            self.STREAM_MONITOR: [],
            self.STREAM_ACQUISITION: [],
            self.STREAM_TRACKING: [],
            self.STREAM_PVT: [],
        }

        for stream, sock in self.sockets.items():
            packets = 0
            while packets < max_packets_per_stream:
                try:
                    payload, _ = sock.recvfrom(65535)
                except BlockingIOError:
                    break
                except OSError:
                    self.stats["parse_errors"] += 1
                    break

                packets += 1
                self.stats["packets_total"] += 1
                self.stats[f"packets_{stream}"] += 1

                try:
                    if stream == self.STREAM_PVT:
                        parsed_pvt = parse_monitor_pvt_packet(payload)
                        if parsed_pvt:
                            messages[stream].append(parsed_pvt)
                    else:
                        for obs in parse_observable_datagram(payload):
                            if obs:
                                messages[stream].append(obs)
                except ProtobufParseError:
                    self.stats["parse_errors"] += 1

        return messages
