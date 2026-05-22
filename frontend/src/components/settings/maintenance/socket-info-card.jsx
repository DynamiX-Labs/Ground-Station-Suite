/**
 * @license
 * Copyright (c) 2025 Efstratios Goudelis
 * Modifications and extensions Copyright (C) 2026 DynamiX-Labs
 */

import React from 'react';
import { Typography, Divider } from '@mui/material';
import Grid from '@mui/material/Grid';
import { useSocket } from "../../common/socket.jsx";

const SocketInfoCard = () => {
    const { socket } = useSocket();

    return (
        <>
            <Typography variant="h6" gutterBottom>
                Socket.IO Connection Information
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Real-time WebSocket connection status and diagnostics
            </Typography>

            <Grid container spacing={2} columns={16}>
                <Grid size={16}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Connection Status
                    </Typography>
                    <Divider sx={{ mb: 1 }} />
                </Grid>

                <Grid size={8}>
                    Session ID
                    <Typography variant="body2" color="text.secondary">
                        Socket.IO client session identifier
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1" sx={{ wordBreak: 'break-word', fontFamily: 'monospace' }}>
                        {socket?.id || 'Not connected'}
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Connected
                    <Typography variant="body2" color="text.secondary">
                        Socket connection status
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1" fontWeight="bold" color={socket?.connected ? 'success.main' : 'error.main'}>
                        {socket?.connected ? 'Yes' : 'No'}
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Engine Ready State
                    <Typography variant="body2" color="text.secondary">
                        Socket engine connection state
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {socket?.io?.engine?.readyState || 'N/A'}
                    </Typography>
                </Grid>

                <Grid size={16}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                        Connection Details
                    </Typography>
                    <Divider sx={{ mb: 1 }} />
                </Grid>

                <Grid size={8}>
                    Transport
                    <Typography variant="body2" color="text.secondary">
                        Socket.IO transport protocol
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {socket?.io?.engine?.transport?.name || 'N/A'}
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Backend URL
                    <Typography variant="body2" color="text.secondary">
                        WebSocket server URL
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body2" sx={{ wordBreak: 'break-word', fontFamily: 'monospace' }}>
                        {socket?.io?.uri || 'N/A'}
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Reconnection Attempts
                    <Typography variant="body2" color="text.secondary">
                        Number of reconnection attempts
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {socket?.io?._reconnectionAttempts || 0}
                    </Typography>
                </Grid>
            </Grid>
        </>
    );
};

export default SocketInfoCard;
