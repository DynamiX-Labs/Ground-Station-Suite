import React, { useEffect, useState } from 'react';
import {
    Box,
    IconButton,
    Tooltip,
    Typography,
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useDispatch, useSelector } from 'react-redux';
import { Responsive, useContainerWidth } from 'react-grid-layout';
import { absoluteStrategy } from 'react-grid-layout/core';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { useSocket } from '../common/socket.jsx';
import {
    getClassNamesBasedOnGridEditing,
    islandTitleBarSx,
    StyledIslandParentNoScrollbar,
    TitleBar,
} from '../common/common.jsx';
import {
    fetchCelestialTracks,
    fetchSolarSystemScene,
    getCelestialMapSettings,
    refreshMonitoredCelestialNow,
    setCelestialMapSettings,
} from './celestial-slice.jsx';
import { fetchMonitoredCelestial } from './monitored-slice.jsx';
import { setOpenGridSettingsDialog } from './monitored-slice.jsx';
import CelestialToolbar from './celestial-toolbar.jsx';
import CelestialStatusBar from './celestial-statusbar.jsx';
import SolarSystemCanvas from './solarsystem-canvas.jsx';
import CelestialTopBar from './celestial-topbar.jsx';
import MonitoredCelestialGridIsland from './monitored-grid-island.jsx';
import CelestialPasses from './celestial-passes.jsx';
import CelestialPassTimeline from './celestial-pass-timeline.jsx';
import CelestialInfoIsland from './celestial-info-island.jsx';
import SolarSystemLayoutOptionsDialog from './solar-system-layout-options-dialog.jsx';
import SettingsIcon from '@mui/icons-material/Settings';

export const gridLayoutStoreName = 'celestial-layouts';
const LAYOUT_SCHEMA_VERSION = 4;
const SHARED_RESIZE_HANDLES = ['s', 'sw', 'w', 'se', 'nw', 'ne', 'e'];
const DEFAULT_PAST_HOURS = 0;
const DEFAULT_FUTURE_HOURS = 24;
const DEFAULT_STEP_MINUTES = 60;
const parseNonNegativeNumber = (value, fallback) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
};
const parsePositiveNumber = (value, fallback) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};
const buildTargetKey = (row) => {
    const explicitKey = String(row?.targetKey || row?.target_key || '').trim();
    if (explicitKey) return explicitKey;

    const type = String(row?.targetType || row?.target_type || 'mission').toLowerCase();
    if (type === 'body') {
        const bodyId = String(row?.bodyId || row?.body_id || row?.command || '').trim().toLowerCase();
        return bodyId ? `body:${bodyId}` : '';
    }
    const command = String(row?.command || '').trim();
    return command ? `mission:${command}` : '';
};
function loadLayoutsFromLocalStorage() {
    try {
        const raw = localStorage.getItem(gridLayoutStoreName);
        if (!raw) return null;

        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== 'object') {
            return null;
        }

        // Enforce new default layout by rejecting legacy/unversioned payloads.
        if (!('version' in parsed) || !('layouts' in parsed)) {
            return null;
        }

        return parsed.version === LAYOUT_SCHEMA_VERSION ? parsed.layouts : null;
    } catch {
        return null;
    }
}

function saveLayoutsToLocalStorage(layouts) {
    localStorage.setItem(
        gridLayoutStoreName,
        JSON.stringify({
            version: LAYOUT_SCHEMA_VERSION,
            layouts,
        }),
    );
}

function normalizeLayoutsResizeHandles(layouts) {
    if (!layouts || typeof layouts !== 'object') {
        return layouts;
    }

    return Object.fromEntries(
        Object.entries(layouts).map(([breakpoint, items]) => [
            breakpoint,
            Array.isArray(items)
                ? items.map((item) => ({
                    ...item,
                    resizeHandles: [...SHARED_RESIZE_HANDLES],
                }))
                : items,
        ]),
    );
}

