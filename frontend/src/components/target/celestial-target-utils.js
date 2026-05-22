const MAX_TARGET_PASS_HOURS = 24;

export const normalizeTargetType = (trackingState = {}) => {
    const explicitType = String(trackingState?.target_type || '').trim().toLowerCase();
    if (explicitType === 'satellite' || explicitType === 'mission' || explicitType === 'body') {
        return explicitType;
    }
    if (String(trackingState?.command || '').trim()) return 'mission';
    if (String(trackingState?.body_id || '').trim()) return 'body';
    return 'satellite';
};

const normalizeText = (value) => String(value ?? '').trim();

const normalizeBodyId = (value) => normalizeText(value).toLowerCase();

const formatBodyNameFromId = (bodyId) => {
    const normalizedBodyId = normalizeBodyId(bodyId);
    if (!normalizedBodyId) return '';
    return normalizedBodyId
        .split(/[_\s-]+/)
        .filter(Boolean)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
};

const buildTargetKey = ({ targetType, command, bodyId }) => {
    if (targetType === 'mission') {
        return command ? `mission:${command}` : '';
    }
    if (targetType === 'body') {
        return bodyId ? `body:${bodyId}` : '';
    }
    return '';
};

const isIdentifierOnlyName = ({ name, targetType, command, bodyId }) => {
    const normalizedName = normalizeText(name).toLowerCase();
    if (!normalizedName) return true;
    if (targetType === 'mission') {
        const normalizedCommand = normalizeText(command).toLowerCase();
        return Boolean(normalizedCommand) && normalizedName === normalizedCommand;
    }
    if (targetType === 'body') {
        const normalizedBodyId = normalizeBodyId(bodyId);
        return Boolean(normalizedBodyId) && normalizedName === normalizedBodyId;
    }
    return false;
};

const resolveNameFromRows = ({ rows = [], targetType, command, bodyId, targetKey }) => {
    const normalizedRows = Array.isArray(rows) ? rows : [];
    const normalizedKey = normalizeText(targetKey);
    const normalizedCommand = normalizeText(command).toLowerCase();
    const normalizedBodyId = normalizeBodyId(bodyId);

    const keyMatch = normalizedRows.find((row) => normalizeText(row?.target_key || row?.targetKey) === normalizedKey);
    if (keyMatch) {
        const keyName = normalizeText(keyMatch?.name || keyMatch?.displayName || keyMatch?.display_name || keyMatch?.target_name);
        if (keyName) return keyName;
    }

    if (targetType === 'mission' && normalizedCommand) {
        const missionMatch = normalizedRows.find(
            (row) => normalizeText(row?.command).toLowerCase() === normalizedCommand
        );
        const missionName = normalizeText(
            missionMatch?.name || missionMatch?.displayName || missionMatch?.display_name || missionMatch?.target_name
        );
        if (missionName) return missionName;
    }

    if (targetType === 'body' && normalizedBodyId) {
        const bodyMatch = normalizedRows.find((row) => {
            const rowBodyId = normalizeBodyId(row?.body_id || row?.bodyId || row?.command);
            return rowBodyId === normalizedBodyId;
        });
        const bodyName = normalizeText(
            bodyMatch?.name || bodyMatch?.displayName || bodyMatch?.display_name || bodyMatch?.target_name
        );
        if (bodyName) return bodyName;
    }

    return '';
};

export const resolveTargetIdentifier = (trackingState = {}) => {
    const targetType = normalizeTargetType(trackingState);
    if (targetType === 'mission') return normalizeText(trackingState?.command);
    if (targetType === 'body') return normalizeBodyId(trackingState?.body_id);
    return normalizeText(trackingState?.norad_id);
};

export const resolveTargetDisplayName = ({
    trackingState = {},
    satelliteDetails = {},
    monitoredRows = [],
    celestialRows = [],
} = {}) => {
    const targetType = normalizeTargetType(trackingState);
    const command = normalizeText(trackingState?.command);
    const bodyId = normalizeBodyId(trackingState?.body_id);
    const targetKey = buildTargetKey({ targetType, command, bodyId });

    const candidates = [
        normalizeText(trackingState?.target_name),
        normalizeText(satelliteDetails?.name),
        resolveNameFromRows({ rows: celestialRows, targetType, command, bodyId, targetKey }),
        resolveNameFromRows({ rows: monitoredRows, targetType, command, bodyId, targetKey }),
    ].filter(Boolean);

    const preferredName = candidates.find(
        (name) => !isIdentifierOnlyName({ name, targetType, command, bodyId })
    );
    if (preferredName) return preferredName;

    if (candidates.length > 0) return candidates[0];

    if (targetType === 'mission') return command ? `Mission ${command}` : 'Mission';
    if (targetType === 'body') return formatBodyNameFromId(bodyId) || bodyId || 'Body';
    return normalizeText(trackingState?.norad_id);
};

export const clampTargetPassHours = (value) => {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return MAX_TARGET_PASS_HOURS;
    }
    return Math.min(MAX_TARGET_PASS_HOURS, parsed);
};

export const buildTargetKeyFromTrackingState = (trackingState = {}) => {
    const targetType = normalizeTargetType(trackingState);
    if (targetType === 'mission') {
        const command = String(trackingState?.command || '').trim();
        return command ? `mission:${command}` : '';
    }
    if (targetType === 'body') {
        const bodyId = String(trackingState?.body_id || '').trim().toLowerCase();
        return bodyId ? `body:${bodyId}` : '';
    }
    return '';
};

export const buildTargetCelestialPayload = ({
    trackingState = {},
    targetName = '',
    nextPassesHours = MAX_TARGET_PASS_HOURS,
} = {}) => {
    const targetType = normalizeTargetType(trackingState);
    if (targetType === 'satellite') {
        return null;
    }

    const futureHours = clampTargetPassHours(nextPassesHours);
    const sharedPayload = {
        past_hours: 0,
        future_hours: futureHours,
        step_minutes: 60,
    };

    if (targetType === 'mission') {
        const command = String(trackingState?.command || '').trim();
        if (!command) return null;
        return {
            ...sharedPayload,
            celestial: [
                {
                    target_type: 'mission',
                    command,
                    name: String(targetName || command).trim() || command,
                },
            ],
        };
    }

    const bodyId = String(trackingState?.body_id || '').trim().toLowerCase();
    if (!bodyId) return null;
    return {
        ...sharedPayload,
        celestial: [
            {
                target_type: 'body',
                body_id: bodyId,
                name: String(targetName || bodyId).trim() || bodyId,
            },
        ],
    };
};

export const filterPassesForTargetWindow = ({
    passes = [],
    targetKey = '',
    nextPassesHours = MAX_TARGET_PASS_HOURS,
    nowMs = Date.now(),
} = {}) => {
    const key = String(targetKey || '').trim();
    if (!key) return [];
    const source = Array.isArray(passes) ? passes : [];
    const windowEndMs = nowMs + (clampTargetPassHours(nextPassesHours) * 3600 * 1000);

    return source
        .filter((pass) => String(pass?.target_key || '').trim() === key)
        .filter((pass) => {
            const startMs = new Date(pass?.event_start || '').getTime();
            const endMs = new Date(pass?.event_end || '').getTime();
            if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) return false;
            if (endMs < nowMs) return false;
            return startMs <= windowEndMs;
        })
        .sort((left, right) => new Date(left.event_start).getTime() - new Date(right.event_start).getTime());
};
