import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import SatelliteAltIcon from '@mui/icons-material/SatelliteAlt';
import SyncIcon from '@mui/icons-material/Sync';
import { humanizeDate } from '../common/common.jsx';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';

const SyncCardHeader = ({ syncState, onSynchronize }) => {
    const { t } = useTranslation('satellites');
    const isSyncing = syncState['progress'] > 0 && syncState['progress'] < 100;

    return (
        <Box sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: { xs: 'flex-start', sm: 'center' },
            mb: 2,
        }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: { xs: 1.5, sm: 0 } }}>
                <SatelliteAltIcon sx={{
                    mr: 1,
                    color: 'primary.light',
                    filter: (theme) => `drop-shadow(0 0 3px ${theme.palette.primary.light}99)`,
                    animation: 'pulse 3s infinite ease-in-out',
                    '@keyframes pulse': {
                        '0%': { opacity: 0.8 },
                        '50%': { opacity: 1 },
                        '100%': { opacity: 0.8 }
                    }
                }}/>
                <Box>
                    <Typography
                        component="div"
                        variant="h6"
                        sx={{
                            fontWeight: 700,
                            color: 'text.primary',
                            textShadow: '0 0 10px rgba(0,0,0,0.5)',
                            letterSpacing: '0.5px',
                            textTransform: 'uppercase',
                            fontSize: { xs: '1rem', sm: '1.25rem' },
                        }}
                    >
                        {t('synchronize.header.title')}
                    </Typography>
                    <Typography
                        variant="subtitle2"
                        component="div"
                        sx={{
                            color: 'text.secondary',
                            fontSize: '0.8rem',
                            fontWeight: 300,
                            letterSpacing: '0.3px',
                            display: { xs: 'none', sm: 'block' },
                        }}
                    >
                        {t('synchronize.header.subtitle')}
                    </Typography>
                </Box>
            </Box>

            <Box sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: { xs: 'flex-start', sm: 'center' }
            }}>
                <Button
                    disabled={isSyncing}
                    variant="contained"
                    color="primary"
                    onClick={onSynchronize}
                    size="small"
                    sx={(theme) => ({
                        background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
                        boxShadow: `0 5px 15px ${theme.palette.primary.main}4D`,
                        textTransform: 'uppercase',
                        fontWeight: 600,
                        letterSpacing: '1px',
                        px: { xs: 2, sm: 3 },
                        py: 1,
                        borderRadius: '8px',
                        position: 'relative',
                        overflow: 'hidden',
                        transition: 'all 0.3s ease',
                        '&:hover': {
                            background: `linear-gradient(135deg, ${theme.palette.primary.light} 0%, ${theme.palette.primary.main} 100%)`,
                            boxShadow: `0 5px 20px ${theme.palette.primary.main}80`,
                            transform: 'translateY(-2px)',
                        },
                        '&::before': {
                            content: '""',
                            position: 'absolute',
                            top: 0,
                            left: '-100%',
                            width: '100%',
                            height: '100%',
                            background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)',
                            transition: 'all 0.5s ease',
                        },
                        '&:hover::before': {
                            left: '100%',
                        },
                    })}
                >
                    <SyncIcon sx={{
                        mr: 1,
                        animation: isSyncing ? 'rotate 2s infinite linear' : 'none',
                        '@keyframes rotate': {
                            '0%': { transform: 'rotate(0deg)' },
                            '100%': { transform: 'rotate(360deg)' }
                        },
                        fontSize: { xs: '1rem', sm: '1.25rem' }
                    }}/>
                    {t('synchronize.header.button')}
                </Button>

                <Typography
                    variant="caption"
                    sx={{
                        fontFamily: 'monospace',
                        color: 'text.disabled',
                        fontSize: '0.65rem',
                        mt: 0.5,
                        textAlign: { xs: 'left', sm: 'center' },
                    }}
                >
                    {t('synchronize.header.last_update', { date: humanizeDate(syncState.last_update) })}
                </Typography>
            </Box>
        </Box>
    );
};

SyncCardHeader.propTypes = {
    syncState: PropTypes.object.isRequired,
    onSynchronize: PropTypes.func.isRequired,
};

export default SyncCardHeader;