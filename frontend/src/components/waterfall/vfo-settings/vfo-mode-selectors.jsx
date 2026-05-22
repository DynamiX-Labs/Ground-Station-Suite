/**
 * VFO Mode Selectors Components
 *
 * Audio demodulation, data decoders, transcription, and bandwidth selectors
 */

import React from 'react';
import { Box, Typography, ToggleButtonGroup, ToggleButton, Link, Tooltip } from '@mui/material';
import SettingsIcon from '@mui/icons-material/Settings';
import { useTranslation } from 'react-i18next';
import { BANDWIDTHS, STEP_SIZES } from './vfo-constants.js';
import { DECODER_SUPPORT } from '../decoder-parameters.js';
import { formatDecoderParamsSummary } from './vfo-formatters.js';
import { isLockedBandwidth } from '../vfo-marker/vfo-config.js';

const sameIdentifier = (left, right) => {
    if (left == null || right == null) {
        return false;
    }
    return String(left) === String(right);
};

// Common toggle button styles
const toggleButtonStyles = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 0.5,
    '& .MuiToggleButton-root': {
        height: '28px',
        minWidth: '50px',
        padding: '4px 8px',
        fontSize: '0.75rem',
        border: '1px solid',
        borderColor: 'rgba(255, 255, 255, 0.23)',
        borderRadius: '4px',
        color: 'text.secondary',
        textAlign: 'center',
        textTransform: 'none',
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        transition: 'all 0.2s ease-in-out',
        '&.Mui-selected': {
            backgroundColor: 'primary.main',
            color: 'primary.contrastText',
            borderColor: 'primary.main',
            fontWeight: 600,
            boxShadow: '0 0 8px rgba(33, 150, 243, 0.4)',
            '&:hover': {
                backgroundColor: 'primary.dark',
                boxShadow: '0 0 12px rgba(33, 150, 243, 0.6)',
            }
        },
        '&:hover': {
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            borderColor: 'rgba(255, 255, 255, 0.4)',
        },
        '&.Mui-disabled': {
            backgroundColor: 'rgba(255, 255, 255, 0.02)',
            borderColor: 'rgba(255, 255, 255, 0.08)',
            color: 'rgba(255, 255, 255, 0.3)',
            opacity: 0.5,
        }
    }
};

/**
 * Step Size Selector Component
 */
export const StepSizeSelector = ({ vfoIndex, vfoActive, stepSize, onVFOPropertyChange }) => {
    const { t } = useTranslation('waterfall');

    return (
        <Box sx={{ mt: 1 }}>
            <Typography variant="body2" sx={{ mb: 1, color: 'text.secondary' }}>
                {t('vfo.step_size')}
            </Typography>
            <ToggleButtonGroup
                value={stepSize || 1000}
                exclusive
                disabled={!vfoActive}
                onChange={(event, newValue) => {
                    if (newValue !== null) {
                        onVFOPropertyChange(vfoIndex, { stepSize: newValue });
                    }
                }}
                sx={{
                    ...toggleButtonStyles,
                    '& .MuiToggleButton-root': {
                        ...toggleButtonStyles['& .MuiToggleButton-root'],
                        width: '60px',
                        minWidth: '70px',
                        maxWidth: '60px',
                    }
                }}
            >
                {STEP_SIZES.map(({ value, label }) => (
                    <ToggleButton key={value} value={value}>{label}</ToggleButton>
                ))}
            </ToggleButtonGroup>
        </Box>
    );
};

/**
 * Audio Demodulation Selector Component
 */
export const AudioDemodSelector = ({ vfoIndex, vfoActive, mode, onVFOPropertyChange }) => {
    const { t } = useTranslation('waterfall');

    return (
        <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary', fontWeight: 600 }}>
                {t('vfo.audio_demodulation', 'Audio Demodulation')}
            </Typography>
            <Typography variant="caption" sx={{ mb: 1, display: 'block', color: 'text.disabled', fontSize: '0.7rem' }}>
                {t('vfo.audio_demodulation_help', 'How to extract audio from the RF signal')}
            </Typography>
            <ToggleButtonGroup
                value={mode || 'none'}
                exclusive
                disabled={!vfoActive}
                onChange={(event, newValue) => {
                    if (newValue !== null) {
                        // When selecting an audio demod mode, clear decoder
                        onVFOPropertyChange(vfoIndex, { mode: newValue, decoder: 'none' });
                    }
                }}
                sx={toggleButtonStyles}
            >
                <ToggleButton value="none">{t('vfo.modes.none')}</ToggleButton>
                <ToggleButton value="AM">{t('vfo.modes.am')}</ToggleButton>
                <ToggleButton value="FM">{t('vfo.modes.fm')}</ToggleButton>
                <ToggleButton value="FM_STEREO">{t('vfo.modes.fm_stereo', 'FM Stereo')}</ToggleButton>
                <ToggleButton value="LSB">{t('vfo.modes.lsb')}</ToggleButton>
                <ToggleButton value="USB">{t('vfo.modes.usb')}</ToggleButton>
                <ToggleButton value="CW">{t('vfo.modes.cw')}</ToggleButton>
            </ToggleButtonGroup>
        </Box>
    );
};

