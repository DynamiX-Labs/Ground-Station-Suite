import React, { useEffect, useMemo, useState } from 'react';
import { DataGrid, gridClasses } from '@mui/x-data-grid';
import { alpha, styled } from '@mui/material/styles';
import {
    Box,
    Button,
    Checkbox,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Divider,
    FormControl,
    FormControlLabel,
    FormGroup,
    InputLabel,
    MenuItem,
    Select,
    Typography,
} from '@mui/material';
import { useDispatch, useSelector } from 'react-redux';
import {
    setSelectedMonitoredIds,
    setMonitoredTableColumnVisibility,
    setMonitoredTablePageSize,
    setMonitoredTableSortModel,
    setOpenGridSettingsDialog,
} from './monitored-slice.jsx';
import { toRowSelectionModel, toSelectedIds } from '../../utils/datagrid-selection.js';
import { useUserTimeSettings } from '../../hooks/useUserTimeSettings.jsx';

const AU_IN_KM = 149597870.7;
const SECONDS_PER_DAY = 86400;
const AU_PER_DAY_TO_KM_PER_S = AU_IN_KM / SECONDS_PER_DAY;
const LIGHT_TIME_MIN_PER_AU = 8.316746397;
const DIALOG_PAPER_SX = {
    bgcolor: 'background.paper',
    border: (theme) => `1px solid ${theme.palette.divider}`,
    borderRadius: 2,
};
const DIALOG_TITLE_SX = {
    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.100',
    borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
    fontSize: '1.25rem',
    fontWeight: 'bold',
    py: 2.5,
};
const DIALOG_CONTENT_SX = {
    px: 3,
    py: 3,
};
const DIALOG_ACTIONS_SX = {
    bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.100',
    borderTop: (theme) => `1px solid ${theme.palette.divider}`,
    px: 3,
    py: 2.5,
    gap: 2,
};
const DIALOG_CANCEL_BUTTON_SX = {
    borderColor: (theme) => theme.palette.mode === 'dark' ? 'grey.700' : 'grey.400',
    '&:hover': {
        borderColor: (theme) => theme.palette.mode === 'dark' ? 'grey.600' : 'grey.500',
        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.800' : 'grey.200',
    },
};

const StyledDataGrid = styled(DataGrid)(({ theme }) => ({
    '& .MuiDataGrid-row': {
        borderLeft: '3px solid transparent',
    },
    '& .celestial-row-visible': {
        backgroundColor: alpha(theme.palette.success.main, 0.15),
        borderLeftColor: alpha(theme.palette.success.main, 0.9),
        ...theme.applyStyles('light', {
            backgroundColor: alpha(theme.palette.success.main, 0.08),
            borderLeftColor: alpha(theme.palette.success.main, 0.6),
        }),
        '&:hover': {
            backgroundColor: alpha(theme.palette.success.main, 0.2),
            ...theme.applyStyles('light', {
                backgroundColor: alpha(theme.palette.success.main, 0.12),
            }),
        },
    },
    '& .celestial-row-below': {
        backgroundColor: alpha(theme.palette.info.main, 0.1),
        borderLeftColor: alpha(theme.palette.info.main, 0.75),
        ...theme.applyStyles('light', {
            backgroundColor: alpha(theme.palette.info.main, 0.05),
            borderLeftColor: alpha(theme.palette.info.main, 0.5),
        }),
    },
    '& .celestial-row-dead': {
        backgroundColor: alpha(theme.palette.error.main, 0.18),
        borderLeftColor: alpha(theme.palette.error.main, 0.9),
        ...theme.applyStyles('light', {
            backgroundColor: alpha(theme.palette.error.main, 0.1),
            borderLeftColor: alpha(theme.palette.error.main, 0.65),
        }),
        '& .MuiDataGrid-cell': {
            color: theme.palette.text.secondary,
        },
    },
    '& .celestial-row-unknown': {
        borderLeftColor: alpha(theme.palette.text.secondary, 0.55),
    },
    '& .celestial-row-selected': {
        backgroundColor: alpha(theme.palette.secondary.main, 0.25),
        borderLeftColor: alpha(theme.palette.secondary.main, 0.95),
        fontWeight: 'bold',
        ...theme.applyStyles('light', {
            backgroundColor: alpha(theme.palette.secondary.main, 0.12),
            borderLeftColor: alpha(theme.palette.secondary.main, 0.75),
        }),
        '&:hover': {
            backgroundColor: alpha(theme.palette.secondary.main, 0.3),
            ...theme.applyStyles('light', {
                backgroundColor: alpha(theme.palette.secondary.main, 0.16),
            }),
        },
    },
}));

