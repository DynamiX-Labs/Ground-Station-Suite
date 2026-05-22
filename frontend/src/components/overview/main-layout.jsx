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


import React, {useState, useEffect, useRef, useCallback} from 'react';
import {Responsive, useContainerWidth} from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import 'leaflet/dist/leaflet.css';
import {absoluteStrategy} from 'react-grid-layout/core';
import {duration, styled} from "@mui/material/styles";
import OverviewSatelliteGroupSelector from "./satellite-selector.jsx";
import {
    StyledIslandParent,
    StyledIslandParentScrollbar,
    StyledIslandParentNoScrollbar,
} from "../common/common.jsx";
import {toast} from '../../utils/toast-with-timestamp.jsx';
import {useSocket} from "../common/socket.jsx";
import {DataGrid, gridClasses} from "@mui/x-data-grid";
import {useDispatch, useSelector} from "react-redux";
import {useTranslation} from 'react-i18next';
import {
    setGridEditable,
} from './overview-slice.jsx';
import NextPassesGroupIsland from "./satellite-passes.jsx";
import OverviewSatelliteInfoCard from "./satellite-info.jsx";
import { setRotator, setTrackerId, setTrackingStateInBackend } from "../target/target-slice.jsx";
import SatelliteMapContainer from './overview-map.jsx';
import SatelliteDetailsTable from "./satellites-table.jsx";
import SatelliteGroupSelectorBar from "./satellite-group-selector-bar.jsx";
import OverviewPassTimeline from './overview-pass-timeline.jsx';
import { useTargetRotatorSelectionDialog } from '../target/use-target-rotator-selection-dialog.jsx';

// global callback for dashboard editing here
const setGridEditableOverviewEvent = 'overview-set-grid-editable';
export const handleSetGridEditableOverview = function (value) {
    window.dispatchEvent(new CustomEvent(setGridEditableOverviewEvent, {detail: value}));
};

export const gridLayoutStoreName = 'global-sat-track-layouts';
const LAYOUT_SCHEMA_VERSION = 2;
const SHARED_RESIZE_HANDLES = ['s', 'sw', 'w', 'se', 'nw', 'ne', 'e'];


// load / save layouts from localStorage
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

const ThemedDiv = styled('div')(({theme}) => ({
    backgroundColor: theme.palette.background.paper,
}));