/**
 * Transcription Selector Component
 */
export const TranscriptionSelector = ({
    vfoIndex,
    vfoActive,
    vfoMarkers,
    geminiConfigured,
    deepgramConfigured,
    onTranscriptionToggle,
    onOpenParamsDialog
}) => {
    const { t } = useTranslation('waterfall');
    const vfo = vfoMarkers[vfoIndex];

    const currentValue = vfo?.transcriptionEnabled ? (vfo?.transcriptionProvider || 'gemini') : 'none';

    // Language flag and name mapping
    const flagMap = {
        'auto': '🌐', 'en': '🇬🇧', 'el': '🇬🇷', 'es': '🇪🇸', 'fr': '🇫🇷',
        'de': '🇩🇪', 'it': '🇮🇹', 'pt': '🇵🇹', 'pt-BR': '🇧🇷', 'ru': '🇷🇺',
        'uk': '🇺🇦', 'ja': '🇯🇵', 'zh': '🇨🇳', 'ar': '🇸🇦', 'tl': '🇵🇭', 'tr': '🇹🇷'
    };
    const langMap = {
        'auto': 'Auto', 'en': 'EN', 'el': 'EL', 'es': 'ES', 'fr': 'FR',
        'de': 'DE', 'it': 'IT', 'pt': 'PT', 'pt-BR': 'PT-BR', 'ru': 'RU',
        'uk': 'UK', 'ja': 'JA', 'zh': 'ZH', 'ar': 'AR', 'tl': 'TL', 'tr': 'TR'
    };

    const getTranscriptionSummary = () => {
        if (!vfo?.transcriptionEnabled) return '- no transcription -';

        const sourceLang = vfo.transcriptionLanguage || 'auto';
        const translateTo = vfo.transcriptionTranslateTo || 'none';

        const sourceFlag = flagMap[sourceLang] || '🏳️';
        const sourceDisplay = langMap[sourceLang] || sourceLang.toUpperCase();
        const translateFlag = translateTo === 'none' ? '⭕' : (flagMap[translateTo] || '🏳️');
        const translateDisplay = translateTo === 'none' ? 'No Trans' : (langMap[translateTo] || translateTo.toUpperCase());

        return `${sourceFlag} ${sourceDisplay} → ${translateFlag} ${translateDisplay}`;
    };

    return (
        <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary', fontWeight: 600 }}>
                {t('vfo.transcription_mode', 'Transcription')}
            </Typography>
            <Typography variant="caption" sx={{ mb: 1, display: 'block', color: 'text.disabled', fontSize: '0.7rem' }}>
                {t('vfo.transcription_help', 'Transcribe audio using AI')}
            </Typography>
            <ToggleButtonGroup
                value={currentValue}
                exclusive
                disabled={!vfoActive || (!geminiConfigured && !deepgramConfigured)}
                onChange={(event, newValue) => {
                    if (newValue !== null && newValue !== currentValue) {
                        const newEnabled = newValue !== 'none';
                        const newProvider = newValue !== 'none' ? newValue : (vfo?.transcriptionProvider || 'gemini');
                        onTranscriptionToggle && onTranscriptionToggle(vfoIndex, newEnabled, newProvider);
                    }
                }}
                sx={toggleButtonStyles}
            >
                <ToggleButton value="none">{t('vfo.transcription_modes.none', 'None')}</ToggleButton>
                <ToggleButton value="gemini" disabled={!geminiConfigured}>
                    {t('vfo.transcription_modes.gemini', 'Gemini AI')}
                </ToggleButton>
                <ToggleButton value="deepgram" disabled={!deepgramConfigured}>
                    {t('vfo.transcription_modes.deepgram', 'Deepgram')}
                </ToggleButton>
            </ToggleButtonGroup>

            {/* API Key notifications */}
            {!geminiConfigured && !deepgramConfigured && (
                <Typography variant="caption" sx={{ mt: 0.5, display: 'block', color: 'text.disabled', fontSize: '0.7rem', fontStyle: 'italic' }}>
                    {t('vfo.api_key_required', 'API key required in Settings')}
                </Typography>
            )}

            {/* Transcription Parameters Link */}
            <Box sx={{ mt: 1.5, width: '100%' }}>
                <Link
                    component="button"
                    variant="body2"
                    disabled={!vfoActive || !vfo?.transcriptionEnabled || !geminiConfigured}
                    onClick={onOpenParamsDialog}
                    sx={{
                        width: '100%',
                        fontSize: '0.8rem',
                        color: 'text.primary',
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 0.75,
                        py: 0.75,
                        px: 1.5,
                        borderRadius: 1,
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        transition: 'all 0.2s ease',
                        '&:hover:not(.Mui-disabled)': {
                            backgroundColor: 'rgba(255, 255, 255, 0.08)',
                            borderColor: 'rgba(255, 255, 255, 0.2)',
                        },
                        '&.Mui-disabled': {
                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                            borderColor: 'rgba(255, 255, 255, 0.05)',
                            color: 'rgba(255, 255, 255, 0.3)',
                            opacity: 0.5,
                            cursor: 'not-allowed',
                        },
                        cursor: 'pointer',
                    }}
                >
                    <SettingsIcon sx={{ fontSize: '1rem', color: 'text.secondary', flexShrink: 0 }} />
                    <Box component="span" sx={{ fontFamily: 'monospace', color: 'text.secondary', flex: 1, textAlign: 'center' }}>
                        {getTranscriptionSummary()}
                    </Box>
                </Link>
            </Box>
        </Box>
    );
};

