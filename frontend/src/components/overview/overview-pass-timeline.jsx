import React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useSocket } from '../common/socket.jsx';
import {
    fetchNextPassesForGroup,
    setShowGeostationarySatellites,
} from './overview-slice.jsx';
import PassTimeline from '../passes/timeline/pass-timeline.jsx';

const OverviewPassTimeline = () => {
    const dispatch = useDispatch();
    const { socket } = useSocket();
    const passes = useSelector((state) => state.overviewSatTrack.passes);
    const gridEditable = useSelector((state) => state.overviewSatTrack.gridEditable);
    const nextPassesHours = useSelector((state) => state.overviewSatTrack.nextPassesHours);
    const passesAreCached = useSelector((state) => state.overviewSatTrack.passesAreCached);
    const passesLoading = useSelector((state) => state.overviewSatTrack.passesLoading);
    const selectedSatGroupId = useSelector((state) => state.overviewSatTrack.selectedSatGroupId);
    const selectedSatelliteId = useSelector((state) => state.overviewSatTrack.selectedSatelliteId);
    const showGeostationarySatellites = useSelector((state) => state.overviewSatTrack.showGeostationarySatellites);
    const passesRangeStart = useSelector((state) => state.overviewSatTrack.passesRangeStart);
    const passesRangeEnd = useSelector((state) => state.overviewSatTrack.passesRangeEnd);
    const groundStationLocation = useSelector((state) => state.location.location);
    const timezone = useSelector(
        (state) => {
            const timezonePref = state.preferences.preferences.find((pref) => pref.name === 'timezone');
            return timezonePref ? timezonePref.value : 'UTC';
        },
        (prev, next) => prev === next,
    );

    const handleRefreshPasses = () => {
        if (selectedSatGroupId) {
            dispatch(fetchNextPassesForGroup({
                socket,
                selectedSatGroupId,
                hours: nextPassesHours,
                forceRecalculate: true,
            }));
        }
    };

    const handleToggleGeostationary = () => {
        dispatch(setShowGeostationarySatellites(!showGeostationarySatellites));
    };

    return (
        <PassTimeline
            timeWindowHours={nextPassesHours}
            satelliteName={null}
            passes={passes}
            activePass={null}
            gridEditable={gridEditable}
            cachedOverride={passesAreCached}
            labelType="name"
            labelVerticalOffset={110}
            loading={passesLoading}
            nextPassesHours={nextPassesHours}
            onRefresh={handleRefreshPasses}
            showHoverElevation={false}
            showGeoToggle={true}
            showGeostationarySatellites={showGeostationarySatellites}
            onToggleGeostationary={handleToggleGeostationary}
            highlightActivePasses={true}
            highlightSatelliteId={selectedSatelliteId}
            forceTimeWindowStart={passesRangeStart}
            forceTimeWindowEnd={passesRangeEnd}
            groundStationLocation={groundStationLocation}
            timezone={timezone}
        />
    );
};

export default React.memo(OverviewPassTimeline);
