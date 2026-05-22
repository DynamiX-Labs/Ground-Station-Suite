import React from 'react';
import { Box, Typography, Paper, Tooltip, Chip } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import SatelliteAltIcon from '@mui/icons-material/SatelliteAlt';
import RadioIcon from '@mui/icons-material/Radio';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';

const RemovedItemsTable = ({ removedSatellitesCount, removedTransmittersCount, syncState }) => {
    const { t } = useTranslation('satellites');
    return (
        <Paper
            elevation={3}
            sx={(theme) => ({
                backgroundColor: `${theme.palette.error.main}1A`,
                border: `1px solid ${theme.palette.error.main}4D`,
                borderRadius: 1,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                height: { xs: 350, sm: 380, md: 400 },
                minHeight: 300,
            })}
        >
            <Box sx={(theme) => ({
                backgroundColor: `${theme.palette.error.main}33`,
                p: { xs: 1, sm: 1.5 },
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
            })}>
                <Typography
                    variant="subtitle1"
                    sx={{
                        color: 'error.main',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px',
                        fontSize: { xs: '0.75rem', sm: '0.85rem' },
                    }}
                >
                    {t('synchronize.results.removed')}
                </Typography>
            </Box>

            {/* Fixed Table Header */}
            <Box sx={(theme) => ({
                backgroundColor: `${theme.palette.error.main}26`,
                borderBottom: `1px solid ${theme.palette.error.main}4D`,
                flexShrink: 0,
            })}>
                <Box sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '60px 1fr 60px', sm: '70px 1fr 70px', md: '80px 1fr 80px' },
                    gap: { xs: 0.5, sm: 0.75, md: 1 },
                    p: { xs: 0.75, sm: 1 },
                }}>
                    <Typography sx={{
                        color: 'error.main',
                        fontWeight: 600,
                        fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                        textTransform: 'uppercase',
                        textAlign: 'center',
                    }}>
                        {t('synchronize.results.type')}
                    </Typography>
                    <Typography sx={{
                        color: 'error.main',
                        fontWeight: 600,
                        fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                        textTransform: 'uppercase',
                        textAlign: 'left',
                        pl: { xs: 0.5, sm: 0.75, md: 1 },
                    }}>
                        {t('synchronize.results.name')}
                    </Typography>
                    <Typography sx={{
                        color: 'error.main',
                        fontWeight: 600,
                        fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                        textTransform: 'uppercase',
                        textAlign: 'center',
                    }}>
                        {t('synchronize.results.id')}
                    </Typography>
                </Box>
            </Box>

            {/* Scrollable Content Area */}
            <Box sx={(theme) => ({
                flex: 1,
                overflow: 'auto',
                '&::-webkit-scrollbar': {
                    width: { xs: '4px', sm: '6px', md: '8px' },
                },
                '&::-webkit-scrollbar-track': {
                    backgroundColor: `${theme.palette.error.main}1A`,
                },
                '&::-webkit-scrollbar-thumb': {
                    backgroundColor: `${theme.palette.error.main}66`,
                    borderRadius: '4px',
                    '&:hover': {
                        backgroundColor: `${theme.palette.error.main}99`,
                    },
                },
            })}>
                {/* Empty State */}
                {removedSatellitesCount === 0 && removedTransmittersCount === 0 && (
                    <Box sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        p: 3,
                    }}>
                        <Typography sx={{
                            color: 'text.secondary',
                            fontSize: { xs: '0.75rem', sm: '0.85rem', md: '0.9rem' },
                            fontStyle: 'italic',
                            textAlign: 'center',
                        }}>
                            {t('synchronize.results.no_removed_items')}
                        </Typography>
                    </Box>
                )}

                {/* Satellites */}
                {syncState.removed.satellites?.slice(0, 50).map((sat, index) => (
                    <Box
                        key={`sat-${index}`}
                        sx={(theme) => ({
                            display: 'grid',
                            gridTemplateColumns: { xs: '60px 1fr 60px', sm: '70px 1fr 70px', md: '80px 1fr 80px' },
                            gap: { xs: 0.5, sm: 0.75, md: 1 },
                            p: { xs: 0.75, sm: 1 },
                            borderBottom: `1px solid ${theme.palette.error.main}1A`,
                            '&:nth-of-type(even)': { backgroundColor: `${theme.palette.error.main}0D` },
                            '&:hover': { backgroundColor: `${theme.palette.error.main}1A` },
                            alignItems: 'center',
                        })}
                    >
                        <Box sx={{
                            color: 'primary.light',
                            fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                            fontFamily: 'monospace',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}>
                            <SatelliteAltIcon sx={{
                                fontSize: { xs: '0.7rem', sm: '0.75rem', md: '0.8rem' },
                                mr: { xs: 0.25, sm: 0.5 }
                            }} />
                            <Box sx={{ display: { xs: 'none', sm: 'block' } }}>{t('synchronize.results.sat')}</Box>
                        </Box>
                        <Box sx={{
                            color: 'text.primary',
                            fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                            fontFamily: 'monospace',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            textAlign: 'left',
                            pl: { xs: 0.5, sm: 0.75, md: 1 },
                        }}>
                            <Tooltip title={sat.name} placement="top">
                                <span>{sat.name}</span>
                            </Tooltip>
                        </Box>
                        <Box sx={{
                            color: 'text.secondary',
                            fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                            fontFamily: 'monospace',
                            textAlign: 'center',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                        }}>
                            {sat.norad_id}
                        </Box>
                    </Box>
                ))}

                {/* Transmitters */}
                {syncState.removed.transmitters?.slice(0, 50).map((trx, index) => (
                    <Box
                        key={`trx-${index}`}
                        sx={(theme) => ({
                            display: 'grid',
                            gridTemplateColumns: { xs: '60px 1fr 60px', sm: '70px 1fr 70px', md: '80px 1fr 80px' },
                            gap: { xs: 0.5, sm: 0.75, md: 1 },
                            p: { xs: 0.75, sm: 1 },
                            borderBottom: `1px solid ${theme.palette.error.main}1A`,
                            '&:nth-of-type(even)': { backgroundColor: `${theme.palette.error.main}0D` },
                            '&:hover': { backgroundColor: `${theme.palette.error.main}1A` },
                            alignItems: 'center',
                        })}
                    >
                        <Box sx={{
                            color: 'error.light',
                            fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                            fontFamily: 'monospace',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}>
                            <RadioIcon sx={{
                                fontSize: { xs: '0.7rem', sm: '0.75rem', md: '0.8rem' },
                                mr: { xs: 0.25, sm: 0.5 }
                            }} />
                            <Box sx={{ display: { xs: 'none', sm: 'block' } }}>{t('synchronize.results.trx')}</Box>
                        </Box>
                        <Box sx={{
                            color: 'text.primary',
                            fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                            fontFamily: 'monospace',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            textAlign: 'left',
                            pl: { xs: 0.5, sm: 0.75, md: 1 },
                        }}>
                            <Tooltip title={`${trx.description || t('synchronize.results.unknown')} (${trx.satellite_name})`} placement="top">
                                <span>{trx.description || t('synchronize.results.unknown')}</span>
                            </Tooltip>
                        </Box>
                        <Box sx={{
                            color: 'text.secondary',
                            fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                            fontFamily: 'monospace',
                            textAlign: 'center',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                        }}>
                            {trx.satellite_name}
                        </Box>
                    </Box>
                ))}

                {/* Show more indicator */}
                {(removedSatellitesCount + removedTransmittersCount > 100) && (
                    <Box sx={{
                        textAlign: 'center',
                        color: 'error.main',
                        fontSize: { xs: '0.6rem', sm: '0.65rem', md: '0.7rem' },
                        fontStyle: 'italic',
                        p: { xs: 1.5, sm: 2 },
                    }}>
                        {t('synchronize.results.more_items', { count: (removedSatellitesCount + removedTransmittersCount) - 100 })}
                    </Box>
                )}
            </Box>

            <Box sx={(theme) => ({
                p: { xs: 0.75, sm: 1 },
                backgroundColor: `${theme.palette.error.main}1A`,
                display: 'flex',
                justifyContent: 'center',
                gap: { xs: 0.5, sm: 1 },
                flexShrink: 0,
                flexWrap: 'wrap',
            })}>
                <Chip
                    label={t('synchronize.results.satellites_count', { count: removedSatellitesCount })}
                    size="small"
                    sx={(theme) => ({
                        backgroundColor: `${theme.palette.primary.light}33`,
                        color: 'primary.light',
                        fontSize: { xs: '0.55rem', sm: '0.6rem', md: '0.65rem' },
                        fontWeight: 600,
                        height: { xs: 16, sm: 18 },
                    })}
                />
                <Chip
                    label={t('synchronize.results.transmitters_count', { count: removedTransmittersCount })}
                    size="small"
                    sx={(theme) => ({
                        backgroundColor: `${theme.palette.error.light}33`,
                        color: 'error.light',
                        fontSize: { xs: '0.55rem', sm: '0.6rem', md: '0.65rem' },
                        fontWeight: 600,
                        height: { xs: 16, sm: 18 },
                    })}
                />
            </Box>
        </Paper>
    );
};

RemovedItemsTable.propTypes = {
    removedSatellitesCount: PropTypes.number.isRequired,
    removedTransmittersCount: PropTypes.number.isRequired,
    syncState: PropTypes.object.isRequired,
};

export default RemovedItemsTable;