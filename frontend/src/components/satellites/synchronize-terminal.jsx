import React from 'react';
import { Box, Typography } from '@mui/material';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';

const SyncTerminal = ({ syncState }) => {
    const { t } = useTranslation('satellites');
    return (
        <>
            <Box sx={{
                height: '60px',
            }}>
                <Typography
                    variant="body2"
                    sx={{
                        fontFamily: 'monospace',
                        color: 'text.secondary',
                        position: 'relative',
                        zIndex: 1,
                        fontSize: { xs: '0.8rem', sm: '0.875rem' },
                        '&::after': (syncState['progress'] > 0 && syncState['progress'] < 100) ? {
                            content: '"█"',
                            animation: 'blink 1s infinite',
                            '@keyframes blink': {
                                '0%': { opacity: 0 },
                                '50%': { opacity: 1 },
                                '100%': { opacity: 0 }
                            }
                        } : {},
                    }}
                >
                    {syncState['message'] || (
                        syncState['progress'] === 0
                            ? t('synchronize.terminal.ready')
                            : syncState['progress'] === 100
                                ? t('synchronize.terminal.complete')
                                : t('synchronize.terminal.syncing')
                    )}
                </Typography>
            </Box>
        </>
    );
};

SyncTerminal.propTypes = {
    syncState: PropTypes.object.isRequired,
};

export default SyncTerminal;
