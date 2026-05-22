/**
 * VFO Control Components
 *
 * Activate/Mute buttons and Frequency display for VFO
 */

import React from 'react';
import { Box, ToggleButton, Tooltip } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useTranslation } from 'react-i18next';
import LCDFrequencyDisplay from '../../common/lcd-frequency-display.jsx';

/**
 * VFO Activate Button Component
 */
export const VfoActivateButton = ({ vfoIndex, vfoActive, onVFOActiveChange }) => {
    const { t } = useTranslation('waterfall');

    return (
        <Tooltip title={vfoActive ? "Deactivate VFO" : "Activate VFO"} arrow>
            <ToggleButton
                value="active"
                selected={vfoActive}
                onChange={() => onVFOActiveChange(vfoIndex, !vfoActive)}
                sx={{
                    flex: 1,
                    height: '32px',
                    fontSize: '0.8rem',
                    border: '1px solid',
                    borderColor: (theme) => theme.palette.border.main,
                    borderRadius: '4px',
                    color: 'text.secondary',
                    textTransform: 'none',
                    backgroundColor: (theme) => theme.palette.state.disabledBg,
                    transition: 'all 0.2s ease-in-out',
                    '&.Mui-selected': {
                        backgroundColor: 'success.main',
                        color: 'success.contrastText',
                        borderColor: 'success.main',
                        fontWeight: 600,
                        boxShadow: (theme) => `0 0 8px ${alpha(theme.palette.success.main, 0.4)}`,
                        '&:hover': {
                            backgroundColor: 'success.dark',
                            boxShadow: (theme) => `0 0 12px ${alpha(theme.palette.success.main, 0.6)}`,
                        }
                    },
                    '&:hover': {
                        backgroundColor: (theme) => theme.palette.state.hover,
                        borderColor: (theme) => theme.palette.border.dark,
                    }
                }}
            >
                {vfoActive ? t('vfo.active') : t('vfo.activate', 'Activate')}
            </ToggleButton>
        </Tooltip>
    );
};

/**
 * VFO Mute Button Component
 */
export const VfoMuteButton = ({ vfoIndex, vfoActive, vfoMuted, onMuteToggle }) => {
    const { t } = useTranslation('waterfall');

    return (
        <Tooltip title={vfoMuted ? "Unmute VFO audio" : "Mute VFO audio"} arrow>
            <span>
                <ToggleButton
                    value="listen"
                    selected={!vfoMuted}
                    disabled={!vfoActive}
                    onChange={() => onMuteToggle(vfoIndex)}
                    sx={{
                        flex: 1,
                        height: '32px',
                        fontSize: '0.8rem',
                        border: '1px solid',
                        borderColor: (theme) => vfoMuted
                            ? alpha(theme.palette.warning.main, 0.6)
                            : theme.palette.border.main,
                        borderRadius: '4px',
                        color: 'text.secondary',
                        textTransform: 'none',
                        backgroundColor: (theme) => vfoMuted
                            ? alpha(theme.palette.warning.main, theme.palette.mode === 'dark' ? 0.16 : 0.12)
                            : theme.palette.state.disabledBg,
                        transition: 'all 0.2s ease-in-out',
                        '&.Mui-selected': {
                            backgroundColor: 'primary.main',
                            color: 'primary.contrastText',
                            borderColor: 'primary.main',
                            fontWeight: 600,
                            boxShadow: (theme) => `0 0 8px ${alpha(theme.palette.primary.main, 0.4)}`,
                            '&:hover': {
                                backgroundColor: 'primary.dark',
                                boxShadow: (theme) => `0 0 12px ${alpha(theme.palette.primary.main, 0.6)}`,
                            }
                        },
                        '&:hover': {
                            backgroundColor: (theme) => vfoMuted
                                ? alpha(theme.palette.warning.main, theme.palette.mode === 'dark' ? 0.24 : 0.18)
                                : theme.palette.state.hover,
                            borderColor: (theme) => vfoMuted
                                ? alpha(theme.palette.warning.main, 0.8)
                                : theme.palette.border.dark,
                        },
                        '&.Mui-disabled': {
                            backgroundColor: (theme) => theme.palette.state.disabledBg,
                            borderColor: (theme) => theme.palette.border.dark,
                            color: (theme) => theme.palette.state.disabled,
                            opacity: 0.5,
                        }
                    }}
                >
                    {!vfoMuted ? t('vfo.mute', 'Mute') : t('vfo.muted', 'Muted')}
                </ToggleButton>
            </span>
        </Tooltip>
    );
};

/**
 * VFO Frequency Display Component
 */
export const VfoFrequencyDisplay = ({ frequency }) => {
    return (
        <Box sx={{
            mt: 2,
            mb: 0,
            width: '100%',
            typography: 'body1',
            fontWeight: 'medium',
            alignItems: 'center'
        }}>
            <Box
                sx={{
                    width: '100%',
                    fontFamily: "Monospace",
                    color: 'info.main',
                    alignItems: 'center',
                    textAlign: 'center',
                    justifyContent: 'center'
                }}>
                <LCDFrequencyDisplay
                    frequency={frequency}
                    size={"large"} />
            </Box>
        </Box>
    );
};
