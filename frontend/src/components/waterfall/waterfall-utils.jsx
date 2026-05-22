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
 * Utility functions for waterfall component
 */

/**
 * Generate a sanitized snapshot filename
 * @param {string} targetSatelliteName - Name of the target satellite
 * @param {number} centerFrequency - Center frequency in Hz
 * @returns {string} Sanitized snapshot name
 */
export const generateSnapshotName = (targetSatelliteName, centerFrequency) => {
    // Helper to sanitize filename
    const sanitizeFilename = (name) => {
        return name.replace(/[^a-zA-Z0-9\-_]/g, '_').replace(/_+/g, '_');
    };

    // Helper to format frequency
    const formatFrequencyShort = (freqHz) => {
        const freqMHz = freqHz / 1e6;
        return `${freqMHz.toFixed(3).replace('.', '_')}MHz`;
    };

    const satName = sanitizeFilename(targetSatelliteName || 'unknown');
    const freqShort = formatFrequencyShort(centerFrequency);

    // Backend will append timestamp, so we just return the base name
    return `${satName}-${freqShort}`;
};

/**
 * Toggle fullscreen mode on an element
 * @param {HTMLElement} element - The element to toggle fullscreen on
 * @param {Function} setIsFullscreen - State setter for fullscreen status
 */
export const toggleFullscreen = (element, setIsFullscreen) => {
    if (!document.fullscreenElement) {
        // Enter fullscreen
        if (element.requestFullscreen) {
            element.requestFullscreen();
        } else if (element.mozRequestFullScreen) { /* Firefox */
            element.mozRequestFullScreen();
        } else if (element.webkitRequestFullscreen) { /* Chrome, Safari & Opera */
            element.webkitRequestFullscreen();
        } else if (element.msRequestFullscreen) { /* IE/Edge */
            element.msRequestFullscreen();
        }
        setIsFullscreen(true);
    } else {
        // Exit fullscreen
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.mozCancelFullScreen) { /* Firefox */
            document.mozCancelFullScreen();
        } else if (document.webkitExitFullscreen) { /* Chrome, Safari & Opera */
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) { /* IE/Edge */
            document.msExitFullscreen();
        }
        setIsFullscreen(false);
    }
};

/**
 * Setup fullscreen change event listeners
 * @param {Function} callback - Callback to invoke on fullscreen change
 * @returns {Function} Cleanup function to remove event listeners
 */
export const setupFullscreenListeners = (callback) => {
    const handleFullscreenChange = () => {
        callback(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    return () => {
        document.removeEventListener('fullscreenchange', handleFullscreenChange);
        document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
        document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
        document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    };
};

/**
 * Initialize worker with canvas transfer
 * @param {Object} params - Initialization parameters
 * @returns {Worker|null} The initialized worker or null on error
 */
export const initializeWorkerWithCanvases = ({
    waterFallCanvasRef,
    bandscopeCanvasRef,
    dBAxisScopeCanvasRef,
    waterFallLeftMarginCanvasRef,
    waterFallCanvasWidth,
    waterFallCanvasHeight,
    colorMap,
    dbRange,
    fftSize,
    showRotatorDottedLines,
    timezone,
    theme,
    workerRef,
    canvasTransferredRef,
    createWorker,
    onMessage
}) => {
    if (!waterFallCanvasRef.current || canvasTransferredRef.current) {
        return null;
    }

    try {
        // Create the offscreen canvases
        const waterfallOffscreenCanvas = waterFallCanvasRef.current.transferControlToOffscreen();
        const bandscopeOffscreenCanvas = bandscopeCanvasRef.current.transferControlToOffscreen();
        const dBAxisOffScreenCanvas = dBAxisScopeCanvasRef.current.transferControlToOffscreen();
        const waterfallLeftMarginCanvas = waterFallLeftMarginCanvasRef.current.transferControlToOffscreen();
        canvasTransferredRef.current = true;

        // Initialize the worker if it doesn't exist
        if (!workerRef.current) {
            workerRef.current = createWorker();

            // Set up message handling from the worker
            workerRef.current.onmessage = onMessage;
        } else {
            console.info('Waterfall worker already exists');
        }

        // Transfer the canvases to the worker
        workerRef.current.postMessage({
            cmd: 'initCanvas',
            waterfallCanvas: waterfallOffscreenCanvas,
            bandscopeCanvas: bandscopeOffscreenCanvas,
            dBAxisCanvas: dBAxisOffScreenCanvas,
            waterfallLeftMarginCanvas: waterfallLeftMarginCanvas,
            config: {
                width: waterFallCanvasWidth,
                height: waterFallCanvasHeight,
                colorMap: colorMap,
                dbRange: dbRange,
                fftSize: fftSize,
                showRotatorDottedLines: showRotatorDottedLines,
                timezone: timezone,
                theme: {
                    palette: {
                        background: {
                            default: theme.palette.background.default,
                            paper: theme.palette.background.paper,
                            elevated: theme.palette.background.elevated,
                        },
                        border: {
                            main: theme.palette.border.main,
                            light: theme.palette.border.light,
                            dark: theme.palette.border.dark,
                        },
                        overlay: {
                            light: theme.palette.overlay.light,
                            medium: theme.palette.overlay.medium,
                            dark: theme.palette.overlay.dark,
                        },
                        text: {
                            primary: theme.palette.text.primary,
                            secondary: theme.palette.text.secondary,
                        }
                    }
                }
            }
        }, [waterfallOffscreenCanvas, bandscopeOffscreenCanvas, dBAxisOffScreenCanvas, waterfallLeftMarginCanvas]);

        console.log('Canvases successfully transferred');
        return workerRef.current;

    } catch (error) {
        console.error('Canvases transfer failed:', error);
        // Reset the flag if transfer failed
        canvasTransferredRef.current = false;
        return null;
    }
};

/**
 * Setup canvas capture event listener
 * @param {Object} workerRef - Reference to the worker
 * @returns {Function} Cleanup function to remove event listener
 */
export const setupCanvasCaptureListener = (workerRef) => {
    const handleCaptureCanvas = () => {
        if (workerRef.current) {
            // Request canvas capture from worker
            workerRef.current.postMessage({
                cmd: 'captureWaterfallCanvas'
            });
        } else {
            console.error('Worker ref is not available');
        }
    };

    window.addEventListener('capture-waterfall-canvas', handleCaptureCanvas);

    return () => {
        window.removeEventListener('capture-waterfall-canvas', handleCaptureCanvas);
    };
};

/**
 * Paint the waterfall left margin filler canvas with background color
 * @param {HTMLCanvasElement} canvas - The canvas element
 * @param {string} backgroundColor - The background color
 */
export const paintLeftMarginFiller = (canvas, backgroundColor) => {
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = backgroundColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
};