const GlobalSatelliteTrackLayout = React.memo(function GlobalSatelliteTrackLayout() {
    const {socket} = useSocket();
    const dispatch = useDispatch();
    const {t} = useTranslation('overview');
    const gridEditable = useSelector((state) => state.overviewSatTrack.gridEditable);
    const selectedSatGroupId = useSelector((state) => state.overviewSatTrack.selectedSatGroupId);
    const {
        trackingState,
        trackerViews,
    } = useSelector(state => state.targetSatTrack);
    const trackerInstances = useSelector((state) => state.trackerInstances?.instances || []);
    const { requestRotatorForTarget, dialog: rotatorSelectionDialog } = useTargetRotatorSelectionDialog();

    const {width, containerRef, mounted} = useContainerWidth({measureBeforeMount: true});

    // Default layout if none in localStorage
    const defaultLayouts = {
        "lg": [{
            "i": "map",
            "x": 0,
            "y": 0,
            "w": 5,
            "h": 13,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "passes",
            "x": 0,
            "y": 18,
            "w": 12,
            "h": 8,
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "sat-info",
            "x": 10,
            "y": 0,
            "w": 2,
            "h": 13,
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "satellite-group",
            "x": 5,
            "y": 0,
            "w": 5,
            "h": 13,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "timeline",
            "x": 0,
            "y": 13,
            "w": 12,
            "h": 5,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }],
        "xs": [{
            "i": "map",
            "x": 0,
            "y": 0,
            "w": 2,
            "h": 17,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "passes",
            "x": 0,
            "y": 35,
            "w": 2,
            "h": 8,
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "sat-info",
            "x": 0,
            "y": 43,
            "w": 2,
            "h": 14,
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "satellite-group",
            "x": 0,
            "y": 23,
            "w": 2,
            "h": 12,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "timeline",
            "x": 0,
            "y": 17,
            "w": 2,
            "h": 6,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }],
        "sm": [{
            "i": "map",
            "x": 0,
            "y": 0,
            "w": 6,
            "h": 17,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "passes",
            "x": 0,
            "y": 32,
            "w": 6,
            "h": 8,
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "sat-info",
            "x": 0,
            "y": 40,
            "w": 6,
            "h": 12,
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "satellite-group",
            "x": 0,
            "y": 23,
            "w": 6,
            "h": 9,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "timeline",
            "x": 0,
            "y": 17,
            "w": 6,
            "h": 6,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }],
        "xxs": [{
            "w": 2,
            "h": 17,
            "x": 0,
            "y": 0,
            "i": "map",
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "w": 2,
            "h": 9,
            "x": 0,
            "y": 23,
            "i": "passes",
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "w": 2,
            "h": 14,
            "x": 0,
            "y": 45,
            "i": "sat-info",
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "w": 2,
            "h": 13,
            "x": 0,
            "y": 32,
            "i": "satellite-group",
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "w": 2,
            "h": 6,
            "x": 0,
            "y": 17,
            "i": "timeline",
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }],
        "md": [{
            "i": "map",
            "x": 0,
            "y": 0,
            "w": 7,
            "h": 17,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "passes",
            "x": 0,
            "y": 29,
            "w": 10,
            "h": 8,
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "sat-info",
            "x": 7,
            "y": 0,
            "w": 3,
            "h": 17,
            "minH": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "satellite-group",
            "x": 0,
            "y": 22,
            "w": 10,
            "h": 7,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "timeline",
            "x": 0,
            "y": 17,
            "w": 10,
            "h": 5,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }]
    };

    useEffect(() => {
        const onSetGridEditable = (event) => {
            dispatch(setGridEditable(event.detail));
        };

        window.addEventListener(setGridEditableOverviewEvent, onSetGridEditable);
        return () => {
            window.removeEventListener(setGridEditableOverviewEvent, onSetGridEditable);
        };
    }, [dispatch]);

    // we load any stored layouts from localStorage or fallback to default
    const [layouts, setLayouts] = useState(() => {
        const loaded = loadLayoutsFromLocalStorage();
        return normalizeLayoutsResizeHandles(loaded ?? defaultLayouts);
    });

    const handleSetTrackingOnBackend = async ({ noradId, satelliteName }) => {
        const selectedAssignment = await requestRotatorForTarget(satelliteName);
        if (!selectedAssignment) {
            return;
        }
        const assignmentAction = String(selectedAssignment?.action || 'retarget_current_slot');
        const isCreateNewSlot = assignmentAction === 'create_new_slot';
        const trackerId = String(selectedAssignment?.trackerId || '');
        const rotatorId = String(selectedAssignment?.rotatorId || 'none');
        const assignmentRigId = String(selectedAssignment?.rigId || 'none');
        if (!trackerId) {
            return;
        }

        const selectedTrackerInstance = trackerInstances.find(
            (instance) => String(instance?.tracker_id || '') === trackerId
        );
        const selectedTrackerView = trackerViews?.[trackerId] || {};
        const selectedTrackerState = selectedTrackerView?.trackingState || selectedTrackerInstance?.tracking_state || {};
        const nextRigId = isCreateNewSlot
            ? assignmentRigId
            : String(
                selectedTrackerView?.selectedRadioRig
                ?? selectedTrackerState?.rig_id
                ?? assignmentRigId
                ?? 'none'
            );
        const nextRotatorId = isCreateNewSlot ? 'none' : rotatorId;
        const nextTransmitterId = isCreateNewSlot
            ? 'none'
            : String(selectedTrackerState?.transmitter_id || 'none');
        const nextGroupId = selectedSatGroupId || selectedTrackerState?.group_id || trackingState?.group_id || '';

        dispatch(setTrackerId(trackerId));
        dispatch(setRotator({ value: nextRotatorId, trackerId }));

        // Always overwrite target identity fields when retargeting to a satellite slot.
        const normalizedTargetName = String(satelliteName || noradId || '').trim();
        const satelliteTargetPatch = {
            target_type: 'satellite',
            target_name: normalizedTargetName || String(noradId || '').trim(),
            command: null,
            body_id: null,
        };

        const newTrackingState = isCreateNewSlot
            ? {
                tracker_id: trackerId,
                norad_id: noradId,
                group_id: nextGroupId,
                ...satelliteTargetPatch,
                rig_id: nextRigId,
                rotator_id: nextRotatorId,
                transmitter_id: 'none',
                rig_state: 'disconnected',
                rotator_state: 'disconnected',
                rig_vfo: 'none',
                vfo1: 'uplink',
                vfo2: 'downlink',
            }
            : {
                ...selectedTrackerState,
                tracker_id: trackerId,
                norad_id: noradId,
                group_id: nextGroupId,
                ...satelliteTargetPatch,
                rig_id: nextRigId,
                rotator_id: nextRotatorId,
                transmitter_id: nextTransmitterId,
            };

        dispatch(setTrackingStateInBackend({socket, data: newTrackingState}))
            .unwrap()
            .then((response) => {
                // Success handling
            })
            .catch((error) => {
                toast.error(`${t('satellite_info.failed_tracking')}: ${error?.message || error?.error || 'Unknown error'}`);
            });
    };

    function handleLayoutsChange(currentLayout, allLayouts) {
        const normalizedLayouts = normalizeLayoutsResizeHandles(allLayouts);
        setLayouts(normalizedLayouts);
        window.dispatchEvent(new Event('overview-map-layout-change'));
    }

    useEffect(() => {
        saveLayoutsToLocalStorage(layouts);
    }, [layouts]);

    function handleLayoutWidthChange() {
        window.dispatchEvent(new Event('overview-map-layout-change'));
    }

    // pre-made ResponsiveGridLayout
    let gridContents = [
        <StyledIslandParent key="map">
            <SatelliteMapContainer handleSetTrackingOnBackend={handleSetTrackingOnBackend}/>
        </StyledIslandParent>,
        <StyledIslandParentNoScrollbar key="passes">
            <NextPassesGroupIsland/>
        </StyledIslandParentNoScrollbar>,
        <StyledIslandParentNoScrollbar key="sat-info">
            <OverviewSatelliteInfoCard/>
        </StyledIslandParentNoScrollbar>,
        <StyledIslandParentNoScrollbar key="satellite-group">
            <SatelliteDetailsTable/>
        </StyledIslandParentNoScrollbar>,
        <StyledIslandParentNoScrollbar key="timeline">
            <OverviewPassTimeline/>
        </StyledIslandParentNoScrollbar>,
    ];

    const ResponsiveGridLayoutParent = mounted ? (
        <Responsive
            width={width}
            positionStrategy={absoluteStrategy}
            className="layout"
            layouts={layouts}
            onLayoutChange={handleLayoutsChange}
            onWidthChange={handleLayoutWidthChange}
            breakpoints={{lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0}}
            cols={{lg: 12, md: 10, sm: 6, xs: 2, xxs: 2}}
            rowHeight={30}
            dragConfig={{enabled: gridEditable, handle: '.react-grid-draggable'}}
            resizeConfig={{enabled: gridEditable}}
        >
            {gridContents}
        </Responsive>
    ) : null;

    return (
        <>
            {rotatorSelectionDialog}
            <SatelliteGroupSelectorBar/>
            <div ref={containerRef}>
                {ResponsiveGridLayoutParent}
            </div>
        </>
    );
});

export default GlobalSatelliteTrackLayout;
