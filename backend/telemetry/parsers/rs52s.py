#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RS52S (STRATOSAT-TK 1) AX.25-encapsulated GEOSCAN telemetry parser

Many GEOSCAN missions encapsulate an AX.25 UI frame inside the GEOSCAN link-layer.
Our AX.25 parser already removes the 16-byte AX.25 header and passes the "info"
field as payload. This module decodes that payload into engineering units for
RS52S based on the commonly used community mapping (aligned with the Edelveis
decoder reference). Units and scales are chosen to match published decoders.

Layout (byte offsets relative to AX.25 payload start):
  0..3   uint32_le  unix_time_s
  4..5   uint16_le  battery_current_a = raw * 7.66e-5
  6..7   uint16_le  panel_current_a   = raw * 3.076e-5
  8..9   uint16_le  v_one_cell_v      = raw * 6.928e-5
  10..11 uint16_le  v_pack_v          = raw * 1.3856e-4
  12     int8       temp_x_p_c
  13     int8       temp_x_n_c
  14     int8       temp_y_p_c
  15     int8       temp_y_n_c
  16     (often z_p, sometimes unused)
  17     int8       temp_z_n_c
  18     int8       temp_bat1_c
  19     int8       temp_bat2_c
  20     int8       cpu_load_pct = raw * 0.390625
  21..22 int16_le   obc_counter = raw - 7476
  23..24 int16_le   comm_counter = raw - 1505
  25     int8       rssi_dbm = raw - 99

This mapping is derived from open-source decoders and field observations. If
future frames show deviations, we can add per-satellite overrides.
"""

from __future__ import annotations

import struct
from datetime import datetime
from typing import Any, Dict, cast


class RS52SGeoscanAx25Parser:
    """
    Decode RS52S AX.25 payload into engineering units.
    Expects the pure AX.25 info field bytes (no AX.25 addresses/control/PID).
    """

    def parse(self, payload: bytes) -> Dict[str, Any]:
        out: Dict[str, Any] = {"satellite": "RS52S", "length": len(payload)}

        def u16le(off: int) -> int:
            return cast(int, struct.unpack_from("<H", payload, off)[0])

        def i16le(off: int) -> int:
            return cast(int, struct.unpack_from("<h", payload, off)[0])

        def u32le(off: int) -> int:
            return cast(int, struct.unpack_from("<I", payload, off)[0])

        def i8(off: int) -> int:
            return cast(int, struct.unpack_from("<b", payload, off)[0])

        if len(payload) < 26:
            out["error"] = "payload too short for RS52S mapping"
            return out

        # Timestamps
        ts = u32le(0)
        out["time_unix_s"] = ts
        try:
            out["time_utc"] = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

        # Currents
        batt_i = u16le(4) * 0.0000766
        panel_i = u16le(6) * 0.00003076

        # Voltages
        v_one_cell = u16le(8) * 0.00006928
        v_pack = u16le(10) * 0.00013856

        # Temperatures (signed int8, Celsius)
        t_x_p = i8(12)
        t_x_n = i8(13)
        t_y_p = i8(14)
        t_y_n = i8(15)
        # 16 often unused/z_p
        t_z_n = i8(17)
        t_bat1 = i8(18)
        t_bat2 = i8(19)

        # CPU load
        cpu_pct = i8(20) * 0.390625

        # Counters and RSSI
        obc_cnt = i16le(21) - 7476
        comm_cnt = i16le(23) - 1505
        rssi_dbm = i8(25) - 99

        out["values"] = {
            "battery_current_a": round(batt_i, 4),
            "panel_current_a": round(panel_i, 4),
            "v_cell_v": round(v_one_cell, 3),
            "v_pack_v": round(v_pack, 3),
            "temp_x_p_c": t_x_p,
            "temp_x_n_c": t_x_n,
            "temp_y_p_c": t_y_p,
            "temp_y_n_c": t_y_n,
            "temp_z_n_c": t_z_n,
            "temp_bat1_c": t_bat1,
            "temp_bat2_c": t_bat2,
            "cpu_load_pct": round(cpu_pct, 1),
            "obc_counter": obc_cnt,
            "comm_counter": comm_cnt,
            "rssi_dbm": rssi_dbm,
        }

        out["raw_fields"] = {
            "time_unix_s": ts,
            "battery_current_raw": u16le(4),
            "panel_current_raw": u16le(6),
            "v_cell_raw": u16le(8),
            "v_pack_raw": u16le(10),
        }

        return out


__all__ = ["RS52SGeoscanAx25Parser"]
