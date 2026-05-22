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
import { toast } from "../../utils/toast-with-timestamp.jsx";

/**
 * Calculates the latitude, longitude, altitude, and velocity of a satellite based on TLE data and date.
 *
 * @param noradId
 * @param {string} tleLine1 The first line of the two-line element set (TLE) describing the satellite's orbit.
 * @param {string} tleLine2 The second line of the two-line element set (TLE) describing the satellite's orbit.
 * @param {Date} date The date and time for which to calculate the satellite's position and velocity.
 * @return {Object|null} An object containing latitude (lat), longitude (lon), altitude, and velocity of the satellite.
 *                       Returns null if the satellite's position or velocity cannot be determined.
 */
export function getSatelliteLatLon(noradId, tleLine1, tleLine2, date) {

    try {
        if (!noradId || !tleLine1 || !tleLine2 || !date) {
            return [0, 0, 0, 0];
        }

        const satrec = satellite.twoline2satrec(tleLine1, tleLine2);

        // Check if TLE parsing failed
        // Error codes: 1=Eccentricity out of range, 2=Mean motion <=0, 3=Perturbed eccentricity,
        // 4=Semi-latus rectum <0, 6=Orbit decayed
        if (satrec.error) {
            console.error(`TLE parsing error for satellite ${noradId}: error code ${satrec.error}`);
            return [0, 0, 0, 0];
        }

        // Check for extreme BSTAR values that indicate rapid orbital decay
        // BSTAR > 0.01 typically indicates a satellite in rapid decay that will cause
        // satellite.js propagation to hang or take extremely long time
        const bstarThreshold = 0.01;
        if (satrec.bstar && Math.abs(satrec.bstar) > bstarThreshold) {
            return [0, 0, 0, 0];
        }

        const pv = satellite.propagate(satrec, date);

        // Check if propagation failed OR if propagation detected an error (like orbit decay)
        if (!pv || !pv.position || !pv.velocity || satrec.error) {
            console.warn(`Failed to propagate satellite ${noradId}: ${!pv ? 'null pv' : !pv.position ? 'no position' : !pv.velocity ? 'no velocity' : `error code ${satrec.error}`}`);
            return [0, 0, 0, 0];
        }

        const gmst = satellite.gstime(date);
        const geo = satellite.eciToGeodetic(pv.position, gmst);

        const lat = satellite.degreesLat(geo.latitude);
        const lon = satellite.degreesLong(geo.longitude);
        const altitude = geo.height;

        // Validate the calculated values
        if (!isFinite(lat) || !isFinite(lon) || !isFinite(altitude)) {
            console.error(`Invalid coordinates calculated for satellite ${noradId}: [${lat}, ${lon}, ${altitude}]`);
            return [0, 0, 0, 0];
        }

        const {x, y, z} = pv.velocity;
        const velocity = Math.sqrt(x * x + y * y + z * z);

        if (!isFinite(velocity)) {
            console.error(`Invalid velocity calculated for satellite ${noradId}: ${velocity}`);
            return [0, 0, 0, 0];
        }

        return [lat, lon, altitude, velocity];

    } catch (error) {
        console.error(`Error calculating satellite ${noradId} position and velocity: ${error.message}`);
        toast.error(`Error calculating satellite ${noradId} position and velocity: ${error.message}`, {
            autoClose: 5000,
        });

        return [0, 0, 0, 0];
    }
}

/**
 * Returns an array of { lat, lon } points representing the satellite’s
 * coverage area on Earth (its horizon circle), adjusted so that if the area
 * includes the north or South Pole, a vertex for that pole is inserted.
 *
 * @param {number} satLat - Satellite latitude in degrees.
 * @param {number} satLon - Satellite longitude in degrees.
 * @param {number} altitudeKm - Satellite altitude above Earth's surface in km.
 * @param {number} [numPoints=36] - Number of segments for the circle boundary.
 *                                  (The resulting array will have numPoints+1 points.)
 * @return {Array<{lat: number, lon: number}>} The polygon (in degrees) for the coverage area.
 */
