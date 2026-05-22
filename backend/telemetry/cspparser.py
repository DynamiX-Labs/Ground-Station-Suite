#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal CSP header parser (v1/v2 tolerant)

Parses the first 4 bytes (32-bit header) and returns a dictionary with
best-effort decoded fields and the remaining payload.

Note: Different CSP versions place fields differently. This parser
tries a v2-like mapping first and falls back to a v1-like mapping to
produce reasonable header fields for telemetry routing (e.g., dport).
"""

from typing import Any, Dict


class CSPParser:
    def parse(self, packet: bytes) -> Dict[str, Any]:
        if len(packet) < 4:
            return {"success": False, "error": "Packet too short for CSP header"}

        word = int.from_bytes(packet[0:4], byteorder="big", signed=False)

        # Try v2-ish mapping
        v2 = self._parse_v2_like(word)

        # Sanity check fields
        if self._looks_reasonable(v2, len(packet)):
            payload = packet[4:]
            return {"success": True, "headers": v2, "payload": payload}

        # Fallback to v1-ish mapping
        v1 = self._parse_v1_like(word)
        if self._looks_reasonable(v1, len(packet)):
            payload = packet[4:]
            return {"success": True, "headers": v1, "payload": payload}

        # If nothing looks right, still return something
        payload = packet[4:]
        return {
            "success": True,
            "headers": v2,
            "payload": payload,
            "warning": "Uncertain CSP mapping",
        }

    def _parse_v2_like(self, word: int) -> Dict[str, Any]:
        # Bit layout (approx):
        # [31:30]=prio (2), [29]=rdp, [28]=xtea, [27]=hmac, [26]=res
        # [25:21]=src (5), [20:16]=dst (5), [15:10]=dport (6), [9:4]=sport (6), [3:0]=len (4) or lower bits
        return {
            "prio": (word >> 30) & 0x3,
            "rdp": (word >> 29) & 0x1,
            "xtea": (word >> 28) & 0x1,
            "hmac": (word >> 27) & 0x1,
            "reserved": (word >> 26) & 0x1,
            "src": (word >> 21) & 0x1F,
            "dst": (word >> 16) & 0x1F,
            "dport": (word >> 10) & 0x3F,
            "sport": (word >> 4) & 0x3F,
            "length": word & 0xF,  # best-effort, may differ by version
            "raw_header": word,
            "version_guess": 2,
        }

    def _parse_v1_like(self, word: int) -> Dict[str, Any]:
        # v1 classic mapping (best-effort):
        # [31:30]=prio(2) [29:25]=src(5) [24:20]=dst(5) [19:14]=dport(6) [13:8]=sport(6) [7:0]=flags
        return {
            "prio": (word >> 30) & 0x3,
            "src": (word >> 25) & 0x1F,
            "dst": (word >> 20) & 0x1F,
            "dport": (word >> 14) & 0x3F,
            "sport": (word >> 8) & 0x3F,
            "flags": word & 0xFF,
            "raw_header": word,
            "version_guess": 1,
        }

    def _looks_reasonable(self, hdr: Dict[str, Any], total_len: int) -> bool:
        # dport and sport should be in 0..63 typically
        dport = hdr.get("dport")
        sport = hdr.get("sport")
        return (
            isinstance(dport, int)
            and isinstance(sport, int)
            and 0 <= dport <= 63
            and 0 <= sport <= 63
            and total_len >= 4
        )
