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

import React, { useState, useMemo } from 'react';
import {
    Box,
    Typography,
    Paper,
    Tooltip,
    IconButton,
    Stack,
    Button,
    useTheme,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { toast } from 'react-toastify';

function HexByte({ byte, offset, onClick, selected }) {
    const theme = useTheme();
    const byteValue = typeof byte === 'string' ? parseInt(byte, 16) : byte;

    const tooltipContent = (
        <Box sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
            <div>Offset: 0x{offset.toString(16).padStart(4, '0').toUpperCase()}</div>
            <div>Hex: 0x{byteValue.toString(16).padStart(2, '0').toUpperCase()}</div>
            <div>Dec: {byteValue}</div>
            <div>Binary: {byteValue.toString(2).padStart(8, '0')}</div>
            <div>ASCII: {byteValue >= 32 && byteValue < 127 ? String.fromCharCode(byteValue) : '·'}</div>
        </Box>
    );

    return (
        <Tooltip title={tooltipContent} placement="top">
            <Box
                component="span"
                onClick={() => onClick && onClick(offset)}
                sx={{
                    display: 'inline-block',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    px: 0.5,
                    cursor: 'pointer',
                    backgroundColor: selected ? theme.palette.primary.main + '40' : 'transparent',
                    borderRadius: 0.5,
                    '&:hover': {
                        backgroundColor: selected
                            ? theme.palette.primary.main + '60'
                            : theme.palette.action.hover,
                    },
                    transition: 'background-color 0.2s',
                }}
            >
                {byteValue.toString(16).padStart(2, '0').toUpperCase()}
            </Box>
        </Tooltip>
    );
}

export default function HexAsciiTab({ packet, telemetry }) {
    const theme = useTheme();
    const [selectedByte, setSelectedByte] = useState(null);

    // Get hex data
    const hexString = packet?.hex || telemetry?.raw?.packet_hex || '';

    // Parse hex string to bytes
    const bytes = useMemo(() => {
        if (!hexString) return [];
        const result = [];
        for (let i = 0; i < hexString.length; i += 2) {
            result.push(parseInt(hexString.substr(i, 2), 16));
        }
        return result;
    }, [hexString]);

    // Split into lines of 16 bytes
    const lines = useMemo(() => {
        const result = [];
        for (let i = 0; i < bytes.length; i += 16) {
            result.push({
                offset: i,
                bytes: bytes.slice(i, i + 16),
            });
        }
        return result;
    }, [bytes]);

    const handleByteClick = (offset) => {
        setSelectedByte(offset === selectedByte ? null : offset);
    };

    const handleCopy = () => {
        if (hexString) {
            navigator.clipboard.writeText(hexString.toUpperCase());
            toast.success('Hex data copied to clipboard');
        }
    };

    const handleCopyFormatted = () => {
        // Create formatted hex dump
        let formatted = '';
        lines.forEach(line => {
            const offsetStr = line.offset.toString(16).padStart(8, '0').toUpperCase();
            const hexPart = line.bytes.map(b => b.toString(16).padStart(2, '0').toUpperCase()).join(' ');
            const asciiPart = line.bytes.map(b =>
                b >= 32 && b < 127 ? String.fromCharCode(b) : '.'
            ).join('');
            formatted += `${offsetStr}  ${hexPart.padEnd(47, ' ')}  ${asciiPart}\n`;
        });

        navigator.clipboard.writeText(formatted);
        toast.success('Formatted hex dump copied to clipboard');
    };

    if (!hexString) {
        return (
            <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography color="text.secondary">
                    No hex data available for this packet
                </Typography>
            </Box>
        );
    }

    return (
        <Box>
            {/* Header with actions */}
            <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                <Button
                    size="small"
                    startIcon={<ContentCopyIcon />}
                    onClick={handleCopy}
                    variant="outlined"
                >
                    Copy Hex
                </Button>
                <Button
                    size="small"
                    startIcon={<ContentCopyIcon />}
                    onClick={handleCopyFormatted}
                    variant="outlined"
                >
                    Copy Formatted
                </Button>
                <Box sx={{ flexGrow: 1 }} />
                <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>
                    {bytes.length} bytes • Click byte for details
                </Typography>
            </Stack>

            {/* Hex dump */}
            <Paper
                variant="outlined"
                sx={{
                    p: 2,
                    backgroundColor: theme.palette.mode === 'dark'
                        ? theme.palette.grey[900]
                        : theme.palette.grey[50],
                    maxHeight: '60vh',
                    overflow: 'auto',
                }}
            >
                <Box sx={{ fontFamily: 'monospace' }}>
                    {/* Header */}
                    <Box
                        sx={{
                            display: 'grid',
                            gridTemplateColumns: '100px 1fr 200px',
                            gap: 2,
                            mb: 1,
                            pb: 1,
                            borderBottom: `1px solid ${theme.palette.divider}`,
                        }}
                    >
                        <Typography
                            variant="caption"
                            sx={{
                                fontFamily: 'monospace',
                                fontWeight: 700,
                                color: theme.palette.text.secondary,
                            }}
                        >
                            Offset
                        </Typography>
                        <Typography
                            variant="caption"
                            sx={{
                                fontFamily: 'monospace',
                                fontWeight: 700,
                                color: theme.palette.text.secondary,
                            }}
                        >
                            Hex
                        </Typography>
                        <Typography
                            variant="caption"
                            sx={{
                                fontFamily: 'monospace',
                                fontWeight: 700,
                                color: theme.palette.text.secondary,
                            }}
                        >
                            ASCII
                        </Typography>
                    </Box>

                    {/* Lines */}
                    {lines.map((line) => (
                        <Box
                            key={line.offset}
                            sx={{
                                display: 'grid',
                                gridTemplateColumns: '100px 1fr 200px',
                                gap: 2,
                                py: 0.5,
                                '&:hover': {
                                    backgroundColor: theme.palette.action.hover,
                                },
                            }}
                        >
                            {/* Offset */}
                            <Typography
                                variant="body2"
                                sx={{
                                    fontFamily: 'monospace',
                                    color: theme.palette.text.secondary,
                                    userSelect: 'none',
                                }}
                            >
                                {line.offset.toString(16).padStart(8, '0').toUpperCase()}
                            </Typography>

                            {/* Hex bytes */}
                            <Box>
                                {line.bytes.map((byte, idx) => (
                                    <React.Fragment key={line.offset + idx}>
                                        <HexByte
                                            byte={byte}
                                            offset={line.offset + idx}
                                            onClick={handleByteClick}
                                            selected={selectedByte === line.offset + idx}
                                        />
                                        {idx < line.bytes.length - 1 && ' '}
                                        {idx === 7 && '  '} {/* Extra space in middle */}
                                    </React.Fragment>
                                ))}
                            </Box>

                            {/* ASCII */}
                            <Typography
                                variant="body2"
                                sx={{
                                    fontFamily: 'monospace',
                                    color: theme.palette.text.secondary,
                                    letterSpacing: '0.1em',
                                }}
                            >
                                {line.bytes.map((byte, idx) => (
                                    <span key={idx}>
                                        {byte >= 32 && byte < 127 ? String.fromCharCode(byte) : '·'}
                                    </span>
                                ))}
                            </Typography>
                        </Box>
                    ))}
                </Box>
            </Paper>

            {/* Legend */}
            <Box sx={{ mt: 2, p: 2, bgcolor: theme.palette.info.main + '30', borderRadius: 1, border: `1px solid ${theme.palette.info.main}60` }}>
                <Typography variant="caption" sx={{ color: theme.palette.info.light, fontWeight: 500 }}>
                    💡 Tip: Hover over bytes to see detailed information. Click to select. ASCII column shows printable characters (·  for non-printable).
                </Typography>
            </Box>
        </Box>
    );
}
