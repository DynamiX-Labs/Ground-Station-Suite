import React from 'react';
import { Box, CircularProgress, IconButton, Paper, Stack, Tooltip, Typography } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import FitScreenIcon from '@mui/icons-material/FitScreen';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import { ResetZoomIcon } from '../common/custom-icons.jsx';

const CelestialToolbar = ({
    onRefresh,
    onFitAll,
    onZoomIn,
    onZoomOut,
    onZoomReset,
    loading,
    loadingText = '',
    disabled = false,
}) => {
    return (
        <Paper
            elevation={1}
            sx={{
                p: 0,
                display: 'inline-block',
                width: '100%',
                borderBottom: '1px solid',
                borderColor: 'border.main',
                borderRadius: 0,
            }}
        >
            <Box
                sx={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    overflowX: 'auto',
                    msOverflowStyle: 'none',
                    scrollbarWidth: 'none',
                    '&::-webkit-scrollbar': { display: 'none' },
                }}
            >
                <Box sx={{ overflowX: 'auto', minWidth: 0, flex: 1 }}>
                    <Stack direction="row" spacing={0} sx={{ minWidth: 'min-content', flexWrap: 'nowrap' }}>
                        <Tooltip title="Fit all">
                            <span>
                                <IconButton
                                    onClick={onFitAll}
                                    disabled={disabled}
                                    color="primary"
                                    sx={{ borderRadius: 0 }}
                                >
                                    <FitScreenIcon />
                                </IconButton>
                            </span>
                        </Tooltip>
                        <Tooltip title="Zoom in">
                            <span>
                                <IconButton
                                    onClick={onZoomIn}
                                    disabled={disabled}
                                    color="primary"
                                    sx={{ borderRadius: 0 }}
                                >
                                    <ZoomInIcon />
                                </IconButton>
                            </span>
                        </Tooltip>
                        <Tooltip title="Zoom out">
                            <span>
                                <IconButton
                                    onClick={onZoomOut}
                                    disabled={disabled}
                                    color="primary"
                                    sx={{ borderRadius: 0 }}
                                >
                                    <ZoomOutIcon />
                                </IconButton>
                            </span>
                        </Tooltip>
                        <Tooltip title="Reset zoom">
                            <span>
                                <IconButton
                                    onClick={onZoomReset}
                                    disabled={disabled}
                                    color="primary"
                                    sx={{ borderRadius: 0 }}
                                >
                                    <ResetZoomIcon />
                                </IconButton>
                            </span>
                        </Tooltip>
                        <Tooltip title="Refresh celestial scene">
                            <span>
                                <IconButton
                                    onClick={onRefresh}
                                    disabled={disabled || loading}
                                    color="primary"
                                    sx={{ borderRadius: 0 }}
                                >
                                    <RefreshIcon />
                                </IconButton>
                            </span>
                        </Tooltip>
                    </Stack>
                </Box>
                <Box sx={{ px: 1.25, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', minWidth: 32, gap: 0.75 }}>
                    {loading && loadingText ? (
                        <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1 }}>
                            {loadingText}
                        </Typography>
                    ) : null}
                    {loading ? <CircularProgress size={16} /> : null}
                </Box>
            </Box>
        </Paper>
    );
};

export default React.memo(CelestialToolbar);
