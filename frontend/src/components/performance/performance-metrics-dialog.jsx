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

import React, { useEffect, useState } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    IconButton,
    Box,
    Typography,
    Chip,
    Button,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import { useSelector, useDispatch } from 'react-redux';
import { setDialogOpen } from './performance-slice.jsx';
import { useSocket } from '../common/socket.jsx';
import PerformanceFlow from './performance-flow.jsx';

const PerformanceMetricsDialog = () => {
    const dispatch = useDispatch();
    const { socket } = useSocket();
    const open = useSelector((state) => state.performance.dialogOpen);
    const metrics = useSelector((state) => state.performance.latestMetrics);
    const connected = useSelector((state) => state.performance.connected);
    const [autoArrangeHandler, setAutoArrangeHandler] = useState(null);

    // Start monitoring when dialog opens, stop when it closes
    useEffect(() => {
        if (open && socket) {
            socket.emit('start-monitoring');
        }

        return () => {
            if (socket) {
                socket.emit('stop-monitoring');
            }
        };
    }, [open, socket]);

    // Close dialog when socket disconnects
    useEffect(() => {
        if (!socket) return;

        const handleDisconnect = () => {
            if (open) {
                dispatch(setDialogOpen(false));
            }
        };

        socket.on('disconnect', handleDisconnect);

        return () => {
            socket.off('disconnect', handleDisconnect);
        };
    }, [socket, open, dispatch]);

    const handleClose = () => {
        dispatch(setDialogOpen(false));
    };

    const handleAutoArrange = () => {
        if (autoArrangeHandler) {
            autoArrangeHandler();
        }
    };

    return (
        <Dialog
            open={open}
            onClose={handleClose}
            maxWidth="xl"
            fullWidth
            PaperProps={{
                sx: {
                    height: '90vh',
                    backgroundColor: (theme) => theme.palette.background?.paper || theme.palette.background.paper,
                    backgroundImage: 'none',
                }
            }}
        >
            <DialogTitle
                sx={{
                    borderBottom: 1,
                    borderColor: (theme) => theme.palette.border?.main || 'divider',
                    backgroundColor: (theme) => theme.palette.background?.elevated || theme.palette.background.default,
                    py: 1.5,
                    px: 2,
                }}
            >
                <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Box display="flex" flexDirection="column" gap={0.5}>
                        <Typography variant="h6">System Topology</Typography>
                        <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ opacity: 0.7, fontSize: '0.75rem' }}
                        >
                            Real-time visualization of system components and data flow
                        </Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1}>
                        <Button
                            variant="outlined"
                            size="small"
                            startIcon={<AutorenewIcon />}
                            onClick={handleAutoArrange}
                            disabled={!metrics}
                        >
                            Auto Arrange
                        </Button>
                        <IconButton onClick={handleClose} size="small">
                            <CloseIcon />
                        </IconButton>
                    </Box>
                </Box>
            </DialogTitle>
            <DialogContent
                dividers
                sx={{
                    backgroundColor: (theme) => theme.palette.background?.default || theme.palette.background.default,
                    borderColor: (theme) => theme.palette.border?.main || 'divider',
                    position: 'relative',
                    p: 0,
                    height: 'calc(90vh - 80px)', // Account for title height
                }}
            >
                {!metrics ? (
                    <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                        <Typography variant="body1" color="text.secondary">
                            Waiting for metrics data...
                        </Typography>
                    </Box>
                ) : (
                    <PerformanceFlow 
                        metrics={metrics} 
                        onAutoArrangeCallback={(handler) => setAutoArrangeHandler(() => handler)}
                    />
                )}
            </DialogContent>
        </Dialog>
    );
};

export default PerformanceMetricsDialog;