function ensureRequiredLayoutItems(layouts) {
    if (!layouts || typeof layouts !== 'object') {
        return layouts;
    }

    const fallbackItems = {
        lg: [
            { i: 'monitored-celestial', x: 5, y: 0, w: 5, h: 13 },
            { i: 'celestial-info', x: 10, y: 0, w: 2, h: 13 },
            { i: 'celestial-timeline', x: 0, y: 13, w: 12, h: 6 },
            { i: 'celestial-passes', x: 0, y: 19, w: 12, h: 7 },
        ],
        md: [
            { i: 'monitored-celestial', x: 0, y: 15, w: 10, h: 8 },
            { i: 'celestial-info', x: 7, y: 0, w: 3, h: 15 },
            { i: 'celestial-timeline', x: 0, y: 30, w: 10, h: 6 },
            { i: 'celestial-passes', x: 0, y: 23, w: 10, h: 7 },
        ],
        sm: [
            { i: 'monitored-celestial', x: 1, y: 13, w: 5, h: 13 },
            { i: 'celestial-info', x: 4, y: 26, w: 2, h: 13 },
            { i: 'celestial-timeline', x: 0, y: 39, w: 6, h: 6 },
            { i: 'celestial-passes', x: 0, y: 45, w: 6, h: 7 },
        ],
        xs: [
            { i: 'monitored-celestial', x: 0, y: 18, w: 2, h: 9 },
            { i: 'celestial-info', x: 0, y: 41, w: 2, h: 8 },
            { i: 'celestial-timeline', x: 0, y: 35, w: 2, h: 6 },
            { i: 'celestial-passes', x: 0, y: 27, w: 2, h: 8 },
        ],
        xxs: [
            { i: 'monitored-celestial', x: 0, y: 18, w: 2, h: 9 },
            { i: 'celestial-info', x: 0, y: 41, w: 2, h: 8 },
            { i: 'celestial-timeline', x: 0, y: 35, w: 2, h: 6 },
            { i: 'celestial-passes', x: 0, y: 27, w: 2, h: 8 },
        ],
    };

    return Object.fromEntries(
        Object.entries(layouts).map(([breakpoint, items]) => {
            const typedItems = Array.isArray(items) ? items : [];
            const existingItemIds = new Set(
                typedItems.map((item) => String(item?.i || '').trim()).filter(Boolean),
            );
            const requiredItems = fallbackItems[breakpoint] || [];
            let nextBottomY = typedItems.reduce(
                (maxY, item) => Math.max(maxY, Number(item?.y || 0) + Number(item?.h || 0)),
                0,
            );
            const nextItems = [...typedItems];

            requiredItems.forEach((fallback) => {
                if (existingItemIds.has(fallback.i)) {
                    return;
                }
                const itemY = Math.max(Number(fallback.y || 0), nextBottomY);
                const nextItem = {
                    ...fallback,
                    y: itemY,
                    resizeHandles: [...SHARED_RESIZE_HANDLES],
                };
                nextItems.push(nextItem);
                existingItemIds.add(fallback.i);
                nextBottomY = itemY + Number(fallback.h || 0);
            });

            return [breakpoint, nextItems];
        }),
    );
}

