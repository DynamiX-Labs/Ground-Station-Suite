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
 * Rendering functions for bandscope, dB axis, and waterfall left margin
 */

import { getColorForPower } from './color-maps.js';

const timeFormatterCache = new Map();

function getTimeFormatter(timezone) {
    const key = timezone || '__local__';
    if (!timeFormatterCache.has(key)) {
        timeFormatterCache.set(
            key,
            new Intl.DateTimeFormat('en-GB', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false,
                ...(timezone ? { timeZone: timezone } : {})
            })
        );
    }
    return timeFormatterCache.get(key);
}

function formatClockTime(date, timezone) {
    try {
        return getTimeFormatter(timezone).format(date);
    } catch {
        // Fallback for invalid/unsupported timezone values.
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }
}

/**
 * Draw bandscope (FFT line display)
 * @param {Object} params - Parameters object
 * @param {CanvasRenderingContext2D} params.bandscopeCtx - Bandscope canvas context
 * @param {OffscreenCanvas} params.bandscopeCanvas - Bandscope canvas
 * @param {Array<number>} params.fftData - FFT data to display
 * @param {Array<number>} params.smoothedFftData - Smoothed FFT data
 * @param {Array<number>} params.dbRange - [minDb, maxDb]
 * @param {string} params.colorMap - Color map name
 * @param {Object} params.theme - Theme colors
 * @param {CanvasRenderingContext2D} params.dBAxisCtx - dB axis canvas context
 * @param {OffscreenCanvas} params.dBAxisCanvas - dB axis canvas
 * @param {number} [params.zoomScale=1] - Current horizontal zoom scale
 */
export function drawBandscope({
    bandscopeCtx,
    bandscopeCanvas,
    fftData,
    smoothedFftData,
    dbRange,
    colorMap,
    theme,
    dBAxisCtx,
    dBAxisCanvas,
    zoomScale = 1
}) {
    if (!bandscopeCanvas || fftData.length === 0) {
        return;
    }

    const width = bandscopeCanvas.width;
    const height = bandscopeCanvas.height;

    // Clear the canvas
    bandscopeCtx.fillStyle = theme.palette.background.default;
    bandscopeCtx.fillRect(0, 0, width, height);

    const [minDb, maxDb] = dbRange;
    const dbRangeDiff = maxDb - minDb;

    // Visual-only viewport pan: move trace lower in canvas by 20px.
    // This shifts display position only and does not alter dB values.
    const linePanPx = 20;

    // Draw dB marks and labels using the current range
    bandscopeCtx.fillStyle = 'white';
    bandscopeCtx.font = '12px Monospace';
    bandscopeCtx.textAlign = 'right';

    // Calculate step size based on range
    const steps = Math.min(6, dbRangeDiff); // Maximum 10 steps
    const stepSize = Math.ceil(dbRangeDiff / steps);

    for (let db = Math.ceil(minDb / stepSize) * stepSize; db <= maxDb; db += stepSize) {
        const y = height - ((db - minDb) / (maxDb - minDb)) * height;

        // Draw a horizontal dotted grid line with 1px thickness
        bandscopeCtx.strokeStyle = 'rgba(150, 150, 150, 0.4)';
        bandscopeCtx.lineWidth = 1;
        bandscopeCtx.setLineDash([5, 5]);
        bandscopeCtx.beginPath();
        bandscopeCtx.moveTo(0, y);
        bandscopeCtx.lineTo(width, y);
        bandscopeCtx.stroke();
        bandscopeCtx.setLineDash([]);
    }

    // Draw the dB axis (y-axis) with the true dB range.
    drawDbAxis({
        dBAxisCtx,
        dBAxisCanvas,
        width,
        height,
        topPadding: 0,
        dbRange,
        theme
    });

    // Draw the FFT data with a visual-only pan.
    drawFftLine({
        ctx: bandscopeCtx,
        fftData: smoothedFftData,
        width,
        height,
        dbRange,
        colorMap,
        zoomScale,
        linePanPx
    });
}

