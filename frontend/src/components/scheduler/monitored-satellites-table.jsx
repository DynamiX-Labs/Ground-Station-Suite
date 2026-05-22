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

import React, { useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { DataGrid, gridClasses } from '@mui/x-data-grid';
import {
    Box,
    Chip,
    IconButton,
    Tooltip,
    Switch,
    Stack,
    Button,
    Paper,
    Typography,
    Alert,
    AlertTitle,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    FormControlLabel,
    Checkbox,
} from '@mui/material';
import {
    Delete as DeleteIcon,
    Edit as EditIcon,
    Add as AddIcon,
    Refresh as RefreshIcon,
    CheckCircle as EnableIcon,
    Cancel as DisableIcon,
} from '@mui/icons-material';
import { alpha } from '@mui/material/styles';
import { useSocket } from '../common/socket.jsx';
import {
    setSelectedMonitoredSatellite,
    setMonitoredSatelliteDialogOpen,
    deleteMonitoredSatellitesAsync,
    toggleMonitoredSatelliteEnabledAsync,
    fetchMonitoredSatellites,
} from './scheduler-slice.jsx';
import RegenerationPreviewDialog from './regeneration-preview-dialog.jsx';
import { toRowSelectionModel, toSelectedIds } from '../../utils/datagrid-selection.js';
import { getFlattenedTasks, getSessionSdrs } from './session-utils.js';

const MonitoredSatellitesTable = () => {
    const dispatch = useDispatch();
    const { socket } = useSocket();
    const [selectedIds, setSelectedIds] = useState([]);
    const [openDeleteConfirm, setOpenDeleteConfirm] = useState(false);
    const [deleteObservations, setDeleteObservations] = useState(false);
    const [openRegenerateConfirm, setOpenRegenerateConfirm] = useState(false);
    const [openPreviewDialog, setOpenPreviewDialog] = useState(false);
    const [previewData, setPreviewData] = useState(null);
    const [isLoadingPreview, setIsLoadingPreview] = useState(false);
    const [regenerationTargetId, setRegenerationTargetId] = useState(null);
    const [openNoEnabledDialog, setOpenNoEnabledDialog] = useState(false);

    const monitoredSatellites = useSelector((state) => state.scheduler?.monitoredSatellites || []);
    const loading = useSelector((state) => state.scheduler?.monitoredSatellitesLoading || false);
    const rotators = useSelector((state) => state.rotators?.rotators || []);
    const rowSelectionModel = useMemo(() => toRowSelectionModel(selectedIds), [selectedIds]);
    const rotatorNameById = useMemo(() => {
        const mapping = {};
        rotators.forEach((rotator) => {
            const rotatorId = rotator?.id;
            if (!rotatorId) return;
            mapping[String(rotatorId)] = rotator?.name || '';
        });
        return mapping;
    }, [rotators]);

    useEffect(() => {
        if (socket) {
            dispatch(fetchMonitoredSatellites({ socket }));
        }
    }, [socket, dispatch]);

    const handleDelete = () => {
        if (selectedIds.length > 0 && socket) {
            dispatch(deleteMonitoredSatellitesAsync({ socket, ids: selectedIds, deleteObservations }));
            setSelectedIds([]);
            setOpenDeleteConfirm(false);
            setDeleteObservations(false);
        }
    };

    const handleEdit = (monitoredSatellite) => {
        dispatch(setSelectedMonitoredSatellite(monitoredSatellite));
        dispatch(setMonitoredSatelliteDialogOpen(true));
    };

    const handleAdd = () => {
        dispatch(setSelectedMonitoredSatellite(null));
        dispatch(setMonitoredSatelliteDialogOpen(true));
    };

    const handleToggleEnabled = (id, currentEnabled) => {
        if (socket) {
            dispatch(toggleMonitoredSatelliteEnabledAsync({ socket, id, enabled: !currentEnabled }));
        }
    };

    const handleBulkEnable = () => {
        if (selectedIds.length > 0 && socket) {
            selectedIds.forEach(id => {
                dispatch(toggleMonitoredSatelliteEnabledAsync({ socket, id, enabled: true }));
            });
        }
    };

    const handleBulkDisable = () => {
        if (selectedIds.length > 0 && socket) {
            selectedIds.forEach(id => {
                dispatch(toggleMonitoredSatelliteEnabledAsync({ socket, id, enabled: false }));
            });
        }
    };

    const triggerRegenerationPreview = (monitoredSatelliteId) => {
        if (socket) {
            setIsLoadingPreview(true);
            setRegenerationTargetId(monitoredSatelliteId);

            socket.emit('data_submission', 'regenerate-observations', {
                monitored_satellite_id: monitoredSatelliteId,
                dry_run: true
            }, (response) => {
                setIsLoadingPreview(false);
                if (response.success && response.dry_run) {
                    setPreviewData(response);
                    setOpenPreviewDialog(true);
                } else {
                    console.error('Dry-run failed:', response.error);
                }
            });
        }
    };

    const handleRegenerateSelectedClick = () => {
        if (selectedIds.length === 1) {
            triggerRegenerationPreview(selectedIds[0]);
        }
    };

    const handleRegenerateAllEnabledClick = () => {
        const hasEnabled = monitoredSatellites.some((sat) => sat.enabled);
        if (!hasEnabled) {
            setOpenNoEnabledDialog(true);
            return;
        }
        triggerRegenerationPreview(null);
    };

    const handlePreviewConfirm = (conflictChoices) => {
        if (socket) {
            socket.emit('data_submission', 'regenerate-observations', {
                monitored_satellite_id: regenerationTargetId,
                dry_run: false,
                user_conflict_overrides: conflictChoices
            }, (response) => {
                if (response.success) {
                    console.log('Regeneration successful:', response.data);
                    setOpenPreviewDialog(false);
                    setPreviewData(null);
                    setRegenerationTargetId(null);
                } else {
                    console.error('Regeneration failed:', response.error);
                }
            });
        }
    };

    const columns = [
        {
            field: 'enabled',
            headerName: 'Enabled',
            width: 90,
            renderCell: (params) => (
                <Switch
                    checked={params.value}
                    onClick={(e) => e.stopPropagation()}
                    onChange={() => handleToggleEnabled(params.row.id, params.value)}
                    size="small"
                />
            ),
        },
        {
            field: 'satellite',
            headerName: 'Satellite',
            flex: 1,
            minWidth: 150,
            valueGetter: (value, row) => row.satellite?.name || '-',
        },
        {
            field: 'min_elevation',
            headerName: 'Peak El.',
            width: 90,
            renderCell: (params) => (
                <Typography variant="body2">{params.value}°</Typography>
            ),
        },
        {
            field: 'task_start_elevation',
            headerName: 'Start El.',
            width: 90,
            renderCell: (params) => (
                <Typography variant="body2">{params.value !== undefined ? `${params.value}°` : '-'}</Typography>
            ),
        },
        {
            field: 'lookahead_hours',
            headerName: 'Lookahead',
            width: 110,
            renderCell: (params) => (
                <Typography variant="body2">{params.value}h</Typography>
            ),
        },
        {
            field: 'sdr',
            headerName: 'SDR',
            flex: 1.5,
            minWidth: 200,
            renderCell: (params) => {
                const sdrs = getSessionSdrs(params.row);
                if (!sdrs.length) return '-';

                const formatSdr = (sdr) => {
                    const freqMHz = sdr.center_frequency ? (sdr.center_frequency / 1000000).toFixed(2) : '?';
                    const gain = (sdr.gain !== undefined && sdr.gain !== null && sdr.gain !== '') ? sdr.gain : '?';
                    const antenna = sdr.antenna_port || '?';
                    return `${sdr.name || 'SDR'} • ${freqMHz}MHz • ${gain}dB • ${antenna}`;
                };

                if (sdrs.length === 1) {
                    return (
                        <Typography variant="body2" sx={{ fontSize: '0.8125rem' }}>
                            {formatSdr(sdrs[0])}
                        </Typography>
                    );
                }

                return (
                    <Stack spacing={0.5} sx={{ py: 0.5 }}>
                        {sdrs.map((sdr, idx) => (
                            <Typography key={idx} variant="body2" sx={{ fontSize: '0.75rem' }}>
                                {formatSdr(sdr)}
                            </Typography>
                        ))}
                    </Stack>
                );
            },
        },
        {
            field: 'rotator',
            headerName: 'Rotator',
            minWidth: 180,
            flex: 1,
            cellClassName: 'target-rotator-nowrap-cell',
            headerClassName: 'target-rotator-nowrap-header',
            renderCell: (params) => {
                const rotator = params.value || {};
                const rotatorId = rotator?.id || '';
                const rotatorName = rotator?.name || (rotatorId ? rotatorNameById[String(rotatorId)] : '');
                const primaryLabel = rotatorName || (rotatorId ? 'Configured rotator' : 'No rotator');
                const secondaryLabel = rotatorId
                    ? (rotator?.tracking_enabled ? 'Tracking enabled' : 'Tracking disabled')
                    : 'Not configured';
                return (
                    <Stack
                        direction="row"
                        spacing={0.8}
                        alignItems="center"
                        sx={{ py: 0.5, width: '100%', whiteSpace: 'nowrap', overflow: 'hidden' }}
                    >
                        <Chip
                            size="small"
                            color={rotatorId ? 'primary' : 'default'}
                            variant={rotatorId ? 'filled' : 'outlined'}
                            label={primaryLabel}
                            sx={{ flexShrink: 0 }}
                        />
                        <Typography variant="caption" color="text.secondary" noWrap>
                            {secondaryLabel}
                        </Typography>
                    </Stack>
                );
            },
        },
        {
            field: 'tasks',
            headerName: 'Tasks',
            flex: 1,
            minWidth: 180,
            renderCell: (params) => {
                const tasks = getFlattenedTasks(params.row);
                if (!tasks.length) return '-';
                return (
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ py: 0.5 }}>
                        {tasks.map((task, idx) => {
                            let label = '';
                            let color = 'default';

                            if (task.type === 'decoder') {
                                const decoderType = task.config.decoder_type || 'unknown';
                                const typeMap = {
                                    'lora': 'LoRa',
                                    'none': 'No Decoder'
                                };
                                label = typeMap[decoderType] || decoderType.toUpperCase();
                                color = 'primary';
                            } else if (task.type === 'audio_recording') {
                                label = 'Audio';
                                color = 'secondary';
                            } else if (task.type === 'transcription') {
                                label = 'Transcription';
                                color = 'info';
                            } else if (task.type === 'iq_recording') {
                                label = 'IQ';
                                color = 'default';
                            }

                            return (
                                <Chip
                                    key={idx}
                                    label={label}
                                    size="small"
                                    color={color}
                                    variant="filled"
                                />
                            );
                        })}
                    </Stack>
                );
            },
        },
        {
            field: 'actions',
            headerName: 'Actions',
            width: 80,
            align: 'center',
            headerAlign: 'center',
            sortable: false,
            filterable: false,
            renderCell: (params) => (
                <Tooltip title="Edit">
                    <IconButton
                        size="small"
                        onClick={(e) => {
                            e.stopPropagation();
                            handleEdit(params.row);
                        }}
                    >
                        <EditIcon fontSize="small" />
                    </IconButton>
                </Tooltip>
            ),
        },
    ];

    return (
        <Paper elevation={3} sx={{ p: 2, display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5 }}>
                Monitored Satellites
            </Typography>

            <Alert severity="success" sx={{ mb: 2, flexShrink: 0 }}>
                <AlertTitle>Automatic Observation Generation</AlertTitle>
                Satellites in this list will automatically generate scheduled observations for all upcoming passes that meet the specified criteria (minimum elevation, lookahead window).
            </Alert>

            <Box sx={{ width: '100%', minWidth: 0, overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
                <DataGrid
                    autoHeight
                    rows={monitoredSatellites}
                    columns={columns}
                    loading={loading}
                    checkboxSelection
                    disableRowSelectionExcludeModel
                    rowSelectionModel={rowSelectionModel}
                    onRowSelectionModelChange={(newSelection) => {
                        setSelectedIds(toSelectedIds(newSelection));
                    }}
                    initialState={{
                        pagination: {
                            paginationModel: { pageSize: 25 },
                        },
                        sorting: {
                            sortModel: [{ field: 'satellite', sort: 'asc' }],
                        },
                    }}
                    pageSizeOptions={[10, 25, 50, {value: -1, label: 'All'}]}
                    localeText={{
                        noRowsLabel: 'No monitored satellites'
                    }}
                    sx={{
                        border: 0,
                        width: '100%',
                        '& .MuiDataGrid-main': {
                            overflowX: 'auto',
                        },
                        '& .MuiDataGrid-virtualScroller': {
                            overflowX: 'auto',
                            touchAction: 'pan-x pan-y',
                        },
                        [`& .${gridClasses.cell}:focus, & .${gridClasses.cell}:focus-within`]: {
                            outline: 'none',
                        },
                        [`& .${gridClasses.columnHeader}:focus, & .${gridClasses.columnHeader}:focus-within`]: {
                            outline: 'none',
                        },
                        '& .MuiDataGrid-columnHeaders': {
                            backgroundColor: (theme) => alpha(
                                theme.palette.primary.main,
                                theme.palette.mode === 'dark' ? 0.18 : 0.10
                            ),
                            borderBottom: (theme) => `2px solid ${alpha(theme.palette.primary.main, 0.45)}`,
                        },
                        '& .MuiDataGrid-columnHeader': {
                            backgroundColor: 'transparent',
                        },
                        '& .MuiDataGrid-columnHeaderTitle': {
                            fontSize: '0.8125rem',
                            fontWeight: 700,
                            letterSpacing: '0.02em',
                        },
                        '& .MuiDataGrid-overlay': {
                            fontSize: '0.875rem',
                            fontStyle: 'italic',
                            color: 'text.secondary',
                        },
                        '& .MuiDataGrid-cell': {
                            display: 'flex',
                            alignItems: 'center',
                        },
                        '& .target-rotator-nowrap-cell': {
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                        },
                        '& .target-rotator-nowrap-header .MuiDataGrid-columnHeaderTitle': {
                            whiteSpace: 'nowrap',
                        },
                    }}
                />
            </Box>

            {/* Actions below table */}
            <Stack direction="row" spacing={1} sx={{ marginTop: '15px', flexShrink: 0, flexWrap: 'wrap', width: '100%' }}>
                <Button
                    variant="contained"
                    onClick={handleAdd}
                    sx={{
                        minWidth: 'auto',
                        px: { xs: 1, md: 2 }
                    }}
                >
                    <AddIcon sx={{ display: { xs: 'block', md: 'none' } }} />
                    <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }}>
                        <AddIcon sx={{ mr: 1 }} />
                        Add
                    </Box>
                </Button>
                <Button
                    variant="contained"
                    onClick={() => {
                        if (selectedIds.length === 1) {
                            const monitoredSatellite = monitoredSatellites.find(ms => ms.id === selectedIds[0]);
                            if (monitoredSatellite) handleEdit(monitoredSatellite);
                        }
                    }}
                    disabled={selectedIds.length !== 1}
                    sx={{
                        minWidth: 'auto',
                        px: { xs: 1, md: 2 }
                    }}
                >
                    <EditIcon sx={{ display: { xs: 'block', md: 'none' } }} />
                    <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }}>
                        <EditIcon sx={{ mr: 1 }} />
                        Edit
                    </Box>
                </Button>
                <Button
                    variant="contained"
                    color="success"
                    onClick={handleBulkEnable}
                    disabled={selectedIds.length === 0}
                    sx={{
                        minWidth: 'auto',
                        px: { xs: 1, md: 2 }
                    }}
                >
                    <EnableIcon sx={{ display: { xs: 'block', md: 'none' } }} />
                    <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }}>
                        <EnableIcon sx={{ mr: 1 }} />
                        Enable
                    </Box>
                </Button>
                <Button
                    variant="contained"
                    color="secondary"
                    onClick={handleBulkDisable}
                    disabled={selectedIds.length === 0}
                    sx={{
                        minWidth: 'auto',
                        px: { xs: 1, md: 2 }
                    }}
                >
                    <DisableIcon sx={{ display: { xs: 'block', md: 'none' } }} />
                    <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }}>
                        <DisableIcon sx={{ mr: 1 }} />
                        Disable
                    </Box>
                </Button>
                <Tooltip
                    title={
                        selectedIds.length === 1
                            ? "Regenerate observations for the selected satellite only"
                            : "Please select exactly one satellite to regenerate observations"
                    }
                    arrow
                >
                    <span>
                        <Button
                            variant="contained"
                            color="warning"
                            onClick={handleRegenerateSelectedClick}
                            disabled={selectedIds.length !== 1 || isLoadingPreview}
                            sx={{
                                minWidth: 'auto',
                                px: { xs: 1, md: 2 }
                            }}
                        >
                            <RefreshIcon sx={{ display: { xs: 'block', md: 'none' } }} />
                            <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }}>
                                <RefreshIcon sx={{ mr: 1 }} />
                                {isLoadingPreview ? 'Loading Preview...' : 'Regenerate'}
                            </Box>
                        </Button>
                    </span>
                </Tooltip>
                <Button
                    variant="contained"
                    color="error"
                    onClick={() => setOpenDeleteConfirm(true)}
                    disabled={selectedIds.length === 0}
                    sx={{
                        minWidth: 'auto',
                        px: { xs: 1, md: 2 }
                    }}
                >
                    <DeleteIcon sx={{ display: { xs: 'block', md: 'none' } }} />
                    <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }}>
                        <DeleteIcon sx={{ mr: 1 }} />
                        Delete
                    </Box>
                </Button>
                <Box sx={{ flexGrow: 1 }} />
                <Box sx={{ display: 'flex' }}>
                    <Tooltip
                        title="Regenerate observations for ALL enabled satellites"
                        arrow
                    >
                        <span>
                            <Button
                                variant="contained"
                                color="warning"
                                onClick={handleRegenerateAllEnabledClick}
                                disabled={isLoadingPreview}
                                sx={{
                                    minWidth: 'auto',
                                    px: { xs: 1, md: 2 }
                                }}
                            >
                                <RefreshIcon sx={{ display: { xs: 'block', md: 'none' } }} />
                                <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }}>
                                    <RefreshIcon sx={{ mr: 1 }} />
                                    Regenerate All Enabled
                                </Box>
                            </Button>
                        </span>
                    </Tooltip>
                </Box>
            </Stack>

            {/* Delete Confirmation Dialog */}
            <Dialog
                open={openDeleteConfirm}
                onClose={() => setOpenDeleteConfirm(false)}
                maxWidth="sm"
                fullWidth
                PaperProps={{
                    sx: {
                        bgcolor: 'background.paper',
                        borderRadius: 2,
                    }
                }}
            >
                <DialogTitle
                    sx={{
                        bgcolor: 'error.main',
                        color: 'error.contrastText',
                        fontSize: '1.125rem',
                        fontWeight: 600,
                        py: 2,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1.5,
                    }}
                >
                    <Box
                        component="span"
                        sx={{
                            width: 24,
                            height: 24,
                            borderRadius: '50%',
                            bgcolor: 'error.contrastText',
                            color: 'error.main',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 'bold',
                            fontSize: '1rem',
                        }}
                    >
                        !
                    </Box>
                    Confirm Deletion
                </DialogTitle>
                <DialogContent
                    sx={{
                        bgcolor: (theme) => (
                            theme.palette.mode === 'dark'
                                ? theme.palette.background.elevated
                                : theme.palette.background.paper
                        ),
                        px: 3,
                        pt: 3,
                        pb: 3,
                    }}
                >
                    <Typography variant="body1" sx={{ mt: 2, mb: 2, color: 'text.primary' }}>
                        Are you sure you want to delete {selectedIds.length} monitored satellite(s)? This will stop automatic observation generation for these satellites.
                    </Typography>
                    <FormControlLabel
                        control={
                            <Checkbox
                                checked={deleteObservations}
                                onChange={(e) => setDeleteObservations(e.target.checked)}
                                color="error"
                            />
                        }
                        label="Also delete all scheduled observations for these satellites"
                        sx={{ mb: 2 }}
                    />
                    <Typography variant="body2" sx={{ mb: 2, fontWeight: 600, color: 'text.secondary' }}>
                        {selectedIds.length === 1 ? 'Monitored satellite to be deleted:' : `${selectedIds.length} Monitored satellites to be deleted:`}
                    </Typography>
                    <Box sx={{
                        maxHeight: 300,
                        overflowY: 'auto',
                        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
                        borderRadius: 1,
                        border: (theme) => `1px solid ${theme.palette.divider}`,
                    }}>
                        {selectedIds.map((id, index) => {
                            const monSat = monitoredSatellites.find(ms => ms.id === id);
                            if (!monSat) return null;
                            return (
                                <Box
                                    key={id}
                                    sx={{
                                        p: 2,
                                        borderBottom: index < selectedIds.length - 1 ? (theme) => `1px solid ${theme.palette.divider}` : 'none',
                                    }}
                                >
                                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'text.primary' }}>
                                        {monSat.satellite?.name || 'Unknown Satellite'}
                                    </Typography>
                                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                                        <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary' }}>
                                            NORAD ID: <Typography component="span" sx={{ fontSize: '0.813rem', color: 'text.primary', fontWeight: 500 }}>{monSat.satellite?.norad_id || 'N/A'}</Typography>
                                        </Typography>
                                        <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary' }}>
                                            Status: <Typography component="span" sx={{ fontSize: '0.813rem', color: 'text.primary', fontWeight: 500 }}>{monSat.enabled ? 'Enabled' : 'Disabled'}</Typography>
                                        </Typography>
                                        {monSat.min_elevation != null && (
                                            <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary' }}>
                                                Min Elevation: <Typography component="span" sx={{ fontSize: '0.813rem', color: 'text.primary', fontWeight: 500 }}>{monSat.min_elevation}°</Typography>
                                            </Typography>
                                        )}
                                    </Box>
                                </Box>
                            );
                        })}
                    </Box>
                </DialogContent>
                <DialogActions
                    sx={{
                        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
                        borderTop: (theme) => `1px solid ${theme.palette.divider}`,
                        px: 3,
                        py: 2,
                        gap: 1.5,
                    }}
                >
                    <Button
                        onClick={() => {
                            setOpenDeleteConfirm(false);
                            setDeleteObservations(false);
                        }}
                        variant="outlined"
                        color="inherit"
                        sx={{
                            minWidth: 100,
                            textTransform: 'none',
                            fontWeight: 500,
                        }}
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="contained"
                        onClick={handleDelete}
                        color="error"
                        sx={{
                            minWidth: 100,
                            textTransform: 'none',
                            fontWeight: 600,
                        }}
                    >
                        Delete
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Regeneration Preview Dialog */}
            <RegenerationPreviewDialog
                open={openPreviewDialog}
                onClose={() => {
                    setOpenPreviewDialog(false);
                    setPreviewData(null);
                    setRegenerationTargetId(null);
                }}
                previewData={previewData}
                onConfirm={handlePreviewConfirm}
            />

            {/* No Enabled Monitors Dialog */}
            <Dialog
                open={openNoEnabledDialog}
                onClose={() => setOpenNoEnabledDialog(false)}
                maxWidth="xs"
                fullWidth
            >
                <DialogTitle>No Enabled Monitors</DialogTitle>
                <DialogContent
                    sx={{
                        bgcolor: (theme) => (
                            theme.palette.mode === 'dark'
                                ? theme.palette.background.elevated
                                : theme.palette.background.paper
                        ),
                    }}
                >
                    <Typography variant="body2">
                        There are no enabled monitored satellites. Enable at least one monitor to regenerate observations.
                    </Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setOpenNoEnabledDialog(false)} variant="contained">
                        OK
                    </Button>
                </DialogActions>
            </Dialog>
        </Paper>
    );
};

export default MonitoredSatellitesTable;
