/**
 * Bandscope smoothing presets shared between worker and DOM render paths.
 */

const PRESETS = {
    off: {
        historyLength: 1,
        smoothingType: 'simple',
        smoothingStrength: 0,
    },
    low: {
        historyLength: 3,
        smoothingType: 'weighted',
        smoothingStrength: 0.6,
    },
    medium: {
        historyLength: 5,
        smoothingType: 'weighted',
        smoothingStrength: 0.9,
    },
    high: {
        historyLength: 8,
        smoothingType: 'exponential',
        smoothingStrength: 0.95,
    },
};

export function getSmoothingConfig(preset) {
    return PRESETS[preset] || PRESETS.medium;
}

