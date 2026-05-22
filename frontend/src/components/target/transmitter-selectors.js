import { createSelector } from '@reduxjs/toolkit';

const TARGET_TRACKER_ID_PATTERN = /^target-(\d+)$/;

const normalizeTrackerId = (value) => {
    if (typeof value !== 'string') {
        return '';
    }
    const normalized = value.trim();
    return normalized && normalized.toLowerCase() !== 'none' ? normalized : '';
};

const parseTargetSlotNumber = (trackerId = '') => {
    const match = String(trackerId || '').match(TARGET_TRACKER_ID_PATTERN);
    if (!match) {
        return null;
    }
    const parsed = Number(match[1]);
    return Number.isFinite(parsed) ? parsed : null;
};

export const getTrackerShortLabel = (trackerId = '') => {
    const slot = parseTargetSlotNumber(trackerId);
    if (slot != null) {
        return `T${slot}`;
    }
    if (String(trackerId || '').toLowerCase().startsWith('obs-')) {
        return 'OBS';
    }
    return trackerId || 'N/A';
};

const sortTrackerIds = (left, right) => {
    const leftSlot = parseTargetSlotNumber(left);
    const rightSlot = parseTargetSlotNumber(right);
    if (leftSlot != null && rightSlot != null) {
        return leftSlot - rightSlot;
    }
    if (leftSlot != null) {
        return -1;
    }
    if (rightSlot != null) {
        return 1;
    }
    return left.localeCompare(right, undefined, { numeric: true });
};

const selectTargetState = (state) => state.targetSatTrack || {};
const selectTrackerInstances = (state) => state.trackerInstances?.instances || [];

export const selectRunningTrackerIds = createSelector(
    [selectTargetState, selectTrackerInstances],
    (targetState, trackerInstances) => {
        const trackerViews = targetState?.trackerViews || {};
        const activeTrackerId = normalizeTrackerId(targetState?.trackerId);

        const instanceById = new Map();
        (trackerInstances || []).forEach((instance) => {
            const trackerId = normalizeTrackerId(instance?.tracker_id);
            if (!trackerId) {
                return;
            }
            instanceById.set(trackerId, instance);
        });

        const candidateTrackerIds = new Set([
            ...Object.keys(trackerViews || {}).map((id) => normalizeTrackerId(id)),
            ...Array.from(instanceById.keys()),
        ]);

        if (activeTrackerId) {
            candidateTrackerIds.add(activeTrackerId);
        }

        const runningIds = Array.from(candidateTrackerIds)
            .filter(Boolean)
            .filter((trackerId) => {
                if (trackerId === activeTrackerId) {
                    return true;
                }

                const instance = instanceById.get(trackerId);
                if (instance?.is_alive === true) {
                    return true;
                }

                const trackerView = trackerViews?.[trackerId] || {};
                if (trackerView?.rigData?.tracking || trackerView?.rotatorData?.tracking) {
                    return true;
                }

                return false;
            })
            .sort(sortTrackerIds);

        return runningIds;
    }
);

export const selectRunningRigTransmitters = createSelector(
    [selectTargetState, selectRunningTrackerIds],
    (targetState, runningTrackerIds) => {
        const trackerViews = targetState?.trackerViews || {};
        const activeTrackerId = normalizeTrackerId(targetState?.trackerId);
        const activeRigTransmitters = Array.isArray(targetState?.rigData?.transmitters)
            ? targetState.rigData.transmitters
            : [];
        const activeSatelliteName = targetState?.satelliteData?.details?.name || '';

        const seen = new Set();
        const transmitters = [];

        runningTrackerIds.forEach((trackerId) => {
            const trackerView = trackerViews?.[trackerId] || {};
            const trackerLabel = getTrackerShortLabel(trackerId);
            const trackerSatelliteName = trackerView?.satelliteData?.details?.name
                || (trackerId === activeTrackerId ? activeSatelliteName : '')
                || '';
            const trackerTransmitters = Array.isArray(trackerView?.rigData?.transmitters)
                ? trackerView.rigData.transmitters
                : (trackerId === activeTrackerId ? activeRigTransmitters : []);

            trackerTransmitters.forEach((transmitter) => {
                if (!transmitter?.id) {
                    return;
                }
                const key = `${trackerId}:${String(transmitter.id)}`;
                if (seen.has(key)) {
                    return;
                }
                seen.add(key);
                transmitters.push({
                    ...transmitter,
                    trackerId,
                    trackerLabel,
                    trackerSatelliteName,
                    uiId: key,
                });
            });
        });

        return transmitters;
    }
);
