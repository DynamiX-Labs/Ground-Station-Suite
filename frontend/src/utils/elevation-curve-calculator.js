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

/**
 * Calculate elevation curve for a single satellite pass with adaptive sampling.
 * This mirrors the backend implementation but runs in the browser using satellite.js.
 *
 * @param {Object} satelliteData - Object containing TLE data (tle1, tle2, norad_id)
 * @param {Object} homeLocation - Object with lat and lon keys (in degrees)
 * @param {string} eventStart - ISO format start time string
 * @param {string} eventEnd - ISO format end time string
 * @param {number} extendStartMinutes - Minutes to extend before event_start (default 0)
 * @returns {Array} Array of objects with time, elevation, azimuth, distance keys
 */
export function calculateElevationCurve(
    satelliteData,
    homeLocation,
    eventStart,
    eventEnd,
    extendStartMinutes = 0
) {
    try {
        // Parse TLE
        const satrec = satellite.twoline2satrec(satelliteData.tle1, satelliteData.tle2);

        // Check if TLE parsing failed
        if (satrec.error) {
            console.error(`TLE parsing error for satellite ${satelliteData.norad_id}: error code ${satrec.error}`);
            return [];
        }

        // Check for extreme BSTAR values that indicate rapid orbital decay
        const bstarThreshold = 0.01;
        if (satrec.bstar && Math.abs(satrec.bstar) > bstarThreshold) {
            // Skip silently - don't log error to avoid console spam
            // This satellite would cause performance issues during propagation
            return [];
        }

        // Parse times
        const startDt = new Date(eventStart);
        const endDt = new Date(eventEnd);

        // Extend by requested minutes before (for first pass) and 2 minutes after to ensure curve touches horizon
        const extendedStartDt = new Date(startDt.getTime() - Math.max(2, extendStartMinutes) * 60 * 1000);
        const extendedEndDt = new Date(endDt.getTime() + 2 * 60 * 1000);

        // Calculate duration including the buffer
        const totalDurationSeconds = (extendedEndDt.getTime() - extendedStartDt.getTime()) / 1000;

        // Adaptive sampling: aim for ~60-120 points per pass
        let sampleInterval;
        if (totalDurationSeconds < 600) {
            // Less than 10 minutes
            sampleInterval = 10; // 10 seconds
        } else if (totalDurationSeconds < 1800) {
            // Less than 30 minutes
            sampleInterval = 15; // 15 seconds
        } else {
            // 30 minutes or more
            sampleInterval = 30; // 30 seconds
        }

        // Calculate number of samples
        const numSamples = Math.max(Math.floor(totalDurationSeconds / sampleInterval), 2);

        // Observer position
        const observerGd = {
            longitude: satellite.degreesToRadians(homeLocation.lon),
            latitude: satellite.degreesToRadians(homeLocation.lat),
            height: 0 // altitude in km (assuming sea level)
        };

        // Calculate elevation at each time point
        const allPoints = [];
        const timeStep = totalDurationSeconds / (numSamples - 1);

        for (let i = 0; i < numSamples; i++) {
            const currentTime = new Date(extendedStartDt.getTime() + i * timeStep * 1000);

            // Propagate satellite position
            const positionAndVelocity = satellite.propagate(satrec, currentTime);

            if (!positionAndVelocity || !positionAndVelocity.position || satrec.error) {
                continue;
            }

            // Get GMST for this time
            const gmst = satellite.gstime(currentTime);

            // Calculate look angles from observer to satellite
            const positionEci = positionAndVelocity.position;
            const lookAngles = satellite.ecfToLookAngles(
                observerGd,
                satellite.eciToEcf(positionEci, gmst)
            );

            const elevationDeg = satellite.radiansToDegrees(lookAngles.elevation);
            const azimuthDeg = satellite.radiansToDegrees(lookAngles.azimuth);
            const rangeKm = lookAngles.rangeSat;

            allPoints.push({
                time: currentTime.toISOString(),
                elevation: Math.round(elevationDeg * 100) / 100,
                azimuth: Math.round(azimuthDeg * 100) / 100,
                distance: Math.round(rangeKm * 100) / 100
            });
        }

        // Filter to only include points above horizon, plus interpolate 0° crossing points
        const filteredPoints = [];

        for (let i = 0; i < allPoints.length; i++) {
            const point = allPoints[i];

            if (point.elevation >= 0) {
                // If this is the first positive point and there's a previous point
                if (filteredPoints.length === 0 && i > 0) {
                    const prevPoint = allPoints[i - 1];
                    if (prevPoint.elevation < 0) {
                        // Interpolate to find 0° crossing
                        const ratio = (0 - prevPoint.elevation) / (point.elevation - prevPoint.elevation);

                        const prevTime = new Date(prevPoint.time).getTime();
                        const currTime = new Date(point.time).getTime();
                        const interpolatedTime = new Date(prevTime + ratio * (currTime - prevTime));

                        filteredPoints.push({
                            time: interpolatedTime.toISOString(),
                            elevation: 0.0,
                            azimuth: Math.round((prevPoint.azimuth + ratio * (point.azimuth - prevPoint.azimuth)) * 100) / 100,
                            distance: Math.round((prevPoint.distance + ratio * (point.distance - prevPoint.distance)) * 100) / 100
                        });
                    }
                }

                // Add the positive elevation point
                filteredPoints.push(point);

                // If next point is negative, interpolate the 0° crossing at the end
                if (i < allPoints.length - 1) {
                    const nextPoint = allPoints[i + 1];
                    if (nextPoint.elevation < 0) {
                        // Interpolate to find 0° crossing
                        const ratio = (0 - point.elevation) / (nextPoint.elevation - point.elevation);

                        const currTime = new Date(point.time).getTime();
                        const nextTime = new Date(nextPoint.time).getTime();
                        const interpolatedTime = new Date(currTime + ratio * (nextTime - currTime));

                        filteredPoints.push({
                            time: interpolatedTime.toISOString(),
                            elevation: 0.0,
                            azimuth: Math.round((point.azimuth + ratio * (nextPoint.azimuth - point.azimuth)) * 100) / 100,
                            distance: Math.round((point.distance + ratio * (nextPoint.distance - point.distance)) * 100) / 100
                        });
                    }
                }
            }
        }

        return filteredPoints;

    } catch (error) {
        console.error(`Error calculating elevation curve for satellite ${satelliteData.norad_id}:`, error);
        return [];
    }
}

