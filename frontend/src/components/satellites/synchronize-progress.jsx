import React from 'react';
import { Box, Typography } from '@mui/material';
import LinearProgress from '@mui/material/LinearProgress';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';

const SyncProgressBar = ({ syncState }) => {
    const { t } = useTranslation('satellites');
    return (
        <>
            <Box sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mb: 1,
            }}>
                <Typography
                    variant="caption"
                    sx={{
                        color: 'text.secondary',
                        fontWeight: 500,
                        textTransform: 'uppercase',
                        letterSpacing: '1px',
                        fontSize: '0.7rem',
                    }}
                >
                    {t('synchronize.progress.title')}
                </Typography>
                <Typography
                    variant="h6"
                    sx={(theme) => ({
                        color: 'primary.light',
                        fontWeight: 700,
                        textShadow: `0 0 5px ${theme.palette.primary.light}4D`,
                        fontFamily: 'monospace',
                        fontSize: '1.1rem',
                    })}
                >
                    {`${Math.round(syncState['progress'])}%`}
                </Typography>
            </Box>

            <Box sx={{ position: 'relative', mb: 2 }}>
                <LinearProgress
                    variant="determinate"
                    value={syncState['progress']}
                    sx={(theme) => ({
                        height: 10,
                        borderRadius: 5,
                        backgroundColor: 'action.hover',
                        '& .MuiLinearProgress-bar': {
                            background: `linear-gradient(90deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.light} 100%)`,
                            borderRadius: 5,
                            boxShadow: `0 0 10px ${theme.palette.primary.light}80`,
                        }
                    })}
                />

                {syncState['progress'] > 0 && syncState['progress'] < 100 && (
                    <Box sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        height: '100%',
                        width: '5px',
                        background: 'rgba(255,255,255,0.7)',
                        filter: 'blur(3px)',
                        animation: 'scan 2s infinite linear',
                        '@keyframes scan': {
                            '0%': { left: '0%' },
                            '100%': { left: '100%' }
                        },
                        zIndex: 2,
                    }}/>
                )}
            </Box>
        </>
    );
};

SyncProgressBar.propTypes = {
    syncState: PropTypes.object.isRequired,
};

export default SyncProgressBar;