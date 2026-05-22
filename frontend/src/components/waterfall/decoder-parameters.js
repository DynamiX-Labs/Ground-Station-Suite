/**
 * @license
 * Copyright (c) 2025 Efstratios Goudelis
 * Modifications and extensions Copyright (C) 2026 DynamiX-Labs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 *
 */

/**
 * Decoder Parameter Definitions
 *
 * Defines all configurable parameters for each decoder type.
 * These parameters map to DecoderConfig fields in the backend and flow through:
 * Frontend VFO state → Socket → Backend VFOStateManager → DecoderConfigService → Decoder
 *
 * Parameter naming convention: {decoder}_{parameter_name}
 * E.g., lora_sf, fsk_baudrate, bpsk_differential
 *
 * Structure:
 * - label: Display name for UI
 * - description: Optional help text
 * - type: 'select' or 'switch'
 * - default: Default value
 * - options: Array of {value, label, tooltip?} for select type
 */

/**
 * LoRa Decoder Parameters
 * LoRa uses chirp spread spectrum modulation with configurable spreading factor,
 * bandwidth, and error correction parameters.
 */
export const LORA_PARAMETERS = {
    lora_sf: {
        label: 'Spreading Factor',
        description: 'Higher SF = longer range but slower data rate',
        type: 'select',
        default: 7,
        options: [
            { value: 7, label: 'SF7', tooltip: 'Fastest, shortest range' },
            { value: 8, label: 'SF8' },
            { value: 9, label: 'SF9' },
            { value: 10, label: 'SF10' },
            { value: 11, label: 'SF11' },
            { value: 12, label: 'SF12', tooltip: 'Slowest, longest range' }
        ]
    },
    lora_bw: {
        label: 'Bandwidth',
        description: 'Signal bandwidth in Hz',
        type: 'select',
        default: 125000,
        options: [
            { value: 62500, label: '62.5 kHz' },
            { value: 125000, label: '125 kHz' },
            { value: 250000, label: '250 kHz' },
            { value: 500000, label: '500 kHz' }
        ]
    },
    lora_cr: {
        label: 'Coding Rate',
        description: 'Forward error correction ratio',
        type: 'select',
        default: 1,
        options: [
            { value: 1, label: '4/5', tooltip: 'Least overhead, fastest' },
            { value: 2, label: '4/6' },
            { value: 3, label: '4/7' },
            { value: 4, label: '4/8', tooltip: 'Most overhead, most robust' }
        ]
    },
    lora_sync_word: {
        label: 'Sync Word',
        description: 'Network identifier for packet filtering',
        type: 'select',
        default: [0x08, 0x10],
        options: [
            { value: [0x12], label: '0x12 (18) - LoRaWAN Private Networks (also for Meshtastic)' },
            { value: [0x34], label: '0x34 (52) - LoRaWAN Public Networks' },
            { value: [0x08, 0x10], label: '0x08 0x10 (8, 16) - TinyGS Satellite Network' },
            { value: [], label: 'Auto-detect (accept all sync words)' }
        ],
        // Custom comparator for array values
        compare: (a, b) => JSON.stringify(a) === JSON.stringify(b)
    },
    lora_preamble_len: {
        label: 'Preamble Length',
        description: 'Number of preamble symbols',
        type: 'select',
        default: 8,
        options: [
            { value: 6, label: '6' },
            { value: 8, label: '8' },
            { value: 12, label: '12' },
            { value: 16, label: '16' }
        ]
    },
    lora_fldro: {
        label: 'Low Data Rate Optimization',
        description: 'Enable for SF11/SF12 with BW < 500kHz',
        type: 'switch',
        default: false
    }
};

/**
 * FSK/GMSK/GFSK Decoder Parameters
 * FSK family decoders (Frequency Shift Keying) use the same underlying demodulator
 * with different pulse shaping. All three share the same parameter set.
 */
