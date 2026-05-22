/**
 * @license
 * Copyright (c) 2025 Efstratios Goudelis
 * Modifications and extensions Copyright (C) 2026 DynamiX-Labs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 */

/**
 * Modulation Type Constants
 *
 * Standardized modulation type names and display formats.
 * Use these constants throughout the application for consistent representation.
 */

export const ModulationType = {
    // Digital modulations
    LORA: 'lora',           // Internal key (lowercase for backend compatibility)
    FSK: 'fsk',
    GFSK: 'gfsk',
    GMSK: 'gmsk',
    BPSK: 'bpsk',
    QPSK: 'qpsk',
    MSK: 'msk',
    AFSK: 'afsk',

    // Analog modulations
    AM: 'am',
    FM: 'fm',
    SSB: 'ssb',
    CW: 'cw',

    // Other
    OOK: 'ook',
    DOKA: 'doka',          // DOKA (Doppler/Offset Keying with Amplitude modulation)
};

/**
 * Display names for modulations (proper capitalization)
 */
export const ModulationDisplay = {
    [ModulationType.LORA]: 'LoRa',
    [ModulationType.FSK]: 'FSK',
    [ModulationType.GFSK]: 'GFSK',
    [ModulationType.GMSK]: 'GMSK',
    [ModulationType.BPSK]: 'BPSK',
    [ModulationType.QPSK]: 'QPSK',
    [ModulationType.MSK]: 'MSK',
    [ModulationType.AFSK]: 'AFSK',
    [ModulationType.AM]: 'AM',
    [ModulationType.FM]: 'FM',
    [ModulationType.SSB]: 'SSB',
    [ModulationType.CW]: 'CW',
    [ModulationType.OOK]: 'OOK',
    [ModulationType.DOKA]: 'DOKA',
};

/**
 * Get display name for a modulation type
 * @param {string} modulationType - Modulation type (case-insensitive)
 * @returns {string} Display name with proper capitalization
 */
export function getModulationDisplay(modulationType) {
    if (!modulationType) return '';

    const key = modulationType.toLowerCase();
    return ModulationDisplay[key] || modulationType.toUpperCase();
}

/**
 * Check if a modulation type is valid
 * @param {string} modulationType - Modulation type to check
 * @returns {boolean}
 */
export function isValidModulation(modulationType) {
    if (!modulationType) return false;
    return Object.values(ModulationType).includes(modulationType.toLowerCase());
}

/**
 * Modulation categories for grouping
 */
export const ModulationCategory = {
    DIGITAL: 'digital',
    ANALOG: 'analog',
    SPREAD_SPECTRUM: 'spread_spectrum',
};

/**
 * Get category for a modulation type
 * @param {string} modulationType - Modulation type
 * @returns {string} Category
 */
export function getModulationCategory(modulationType) {
    if (!modulationType) return ModulationCategory.DIGITAL;

    const key = modulationType.toLowerCase();

    if (key === ModulationType.LORA) {
        return ModulationCategory.SPREAD_SPECTRUM;
    }

    if ([ModulationType.FSK, ModulationType.GFSK, ModulationType.GMSK,
         ModulationType.BPSK, ModulationType.QPSK, ModulationType.MSK,
         ModulationType.AFSK, ModulationType.OOK, ModulationType.DOKA].includes(key)) {
        return ModulationCategory.DIGITAL;
    }

    if ([ModulationType.AM, ModulationType.FM, ModulationType.SSB,
         ModulationType.CW].includes(key)) {
        return ModulationCategory.ANALOG;
    }

    return ModulationCategory.DIGITAL;
}

/**
 * Decoder type names (for backend compatibility)
 */
export const DecoderType = {
    LORA: 'lora',
    FSK: 'fsk',
    BPSK: 'bpsk',
    AFSK: 'afsk',
};

/**
 * Get decoder type display name
 * @param {string} decoderType - Decoder type
 * @returns {string} Display name
 */
export function getDecoderDisplay(decoderType) {
    return getModulationDisplay(decoderType);
}
