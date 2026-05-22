#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Constants package for Ground Station backend
"""

from .framing import (
    AX25_FRAMINGS,
    CCSDS_FRAMINGS,
    CSP_FRAMINGS,
    GR_SATELLITES_FRAMING_MAP,
    PROPRIETARY_FRAMINGS,
    FramingType,
    payload_protocol_from_framing,
)
from .modulations import (
    MODULATION_DISPLAY,
    ModulationCategory,
    ModulationType,
    get_modulation_category,
    get_modulation_display,
    is_valid_modulation,
)

__all__ = [
    "ModulationType",
    "MODULATION_DISPLAY",
    "get_modulation_display",
    "is_valid_modulation",
    "ModulationCategory",
    "get_modulation_category",
    "FramingType",
    "AX25_FRAMINGS",
    "CSP_FRAMINGS",
    "CCSDS_FRAMINGS",
    "PROPRIETARY_FRAMINGS",
    "GR_SATELLITES_FRAMING_MAP",
    "payload_protocol_from_framing",
]
