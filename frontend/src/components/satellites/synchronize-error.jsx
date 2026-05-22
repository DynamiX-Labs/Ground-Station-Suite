import React from 'react';
import { Box, Typography, IconButton, Collapse } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ErrorIcon from '@mui/icons-material/Error';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';

const ErrorSection = ({ hasErrors, errorsCount, showErrors, setShowErrors, syncState }) => {
    const { t } = useTranslation('satellites');
    if (!hasErrors) return null;

    return (
        <Box sx={(theme) => ({
            backgroundColor: `${theme.palette.error.main}1A`,
            border: `1px solid ${theme.palette.error.main}4D`,
            borderRadius: 1,
            p: 1,
            mb: 1,
        })}>
            <Box sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                cursor: 'pointer',
            }}
                 onClick={() => setShowErrors(!showErrors)}
            >
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <ErrorIcon
                        sx={(theme) => ({
                            color: 'error.main',
                            mr: 1,
                            fontSize: '1.2rem',
                            animation: 'pulseError 2s infinite ease-in-out',
                            '@keyframes pulseError': {
                                '0%': { filter: `drop-shadow(0 0 3px ${theme.palette.error.main}99)` },
                                '50%': { filter: `drop-shadow(0 0 8px ${theme.palette.error.main}E6)` },
                                '100%': { filter: `drop-shadow(0 0 3px ${theme.palette.error.main}99)` }
                            }
                        })}
                    />
                    <Typography
                        variant="caption"
                        sx={{
                            color: 'error.main',
                            fontWeight: 600,
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px',
                            fontSize: '0.75rem',
                        }}
                    >
                        {errorsCount > 1 ? t('synchronize.errors.title_plural', { count: errorsCount }) : t('synchronize.errors.title_singular', { count: errorsCount })}
                    </Typography>
                </Box>
                <IconButton
                    size="small"
                    sx={{ color: 'error.main', p: 0.5 }}
                >
                    {showErrors ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
            </Box>

            <Collapse in={showErrors}>
                <Box sx={{ mt: 1, maxHeight: '200px', overflowY: 'auto', p: 1, backgroundColor: 'action.hover', borderRadius: 1 }}>
                    {syncState.errors.map((error, index) => (
                        <Typography
                            key={index}
                            variant="caption"
                            component="div"
                            sx={{
                                fontFamily: 'monospace',
                                color: 'error.light',
                                fontSize: '0.75rem',
                                mb: 1,
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                            }}
                        >
                            - {error}
                        </Typography>
                    ))}
                </Box>
            </Collapse>
        </Box>
    );
};

ErrorSection.propTypes = {
    hasErrors: PropTypes.bool.isRequired,
    errorsCount: PropTypes.number.isRequired,
    showErrors: PropTypes.bool.isRequired,
    setShowErrors: PropTypes.func.isRequired,
    syncState: PropTypes.object.isRequired,
};

export default ErrorSection;