export const FSK_PARAMETERS = {
    fsk_baudrate: {
        label: 'Baud Rate',
        description: 'Symbol rate in symbols/second',
        type: 'select',
        default: 9600,
        options: [
            { value: 50, label: '50 baud', tooltip: 'RTTY' },
            { value: 75, label: '75 baud', tooltip: 'RTTY' },
            { value: 110, label: '110 baud', tooltip: 'Old RTTY standard' },
            { value: 150, label: '150 baud', tooltip: 'RTTY' },
            { value: 200, label: '200 baud', tooltip: 'Legacy satellites' },
            { value: 300, label: '300 baud', tooltip: 'Low-speed satellite links' },
            { value: 600, label: '600 baud', tooltip: 'Low-speed satellite links' },
            { value: 1200, label: '1200 baud' },
            { value: 1250, label: '1250 baud' },
            { value: 2400, label: '2400 baud' },
            { value: 2500, label: '2500 baud' },
            { value: 4800, label: '4800 baud' },
            { value: 5000, label: '5000 baud' },
            { value: 9600, label: '9600 baud' },
            { value: 12500, label: '12500 baud' },
            { value: 19200, label: '19200 baud' },
            { value: 38400, label: '38400 baud', tooltip: 'High-speed UHF links' },
            { value: 57600, label: '57600 baud', tooltip: 'Very high-speed links' },
            { value: 115200, label: '115200 baud', tooltip: 'Extremely high-speed links' }
        ]
    },
    fsk_framing: {
        label: 'Framing Protocol',
        description: 'Data framing and error correction protocol',
        type: 'select',
        default: 'ax25',
        options: [
            { value: 'ax25', label: 'AX.25 (G3RUH)', tooltip: 'Amateur packet radio standard with G3RUH scrambler' },
            { value: 'usp', label: 'USP (FEC)', tooltip: 'Unified Space Protocol with Viterbi + Reed-Solomon FEC' },
            { value: 'geoscan', label: 'GEOSCAN', tooltip: 'GEOSCAN protocol with PN9 scrambling and CC11xx CRC' },
            { value: 'doka', label: 'DOKA (CCSDS)', tooltip: 'CCSDS concatenated frames (Russian satellites)' },
            { value: 'ax100_asm', label: 'AX100 (ASM+Golay)', tooltip: 'GomSpace AX100 with ASM sync and Golay FEC' },
            { value: 'ax100_rs', label: 'AX100 (Reed-Solomon)', tooltip: 'GomSpace AX100 with Reed-Solomon FEC' }
        ]
    },
    fsk_deviation: {
        label: 'Frequency Deviation',
        description: 'Auto-calculated based on baud rate if not specified',
        type: 'select',
        default: null,
        options: [
            { value: null, label: 'Auto (recommended)', tooltip: 'Automatically calculated: ~50% of baud rate' },
            { value: 125, label: '125 Hz' },
            { value: 300, label: '300 Hz' },
            { value: 312.5, label: '312.5 Hz' },
            { value: 500, label: '500 Hz' },
            { value: 560, label: '560 Hz' },
            { value: 562.5, label: '562.5 Hz' },
            { value: 565, label: '565 Hz' },
            { value: 575, label: '575 Hz' },
            { value: 600, label: '600 Hz' },
            { value: 625, label: '625 Hz' },
            { value: 750, label: '750 Hz' },
            { value: 800, label: '800 Hz' },
            { value: 1200, label: '1.2 kHz' },
            { value: 1250, label: '1.2 kHz' },
            { value: 1600, label: '1.6 kHz' },
            { value: 1800, label: '1.8 kHz' },
            { value: 2000, label: '2 kHz' },
            { value: 2400, label: '2.4 kHz' },
            { value: 2600, label: '2.6 kHz' },
            { value: 2700, label: '2.7 kHz' },
            { value: 3000, label: '3 kHz' },
            { value: 3125, label: '3.1 kHz' },
            { value: 3200, label: '3.2 kHz' },
            { value: 3500, label: '3.5 kHz' },
            { value: 4000, label: '4 kHz' },
            { value: 4800, label: '4.8 kHz' },
            { value: 5000, label: '5 kHz' },
            { value: 5400, label: '5.4 kHz' },
            { value: 7500, label: '7.5 kHz' },
            { value: 10000, label: '10 kHz' },
            { value: 15000, label: '15 kHz' },
            { value: 19200, label: '19.2 kHz' }
        ]
    },
    // GEOSCAN-specific parameters (conditionally shown)
    fsk_geoscan_frame_size: {
        label: 'GEOSCAN Frame Size',
        description: 'Frame size in bytes (satellite-specific)',
        type: 'select',
        default: 66,
        options: [
            { value: 66, label: '66 bytes', tooltip: 'Most common (e.g., GEOSCAN-Edelveis)' },
            { value: 74, label: '74 bytes', tooltip: 'Alternative frame size' }
        ],
        visibleWhen: (params) => params.fsk_framing === 'geoscan'
    }
};

