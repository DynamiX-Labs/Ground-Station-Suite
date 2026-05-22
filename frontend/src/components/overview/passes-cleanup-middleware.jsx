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


import { setPasses } from './overview-slice.jsx';

/**
 * Middleware that periodically removes expired satellite passes from the Redux store.
 * Runs independently of component mount state, ensuring cleanup happens even when
 * the satellite passes table is not visible.
 *
 * Passes are considered expired if they ended more than 1 minute ago (60000ms),
 * except for geostationary/geosynchronous satellites which are never removed.
 */
const passesCleanupMiddleware = (store) => {
    // Set up periodic cleanup every 10 seconds
    const cleanupInterval = setInterval(() => {
        const state = store.getState();
        const passes = state.overviewSatTrack?.passes;

        if (!passes || passes.length === 0) {
            return;
        }

        const now = new Date();
        const filteredPasses = passes.filter(pass => {
            // Keep geostationary/geosynchronous satellites
            if (pass.is_geostationary || pass.is_geosynchronous) {
                return true;
            }

            const eventEnd = new Date(pass.event_end);
            const timeSinceEnd = now - eventEnd;

            // Keep passes that haven't ended or ended less than 1 minute ago
            return timeSinceEnd <= 60000;
        });

        // Only update if we actually removed some passes
        if (filteredPasses.length !== passes.length) {
            console.log(`Cleaned up ${passes.length - filteredPasses.length} expired satellite pass(es)`);
            store.dispatch(setPasses(filteredPasses));
        }
    }, 10000); // Check every 10 seconds

    // Return the middleware function
    return (next) => (action) => {
        // Just pass through all actions - cleanup happens in the interval
        return next(action);
    };
};

export default passesCleanupMiddleware;
