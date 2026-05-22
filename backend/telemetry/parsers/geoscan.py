#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GEOSCAN Telemetry Parser

Parses GEOSCAN beacon payloads (post-deframe, post-PN9, post-CRC) into
engineering units such as voltages and temperatures.

Notes:
- GEOSCAN beacons are fixed-length (commonly 66 or 74 bytes).
- Field layouts differ between satellites; use the PDF/repo tables to
  populate the layouts below. The structure here supports easy updates
  without code changes.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, cast

from ..payloadanalyzers import PayloadAnalyzer


@dataclass(frozen=True)
class Field:
    name: str
    offset: int
    ftype: str  # 'u8','i8','u16','i16','u32','i32'
    scale: float = 1.0
    bias: float = 0.0
    unit: Optional[str] = None


def _decode_int(payload: bytes, offset: int, ftype: str) -> int:
    # All known GEOSCAN payloads are little-endian
    fmt_map = {
        "u8": "<B",
        "i8": "<b",
        "u16": "<H",
        "i16": "<h",
        "u32": "<I",
        "i32": "<i",
    }
    fmt = fmt_map.get(ftype)
    if not fmt:
        raise ValueError(f"Unsupported field type: {ftype}")
    size = struct.calcsize(fmt)
    if offset + size > len(payload):
        raise ValueError(f"Field '{ftype}' at {offset} out of range for payload len {len(payload)}")
    return cast(int, struct.unpack(fmt, payload[offset : offset + size])[0])