/**
 * Draw dB axis scale
 * @param {Object} params - Parameters object
 * @param {CanvasRenderingContext2D} params.dBAxisCtx - dB axis canvas context
 * @param {OffscreenCanvas} params.dBAxisCanvas - dB axis canvas
 * @param {number} params.width - Canvas width
 * @param {number} params.height - Canvas height (actual drawing area, excluding top padding)
 * @param {number} params.topPadding - Top padding offset
 * @param {Array<number>} params.dbRange - [minDb, maxDb]
 * @param {Object} params.theme - Theme colors
 */
export function drawDbAxis({
    dBAxisCtx,
    dBAxisCanvas,
    width,
    height,
    topPadding = 0,
    dbRange,
    theme
}) {
    const [minDb, maxDb] = dbRange;

    // Draw background for the entire canvas including top padding
    dBAxisCtx.fillStyle = theme.palette.background.elevated;
    dBAxisCtx.fillRect(0, 0, dBAxisCanvas.width, dBAxisCanvas.height);

    // Draw dB marks and labels (offset by topPadding)
    dBAxisCtx.fillStyle = theme.palette.text.primary;
    dBAxisCtx.font = '12px Monospace';
    dBAxisCtx.textAlign = 'right';

    // Calculate step size based on range
    const dbRangeValue = maxDb - minDb;
    const steps = Math.min(6, dbRangeValue); // Maximum 10 steps
    const stepSize = Math.ceil(dbRangeValue / steps);

    for (let db = Math.ceil(minDb / stepSize) * stepSize; db <= maxDb; db += stepSize) {
        const y = topPadding + height - ((db - minDb) / (maxDb - minDb)) * height;

        // Draw a horizontal dotted grid line (matches old behavior exactly)
        dBAxisCtx.strokeStyle = theme.palette.overlay.light;
        dBAxisCtx.setLineDash([2, 2]);
        dBAxisCtx.beginPath();
        dBAxisCtx.moveTo(dBAxisCanvas.width, y);
        dBAxisCtx.lineTo(width, y);
        dBAxisCtx.stroke();
        dBAxisCtx.setLineDash([]);

        // Draw label
        dBAxisCtx.fillText(`${db} dB`, dBAxisCanvas.width - 5, y + 3);
    }
}

/**
 * Efficiently downsample FFT data using averaging for smooth visualization
 * @param {Array<number>} fftData - Full FFT data
 * @param {number} targetPoints - Target number of points
 * @returns {Array<{x: number, y: number}>} Downsampled points with x as fraction [0,1] and y as amplitude
 */
function downsampleFftData(fftData, targetPoints) {
    const dataLength = fftData.length;

    // If we have fewer or equal points than target, return all points
    if (dataLength <= targetPoints) {
        return fftData.map((amplitude, i) => ({
            x: i / (dataLength - 1),
            y: amplitude
        }));
    }

    // Calculate how many input samples per output point
    const binSize = dataLength / targetPoints;
    const result = [];

    // Use averaging with peak weighting for smooth but accurate representation
    for (let i = 0; i < targetPoints; i++) {
        const startIdx = Math.floor(i * binSize);
        const endIdx = Math.floor((i + 1) * binSize);

        let sum = 0;
        let max = -Infinity;
        let count = 0;

        // Calculate average and find peak in this bin
        for (let j = startIdx; j < endIdx && j < dataLength; j++) {
            const val = fftData[j];
            sum += val;
            count++;
            if (val > max) {
                max = val;
            }
        }

        // Weighted average: 70% average + 30% peak (preserves some peaks while smoothing)
        const avg = sum / count;
        const weightedValue = avg * 0.7 + max * 0.3;

        // Use the center of the bin for x position
        const centerIdx = (startIdx + endIdx) / 2;
        result.push({
            x: centerIdx / (dataLength - 1),
            y: weightedValue
        });
    }

    return result;
}

