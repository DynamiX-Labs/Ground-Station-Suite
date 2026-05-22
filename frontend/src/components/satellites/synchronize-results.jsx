import React from 'react';
import {Box, Typography} from '@mui/material';
import Grid from '@mui/material/Grid';
import AddedItemsTable from './synchronize-added.jsx';
import ModifiedItemsTable from './synchronize-modifed.jsx';
import RemovedItemsTable from './synchronize-removed.jsx';
import PropTypes from 'prop-types';

const SyncResultsTable = ({
                              hasNewItems=true,
                              hasModifiedItems=true,
                              hasRemovedItems=true,
                              newSatellitesCount=0,
                              newTransmittersCount=0,
                              modifiedSatellitesCount=0,
                              modifiedTransmittersCount=0,
                              removedSatellitesCount=0,
                              removedTransmittersCount=0,
                              syncState
                          }) => {

    //if (!hasNewItems && !hasModifiedItems && !hasRemovedItems) return null;

    return (
        <Box sx={{mt: 2}}>
            <Grid
                container
                spacing={{xs: 1, sm: 1, md: 1}}
                sx={{
                    width: '100%',
                    justifyContent: 'flex-start'
                }}
            >
                <Grid size={{xs: 12, sm: 12, md: 4, lg: 4, xl: 4}}>
                    <AddedItemsTable
                        newSatellitesCount={newSatellitesCount}
                        newTransmittersCount={newTransmittersCount}
                        syncState={syncState}
                    />
                </Grid>

                <Grid size={{xs: 12, sm: 12, md: 4, lg: 4, xl: 4}}>
                    <ModifiedItemsTable
                        modifiedSatellitesCount={modifiedSatellitesCount}
                        modifiedTransmittersCount={modifiedTransmittersCount}
                        syncState={syncState}
                    />
                </Grid>

                <Grid size={{xs: 12, sm: 12, md: 4, lg: 4, xl: 4}}>
                    <RemovedItemsTable
                        removedSatellitesCount={removedSatellitesCount}
                        removedTransmittersCount={removedTransmittersCount}
                        syncState={syncState}
                    />
                </Grid>
            </Grid>
        </Box>
    );
};

SyncResultsTable.propTypes = {
    hasNewItems: PropTypes.bool.isRequired,
    hasModifiedItems: PropTypes.bool.isRequired,
    hasRemovedItems: PropTypes.bool.isRequired,
    newSatellitesCount: PropTypes.number.isRequired,
    newTransmittersCount: PropTypes.number.isRequired,
    modifiedSatellitesCount: PropTypes.number.isRequired,
    modifiedTransmittersCount: PropTypes.number.isRequired,
    removedSatellitesCount: PropTypes.number.isRequired,
    removedTransmittersCount: PropTypes.number.isRequired,
    syncState: PropTypes.object.isRequired,
};

export default SyncResultsTable;