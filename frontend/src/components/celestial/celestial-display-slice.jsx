import { createSlice } from '@reduxjs/toolkit';

export const DEFAULT_SOLAR_SYSTEM_DISPLAY_OPTIONS = {
    showGrid: true,
    showPlanets: true,
    showPlanetLabels: true,
    showPlanetOrbits: true,
    showTrackedObjects: true,
    showTrackedOrbits: true,
    showTrackedLabels: true,
    showAsteroidZones: true,
    showZoneLabels: true,
    showResonanceMarkers: true,
    showTimestamp: true,
    showScaleIndicator: true,
    showGestureHint: true,
};

const celestialDisplaySlice = createSlice({
    name: 'celestialDisplay',
    initialState: {
        solarSystem: { ...DEFAULT_SOLAR_SYSTEM_DISPLAY_OPTIONS },
    },
    reducers: {
        setSolarSystemDisplayOption: (state, action) => {
            const { key, value } = action.payload || {};
            if (!key || typeof value !== 'boolean') return;
            if (!(key in DEFAULT_SOLAR_SYSTEM_DISPLAY_OPTIONS)) return;
            state.solarSystem[key] = value;
        },
        resetSolarSystemDisplayOptions: (state) => {
            state.solarSystem = { ...DEFAULT_SOLAR_SYSTEM_DISPLAY_OPTIONS };
        },
    },
});

export const {
    setSolarSystemDisplayOption,
    resetSolarSystemDisplayOptions,
} = celestialDisplaySlice.actions;

export default celestialDisplaySlice.reducer;
