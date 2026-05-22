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

import {Box, Typography, Dialog, DialogTitle, DialogContent, DialogActions, IconButton} from "@mui/material";
import {betterDateTimes, betterStatusValue, renderCountryFlagsCSV} from "../common/common.jsx";
import Button from "@mui/material/Button";
import * as React from "react";
import {useEffect, useState} from "react";
import Grid from "@mui/material/Grid";
import {useDispatch, useSelector} from "react-redux";
import {
    setClickedSatellite,
    fetchSatellite,
    deleteSatellite
} from "./satellite-slice.jsx";
import {useSocket} from "../common/socket.jsx";
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import SatelliteMapContainer from "./satellite-map.jsx";
import TransmittersTable from "./transmitters-table.jsx";
import { useParams, useNavigate } from 'react-router';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CloseIcon from '@mui/icons-material/Close';
import { toast } from '../../utils/toast-with-timestamp.jsx';
import { useTranslation } from 'react-i18next';


// Fix for default markers in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});


// Core satellite info content component
const SatelliteInfoContent = ({
    satelliteData,
    asDialog = false,
    onClose = null,
    showDeleteButton = true,
    deleteButtonSlot = null
}) => {
    const { t } = useTranslation('satellites');
    const dispatch = useDispatch();
    const {socket} = useSocket();
    const navigate = useNavigate();
    const [imageError, setImageError] = useState(false);
    const [satellitePosition, setSatellitePosition] = useState([0, 0]);
    const [deleteSatelliteConfirmOpen, setDeleteSatelliteConfirmOpen] = useState(false);

    // Get timezone preference
    const timezone = useSelector((state) => {
        const tzPref = state.preferences?.preferences?.find(p => p.name === 'timezone');
        return tzPref?.value || 'UTC';
    });

    useEffect(() => {
        if (satelliteData) {
            if (satelliteData.latitude && satelliteData.longitude) {
                setSatellitePosition([satelliteData.latitude, satelliteData.longitude]);
            } else {
                setSatellitePosition([0, 0]);
            }
        }
    }, [satelliteData]);

    const handleImageError = () => {
        setImageError(true);
    };

    const renderTextWithClickableLinks = (text) => {
        if (!text || text === '-') return '-';

        const urlRegex = /(https?:\/\/[^\s]+)/g;
        const parts = text.split(urlRegex);

        return parts.map((part, index) => {
            if (urlRegex.test(part)) {
                return (
                    <a
                        key={index}
                        href={part}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{textDecoration: 'underline'}}
                    >
                        {part}
                    </a>
                );
            }
            return part;
        });
    };

    if (!satelliteData || satelliteData.id === null) {
        return (
            <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography>{t('satellite_info.transmitters.no_data')}</Typography>
            </Box>
        );
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            {/* Delete button - render in slot if provided, otherwise show here */}
            {showDeleteButton && !deleteButtonSlot && (
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
                    <Button
                        variant="contained"
                        color="error"
                        onClick={() => setDeleteSatelliteConfirmOpen(true)}
                    >
                        {t('satellite_info.delete_satellite')}
                    </Button>
                </Box>
            )}

            {/* Delete confirmation dialog */}
            <Dialog
                open={deleteSatelliteConfirmOpen}
                onClose={() => setDeleteSatelliteConfirmOpen(false)}
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
                    {t('satellite_info.delete_confirm_title')}
                </DialogTitle>
                <DialogContent sx={{ px: 3, pt: 3, pb: 3 }}>
                    <Typography variant="body1" sx={{ mt: 2, mb: 2, color: 'text.primary' }}>
                        {t('satellite_info.delete_confirm_message')}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 2, fontWeight: 600, color: 'text.secondary' }}>
                        Satellite to be deleted:
                    </Typography>
                    <Box sx={{
                        p: 2,
                        bgcolor: (theme) => theme.palette.mode === 'dark' ? 'grey.900' : 'grey.50',
                        borderRadius: 1,
                        border: (theme) => `1px solid ${theme.palette.divider}`,
                    }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: 'text.primary' }}>
                            {satelliteData.name}
                        </Typography>
                        <Box sx={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 1, columnGap: 2 }}>
                            <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary', fontWeight: 500 }}>
                                NORAD ID:
                            </Typography>
                            <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.primary' }}>
                                {satelliteData.norad_id}
                            </Typography>

                            {satelliteData.status && (
                                <>
                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary', fontWeight: 500 }}>
                                        Status:
                                    </Typography>
                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.primary' }}>
                                        {betterStatusValue(satelliteData.status)}
                                    </Typography>
                                </>
                            )}

                            {satelliteData.countries && (
                                <>
                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary', fontWeight: 500 }}>
                                        Countries:
                                    </Typography>
                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.primary' }}>
                                        {renderCountryFlagsCSV(satelliteData.countries)}
                                    </Typography>
                                </>
                            )}

                            {satelliteData.transmitters && satelliteData.transmitters.length > 0 && (
                                <>
                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'text.secondary', fontWeight: 500 }}>
                                        Transmitters:
                                    </Typography>
                                    <Typography variant="body2" sx={{ fontSize: '0.813rem', color: 'warning.main', fontWeight: 500 }}>
                                        {satelliteData.transmitters.length} transmitter(s) will also be deleted
                                    </Typography>
                                </>
                            )}
                        </Box>
                    </Box>
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
                        onClick={() => setDeleteSatelliteConfirmOpen(false)}
                        variant="outlined"
                        color="inherit"
                        sx={{
                            minWidth: 100,
                            textTransform: 'none',
                            fontWeight: 500,
                        }}
                    >
                        {t('satellite_info.transmitters.cancel')}
                    </Button>
                    <Button
                        variant="contained"
                        color="error"
                        onClick={async () => {
                            try {
                                await dispatch(deleteSatellite({
                                    socket,
                                    noradId: satelliteData.norad_id
                                })).unwrap();
                                if (!asDialog) {
                                    navigate('/satellites/satellites');
                                } else if (onClose) {
                                    onClose();
                                }
                                toast.success(t('satellite_info.delete_success'));
                            } catch (error) {
                                console.error('Failed to delete satellite:', error);
                                toast.error(t('satellite_info.delete_failed', { error }));
                            }
                            setDeleteSatelliteConfirmOpen(false);
                        }}
                        sx={{
                            minWidth: 100,
                            textTransform: 'none',
                            fontWeight: 600,
                        }}
                    >
                        {t('satellite_info.transmitters.delete')}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Render delete button in custom slot if provided */}
            {deleteButtonSlot && deleteButtonSlot(() => setDeleteSatelliteConfirmOpen(true))}

            {/* Main Content */}
            <Grid
                container
                spacing={3}
                sx={{
                    width: '100%',
                    flexShrink: 0,
                    mb: 2
                }}
            >
                {/* Row 1: Satellite Info */}
                <Grid
                    size={{xs: 12, md: asDialog ? 6 : 12, lg: asDialog ? 6 : 4}}
                    sx={{
                        backgroundColor: 'background.paper',
                        borderRadius: '8px',
                        padding: 3,
                        minHeight: '300px',
                        color: 'text.primary',
                        boxSizing: 'border-box'
                    }}
                >
                    <Box sx={{display: 'flex', flexDirection: 'column', gap: 2}}>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.name')}</strong> <span>{satelliteData['name']}</span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.norad_id')}</strong> <span>{satelliteData['norad_id']}</span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.status')}</strong>
                            <span>{betterStatusValue(satelliteData['status'])}</span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.countries')}</strong>
                            <span>{renderCountryFlagsCSV(satelliteData['countries'])}</span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.operator')}</strong> <span>{satelliteData['operator'] || '-'}</span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.launched')}</strong>
                            <span>{betterDateTimes(satelliteData['launched'], timezone)}</span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.deployed')}</strong>
                            <span>{betterDateTimes(satelliteData['deployed'], timezone)}</span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.decayed')}</strong>
                            <span>{betterDateTimes(satelliteData['decayed'], timezone)}</span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.updated')}</strong>
                            <span>{betterDateTimes(satelliteData['updated'], timezone)}</span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.website')}</strong>
                            <span>
                                {renderTextWithClickableLinks(satelliteData['website'])}
                            </span>
                        </Box>
                        <Box
                            sx={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                width: '100%',
                                padding: '8px 0',
                                borderBottom: '1px solid',
                                borderColor: 'border.main',
                            }}
                        >
                            <strong>{t('satellite_info.fields.citation')}</strong>
                            <span>
                                {renderTextWithClickableLinks(satelliteData['citation'])}
                            </span>
                        </Box>
                    </Box>
                </Grid>

                {/* Row 1: Image */}
                <Grid
                    size={{ xs: 12, md: asDialog ? 6 : 12, lg: asDialog ? 6 : 4 }}
                    sx={{
                        textAlign: 'center',
                        minHeight: '300px',
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        backgroundColor: 'background.paper',
                        borderRadius: '8px',
                        boxSizing: 'border-box'
                    }}
                >
                    <Box sx={{textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1}}>
                        {!imageError ? (
                            <img
                                src={`/satimages/full/${satelliteData['norad_id']}.png`}
                                alt={`Satellite ${satelliteData['norad_id']}`}
                                onError={handleImageError}
                                style={{
                                    maxWidth: '100%',
                                    height: 'auto',
                                    borderRadius: '4px',
                                }}
                            />
                        ) : (
                            <Box
                                sx={{
                                    width: '200px',
                                    height: '150px',
                                    border: '1px solid',
                                    borderColor: 'border.main',
                                    borderRadius: '4px',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center',
                                    alignItems: 'center',
                                    backgroundColor: 'background.elevated',
                                    color: 'text.disabled',
                                    gap: 1
                                }}
                            >
                                <Typography variant="caption" sx={{ color: 'text.disabled', textAlign: 'center' }}>
                                    {t('satellite_info.no_image')}
                                </Typography>
                            </Box>
                        )}
                    </Box>
                </Grid>

                {/* Row 2: Map */}
                <Grid
                    size={{ xs: 12, lg: asDialog ? 12 : 4 }}
                    sx={{
                        backgroundColor: 'background.paper',
                        borderRadius: '8px',
                        minHeight: '300px',
                        boxSizing: 'border-box',
                        overflow: 'hidden'
                    }}
                >
                    <Box sx={{ height: '100%', position: 'relative' }}>
                        <Box sx={{ height: 'calc(100%)', minHeight: '240px' }}>
                            <SatelliteMapContainer satelliteData={satelliteData}/>
                        </Box>
                    </Box>
                </Grid>
            </Grid>

            {/* Transmitters section */}
            <TransmittersTable
                satelliteData={satelliteData}
            />
        </Box>
    );
};

