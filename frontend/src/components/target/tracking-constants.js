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

export const ROTATOR_STATES = Object.freeze({
    CONNECTED: 'connected',
    DISCONNECTED: 'disconnected',
    TRACKING: 'tracking',
    STOPPED: 'stopped',
    PARKED: 'parked',
});

export const RIG_STATES = Object.freeze({
    CONNECTED: 'connected',
    DISCONNECTED: 'disconnected',
    TRACKING: 'tracking',
    STOPPED: 'stopped',
});

export const TRACKER_COMMAND_STATUS = Object.freeze({
    SUBMITTED: 'submitted',
    STARTED: 'started',
    SUCCEEDED: 'succeeded',
    FAILED: 'failed',
});

export const TRACKER_COMMAND_SCOPES = Object.freeze({
    ROTATOR: 'rotator',
    RIG: 'rig',
    TARGET: 'target',
    TRACKING: 'tracking',
});

export const DEFAULT_TRACKER_ID = '';

export const resolveTrackerId = (candidate, fallback = DEFAULT_TRACKER_ID) => {
    if (typeof candidate === 'string') {
        const normalized = candidate.trim();
        if (normalized && normalized !== 'none') {
            return normalized;
        }
    }
    return fallback;
};
