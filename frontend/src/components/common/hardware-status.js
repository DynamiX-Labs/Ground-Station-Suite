/**
 * Shared hardware status helpers used by target tabs and hardware popovers.
 * Keep state derivation rules centralized so UI surfaces stay consistent.
 */

export const NONE_ID_VALUES = ['', 'none', null, undefined];

export const ROTATOR_LED_STATUS = {
    NONE: 'none',
    DISCONNECTED: 'disconnected',
    PARKED: 'parked',
    OUT_OF_BOUNDS: 'outofbounds',
    MIN_ELEVATION: 'minelevation',
    SLEWING: 'slewing',
    TRACKING: 'tracking',
    STOPPED: 'stopped',
    CONNECTED: 'connected',
    UNKNOWN: 'unknown',
};

export const RIG_LED_STATUS = {
    NONE: 'none',
    DISCONNECTED: 'disconnected',
    TRACKING: 'tracking',
    STOPPED: 'stopped',
    CONNECTED: 'connected',
    UNKNOWN: 'unknown',
};

export const hasAssignedHardwareId = (value) => {
    const normalized = String(value ?? '').trim().toLowerCase();
    return !['', 'none', 'null', 'undefined'].includes(normalized);
};

export const resolveAssignedHardwareId = (...candidates) => {
    for (const candidate of candidates) {
        // Empty string means "unset in this source", so try the next fallback.
        // Explicit "none" must be preserved as a deliberate unassignment.
        if (candidate == null) continue;
        if (String(candidate).trim() === '') continue;
        return candidate;
    }
    return 'none';
};

export const resolveRotatorLedStatus = ({ rotatorId, rotatorData = {}, trackingState = {} }) => {
    if (NONE_ID_VALUES.includes(rotatorId)) return ROTATOR_LED_STATUS.NONE;
    if (rotatorData?.connected === false || trackingState?.rotator_state === 'disconnected') return ROTATOR_LED_STATUS.DISCONNECTED;
    if (rotatorData?.parked === true || trackingState?.rotator_state === 'parked') return ROTATOR_LED_STATUS.PARKED;
    if (rotatorData?.outofbounds === true) return ROTATOR_LED_STATUS.OUT_OF_BOUNDS;
    if (rotatorData?.minelevation === true) return ROTATOR_LED_STATUS.MIN_ELEVATION;
    if (rotatorData?.slewing === true) return ROTATOR_LED_STATUS.SLEWING;
    if (rotatorData?.tracking === true || trackingState?.rotator_state === 'tracking') return ROTATOR_LED_STATUS.TRACKING;
    if (rotatorData?.stopped === true || trackingState?.rotator_state === 'stopped') return ROTATOR_LED_STATUS.STOPPED;
    if (rotatorData?.connected === true || trackingState?.rotator_state === 'connected') return ROTATOR_LED_STATUS.CONNECTED;
    return ROTATOR_LED_STATUS.UNKNOWN;
};

export const resolveRigLedStatus = ({ rigId, rigData = {}, trackingState = {} }) => {
    if (NONE_ID_VALUES.includes(rigId)) return RIG_LED_STATUS.NONE;
    if (rigData?.connected === false || trackingState?.rig_state === 'disconnected') return RIG_LED_STATUS.DISCONNECTED;
    if (rigData?.tracking === true || trackingState?.rig_state === 'tracking') return RIG_LED_STATUS.TRACKING;
    if (rigData?.stopped === true || trackingState?.rig_state === 'stopped') return RIG_LED_STATUS.STOPPED;
    if (rigData?.connected === true || trackingState?.rig_state === 'connected') return RIG_LED_STATUS.CONNECTED;
    return RIG_LED_STATUS.UNKNOWN;
};

export const shouldFallbackToRigStatus = (rotatorStatus, rigStatus) => {
    return (
        (rotatorStatus === ROTATOR_LED_STATUS.NONE || rotatorStatus === ROTATOR_LED_STATUS.DISCONNECTED)
        && ![RIG_LED_STATUS.NONE, RIG_LED_STATUS.UNKNOWN, RIG_LED_STATUS.DISCONNECTED].includes(rigStatus)
    );
};

export const resolveTabHardwareLedStatus = ({ rotatorId, rigId, rotatorData = {}, rigData = {}, trackingState = {} }) => {
    const rotatorStatus = resolveRotatorLedStatus({ rotatorId, rotatorData, trackingState });
    const rigStatus = resolveRigLedStatus({ rigId, rigData, trackingState });

    if (shouldFallbackToRigStatus(rotatorStatus, rigStatus)) {
        return {
            source: 'rig',
            status: rigStatus,
            usedRigFallback: true,
            rotatorStatus,
            rigStatus,
        };
    }

    if (rotatorStatus !== ROTATOR_LED_STATUS.NONE && rotatorStatus !== ROTATOR_LED_STATUS.UNKNOWN) {
        return {
            source: 'rotator',
            status: rotatorStatus,
            usedRigFallback: false,
            rotatorStatus,
            rigStatus,
        };
    }

    return {
        source: 'rig',
        status: rigStatus,
        usedRigFallback: false,
        rotatorStatus,
        rigStatus,
    };
};

// Warning/attention semantics for dashboard badge counters:
// - disconnected is neutral
// - stopped is neutral
export const isRotatorWarningStatus = (status) => {
    return [
        ROTATOR_LED_STATUS.OUT_OF_BOUNDS,
        ROTATOR_LED_STATUS.MIN_ELEVATION,
        ROTATOR_LED_STATUS.PARKED,
    ].includes(status);
};

export const isRigWarningStatus = (_status) => {
    return false;
};
