/**
 * VFO Decoder Status Component
 *
 * Displays two-line status for decoders and transcription
 */

import React from 'react';
import { Box, Typography } from '@mui/material';

/**
 * Decoder Status Display Component
 * Shows active decoder/transcription status with metrics
 */
export const DecoderStatusDisplay = ({ vfo, decoderInfo }) => {
    // Determine what to display
    let line1Text = '—';
    let line2Text = '';
    let borderColor = 'divider';
    let textColor = 'text.disabled';

    // Check if this is a transcription decoder
    if (decoderInfo && decoderInfo.decoder_type === 'transcription') {
        const info = decoderInfo.info || {};
        const status = decoderInfo.status || 'unknown';

        // Line 1: TRANSCRIBING status and language info
        const statusParts = [];
        statusParts.push(status.toUpperCase());

        // Show language flow: source -> target
        if (info.language) {
            const langDisplay = info.language.toUpperCase();
            const translateDisplay = info.translate_to ? info.translate_to.toUpperCase() : null;
            if (translateDisplay && translateDisplay !== 'NONE') {
                statusParts.push(`${langDisplay} → ${translateDisplay}`);
            } else {
                statusParts.push(langDisplay);
            }
        }

        line1Text = statusParts.join(' • ');

        // Line 2: Transcription metrics
        const metricParts = [];

        // Transcription request stats
        if (info.transcriptions_sent !== undefined && info.transcriptions_received !== undefined) {
            const successRate = info.transcriptions_sent > 0
                ? Math.round((info.transcriptions_received / info.transcriptions_sent) * 100)
                : 0;
            metricParts.push(`SENT:${info.transcriptions_sent} RCV:${info.transcriptions_received} (${successRate}%)`);
        }

        // Show errors if any
        if (info.errors !== undefined && info.errors > 0) {
            metricParts.push(`ERR:${info.errors}`);
        }

        line2Text = metricParts.length > 0 ? metricParts.join(' • ') : '—';

        borderColor = status === 'transcribing' ? 'success.dark' : 'warning.dark';
        textColor = 'text.secondary';
    } else if (vfo && vfo.transcriptionEnabled) {
        // Transcription enabled but not active
        line1Text = 'TRANSCRIPTION - Not Active';
        line2Text = '';
        borderColor = 'warning.dark';
        textColor = 'warning.main';
    } else if (vfo && vfo.decoder && vfo.decoder !== 'none') {
        // Data decoder (existing logic)
        if (decoderInfo) {
            const info = decoderInfo.info || {};
            const status = decoderInfo.status || 'unknown';

            // Line 1: STATUS, MODE, FRAMING
            const statusParts = [];
            statusParts.push(status.toUpperCase());
            if (info.transmitter_mode !== undefined && info.transmitter_mode !== null) {
                statusParts.push(info.transmitter_mode);
            }
            if (info.framing !== undefined && info.framing !== null) {
                statusParts.push(info.framing.toUpperCase());
            }
            line1Text = statusParts.join(' • ');

            // Line 2: baudrate and existing metrics (packets, signal power) or progress or morse-specific
            const metricParts = [];

            // Add baudrate at the start of line 2
            if (info.baudrate !== undefined && info.baudrate !== null) {
                metricParts.push(`${info.baudrate}bd`);
            }

            // Show progress for SSTV if available
            if (decoderInfo.progress !== undefined && decoderInfo.progress !== null) {
                metricParts.push(`Progress: ${decoderInfo.progress}%`);
            }

            // Show WPM and character count for Morse
            if (info.wpm !== undefined && info.wpm !== null) {
                metricParts.push(`${info.wpm} WPM`);
            }
            if (info.character_count !== undefined && info.character_count !== null && info.character_count > 0) {
                metricParts.push(`CHAR:${info.character_count}`);
            }

            if (info.packets_decoded !== undefined && info.packets_decoded !== null) {
                metricParts.push(`PKT:${info.packets_decoded}`);
            }
            if (info.signal_power_dbfs !== undefined && info.signal_power_dbfs !== null) {
                metricParts.push(`${info.signal_power_dbfs.toFixed(1)}dB`);
            }
            line2Text = metricParts.length > 0 ? metricParts.join(' • ') : '—';

            borderColor = (status === 'decoding' || status === 'transcribing') ? 'success.dark' : 'warning.dark';
            textColor = 'text.secondary';
        } else {
            // Decoder selected but not running
            line1Text = `${vfo.decoder.toUpperCase()} - Not Active`;
            line2Text = '';
            borderColor = 'warning.dark';
            textColor = 'warning.main';
        }
    } else {
        // No decoder or transcription selected
        line1Text = '- no decoder -';
        line2Text = '';
        borderColor = 'divider';
        textColor = 'text.disabled';
    }

    return (
        <Box sx={{
            mt: 1,
            px: 1,
            py: 0.5,
            backgroundColor: 'rgba(0, 0, 0, 0.2)',
            borderRadius: 0.5,
            border: '1px solid',
            borderColor: borderColor,
            minHeight: '42px', // Ensure consistent height for two lines
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center'
        }}>
            <Typography
                variant="caption"
                sx={{
                    fontSize: '0.7rem',
                    fontFamily: 'monospace',
                    color: textColor,
                    display: 'block',
                    textAlign: 'center'
                }}
            >
                {line1Text}
            </Typography>
            {line2Text && (
                <Typography
                    variant="caption"
                    sx={{
                        fontSize: '0.7rem',
                        fontFamily: 'monospace',
                        color: textColor,
                        display: 'block',
                        textAlign: 'center',
                        minHeight: '0.7rem' // Reserve space even when empty
                    }}
                >
                    {line2Text || '\u00A0'}
                </Typography>
            )}
        </Box>
    );
};
