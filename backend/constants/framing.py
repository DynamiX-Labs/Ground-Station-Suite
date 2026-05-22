#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Framing protocol constants and helpers.

This module centralizes framing identifiers used across decoder config,
demodulators, and telemetry protocol routing.
"""

from typing import Optional


class FramingType:
    AX25 = "ax25"
    USP = "usp"
    GEOSCAN = "geoscan"
    DOKA = "doka"
    AX100_ASM = "ax100_asm"
    AX100_RS = "ax100_rs"
    AO40_FEC = "ao40_fec"
    AO40_FEC_SHORT = "ao40_fec_short"


AX25_FRAMINGS = {FramingType.AX25, FramingType.USP}
CSP_FRAMINGS = {FramingType.AX100_ASM, FramingType.AX100_RS}
CCSDS_FRAMINGS = {FramingType.DOKA}
PROPRIETARY_FRAMINGS = {FramingType.GEOSCAN}


GR_SATELLITES_FRAMING_MAP = {
    "USP": FramingType.USP,
    "AX.25": FramingType.AX25,
    "AX.25 G3RUH": FramingType.AX25,
    "GEOSCAN": FramingType.GEOSCAN,
    "CCSDS Concatenated": FramingType.AX25,
    "CCSDS Reed-Solomon": FramingType.AX25,
    "CCSDS Uncoded": FramingType.AX25,
    # Keep current behavior for now: AO-40 entries map to AX.25 unless explicitly overridden.
    "AO-40 FEC": FramingType.AX25,
    "AO-40 FEC short": FramingType.AX25,
    "NGHam": FramingType.AX25,
    "NGHam no Reed Solomon": FramingType.AX25,
}


def payload_protocol_from_framing(framing: Optional[str], default: str = "ax25") -> str:
    """Map a framing protocol key to telemetry payload protocol family."""
    if framing in CCSDS_FRAMINGS:
        return "ccsds"
    if framing in AX25_FRAMINGS:
        return "ax25"
    if framing in CSP_FRAMINGS:
        return "csp"
    if framing in PROPRIETARY_FRAMINGS:
        return "proprietary"
    return default
