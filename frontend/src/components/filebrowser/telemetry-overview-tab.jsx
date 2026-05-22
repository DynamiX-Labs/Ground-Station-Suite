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

import React from 'react';
import {
    Box,
    Typography,
    Divider,
    Chip,
    Stack,
    useTheme,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { getDecoderDisplay, ModulationType } from '../../constants/modulations';
import { useUserTimeSettings } from '../../hooks/useUserTimeSettings.jsx';
import { formatDateTime } from '../../utils/date-time.js';

function InfoSection({ title, children }) {
    const theme = useTheme();
    return (
        <Box sx={{ mb: 3 }}>
            <Typography
                variant="subtitle2"
                sx={{
                    mb: 1.5,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: theme.palette.text.secondary,
                    fontSize: '0.75rem',
                    letterSpacing: 1,
                }}
            >
                {title}
            </Typography>
            <Divider sx={{ mb: 2 }} />
            {children}
        </Box>
    );
}

function InfoRow({ label, value, mono = false }) {
    return (
        <Box sx={{
            display: 'flex',
            justifyContent: 'space-between',
            py: 0.75,
            alignItems: 'center',
        }}>
            <Typography variant="body2" color="text.secondary">
                {label}
            </Typography>
            <Typography
                variant="body2"
                sx={{
                    fontFamily: mono ? 'monospace' : 'inherit',
                    fontWeight: 500,
                }}
            >
                {value || '-'}
            </Typography>
        </Box>
    );
}

export default function OverviewTab({ metadata, file, telemetry, packet, ax25 }) {
    const theme = useTheme();
    const { timezone, locale } = useUserTimeSettings();

    // Format timestamp
    const formatTimestamp = (ts) => {
        if (!ts) return '-';
        try {
            const dateValue = typeof ts === 'number' ? ts * 1000 : ts;
            return formatDateTime(dateValue, { timezone, locale });
        } catch {
            return String(ts);
        }
    };

    // Get frame info from telemetry
    const frame = telemetry.frame || {};
    const signal = metadata.signal || {};
    const vfo = metadata.vfo || {};
    const decoder = metadata.decoder || {};

    const decoderConfig = metadata.decoder_config || {};
    const framing = decoderConfig.framing;
    const payloadProtocol = decoderConfig.payload_protocol;
    const geoscan = decoderConfig.geoscan || {};
    const framingParams = decoderConfig.framing_params || {};
    const telemetryParser = telemetry.parser || '';

    const isGeoscan = framing === 'geoscan' || payloadProtocol === 'proprietary';
    // Encapsulated AX.25 detection: show AX.25 frame whenever telemetry.frame carries
    // source/destination, regardless of which payload parser produced values.
    const hasEncapsulatedAx25 = Boolean((telemetry?.frame && telemetry.frame.source && telemetry.frame.destination));


    return (
        <Box>
            {/* Two Column Layout for remaining sections */}
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
                {/* Left Column */}
                <Box>
                    {/* Link-layer / Frame Information */}
                    {isGeoscan ? (
                        <InfoSection title="GEOSCAN Frame Information">
                            <InfoRow label="Framing" value={framing || 'geoscan'} />
                            <InfoRow label="Protocol" value={payloadProtocol || 'proprietary'} />
                            <InfoRow
                                label="Configured Frame Size"
                                value={`${geoscan.frame_size || framingParams.frame_size || 66} bytes`}
                            />
                            <InfoRow
                                label="Delivered Payload Length"
                                value={`${telemetry.raw?.payload_length || packet.length_bytes || '-'} bytes`}
                            />
                            <InfoRow
                                label="PN9 Descrambler"
                                value={geoscan.pn9_descrambled === false ? 'No' : 'Yes'}
                            />
                            <InfoRow
                                label="CC11xx CRC"
                                value={(geoscan.cc11xx_crc || 'ok').toUpperCase()}
                            />
                            <InfoRow
                                label="Syncword Threshold"
                                value={`${geoscan.syncword_threshold ?? framingParams.syncword_threshold ?? 4}`}
                            />
                            <InfoRow label="Parser" value={telemetryParser || 'proprietary'} />
                        </InfoSection>
                    ) : (
                        <InfoSection title="AX.25 Frame Information">
                            <InfoRow
                                label="Source"
                                value={frame.source || ax25.from_callsign}
                                mono
                            />
                            <InfoRow
                                label="Destination"
                                value={frame.destination || ax25.to_callsign}
                                mono
                            />
                            <InfoRow
                                label="Control"
                                value={frame.control}
                                mono
                            />
                            <InfoRow
                                label="PID"
                                value={frame.pid}
                                mono
                            />
                            <InfoRow
                                label="Parser"
                                value={telemetryParser || 'ax25'}
                            />
                        </InfoSection>
                    )}

                    {/* Encapsulated AX.25 (when GEOSCAN carries an inner AX.25) */}
                    {isGeoscan && hasEncapsulatedAx25 && (
                        <InfoSection title="Encapsulated AX.25 Frame">
                            <InfoRow label="Source" value={frame.source || ax25.from_callsign} mono />
                            <InfoRow label="Destination" value={frame.destination || ax25.to_callsign} mono />
                            <InfoRow label="Control" value={frame.control} mono />
                            <InfoRow label="PID" value={frame.pid} mono />
                        </InfoSection>
                    )}

                    {/* Packet Metadata */}
                    <InfoSection title="Packet Metadata">
                        <InfoRow
                            label="Packet Number"
                            value={`#${packet.number || metadata.packet_number || '-'}`}
                        />
                        <InfoRow
                            label="Timestamp"
                            value={formatTimestamp(packet.timestamp || metadata.timestamp)}
                        />
                        <InfoRow
                            label="Total Length"
                            value={`${packet.length_bytes || packet.length || '-'} bytes`}
                        />
                        <InfoRow
                            label="Payload Length"
                            value={`${telemetry.raw?.payload_length || '-'} bytes`}
                        />
                        <InfoRow
                            label="Session ID"
                            value={decoder.session_id}
                            mono
                        />
                        <InfoRow
                            label="VFO"
                            value={vfo.id}
                        />
                    </InfoSection>
                </Box>

                {/* Right Column */}
                <Box>
                    {/* Signal Information */}
                    <InfoSection title="Signal Information">
                        <InfoRow
                            label="Frequency"
                            value={signal.frequency_mhz ? `${signal.frequency_mhz} MHz` : '-'}
                        />
                        <InfoRow
                            label="Baudrate"
                            value={decoder.baudrate ? `${decoder.baudrate} baud` : '-'}
                        />
                        <InfoRow
                            label="SDR Center"
                            value={signal.sdr_center_freq_mhz ? `${signal.sdr_center_freq_mhz} MHz` : '-'}
                        />
                        <InfoRow
                            label="VFO Center"
                            value={vfo.center_freq_mhz ? `${vfo.center_freq_mhz} MHz` : '-'}
                        />
                        <InfoRow
                            label="VFO Bandwidth"
                            value={vfo.bandwidth_khz ? `${vfo.bandwidth_khz} kHz` : '-'}
                        />
                        <InfoRow
                            label="Sample Rate"
                            value={signal.sample_rate_hz ? `${(signal.sample_rate_hz / 1000).toFixed(2)} kS/s` : '-'}
                        />
                    </InfoSection>

                    {/* Signal Power */}
                    {signal.signal_power_dbfs !== undefined && (
                        <InfoSection title="Signal Power">
                            <InfoRow
                                label="Signal Power"
                                value={`${signal.signal_power_dbfs.toFixed(1)} dBFS`}
                            />
                            {signal.signal_power_avg_dbfs !== undefined && (
                                <InfoRow
                                    label="Avg Power"
                                    value={`${signal.signal_power_avg_dbfs.toFixed(1)} dBFS`}
                                />
                            )}
                            {signal.signal_power_max_dbfs !== undefined && (
                                <InfoRow
                                    label="Peak Power"
                                    value={`${signal.signal_power_max_dbfs.toFixed(1)} dBFS`}
                                />
                            )}
                            {signal.signal_power_min_dbfs !== undefined && (
                                <InfoRow
                                    label="Min Power"
                                    value={`${signal.signal_power_min_dbfs.toFixed(1)} dBFS`}
                                />
                            )}
                        </InfoSection>
                    )}
                </Box>
            </Box>

            {/* Validation Status - Full Width */}
            <InfoSection title="Validation">
                <Stack spacing={1}>
                    {/* Show validation info based on decoder type */}
                    {decoder.type === ModulationType.LORA ? (
                        <>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                <Typography variant="body2">
                                    LoRa CRC validated by PHY layer
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                <Typography variant="body2">
                                    Spreading Factor: SF{decoder.spreading_factor || metadata.demodulator_parameters?.spreading_factor}
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                <Typography variant="body2">
                                    Forward Error Correction: CR {decoder.coding_rate || metadata.decoder?.coding_rate || '4/5'}
                                </Typography>
                            </Box>
                            {telemetry.success && telemetry.parser === 'ax25' ? (
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                    <Typography variant="body2">
                                        AX.25 frame decoded successfully
                                    </Typography>
                                </Box>
                            ) : null}
                        </>
                    ) : isGeoscan ? (
                        <>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                <Typography variant="body2">
                                    CC11xx CRC validated by GEOSCAN deframer
                                </Typography>
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                <Typography variant="body2">
                                    PN9 descrambling applied
                                </Typography>
                            </Box>
                            {hasEncapsulatedAx25 && (
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                    <Typography variant="body2">
                                        Encapsulated AX.25 frame decoded successfully
                                    </Typography>
                                </Box>
                            )}
                        </>
                    ) : (
                        <>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                <Typography variant="body2">
                                    CRC-16 validated by HDLC deframer
                                </Typography>
                            </Box>
                            {telemetry.success && telemetry.parser === 'ax25' ? (
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                    <Typography variant="body2">
                                        AX.25 callsigns decoded correctly
                                    </Typography>
                                </Box>
                            ) : null}
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
                                <Typography variant="body2">
                                    Packet integrity confirmed
                                </Typography>
                            </Box>
                        </>
                    )}
                </Stack>

                <Box sx={{ mt: 2, p: 1.5, bgcolor: theme.palette.info.main + '30', borderRadius: 1, border: `1px solid ${theme.palette.info.main}60` }}>
                    <Typography variant="caption" sx={{ color: theme.palette.info.light, fontWeight: 500 }}>
                        {decoder.type === ModulationType.LORA ? (
                            <>ℹ️ {getDecoderDisplay(decoder.type)} packets include PHY-layer CRC validation and Forward Error Correction (FEC). Invalid packets are automatically discarded by the {getDecoderDisplay(decoder.type)} decoder.</>
                        ) : isGeoscan ? (
                            <>ℹ️ GEOSCAN frames include TI CC11xx CRC and PN9 scrambling. The configured frame size typically includes a 2-byte CC11xx CRC that is removed after validation.</>
                        ) : (
                            <>ℹ️ All decoded packets have passed CRC-16-CCITT validation. Invalid packets are automatically discarded by the HDLC deframer.</>
                        )}
                    </Typography>
                </Box>
            </InfoSection>

            {/* File Information - Full Width */}
            <InfoSection title="File Information">
                <InfoRow
                    label="Binary File"
                    value={metadata.file?.binary || file.filename}
                    mono
                />
                <InfoRow
                    label="Metadata File"
                    value={metadata.file?.binary?.replace('.bin', '.json')}
                    mono
                />
                <InfoRow
                    label="File Size"
                    value={file.size ? `${file.size} bytes` : '-'}
                />
            </InfoSection>
        </Box>
    );
}
