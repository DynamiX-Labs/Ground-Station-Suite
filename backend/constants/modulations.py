#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulation Type Constants

Standardized modulation type names and display formats.
Use these constants throughout the application for consistent representation.
"""


# Modulation type internal keys (lowercase)
class ModulationType:
    LORA = "lora"
    FSK = "fsk"
    GFSK = "gfsk"
    GMSK = "gmsk"
    BPSK = "bpsk"
    QPSK = "qpsk"
    MSK = "msk"
    AFSK = "afsk"
    AM = "am"
    FM = "fm"
    SSB = "ssb"
    CW = "cw"
    OOK = "ook"
    DOKA = "doka"


# Display names for modulations (proper capitalization)
MODULATION_DISPLAY = {
    ModulationType.LORA: "LoRa",
    ModulationType.FSK: "FSK",
    ModulationType.GFSK: "GFSK",
    ModulationType.GMSK: "GMSK",
    ModulationType.BPSK: "BPSK",
    ModulationType.QPSK: "QPSK",
    ModulationType.MSK: "MSK",
    ModulationType.AFSK: "AFSK",
    ModulationType.AM: "AM",
    ModulationType.FM: "FM",
    ModulationType.SSB: "SSB",
    ModulationType.CW: "CW",
    ModulationType.OOK: "OOK",
    ModulationType.DOKA: "DOKA",
}


def get_modulation_display(modulation_type: str) -> str:
    """
    Get display name for a modulation type with proper capitalization.

    Args:
        modulation_type: Modulation type (case-insensitive)

    Returns:
        Display name with proper capitalization (e.g., 'LoRa', 'FSK')
    """
    if not modulation_type:
        return ""

    key = modulation_type.lower()
    return MODULATION_DISPLAY.get(key, modulation_type.upper())


def is_valid_modulation(modulation_type: str) -> bool:
    """
    Check if a modulation type is valid.

    Args:
        modulation_type: Modulation type to check

    Returns:
        True if valid, False otherwise
    """
    if not modulation_type:
        return False

    key = modulation_type.lower()
    return key in MODULATION_DISPLAY


# Modulation categories
class ModulationCategory:
    DIGITAL = "digital"
    ANALOG = "analog"
    SPREAD_SPECTRUM = "spread_spectrum"


def get_modulation_category(modulation_type: str) -> str:
    """
    Get category for a modulation type.

    Args:
        modulation_type: Modulation type

    Returns:
        Category string
    """
    if not modulation_type:
        return ModulationCategory.DIGITAL

    key = modulation_type.lower()

    if key == ModulationType.LORA:
        return ModulationCategory.SPREAD_SPECTRUM

    if key in [
        ModulationType.FSK,
        ModulationType.GFSK,
        ModulationType.GMSK,
        ModulationType.BPSK,
        ModulationType.QPSK,
        ModulationType.MSK,
        ModulationType.AFSK,
        ModulationType.OOK,
        ModulationType.DOKA,
    ]:
        return ModulationCategory.DIGITAL

    if key in [ModulationType.AM, ModulationType.FM, ModulationType.SSB, ModulationType.CW]:
        return ModulationCategory.ANALOG

    return ModulationCategory.DIGITAL
