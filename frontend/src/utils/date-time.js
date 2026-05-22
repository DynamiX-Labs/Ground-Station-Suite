export const normalizeDateInput = (dateInput) => {
    if (!dateInput) return null;
    const dateObj = dateInput instanceof Date ? dateInput : new Date(dateInput);
    if (Number.isNaN(dateObj.getTime())) return null;
    return dateObj;
};

export const formatDateTime = (dateInput, { timezone, locale, options } = {}) => {
    const dateObj = normalizeDateInput(dateInput);
    if (!dateObj) return '';

    const formatOptions = { ...options };
    if (timezone) {
        formatOptions.timeZone = timezone;
    }

    return dateObj.toLocaleString(locale, formatOptions);
};

export const formatDate = (dateInput, { timezone, locale, options } = {}) => {
    const dateObj = normalizeDateInput(dateInput);
    if (!dateObj) return '';

    const formatOptions = { ...options };
    if (timezone) {
        formatOptions.timeZone = timezone;
    }

    return dateObj.toLocaleDateString(locale, formatOptions);
};

export const formatTime = (dateInput, { timezone, locale, options } = {}) => {
    const dateObj = normalizeDateInput(dateInput);
    if (!dateObj) return '';

    const formatOptions = { ...options };
    if (timezone) {
        formatOptions.timeZone = timezone;
    }

    return dateObj.toLocaleTimeString(locale, formatOptions);
};
