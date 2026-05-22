/**
 * Audio service for managing audio buffer flushing
 * This module provides a way for non-React code (like middleware) to trigger audio buffer flushes
 * Supports per-VFO flushing for multi-VFO audio streaming
 */

let flushCallback = null;

/**
 * Register the flush callback from the AudioProvider
 * @param {Function} callback - The flush function from AudioProvider (accepts optional vfoNumber parameter)
 */
export const registerFlushCallback = (callback) => {
    flushCallback = callback;
};

/**
 * Unregister the flush callback
 */
export const unregisterFlushCallback = () => {
    flushCallback = null;
};

/**
 * Flush audio buffers (to be called from middleware or other non-React code)
 * @param {number|null} vfoNumber - Optional VFO number (0-3). If null, flushes all VFOs.
 */
export const flushAudioBuffers = (vfoNumber = null) => {
    if (flushCallback) {
        flushCallback(vfoNumber);
    }
};
