// Constants for satellite pass timeline component

export const Y_AXIS_WIDTH = 25; // Width of elevation axis in pixels
export const X_AXIS_HEIGHT = 30; // Height of time axis in pixels
export const Y_AXIS_TOP_MARGIN = 25; // Top margin to prevent 90° label clipping
export const ZOOM_FACTOR = 1.3; // Zoom step multiplier (higher = bigger steps)

/**
 * UNIFIED COORDINATE SYSTEM:
 *
 * The chart area (excluding axes) uses this coordinate system:
 * - X-axis (Time): 0% = left edge (start time), 100% = right edge (end time)
 * - Y-axis (Elevation): 0% = top (90°), 100% = bottom (0°)
 *
 * Conversion formulas:
 * - Time to X%: ((time - startTime) / totalDuration) * 100
 * - Elevation to Y%: ((90 - elevation) / 90) * 100
 *
 * Chart boundaries in DOM:
 * - Left: Y_AXIS_WIDTH px
 * - Right: 100% of container
 * - Top: Y_AXIS_TOP_MARGIN px
 * - Bottom: Container height - X_AXIS_HEIGHT px
 */

/**
 * Helper function: Convert elevation degrees to Y percentage
 * @param {number} elevation - Elevation in degrees (0-90)
 * @returns {number} Y percentage (0-100, where 0% = 90°, 100% = 0°)
 */
export const elevationToYPercent = (elevation) => ((90 - elevation) / 90) * 100;