const defaultLayouts = {
    lg: [
        { i: 'solar-system', x: 0, y: 0, w: 5, h: 13, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'monitored-celestial', x: 5, y: 0, w: 5, h: 13, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-info', x: 10, y: 0, w: 2, h: 13, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-timeline', x: 0, y: 13, w: 12, h: 6, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-passes', x: 0, y: 19, w: 12, h: 7, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
    ],
    md: [
        { i: 'solar-system', x: 0, y: 0, w: 7, h: 15, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'monitored-celestial', x: 0, y: 15, w: 10, h: 8, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-info', x: 7, y: 0, w: 3, h: 15, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-timeline', x: 0, y: 30, w: 10, h: 6, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-passes', x: 0, y: 23, w: 10, h: 7, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
    ],
    sm: [
        { i: 'solar-system', x: 0, y: 0, w: 5, h: 13, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'monitored-celestial', x: 1, y: 13, w: 5, h: 13, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-info', x: 4, y: 26, w: 2, h: 13, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-timeline', x: 0, y: 39, w: 6, h: 6, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-passes', x: 0, y: 45, w: 6, h: 7, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
    ],
    xs: [
        { i: 'solar-system', x: 0, y: 0, w: 2, h: 18, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'monitored-celestial', x: 0, y: 18, w: 2, h: 9, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-info', x: 0, y: 41, w: 2, h: 8, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-timeline', x: 0, y: 35, w: 2, h: 6, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-passes', x: 0, y: 27, w: 2, h: 8, moved: false, static: false, resizeHandles: [...SHARED_RESIZE_HANDLES] },
    ],
    xxs: [
        { i: 'solar-system', x: 0, y: 0, w: 2, h: 18, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'monitored-celestial', x: 0, y: 18, w: 2, h: 9, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-passes', x: 0, y: 27, w: 2, h: 8, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-timeline', x: 0, y: 35, w: 2, h: 6, resizeHandles: [...SHARED_RESIZE_HANDLES] },
        { i: 'celestial-info', x: 0, y: 41, w: 2, h: 8, resizeHandles: [...SHARED_RESIZE_HANDLES] },
    ],
};

const CelestialMainLayout = () => {
    const { t } = useTranslation('overview');
    const dispatch = useDispatch();
    const { socket } = useSocket();
    const isEditing = useSelector((state) => state.dashboard?.isEditing);
    const celestialState = useSelector((state) => state.celestial);
    const solarSystemDisplayOptions = useSelector((state) => state.celestialDisplay?.solarSystem);
    const monitoredState = useSelector((state) => state.celestialMonitored);
    const { width, containerRef, mounted } = useContainerWidth({ measureBeforeMount: true });

    const [layouts, setLayouts] = useState(() => {
        const loaded = loadLayoutsFromLocalStorage();
        return ensureRequiredLayoutItems(normalizeLayoutsResizeHandles(loaded ?? defaultLayouts));
    });
    const [fitAllSignal, setFitAllSignal] = useState(0);
    const [focusTargetSignal, setFocusTargetSignal] = useState(0);
    const [focusTargetKey, setFocusTargetKey] = useState('');
    const [zoomInSignal, setZoomInSignal] = useState(0);
    const [zoomOutSignal, setZoomOutSignal] = useState(0);
    const [resetZoomSignal, setResetZoomSignal] = useState(0);
    const [openSolarSystemLayoutOptionsDialog, setOpenSolarSystemLayoutOptionsDialog] = useState(false);

    const projectionSettings = React.useMemo(() => {
        const mapSettings = celestialState.mapSettings || {};
        return {
            past_hours: parseNonNegativeNumber(mapSettings.pastHours, DEFAULT_PAST_HOURS),
            future_hours: parsePositiveNumber(mapSettings.futureHours, DEFAULT_FUTURE_HOURS),
            step_minutes: parsePositiveNumber(mapSettings.stepMinutes, DEFAULT_STEP_MINUTES),
        };
    }, [celestialState.mapSettings]);

    const sceneRequestPayload = React.useMemo(
        () => ({
            past_hours: projectionSettings.past_hours,
            future_hours: projectionSettings.future_hours,
            step_minutes: projectionSettings.step_minutes,
        }),
        [projectionSettings.future_hours, projectionSettings.past_hours, projectionSettings.step_minutes],
    );

    const handleLayoutsChange = (currentLayout, allLayouts) => {
        const normalizedLayouts = normalizeLayoutsResizeHandles(allLayouts);
        const mergedLayouts = ensureRequiredLayoutItems(normalizedLayouts);
        setLayouts(mergedLayouts);
    };

    useEffect(() => {
        saveLayoutsToLocalStorage(layouts);
    }, [layouts]);

    useEffect(() => {
        if (!socket) return;
        dispatch(getCelestialMapSettings({ socket }));
        dispatch(fetchMonitoredCelestial({ socket }));
    }, [socket, dispatch]);

    useEffect(() => {
        if (!socket) return;
        dispatch(fetchSolarSystemScene({ socket, payload: sceneRequestPayload }));
        dispatch(fetchCelestialTracks({ socket, payload: sceneRequestPayload }));
    }, [socket, dispatch, sceneRequestPayload]);

    const handleRefreshCelestial = React.useCallback(async () => {
        if (!socket) return;
        await dispatch(refreshMonitoredCelestialNow({ socket, payload: sceneRequestPayload }));
        await dispatch(fetchMonitoredCelestial({ socket }));
    }, [socket, dispatch, sceneRequestPayload]);

    const handleViewportCommit = React.useCallback((nextViewport) => {
        if (!socket) return;

        const existing = celestialState.mapSettings || {};
        const prev = existing.solarSystemViewport || {};
        const unchanged =
            Number(prev.zoom) === Number(nextViewport.zoom)
            && Number(prev.panX) === Number(nextViewport.panX)
            && Number(prev.panY) === Number(nextViewport.panY);

        if (unchanged) return;

        dispatch(
            setCelestialMapSettings({
                socket,
                value: {
                    ...existing,
                    solarSystemViewport: nextViewport,
                },
            }),
        );
    }, [socket, celestialState.mapSettings, dispatch]);

    const combinedScene = React.useMemo(() => {
        const solar = celestialState.solarScene || {};
        const tracks = celestialState.celestialTracks || {};
        return {
            ...solar,
            ...tracks,
            planets: solar.planets || [],
            celestial: tracks.celestial || [],
            celestial_passes: tracks.celestial_passes || [],
            meta: {
                ...(solar.meta || {}),
                ...(tracks.meta || {}),
            },
        };
    }, [celestialState.solarScene, celestialState.celestialTracks]);

    const solarBodies = Array.isArray(combinedScene?.planets) ? combinedScene.planets : [];
    const bodyTypeCounts = combinedScene?.meta?.solar_system?.body_type_counts || {};
    const inferredCounts = solarBodies.reduce(
        (acc, body) => {
            if (body?.body_type === 'moon' || (body?.body_type == null && body?.parent_id)) {
                acc.moons += 1;
            } else {
                acc.planets += 1;
            }
            return acc;
        },
        { planets: 0, moons: 0 },
    );
    const planetsCount = Number.isFinite(Number(bodyTypeCounts?.planet))
        ? Number(bodyTypeCounts.planet)
        : inferredCounts.planets;
    const moonsCount = Number.isFinite(Number(bodyTypeCounts?.moon))
        ? Number(bodyTypeCounts.moon)
        : inferredCounts.moons;
    const trackedCount = combinedScene?.celestial?.length || 0;
    const hasSolarScene = (planetsCount + moonsCount) > 0;
    const selectedInfoTargetKey = React.useMemo(() => {
        const focusedKey = String(focusTargetKey || '').trim();
        if (focusedKey) {
            return focusedKey;
        }

        const rows = monitoredState?.monitored || [];
        const selectedId = (monitoredState?.selectedIds || [])[0];
        const selectedRow = rows.find((row) => row.id === selectedId);
        if (!selectedRow) return '';

        return buildTargetKey(selectedRow);
    }, [focusTargetKey, monitoredState?.monitored, monitoredState?.selectedIds]);
    const selectedTargetKeys = React.useMemo(
        () => (selectedInfoTargetKey ? [selectedInfoTargetKey] : []),
        [selectedInfoTargetKey],
    );
    const tracksProgress = celestialState?.tracksProgress || null;
    const tracksProgressText = React.useMemo(() => {
        if (!celestialState?.tracksLoading) return '';
        const current = Number(tracksProgress?.current);
        const total = Number(tracksProgress?.total);
        if (Number.isFinite(current) && Number.isFinite(total) && total > 0) {
            return `${Math.max(0, Math.min(current, total))}/${total}`;
        }
        return 'Loading...';
    }, [celestialState?.tracksLoading, tracksProgress?.current, tracksProgress?.total]);

    const updateProjectionSetting = React.useCallback((updates) => {
        if (!socket) return;
        const existing = celestialState.mapSettings || {};
        const nextSettings = { ...existing, ...updates };
        const unchanged = Object.keys(updates).every((key) => existing[key] === nextSettings[key]);
        if (unchanged) return;

        dispatch(
            setCelestialMapSettings({
                socket,
                value: nextSettings,
            }),
        );
    }, [socket, celestialState.mapSettings, dispatch]);

    const gridContents = [
        <StyledIslandParentNoScrollbar key="solar-system">
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <TitleBar
                    className={getClassNamesBasedOnGridEditing(isEditing, [])}
                    sx={{ ...islandTitleBarSx, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                >
                    <Box component="span">
                        {t('celestial.solar_system_layout_title', { defaultValue: 'Solar System Layout' })}
                    </Box>
                    <Tooltip title="Layout options">
                        <span>
                            <IconButton
                                size="small"
                                onClick={() => setOpenSolarSystemLayoutOptionsDialog(true)}
                                sx={{ p: 0.25 }}
                            >
                                <SettingsIcon fontSize="small" />
                            </IconButton>
                        </span>
                    </Tooltip>
                </TitleBar>
                <CelestialToolbar
                    onFitAll={() => setFitAllSignal((value) => value + 1)}
                    onZoomIn={() => setZoomInSignal((value) => value + 1)}
                    onZoomOut={() => setZoomOutSignal((value) => value + 1)}
                    onZoomReset={() => setResetZoomSignal((value) => value + 1)}
                    onRefresh={handleRefreshCelestial}
                    loading={celestialState.tracksLoading}
                    loadingText={tracksProgressText}
                    disabled={!socket}
                />
                <Box sx={{ p: 0, flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative' }}>
                    {celestialState.error && !hasSolarScene ? (
                        <Typography variant="body2" color="error" sx={{ p: 1 }}>
                            {celestialState.error}
                        </Typography>
                    ) : (
                        <Box sx={{ height: '100%', minHeight: 220 }}>
                            <SolarSystemCanvas
                                scene={combinedScene}
                                selectedTargetKeys={selectedTargetKeys}
                                fitAllSignal={fitAllSignal}
                                focusTargetSignal={focusTargetSignal}
                                focusTargetKey={focusTargetKey}
                                zoomInSignal={zoomInSignal}
                                zoomOutSignal={zoomOutSignal}
                                resetZoomSignal={resetZoomSignal}
                                initialViewport={celestialState.mapSettings?.solarSystemViewport}
                                onViewportCommit={handleViewportCommit}
                                displayOptions={solarSystemDisplayOptions}
                            />
                        </Box>
                    )}
                </Box>
                <CelestialStatusBar
                    planetsCount={planetsCount}
                    moonsCount={moonsCount}
                    trackedCount={trackedCount}
                />
            </Box>
        </StyledIslandParentNoScrollbar>,
        <StyledIslandParentNoScrollbar key="monitored-celestial">
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <TitleBar
                    className={getClassNamesBasedOnGridEditing(isEditing, [])}
                    sx={{ ...islandTitleBarSx, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
                >
                    <Box component="span">
                        {t('celestial.monitored_title', { defaultValue: 'Monitored Celestial' })}
                    </Box>
                    <Tooltip title="Table settings">
                        <span>
                            <IconButton
                                size="small"
                                onClick={() => dispatch(setOpenGridSettingsDialog(true))}
                                sx={{ p: 0.25 }}
                            >
                                <SettingsIcon fontSize="small" />
                            </IconButton>
                        </span>
                    </Tooltip>
                </TitleBar>
                <Box sx={{ p: 0, flex: 1, minHeight: 0 }}>
                    <MonitoredCelestialGridIsland
                        rows={monitoredState.monitored || []}
                        loading={Boolean(monitoredState.loading)}
                        onTargetSelected={(row) => {
                            const key = buildTargetKey(row);
                            if (!key) return;
                            setFocusTargetKey(key);
                            setFocusTargetSignal((value) => value + 1);
                        }}
                    />
                </Box>
            </Box>
        </StyledIslandParentNoScrollbar>,
        <StyledIslandParentNoScrollbar key="celestial-info">
            <CelestialInfoIsland
                selectedTargetKey={selectedInfoTargetKey}
                tracks={combinedScene?.celestial || []}
                passes={combinedScene?.celestial_passes || []}
                monitoredRows={monitoredState?.monitored || []}
                gridEditable={isEditing}
                loading={Boolean(celestialState.tracksLoading)}
            />
        </StyledIslandParentNoScrollbar>,
        <StyledIslandParentNoScrollbar key="celestial-timeline">
            <CelestialPassTimeline
                passes={combinedScene?.celestial_passes || []}
                loading={Boolean(celestialState.tracksLoading)}
                gridEditable={isEditing}
                projectionFutureHours={projectionSettings.future_hours}
                selectedTargetKey={selectedInfoTargetKey}
                onRefresh={handleRefreshCelestial}
            />
        </StyledIslandParentNoScrollbar>,
        <StyledIslandParentNoScrollbar key="celestial-passes">
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                <CelestialPasses
                    passes={combinedScene?.celestial_passes || []}
                    tracks={combinedScene?.celestial || []}
                    loading={Boolean(celestialState.tracksLoading)}
                    gridEditable={isEditing}
                    onTargetSelected={(targetKey) => {
                        if (!targetKey) return;
                        setFocusTargetKey(targetKey);
                        setFocusTargetSignal((value) => value + 1);
                    }}
                    onRefresh={handleRefreshCelestial}
                    refreshDisabled={!socket || Boolean(celestialState.tracksLoading)}
                />
            </Box>
        </StyledIslandParentNoScrollbar>,
    ];

    return (
        <Box sx={{ width: '100%', height: '100%' }}>
            <SolarSystemLayoutOptionsDialog
                open={openSolarSystemLayoutOptionsDialog}
                initialOptions={solarSystemDisplayOptions}
                onClose={() => setOpenSolarSystemLayoutOptionsDialog(false)}
            />
            <CelestialTopBar
                projectionPastHours={projectionSettings.past_hours}
                projectionFutureHours={projectionSettings.future_hours}
                onProjectionPastHoursChange={(value) => updateProjectionSetting({ pastHours: value })}
                onProjectionFutureHoursChange={(value) => updateProjectionSetting({ futureHours: value })}
            />
            <div ref={containerRef}>
                {mounted ? (
                    <Responsive
                        width={width}
                        positionStrategy={absoluteStrategy}
                        className="layout"
                        layouts={layouts}
                        onLayoutChange={handleLayoutsChange}
                        breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                        cols={{ lg: 12, md: 10, sm: 6, xs: 2, xxs: 2 }}
                        rowHeight={30}
                        dragConfig={{ enabled: isEditing, handle: '.react-grid-draggable' }}
                        resizeConfig={{ enabled: isEditing }}
                    >
                        {gridContents}
                    </Responsive>
                ) : null}
            </div>
        </Box>
    );
};

export default CelestialMainLayout;