/**
 * Draw FFT line on bandscope
 * @param {Object} params - Parameters object
 * @param {CanvasRenderingContext2D} params.ctx - Canvas context
 * @param {Array<number>} params.fftData - FFT data
 * @param {number} params.width - Canvas width
 * @param {number} params.height - Canvas height
 * @param {Array<number>} params.dbRange - [minDb, maxDb]
 * @param {string} params.colorMap - Color map name
 * @param {number} [params.zoomScale=1] - Current horizontal zoom scale
 * @param {number} [params.linePanPx=0] - Visual-only pan offset in pixels
 */
export function drawFftLine({
    ctx,
    fftData,
    width,
    height,
    dbRange,
    colorMap,
    zoomScale = 1,
    linePanPx = 0
}) {
    const [minDb, maxDb] = dbRange;
    const graphWidth = width;
    const mapAmplitudeToY = (amplitude) => {
        const normalizedValue = Math.max(0, Math.min(1, (amplitude - minDb) / (maxDb - minDb)));

        // Keep the visual pan while preserving full vertical reach:
        // normalized=1 can still reach y=0 (top), normalized=0 remains near bottom.
        const y = height - (normalizedValue * (height + linePanPx)) + linePanPx;
        return Math.min(height, Math.max(0, y));
    };

    // Adaptive target points: use width for small FFTs, cap at reasonable limit for large FFTs
    // This prevents excessive point generation while maintaining visual quality
    const basePoints = Math.min(graphWidth, Math.max(1024, fftData.length / 24));

    // Progressive detail tiers by zoom to improve high-zoom readability
    // while keeping CPU predictable and allocations bounded.
    let zoomTierMultiplier = 0.75;
    if (zoomScale >= 12) {
        zoomTierMultiplier = 8;
    } else if (zoomScale >= 10) {
        zoomTierMultiplier = 6;
    } else if (zoomScale >= 6) {
        zoomTierMultiplier = 3;
    } else if (zoomScale >= 3) {
        zoomTierMultiplier = 2;
    } else if (zoomScale >= 1.5) {
        zoomTierMultiplier = 1.25;
    }

    const hardPointCap = 4096;
    const targetPoints = Math.max(
        128,
        Math.min(fftData.length, hardPointCap, Math.floor(basePoints * zoomTierMultiplier))
    );

    // Downsample the FFT data efficiently
    const downsampledPoints = downsampleFftData(fftData, targetPoints);

    // Generate line color based on a "hot" point in the colormap (e.g., 80% intensity)
    // This gives a color that's representative of the colormap
    const lineColorPoint = 0.8; // Use 80% intensity for the line
    const lineRgb = getColorForPower(
        minDb + (maxDb - minDb) * lineColorPoint,
        colorMap,
        [minDb, maxDb],
    );

    // Create line color with proper opacity
    const lineColor = `rgba(${lineRgb.r}, ${lineRgb.g}, ${lineRgb.b}, 0.8)`;

    // Generate fill color based on the same colormap but with lower intensity
    const fillColorPoint = 0.7; // Use 50% intensity for fill base color
    const fillRgb = getColorForPower(
        minDb + (maxDb - minDb) * fillColorPoint,
        colorMap,
        [minDb, maxDb],
    );

    // Create fill color with low opacity
    const fillColor = `rgba(${fillRgb.r}, ${fillRgb.g}, ${fillRgb.b}, 0.3)`;

    // Set line style with generated color
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.beginPath();

    // Draw the line path using downsampled points with quadratic curves for smoothness
    for (let i = 0; i < downsampledPoints.length; i++) {
        const point = downsampledPoints[i];
        const x = point.x * graphWidth;
        const y = mapAmplitudeToY(point.y);

        if (i === 0) {
            ctx.moveTo(x, y);
        } else if (i === 1) {
            ctx.lineTo(x, y);
        } else {
            // Use quadratic curve for smooth interpolation between points
            const prevPoint = downsampledPoints[i - 1];
            const prevX = prevPoint.x * graphWidth;
            const prevY = mapAmplitudeToY(prevPoint.y);

            // Control point is midway between previous and current point
            const cpX = (prevX + x) / 2;
            const cpY = (prevY + y) / 2;

            ctx.quadraticCurveTo(prevX, prevY, cpX, cpY);
        }
    }

    // Final segment to last point
    if (downsampledPoints.length > 2) {
        const lastPoint = downsampledPoints[downsampledPoints.length - 1];
        const x = lastPoint.x * graphWidth;
        const y = mapAmplitudeToY(lastPoint.y);
        ctx.lineTo(x, y);
    }

    // Draw the line
    ctx.stroke();

    // Add fill below the line using the generated fill color
    ctx.fillStyle = fillColor;
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.fill();
}

