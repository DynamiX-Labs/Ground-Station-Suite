export const BOOKMARK_SOURCE_KEYS = ['manual', 'satnogs', 'gr-satellites', 'satdump'];

export const normalizeBookmarkSource = (source) => {
    if (typeof source !== 'string') {
        return 'unknown';
    }
    const lowered = source.toLowerCase();
    if (BOOKMARK_SOURCE_KEYS.includes(lowered)) {
        return lowered;
    }
    return 'unknown';
};

export const getBookmarkSourceStyle = (source, theme) => {
    const normalized = normalizeBookmarkSource(source);

    if (normalized === 'manual') {
        return {
            key: normalized,
            badge: 'M',
            accent: theme.palette.primary.light,
            lineDash: [],
            strokeWidth: 1.0,
        };
    }

    if (normalized === 'satnogs') {
        return {
            key: normalized,
            badge: 'SN',
            accent: theme.palette.success.main,
            lineDash: [4, 2],
            strokeWidth: 1.0,
        };
    }

    if (normalized === 'gr-satellites') {
        return {
            key: normalized,
            badge: 'GR',
            accent: theme.palette.warning.main,
            lineDash: [2, 2],
            strokeWidth: 1.0,
        };
    }

    if (normalized === 'satdump') {
        return {
            key: normalized,
            badge: 'SD',
            accent: theme.palette.secondary.main,
            lineDash: [6, 2],
            strokeWidth: 1.2,
        };
    }

    return {
        key: 'unknown',
        badge: '?',
        accent: theme.palette.text.secondary,
        lineDash: [1.5, 2],
        strokeWidth: 1.0,
    };
};
