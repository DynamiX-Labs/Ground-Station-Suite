// Source: https://github.com/joergdietrich/Leaflet.Terminator

let _R2D = 180 / Math.PI;
let _D2R = Math.PI / 180;

let options = {
    interactive: false, // Disable "clickable" mouse pointer
        color: '#00',
        opacity: 0.4,
        fillColor: '#00',
        fillOpacity: 0.5,
        resolution: 5,
        longitudeRange: 1080
}

function julian(date) {
    /* Calculate the present UTC Julian Date. Function is valid after
     * the beginning of the UNIX epoch 1970-01-01 and ignores leap
     * seconds. */
    return (date / 86400000) + 2440587.5;
}

function GMST(julianDay) {
    /* Calculate Greenwich Mean Sidereal Time according to
         http://aa.usno.navy.mil/faq/docs/GAST.php */
    let d = julianDay - 2451545.0;
    // Low precision equation is good enough for our purposes.
    return (18.697374558 + 24.06570982441908 * d) % 24;
}

function createTerminatorLine() {
    let latLng = compute(new Date());
    return latLng;
}

function setTime (date) {
    options.time = date;
    let latLng = compute(date);
}

function sunEclipticPosition (julianDay) {
    /* Compute the position of the Sun in ecliptic coordinates at
         julianDay.  Following
         http://en.wikipedia.org/wiki/Position_of_the_Sun */
    // Days since start of J2000.0
    let n = julianDay - 2451545.0;
    // mean longitude of the Sun
    let L = 280.460 + 0.9856474 * n;
    L %= 360;
    // mean anomaly of the Sun
    let g = 357.528 + 0.9856003 * n;
    g %= 360;
    // ecliptic longitude of Sun
    let lambda = L + 1.915 * Math.sin(g * _D2R) +
        0.02 * Math.sin(2 * g * _D2R);
    // distance from Sun in AU
    let R = 1.00014 - 0.01671 * Math.cos(g * _D2R) -
        0.0014 * Math.cos(2 * g * _D2R);
    return {lambda: lambda, R: R};
}

function eclipticObliquity (julianDay) {
    // Following the short term expression in
    // http://en.wikipedia.org/wiki/Axial_tilt#Obliquity_of_the_ecliptic_.28Earth.27s_axial_tilt.29
    let n = julianDay - 2451545.0;
    // Julian centuries since J2000.0
    let T = n / 36525;
    let epsilon = 23.43929111 -
        T * (46.836769 / 3600
            - T * (0.0001831 / 3600
                + T * (0.00200340 / 3600
                    - T * (0.576e-6 / 3600
                        - T * 4.34e-8 / 3600))));
    return epsilon;
}

function sunEquatorialPosition (sunEclLng, eclObliq) {
    /* Compute the Sun's equatorial position from its ecliptic
     * position. Inputs are expected in degrees. Outputs are in
     * degrees as well. */
    let alpha = Math.atan(Math.cos(eclObliq * _D2R)
        * Math.tan(sunEclLng * _D2R)) * _R2D;
    let delta = Math.asin(Math.sin(eclObliq * _D2R)
        * Math.sin(sunEclLng * _D2R)) * _R2D;

    let lQuadrant = Math.floor(sunEclLng / 90) * 90;
    let raQuadrant = Math.floor(alpha / 90) * 90;
    alpha = alpha + (lQuadrant - raQuadrant);

    return {alpha: alpha, delta: delta};
}

function hourAngle (lng, sunPos, gst) {
    /* Compute the hour angle of the sun for a longitude on
     * Earth. Return the hour angle in degrees. */
    let lst = gst + lng / 15;
    return lst * 15 - sunPos.alpha;
}

function latitude (ha, sunPos) {
    /* For a given hour angle and sun position, compute the
     * latitude of the terminator in degrees. */
    let lat = Math.atan(-Math.cos(ha * _D2R) /
        Math.tan(sunPos.delta * _D2R)) * _R2D;
    return lat;
}

function compute (time) {
    let today = time ? new Date(time) : new Date();
    let julianDay = julian(today);
    let gst = GMST(julianDay);
    let latLng = [];

    let sunEclPos = sunEclipticPosition(julianDay);
    let eclObliq = eclipticObliquity(julianDay);
    let sunEqPos = sunEquatorialPosition(sunEclPos.lambda, eclObliq);
    for (let i = 0; i <= options.longitudeRange * options.resolution; i++) {
        let lng = -options.longitudeRange/2 + i / options.resolution;
        let ha = hourAngle(lng, sunEqPos, gst);
        latLng[i + 1] = [latitude(ha, sunEqPos), lng];
    }
    if (sunEqPos.delta < 0) {
        latLng[0] = [90, -options.longitudeRange/2];
        latLng[latLng.length] = [90, options.longitudeRange/2];
    } else {
        latLng[0] = [-90, -options.longitudeRange/2];
        latLng[latLng.length] = [-90, options.longitudeRange/2];
    }
    return latLng;
}

export default createTerminatorLine;