/**
 * Data Decoder Selector Component
 */
export const DataDecoderSelector = ({
    vfoIndex,
    vfoActive,
    vfoMarkers,
    decoder,
    transmitters,
    onVFOPropertyChange,
    onTranscriptionToggle,
    onOpenParamsDialog
}) => {
    const { t } = useTranslation('waterfall');
    const vfo = vfoMarkers[vfoIndex];
    const unsupportedDecoderTooltip = t('vfo.decoders_unsupported', 'Not supported yet');
    const isDecoderSupported = (decoderKey) => DECODER_SUPPORT[decoderKey] !== false;

    const handleDecoderChange = (event, newValue) => {
        if (newValue !== null) {
            if (newValue !== 'none') {
                // Disable transcription when selecting a decoder
                if (vfo?.transcriptionEnabled) {
                    onTranscriptionToggle && onTranscriptionToggle(vfoIndex, false);
                }

                const updates = { decoder: newValue, mode: 'none' };

                // Set bandwidth based on decoder type
                if (newValue === 'sstv') updates.bandwidth = 3300;
                else if (newValue === 'apt') updates.bandwidth = 40000;
                else if (newValue === 'lora') updates.bandwidth = 500000;
                else if (newValue === 'gnss') updates.bandwidth = 2000000;
                else if (newValue === 'morse') updates.bandwidth = 2500;
                else if (newValue === 'afsk') updates.bandwidth = 3300;
                else if (['gmsk', 'gfsk', 'bpsk'].includes(newValue)) {
                    const lockedTransmitterTrackerId = vfo?.lockedTransmitterTrackerId;
                    const lockedTransmitter = vfo?.lockedTransmitterId
                        ? transmitters.find((tx) => {
                            if (!sameIdentifier(tx.id, vfo.lockedTransmitterId)) {
                                return false;
                            }
                            if (!lockedTransmitterTrackerId) {
                                return true;
                            }
                            return sameIdentifier(tx.trackerId, lockedTransmitterTrackerId);
                        })
                        : null;
                    if (lockedTransmitter && lockedTransmitter.baud) {
                        updates.bandwidth = lockedTransmitter.baud * 3;
                        updates.transmitterBaud = lockedTransmitter.baud;
                    } else {
                        updates.bandwidth = 30000;
                    }
                }

                onVFOPropertyChange(vfoIndex, updates);
            } else {
                onVFOPropertyChange(vfoIndex, { decoder: newValue });
            }
        }
    };

    return (
        <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary', fontWeight: 600 }}>
                {t('vfo.data_decoders', 'Data Decoders')}
            </Typography>
            <Typography variant="caption" sx={{ mb: 1, display: 'block', color: 'text.disabled', fontSize: '0.7rem' }}>
                {t('vfo.data_decoders_help', 'An internal FM or SSB demodulator will be spun up as needed to decode some modes')}
            </Typography>
            <ToggleButtonGroup
                value={decoder || 'none'}
                exclusive
                disabled={!vfoActive}
                onChange={handleDecoderChange}
                sx={toggleButtonStyles}
            >
                {[
                    { value: 'none', label: t('vfo.decoders_modes.none', 'None') },
                    { value: 'sstv', label: t('vfo.decoders_modes.sstv', 'SSTV') },
                    { value: 'morse', label: t('vfo.decoders_modes.morse', 'Morse') },
                    { value: 'lora', label: t('vfo.decoders_modes.lora', 'LoRa') },
                    { value: 'fsk', label: t('vfo.decoders_modes.fsk', 'FSK') },
                    { value: 'gmsk', label: t('vfo.decoders_modes.gmsk', 'GMSK') },
                    { value: 'gfsk', label: t('vfo.decoders_modes.gfsk', 'GFSK') },
                    { value: 'bpsk', label: t('vfo.decoders_modes.bpsk', 'BPSK') },
                    { value: 'afsk', label: t('vfo.decoders_modes.afsk', 'AFSK') },
                    { value: 'gnss', label: t('vfo.decoders_modes.gnss', 'GNSS') }
                ].map(({ value, label }) => {
                    const supported = isDecoderSupported(value);
                    const button = (
                        <ToggleButton key={value} value={value} disabled={!supported}>
                            {label}
                        </ToggleButton>
                    );

                    if (supported) {
                        return button;
                    }

                    return (
                        <Tooltip key={value} title={unsupportedDecoderTooltip} arrow>
                            <span style={{ display: 'inline-flex' }}>
                                {button}
                            </span>
                        </Tooltip>
                    );
                })}
            </ToggleButtonGroup>

            {/* Decoder Parameters Link */}
            <Box sx={{ mt: 1.5, width: '100%' }}>
                <Link
                    component="button"
                    variant="body2"
                    disabled={!vfoActive || !decoder || decoder === 'none'}
                    onClick={onOpenParamsDialog}
                    sx={{
                        width: '100%',
                        fontSize: '0.8rem',
                        color: 'text.primary',
                        textDecoration: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 0.75,
                        py: 0.75,
                        px: 1.5,
                        borderRadius: 1,
                        backgroundColor: vfo?.parametersEnabled ? 'rgba(33, 150, 243, 0.08)' : 'rgba(255, 255, 255, 0.05)',
                        border: vfo?.parametersEnabled ? '1px solid rgba(33, 150, 243, 0.3)' : '1px solid rgba(255, 255, 255, 0.1)',
                        transition: 'all 0.2s ease',
                        '&:hover:not(.Mui-disabled)': {
                            backgroundColor: vfo?.parametersEnabled ? 'rgba(33, 150, 243, 0.12)' : 'rgba(255, 255, 255, 0.08)',
                            borderColor: vfo?.parametersEnabled ? 'rgba(33, 150, 243, 0.4)' : 'rgba(255, 255, 255, 0.2)',
                        },
                        '&.Mui-disabled': {
                            backgroundColor: 'rgba(255, 255, 255, 0.02)',
                            borderColor: 'rgba(255, 255, 255, 0.05)',
                            color: 'rgba(255, 255, 255, 0.3)',
                            opacity: 0.5,
                            cursor: 'not-allowed',
                        },
                        cursor: 'pointer',
                    }}
                >
                    <SettingsIcon sx={{ fontSize: '1rem', color: vfo?.parametersEnabled ? 'primary.main' : 'text.secondary' }} />
                    <Box
                        component="span"
                        sx={{
                            fontFamily: 'monospace',
                            color: 'text.secondary',
                            flex: 1,
                            textDecoration: decoder && decoder !== 'none' && !vfo?.parametersEnabled ? 'line-through' : 'none',
                        }}
                    >
                        {decoder === 'none' || !decoder
                            ? '- no decoder -'
                            : (formatDecoderParamsSummary(vfo) || 'Decoder Parameters')}
                    </Box>
                </Link>
            </Box>
        </Box>
    );
};

