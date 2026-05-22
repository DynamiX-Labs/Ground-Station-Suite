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



const normalizeTargetType = (trackingState = {}) => {
    const explicitType = String(trackingState?.target_type || '').trim().toLowerCase();
    if (explicitType === 'satellite' || explicitType === 'mission' || explicitType === 'body') {
        return explicitType;
    }
    if (trackingState?.command) {
        return 'mission';
    }
    if (trackingState?.body_id) {
        return 'body';
    }
    return 'satellite';
};

export const trackingStateSelector = (state) => state.targetSatTrack.trackingState || {};
export const targetTypeSelector = (state) => normalizeTargetType(trackingStateSelector(state));
export const targetIdentifierSelector = (state) => {
    const trackingState = trackingStateSelector(state);
    const targetType = normalizeTargetType(trackingState);
    if (targetType === 'mission') {
        return String(trackingState?.command || '').trim();
    }
    if (targetType === 'body') {
        return String(trackingState?.body_id || '').trim().toLowerCase();
    }
    return String(trackingState?.norad_id || '').trim();
};

export const satellitePositionSelector = state => state.targetSatTrack.satelliteData.position;
export const satellitePathsSelector = state => state.targetSatTrack.satelliteData.paths;
export const satelliteCoverageSelector = state => state.targetSatTrack.satelliteData.coverage;
export const satelliteTrackingStateSelector = state => state.targetSatTrack.trackingState;
export const satelliteDetailsSelector = state => state.targetSatTrack.satelliteData.details;
export const satelliteTransmittersSelector = state => state.targetSatTrack.satelliteData.transmitters;