export function getSatelliteCoverageCircle(satLat, satLon, altitudeKm, numPoints = 36) {
    try {
        // Mean Earth radius in kilometers (WGS-84 approximate)
        const R_EARTH = 6378.137;

        // Convert satellite subpoint to radians
        const lat0 = (satLat * Math.PI) / 180;
        const lon0 = (satLon * Math.PI) / 180;

        // Compute angular radius of the coverage circle (in radians)
        // d = arccos(R_EARTH / (R_EARTH + altitudeKm))
        const d = Math.acos(R_EARTH / (R_EARTH + altitudeKm));

        // Generate the circle points (closed polygon)
        const circlePoints = [];
        for (let i = 0; i <= numPoints; i++) {
            const theta = (2 * Math.PI * i) / numPoints;

            // Using spherical trigonometry to compute a point d away from (lat0,lon0)
            const lat_i = Math.asin(
                Math.sin(lat0) * Math.cos(d) +
                Math.cos(lat0) * Math.sin(d) * Math.cos(theta)
            );
            const lon_i = lon0 + Math.atan2(
                Math.sin(d) * Math.sin(theta) * Math.cos(lat0),
                Math.cos(d) - Math.sin(lat0) * Math.sin(lat_i)
            );

            // Convert back to degrees and normalize longitude to [-180, 180)
            const latDeg = (lat_i * 180) / Math.PI;
            let lonDeg = (lon_i * 180) / Math.PI;
            //lonDeg = ((lonDeg + 540) % 360) - 180;

            circlePoints.push({ lat: latDeg, lon: lonDeg });
        }

        // Adjust the polygon if it should include a pole.
        // Condition for North Pole inclusion: the spherical cap extends beyond the North Pole.
        // (That is, if d > (π/2 - lat0)). Similarly, for the South Pole: d > (π/2 + lat0) when lat0 is negative.
        let adjustedPoints = circlePoints.slice();

        // North Pole case (for satellites in the northern hemisphere or whose cap covers the north)
        if (d > (Math.PI / 2 - lat0)) {
            // Find the index with the maximum latitude (the highest point in our computed circle)
            let maxIndex = 0, maxLat = -Infinity;
            for (let i = 0; i < circlePoints.length; i++) {
                if (circlePoints[i].lat > maxLat) {
                    maxLat = circlePoints[i].lat;
                    maxIndex = i;
                }
            }
            // Insert the North Pole as an extra vertex immediately after the highest point.
            // (Using the same longitude as that highest point.)
            adjustedPoints = [
                { lat: 90, lon: circlePoints[0].lon },
                ...circlePoints.slice(0, maxIndex + 1),
                ...circlePoints.slice(maxIndex + 1),
                { lat: 90, lon: circlePoints[circlePoints.length - 1].lon },
            ];
        }

        // South Pole case (for satellites in the southern hemisphere or whose cap covers the south)
        if (d > (Math.PI / 2 + lat0)) {
            // Find the index with the minimum latitude (the lowest point in our computed circle)
            let minIndex = 0, minLat = Infinity;
            for (let i = 0; i < circlePoints.length; i++) {
                if (circlePoints[i].lat < minLat) {
                    minLat = circlePoints[i].lat;
                    minIndex = i;
                }
            }
            // Insert the South Pole as an extra vertex immediately after the lowest point.
            adjustedPoints = [
                ...adjustedPoints.slice(0, minIndex + 1),
                { lat: -90, lon: circlePoints[minIndex].lon },
                { lat: -90, lon: circlePoints[minIndex + 1].lon },
                ...adjustedPoints.slice(minIndex + 1),
            ];
        }

        return adjustedPoints;
    } catch (error) {
        console.error("Error computing satellite coverage circle:", error);
        return [];
    }
}

/**
 * Normalizes a longitude value to be within -180 to 180 degrees.
 * @param {number} lon - The longitude in degrees.
 * @returns {number} - The normalized longitude.
 */
export function normalizeLongitude(lon) {
    while (lon > 180) {
        lon -= 360;
    }
    while (lon < -180) {
        lon += 360;
    }
    return lon;
}

/**
 * Splits an array of points into segments so that no segment contains a jump
 * greater than 180 degrees in longitude.
 *
 * @param {Array} points - An array of objects of the form {lat, lon}.
 * @returns {Array} - Either an array of points (if only one segment exists) or an array of segments.
 */
