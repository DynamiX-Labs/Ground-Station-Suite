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

import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import {
    Accordion,
    AccordionSummary,
    AccordionDetails,
} from './settings-elements.jsx';
import Typography from '@mui/material/Typography';
import {
    Box,
    Button,
    TextField,
    Chip,
    Stack,
    LinearProgress,
} from "@mui/material";
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import StopIcon from '@mui/icons-material/Stop';
import { useTranslation } from 'react-i18next';

const RecordingAccordion = ({
    expanded,
    onAccordionChange,
    isRecording,
    recordingDuration,
    recordingName,
    actualRecordingName,
    onRecordingNameChange,
    onStartRecording,
    onStopRecording,
    isStreaming,
    selectedSDRId,
    centerFrequency,
}) => {
    const { t } = useTranslation('waterfall');
    const [localRecordingName, setLocalRecordingName] = useState(recordingName);
    const [recordingStartFilename, setRecordingStartFilename] = useState('');

    // Get target satellite name from Redux
    const targetSatelliteName = useSelector((state) => state.targetSatTrack?.satelliteData?.details?.name || '');

    // Get disk usage from Redux
    const diskUsage = useSelector((state) => state.filebrowser?.diskUsage || { total: 0, used: 0, available: 0 });

    useEffect(() => {
        setLocalRecordingName(recordingName);
    }, [recordingName]);

    // Clear textbox when recording stops
    useEffect(() => {
        if (!isRecording && localRecordingName) {
            setLocalRecordingName('');
            onRecordingNameChange('');
        }
    }, [isRecording]);

    const formatDuration = (seconds) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    };

    const generateTimestamp = () => {
        const now = new Date();
        const date = now.toISOString().split('T')[0].replace(/-/g, '');
        const time = now.toTimeString().split(' ')[0].replace(/:/g, '');
        return `${date}_${time}`;
    };

    const formatFrequencyShort = (freqHz) => {
        const freqMHz = freqHz / 1e6;
        // Replace decimal point with underscore for filename compatibility
        return `${freqMHz.toFixed(3).replace('.', '_')}MHz`;
    };

    const sanitizeFilename = (name) => {
        // Replace spaces and special characters with underscores, keep only alphanumeric, dash, underscore
        return name.replace(/[^a-zA-Z0-9\-_]/g, '_').replace(/_+/g, '_');
    };

    const handleStartRecording = () => {
        let baseName = localRecordingName.trim();

        // If empty, generate name: <satellite-name>-<center-freq>-<timestamp>
        if (!baseName) {
            const satName = sanitizeFilename(targetSatelliteName || 'unknown');
            const freqShort = formatFrequencyShort(centerFrequency);
            const timestamp = generateTimestamp();
            baseName = `${satName}-${freqShort}-${timestamp}`;
        } else {
            // Sanitize user-provided name
            baseName = sanitizeFilename(baseName);
        }

        // Generate the actual filename with timestamp (matching backend logic)
        const timestamp = generateTimestamp();
        const actualFilename = `${baseName}_${timestamp}`;

        // Store the actual filename for display during recording
        setRecordingStartFilename(actualFilename);

        // Update Redux state with the name
        onRecordingNameChange(baseName);

        // Pass the base name directly to avoid race condition with Redux state update
        onStartRecording(baseName);
    };

    const handleNameChange = (e) => {
        const value = e.target.value;
        setLocalRecordingName(value);
        onRecordingNameChange(value);
    };

    const canStartRecording = isStreaming && !isRecording && selectedSDRId !== "none" && selectedSDRId !== "sigmf-playback";

    const formatBytes = (bytes) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
    };

    const usagePercent = diskUsage.total > 0 ? ((diskUsage.used / diskUsage.total) * 100) : 0;

    return (
        <Accordion expanded={expanded} onChange={onAccordionChange}>
            <AccordionSummary
                sx={{
                    boxShadow: '-1px 4px 7px #00000059',
                    ...(isRecording && { backgroundColor: 'rgba(255, 0, 0, 0.1)' }),
                }}
                aria-controls="panel-recording-content"
                id="panel-recording-header"
            >
                <Stack direction="row" spacing={1} alignItems="center" width="100%" justifyContent="space-between">
                    <Typography component="span">
                        {t('recording.title', 'IQ Recording')}
                    </Typography>
                    {isRecording && (
                        <Chip
                            icon={<FiberManualRecordIcon />}
                            label={formatDuration(recordingDuration)}
                            color="error"
                            size="small"
                            sx={{
                                animation: 'pulse 2s ease-in-out infinite',
                                '@keyframes pulse': {
                                    '0%, 100%': { opacity: 1 },
                                    '50%': { opacity: 0.6 },
                                },
                                fontWeight: 'bold',
                            }}
                        />
                    )}
                </Stack>
            </AccordionSummary>
            <AccordionDetails
                sx={{
                    backgroundColor: 'background.elevated',
                }}
            >
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <TextField
                        label={t('recording.filename', 'Recording Name')}
                        value={localRecordingName}
                        onChange={handleNameChange}
                        disabled={isRecording}
                        size="small"
                        fullWidth
                        variant="outlined"
                        placeholder="unknown_recording"
                    />

                    {/* Disk Space Progress Bar */}
                    {diskUsage.total > 0 && (
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                            <Stack direction="row" justifyContent="space-between" alignItems="center">
                                <Typography variant="caption" color="text.secondary">
                                    {t('recording.diskSpace', 'Disk Space')}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                    {formatBytes(diskUsage.available)} {t('recording.available', 'available')} / {formatBytes(diskUsage.total)}
                                </Typography>
                            </Stack>
                            <LinearProgress
                                variant="determinate"
                                value={usagePercent}
                                sx={{
                                    height: 8,
                                    borderRadius: 1,
                                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                                    '& .MuiLinearProgress-bar': {
                                        borderRadius: 1,
                                        backgroundColor: usagePercent > 90 ? 'error.main' : usagePercent > 75 ? 'warning.main' : 'success.main',
                                    },
                                }}
                            />
                        </Box>
                    )}

                    <Stack direction="row" spacing={1}>
                        <Button
                            variant="contained"
                            color="error"
                            startIcon={<FiberManualRecordIcon />}
                            onClick={handleStartRecording}
                            disabled={!canStartRecording}
                            fullWidth
                        >
                            {t('recording.start', 'RECORD')}
                        </Button>
                        <Button
                            variant="outlined"
                            color="inherit"
                            startIcon={<StopIcon />}
                            onClick={onStopRecording}
                            disabled={!isRecording}
                            fullWidth
                        >
                            {t('recording.stop', 'Stop')}
                        </Button>
                    </Stack>
                </Box>
            </AccordionDetails>
        </Accordion>
    );
};

function areRecordingAccordionPropsEqual(prevProps, nextProps) {
    return (
        prevProps.expanded === nextProps.expanded &&
        prevProps.onAccordionChange === nextProps.onAccordionChange &&
        prevProps.isRecording === nextProps.isRecording &&
        prevProps.recordingDuration === nextProps.recordingDuration &&
        prevProps.recordingName === nextProps.recordingName &&
        prevProps.actualRecordingName === nextProps.actualRecordingName &&
        prevProps.onRecordingNameChange === nextProps.onRecordingNameChange &&
        prevProps.onStartRecording === nextProps.onStartRecording &&
        prevProps.onStopRecording === nextProps.onStopRecording &&
        prevProps.isStreaming === nextProps.isStreaming &&
        prevProps.selectedSDRId === nextProps.selectedSDRId &&
        prevProps.centerFrequency === nextProps.centerFrequency
    );
}

export default React.memo(RecordingAccordion, areRecordingAccordionPropsEqual);