/**
 * GMSK uses the same parameters as FSK
 * GMSK (Gaussian Minimum Shift Keying) is FSK with Gaussian pulse shaping and h=0.5
 *
 * Create GMSK-prefixed copies of FSK parameters
 */
export const GMSK_PARAMETERS = Object.entries(FSK_PARAMETERS).reduce((acc, [key, value]) => {
    const gmskKey = key.replace('fsk_', 'gmsk_');
    acc[gmskKey] = {
        ...value,
        // Update visibleWhen to use gmsk_ prefix
        visibleWhen: value.visibleWhen
            ? (params) => value.visibleWhen(
                Object.entries(params).reduce((p, [k, v]) => {
                    p[k.replace('gmsk_', 'fsk_')] = v;
                    return p;
                }, {})
            )
            : undefined
    };
    return acc;
}, {});

/**
 * GFSK uses the same parameters as FSK
 * GFSK (Gaussian Frequency Shift Keying) is FSK with Gaussian pulse shaping and h>0.5
 *
 * Create GFSK-prefixed copies of FSK parameters
 */
export const GFSK_PARAMETERS = Object.entries(FSK_PARAMETERS).reduce((acc, [key, value]) => {
    const gfskKey = key.replace('fsk_', 'gfsk_');
    acc[gfskKey] = {
        ...value,
        // Update visibleWhen to use gfsk_ prefix
        visibleWhen: value.visibleWhen
            ? (params) => value.visibleWhen(
                Object.entries(params).reduce((p, [k, v]) => {
                    p[k.replace('gfsk_', 'fsk_')] = v;
                    return p;
                }, {})
            )
            : undefined
    };
    return acc;
}, {});

/**
 * BPSK Decoder Parameters
 * BPSK (Binary Phase Shift Keying) modulates data by shifting carrier phase.
 * Supports coherent BPSK and non-coherent DBPSK (differential) modes.
 */
export const BPSK_PARAMETERS = {
    bpsk_baudrate: {
        label: 'Baud Rate',
        description: 'Symbol rate in symbols/second',
        type: 'select',
        default: 9600,
        options: [
            { value: 50, label: '50 baud', tooltip: 'RTTY' },
            { value: 75, label: '75 baud', tooltip: 'RTTY' },
            { value: 110, label: '110 baud', tooltip: 'Old RTTY standard' },
            { value: 150, label: '150 baud', tooltip: 'RTTY' },
            { value: 200, label: '200 baud', tooltip: 'Legacy satellites' },
            { value: 300, label: '300 baud', tooltip: 'Low-speed satellite links' },
            { value: 600, label: '600 baud', tooltip: 'Low-speed satellite links' },
            { value: 1200, label: '1200 baud' },
            { value: 1250, label: '1250 baud' },
            { value: 2400, label: '2400 baud' },
            { value: 2500, label: '2500 baud' },
            { value: 4800, label: '4800 baud' },
            { value: 5000, label: '5000 baud' },
            { value: 9600, label: '9600 baud' },
            { value: 12500, label: '12500 baud' },
            { value: 19200, label: '19200 baud' },
            { value: 38400, label: '38400 baud', tooltip: 'High-speed UHF links' },
            { value: 57600, label: '57600 baud', tooltip: 'Very high-speed links' },
            { value: 115200, label: '115200 baud', tooltip: 'Extremely high-speed links' }
        ]
    },
    bpsk_framing: {
        label: 'Framing Protocol',
        description: 'Data framing and error correction protocol',
        type: 'select',
        default: 'ax25',
        options: [
            { value: 'ax25', label: 'AX.25 (G3RUH)', tooltip: 'Amateur packet radio standard with G3RUH scrambler' },
            { value: 'doka', label: 'DOKA (CCSDS)', tooltip: 'CCSDS Reed-Solomon frames (e.g., Chomptt)' }
        ]
    },
    bpsk_differential: {
        label: 'Differential Mode (DBPSK)',
        description: 'Enable for non-coherent differential BPSK decoding',
        type: 'switch',
        default: false
    }
};

