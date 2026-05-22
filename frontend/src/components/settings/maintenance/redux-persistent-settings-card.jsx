/**
 * @license
 * Copyright (c) 2025 Efstratios Goudelis
 * Modifications and extensions Copyright (C) 2026 DynamiX-Labs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 *
 */

import React, {useState} from 'react';
import {
    Typography,
    Divider,
    Button,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Alert,
    AlertTitle,
    Backdrop,
    Box,
    CircularProgress
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {useTranslation} from 'react-i18next';

const ReduxPersistentSettingsCard = () => {
    const {t} = useTranslation('settings');
    const [confirmClearReduxOpen, setConfirmClearReduxOpen] = useState(false);
    const [confirmIndividualAction, setConfirmIndividualAction] = useState(null);
    const [isReloading, setIsReloading] = useState(false);

    const clearReduxPersistentState = () => {
        setConfirmClearReduxOpen(false);
        // Clear all Redux persist keys
        const persistKeys = [
            'persist:waterfall',
            'persist:vfo',
            'persist:rigs',
            'persist:rotators',
            'persist:tleSources',
            'persist:satellites',
            'persist:satelliteGroups',
            'persist:location',
            'persist:synchronize',
            'persist:preferences',
            'persist:targetSatTrack',
            'persist:overviewSatTrack',
            'persist:dashboard',
            'persist:weather',
            'persist:sdr',
            'persist:version',
            'persist:filebrowser',
            'persist:celestial',
            'persist:celestialMonitored',
            'persist:celestialDisplay',
            'persist:root'
        ];

        persistKeys.forEach(key => {
            localStorage.removeItem(key);
        });

        // Show reload spinner and reload after 1 second
        setIsReloading(true);
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    };

    const clearFileBrowserPersist = () => {
        localStorage.removeItem('persist:filebrowser');
    };

    const clearWaterfallPersist = () => {
        localStorage.removeItem('persist:waterfall');
    };

    const clearVfoPersist = () => {
        localStorage.removeItem('persist:vfo');
    };

    const clearPreferencesPersist = () => {
        localStorage.removeItem('persist:preferences');
    };

    const clearOverviewSatTrackPersist = () => {
        localStorage.removeItem('persist:overviewSatTrack');
    };

    const clearCelestialPersist = () => {
        localStorage.removeItem('persist:celestial');
        localStorage.removeItem('persist:celestialMonitored');
        localStorage.removeItem('persist:celestialDisplay');
    };

    const openIndividualConfirmDialog = (title, description, confirmLabel, onConfirm) => {
        setConfirmIndividualAction({
            title,
            description,
            confirmLabel,
            onConfirm,
        });
    };

    const handleConfirmIndividualAction = () => {
        if (!confirmIndividualAction?.onConfirm) return;
        const action = confirmIndividualAction.onConfirm;
        setConfirmIndividualAction(null);
        action();
    };

    return (
        <>
            <Typography variant="h6" gutterBottom>
                Redux Persistent Settings
            </Typography>
            <Divider sx={{mb: 2}}/>

            <Grid container spacing={2} columns={16}>
                <Grid size={16}>
                    <Alert severity="warning" sx={{mb: 2}}>
                        <AlertTitle>Clear All Redux Settings</AlertTitle>
                        This will reset all application settings below to their defaults. Use individual buttons to
                        clear specific settings only.
                    </Alert>
                </Grid>

                <Grid size={10}>
                    {t('maintenance.clear_redux')}
                    <Typography variant="body2" color="text.secondary">
                        Clears all Redux persistent data (all settings below)
                    </Typography>
                </Grid>
                <Grid size={6}>
                    <Button
                        variant="contained"
                        color="error"
                        onClick={() => setConfirmClearReduxOpen(true)}
                        fullWidth
                        size="small"
                    >
                        {t('maintenance.clear_redux_button')}
                    </Button>
                </Grid>

                <Grid size={16}>
                    <Divider sx={{my: 2}}/>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                        Or clear individual settings:
                    </Typography>
                </Grid>

                <Grid size={10}>
                    Clear File Browser Settings
                    <Typography variant="body2" color="text.secondary">
                        Resets page size, sorting, filters, and view mode
                    </Typography>
                </Grid>
                <Grid size={6}>
                    <Button
                        variant="outlined"
                        color="warning"
                        onClick={() => openIndividualConfirmDialog(
                            'Clear File Browser Settings?',
                            'This will reset page size, sorting, filters, and view mode for the File Browser.',
                            'Clear File Browser',
                            clearFileBrowserPersist,
                        )}
                        fullWidth
                        size="small"
                    >
                        Clear
                    </Button>
                </Grid>

                <Grid size={10}>
                    Clear Waterfall Settings
                    <Typography variant="body2" color="text.secondary">
                        Resets frequency, gain, sample rate, colormap, FFT settings
                    </Typography>
                </Grid>
                <Grid size={6}>
                    <Button
                        variant="outlined"
                        color="warning"
                        onClick={() => openIndividualConfirmDialog(
                            'Clear Waterfall Settings?',
                            'This will reset frequency, gain, sample rate, colormap, and FFT settings.',
                            'Clear Waterfall',
                            clearWaterfallPersist,
                        )}
                        fullWidth
                        size="small"
                    >
                        Clear
                    </Button>
                </Grid>

                <Grid size={10}>
                    Clear VFO Settings
                    <Typography variant="body2" color="text.secondary">
                        Resets all VFO markers, frequencies, modes, and active states
                    </Typography>
                </Grid>
                <Grid size={6}>
                    <Button
                        variant="outlined"
                        color="warning"
                        onClick={() => openIndividualConfirmDialog(
                            'Clear VFO Settings?',
                            'This will reset all VFO markers, frequencies, modes, and active states.',
                            'Clear VFO',
                            clearVfoPersist,
                        )}
                        fullWidth
                        size="small"
                    >
                        Clear
                    </Button>
                </Grid>

                <Grid size={10}>
                    Clear Preferences
                    <Typography variant="body2" color="text.secondary">
                        Resets all user preferences like timezone, theme, etc.
                    </Typography>
                </Grid>
                <Grid size={6}>
                    <Button
                        variant="outlined"
                        color="warning"
                        onClick={() => openIndividualConfirmDialog(
                            'Clear Preferences?',
                            'This will reset user preferences such as timezone and theme.',
                            'Clear Preferences',
                            clearPreferencesPersist,
                        )}
                        fullWidth
                        size="small"
                    >
                        Clear
                    </Button>
                </Grid>

                <Grid size={10}>
                    Clear Overview Satellite Selection
                    <Typography variant="body2" color="text.secondary">
                        Resets selected satellite group and satellite in overview page
                    </Typography>
                </Grid>
                <Grid size={6}>
                    <Button
                        variant="outlined"
                        color="warning"
                        onClick={() => openIndividualConfirmDialog(
                            'Clear Overview Satellite Selection?',
                            'This will reset selected satellite group and satellite on the Overview page.',
                            'Clear Selection',
                            clearOverviewSatTrackPersist,
                        )}
                        fullWidth
                        size="small"
                    >
                        Clear
                    </Button>
                </Grid>

                <Grid size={10}>
                    Clear Celestial Settings
                    <Typography variant="body2" color="text.secondary">
                        Resets map settings, monitored table state, and solar system display options
                    </Typography>
                </Grid>
                <Grid size={6}>
                    <Button
                        variant="outlined"
                        color="warning"
                        onClick={() => openIndividualConfirmDialog(
                            'Clear Celestial Settings?',
                            'This will reset map settings, monitored table state, and solar system display options.',
                            'Clear Celestial',
                            clearCelestialPersist,
                        )}
                        fullWidth
                        size="small"
                    >
                        Clear
                    </Button>
                </Grid>
            </Grid>

            {/* Clear Redux Persist Confirmation Dialog */}
            <Dialog
                open={confirmClearReduxOpen}
                onClose={() => setConfirmClearReduxOpen(false)}
                maxWidth="sm"
                fullWidth
                PaperProps={{
                    sx: {
                        bgcolor: 'background.paper',
                        borderRadius: 2,
                    }
                }}
            >
                <DialogTitle
                    sx={{
                        bgcolor: 'error.main',
                        color: 'error.contrastText',
                        fontSize: '1.125rem',
                        fontWeight: 600,
                        py: 2,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1.5,
                    }}
                >
                    <Box
                        component="span"
                        sx={{
                            width: 24,
                            height: 24,
                            borderRadius: '50%',
                            bgcolor: 'error.contrastText',
                            color: 'error.main',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 'bold',
                            fontSize: '1rem',
                        }}
                    >
                        !
                    </Box>
                    Clear All Redux Persistent State?
                </DialogTitle>
                <DialogContent sx={{ px: 3, pt: 3, pb: 3 }}>
                    <Alert severity="info" sx={{ mt: 2, mb: 2 }}>
                        <AlertTitle>Local Browser Cache Only</AlertTitle>
                        This will only clear application settings stored in your browser's local storage. No backend
                        data (satellites, rigs, rotators, recordings, etc.) will be deleted.
                    </Alert>
                    <Typography variant="body1" sx={{ mb: 2, color: 'text.primary' }}>
                        This action will reset ALL local application settings to their defaults!
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 2, fontWeight: 600, color: 'text.secondary' }}>
                        Settings to be cleared:
                    </Typography>
                    <Box sx={{
                        maxHeight: 300,
                        overflowY: 'auto',
                        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
                        borderRadius: 1,
                        border: (theme) => `1px solid ${theme.palette.divider}`,
                        p: 2,
                    }}>
                        <Typography component="div" variant="body2" sx={{ fontSize: '0.813rem', color: 'text.primary' }}>
                            <ul style={{ margin: 0, paddingLeft: '1.5rem' }}>
                                <li>Waterfall settings (frequency, gain, sample rate, colormap, FFT)</li>
                                <li>VFO settings (markers, frequencies, modes, active states)</li>
                                <li>Cached rig configurations</li>
                                <li>Cached rotator configurations</li>
                                <li>Cached orbital sources</li>
                                <li>Cached satellite and group data</li>
                                <li>Location settings</li>
                                <li>User preferences (timezone, theme)</li>
                                <li>Dashboard settings</li>
                                <li>Weather settings</li>
                                <li>SDR settings</li>
                                <li>File browser settings</li>
                                <li>Celestial settings (map, monitored table, display options)</li>
                            </ul>
                        </Typography>
                    </Box>
                    <Alert severity="warning" sx={{ mt: 2 }}>
                        <AlertTitle>Page Refresh Required</AlertTitle>
                        You will need to refresh the page after clearing. The application will re-fetch all configuration data from the backend.
                    </Alert>
                </DialogContent>
                <DialogActions
                    sx={{
                        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
                        borderTop: (theme) => `1px solid ${theme.palette.divider}`,
                        px: 3,
                        py: 2,
                        gap: 1.5,
                    }}
                >
                    <Button
                        onClick={() => setConfirmClearReduxOpen(false)}
                        variant="outlined"
                        color="inherit"
                        sx={{
                            minWidth: 100,
                            textTransform: 'none',
                            fontWeight: 500,
                        }}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={clearReduxPersistentState}
                        color="error"
                        variant="contained"
                        sx={{
                            minWidth: 100,
                            textTransform: 'none',
                            fontWeight: 600,
                        }}
                    >
                        Clear All Settings
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Individual Clear Action Confirmation Dialog */}
            <Dialog
                open={Boolean(confirmIndividualAction)}
                onClose={() => setConfirmIndividualAction(null)}
                maxWidth="sm"
                fullWidth
                PaperProps={{
                    sx: {
                        bgcolor: 'background.paper',
                        borderRadius: 2,
                    }
                }}
            >
                <DialogTitle
                    sx={{
                        bgcolor: 'error.main',
                        color: 'error.contrastText',
                        fontSize: '1.125rem',
                        fontWeight: 600,
                        py: 2,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1.5,
                    }}
                >
                    <Box
                        component="span"
                        sx={{
                            width: 24,
                            height: 24,
                            borderRadius: '50%',
                            bgcolor: 'error.contrastText',
                            color: 'error.main',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 'bold',
                            fontSize: '1rem',
                        }}
                    >
                        !
                    </Box>
                    {confirmIndividualAction?.title || 'Confirm Clear Action'}
                </DialogTitle>
                <DialogContent sx={{ px: 3, pt: 3, pb: 3 }}>
                    <Alert severity="info" sx={{ mt: 2, mb: 2 }}>
                        <AlertTitle>Local Browser Cache Only</AlertTitle>
                        This only clears settings stored in your browser's local storage.
                    </Alert>
                    <Typography variant="body1" sx={{ mb: 2, color: 'text.primary' }}>
                        {confirmIndividualAction?.description}
                    </Typography>
                    <Alert severity="warning" sx={{ mt: 2 }}>
                        <AlertTitle>Reload May Be Required</AlertTitle>
                        Refresh the page if you do not immediately see the updated defaults.
                    </Alert>
                </DialogContent>
                <DialogActions
                    sx={{
                        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
                        borderTop: (theme) => `1px solid ${theme.palette.divider}`,
                        px: 3,
                        py: 2,
                        gap: 1.5,
                    }}
                >
                    <Button
                        onClick={() => setConfirmIndividualAction(null)}
                        variant="outlined"
                        color="inherit"
                        sx={{
                            minWidth: 100,
                            textTransform: 'none',
                            fontWeight: 500,
                        }}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleConfirmIndividualAction}
                        color="error"
                        variant="contained"
                        sx={{
                            minWidth: 100,
                            textTransform: 'none',
                            fontWeight: 600,
                        }}
                    >
                        {confirmIndividualAction?.confirmLabel || 'Clear'}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Reload Spinner Overlay */}
            <Backdrop
                sx={{color: '#fff', zIndex: (theme) => theme.zIndex.modal + 1}}
                open={isReloading}
            >
                <Box sx={{textAlign: 'center'}}>
                    <CircularProgress color="inherit" size={60}/>
                    <Typography variant="h6" sx={{mt: 2}}>
                        Reloading...
                    </Typography>
                </Box>
            </Backdrop>
        </>
    );
};

export default ReduxPersistentSettingsCard;
