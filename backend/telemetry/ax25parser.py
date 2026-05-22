#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AX.25 Frame Parser

Generic parser for AX.25 frames used by amateur radio satellites.
Based on gr-satellites implementation by Daniel Estevez.
"""

import re

from construct import (
    Adapter,
    BitsInteger,
    BitStruct,
    Bytes,
    Default,
    Flag,
    GreedyBytes,
    Hex,
    Int8ub,
    RepeatUntil,
    Struct,
)


class AX25Parser:
    """Parse AX.25 frames and extract header + payload"""

    # AX.25 SSID field
    SSID = BitStruct(
        "ch" / Flag,  # C / H bit
        Default(BitsInteger(2), 3),  # reserved bits
        "ssid" / BitsInteger(4),
        "extension" / Flag,  # last address bit
    )

    # Callsign adapter to decode shifted ASCII
    class CallsignAdapter(Adapter):
        def _decode(self, obj, context, path=None):
            return str(bytes([x >> 1 for x in obj]), encoding="ascii").replace("\x00", " ").strip()

    Callsign = CallsignAdapter(Bytes(6))

    # Address field (callsign + SSID)
    Address = Struct("callsign" / Callsign, "ssid" / SSID)

    # Complete AX.25 frame
    Frame = Struct(
        "addresses" / RepeatUntil(lambda x, lst, ctx: x.ssid.extension, Address),
        "control" / Hex(Int8ub),
        "pid" / Hex(Int8ub),
        "info" / GreedyBytes,
    )

    @classmethod
    def parse(cls, packet_bytes):
        """
        Parse AX.25 frame from bytes

        Args:
            packet_bytes: Raw packet bytes (without HDLC flags)

        Returns:
            dict with parsed frame data:
            {
                'destination': 'CALL-SSID',
                'source': 'CALL-SSID',
                'control': '0x03',
                'pid': '0xf0',
                'payload': bytes,
                'payload_hex': 'hexstring',
                'repeaters': ['CALL-SSID', ...]  # if present
            }
        """
        try:
            parsed = cls.Frame.parse(packet_bytes)

            # Extract callsigns
            dest_call = parsed.addresses[0].callsign
            src_call = parsed.addresses[1].callsign

            # Validate callsigns: AX.25 callsigns must be alphanumeric ASCII + space/dash
            # Valid examples: "W1AW  ", "ISS   ", "FOSSAT", "CQ    "
            if not re.match(r"^[A-Z0-9 -]{1,6}$", dest_call.strip()):
                return {
                    "success": False,
                    "error": f"Invalid destination callsign: '{dest_call}' (not valid AX.25 format)",
                    "error_type": "ValidationError",
                }
            if not re.match(r"^[A-Z0-9 -]{1,6}$", src_call.strip()):
                return {
                    "success": False,
                    "error": f"Invalid source callsign: '{src_call}' (not valid AX.25 format)",
                    "error_type": "ValidationError",
                }

            destination = f"{dest_call}-{parsed.addresses[0].ssid.ssid}"
            source = f"{src_call}-{parsed.addresses[1].ssid.ssid}"

            # Check for repeaters (digipeaters)
            repeaters = []
            if len(parsed.addresses) > 2:
                for i in range(2, len(parsed.addresses)):
                    repeater = f"{parsed.addresses[i].callsign}-{parsed.addresses[i].ssid.ssid}"
                    repeaters.append(repeater)

            return {
                "success": True,
                "destination": destination,
                "source": source,
                "control": f"0x{parsed.control:02x}",
                "pid": f"0x{parsed.pid:02x}",
                "payload": parsed.info,
                "payload_hex": parsed.info.hex(),
                "payload_length": len(parsed.info),
                "repeaters": repeaters if repeaters else None,
                "raw": {
                    "destination_callsign": dest_call,
                    "destination_ssid": parsed.addresses[0].ssid.ssid,
                    "source_callsign": src_call,
                    "source_ssid": parsed.addresses[1].ssid.ssid,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
