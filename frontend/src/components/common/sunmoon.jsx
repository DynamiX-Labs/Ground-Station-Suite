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
 * Returns Julian Day for the given Date object.
 */
function getJulianDay(date) {
    // 2440587.5 = Julian date at Unix epoch (Jan 1 1970, 00:00:00 UTC).
    return date.getTime() / 86400000 + 2440587.5;
}

/**
 * Calculate the Greenwich Mean Sidereal Time (GMST) in degrees.
 * The result wraps to [0, 360).
 */
function getGMSTInDegrees(date) {
    // Julian Day relative to J2000 (Jan 1, 2000 12:00 TT, which is JD 2451545.0)
    const JD = getJulianDay(date);
    const n = JD - 2451545.0; // days since J2000

    // GMST in hours
    // 6.697374558 is the GMST at J2000 midnight
    // 0.06570982441908 ~ sidereal hours/solar day
    // plus the time of day in hours
    let GMST_hours = 6.697374558 + 0.06570982441908 * n
        + (date.getUTCHours()
            + date.getUTCMinutes() / 60
            + date.getUTCSeconds() / 3600);

    // Normalize to [0, 24)
    GMST_hours = GMST_hours % 24;
    if (GMST_hours < 0) {
        GMST_hours += 24;
    }

    // Convert hours to degrees: 360° / 24h = 15°/h
    return GMST_hours * 15;
}

/**
 * Computes sub-solar coordinates at the given Date.
 * Returns {lat, lng} in degrees.
 *
 * Approximate formulas:
 *  1. Mean anomaly, M = 357.528 + 0.9856003 * n
 *  2. Mean longitude, L0 = 280.460 + 0.9856474 * n
 *  3. Ecliptic longitude, λ = L0 + 1.915*sin(M) + 0.020*sin(2M)
 *  4. Obliquity, ε = 23.439 - 0.0000004*n
 *  5. Declination, δ = arcsin(sin(ε) * sin(λ))
 *  6. Right ascension (in degrees), α = atan2( cos(ε)*sin(λ), cos(λ) )
 *  7. GHA_sun = GMST - α  (in degrees)
 *  8. Sub-solar longitude = -GHA_sun
 */
export function getSubSolarCoords(date) {
    const JD = getJulianDay(date);
    const n = JD - 2451545.0;  // days since J2000

    // 1. Mean anomaly of the Sun (in degrees)
    const M = (357.528 + 0.9856003 * n) % 360;
    // 2. Mean longitude of the Sun
    const L0 = (280.460 + 0.9856474 * n) % 360;
    // 3. Ecliptic longitude (approx)
    const lambda = L0
        + 1.915 * Math.sin(M * Math.PI / 180)
        + 0.020 * Math.sin(2 * M * Math.PI / 180);

    // 4. Obliquity of the ecliptic (approx)
    const epsilon = 23.439 - 0.0000004 * n;

    // Convert to radians for trig
    const lambdaRad = lambda * Math.PI / 180;
    const epsilonRad = epsilon * Math.PI / 180;

    // 5. Declination
    const sinDec = Math.sin(epsilonRad) * Math.sin(lambdaRad);
    const dec = Math.asin(sinDec) * 180 / Math.PI; // in degrees

    // 6. Right ascension in degrees, range [0, 360)
    const y = Math.cos(epsilonRad) * Math.sin(lambdaRad);
    const x = Math.cos(lambdaRad);
    let alpha = Math.atan2(y, x) * 180 / Math.PI;
    if (alpha < 0) alpha += 360;

    // 7. Greenwich Mean Sidereal Time in degrees
    let GMST = getGMSTInDegrees(date);

    // 8. GHA = GMST - α (in degrees)
    let GHA = GMST - alpha;
    if (GHA < 0) {
        GHA += 360;
    }

    // Sub-solar latitude is declination
    const lat = dec;

    // Sub-solar longitude is -GHA
    // Normalize range to [-180, 180) if you prefer.
    let lng = -GHA;
    if (lng < -180) lng += 360;
    if (lng > 180) lng -= 360;

    return {lat, lng};
}

/**
 * Computes sub-lunar coordinates at the given Date.
 * Approximate approach (similar idea but with Moon orbit parameters).
 * Returns {lat, lng} in degrees.
 *
 * For more accurate sub-lunar calculations, you would:
 *  - Use the Moon’s mean longitude, mean anomaly, ascending node,
 *    inclination, etc. and do a similar approach to above.
 *  - Or rely on a specialized library for lunar position.
 */
export function getSubLunarCoords(date) {
    // This is a *very rough* approximation of the Moon’s position.
    // For demonstration only—real calculations are more involved.

    const JD = getJulianDay(date);
    const n = JD - 2451545.0;  // days since J2000

    // Moon's mean longitude (simplified)
    let Lm = (218.316 + 13.176396 * n) % 360;
    // Moon's mean anomaly
    let Mm = (134.963 + 13.064993 * n) % 360;
    // Moon's mean elongation
    let D = (297.850 + 12.190749 * n) % 360;

    // Ecliptic longitude (rough)
    let lambda = Lm
        + 6.289 * Math.sin(Mm * Math.PI / 180)    // main term
        - 1.274 * Math.sin((2 * D - Mm) * Math.PI / 180)
        + 0.658 * Math.sin((2 * D) * Math.PI / 180)
        - 0.214 * Math.sin((2 * Mm) * Math.PI / 180)
        - 0.110 * Math.sin(D * Math.PI / 180);

    // Ecliptic latitude (rough)
    let beta = 5.128 * Math.sin((93.272 + 13.229350 * n) * Math.PI / 180);

    // Obliquity of the ecliptic
    const epsilon = 23.439 - 0.0000004 * n;
    const epsilonRad = epsilon * Math.PI / 180;

    // Convert to radians
    let lambdaRad = lambda * Math.PI / 180;
    let betaRad = beta * Math.PI / 180;

    // Convert ecliptic coords -> equatorial coords
    let sinDec = Math.sin(betaRad) * Math.cos(epsilonRad)
        + Math.cos(betaRad) * Math.sin(epsilonRad) * Math.sin(lambdaRad);
    let dec = Math.asin(sinDec) * 180 / Math.PI;

    let y = Math.sin(lambdaRad) * Math.cos(epsilonRad)
        - Math.tan(betaRad) * Math.sin(epsilonRad);
    let x = Math.cos(lambdaRad);
    let alpha = Math.atan2(y, x) * 180 / Math.PI;
    if (alpha < 0) alpha += 360;

    // GMST
    let GMST = getGMSTInDegrees(date);

    // GHA of the Moon = GMST - RA
    let GHA = GMST - alpha;
    if (GHA < 0) {
        GHA += 360;
    }

    let lat = dec;
    let lng = -GHA;
    if (lng < -180) lng += 360;
    if (lng > 180) lng -= 360;

    return {lat, lng};
}

export function getSunMoonCoords() {
    const now = new Date();
    const subSolar = getSubSolarCoords(now);
    const subLunar = getSubLunarCoords(now);

    return [[subSolar.lat, subSolar.lng], [subLunar.lat, subLunar.lng]];
}
