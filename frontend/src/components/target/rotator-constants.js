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

/**
 * Rotator event key constants
 * These are the clean, semantic keys stored in Redux state
 */
export const ROTATOR_EVENT_KEYS = {
    EL_MIN: 'EL-MIN',
    EL_MAX: 'EL-MAX',
    AZ_MIN: 'AZ-MIN',
    AZ_MAX: 'AZ-MAX',
    OOB: 'OOB',
    SLEW: 'SLEW',
    TRK: 'TRK',
    STOP: 'STOP'
};

/**
 * Rotator event display strings with decorative dashes
 * Used for waterfall timeline visualization
 */
export const ROTATOR_EVENT_DISPLAY = {
    [ROTATOR_EVENT_KEYS.EL_MIN]: '━━ EL-MIN ━━',
    [ROTATOR_EVENT_KEYS.EL_MAX]: '━━ EL-MAX ━━',
    [ROTATOR_EVENT_KEYS.AZ_MIN]: '━━ AZ-MIN ━━',
    [ROTATOR_EVENT_KEYS.AZ_MAX]: '━━ AZ-MAX ━━',
    [ROTATOR_EVENT_KEYS.OOB]: '━━━ OOB ━━━',
    [ROTATOR_EVENT_KEYS.SLEW]: '━━ SLEW ━━',
    [ROTATOR_EVENT_KEYS.TRK]: '━━━ TRK ━━━',
    [ROTATOR_EVENT_KEYS.STOP]: '━━ STOP ━━'
};

/**
 * Get the display string for a rotator event
 * @param {string} eventKey - The event key (e.g., 'TRK', 'SLEW')
 * @returns {string} Formatted display string with decorative dashes
 */
export function getRotatorEventDisplay(eventKey) {
    return ROTATOR_EVENT_DISPLAY[eventKey] || eventKey;
}