/**
 * AFSK Decoder Parameters
 * AFSK (Audio Frequency Shift Keying) modulates data onto an audio frequency carrier.
 * Used for FM-based packet radio (APRS, amateur satellites with FM transponders).
 */
export const AFSK_PARAMETERS = {
    afsk_baudrate: {
        label: 'Baud Rate',
        description: 'Symbol rate in symbols/second',
        type: 'select',
        default: 1200,
        options: [
            { value: 300, label: '300 baud', tooltip: 'Low-speed HF packet radio' },
            { value: 1143, label: '1143 baud', tooltip: 'Some satellites' },
            { value: 1200, label: '1200 baud', tooltip: 'Bell 202 (APRS, VHF packet radio)' },
            { value: 2400, label: '2400 baud', tooltip: 'Medium-speed packet radio' },
            { value: 2500, label: '2500 baud', tooltip: 'Some satellite links' },
            { value: 4800, label: '4800 baud', tooltip: 'High-speed VHF packet radio' },
            { value: 9600, label: '9600 baud', tooltip: 'G3RUH (UHF packet radio)' }
        ]
    },
    afsk_af_carrier: {
        label: 'Audio Carrier Frequency',
        description: 'Center frequency of the audio FSK tones',
        type: 'select',
        default: 1700,
        options: [
            { value: 1200, label: '1200 Hz', tooltip: 'VHF/UHF packet radio' },
            { value: 1700, label: '1700 Hz', tooltip: 'Bell 202 APRS standard' },
            { value: 2200, label: '2200 Hz', tooltip: 'Alternative carrier frequency' }
        ]
    },
    afsk_deviation: {
        label: 'Frequency Deviation',
        description: 'Audio frequency shift from carrier',
        type: 'select',
        default: 500,
        options: [
            { value: 500, label: '500 Hz', tooltip: 'Standard for 1200 baud (Bell 202)' },
            { value: 565, label: '565 Hz', tooltip: 'Some satellites' },
            { value: 1000, label: '1000 Hz', tooltip: 'Wide deviation for 1200 baud' },
            { value: 2400, label: '2400 Hz', tooltip: 'Standard for 9600 baud' },
            { value: 3000, label: '3000 Hz', tooltip: 'Wide deviation for 9600 baud' }
        ]
    },
    afsk_framing: {
        label: 'Framing Protocol',
        description: 'Data framing protocol',
        type: 'select',
        default: 'ax25',
        options: [
            { value: 'ax25', label: 'AX.25 (G3RUH)', tooltip: 'Amateur packet radio standard with G3RUH scrambler' }
        ]
    }
};

/**
 * SSTV Decoder Parameters
 * SSTV (Slow Scan Television) supports multiple transmission modes.
 * Mode can be auto-detected via VIS code or manually specified.
 */
export const SSTV_PARAMETERS = {
    sstv_mode: {
        label: 'SSTV Mode',
        description: 'SSTV transmission mode (auto-detect or manual)',
        type: 'select',
        default: 'auto',
        options: [
            { value: 'auto', label: 'Auto-detect (VIS code)', tooltip: 'Automatically detect mode from VIS signal' },
            { value: 'robot36', label: 'Robot 36', tooltip: '36 second color mode' },
            { value: 'robot72', label: 'Robot 72', tooltip: '72 second color mode' },
            { value: 'martin_m1', label: 'Martin M1', tooltip: '114 second color mode' },
            { value: 'martin_m2', label: 'Martin M2', tooltip: '58 second color mode' },
            { value: 'scottie_s1', label: 'Scottie S1', tooltip: '110 second color mode' },
            { value: 'scottie_s2', label: 'Scottie S2', tooltip: '71 second color mode' },
            { value: 'scottie_dx', label: 'Scottie DX', tooltip: '269 second color mode' },
            { value: 'pd50', label: 'PD 50', tooltip: '50 second color mode' },
            { value: 'pd90', label: 'PD 90', tooltip: '90 second color mode' },
            { value: 'pd120', label: 'PD 120', tooltip: '126 second color mode' },
            { value: 'pd160', label: 'PD 160', tooltip: '161 second color mode' },
            { value: 'pd180', label: 'PD 180', tooltip: '187 second color mode' },
            { value: 'pd240', label: 'PD 240', tooltip: '248 second color mode' },
            { value: 'pd290', label: 'PD 290', tooltip: '289 second color mode' },
            { value: 'wraase_sc2_180', label: 'Wraase SC2-180', tooltip: '180 second color mode' }
        ]
    }
};