/**
 * Update waterfall left margin with timestamps and rotator events
 * @param {Object} params - Parameters object
 * @param {CanvasRenderingContext2D} params.waterFallLeftMarginCtx - Left margin canvas context
 * @param {OffscreenCanvas} params.waterfallLeftMarginCanvas - Left margin canvas
 * @param {OffscreenCanvas} params.waterfallCanvas - Main waterfall canvas
 * @param {CanvasRenderingContext2D} params.waterfallCtx - Main waterfall canvas context
 * @param {Array<string>} params.rotatorEventQueue - Queue of rotator events
 * @param {boolean} params.showRotatorDottedLines - Whether to show dotted lines
 * @param {Object} params.theme - Theme colors
 * @param {string} [params.timezone='UTC'] - IANA timezone used for timestamp labels
 * @param {Object} params.lastTimestamp - Last timestamp reference (mutable)
 * @param {Object} params.dottedLineImageData - Cached dotted line image data (mutable)
 * @param {Date|null} params.recordingDatetime - Recording datetime for playback mode (null for live)
 * @returns {Object} Updated state { lastTimestamp, dottedLineImageData }
 */
export function updateWaterfallLeftMargin({
    waterFallLeftMarginCtx,
    waterfallLeftMarginCanvas,
    waterfallCanvas,
    waterfallCtx,
    rotatorEventQueue,
    showRotatorDottedLines,
    theme,
    timezone = 'UTC',
    lastTimestamp,
    dottedLineImageData,
    recordingDatetime = null
}) {
    // This part should run on EVERY frame, not just when minutes change
    // Move existing pixels DOWN by 1 pixel
    waterFallLeftMarginCtx.drawImage(
        waterfallLeftMarginCanvas,
        0, 0,
        waterfallLeftMarginCanvas.width, waterfallLeftMarginCanvas.height - 1,
        0, 1,
        waterfallLeftMarginCanvas.width, waterfallLeftMarginCanvas.height - 1
    );

    // Fill the top row with the background color
    waterFallLeftMarginCtx.fillStyle = theme.palette.background.paper;
    waterFallLeftMarginCtx.fillRect(0, 0, waterfallLeftMarginCanvas.width, 1);

    // Process last rotator events, if there are any then print a line
    const newRotatorEvent = rotatorEventQueue.pop();
    const hasRotatorEvent = !!newRotatorEvent;

    if (hasRotatorEvent) {
        // Set font properties first to measure text
        waterFallLeftMarginCtx.font = '12px monospace';
        waterFallLeftMarginCtx.textAlign = 'center';
        waterFallLeftMarginCtx.textBaseline = 'top';

        // Measure text to get precise dimensions
        const textMetrics = waterFallLeftMarginCtx.measureText(newRotatorEvent);
        const textWidth = textMetrics.width;
        const textHeight = 12; // Match the actual font size
        const centerX = waterfallLeftMarginCanvas.width / 2;
        const textX = centerX - (textWidth / 2);

        // Only clear the specific rectangle where the text will be drawn
        waterFallLeftMarginCtx.clearRect(textX - 1, 0, textWidth + 2, textHeight);

        // Fill with background color
        waterFallLeftMarginCtx.fillStyle = theme.palette.background.paper;
        waterFallLeftMarginCtx.fillRect(textX - 1, 0, textWidth + 2, textHeight);

        // Draw the time text at y=0
        waterFallLeftMarginCtx.fillStyle = theme.palette.text.primary;
        waterFallLeftMarginCtx.fillText(newRotatorEvent, centerX, 0);

        // Draw dotted line only when a target waterfall canvas/context is available.
        // In headless left-margin updates we skip this overlay and keep timestamp continuity.
        if (showRotatorDottedLines && waterfallCanvas && waterfallCtx) {
            // Get or create the imageData for the dotted line
            let imageData;

            // Check if we have a cached imageData for the dotted line
            if (!dottedLineImageData || dottedLineImageData.width !== waterfallCanvas.width) {
                // Create new ImageData if none exists or if width changed
                imageData = waterfallCtx.createImageData(waterfallCanvas.width, 1);
                dottedLineImageData = imageData;

                // Pre-fill the dotted line pattern
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 32) { // Increase step to create dots
                    for (let j = 0; j < 4; j++) { // Dot width of 1 pixel
                        const idx = i + (j * 4);
                        if (idx < data.length) {
                            data[idx] = 255;     // R
                            data[idx + 1] = 255; // G
                            data[idx + 2] = 255; // B
                            data[idx + 3] = 100; // A
                        }
                    }
                }
            } else {
                // Reuse the cached imageData
                imageData = dottedLineImageData;
            }

            // Draw the dotted line
            waterfallCtx.putImageData(imageData, 0, 0);
        }
    }

    // Use recording datetime if available (playback mode), otherwise use current time (live mode)
    const now = recordingDatetime || new Date();
    const currentSeconds = Math.floor(now.getTime() / 1000);

    // Update once per 15-second bucket to avoid missing draws if exact second boundaries are skipped.
    const lastSeconds = lastTimestamp ? Math.floor(lastTimestamp.getTime() / 1000) : -1;
    const currentQuarterMinute = Math.floor(currentSeconds / 15);
    const lastQuarterMinute = lastTimestamp ? Math.floor(lastSeconds / 15) : -1;
    const shouldUpdate = !lastTimestamp || currentQuarterMinute !== lastQuarterMinute;

    // Update the timestamp every 15 seconds (but not if we just drew a rotator event)
    if (shouldUpdate && !hasRotatorEvent) {
        const timeString = formatClockTime(now, timezone);

        // Set font properties first to measure text
        waterFallLeftMarginCtx.font = '12px monospace';
        waterFallLeftMarginCtx.textAlign = 'center';
        waterFallLeftMarginCtx.textBaseline = 'top';

        // Measure text to get precise dimensions
        const textMetrics = waterFallLeftMarginCtx.measureText(timeString);
        const textWidth = textMetrics.width;
        const textHeight = 12; // Match the actual font size
        const centerX = waterfallLeftMarginCanvas.width / 2;
        const textX = centerX - (textWidth / 2);

        // Only clear the specific rectangle where the text will be drawn
        waterFallLeftMarginCtx.clearRect(textX - 1, 0, textWidth + 2, textHeight);

        // Fill with background color
        waterFallLeftMarginCtx.fillStyle = theme.palette.background.paper;
        waterFallLeftMarginCtx.fillRect(textX - 1, 0, textWidth + 2, textHeight);

        // Draw the time text at y=0
        waterFallLeftMarginCtx.fillStyle = theme.palette.text.primary;
        waterFallLeftMarginCtx.fillText(timeString, centerX, 0);

        // Update the last timestamp reference
        lastTimestamp = now;
    }

    // Return updated mutable state
    return {
        lastTimestamp,
        dottedLineImageData
    };
}