export function splitAtDateline(points) {
    if (points.length === 0) return points;
    const segments = [];
    let currentSegment = [points[0]];

    for (let i = 1; i < points.length; i++) {
        const prev = points[i - 1];
        const curr = points[i];
        // Because our points are normalized, a jump of more than 180 degrees
        // indicates a crossing of the dateline.
        if (Math.abs(curr.lon - prev.lon) > 180) {
            // End the current segment and start a new one.
            segments.push(currentSegment);
            currentSegment = [curr];
        } else {
            currentSegment.push(curr);
        }
    }
    segments.push(currentSegment);
    // If there is only one segment, return it directly; otherwise return the segments.
    return segments.length === 1 ? segments[0] : segments;
}

/**
 * Computes the satellite's past and future path coordinates from its TLE.
 * The path is computed at a fixed time step and then split into segments so that
 * no segment contains a line crossing the dateline (+180 or -180 longitude).
 *
 * @param {Array} tle - An array containing two TLE lines [line1, line2].
 * @param {number} durationMinutes - The projection duration (in minutes) for both past and future.
 * @param {number} [stepMinutes=1] - (Optional) The time interval in minutes between coordinate samples.
 * @param {number} [noradId=null] - (Optional) NORAD ID for debug logging.
 * @returns {Object} An object with two properties:
 *                   { past: [{lat, lon}] or [[{lat, lon}], ...],
 *                     future: [{lat, lon}] or [[{lat, lon}], ...] }
 */
export function getSatellitePaths(tle, durationMinutes, stepMinutes = 1, noradId = null) {
    try {
        // Create a satellite record from the provided TLE
        const satrec = satellite.twoline2satrec(tle[0], tle[1]);

        // Check if TLE parsing failed
        if (satrec.error) {
            console.error(`TLE parsing error in getSatellitePaths: error code ${satrec.error}`);
            return { past: [], future: [] };
        }

        // Check for extreme BSTAR values that would cause propagation to hang
        const bstarThreshold = 0.01;
        if (satrec.bstar && Math.abs(satrec.bstar) > bstarThreshold) {
            // Skip silently - this satellite would cause severe performance issues
            return { past: [], future: [] };
        }

        const now = new Date();
        const pastPoints = [];
        const futurePoints = [];
        const stepMs = stepMinutes * 60 * 1000;

        // Compute past points: from (now - durationMinutes) up to now (inclusive)
        for (let t = now.getTime() - durationMinutes * 60 * 1000; t <= now.getTime(); t += stepMs) {
            const time = new Date(t);
            const pv = satellite.propagate(satrec, time);
            const position = pv ? pv.position : null;

            // Check for propagation errors (orbit decay, etc)
            if (!pv || satrec.error) {
                console.warn(`Satellite path propagation error at time ${time}: ${!pv ? 'null pv' : `error code ${satrec.error}`}`);
                break; // Stop calculating path if propagation fails
            }
            if (position) {
                const gmst = satellite.gstime(time);
                const posGd = satellite.eciToGeodetic(position, gmst);
                let lon = normalizeLongitude(satellite.degreesLong(posGd.longitude));
                const lat = satellite.degreesLat(posGd.latitude);
                // Validate coordinates before adding
                if (isFinite(lat) && isFinite(lon)) {
                    pastPoints.push({ lat, lon });
                }
            }
        }

        // Compute future points: from now up to (now + durationMinutes) (inclusive)
        for (let t = now.getTime(); t <= now.getTime() + durationMinutes * 60 * 1000; t += stepMs) {
            const time = new Date(t);
            const pv = satellite.propagate(satrec, time);
            const position = pv ? pv.position : null;

            // Check for propagation errors (orbit decay, etc)
            if (!pv || satrec.error) {
                console.warn(`Satellite path propagation error at time ${time}: ${!pv ? 'null pv' : `error code ${satrec.error}`}`);
                break; // Stop calculating path if propagation fails
            }
            if (position) {
                const gmst = satellite.gstime(time);
                const posGd = satellite.eciToGeodetic(position, gmst);
                let lon = normalizeLongitude(satellite.degreesLong(posGd.longitude));
                const lat = satellite.degreesLat(posGd.latitude);
                // Validate coordinates before adding
                if (isFinite(lat) && isFinite(lon)) {
                    futurePoints.push({ lat, lon });
                }
            }
        }

        // Split the past and future arrays into segments to avoid drawing lines across the dateline.
        const past = splitAtDateline(pastPoints);
        const future = splitAtDateline(futurePoints);

        return { past, future };
    } catch (error) {
        console.error("Error computing satellite paths:", error);
        toast.error("Error computing satellite paths: " + error.message, {
            autoClose: 5000,
        });
        return { past: [], future: [] };
    }
}