/**
 * GNSS-SDR Decoder Parameters
 * GNSS decoder streams wideband L1 IQ into GNSS-SDR for multi-constellation processing.
 */
export const GNSS_PARAMETERS = {
    gnss_sample_rate: {
        label: 'GNSS Processing Rate',
        description: 'Target rate fed to GNSS-SDR. If SDR rate is higher, IQ is integer-downsampled after filtering (e.g., 4.0 -> 2.0 MS/s = /2). If SDR rate is lower, no upsampling is applied.',
        type: 'select',
        default: 4000000,
        options: [
            { value: 2000000, label: '2.0 MS/s' },
            { value: 2500000, label: '2.5 MS/s' },
            { value: 4000000, label: '4.0 MS/s' },
            { value: 5000000, label: '5.0 MS/s' }
        ]
    },
    gnss_total_channels: {
        label: 'Total Channels',
        description: 'Total acquisition/tracking channels shared across enabled constellations',
        type: 'select',
        default: 24,
        options: [
            { value: 8, label: '8' },
            { value: 12, label: '12' },
            { value: 16, label: '16' },
            { value: 24, label: '24' },
            { value: 32, label: '32' },
            { value: 48, label: '48' }
        ]
    },
    gnss_output_rate_ms: {
        label: 'PVT Update Rate',
        description: 'Navigation/PVT output interval',
        type: 'select',
        default: 500,
        options: [
            { value: 100, label: '100 ms' },
            { value: 200, label: '200 ms' },
            { value: 500, label: '500 ms' },
            { value: 1000, label: '1000 ms' }
        ]
    },
    gnss_doppler_max: {
        label: 'Max Doppler Search',
        description: 'Acquisition Doppler search window in Hz',
        type: 'select',
        default: 6000,
        options: [
            { value: 3000, label: '3 kHz' },
            { value: 4000, label: '4 kHz' },
            { value: 6000, label: '6 kHz' },
            { value: 8000, label: '8 kHz' },
            { value: 10000, label: '10 kHz' }
        ]
    },
    gnss_enable_gps: {
        label: 'GPS (L1 C/A)',
        type: 'switch',
        default: true
    },
    gnss_enable_galileo: {
        label: 'Galileo (E1B)',
        type: 'switch',
        default: true
    },
    gnss_enable_glonass: {
        label: 'GLONASS (L1 C/A)',
        type: 'switch',
        default: true
    },
    gnss_enable_beidou: {
        label: 'BeiDou (B1I)',
        type: 'switch',
        default: true
    },
    gnss_enable_qzss: {
        label: 'QZSS (L1 C/A)',
        type: 'switch',
        default: true
    }
};

/**
 * Decoder support flags
 * Use this map to disable unsupported decoders in the UI.
 */
export const DECODER_SUPPORT = {
    sstv: true,
    fsk: true,
    gmsk: true,
    gfsk: true,
    bpsk: true,
    apt: true,
    lora: false,
    morse: false,
    afsk: false,
    gnss: true
};

/**
 * SatDump Pipeline Definitions
 * Defines supported SatDump pipelines by satellite family.
 */
export const SATDUMP_PIPELINES = {
    meteor: {
        label: 'METEOR',
        description: 'SatDump pipelines for METEOR satellites',
        pipelines: [
            { value: 'meteor_m2-x_lrpt', label: 'METEOR-M2 LRPT' },
            { value: 'meteor_m2-x_lrpt_80k', label: 'METEOR-M2 LRPT (80k)' },
            { value: 'meteor_hrpt', label: 'METEOR HRPT' }
        ]
    },
    elektro: {
        label: 'ELEKTRO',
        description: 'SatDump pipelines for ELEKTRO-L',
        pipelines: [
            { value: 'elektro_lrit', label: 'ELEKTRO-L LRIT' },
            { value: 'elektro_hrit', label: 'ELEKTRO-L HRIT' }
        ]
    }
};

