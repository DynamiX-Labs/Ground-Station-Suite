
import CloudOffIcon from '@mui/icons-material/CloudOff';
import SyncProblemIcon from '@mui/icons-material/SyncProblem';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import { keyframes } from '@emotion/react';
import { Backdrop, Box, LinearProgress, Typography, useTheme } from "@mui/material";
import { alpha } from '@mui/material/styles';
import { useSelector } from "react-redux";
import { useTranslation } from 'react-i18next';

// Minimal animations
const fadeIn = keyframes`
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
`;

function ConnectionOverlay() {
    const { t } = useTranslation('dashboard');
    const theme = useTheme();
    const {
        connecting,
        connected,
        disconnected,
        reConnectAttempt,
        connectionError,
        initialDataLoading,
        initialDataProgress,
    } = useSelector((state) => state.dashboard);

    // Don't show overlay if connected
    if (connected && !connecting && !initialDataLoading) {
        return null;
    }

    // Determine the status and styling with industrial colors
    const getConnectionStatus = () => {
        if (connectionError) {
            return {
                icon: ErrorOutlineIcon,
                title: t('connection.connection_failed'),
                message: t('connection.network_error'),
                tone: 'error',
            };
        }

        if (initialDataLoading) {
            return {
                icon: SyncProblemIcon,
                title: t('connection.syncing_data', 'Syncing data'),
                message: t('connection.loading_initial_state', 'Loading initial application data'),
                tone: 'success',
            };
        }

        if (reConnectAttempt > 0) {
            return {
                icon: SyncProblemIcon,
                title: t('connection.reconnecting'),
                message: t('connection.attempt', { count: reConnectAttempt }),
                tone: 'warning',
            };
        }

        if (connecting || disconnected) {
            return {
                icon: CloudOffIcon,
                title: t('connection.connecting'),
                message: t('connection.establishing_connection'),
                tone: 'info',
            };
        }

        return null;
    };

    const status = getConnectionStatus();

    if (!status) {
        return null;
    }

    const toneColor = theme.palette[status.tone]?.main || theme.palette.text.secondary;
    const toneSurface = theme.palette.statusSurface?.[status.tone] || theme.palette.surface.raised;
    const toneBorder = alpha(toneColor, theme.palette.mode === 'dark' ? 0.6 : 0.45);
    const StatusIcon = status.icon;

    return (
        <Backdrop
            open={true}
            sx={{
                zIndex: (theme) => theme.zIndex.drawer + 1,
                backgroundColor: theme.palette.surface.scrim,
                backdropFilter: 'blur(4px)'
            }}
        >
            <Box
                sx={{
                    animation: `${fadeIn} 0.2s ease-out`,
                    backgroundColor: toneSurface,
                    border: `1px solid ${toneBorder}`,
                    borderRadius: 1,
                    padding: 3,
                    minWidth: 280,
                    maxWidth: 320,
                    boxShadow: theme.palette.mode === 'dark'
                        ? '0 8px 24px rgba(0, 0, 0, 0.45)'
                        : '0 8px 24px rgba(15, 23, 42, 0.16)',
                }}
            >
                {/* Header */}
                <Box sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    mb: 2,
                }}>
                    <StatusIcon sx={{ fontSize: 24, color: toneColor }} />
                    <Box sx={{ flex: 1 }}>
                        <Typography
                            variant="subtitle1"
                            sx={{
                                color: 'text.primary',
                                fontWeight: 500,
                                mb: 0.5,
                                fontSize: '1rem'
                            }}
                        >
                            {status.title}
                        </Typography>
                        <Typography
                            variant="body2"
                            sx={{
                                color: 'text.secondary',
                                fontSize: '0.875rem'
                            }}
                        >
                            {status.message}
                        </Typography>
                    </Box>
                </Box>

                {/* Progress indicator */}
                {initialDataLoading && initialDataProgress.total > 0 ? (
                    <>
                        <LinearProgress
                            variant="determinate"
                            value={(initialDataProgress.completed / initialDataProgress.total) * 100}
                            sx={{
                                height: 4,
                                borderRadius: 1,
                                backgroundColor: (theme) => theme.palette.state.disabledBg,
                                '& .MuiLinearProgress-bar': {
                                    backgroundColor: toneColor,
                                },
                            }}
                        />
                        <Typography
                            variant="caption"
                            sx={{
                                color: 'text.secondary',
                                fontSize: '0.75rem',
                                display: 'block',
                                textAlign: 'center',
                                mt: 1,
                            }}
                        >
                            {t('connection.loading_progress', 'Loaded {{completed}} of {{total}}', {
                                completed: initialDataProgress.completed,
                                total: initialDataProgress.total,
                            })}
                        </Typography>
                    </>
                ) : (
                    <Box
                        sx={{
                            width: '100%',
                            height: 2,
                            backgroundColor: (theme) => theme.palette.state.disabledBg,
                            borderRadius: 1,
                            overflow: 'hidden',
                            position: 'relative'
                        }}
                    >
                        <Box
                            sx={{
                                height: '100%',
                                width: '30%',
                                backgroundColor: toneColor,
                                borderRadius: 1,
                                animation: `${keyframes`
                                    0% { transform: translateX(-100%); }
                                    100% { transform: translateX(333%); }
                                `} 2s infinite ease-in-out`,
                            }}
                        />
                    </Box>
                )}

                {/* Status text */}
                <Typography
                    variant="caption"
                    sx={{
                        color: 'text.secondary',
                        fontFamily: 'monospace',
                        fontSize: '0.75rem',
                        display: 'block',
                        textAlign: 'center',
                        mt: 1.5,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                    }}
                >
                    {/*{connectionError ? 'ERROR' :*/}
                    {/*    reConnectAttempt > 0 ? 'RECONNECTING' : 'CONNECTING'}*/}
                </Typography>
            </Box>
        </Backdrop>
    );
}

export default ConnectionOverlay;
