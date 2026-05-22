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

import React from 'react';
import {
    Box,
    Typography,
    Chip,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Stack,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import { useSelector } from 'react-redux';
import ZoomableImage from '../common/zoomable-image.jsx';

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), sizes.length - 1);
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

export default function RecordingDialog({ open, onClose, recording }) {
    // Get timezone preference
    const timezone = useSelector((state) => {
        const tzPref = state.preferences?.preferences?.find(p => p.name === 'timezone');
        return tzPref?.value || 'UTC';
    });

    // Timezone-aware date formatting function
    const formatDate = (isoDate) => {
        const date = new Date(isoDate);
        return date.toLocaleString('en-US', { timeZone: timezone });
    };

    const sectionSx = {
        p: 2,
        mb: 2,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 1.5,
        bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50'),
    };

    const rowSx = {
        display: 'grid',
        gridTemplateColumns: { xs: '1fr', sm: '160px 1fr' },
        gap: { xs: 0.5, sm: 2 },
        py: 0.5,
    };

    const formatFrequency = (frequencyHz) => {
        if (frequencyHz === null || frequencyHz === undefined) return '';
        if (frequencyHz >= 1e9) {
            return `${(frequencyHz / 1e9).toFixed(6)} GHz`;
        }
        if (frequencyHz >= 1e6) {
            return `${(frequencyHz / 1e6).toFixed(6)} MHz`;
        }
        if (frequencyHz >= 1e3) {
            return `${(frequencyHz / 1e3).toFixed(3)} kHz`;
        }
        return `${frequencyHz.toFixed(0)} Hz`;
    };


    const getImageCursorInfo = ({ event, containerRect, naturalWidth, naturalHeight, pan, zoom }) => {
        if (!containerRect || !naturalWidth || !naturalHeight) return null;

        const localX = event.clientX - containerRect.left;
        const localY = event.clientY - containerRect.top;
        const centeredX = localX - containerRect.width / 2;
        const centeredY = localY - containerRect.height / 2;
        const unscaledX = (centeredX - pan.x) / zoom;
        const unscaledY = (centeredY - pan.y) / zoom;

        const scaleToContain = Math.min(containerRect.width / naturalWidth, containerRect.height / naturalHeight);
        const contentWidth = naturalWidth * scaleToContain;
        const contentHeight = naturalHeight * scaleToContain;

        const halfWidth = contentWidth / 2;
        const halfHeight = contentHeight / 2;
        if (unscaledX < -halfWidth || unscaledX > halfWidth || unscaledY < -halfHeight || unscaledY > halfHeight) {
            return null;
        }

        const imageX = (unscaledX + halfWidth) / contentWidth * naturalWidth;
        const imageY = (unscaledY + halfHeight) / contentHeight * naturalHeight;

        const centerFrequency = recording?.metadata?.center_frequency;
        const sampleRate = recording?.metadata?.sample_rate;
        const startTime = recording?.metadata?.start_time;
        const endTime = recording?.metadata?.finalized_time || recording?.modified || recording?.created;

        const hasFrequencyData = Number.isFinite(centerFrequency) && Number.isFinite(sampleRate);
        const hasTimeData = Boolean(startTime && endTime);

        let frequency = null;
        if (hasFrequencyData) {
            const startFreq = centerFrequency - sampleRate / 2;
            frequency = startFreq + (imageX / naturalWidth) * sampleRate;
        }

        let timeLabel = '';
        if (hasTimeData) {
            const startMs = new Date(startTime).getTime();
            const endMs = new Date(endTime).getTime();
            if (!Number.isNaN(startMs) && !Number.isNaN(endMs) && endMs >= startMs) {
                const timeMs = startMs + (imageY / naturalHeight) * (endMs - startMs);
                timeLabel = formatDate(new Date(timeMs).toISOString());
            }
        }

        return {
            x: localX,
            y: localY,
            frequency,
            timeLabel,
        };
    };

    if (!recording) return null;

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="lg"
            fullWidth
            PaperProps={{
                sx: {
                    bgcolor: 'background.paper',
                    border: (theme) => `1px solid ${theme.palette.divider}`,
                    borderRadius: 2,
                },
            }}
        >
            <DialogTitle
                sx={{
                    bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'grey.900' : 'grey.100'),
                    borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
                    py: 2.5,
                    px: 3,
                }}
            >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="h6">Recording Details</Typography>
                    <Box>
                        {recording?.snapshot?.width && recording?.snapshot?.height && (
                            <Chip
                                label={`${recording.snapshot.width}×${recording.snapshot.height}`}
                                size="small"
                                sx={{ mr: 1, height: '20px', fontSize: '0.65rem', '& .MuiChip-label': { px: 0.75 } }}
                            />
                        )}
                        <Chip label={formatBytes(recording?.data_size || 0)} size="small" sx={{ height: '20px', fontSize: '0.65rem', '& .MuiChip-label': { px: 0.75 } }} />
                    </Box>
                </Box>
            </DialogTitle>
            <DialogContent
                sx={{
                    bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'rgba(0, 0, 0, 0.36)' : 'grey.100'),
                    px: 3,
                    py: 3,
                }}
            >
                {recording && (
                    <Box sx={{ mt: 3 }}>
                        {recording.snapshot && (
                            <ZoomableImage
                                src={recording.snapshot.url}
                                alt={recording.name}
                                resetKey={`${open}-${recording.snapshot.url}`}
                                getCursorInfo={getImageCursorInfo}
                                containerSx={{
                                    mb: 2,
                                    height: { xs: 280, sm: 360, md: 440 },
                                    '&:hover': {
                                        boxShadow: '0 0 0 2px rgba(66, 135, 245, 0.25)',
                                        borderStyle: 'dashed',
                                    },
                                }}
                                renderOverlay={({ cursorInfo }) => (
                                    cursorInfo ? (
                                        <>
                                            <Box
                                                sx={{
                                                    position: 'absolute',
                                                    top: 0,
                                                    bottom: 0,
                                                    left: cursorInfo.x,
                                                    width: '1px',
                                                    bgcolor: 'rgba(255, 255, 255, 0.5)',
                                                    pointerEvents: 'none',
                                                }}
                                            />
                                            <Box
                                                sx={{
                                                    position: 'absolute',
                                                    left: 0,
                                                    right: 0,
                                                    top: cursorInfo.y,
                                                    height: '1px',
                                                    bgcolor: 'rgba(255, 255, 255, 0.5)',
                                                    pointerEvents: 'none',
                                                }}
                                            />
                                            {cursorInfo.frequency !== null && (
                                                <Box
                                                    sx={{
                                                        position: 'absolute',
                                                        top: 8,
                                                        left: cursorInfo.x,
                                                        transform: 'translateX(-50%)',
                                                        px: 1,
                                                        py: 0.4,
                                                        borderRadius: 1,
                                                        bgcolor: 'rgba(0, 0, 0, 0.7)',
                                                        color: 'common.white',
                                                        fontSize: '0.7rem',
                                                        letterSpacing: '0.02em',
                                                        pointerEvents: 'none',
                                                        whiteSpace: 'nowrap',
                                                    }}
                                                >
                                                    {formatFrequency(cursorInfo.frequency)}
                                                </Box>
                                            )}
                                            {cursorInfo.timeLabel && (
                                                <Box
                                                    sx={{
                                                        position: 'absolute',
                                                        left: 8,
                                                        top: cursorInfo.y,
                                                        transform: 'translateY(-50%)',
                                                        px: 1,
                                                        py: 0.4,
                                                        borderRadius: 1,
                                                        bgcolor: 'rgba(0, 0, 0, 0.7)',
                                                        color: 'common.white',
                                                        fontSize: '0.7rem',
                                                        letterSpacing: '0.02em',
                                                        pointerEvents: 'none',
                                                        whiteSpace: 'nowrap',
                                                    }}
                                                >
                                                    {cursorInfo.timeLabel}
                                                </Box>
                                            )}
                                        </>
                                    ) : null
                                )}
                            />
                        )}

                        <Typography variant="subtitle2" gutterBottom>
                            Recording
                        </Typography>
                        <Box sx={sectionSx}>
                            <Box sx={rowSx}>
                                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                    Name
                                </Typography>
                                <Typography variant="body2" sx={{ fontFamily: 'monospace', wordBreak: 'break-word' }}>
                                    {recording.name}
                                </Typography>
                            </Box>
                            <Box sx={rowSx}>
                                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                    Files
                                </Typography>
                                <Box sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                                    <Box sx={{ mb: 0.5 }}>
                                        {recording.data_file} ({formatBytes(recording.data_size)})
                                    </Box>
                                    <Box sx={{ mb: recording.snapshot ? 0.5 : 0 }}>
                                        {recording.meta_file}
                                    </Box>
                                    {recording.snapshot && (
                                        <Box>
                                            {recording.snapshot.filename} ({recording.snapshot.width}×{recording.snapshot.height})
                                        </Box>
                                    )}
                                </Box>
                            </Box>
                        </Box>

                        {recording.metadata && (
                            <>
                                {(recording.metadata.target_satellite_name || recording.metadata.target_satellite_norad_id) && (
                                    <>
                                        <Typography variant="subtitle2" gutterBottom>
                                            Target Satellite
                                        </Typography>
                                        <Box sx={sectionSx}>
                                            {recording.metadata.target_satellite_name && (
                                                <Box sx={rowSx}>
                                                    <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                        Name
                                                    </Typography>
                                                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                                        {recording.metadata.target_satellite_name}
                                                    </Typography>
                                                </Box>
                                            )}
                                            {recording.metadata.target_satellite_norad_id && (
                                                <Box sx={rowSx}>
                                                    <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                        NORAD ID
                                                    </Typography>
                                                    <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                                        {recording.metadata.target_satellite_norad_id}
                                                    </Typography>
                                                </Box>
                                            )}
                                        </Box>
                                    </>
                                )}

                                <Typography variant="subtitle2" gutterBottom>
                                    Metadata
                                </Typography>
                                <Box sx={sectionSx}>
                                    {recording.metadata.datatype && (
                                        <Box sx={rowSx}>
                                            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                Data Type
                                            </Typography>
                                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                                {recording.metadata.datatype}
                                            </Typography>
                                        </Box>
                                    )}
                                    {recording.metadata.sample_rate && (
                                        <Box sx={rowSx}>
                                            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                Sample Rate
                                            </Typography>
                                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                                {recording.metadata.sample_rate} Hz
                                            </Typography>
                                        </Box>
                                    )}
                                    {recording.metadata.start_time && (
                                        <Box sx={rowSx}>
                                            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                Start Time
                                            </Typography>
                                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                                {formatDate(recording.metadata.start_time)}
                                            </Typography>
                                        </Box>
                                    )}
                                    {recording.metadata.finalized_time && (
                                        <Box sx={rowSx}>
                                            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                End Time
                                            </Typography>
                                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                                {formatDate(recording.metadata.finalized_time)}
                                            </Typography>
                                        </Box>
                                    )}
                                    {recording.metadata.version && (
                                        <Box sx={rowSx}>
                                            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                SigMF Version
                                            </Typography>
                                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                                {recording.metadata.version}
                                            </Typography>
                                        </Box>
                                    )}
                                    {recording.metadata.recorder && (
                                        <Box sx={rowSx}>
                                            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                Recorder
                                            </Typography>
                                            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                                {recording.metadata.recorder}
                                            </Typography>
                                        </Box>
                                    )}
                                    {recording.metadata.description && (
                                        <Box sx={rowSx}>
                                            <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                Description
                                            </Typography>
                                            <Typography variant="body2" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                                                {recording.metadata.description}
                                            </Typography>
                                        </Box>
                                    )}
                                </Box>

                                {recording.metadata.captures?.length > 0 && (
                                    <>
                                        <Typography variant="subtitle2" gutterBottom>
                                            Capture Segments ({recording.metadata.captures.length})
                                        </Typography>
                                        <Stack spacing={1} sx={{ mb: 2 }}>
                                            {recording.metadata.captures.map((capture, index) => (
                                                <Box
                                                    key={index}
                                                    sx={{
                                                        p: 2,
                                                        border: '1px solid',
                                                        borderColor: 'divider',
                                                        borderRadius: 1.5,
                                                        bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'grey.900' : 'common.white'),
                                                        boxShadow: '0 1px 2px rgba(0, 0, 0, 0.08)',
                                                    }}
                                                >
                                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                                                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                                            Segment {index + 1}
                                                        </Typography>
                                                        <Chip
                                                            label={`${Object.keys(capture).length} fields`}
                                                            size="small"
                                                            sx={{ height: '20px', fontSize: '0.65rem', '& .MuiChip-label': { px: 0.75 } }}
                                                        />
                                                    </Box>
                                                    <Box sx={{ fontFamily: 'monospace', fontSize: '0.8125rem' }}>
                                                        {Object.entries(capture).map(([key, value]) => (
                                                            <Box key={key} sx={rowSx}>
                                                                <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                                                                    {key}
                                                                </Typography>
                                                                <Typography variant="body2" sx={{ fontFamily: 'monospace', wordBreak: 'break-word' }}>
                                                                    {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                                                </Typography>
                                                            </Box>
                                                        ))}
                                                    </Box>
                                                </Box>
                                            ))}
                                        </Stack>
                                    </>
                                )}
                            </>
                        )}
                    </Box>
                )}
            </DialogContent>
            <DialogActions
                sx={{
                    bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'grey.900' : 'grey.100'),
                    borderTop: (theme) => `1px solid ${theme.palette.divider}`,
                    px: 3,
                    py: 2.5,
                    gap: 1,
                    flexWrap: 'wrap',
                    justifyContent: 'flex-end',
                }}
            >
                <Button
                    onClick={() => window.open(recording?.download_urls.data, '_blank')}
                    startIcon={<DownloadIcon />}
                    variant="outlined"
                >
                    Download Data
                </Button>
                <Button
                    onClick={() => window.open(recording?.download_urls.meta, '_blank')}
                    startIcon={<DownloadIcon />}
                    variant="outlined"
                >
                    Download Metadata
                </Button>
                {recording?.snapshot && (
                    <Button
                        onClick={() => window.open(recording.snapshot.url, '_blank')}
                        startIcon={<DownloadIcon />}
                        variant="outlined"
                    >
                        Download Snapshot
                    </Button>
                )}
                <Button
                    onClick={onClose}
                    variant="outlined"
                    sx={{
                        borderColor: (theme) => (theme.palette.mode === 'dark' ? 'grey.700' : 'grey.400'),
                        '&:hover': {
                            borderColor: (theme) => (theme.palette.mode === 'dark' ? 'grey.600' : 'grey.500'),
                            bgcolor: (theme) => (theme.palette.mode === 'dark' ? 'grey.800' : 'grey.200'),
                        },
                    }}
                >
                    Close
                </Button>
            </DialogActions>
        </Dialog>
    );
}
