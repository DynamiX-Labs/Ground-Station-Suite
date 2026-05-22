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

import { useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { setNeighboringTransmitters } from '../components/waterfall/waterfall-slice.jsx';
import { calculateNeighboringTransmitters, groupNeighboringTransmitters } from '../utils/doppler-calculator.js';
import { isSatelliteVisible } from '../components/common/tracking-logic.jsx';

/**
 * Custom hook to calculate doppler-shifted neighboring transmitters.
 *
 * Updates every 3 seconds (similar to overview map satellite updates).
 * Filters transmitters from groupOfSats that fall within the active SDR bandwidth
 * and are currently visible (above horizon) from the observer's location.
 * Stores the results in the waterfall slice.
 */
export function useDopplerNeighbors() {
    const dispatch = useDispatch();
    const updateIntervalRef = useRef(null);

    // Get data from Redux
    const { groupOfSats, satelliteId } = useSelector(state => state.targetSatTrack);
    const { centerFrequency, sampleRate, showNeighboringTransmitters } = useSelector(state => state.waterfall);
    const { location } = useSelector(state => state.location);

    useEffect(() => {
        // Clear existing interval
        if (updateIntervalRef.current) {
            clearInterval(updateIntervalRef.current);
            updateIntervalRef.current = null;
        }

        // Only run if feature is enabled and we have required data
        if (!showNeighboringTransmitters || !centerFrequency || !sampleRate || !location) {
            dispatch(setNeighboringTransmitters([]));
            return;
        }

        // Function to update neighboring transmitters
        const updateNeighbors = () => {
            try {
                const now = new Date();

                // Filter to only visible satellites (above horizon)
                // This dramatically reduces the number of doppler calculations needed
                // Also exclude the currently targeted satellite
                const visibleSatellites = groupOfSats.filter(sat => {
                    if (!sat.tle1 || !sat.tle2) {
                        return false;
                    }

                    // Exclude the currently targeted satellite
                    if (satelliteId && sat.norad_id === satelliteId) {
                        return false;
                    }

                    return isSatelliteVisible(
                        sat.tle1,
                        sat.tle2,
                        now,
                        { lat: location.lat, lon: location.lon, alt: location.alt },
                        0 // minimum elevation: 0 degrees (above horizon)
                    );
                });

                // Calculate doppler shift only for visible satellites
                const neighbors = calculateNeighboringTransmitters(
                    visibleSatellites,
                    centerFrequency,
                    sampleRate,
                    location.lat,
                    location.lon,
                    location.alt,
                    now
                );

                // Group transmitters that are close together (within 50kHz)
                const groupedNeighbors = groupNeighboringTransmitters(neighbors, 50000);

                dispatch(setNeighboringTransmitters(groupedNeighbors));
            } catch (error) {
                console.error('Error updating neighboring transmitters:', error);
                dispatch(setNeighboringTransmitters([]));
            }
        };

        // Initial update
        updateNeighbors();

        // Set up interval for updates every 3 seconds
        updateIntervalRef.current = setInterval(updateNeighbors, 3000);

        // Cleanup
        return () => {
            if (updateIntervalRef.current) {
                clearInterval(updateIntervalRef.current);
                updateIntervalRef.current = null;
            }
        };
    }, [
        dispatch,
        groupOfSats,
        centerFrequency,
        sampleRate,
        location,
        showNeighboringTransmitters,
        satelliteId
    ]);
}