class GeoscanParser:
    """
    Layout-driven parser for GEOSCAN payloads.

    Populate LAYOUTS with the official field tables (from the PDF and/or
    the two reference repos). Currently includes placeholders; decoding
    will fall back to generic analysis until layouts are filled in.
    """

    # Layouts can be keyed by (frame_size) or (satellite_name_lower)
    # Use precise per-satellite overrides when available.
    LAYOUTS: Dict[Any, List[Field]] = {
        # Generic GEOSCAN Type-I (74-byte frame → 72-byte payload)
        # Full payload includes AX.25 header (16), then ID + EPS + OBC + COMMu
        74: [
            # AX.25 header (destination 0..5, dest SSID 6, source 7..12, src SSID 13, control 14, pid 15)
            Field("ax25_control", 14, "u8"),
            Field("ax25_pid", 15, "u8"),
            # Mayak ID
            Field("mayak_id", 16, "u8"),
            # EPS
            Field("eps_time_unix_s", 17, "u32"),
            Field("eps_mode_enum", 21, "u8"),
            Field("eps_reserve_22", 22, "u8"),
            Field("eps_current_platform_a", 23, "u16", scale=0.001, unit="A"),
            Field("eps_current_solar_a", 25, "u16", scale=0.001, unit="A"),
            Field("v_cell_v", 27, "u16", scale=0.001, unit="V"),
            Field("v_pack_v", 29, "u16", scale=0.001, unit="V"),
            Field("eps_reserve_bitfield_31", 31, "u16"),
            Field("temp_bat1_c", 33, "i8", unit="°C"),
            Field("temp_bat2_c", 34, "i8", unit="°C"),
            Field("eps_reserve_35", 35, "u16"),
            Field("eps_reserve_bitfield_37", 37, "u8"),
            Field("eps_reserve_38", 38, "u16"),
            # OBC
            Field("obc_reserve_40", 40, "u16"),
            Field("obc_activity_raw", 42, "u8"),
            Field("temp_x_p_c", 43, "i8", unit="°C"),
            Field("temp_x_n_c", 44, "i8", unit="°C"),
            Field("temp_y_p_c", 45, "i8", unit="°C"),
            Field("temp_y_n_c", 46, "i8", unit="°C"),
            Field("gnss_sat_count", 47, "u8"),
            Field("obc_reserve_48_enum", 48, "u8"),
            Field("obc_reserve_49", 49, "u8"),
            Field("camera_media_files_count", 50, "u8"),
            Field("obc_reserve_51_enum", 51, "u8"),
            Field("obc_reserve_52_4b", 52, "u32"),
            # COMMu
            Field("commu_reserve_56_enum", 56, "u8"),
            Field("vbus_v", 57, "u16", scale=0.001, unit="V"),
            Field("commu_reserve_59", 59, "u16"),
            Field("rssi_last_dbm", 61, "i8"),
            Field("rssi_min_dbm", 62, "i8"),
            Field("commu_reserve_63", 63, "u8"),
            Field("commu_reserve_64", 64, "u8"),
            Field("tx_packets_count", 65, "u8"),
            Field("commu_reserve_66", 66, "u8"),
            Field("commu_reserve_67_enum", 67, "u8"),
            Field("commu_reserve_68_signed", 68, "i8"),
            Field("qso_received_count", 69, "u8"),
            Field("commu_reserve_70", 70, "u16"),
        ],
        # Generic GEOSCAN Type-I (66-byte frame → 64-byte payload)
        # Keep same structure but payload is shorter (info field ~48 bytes). Fields which overflow
        # the payload will be ignored by bounds checks in _decode_int.
        66: [
            Field("ax25_control", 14, "u8"),
            Field("ax25_pid", 15, "u8"),
            Field("mayak_id", 16, "u8"),
            Field("eps_time_unix_s", 17, "u32"),
            Field("eps_mode_enum", 21, "u8"),
            Field("eps_reserve_22", 22, "u8"),
            Field("eps_current_platform_a", 23, "u16", scale=0.001, unit="A"),
            Field("eps_current_solar_a", 25, "u16", scale=0.001, unit="A"),
            Field("v_cell_v", 27, "u16", scale=0.001, unit="V"),
            Field("v_pack_v", 29, "u16", scale=0.001, unit="V"),
            Field("eps_reserve_bitfield_31", 31, "u16"),
            Field("temp_bat1_c", 33, "i8", unit="°C"),
            Field("temp_bat2_c", 34, "i8", unit="°C"),
            # OBC (partial, within 64 bytes)
            Field("obc_reserve_40", 40, "u16"),
            Field("obc_activity_raw", 42, "u8"),
            Field("temp_x_p_c", 43, "i8", unit="°C"),
            Field("temp_x_n_c", 44, "i8", unit="°C"),
            Field("temp_y_p_c", 45, "i8", unit="°C"),
            Field("temp_y_n_c", 46, "i8", unit="°C"),
            Field("gnss_sat_count", 47, "u8"),
            Field("obc_reserve_48_enum", 48, "u8"),
            Field("obc_reserve_49", 49, "u8"),
            Field("camera_media_files_count", 50, "u8"),
        ],
        # GEOSCAN Type-I ax25-info view for 66-byte frames (AX.25 info is typically 48 bytes)
        # Offsets relative to the start of the AX.25 info field (length typically 48 bytes):
        # ID = 0; EPS = 1..23; OBC = 24..47 (no COMMu in 48 bytes window)
        ("ax25_info", 66): [
            # ID
            Field("mayak_id", 0, "u8"),
            # EPS
            Field("eps_time_unix_s", 1, "u32"),
            Field("eps_mode_enum", 5, "u8"),
            Field("eps_reserve_22", 6, "u8"),
            Field("eps_current_platform_a", 7, "u16", scale=0.001, unit="A"),
            Field("eps_current_solar_a", 9, "u16", scale=0.001, unit="A"),
            Field("v_cell_v", 11, "u16", scale=0.001, unit="V"),
            Field("v_pack_v", 13, "u16", scale=0.001, unit="V"),
            Field("eps_reserve_bitfield_31", 15, "u16"),
            Field("temp_bat1_c", 17, "i8", unit="°C"),
            Field("temp_bat2_c", 18, "i8", unit="°C"),
            Field("eps_reserve_35", 19, "u16"),
            Field("eps_reserve_bitfield_37", 21, "u8"),
            Field("eps_reserve_38", 22, "u16"),
            # OBC (fits within 48 bytes window 24..47)
            Field("obc_reserve_40", 24, "u16"),
            Field("obc_activity_raw", 26, "u8"),
            Field("temp_x_p_c", 27, "i8", unit="°C"),
            Field("temp_x_n_c", 28, "i8", unit="°C"),
            Field("temp_y_p_c", 29, "i8", unit="°C"),
            Field("temp_y_n_c", 30, "i8", unit="°C"),
            Field("gnss_sat_count", 31, "u8"),
            Field("obc_reserve_48_enum", 32, "u8"),
            Field("obc_reserve_49", 33, "u8"),
            Field("camera_media_files_count", 34, "u8"),
            Field("obc_reserve_51_enum", 35, "u8"),
            Field("obc_reserve_52_4b", 36, "u32"),
        ],
        # NEW: GEOSCAN Type-I ax25-info view (for 74-byte frames with AX.25 header)
        # Offsets relative to the start of the AX.25 info field (length typically 56 bytes):
        # ID = 0; EPS = 1..23; OBC = 24..39; COMMu = 40..55
        ("ax25_info", 74): [
            # ID
            Field("mayak_id", 0, "u8"),
            # EPS
            Field("eps_time_unix_s", 1, "u32"),
            Field("eps_mode_enum", 5, "u8"),
            Field("eps_reserve_22", 6, "u8"),
            Field("eps_current_platform_a", 7, "u16", scale=0.001, unit="A"),
            Field("eps_current_solar_a", 9, "u16", scale=0.001, unit="A"),
            Field("v_cell_v", 11, "u16", scale=0.001, unit="V"),
            Field("v_pack_v", 13, "u16", scale=0.001, unit="V"),
            Field("eps_reserve_bitfield_31", 15, "u16"),
            Field("temp_bat1_c", 17, "i8", unit="°C"),
            Field("temp_bat2_c", 18, "i8", unit="°C"),
            Field("eps_reserve_35", 19, "u16"),
            Field("eps_reserve_bitfield_37", 21, "u8"),
            Field("eps_reserve_38", 22, "u16"),
            # OBC
            Field("obc_reserve_40", 24, "u16"),
            Field("obc_activity_raw", 26, "u8"),
            Field("temp_x_p_c", 27, "i8", unit="°C"),
            Field("temp_x_n_c", 28, "i8", unit="°C"),
            Field("temp_y_p_c", 29, "i8", unit="°C"),
            Field("temp_y_n_c", 30, "i8", unit="°C"),
            Field("gnss_sat_count", 31, "u8"),
            Field("obc_reserve_48_enum", 32, "u8"),
            Field("obc_reserve_49", 33, "u8"),
            Field("camera_media_files_count", 34, "u8"),
            Field("obc_reserve_51_enum", 35, "u8"),
            Field("obc_reserve_52_4b", 36, "u32"),
            # COMMu (fits exactly within 56 bytes window 40..55)
            Field("commu_reserve_56_enum", 40, "u8"),
            Field("vbus_v", 41, "u16", scale=0.001, unit="V"),
            Field("commu_reserve_59", 43, "u16"),
            Field("rssi_last_dbm", 45, "i8"),
            Field("rssi_min_dbm", 46, "i8"),
            Field("commu_reserve_63", 47, "u8"),
            Field("commu_reserve_64", 48, "u8"),
            Field("tx_packets_count", 49, "u8"),
            Field("commu_reserve_66", 50, "u8"),
            Field("commu_reserve_67_enum", 51, "u8"),
            Field("commu_reserve_68_signed", 52, "i8"),
            Field("qso_received_count", 53, "u8"),
            Field("commu_reserve_70", 54, "u16"),
        ],
    }

    def parse(
        self,
        payload: bytes,
        sat_name: Optional[str] = None,
        norad: Optional[int] = None,
        frame_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "format": "geoscan",
            "length": len(payload),
        }

        # Guard: image packet structure (Section 3.1). Detect image syncword 0x316F6B6F at offset 13
        # (little-endian), which corresponds to bytes 6F 6B 6F 31.
        try:
            if len(payload) >= 17 and payload[13:17] == bytes([0x6F, 0x6B, 0x6F, 0x31]):
                result["warning"] = (
                    "GEOSCAN image packet detected (syncword 0x316F6B6F). "
                    "Image payload is not parsed by the housekeeping decoder."
                )
                return result
        except Exception:
            pass

        # Choose layout priority: exact satellite match → AX.25-info view (when applicable) → frame_size → none
        layout: Optional[List[Field]] = None
        if sat_name:
            key = (sat_name or "").strip().lower()
            layout = self.LAYOUTS.get(key)
        # Heuristic: if payload length <= 56 and caller hinted 74, we are likely parsing
        # the AX.25 info field from a 74-byte Type-I. Use the ax25-info layout.
        if layout is None and frame_size in (74,):
            try:
                if len(payload) <= 56 and ("ax25" in (sat_name or "").lower() or True):
                    layout = self.LAYOUTS.get(("ax25_info", 74))
            except Exception:
                pass
        if layout is None and frame_size is not None:
            layout = self.LAYOUTS.get(frame_size)

        if not layout:
            # No layout yet: provide helpful analysis and extract heuristic candidates
            result["warning"] = (
                "GEOSCAN payload layout not defined; showing generic analysis and heuristic "
                "candidates for voltages and temperatures. Populate LAYOUTS for exact values."
            )
            result["analysis"] = PayloadAnalyzer.analyze(payload)
            # Heuristic extraction: look for plausible millivolts and deci-degC in little-endian u16/i16
            candidates: Dict[str, Any] = {"voltages_v": [], "temperatures_c": []}
            # Voltages: u16 in [2500, 25000] mV → report V
            for i in range(0, max(0, len(payload) - 1), 2):
                try:
                    raw_u16 = struct.unpack_from("<H", payload, i)[0]
                    if 2500 <= raw_u16 <= 25000:
                        v = round(raw_u16 / 1000.0, 3)
                        candidates["voltages_v"].append(
                            {"offset": i, "value": v, "raw_mV": raw_u16}
                        )
                except Exception:
                    pass
            # Temperatures: i16 in [-400, 1250] deci-degrees → report °C
            for i in range(0, max(0, len(payload) - 1), 2):
                try:
                    raw_i16 = struct.unpack_from("<h", payload, i)[0]
                    if -400 <= raw_i16 <= 1250:
                        t = round(raw_i16 / 10.0, 1)
                        candidates["temperatures_c"].append(
                            {"offset": i, "value": t, "raw_deciC": raw_i16}
                        )
                except Exception:
                    pass

            # Deduplicate by offset and keep up to a reasonable number to avoid UI clutter
            def _dedup(items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
                seen = set()
                out: List[Dict[str, Any]] = []
                for it in items:
                    off = it.get("offset")
                    if off in seen:
                        continue
                    seen.add(off)
                    out.append(it)
                    if len(out) >= limit:
                        break
                return out

            candidates["voltages_v"] = _dedup(candidates["voltages_v"], limit=12)
            candidates["temperatures_c"] = _dedup(candidates["temperatures_c"], limit=12)
            result["candidates"] = candidates
            return result

        decoded: Dict[str, Any] = {}
        raw: Dict[str, int] = {}
        for field in layout:
            try:
                ival = _decode_int(payload, field.offset, field.ftype)
                value = ival * field.scale + field.bias
                # Round reasonable engineering values
                if field.unit in ("V", "A"):
                    value = round(value, 3)
                elif field.unit in ("°C", "C"):
                    value = round(value, 1)
                elif field.scale != 1.0 or field.bias != 0.0:
                    value = round(value, 3)
                decoded[field.name] = {"value": value, "unit": field.unit}
                raw[field.name + "_raw"] = ival
            except Exception as e:
                decoded[field.name] = {"error": str(e)}

        result["values"] = decoded
        result["raw_fields"] = raw
        return result