/**
 * Determines whether a satellite is geostationary based on its TLE.
 * @param {string[]} tle - An array of two TLE lines [line1, line2].
 * @returns {boolean} - True if the orbit is approximately geostationary, false otherwise.
 */
function isGeostationary(tle) {
    if (!Array.isArray(tle) || tle.length < 2) {
        throw new Error("TLE must be an array containing two lines of valid TLE data.");
    }

    const line2 = tle[1];

    // Each field in Line 2 has a fixed position (character index). Refer to the TLE format.
    // - Inclination (degrees):    columns 8-15
    // - RA of ascending node:     columns 17-24
    // - Eccentricity:            columns 26-32 (decimal point is implied at the start)
    // - Argument of perigee:     columns 34-41
    // - Mean anomaly:            columns 43-50
    // - Mean motion (rev/day):   columns 52-62
    // - Revolution number:       columns 63-68 (not used here)

    const inclinationDeg = parseFloat(line2.substring(8, 16));
    // Eccentricity is typically given as an integer with an implied decimal point at the beginning.
    // For example, "0000457" means 0.0000457
    const eccentricityStr = line2.substring(26, 33);
    const eccentricity = parseFloat(`0.${eccentricityStr}`);
    const meanMotion = parseFloat(line2.substring(52, 63));

    // Typical checks for geostationary orbit:
    // 1. Mean motion ~ 1 revolution per sidereal day ≈ 1.0027 rev/day
    //    Here we allow a small range around 1.0–1.0027 for tolerance.
    // 2. Inclination close to 0° (must be near the equator)
    // 3. Eccentricity near 0 (circular orbit)

    // Define thresholds (can be tweaked depending on desired strictness)
    const meanMotionLower = 0.995;    // Lower bound on mean motion
    const meanMotionUpper = 1.005;    // Upper bound on mean motion
    const inclinationMax   = 3.0;     // Degrees (allow small inclination for station-keeping)
    const eccentricityMax  = 0.01;    // Allow small eccentricity

    const isMeanMotionOK   = meanMotion >= meanMotionLower && meanMotion <= meanMotionUpper;
    const isInclinationOK  = inclinationDeg <= inclinationMax;
    const isEccentricityOK = eccentricity <= eccentricityMax;

    return isMeanMotionOK && isInclinationOK && isEccentricityOK;
}


/**
 * Determines if a satellite is visible from a specific location on Earth,
 * considering line of sight with an elevation angle as low as 1 degree.
 *
 * @param {string} tleLine1 - The first line of the TLE data.
 * @param {string} tleLine2 - The second line of the TLE data.
 * @param {Date} date - The date and time to check visibility.
 * @param {Object} observerCoords - The observer's coordinates.
 * @param {number} observerCoords.lat - The observer's latitude in degrees.
 * @param {number} observerCoords.lon - The observer's longitude in degrees.
 * @param {number} observerCoords.alt - The observer's altitude in meters (default: 0).
 * @param {number} minElevation - Minimum elevation angle in degrees for visibility (default: 1).
 * @return {boolean} True if the satellite is visible from the observer's location, false otherwise.
 */
