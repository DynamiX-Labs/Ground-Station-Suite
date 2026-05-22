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


import React, {useState, useEffect, useRef, useCallback, useMemo} from 'react';
import {Responsive, useContainerWidth} from 'react-grid-layout';
import 'leaflet-fullscreen/dist/Leaflet.fullscreen.js';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import 'leaflet/dist/leaflet.css';
import {
    StyledIslandParentScrollbar,
} from "../common/common.jsx";
import {
    setGridEditable
} from './waterfall-slice.jsx';
import {useDispatch, useSelector} from "react-redux";
import MainWaterfallDisplay from "./waterfall-island.jsx";
import DecodedInsightsIsland from "./decoded-insights-island.jsx";
import WaterfallSettings from "./settings-column.jsx";
import TranscriptionSubtitles from "./transcription-subtitles.jsx";


// A global callback for dashboard editing here
const setGridEditableWaterfallEvent = 'waterfall-set-grid-editable';
export const handleSetGridEditableWaterfall = function (value) {
    window.dispatchEvent(new CustomEvent(setGridEditableWaterfallEvent, {detail: value}));
};

export const gridLayoutStoreName = 'waterfall-view-layouts';
const LAYOUT_SCHEMA_VERSION = 6;
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

const MainLayout = React.memo(function MainLayout() {
    const waterfallComponentSettingsRef = useRef(null);

    // Playback timing refs shared between waterfall and settings components
    const playbackElapsedSecondsRef = useRef(null);
    const playbackRemainingSecondsRef = useRef(null);
    const playbackTotalSecondsRef = useRef(null);

    const dispatch = useDispatch();
    const {
        gridEditable,
    } = useSelector(state => state.waterfall);

    const {width, containerRef, mounted} = useContainerWidth({measureBeforeMount: true});

    // Default layout if none in localStorage
    const defaultLayouts = {
        "lg": [{
            "i": "waterfall",
            "x": 0,
            "y": 0,
            "w": 10,
            "h": 19,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "settings",
            "x": 10,
            "y": 0,
            "w": 2,
            "h": 19,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "decoding",
            "x": 0,
            "y": 19,
            "w": 12,
            "h": 8,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }],
        "md": [{
            "i": "waterfall",
            "x": 0,
            "y": 0,
            "w": 7,
            "h": 25,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "settings",
            "x": 7,
            "y": 0,
            "w": 3,
            "h": 25,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "decoding",
            "x": 0,
            "y": 25,
            "w": 10,
            "h": 10,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }],
        "sm": [{
            "i": "waterfall",
            "x": 0,
            "y": 0,
            "w": 6,
            "h": 22,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "settings",
            "x": 0,
            "y": 22,
            "w": 6,
            "h": 14,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "decoding",
            "x": 0,
            "y": 36,
            "w": 6,
            "h": 10,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }],
        "xs": [{
            "i": "waterfall",
            "x": 0,
            "y": 0,
            "w": 2,
            "h": 22,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "settings",
            "x": 0,
            "y": 22,
            "w": 2,
            "h": 13,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "decoding",
            "x": 0,
            "y": 35,
            "w": 2,
            "h": 10,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }],
        "xxs": [{
            "i": "waterfall",
            "x": 0,
            "y": 0,
            "w": 2,
            "h": 20,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "settings",
            "x": 0,
            "y": 20,
            "w": 2,
            "h": 12,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }, {
            "i": "decoding",
            "x": 0,
            "y": 32,
            "w": 2,
            "h": 10,
            "moved": false,
            "static": false,
            "resizeHandles": ["s", "sw", "w", "se", "nw", "ne", "e"]
        }]
    };

    useEffect(() => {
        const onSetGridEditable = (event) => {
            dispatch(setGridEditable(event.detail));
        };

        window.addEventListener(setGridEditableWaterfallEvent, onSetGridEditable);
        return () => {
            window.removeEventListener(setGridEditableWaterfallEvent, onSetGridEditable);
        };
    }, [dispatch]);


    // we load any stored layouts from localStorage or fallback to default
    const [layouts, setLayouts] = useState(() => {
        const loaded = loadLayoutsFromLocalStorage();
        return normalizeLayoutsResizeHandles(loaded ?? defaultLayouts);
    });

    function handleLayoutsChange(currentLayout, allLayouts) {
        const normalizedLayouts = normalizeLayoutsResizeHandles(allLayouts);
        setLayouts(normalizedLayouts);
    }

    useEffect(() => {
        saveLayoutsToLocalStorage(layouts);
    }, [layouts]);

    const gridContents = useMemo(() => [
        <StyledIslandParentScrollbar key="waterfall">
            <MainWaterfallDisplay
                playbackElapsedSecondsRef={playbackElapsedSecondsRef}
                playbackRemainingSecondsRef={playbackRemainingSecondsRef}
                playbackTotalSecondsRef={playbackTotalSecondsRef}
            />
        </StyledIslandParentScrollbar>,
        <StyledIslandParentScrollbar key="settings">
            <WaterfallSettings
                ref={waterfallComponentSettingsRef}
                playbackRemainingSecondsRef={playbackRemainingSecondsRef}
            />
        </StyledIslandParentScrollbar>,
        <StyledIslandParentScrollbar key="decoding">
            <DecodedInsightsIsland />
        </StyledIslandParentScrollbar>,
    ], []);

    const responsiveGridLayoutParent = mounted ? (
        <Responsive
            width={width}
            className="layout"
            layouts={layouts}
            onLayoutChange={handleLayoutsChange}
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
            <div ref={containerRef}>
                {responsiveGridLayoutParent}
            </div>

            {/* Transcription Subtitles Overlay - positioned over entire page */}
            <TranscriptionSubtitles
                maxLines={4}
                maxWordsPerLine={20}
            />
        </>
    );
});

export default MainLayout;
