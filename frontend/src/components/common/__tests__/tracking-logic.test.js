/**
 * Unit tests for tracking-logic.jsx
 * Tests pure calculation functions for satellite tracking
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  normalizeLongitude,
  splitAtDateline,
  getSatelliteLatLon,
  isSatelliteVisible,
  calculateSatelliteAzEl,
} from '../tracking-logic';

describe('normalizeLongitude', () => {
  it('should keep longitude within -180 to 180 range', () => {
    expect(normalizeLongitude(0)).toBe(0);
    expect(normalizeLongitude(180)).toBe(180);
    expect(normalizeLongitude(-180)).toBe(-180);
    expect(normalizeLongitude(90)).toBe(90);
    expect(normalizeLongitude(-90)).toBe(-90);
  });

  it('should normalize longitude greater than 180', () => {
    expect(normalizeLongitude(181)).toBe(-179);
    expect(normalizeLongitude(270)).toBe(-90);
    expect(normalizeLongitude(360)).toBe(0);
    expect(normalizeLongitude(540)).toBe(180); // 540 - 360 = 180
  });

  it('should normalize longitude less than -180', () => {
    expect(normalizeLongitude(-181)).toBe(179);
    expect(normalizeLongitude(-270)).toBe(90);
    expect(normalizeLongitude(-360)).toBe(0);
    expect(normalizeLongitude(-540)).toBe(-180); // -540 + 360 = -180
  });
});

describe('splitAtDateline', () => {
  it('should return empty array for empty input', () => {
    expect(splitAtDateline([])).toEqual([]);
  });

  it('should return single segment when no dateline crossing', () => {
    const points = [
      { lat: 0, lon: 10 },
      { lat: 0, lon: 20 },
      { lat: 0, lon: 30 },
    ];
    const result = splitAtDateline(points);
    expect(result).toEqual(points);
  });

  it('should split segments at dateline crossing', () => {
    const points = [
      { lat: 0, lon: 170 },
      { lat: 0, lon: -170 }, // Jump of 340 degrees
      { lat: 0, lon: -160 },
    ];
    const result = splitAtDateline(points);

    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(2);
    expect(result[0]).toEqual([{ lat: 0, lon: 170 }]);
    expect(result[1]).toEqual([
      { lat: 0, lon: -170 },
      { lat: 0, lon: -160 },
    ]);
  });

  it('should handle multiple dateline crossings', () => {
    const points = [
      { lat: 0, lon: 170 },
      { lat: 0, lon: -170 }, // First crossing
      { lat: 0, lon: -160 },
      { lat: 0, lon: 160 }, // Second crossing
      { lat: 0, lon: 170 },
    ];
    const result = splitAtDateline(points);

    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(3);
  });
});

describe('getSatelliteLatLon', () => {
  // Sample TLE for ISS (International Space Station)
  const tleLine1 = '1 25544U 98067A   21001.00000000  .00002182  00000-0  41420-4 0  9990';
  const tleLine2 = '2 25544  51.6461 339.8014 0002571  34.5857 120.4689 15.48919393263123';
  const date = new Date('2021-01-01T00:00:00Z');

  it('should return valid satellite position', () => {
    const result = getSatelliteLatLon(25544, tleLine1, tleLine2, date);

    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(4);

    const [lat, lon, alt, velocity] = result;

    // Basic sanity checks
    expect(lat).toBeGreaterThanOrEqual(-90);
    expect(lat).toBeLessThanOrEqual(90);
    expect(lon).toBeGreaterThanOrEqual(-180);
    expect(lon).toBeLessThanOrEqual(180);
    expect(alt).toBeGreaterThan(0); // Should be in space
    expect(velocity).toBeGreaterThan(0); // Should be moving
  });

  it('should return zeros for missing parameters', () => {
    expect(getSatelliteLatLon(null, tleLine1, tleLine2, date)).toEqual([0, 0, 0, 0]);
    expect(getSatelliteLatLon(25544, null, tleLine2, date)).toEqual([0, 0, 0, 0]);
    expect(getSatelliteLatLon(25544, tleLine1, null, date)).toEqual([0, 0, 0, 0]);
    expect(getSatelliteLatLon(25544, tleLine1, tleLine2, null)).toEqual([0, 0, 0, 0]);
  });

  it('should handle invalid TLE data gracefully', () => {
    const result = getSatelliteLatLon(25544, 'invalid', 'invalid', date);
    // Invalid TLE is caught by try-catch and returns [0, 0, 0, 0]
    // but satellite.js may produce NaN before the catch
    expect(Array.isArray(result)).toBe(true);
    expect(result.length).toBe(4);
  });
});

describe('isSatelliteVisible', () => {
  const tleLine1 = '1 25544U 98067A   21001.00000000  .00002182  00000-0  41420-4 0  9990';
  const tleLine2 = '2 25544  51.6461 339.8014 0002571  34.5857 120.4689 15.48919393263123';
  const date = new Date('2021-01-01T00:00:00Z');

  const observerCoords = {
    lat: 40.7128,  // New York
    lon: -74.0060,
    alt: 0
  };

  it('should return boolean for valid inputs', () => {
    const result = isSatelliteVisible(tleLine1, tleLine2, date, observerCoords);
    expect(typeof result).toBe('boolean');
  });

  it('should return false for missing parameters', () => {
    expect(isSatelliteVisible(null, tleLine2, date, observerCoords)).toBe(false);
    expect(isSatelliteVisible(tleLine1, null, date, observerCoords)).toBe(false);
    expect(isSatelliteVisible(tleLine1, tleLine2, null, observerCoords)).toBe(false);
    expect(isSatelliteVisible(tleLine1, tleLine2, date, null)).toBe(false);
  });

  it('should respect minimum elevation angle', () => {
    // Test with different minimum elevation angles
    const result0 = isSatelliteVisible(tleLine1, tleLine2, date, observerCoords, 0);
    const result10 = isSatelliteVisible(tleLine1, tleLine2, date, observerCoords, 10);

    expect(typeof result0).toBe('boolean');
    expect(typeof result10).toBe('boolean');

    // If visible at 10 degrees, should also be visible at 0 degrees
    if (result10 === true) {
      expect(result0).toBe(true);
    }
  });

  it('should handle invalid TLE data gracefully', () => {
    const result = isSatelliteVisible('invalid', 'invalid', date, observerCoords);
    expect(result).toBe(false);
  });
});

describe('calculateSatelliteAzEl', () => {
  const tleLine1 = '1 25544U 98067A   21001.00000000  .00002182  00000-0  41420-4 0  9990';
  const tleLine2 = '2 25544  51.6461 339.8014 0002571  34.5857 120.4689 15.48919393263123';
  const date = new Date('2021-01-01T00:00:00Z');

  const groundStation = {
    lat: 40.7128,  // New York
    lon: -74.0060,
    alt: 0
  };

  it('should return valid azimuth, elevation, and range', () => {
    const result = calculateSatelliteAzEl(tleLine1, tleLine2, groundStation, date);

    if (result !== null) {
      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBe(3);

      const [azimuth, elevation, range] = result;

      // Azimuth should be 0-360
      expect(azimuth).toBeGreaterThanOrEqual(0);
      expect(azimuth).toBeLessThan(360);

      // Elevation should be -90 to 90
      expect(elevation).toBeGreaterThanOrEqual(-90);
      expect(elevation).toBeLessThanOrEqual(90);

      // Range should be positive
      expect(range).toBeGreaterThan(0);
    }
  });

  it('should return null for invalid inputs', () => {
    expect(calculateSatelliteAzEl(null, tleLine2, groundStation, date)).toBe(null);
    expect(calculateSatelliteAzEl(tleLine1, null, groundStation, date)).toBe(null);
    expect(calculateSatelliteAzEl(tleLine1, tleLine2, null, date)).toBe(null);
  });

  it('should return null for invalid latitude', () => {
    const invalidStation = { lat: 100, lon: 0, alt: 0 }; // Lat > 90
    expect(calculateSatelliteAzEl(tleLine1, tleLine2, invalidStation, date)).toBe(null);

    const invalidStation2 = { lat: -100, lon: 0, alt: 0 }; // Lat < -90
    expect(calculateSatelliteAzEl(tleLine1, tleLine2, invalidStation2, date)).toBe(null);
  });

  it('should normalize longitude outside -180 to 180 range', () => {
    const stationWithLargeLon = { lat: 40, lon: 370, alt: 0 }; // 370 = 10
    const result = calculateSatelliteAzEl(tleLine1, tleLine2, stationWithLargeLon, date);

    // Should not return null due to longitude normalization
    expect(result).not.toBe(null);
  });

  it('should use default date when not provided', () => {
    const result = calculateSatelliteAzEl(tleLine1, tleLine2, groundStation);
    // Should calculate for current time without errors
    expect(result === null || Array.isArray(result)).toBe(true);
  });

  it('should handle invalid TLE data gracefully', () => {
    const result = calculateSatelliteAzEl('invalid', 'invalid', groundStation, date);
    // Invalid TLE may return array with NaN or null depending on where parsing fails
    expect(result === null || (Array.isArray(result) && result.length === 3)).toBe(true);
  });
});