/**
 * Bandwidth Selector Component
 */
export const BandwidthSelector = ({ vfoIndex, vfoActive, bandwidth, mode, decoder, onVFOPropertyChange }) => {
    const { t } = useTranslation('waterfall');

    const currentValue = BANDWIDTHS.hasOwnProperty(bandwidth) ? bandwidth.toString() : 'custom';
    const isLocked = isLockedBandwidth(mode, decoder);

    return (
        <Box sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ mb: 1, color: 'text.secondary' }}>
                {t('vfo.bandwidth')}
            </Typography>
            <ToggleButtonGroup
                value={currentValue}
                exclusive
                disabled={!vfoActive || isLocked}
                onChange={(event, newValue) => {
                    if (newValue !== null && newValue !== 'custom') {
                        onVFOPropertyChange(vfoIndex, { bandwidth: parseInt(newValue) });
                    }
                }}
                sx={{
                    ...toggleButtonStyles,
                    '& .MuiToggleButton-root': {
                        ...toggleButtonStyles['& .MuiToggleButton-root'],
                        width: '75px',
                        minWidth: '75px',
                        maxWidth: '75px',
                        fontSize: '0.8rem',
                    }
                }}
            >
                <ToggleButton value="custom">{t('vfo.custom')}</ToggleButton>
                {Object.entries(BANDWIDTHS).map(([value, label]) => (
                    <ToggleButton key={value} value={value}>
                        {label}
                    </ToggleButton>
                ))}
            </ToggleButtonGroup>
        </Box>
    );
};