const formatNumeric = (value, digits = 3) => {
    if (!Number.isFinite(value)) return '-';
    return Number(value).toFixed(digits);
};

const formatLastRefresh = (value, timezone, locale) => {
    if (!value) return 'Never';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return 'Unknown';
    const options = timezone ? { timeZone: timezone } : undefined;
    return parsed.toLocaleString(locale, options);
};

const formatAge = (value, nowMs) => {
    if (!value) return 'Never';
    const parsed = new Date(value).getTime();
    if (!Number.isFinite(parsed)) return 'Unknown';
    const diffSec = Math.max(0, Math.floor((nowMs - parsed) / 1000));
    if (diffSec < 60) return `${diffSec}s`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h`;
    return `${Math.floor(diffSec / 86400)}d`;
};

const magnitude3 = (vector) => {
    if (!Array.isArray(vector) || vector.length < 3) return NaN;
    const [x, y, z] = vector;
    if (![x, y, z].every((v) => Number.isFinite(v))) return NaN;
    return Math.sqrt(x * x + y * y + z * z);
};

const computeProjectionSpan = (orbitSampling) => {
    const past = Number(orbitSampling?.past_hours);
    const future = Number(orbitSampling?.future_hours);
    const step = Number(orbitSampling?.step_minutes);
    if (!Number.isFinite(past) || !Number.isFinite(future) || !Number.isFinite(step)) {
        return '-';
    }
    return `${past}h / ${future}h @ ${step}m`;
};

const buildTargetKey = (entry) => {
    const type = String(entry?.targetType || entry?.target_type || 'mission').toLowerCase();
    if (type === 'body') {
        const bodyId = String(entry?.bodyId || entry?.body_id || entry?.command || '').toLowerCase();
        return bodyId ? `body:${bodyId}` : '';
    }
    const command = String(entry?.command || '').trim();
    return command ? `mission:${command}` : '';
};

const getVisibilityState = (visible, elevationDeg) => {
    if (typeof visible === 'boolean') {
        return visible ? 'visible' : 'below';
    }
    if (Number.isFinite(elevationDeg)) {
        return elevationDeg > 0 ? 'visible' : 'below';
    }
    return 'unknown';
};

const formatAngle = (value, digits = 1) => {
    if (!Number.isFinite(value)) return '-';
    return `${Number(value).toFixed(digits)}°`;
};

const SettingsDialog = ({ open, onClose }) => {
    const dispatch = useDispatch();
    const columnVisibility = useSelector((state) => state.celestialMonitored.tableColumnVisibility);
    const tablePageSize = useSelector((state) => state.celestialMonitored.tablePageSize);

    const columns = [
        { name: 'displayName', label: 'Name', category: 'identity', alwaysVisible: true },
        { name: 'targetType', label: 'Type', category: 'identity' },
        { name: 'command', label: 'Target ID', category: 'identity' },
        { name: 'source', label: 'Source', category: 'identity' },
        { name: 'sourceMode', label: 'Source Mode', category: 'identity' },
        { name: 'enabled', label: 'Enabled', category: 'state' },
        { name: 'elevationDeg', label: 'Elevation (deg)', category: 'state' },
        { name: 'azimuthDeg', label: 'Azimuth (deg)', category: 'state' },
        { name: 'distanceFromSunAu', label: 'Distance from Sun (AU)', category: 'metrics' },
        { name: 'speedKmS', label: 'Speed (km/s)', category: 'metrics' },
        { name: 'lightTimeMinutes', label: 'Light Time (min)', category: 'metrics' },
        { name: 'lastRefreshAt', label: 'Last Refresh', category: 'state' },
        { name: 'lastRefreshAge', label: 'Refresh Age', category: 'state' },
        { name: 'projectionSpan', label: 'Projection Span', category: 'projection' },
        { name: 'cacheStatus', label: 'Cache', category: 'projection' },
        { name: 'stale', label: 'Stale', category: 'projection' },
        { name: 'sampleCount', label: 'Samples', category: 'projection' },
        { name: 'lastError', label: 'Last Error', category: 'state' },
    ];

    const categories = {
        identity: 'Identity',
        state: 'State',
        metrics: 'Metrics',
        projection: 'Projection',
    };

    const columnsByCategory = {
        identity: columns.filter((col) => col.category === 'identity'),
        state: columns.filter((col) => col.category === 'state'),
        metrics: columns.filter((col) => col.category === 'metrics'),
        projection: columns.filter((col) => col.category === 'projection'),
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth PaperProps={{ sx: DIALOG_PAPER_SX }}>
            <DialogTitle sx={DIALOG_TITLE_SX}>Monitored Celestial Table Settings</DialogTitle>
            <DialogContent sx={DIALOG_CONTENT_SX}>
                <Box sx={{ mb: 2 }}>
                    <FormControl fullWidth size="small" sx={{ mt: 2 }}>
                        <InputLabel id="celestial-table-rows-label">Rows per page</InputLabel>
                        <Select
                            labelId="celestial-table-rows-label"
                            value={tablePageSize}
                            label="Rows per page"
                            onChange={(event) => dispatch(setMonitoredTablePageSize(event.target.value))}
                        >
                            {[5, 10, 15, 20, 25].map((option) => (
                                <MenuItem key={option} value={option}>
                                    {option}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <Divider sx={{ mt: 2 }} />
                </Box>

                {Object.entries(columnsByCategory).map(([category, cols]) => (
                    <Box key={category} sx={{ mb: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
                            {categories[category]}
                        </Typography>
                        <FormGroup>
                            {cols.map((column) => (
                                <FormControlLabel
                                    key={column.name}
                                    control={
                                        <Checkbox
                                            checked={column.alwaysVisible || columnVisibility[column.name] !== false}
                                            onChange={() =>
                                                dispatch(
                                                    setMonitoredTableColumnVisibility({
                                                        ...columnVisibility,
                                                        [column.name]: !columnVisibility[column.name],
                                                    }),
                                                )
                                            }
                                            disabled={column.alwaysVisible}
                                        />
                                    }
                                    label={column.label}
                                />
                            ))}
                        </FormGroup>
                        <Divider sx={{ mt: 1 }} />
                    </Box>
                ))}
            </DialogContent>
            <DialogActions sx={DIALOG_ACTIONS_SX}>
                <Button onClick={onClose} variant="outlined" sx={DIALOG_CANCEL_BUTTON_SX}>
                    Close
                </Button>
            </DialogActions>
        </Dialog>
    );
};

const MonitoredCelestialGridIsland = ({
    rows = [],
    loading = false,
    onRowDoubleClick = null,
    onTargetSelected = null,
}) => {
    const dispatch = useDispatch();
    const { timezone, locale } = useUserTimeSettings();
    const tracks = useSelector((state) => state.celestial?.celestialTracks?.celestial || []);
    const {
        selectedIds,
        tableColumnVisibility,
        tablePageSize,
        tableSortModel,
        openGridSettingsDialog,
    } = useSelector((state) => state.celestialMonitored);
    const [nowMs, setNowMs] = useState(() => Date.now());
    const [page, setPage] = useState(0);
    const rowSelectionModel = useMemo(() => toRowSelectionModel(selectedIds), [selectedIds]);

    useEffect(() => {
        const interval = setInterval(() => setNowMs(Date.now()), 30000);
        return () => clearInterval(interval);
    }, []);

    const trackByTargetKey = useMemo(() => {
        const entries = Array.isArray(tracks) ? tracks : [];
        return entries.reduce((acc, track) => {
            const key = String(track?.target_key || '').trim()
                || (() => {
                    const type = String(track?.target_type || 'mission').toLowerCase();
                    if (type === 'body') {
                        const bodyId = String(track?.body_id || track?.command || '').toLowerCase();
                        return bodyId ? `body:${bodyId}` : '';
                    }
                    const command = String(track?.command || '').trim();
                    return command ? `mission:${command}` : '';
                })();
            if (key) acc[key] = track;
            return acc;
        }, {});
    }, [tracks]);

    const enrichedRows = useMemo(
        () =>
            (rows || []).map((row) => {
                const targetKey = buildTargetKey(row);
                const track = trackByTargetKey[targetKey] || {};
                const targetType = String(row.targetType || row.target_type || 'mission').toLowerCase();
                const distanceAu = magnitude3(track.position_xyz_au);
                const speedAuPerDay = magnitude3(track.velocity_xyz_au_per_day);
                const speedKmS = Number.isFinite(speedAuPerDay) ? speedAuPerDay * AU_PER_DAY_TO_KM_PER_S : NaN;
                const lightTimeMin = Number.isFinite(distanceAu) ? distanceAu * LIGHT_TIME_MIN_PER_AU : NaN;
                const sampleCount = Array.isArray(track.orbit_samples_xyz_au) ? track.orbit_samples_xyz_au.length : 0;
                const rawElevationDeg = Number(track?.sky_position?.el_deg);
                const rawAzimuthDeg = Number(track?.sky_position?.az_deg);
                const elevationDeg = Number.isFinite(rawElevationDeg) ? rawElevationDeg : null;
                const azimuthDeg = Number.isFinite(rawAzimuthDeg) ? rawAzimuthDeg : null;
                const visibility = getVisibilityState(track?.visibility?.visible, rawElevationDeg);
                return {
                    ...row,
                    targetType,
                    targetKey,
                    color: row.color || track.color || null,
                    source: track.source || '-',
                    sourceMode: row.sourceMode || row.source_mode || (targetType === 'body' ? 'static-body' : '-'),
                    visibility,
                    elevationDeg,
                    azimuthDeg,
                    distanceFromSunAu: distanceAu,
                    speedKmS,
                    lightTimeMinutes: lightTimeMin,
                    lastRefreshAge: formatAge(row.lastRefreshAt, nowMs),
                    projectionSpan: computeProjectionSpan(track.orbit_sampling),
                    cacheStatus: track.cache || '-',
                    stale: track.stale ? 'Yes' : 'No',
                    sampleCount,
                };
            }),
        [rows, trackByTargetKey, nowMs],
    );

    const columns = useMemo(
        () => [
            {
                field: 'displayName',
                headerName: 'Name',
                minWidth: 170,
                flex: 1,
                renderCell: (params) => (
                    <Box
                        sx={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'flex-start',
                            width: '100%',
                            height: '100%',
                            minWidth: 0,
                            gap: 0.75,
                        }}
                    >
                        {(() => {
                            const value = String(params.row?.color || '').trim();
                            const valid = /^#[0-9A-Fa-f]{6}$/.test(value);
                            const swatchColor = valid ? value : 'transparent';
                            return (
                                <Box
                                    sx={{
                                        width: 12,
                                        height: 12,
                                        borderRadius: '3px',
                                        border: '1px solid',
                                        borderColor: 'divider',
                                        bgcolor: swatchColor,
                                        flexShrink: 0,
                                    }}
                                    title={valid ? value.toUpperCase() : 'No color'}
                                />
                            );
                        })()}
                        <Typography
                            component="span"
                            variant="body2"
                            sx={{
                                fontWeight: 700,
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                lineHeight: 1.2,
                                minWidth: 0,
                            }}
                        >
                            {params?.value || '-'}
                        </Typography>
                    </Box>
                ),
            },
            {
                field: 'targetType',
                headerName: 'Type',
                minWidth: 95,
                valueGetter: (value) => (String(value || '').toLowerCase() === 'body' ? 'Body' : 'Mission'),
            },
            {
                field: 'command',
                headerName: 'Target ID',
                minWidth: 170,
                flex: 1,
                valueGetter: (value, row) =>
                    String(row?.targetType || '').toLowerCase() === 'body' ? (row?.bodyId || value) : value,
            },
            { field: 'source', headerName: 'Source', minWidth: 110, flex: 0.7 },
            { field: 'sourceMode', headerName: 'Source Mode', minWidth: 120, flex: 0.8 },
            {
                field: 'enabled',
                headerName: 'Enabled',
                minWidth: 90,
                align: 'center',
                headerAlign: 'center',
                valueGetter: (value) => (value ? 'Yes' : 'No'),
            },
            {
                field: 'elevationDeg',
                minWidth: 130,
                headerName: 'Elevation (deg)',
                type: 'number',
                align: 'center',
                headerAlign: 'center',
                valueFormatter: (value) => formatAngle(value, 2),
            },
            {
                field: 'azimuthDeg',
                minWidth: 125,
                headerName: 'Azimuth (deg)',
                align: 'center',
                headerAlign: 'center',
                valueGetter: (value) => formatAngle(value, 2),
            },
            {
                field: 'distanceFromSunAu',
                headerName: 'Distance from Sun (AU)',
                minWidth: 165,
                valueGetter: (value) => formatNumeric(value, 4),
            },
            {
                field: 'speedKmS',
                headerName: 'Speed (km/s)',
                minWidth: 120,
                valueGetter: (value) => formatNumeric(value, 3),
            },
            {
                field: 'lightTimeMinutes',
                headerName: 'Light Time (min)',
                minWidth: 130,
                valueGetter: (value) => formatNumeric(value, 2),
            },
            { field: 'lastRefreshAge', headerName: 'Refresh Age', minWidth: 100 },
            { field: 'projectionSpan', headerName: 'Projection Span', minWidth: 150 },
            { field: 'cacheStatus', headerName: 'Cache', minWidth: 90 },
            { field: 'stale', headerName: 'Stale', minWidth: 80 },
            { field: 'sampleCount', headerName: 'Samples', minWidth: 90, type: 'number' },
            {
                field: 'lastError',
                headerName: 'Last Error',
                minWidth: 250,
                flex: 1.2,
                valueGetter: (value) => value || '-',
            },
            {
                field: 'lastRefreshAt',
                headerName: 'Last Refresh',
                minWidth: 185,
                valueGetter: (value) => formatLastRefresh(value, timezone, locale),
            },
        ],
        [timezone, locale],
    );

    return (
        <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <Box sx={{ width: '100%', flex: 1, minHeight: 0 }}>
                <StyledDataGrid
                    rows={enrichedRows}
                    columns={columns}
                    getRowId={(row) => row.id}
                    loading={loading}
                    disableMultipleRowSelection
                    disableRowSelectionOnClick={false}
                    rowSelectionModel={rowSelectionModel}
                    onRowSelectionModelChange={(nextSelection) => {
                        const selected = toSelectedIds(nextSelection);
                        const selectedId = selected.length ? selected[0] : null;
                        dispatch(setSelectedMonitoredIds(selectedId ? [selectedId] : []));
                        if (selectedId && onTargetSelected) {
                            const selectedRow = enrichedRows.find((row) => row.id === selectedId);
                            if (selectedRow) {
                                onTargetSelected(selectedRow);
                            }
                        }
                    }}
                    onRowDoubleClick={(params) => {
                        if (onRowDoubleClick) {
                            onRowDoubleClick(params?.row || null);
                        }
                    }}
                    density="compact"
                    columnVisibilityModel={tableColumnVisibility}
                    onColumnVisibilityModelChange={(model) => dispatch(setMonitoredTableColumnVisibility(model))}
                    paginationModel={{ pageSize: tablePageSize, page }}
                    onPaginationModelChange={(model) => {
                        setPage(model.page);
                        dispatch(setMonitoredTablePageSize(model.pageSize));
                    }}
                    pageSizeOptions={[5, 10, 15, 20, 25]}
                    sortModel={tableSortModel}
                    onSortModelChange={(model) => dispatch(setMonitoredTableSortModel(model))}
                    getRowClassName={(params) => {
                        if ((selectedIds || [])[0] === params.row.id) {
                            return 'celestial-row-selected pointer-cursor';
                        }
                        if (params.row.lastError && params.row.lastError !== '-') {
                            return 'celestial-row-dead pointer-cursor';
                        }
                        if (params.row.visibility === 'visible') {
                            return 'celestial-row-visible pointer-cursor';
                        }
                        if (params.row.visibility === 'below') {
                            return 'celestial-row-below pointer-cursor';
                        }
                        return 'celestial-row-unknown pointer-cursor';
                    }}
                    sx={{
                        border: 0,
                        marginTop: 0,
                        [`& .${gridClasses.cell}:focus, & .${gridClasses.cell}:focus-within`]: {
                            outline: 'none',
                        },
                        [`& .${gridClasses.columnHeader}:focus, & .${gridClasses.columnHeader}:focus-within`]: {
                            outline: 'none',
                        },
                        '& .MuiDataGrid-overlay': {
                            fontSize: '0.875rem',
                            fontStyle: 'italic',
                            color: 'text.secondary',
                        },
                    }}
                />
            </Box>
            <SettingsDialog
                open={openGridSettingsDialog}
                onClose={() => dispatch(setOpenGridSettingsDialog(false))}
            />
        </Box>
    );
};

export default React.memo(MonitoredCelestialGridIsland);