export function isSatelliteVisible(tleLine1, tleLine2, date, observerCoords, minElevation = 0) {
    try {
        if (!tleLine1 || !tleLine2 || !date || !observerCoords) {
            return false;
        }

        // Extract observer coordinates and set defaults
        const { lat, lon, alt = 0 } = observerCoords;

        // Initialize satellite record from TLE data
        const satrec = satellite.twoline2satrec(tleLine1, tleLine2);

        // Get satellite position in ECI coordinates
        const positionAndVelocity = satellite.propagate(satrec, date);
        if (!positionAndVelocity || !positionAndVelocity.position) {
            return false;
        }

        // Get observer's position in ECEF coordinates
        const observerGd = {
            longitude: satellite.degreesToRadians(lon),
            latitude: satellite.degreesToRadians(lat),
            height: alt / 1000 // Convert meters to kilometers
        };

        const observerEcf = satellite.geodeticToEcf(observerGd);

        // Get current Greenwich Mean Sidereal Time
        const gmst = satellite.gstime(date);

        // Convert satellite position from ECI to ECEF coordinates
        const positionEcf = satellite.eciToEcf(positionAndVelocity.position, gmst);

        // Calculate look angles (azimuth, elevation, range) from observer to satellite
        const lookAngles = satellite.ecfToLookAngles(observerGd, positionEcf);

        // Convert elevation from radians to degrees
        const elevationDeg = satellite.degreesLat(lookAngles.elevation);

        // Satellite is visible if elevation is greater than or equal to the minimum required
        return elevationDeg >= minElevation;

    } catch (error) {
        console.error("Error calculating satellite visibility:", error);
        return false;
    }
}

/**
 * Calculate the great-circle distance between two lat/lon points on Earth (in km).
 * Uses the haversine formula.
 *
 * @param {number} lat1 - Latitude of point 1 (in degrees).
 * @param {number} lon1 - Longitude of point 1 (in degrees).
 * @param {number} lat2 - Latitude of point 2 (in degrees).
 * @param {number} lon2 - Longitude of point 2 (in degrees).
 * @returns {number} Distance in kilometers.
 */
function calculateGreatCircleDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Approx Earth radius in km

    // Convert degrees to radians
    const dLat = toRadians(lat2 - lat1);
    const dLon = toRadians(lon2 - lon1);
    const radLat1 = toRadians(lat1);
    const radLat2 = toRadians(lat2);

    // Haversine formula
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
        + Math.cos(radLat1) * Math.cos(radLat2)
        * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

function toRadians(deg) {
    return deg * (Math.PI / 180);
}


/**
 * Calculates the current azimuth and elevation of a satellite from a ground station.
 *
 * @param {string} tleLine1 - The first line of the two-line element set (TLE).
 * @param {string} tleLine2 - The second line of the two-line element set (TLE).
 * @param {Object} groundStation - The ground station location.
 * @param {number} groundStation.lat - Ground station latitude in degrees.
 * @param {number} groundStation.lon - Ground station longitude in degrees.
 * @param {number} [groundStation.alt=0] - Ground station altitude in meters (default: 0).
 * @param {Date} [date=new Date()] - The date and time for calculation (default: current time).
 * @returns {Object|null} An object containing azimuth and elevation in degrees, or null if calculation fails.
 *                        Format: { azimuth: number, elevation: number, range: number }
 */
