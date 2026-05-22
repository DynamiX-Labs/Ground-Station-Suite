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

import * as satellite from 'satellite.js';

const normalizeSource = (source) => {
    if (typeof source !== 'string') {
        return 'manual';
    }
    const lowered = source.toLowerCase();
    if (lowered === 'manual' || lowered === 'satdump' || lowered === 'satnogs') {
        return lowered;
    }
    return 'manual';
};

/**
 * Calculate the Doppler shift for a satellite at a given time.
 *
 * This is a JavaScript port of backend/tracking/doppler.py
 *
 * @param {string} tleLine1 - TLE line 1
 * @param {string} tleLine2 - TLE line 2
 * @param {number} observerLat - Observer's latitude in degrees
 * @param {number} observerLon - Observer's longitude in degrees
 * @param {number} observerElevation - Observer's elevation in meters
 * @param {number} transmittedFreqHz - Transmitted frequency in Hz
 * @param {Date} time - Time of observation (defaults to now)
 * @returns {{observedFreqHz: number, dopplerShiftHz: number}} - Doppler-shifted frequency and shift amount
 */
export function calculateDopplerShift(
    tleLine1,
    tleLine2,
    observerLat,
    observerLon,
    observerElevation,
    transmittedFreqHz,
    time = null
) {
    try {
        // Use current time if not specified
        if (!time) {
            time = new Date();
        }

        // Parse TLE
        const satrec = satellite.twoline2satrec(tleLine1, tleLine2);

        // Calculate satellite position at the given time
        const positionAndVelocity = satellite.propagate(satrec, time);

        // Check for propagation errors
        if (!positionAndVelocity || positionAndVelocity.error) {
            console.error('Satellite propagation error:', positionAndVelocity ? positionAndVelocity.error : 'null result');
            return { observedFreqHz: transmittedFreqHz, dopplerShiftHz: 0 };
        }

        const positionEci = positionAndVelocity.position;
        const velocityEci = positionAndVelocity.velocity;

        // Validate ECI position and velocity
        if (!positionEci || !velocityEci) {
            return { observedFreqHz: transmittedFreqHz, dopplerShiftHz: 0 };
        }

        // Convert observer location to radians
        const observerGd = {
            latitude: satellite.degreesToRadians(observerLat),
            longitude: satellite.degreesToRadians(observerLon),
            height: observerElevation / 1000 // Convert meters to km
        };

        // Calculate GMST for the given time
        const gmst = satellite.gstime(time);

        // Convert observer position to ECI coordinates
        const observerEcf = satellite.geodeticToEcf(observerGd);
        const observerEci = satellite.ecfToEci(observerEcf, gmst);

        // Calculate relative position (satellite - observer) in ECI
        const relativePosition = {
            x: positionEci.x - observerEci.x,
            y: positionEci.y - observerEci.y,
            z: positionEci.z - observerEci.z
        };

        // Calculate range (distance)
        const range = Math.sqrt(
            relativePosition.x * relativePosition.x +
            relativePosition.y * relativePosition.y +
            relativePosition.z * relativePosition.z
        );

        // Calculate unit vector along line of sight
        const positionUnit = {
            x: relativePosition.x / range,
            y: relativePosition.y / range,
            z: relativePosition.z / range
        };

        // Calculate radial velocity (dot product of unit position vector and velocity vector)
        const rangeRate =
            positionUnit.x * velocityEci.x +
            positionUnit.y * velocityEci.y +
            positionUnit.z * velocityEci.z;

        // Speed of light in km/s
        const c = 299792.458;

        // Calculate Doppler factor
        const dopplerFactor = 1.0 - (rangeRate / c);

        // Calculate observed frequency
        const observedFreqHz = transmittedFreqHz * dopplerFactor;

        // Calculate the shift in Hz
        const dopplerShiftHz = observedFreqHz - transmittedFreqHz;

        return {
            observedFreqHz: Math.round(observedFreqHz),
            dopplerShiftHz: Math.round(dopplerShiftHz)
        };
    } catch (error) {
        console.error('Error calculating doppler shift:', error);
        return { observedFreqHz: transmittedFreqHz, dopplerShiftHz: 0 };
    }
}

/**
 * Calculate doppler-shifted frequencies for transmitters within a given bandwidth.
 *
 * @param {Array} groupOfSats - Array of satellite objects with TLEs and transmitters
 * @param {number} centerFrequency - SDR center frequency in Hz
 * @param {number} sampleRate - SDR sample rate (bandwidth) in Hz
 * @param {number} observerLat - Observer's latitude in degrees
 * @param {number} observerLon - Observer's longitude in degrees
 * @param {number} observerElevation - Observer's elevation in meters
 * @param {Date} time - Time of observation (defaults to now)
 * @returns {Array} - Array of transmitters with doppler-corrected frequencies within bandwidth
 */
