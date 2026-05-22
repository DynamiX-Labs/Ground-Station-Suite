import React from 'react';
import { useCallback, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import PassTimeline from '../passes/timeline/pass-timeline.jsx';
import CelestialPassTimeline from '../celestial/celestial-pass-timeline.jsx';
import { useSocket } from '../common/socket.jsx';
import { fetchCelestialTracks, fetchSolarSystemScene } from '../celestial/celestial-slice.jsx';
import {
    buildTargetCelestialPayload,
    buildTargetKeyFromTrackingState,
    clampTargetPassHours,
    filterPassesForTargetWindow,
    normalizeTargetType,
    resolveTargetDisplayName,
} from './celestial-target-utils.js';

const TargetPassTimelineComponent = (props) => {
    const dispatch = useDispatch();
    const { socket } = useSocket();
    const satellitePasses = useSelector((state) => state.targetSatTrack.satellitePasses);
    const activePass = useSelector((state) => state.targetSatTrack.activePass);
    const gridEditable = useSelector((state) => state.targetSatTrack.gridEditable);
    const trackingState = useSelector((state) => state.targetSatTrack.trackingState || {});
    const satelliteDetails = useSelector((state) => state.targetSatTrack.satelliteData?.details || {});
    const trackerInstances = useSelector((state) => state.trackerInstances?.instances || []);
    const nextPassesHours = useSelector((state) => state.targetSatTrack.nextPassesHours || 24.0);
    const celestialState = useSelector((state) => state.celestial || {});
    const monitoredRows = useSelector((state) => state.celestialMonitored?.monitored || []);
    const groundStationLocation = useSelector((state) => state.location.location);
    const timezone = useSelector(
        (state) => {
            const timezonePref = state.preferences.preferences.find((pref) => pref.name === 'timezone');
            return timezonePref ? timezonePref.value : 'UTC';
        },
        (prev, next) => prev === next,
    );
    const targetType = normalizeTargetType(trackingState);
    const isSatelliteTarget = targetType === 'satellite';
    const targetKey = useMemo(
        () => buildTargetKeyFromTrackingState(trackingState),
        [trackingState],
    );
    const targetName = useMemo(() => {
        return resolveTargetDisplayName({
            trackingState,
            satelliteDetails,
            monitoredRows,
            celestialRows: celestialState?.celestialTracks?.celestial || [],
        });
    }, [celestialState?.celestialTracks?.celestial, monitoredRows, satelliteDetails, trackingState]);
    const nonSatellitePayload = useMemo(
        () => buildTargetCelestialPayload({
            trackingState,
            targetName,
            nextPassesHours,
        }),
        [nextPassesHours, targetName, trackingState],
    );
    const nonSatellitePasses = useMemo(
        () => filterPassesForTargetWindow({
            passes: celestialState?.celestialTracks?.celestial_passes || [],
            targetKey,
            nextPassesHours,
        }),
        [celestialState?.celestialTracks?.celestial_passes, nextPassesHours, targetKey],
    );
    const handleRefreshNonSatelliteTimeline = useCallback(async () => {
        if (!socket || !nonSatellitePayload) return;
        await Promise.all([
            dispatch(fetchSolarSystemScene({ socket, payload: nonSatellitePayload })),
            dispatch(fetchCelestialTracks({ socket, payload: nonSatellitePayload })),
        ]);
    }, [dispatch, nonSatellitePayload, socket]);

    if (!isSatelliteTarget) {
        return (
            <CelestialPassTimeline
                passes={nonSatellitePasses}
                loading={Boolean(celestialState?.tracksLoading)}
                gridEditable={gridEditable}
                projectionFutureHours={clampTargetPassHours(nextPassesHours)}
                selectedTargetKey={targetKey}
                onRefresh={handleRefreshNonSatelliteTimeline}
            />
        );
    }

    return (
        <PassTimeline
            {...props}
            passes={satellitePasses}
            activePass={activePass}
            gridEditable={gridEditable}
            groundStationLocation={groundStationLocation}
            timezone={timezone}
            noTargetsConfigured={trackerInstances.length === 0}
        />
    );
};

export const SatellitePassTimeline = React.memo(TargetPassTimelineComponent);

export default SatellitePassTimeline;