export function calculateSatelliteAzEl(tleLine1, tleLine2, groundStation, date = new Date()) {
    try {
        // Validate inputs
        if (!tleLine1 || !tleLine2 || !groundStation ||
            groundStation.lat === undefined || groundStation.lon === undefined) {
            console.error("Invalid input parameters for satellite AzEl calculation");
            return null;
        }

        // Extract ground station coordinates with defaults
        const { lat, lon, alt = 0 } = groundStation;

        // Validate coordinate ranges
        if (lat < -90 || lat > 90) {
            console.error("Latitude must be between -90 and 90 degrees");
            return null;
        }

        // Normalize longitude to [-180, 180] range
        let normalizedLon = lon;
        while (normalizedLon > 180) normalizedLon -= 360;
        while (normalizedLon < -180) normalizedLon += 360;

        // Initialize satellite record from TLE data
        const satrec = satellite.twoline2satrec(tleLine1, tleLine2);

        // Check if TLE parsing failed
        if (satrec.error) {
            console.error(`TLE parsing error in AzEl calculation: error code ${satrec.error}`);
            return null;
        }

        // Check for extreme BSTAR values that indicate rapid orbital decay
        const bstarThreshold = 0.01;
        if (satrec.bstar && Math.abs(satrec.bstar) > bstarThreshold) {
            // Skip silently - don't log to avoid console spam when called repeatedly
            return null;
        }

        // Get satellite position and velocity in ECI coordinates
        const positionAndVelocity = satellite.propagate(satrec, date);
        if (!positionAndVelocity || !positionAndVelocity.position || satrec.error) {
            console.error(`Failed to propagate satellite position: ${!positionAndVelocity ? 'null result' : !positionAndVelocity.position ? 'no position' : `error code ${satrec.error}`}`);
            return null;
        }

        // Set up observer's geodetic coordinates (using radians)
        const observerGd = {
            longitude: normalizedLon * (Math.PI / 180), // Convert to radians manually
            latitude: lat * (Math.PI / 180),            // Convert to radians manually
            height: alt / 1000 // Convert meters to kilometers
        };

        // Get current Greenwich Mean Sidereal Time
        const gmst = satellite.gstime(date);

        // Convert satellite position from ECI to ECEF coordinates
        const positionEcf = satellite.eciToEcf(positionAndVelocity.position, gmst);

        // Calculate look angles (azimuth, elevation, range) from observer to satellite
        const lookAngles = satellite.ecfToLookAngles(observerGd, positionEcf);

        // Convert from radians to degrees
        let azimuthDeg = lookAngles.azimuth * (180 / Math.PI);
        const elevationDeg = lookAngles.elevation * (180 / Math.PI);
        const rangeKm = lookAngles.rangeSat; // Range in kilometers

        // Validate calculated values
        if (!isFinite(azimuthDeg) || !isFinite(elevationDeg) || !isFinite(rangeKm)) {
            console.error(`Invalid AzEl values calculated: [${azimuthDeg}, ${elevationDeg}, ${rangeKm}]`);
            return null;
        }

        // Normalize azimuth to 0-360 degrees
        while (azimuthDeg < 0) azimuthDeg += 360;
        while (azimuthDeg >= 360) azimuthDeg -= 360;

        return [
            azimuthDeg,
            elevationDeg,
            rangeKm
        ];

    } catch (error) {
        console.error("Error calculating satellite azimuth and elevation:", error);
        toast.error("Error calculating satellite tracking data: " + error.message, {
            autoClose: 5000,
        });
        return null;
    }
}

/**
 * Calculate time to maximum elevation for a satellite
 * @param {string} tleLine1 - First line of TLE
 * @param {string} tleLine2 - Second line of TLE
 * @param {object} groundStation - Ground station coordinates {lat, lon, alt}
 * @param {Date} startDate - Start date for calculation
 * @param {number} maxMinutes - Maximum time to look ahead (default 30 minutes)
 * @returns {number|null} - Time to max elevation in seconds, or null if satellite is descending or error
 */
export function calculateTimeToMaxElevation(tleLine1, tleLine2, groundStation, startDate = new Date(), maxMinutes = 30) {
    try {
        let maxEl = -90;
        let maxElTime = null;
        const stepSeconds = 10; // Check every 10 seconds
        const maxSteps = (maxMinutes * 60) / stepSeconds;

        // Get current elevation
        const currentData = calculateSatelliteAzEl(tleLine1, tleLine2, groundStation, startDate);
        if (!currentData) return null;

        const currentEl = currentData[1];

        // If satellite is below horizon, don't calculate
        if (currentEl < 0) return null;

        maxEl = currentEl;

        // Look ahead in time
        for (let i = 1; i <= maxSteps; i++) {
            const futureDate = new Date(startDate.getTime() + (i * stepSeconds * 1000));
            const data = calculateSatelliteAzEl(tleLine1, tleLine2, groundStation, futureDate);

            if (!data) continue;

            const el = data[1];

            // If below horizon, we've passed the peak
            if (el < 0) break;

            if (el > maxEl) {
                maxEl = el;
                maxElTime = i * stepSeconds;
            } else if (maxElTime !== null && el < maxEl - 0.5) {
                // If elevation is dropping significantly after finding max, we found the peak
                break;
            }
        }

        return maxElTime;
    } catch (error) {
        console.error("Error calculating time to max elevation:", error);
        return null;
    }
}