/**
 * Combined parameter definitions for all decoders
 */
export const DECODER_PARAMETERS = {
    ...LORA_PARAMETERS,
    ...FSK_PARAMETERS,
    ...GMSK_PARAMETERS,
    ...GFSK_PARAMETERS,
    ...BPSK_PARAMETERS,
    ...AFSK_PARAMETERS,
    ...GNSS_PARAMETERS,
    ...SSTV_PARAMETERS
};

/**
 * Get parameter definitions for a specific decoder
 * @param {string} decoder - Decoder name (e.g., 'lora', 'fsk', 'gmsk', 'gfsk', 'bpsk', 'sstv')
 * @returns {Object} Parameter definitions for this decoder
 */
export function getDecoderParameters(decoder) {
    const prefix = `${decoder}_`;
    return Object.entries(DECODER_PARAMETERS)
        .filter(([key]) => key.startsWith(prefix))
        .reduce((acc, [key, value]) => {
            acc[key] = value;
            return acc;
        }, {});
}

/**
 * Get default parameters for a specific decoder
 * @param {string} decoder - Decoder name
 * @returns {Object} Default parameter values
 */
export function getDecoderDefaultParameters(decoder) {
    const params = getDecoderParameters(decoder);
    return Object.entries(params).reduce((acc, [key, param]) => {
        acc[key] = param.default;
        return acc;
    }, {});
}

/**
 * Map frontend parameter names to backend names
 * Frontend uses prefixed flat keys (lora_sf), backend uses unprefixed names (sf)
 *
 * @param {string} decoder - Decoder name (e.g., 'lora', 'fsk', 'gmsk', 'gfsk', 'bpsk')
 * @param {Object} parameters - Frontend parameters object
 * @returns {Object} Backend-compatible parameters (for DecoderConfigService overrides)
 */
export function mapParametersToBackend(decoder, parameters) {
    if (decoder === 'lora') {
        return {
            sf: parameters.lora_sf,
            bw: parameters.lora_bw,
            cr: parameters.lora_cr,
            sync_word: parameters.lora_sync_word,
            preamble_len: parameters.lora_preamble_len,
            fldro: parameters.lora_fldro
        };
    }

    // FSK-family decoders (FSK, GMSK, GFSK) share the same parameter structure
    if (decoder === 'fsk' || decoder === 'gmsk' || decoder === 'gfsk') {
        const prefix = `${decoder}_`;
        const backendParams = {
            baudrate: parameters[`${prefix}baudrate`],
            framing: parameters[`${prefix}framing`],
            deviation: parameters[`${prefix}deviation`]
        };

        // Add framing-specific parameters
        const framing = parameters[`${prefix}framing`];
        if (framing === 'geoscan') {
            backendParams.framing_params = {
                frame_size: parameters[`${prefix}geoscan_frame_size`] || 66
            };
        }

        return backendParams;
    }

    if (decoder === 'bpsk') {
        return {
            baudrate: parameters.bpsk_baudrate,
            framing: parameters.bpsk_framing,
            differential: parameters.bpsk_differential
        };
    }

    if (decoder === 'afsk') {
        return {
            baudrate: parameters.afsk_baudrate,
            af_carrier: parameters.afsk_af_carrier,
            deviation: parameters.afsk_deviation,
            framing: parameters.afsk_framing
        };
    }

    if (decoder === 'gnss') {
        return {
            gnss_sample_rate: parameters.gnss_sample_rate ?? 4000000,
            gnss_total_channels: parameters.gnss_total_channels ?? 24,
            gnss_output_rate_ms: parameters.gnss_output_rate_ms ?? 500,
            gnss_doppler_max: parameters.gnss_doppler_max ?? 6000,
            gnss_enable_gps: parameters.gnss_enable_gps ?? true,
            gnss_enable_galileo: parameters.gnss_enable_galileo ?? true,
            gnss_enable_glonass: parameters.gnss_enable_glonass ?? true,
            gnss_enable_beidou: parameters.gnss_enable_beidou ?? true,
            gnss_enable_qzss: parameters.gnss_enable_qzss ?? true
        };
    }

    // SSTV and other decoders have no parameters
    return {};
}