export function calculateNeighboringTransmitters(
    groupOfSats,
    centerFrequency,
    sampleRate,
    observerLat,
    observerLon,
    observerElevation,
    time = null
) {
    if (!groupOfSats || !Array.isArray(groupOfSats) || groupOfSats.length === 0) {
        return [];
    }

    if (!centerFrequency || !sampleRate) {
        return [];
    }

    const bandwidth = sampleRate;
    const minFreq = centerFrequency - bandwidth / 2;
    const maxFreq = centerFrequency + bandwidth / 2;

    const neighboringTransmitters = [];

    groupOfSats.forEach(sat => {
        if (!sat.tle1 || !sat.tle2 || !sat.transmitters || !Array.isArray(sat.transmitters)) {
            return;
        }

        sat.transmitters.forEach(tx => {
            // Only process alive transmitters with downlink frequencies
            if (!tx.alive || !tx.downlink_low) {
                return;
            }

            try {
                // Calculate doppler shift
                const { observedFreqHz, dopplerShiftHz } = calculateDopplerShift(
                    sat.tle1,
                    sat.tle2,
                    observerLat,
                    observerLon,
                    observerElevation,
                    tx.downlink_low,
                    time
                );

                // Check if doppler-shifted frequency is within bandwidth
                if (observedFreqHz >= minFreq && observedFreqHz <= maxFreq) {
                    neighboringTransmitters.push({
                        ...tx,
                        source: normalizeSource(tx.source),
                        satellite_name: sat.name,
                        satellite_norad_id: sat.norad_id,
                        original_frequency: tx.downlink_low,
                        doppler_frequency: observedFreqHz,
                        doppler_shift: dopplerShiftHz
                    });
                }
            } catch (error) {
                console.error(`Error processing transmitter ${tx.id} for satellite ${sat.name}:`, error);
            }
        });
    });

    return neighboringTransmitters;
}

/**
 * Group neighboring transmitters by satellite when they are within a frequency threshold.
 * This prevents visual clutter when multiple transmitters from the same satellite are close together.
 *
 * @param {Array} neighboringTransmitters - Array of neighboring transmitters
 * @param {number} frequencyThresholdHz - Frequency threshold in Hz to group transmitters (default 50kHz)
 * @returns {Array} - Array of grouped transmitters
 */
export function groupNeighboringTransmitters(neighboringTransmitters, frequencyThresholdHz = 50000) {
    if (!neighboringTransmitters || neighboringTransmitters.length === 0) {
        return [];
    }

    // Group transmitters by satellite
    const satelliteGroups = {};

    neighboringTransmitters.forEach(tx => {
        const satKey = tx.satellite_norad_id;
        if (!satelliteGroups[satKey]) {
            satelliteGroups[satKey] = {
                satellite_name: tx.satellite_name,
                satellite_norad_id: tx.satellite_norad_id,
                transmitters: []
            };
        }
        satelliteGroups[satKey].transmitters.push(tx);
    });

    // For each satellite, group transmitters that are within threshold
    const groupedResults = [];

    Object.values(satelliteGroups).forEach(satGroup => {
        // Sort transmitters by frequency
        const sortedTxs = [...satGroup.transmitters].sort((a, b) =>
            a.doppler_frequency - b.doppler_frequency
        );

        let currentGroup = [sortedTxs[0]];

        for (let i = 1; i < sortedTxs.length; i++) {
            const prevTx = sortedTxs[i - 1];
            const currTx = sortedTxs[i];
            const freqDiff = Math.abs(currTx.doppler_frequency - prevTx.doppler_frequency);

            if (freqDiff <= frequencyThresholdHz) {
                // Add to current group
                currentGroup.push(currTx);
            } else {
                // Finalize current group and start new one
                groupedResults.push(createGroupedTransmitter(currentGroup, satGroup));
                currentGroup = [currTx];
            }
        }

        // Don't forget the last group
        if (currentGroup.length > 0) {
            groupedResults.push(createGroupedTransmitter(currentGroup, satGroup));
        }
    });

    return groupedResults;
}

/**
 * Create a grouped transmitter object.
 * If multiple transmitters are in the group, create a summary object.
 * If only one transmitter, return it as-is.
 */
function createGroupedTransmitter(transmitters, satGroup) {
    if (transmitters.length === 1) {
        // Single transmitter - return as-is
        return transmitters[0];
    }

    // Multiple transmitters - create a group summary
    // Use the average frequency of all transmitters in the group
    const avgFrequency = Math.round(
        transmitters.reduce((sum, tx) => sum + tx.doppler_frequency, 0) / transmitters.length
    );

    const groupSource = normalizeSource(transmitters[0]?.source);
    return {
        id: `group_${satGroup.satellite_norad_id}_${avgFrequency}`,
        satellite_name: satGroup.satellite_name,
        satellite_norad_id: satGroup.satellite_norad_id,
        doppler_frequency: avgFrequency,
        original_frequency: avgFrequency, // Not accurate but needed for structure
        doppler_shift: 0,
        description: `${transmitters.length} transmitters`,
        is_group: true,
        group_count: transmitters.length,
        source: groupSource,
        grouped_transmitters: transmitters
    };
}
