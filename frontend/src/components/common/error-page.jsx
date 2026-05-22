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


import React from 'react';
import { useNavigate, useRouteError } from 'react-router-dom';
import {
    Alert,
    Box,
    Button,
    Container,
    Divider,
    Paper,
    Stack,
    Typography,
} from '@mui/material';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import HomeIcon from '@mui/icons-material/Home';
import RefreshIcon from '@mui/icons-material/Refresh';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';

const ErrorPage = () => {
    const error = useRouteError();
    const navigate = useNavigate();
    const [showStack, setShowStack] = React.useState(false);
    const [copyState, setCopyState] = React.useState('idle');
    const isDev = import.meta.env.DEV;
    const status = error?.status || 500;
    const title = status === 404 ? 'Page Not Found' : 'Application Error';
    const subtitle = error?.statusText || 'Something went wrong while loading this page.';
    const message = isDev
        ? (error?.message || 'An unexpected error has occurred, please try again later.')
        : 'Please try refreshing the page. If the problem persists, check backend connectivity.';
    const stackText = error?.stack || 'No stack trace available.';
    const stackLines = stackText.split('\n').filter((line) => line.trim().length > 0);
    const debugDetails = `Message: ${message}\n\nStack trace:\n${stackText}`;

    const handleCopyDetails = React.useCallback(async () => {
        try {
            await navigator.clipboard.writeText(debugDetails);
            setCopyState('copied');
            window.setTimeout(() => setCopyState('idle'), 1500);
        } catch {
            setCopyState('failed');
            window.setTimeout(() => setCopyState('idle'), 2000);
        }
    }, [debugDetails]);

    return (
        <Container
            maxWidth="md"
            sx={{
                display: 'flex',
                minHeight: '100vh',
                alignItems: 'center',
                justifyContent: 'center',
                py: 4,
            }}
        >
            <Paper elevation={4} sx={{ width: '100%', p: { xs: 2.5, sm: 4 }, borderRadius: 2 }}>
                <Stack spacing={2.5}>
                    <Stack direction="row" spacing={1.5} alignItems="center">
                        <ErrorOutlineIcon color="error" sx={{ fontSize: 30 }} />
                        <Box>
                            <Typography variant="h5" sx={{ fontWeight: 700 }}>
                                {title}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Error code: {status}
                            </Typography>
                        </Box>
                    </Stack>

                    <Divider />

                    <Alert severity="error" variant="outlined">
                        {subtitle}
                    </Alert>

                    <Typography variant="body1" color="text.secondary">
                        {message}
                    </Typography>

                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                        <Button
                            variant="contained"
                            startIcon={<HomeIcon />}
                            onClick={() => navigate('/')}
                        >
                            Back to Home
                        </Button>
                        <Button
                            variant="outlined"
                            startIcon={<RefreshIcon />}
                            onClick={() => window.location.reload()}
                        >
                            Reload Page
                        </Button>
                    </Stack>

                    {isDev && (
                        <Box>
                            <Button
                                variant="text"
                                size="small"
                                onClick={() => setShowStack(prev => !prev)}
                                sx={{ textTransform: 'none', px: 0 }}
                            >
                                {showStack ? 'Hide Debug Details' : 'Show Debug Details'}
                            </Button>
                            {showStack && (
                                <Box
                                    sx={{
                                        mt: 1,
                                        borderRadius: 1.5,
                                        border: '1px solid',
                                        borderColor: 'divider',
                                        overflow: 'hidden',
                                        bgcolor: 'background.default',
                                    }}
                                >
                                    <Box
                                        sx={{
                                            px: 1.5,
                                            py: 1,
                                            borderBottom: '1px solid',
                                            borderColor: 'divider',
                                            bgcolor: 'action.hover',
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                        }}
                                    >
                                        <Typography variant="caption" sx={{ fontWeight: 600 }}>
                                            Error Details
                                        </Typography>
                                        <Stack direction="row" spacing={1} alignItems="center">
                                            <Typography variant="caption" color="text.secondary">
                                                {stackLines.length} line{stackLines.length === 1 ? '' : 's'}
                                            </Typography>
                                            <Button
                                                size="small"
                                                variant="outlined"
                                                color={copyState === 'failed' ? 'error' : 'primary'}
                                                startIcon={<ContentCopyIcon />}
                                                onClick={handleCopyDetails}
                                                sx={{ textTransform: 'none', minWidth: 0, px: 1 }}
                                            >
                                                {copyState === 'copied' ? 'Copied' : copyState === 'failed' ? 'Copy failed' : 'Copy details'}
                                            </Button>
                                        </Stack>
                                    </Box>
                                    <Box
                                        sx={{
                                            overflow: 'auto',
                                            maxHeight: 320,
                                            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                            fontSize: 12,
                                        }}
                                    >
                                        <Box
                                            sx={{
                                                display: 'grid',
                                                gridTemplateColumns: '40px 1fr',
                                                columnGap: 1,
                                                px: 1.5,
                                                py: 0.4,
                                                borderBottom: '1px solid',
                                                borderColor: 'divider',
                                                '&:hover': { bgcolor: 'action.hover' },
                                            }}
                                        >
                                            <Typography
                                                component="span"
                                                sx={{
                                                    color: 'text.disabled',
                                                    textAlign: 'right',
                                                    userSelect: 'none',
                                                    fontSize: 12,
                                                }}
                                            >
                                                msg
                                            </Typography>
                                            <Typography
                                                component="pre"
                                                sx={{
                                                    m: 0,
                                                    whiteSpace: 'pre-wrap',
                                                    wordBreak: 'break-word',
                                                    color: 'error.main',
                                                    fontSize: 12,
                                                    lineHeight: 1.45,
                                                }}
                                            >
                                                {message}
                                            </Typography>
                                        </Box>
                                        {stackLines.map((line, idx) => (
                                            <Box
                                                key={`${idx}-${line}`}
                                                sx={{
                                                    display: 'grid',
                                                    gridTemplateColumns: '40px 1fr',
                                                    columnGap: 1,
                                                    px: 1.5,
                                                    py: 0.4,
                                                    borderBottom: idx === stackLines.length - 1 ? 'none' : '1px solid',
                                                    borderColor: 'divider',
                                                    '&:hover': { bgcolor: 'action.hover' },
                                                }}
                                            >
                                                <Typography
                                                    component="span"
                                                    sx={{
                                                        color: 'text.disabled',
                                                        textAlign: 'right',
                                                        userSelect: 'none',
                                                        fontSize: 12,
                                                    }}
                                                >
                                                    {idx + 1}
                                                </Typography>
                                                <Typography
                                                    component="pre"
                                                    sx={{
                                                        m: 0,
                                                        whiteSpace: 'pre-wrap',
                                                        wordBreak: 'break-word',
                                                        color: idx === 0 ? 'error.main' : 'text.primary',
                                                        fontSize: 12,
                                                        lineHeight: 1.45,
                                                    }}
                                                >
                                                    {line}
                                                </Typography>
                                            </Box>
                                        ))}
                                    </Box>
                                </Box>
                            )}
                        </Box>
                    )}
                </Stack>
            </Paper>
        </Container>
    );
};

export default ErrorPage;
