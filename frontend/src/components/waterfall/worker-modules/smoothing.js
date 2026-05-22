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
 * FFT smoothing algorithms
 */

/**
 * Update smoothed FFT data using the specified algorithm
 * @param {Array<number>} newFftData - New FFT data
 * @param {Array<Array<number>>} fftHistory - History of FFT data
 * @param {Array<number>} smoothedFftData - Current smoothed data (will be modified)
 * @param {string} smoothingType - 'simple', 'weighted', or 'exponential'
 * @param {number} smoothingStrength - Strength for exponential smoothing (0-1)
 * @param {number} maxFftHistoryLength - Maximum history length
 * @returns {Object} Updated history and smoothed data
 */
export function updateSmoothedFftData(
    newFftData,
    fftHistory,
    smoothedFftData,
    smoothingType,
    smoothingStrength,
    maxFftHistoryLength
) {
    // Check if smoothedFftData needs to be resized
    if (smoothedFftData.length !== newFftData.length) {
        console.log(`Resizing smoothed FFT data from ${smoothedFftData.length} to ${newFftData.length}`);
        smoothedFftData = new Array(newFftData.length).fill(-120);
        fftHistory = []; // Clear history when size changes
    }

    // Add new FFT data to history
    fftHistory.push([...newFftData]);

    // Keep only the last N frames
    if (fftHistory.length > maxFftHistoryLength) {
        fftHistory.shift();
    }

    // Apply different smoothing algorithms
    switch (smoothingType) {
        case 'simple':
            smoothedFftData = simpleMovingAverage(fftHistory, newFftData.length);
            break;

        case 'weighted':
            smoothedFftData = weightedMovingAverage(fftHistory, newFftData.length);
            break;

        case 'exponential':
            smoothedFftData = exponentialMovingAverage(
                fftHistory,
                newFftData,
                smoothedFftData,
                smoothingStrength
            );
            break;

        default:
            smoothedFftData = simpleMovingAverage(fftHistory, newFftData.length);
    }

    return { fftHistory, smoothedFftData };
}

/**
 * Simple moving average
 * @param {Array<Array<number>>} fftHistory - History of FFT data
 * @param {number} dataLength - Length of FFT data
 * @returns {Array<number>} Smoothed data
 */
function simpleMovingAverage(fftHistory, dataLength) {
    const result = new Array(dataLength);
    for (let i = 0; i < dataLength; i++) {
        let sum = 0;
        for (let j = 0; j < fftHistory.length; j++) {
            sum += fftHistory[j][i];
        }
        result[i] = sum / fftHistory.length;
    }
    return result;
}

/**
 * Weighted moving average - recent frames have more influence
 * @param {Array<Array<number>>} fftHistory - History of FFT data
 * @param {number} dataLength - Length of FFT data
 * @returns {Array<number>} Smoothed data
 */
function weightedMovingAverage(fftHistory, dataLength) {
    const result = new Array(dataLength);
    for (let i = 0; i < dataLength; i++) {
        let weightedSum = 0;
        let totalWeight = 0;

        for (let j = 0; j < fftHistory.length; j++) {
            // More recent frames get higher weight
            const weight = j + 1; // weights: 1, 2, 3, 4, 5...
            weightedSum += fftHistory[j][i] * weight;
            totalWeight += weight;
        }
        result[i] = weightedSum / totalWeight;
    }
    return result;
}

/**
 * Exponential moving average - only needs current and previous
 * @param {Array<Array<number>>} fftHistory - History of FFT data
 * @param {Array<number>} newFftData - New FFT data
 * @param {Array<number>} smoothedFftData - Previous smoothed data
 * @param {number} smoothingStrength - Smoothing strength (0-1, higher = more smoothing)
 * @returns {Array<number>} Smoothed data
 */
function exponentialMovingAverage(fftHistory, newFftData, smoothedFftData, smoothingStrength) {
    if (fftHistory.length === 1) {
        // First frame, just copy
        return [...newFftData];
    } else {
        const result = new Array(newFftData.length);
        for (let i = 0; i < newFftData.length; i++) {
            // EMA formula: new_value = alpha * current + (1 - alpha) * previous
            const alpha = 1 - smoothingStrength; // Convert to alpha (lower strength = higher alpha = less smoothing)
            result[i] = alpha * newFftData[i] + smoothingStrength * smoothedFftData[i];
        }
        return result;
    }
}
