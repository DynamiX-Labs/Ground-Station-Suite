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
 * Developed with the assistance of Claude (Anthropic AI Assistant)
 */

/**
 * Auto-scaling logic for dynamic dB range adjustment
 */

/**
 * Store FFT data in history for auto-scaling
 * @param {Array<number>} newFftData - New FFT data
 * @param {Array<Array<number>>} waterfallHistory - History of waterfall data
 * @param {number} maxHistoryLength - Maximum history length
 * @returns {Array<Array<number>>} Updated history
 */
export function storeFFTDataInHistory(newFftData, waterfallHistory, maxHistoryLength) {
    // Add new FFT data to history
    waterfallHistory.push([...newFftData]);

    // Keep only the last N frames for analysis
    if (waterfallHistory.length > maxHistoryLength) {
        waterfallHistory.shift();
    }

    return waterfallHistory;
}

/**
 * Auto-scale dB range based on waterfall history
 * @param {Array<Array<number>>} waterfallHistory - History of waterfall data
 * @param {string} preset - 'strong', 'medium', or 'weak'
 * @returns {Object} New dB range and statistics
 */
export function autoScaleDbRange(waterfallHistory, preset = 'medium') {
    if (waterfallHistory.length === 0) {
        return null;
    }

    // Only use the most recent 10 frames for auto-scaling (matches old behavior)
    const samplesToCheck = Math.min(10, waterfallHistory.length);
    const recentFrames = waterfallHistory.slice(0, samplesToCheck);

    // Flatten FFT data from recent frames into a single array for analysis
    const allValues = recentFrames.flat();

    // Sort values for percentile calculation
    const sortedValues = allValues.slice().sort((a, b) => a - b);

    // Apply different scaling strategies based on preset (matches old behavior exactly)
    let minDb, maxDb;

    switch (preset) {
        case 'strong': {
            // For strong signals: Very wide dB range to handle strong signals without clipping
            // Use 2nd to 99th percentile for maximum range
            const strongLowIdx = Math.floor(sortedValues.length * 0.02);
            const strongHighIdx = Math.floor(sortedValues.length * 0.99);
            minDb = sortedValues[strongLowIdx];
            maxDb = sortedValues[strongHighIdx];
            // Extra padding for strong signals
            minDb = Math.floor(minDb - 10);
            maxDb = Math.ceil(maxDb + 10);
            break;
        }

        case 'medium': {
            // For medium signals: Moderate range, less strict than weak
            // Use 5th to 97th percentile
            const mediumLowIdx = Math.floor(sortedValues.length * 0.05);
            const mediumHighIdx = Math.floor(sortedValues.length * 0.97);
            minDb = sortedValues[mediumLowIdx];
            maxDb = sortedValues[mediumHighIdx];
            // Moderate padding
            minDb = Math.floor(minDb - 5);
            maxDb = Math.ceil(maxDb + 5);
            break;
        }

        case 'weak':
        default: {
            // For weak signals: Original algorithm with std dev filtering (tight range, good contrast)
            const sum = allValues.reduce((acc, val) => acc + val, 0);
            const mean = sum / allValues.length;

            const squaredDiffs = allValues.map(val => (val - mean) ** 2);
            const variance = squaredDiffs.reduce((acc, val) => acc + val, 0) / allValues.length;
            const stdDev = Math.sqrt(variance);

            // Filter out values more than X standard deviations from the mean
            const stdDevMultiplier = 4.5;
            const filteredValues = allValues.filter(val =>
                Math.abs(val - mean) <= stdDevMultiplier * stdDev
            );

            if (filteredValues.length === 0) {
                console.warn('No valid values after filtering for auto-scaling');
                return null;
            }

            minDb = filteredValues.reduce((a, b) => Math.min(a, b), filteredValues[0]);
            maxDb = filteredValues.reduce((a, b) => Math.max(a, b), filteredValues[0]);

            // Weak preset should stay responsive, but not be overly tight.
            // Keep this only slightly more relaxed than the original behavior.
            const weakPaddingDb = 1.5;
            minDb = Math.floor(minDb - weakPaddingDb);
            maxDb = Math.ceil(maxDb + weakPaddingDb);

            const weakMinSpanDb = 10;
            const weakSpan = maxDb - minDb;
            if (weakSpan < weakMinSpanDb) {
                const mid = (maxDb + minDb) / 2;
                minDb = Math.floor(mid - weakMinSpanDb / 2);
                maxDb = Math.ceil(mid + weakMinSpanDb / 2);
            }
            break;
        }
    }

    // Calculate some statistics for debugging
    const mean = allValues.reduce((sum, val) => sum + val, 0) / allValues.length;
    const median = sortedValues[Math.floor(sortedValues.length / 2)];

    return {
        dbRange: [minDb, maxDb],
        stats: {
            mean: mean.toFixed(2),
            median: median.toFixed(2),
            min: sortedValues[0].toFixed(2),
            max: sortedValues[sortedValues.length - 1].toFixed(2),
            rangeMin: minDb.toFixed(2),
            rangeMax: maxDb.toFixed(2),
            rangeSpan: (maxDb - minDb).toFixed(2),
            samples: allValues.length,
            preset
        }
    };
}