// Page wrapper component
const SatelliteInfoPage = () => {
    const { t } = useTranslation('satellites');
    const { noradId } = useParams();
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const {socket} = useSocket();

    // Get satellite list, clickedSatellite and loading state from Redux store
    const { satellites, clickedSatellite, loading, error } = useSelector(state => state.satellites);

    useEffect(() => {
        const noradIdInt = parseInt(noradId);

        // If we don't have the satellite data in Redux or it doesn't match the URL parameter
        if (!clickedSatellite || clickedSatellite.norad_id !== noradIdInt) {
            // First check if the satellite exists in the satellites list
            const satellite = satellites.find(sat => sat.norad_id === noradIdInt);
            if (satellite) {
                dispatch(setClickedSatellite(satellite));
            } else {
                // Try to fetch the specific satellite by NORAD ID
                dispatch(fetchSatellite({socket, noradId: noradIdInt}))
                    .unwrap()
                    .then((satelliteData) => {
                        // Successfully fetched the satellite
                        //console.info('Successfully fetched satellite:', satelliteData);
                    })
                    .catch((error) => {
                        console.error(`Failed to fetch satellite with NORAD ID ${noradId}:`, error);
                        toast.error(`Failed to load satellite data: ${error}`, {
                            autoClose: 5000,
                        });
                    });
            }
        }
    }, [noradId, satellites, clickedSatellite, dispatch, socket]);

    const handleBackClick = () => {
        navigate(-1);
    };

    // Show loading state while fetching satellite data
    if (loading && clickedSatellite.id === null) {
        return (
            <Box sx={{ p: 3 }}>
                <Box sx={{ mb: 2 }}>
                    <IconButton onClick={handleBackClick} sx={{ mr: 2 }}>
                        <ArrowBackIcon />
                    </IconButton>
                    <Typography variant="h6" display="inline">
                        {t('satellite_info.loading')}
                    </Typography>
                </Box>
            </Box>
        );
    }

    // Show error state if the satellite couldn't be found
    if (error && clickedSatellite.id === null) {
        return (
            <Box sx={{ p: 3 }}>
                <Box sx={{ mb: 2 }}>
                    <IconButton onClick={handleBackClick} sx={{ mr: 2 }}>
                        <ArrowBackIcon />
                    </IconButton>
                    <Typography variant="h6" display="inline">
                        {t('satellite_info.not_found')}
                    </Typography>
                </Box>
                <Typography variant="body1" sx={{ mt: 2 }}>
                    {t('satellite_info.not_found_message', { noradId })}
                </Typography>
                <Button
                    variant="contained"
                    onClick={() => navigate('/satellites/satellites')}
                    sx={{ mt: 2 }}
                >
                    {t('satellite_info.go_to_list')}
                </Button>
            </Box>
        );
    }

    // Don't render anything if we don't have satellite data yet
    if (clickedSatellite.id === null) {
        return (
            <Box sx={{ p: 3 }}>
                <Box sx={{ mb: 2 }}>
                    <IconButton onClick={handleBackClick} sx={{ mr: 2 }}>
                        <ArrowBackIcon />
                    </IconButton>
                    <Typography variant="h6" display="inline">
                        {t('satellite_info.loading')}
                    </Typography>
                </Box>
            </Box>
        );
    }

    return (
        <Box
            className={"top-level-box"}
            sx={{
                display: 'flex',
                flexDirection: 'column',
                p: 3,
                backgroundColor: 'background.default',
            }}>
            <SatelliteInfoContent
                satelliteData={clickedSatellite}
                asDialog={false}
                showDeleteButton={true}
                deleteButtonSlot={(onDeleteClick) => (
                    <Box sx={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2}}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <IconButton onClick={handleBackClick} sx={{mr: 2}}>
                                <ArrowBackIcon/>
                            </IconButton>
                            <Typography variant="h6">
                                {clickedSatellite.name} - {t('satellite_info.title')}
                            </Typography>
                        </Box>
                        <Button
                            variant="contained"
                            color="error"
                            onClick={onDeleteClick}
                        >
                            {t('satellite_info.delete_satellite')}
                        </Button>
                    </Box>
                )}
            />
        </Box>
    );
};

// Dialog wrapper component for use in other parts of the app
export const SatelliteInfoDialog = ({ open, onClose, satelliteData }) => {
    const { t } = useTranslation('satellites');

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="lg"
            fullWidth
            PaperProps={{
                sx: {
                    minHeight: '80vh',
                    maxHeight: '90vh'
                }
            }}
        >
            <DialogTitle>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="h6">
                        {satelliteData?.name} - {t('satellite_info.title')}
                    </Typography>
                    <IconButton onClick={onClose} size="small">
                        <CloseIcon />
                    </IconButton>
                </Box>
            </DialogTitle>
            <DialogContent dividers sx={{ p: 3 }}>
                <SatelliteInfoContent
                    satelliteData={satelliteData}
                    asDialog={true}
                    onClose={onClose}
                    showDeleteButton={false}
                />
            </DialogContent>
        </Dialog>
    );
};

export default SatelliteInfoPage;
