#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal CCSDS TM Space Packet primary header parser.

Parses the 6-byte primary header and returns fields plus remaining payload.
Does not attempt to parse secondary headers.
"""

from typing import Any, Dict


class CCSDSParser:
    def parse(self, packet: bytes) -> Dict[str, Any]:
        if len(packet) < 6:
            return {"success": False, "error": "Packet too short for CCSDS primary header"}

        b0, b1, b2, b3, b4, b5 = packet[0:6]

        version = (b0 & 0xE0) >> 5
        pkt_type = (b0 & 0x10) >> 4
        sec_hdr_flag = (b0 & 0x08) >> 3
        apid = ((b0 & 0x07) << 8) | b1

        seq_flags = (b2 & 0xC0) >> 6
        seq_count = ((b2 & 0x3F) << 8) | b3

        pkt_len = (b4 << 8) | b5  # this is (total_length - 1 - 6)

        primary_header = {
            "version": version,
            "type": pkt_type,
            "secondary_header_flag": sec_hdr_flag,
            "apid": apid,
            "sequence_flags": seq_flags,
            "sequence_count": seq_count,
            "packet_length_field": pkt_len,
        }

        # Compute payload length if consistent
        total_len_field = pkt_len + 1 + 6
        payload = packet[6:]

        return {
            "success": True,
            "primary_header": primary_header,
            "payload": payload,
            "length_check": (len(packet) == total_len_field) if len(packet) >= 6 else None,
        }