/**
 * Calculate elevation curves for multiple passes in parallel.
 * This function processes all passes and adds elevation_curve data to each pass object.
 *
 * @param {Array} passes - Array of pass objects
 * @param {Object} homeLocation - Object with lat and lon keys (in degrees)
 * @param {Object} satelliteLookup - Object mapping norad_id to satellite data (tle1, tle2)
 * @returns {Array} Array of passes with elevation_curve data added
 */
export function calculateElevationCurvesForPasses(passes, homeLocation, satelliteLookup) {
    if (!passes || !homeLocation || !satelliteLookup) {
        console.error('Missing required parameters for elevation curve calculation');
        return passes;
    }

    const currentTime = new Date();

    return passes.map(pass => {
        // Get satellite data for this pass
        const satelliteData = satelliteLookup[pass.norad_id];

        if (!satelliteData) {
            console.warn(`No satellite data found for NORAD ID ${pass.norad_id}`);
            return pass;
        }

        // Calculate time until pass starts (negative if already started)
        const eventStart = new Date(pass.event_start);
        const eventEnd = new Date(pass.event_end);
        const timeUntilStart = (eventStart - currentTime) / 60000; // minutes
        const timeSinceEnd = (currentTime - eventEnd) / 60000; // minutes

        // Extend if: pass is active OR starts within next 2 hours OR ended less than 30 min ago
        const shouldExtend = (timeUntilStart <= 120) && (timeSinceEnd <= 30);
        const extendStartMinutes = shouldExtend ? 30 : 0;

        // Calculate elevation curve
        const elevationCurve = calculateElevationCurve(
            satelliteData,
            homeLocation,
            pass.event_start,
            pass.event_end,
            extendStartMinutes
        );

        // Return pass with elevation curve added
        return {
            ...pass,
            elevation_curve: elevationCurve
        };
    });
}
