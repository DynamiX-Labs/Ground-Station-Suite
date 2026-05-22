import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Card, Box } from '@mui/material';
import { useSocket } from '../common/socket.jsx';
import {
    startSatelliteSync,
    fetchSyncState,
} from './synchronize-slice.jsx';
import SyncCardHeader from './synchronize-header.jsx';
import SyncProgressBar from './synchronize-progress.jsx';
import SyncTerminal from './synchronize-terminal.jsx';
import ErrorSection from './synchronize-error.jsx';
import SyncResultsTable from './synchronize-results.jsx';


const SynchronizeOrbitalDataCard = function () {
    const dispatch = useDispatch();
    const { socket } = useSocket();
    const {
        syncState,
    } = useSelector((state) => state.syncSatellite);
    const [showErrors, setShowErrors] = useState(false);

    const handleSynchronizeSatellites = async () => {
        dispatch(startSatelliteSync({ socket }));
    };

    useEffect(() => {
        dispatch(fetchSyncState({socket: socket}));
    }, []);

    // Check if there are newly added items
    const hasNewItems = syncState?.newly_added &&
        (syncState.newly_added.satellites?.length > 0 || syncState.newly_added.transmitters?.length > 0);

    const newSatellitesCount = syncState?.newly_added?.satellites?.length || 0;
    const newTransmittersCount = syncState?.newly_added?.transmitters?.length || 0;

    // Check if there are removed items
    const hasRemovedItems = syncState?.removed &&
        (syncState.removed.satellites?.length > 0 || syncState.removed.transmitters?.length > 0);

    const removedSatellitesCount = syncState?.removed?.satellites?.length || 0;
    const removedTransmittersCount = syncState?.removed?.transmitters?.length || 0;

    // Check if there are modified items
    const hasModifiedItems = syncState?.modified &&
        (syncState.modified.satellites?.length > 0 || syncState.modified.transmitters?.length > 0);

    const modifiedSatellitesCount = syncState?.modified?.satellites?.length || 0;
    const modifiedTransmittersCount = syncState?.modified?.transmitters?.length || 0;

    const hasErrors = syncState?.errors && syncState.errors.length > 0;
    const errorsCount = syncState?.errors?.length || 0;

    return (
        <Card sx={(theme) => ({
            position: 'relative',
            marginBottom: 0,
            background: `linear-gradient(135deg, ${theme.palette.background.default} 0%, ${theme.palette.background.paper} 100%)`,
            borderRadius: 1,
            border: `1px solid ${theme.palette.divider}`,
            overflow: 'hidden',
        })}>
            <Box sx={(theme) => ({
                position: 'absolute',
                top: -60,
                right: -60,
                width: 150,
                height: 150,
                borderRadius: '50%',
                background: `radial-gradient(circle at center, ${theme.palette.primary.light}26 0%, ${theme.palette.primary.light}00 70%)`,
                filter: 'blur(20px)',
                zIndex: 0
            })}/>

            <Box sx={{
                position: 'relative',
                zIndex: 1,
                p: { xs: 2, sm: 3 },
            }}>
                <Box sx={(theme) => ({
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '3px',
                    background: `linear-gradient(90deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.main}00 100%)`,
                    boxShadow: `0 0 10px ${theme.palette.primary.main}80`,
                })}/>

                <SyncCardHeader
                    syncState={syncState}
                    onSynchronize={handleSynchronizeSatellites}
                />

                <SyncProgressBar syncState={syncState} />

                <SyncTerminal syncState={syncState} />

                <ErrorSection
                    hasErrors={hasErrors}
                    errorsCount={errorsCount}
                    showErrors={showErrors}
                    setShowErrors={setShowErrors}
                    syncState={syncState}
                />

                <SyncResultsTable
                    hasNewItems={hasNewItems}
                    hasModifiedItems={hasModifiedItems}
                    hasRemovedItems={hasRemovedItems}
                    newSatellitesCount={newSatellitesCount}
                    newTransmittersCount={newTransmittersCount}
                    modifiedSatellitesCount={modifiedSatellitesCount}
                    modifiedTransmittersCount={modifiedTransmittersCount}
                    removedSatellitesCount={removedSatellitesCount}
                    removedTransmittersCount={removedTransmittersCount}
                    syncState={syncState}
                />
            </Box>
        </Card>
    );
};

export default SynchronizeOrbitalDataCard;
