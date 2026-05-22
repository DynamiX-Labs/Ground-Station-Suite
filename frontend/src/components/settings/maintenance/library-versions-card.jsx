/**
 * @license
 * Copyright (c) 2025 Efstratios Goudelis
 * Modifications and extensions Copyright (C) 2026 DynamiX-Labs
 */

import React, { useState, useEffect } from 'react';
import { Typography, Divider, Button, Alert, CircularProgress, Box, Tabs, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useSocket } from "../../common/socket.jsx";
import { useDispatch, useSelector } from 'react-redux';
import { fetchLibraryVersions, fetchFrontendLibraryVersions } from '../library-versions-slice.jsx';

const LibraryVersionsCard = () => {
    const { socket } = useSocket();
    const dispatch = useDispatch();
    const libraryVersions = useSelector((state) => state.libraryVersions);
    const [libraryVersionsTab, setLibraryVersionsTab] = useState(0);

    // Load library versions on component mount
    useEffect(() => {
        if (socket && socket.connected) {
            if (Object.keys(libraryVersions.backend.categories).length === 0 && !libraryVersions.backend.loading) {
                dispatch(fetchLibraryVersions({ socket }));
            }
            if (Object.keys(libraryVersions.frontend.categories).length === 0 && !libraryVersions.frontend.loading) {
                dispatch(fetchFrontendLibraryVersions({ socket }));
            }
        }
    }, [socket, dispatch, libraryVersions.backend.categories, libraryVersions.backend.loading, libraryVersions.frontend.categories, libraryVersions.frontend.loading]);

    const handleRefreshLibraryVersions = () => {
        if (socket && socket.connected) {
            dispatch(fetchLibraryVersions({ socket }));
        }
    };

    const handleRefreshFrontendLibraryVersions = () => {
        if (socket && socket.connected) {
            dispatch(fetchFrontendLibraryVersions({ socket }));
        }
    };

    return (
        <>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                    Library Versions
                </Typography>
                <Button
                    variant="outlined"
                    size="small"
                    startIcon={
                        (libraryVersionsTab === 0 ? libraryVersions.backend.loading : libraryVersions.frontend.loading)
                        ? <CircularProgress size={16} />
                        : <RefreshIcon />
                    }
                    onClick={libraryVersionsTab === 0 ? handleRefreshLibraryVersions : handleRefreshFrontendLibraryVersions}
                    disabled={libraryVersionsTab === 0 ? libraryVersions.backend.loading : libraryVersions.frontend.loading}
                >
                    Refresh
                </Button>
            </Box>
            <Divider sx={{ mb: 2 }} />

            <Tabs value={libraryVersionsTab} onChange={(e, newValue) => setLibraryVersionsTab(newValue)} sx={{ mb: 2 }}>
                <Tab label="Backend" />
                <Tab label="Frontend" />
            </Tabs>

            {/* Backend Tab */}
            {libraryVersionsTab === 0 && (
                <>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Versions of installed backend libraries and dependencies
                    </Typography>

                    {libraryVersions.backend.error && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                            {libraryVersions.backend.error}
                        </Alert>
                    )}

                    {libraryVersions.backend.loading && !Object.keys(libraryVersions.backend.categories).length ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                            <CircularProgress />
                        </Box>
                    ) : (
                        <>
                            {Object.keys(libraryVersions.backend.categories).length > 0 ? (
                                <>
                                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                        Total libraries: <strong>{libraryVersions.backend.totalCount}</strong>
                                    </Typography>
                                    <TableContainer>
                                        <Table size="small">
                                            <TableHead>
                                                <TableRow>
                                                    <TableCell><strong>Category</strong></TableCell>
                                                    <TableCell><strong>Library</strong></TableCell>
                                                    <TableCell><strong>Description</strong></TableCell>
                                                    <TableCell><strong>Version</strong></TableCell>
                                                </TableRow>
                                            </TableHead>
                                            <TableBody>
                                                {Object.entries(libraryVersions.backend.categories).map(([category, libraries]) => (
                                                    libraries.map((lib, index) => (
                                                        <TableRow key={lib.key} hover>
                                                            <TableCell sx={{ textTransform: 'capitalize' }}>
                                                                {index === 0 ? category : ''}
                                                            </TableCell>
                                                            <TableCell>
                                                                {lib.name}
                                                            </TableCell>
                                                            <TableCell>
                                                                <Typography variant="body2" color="text.secondary">
                                                                    {lib.description}
                                                                </Typography>
                                                            </TableCell>
                                                            <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                                                                {lib.version}
                                                            </TableCell>
                                                        </TableRow>
                                                    ))
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </TableContainer>
                                </>
                            ) : (
                                <Alert severity="info">
                                    No backend library version information available
                                </Alert>
                            )}
                        </>
                    )}
                </>
            )}

            {/* Frontend Tab */}
            {libraryVersionsTab === 1 && (
                <>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Versions of frontend packages from package.json
                    </Typography>

                    {libraryVersions.frontend.error && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                            {libraryVersions.frontend.error}
                        </Alert>
                    )}

                    {libraryVersions.frontend.loading && !Object.keys(libraryVersions.frontend.categories).length ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                            <CircularProgress />
                        </Box>
                    ) : (
                        <>
                            {Object.keys(libraryVersions.frontend.categories).length > 0 ? (
                                <>
                                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                        Total packages: <strong>{libraryVersions.frontend.totalCount}</strong>
                                    </Typography>
                                    <TableContainer>
                                        <Table size="small">
                                            <TableHead>
                                                <TableRow>
                                                    <TableCell><strong>Category</strong></TableCell>
                                                    <TableCell><strong>Package</strong></TableCell>
                                                    <TableCell><strong>Description</strong></TableCell>
                                                    <TableCell><strong>Version</strong></TableCell>
                                                </TableRow>
                                            </TableHead>
                                            <TableBody>
                                                {Object.entries(libraryVersions.frontend.categories).map(([category, libraries]) => (
                                                    libraries.map((lib, index) => (
                                                        <TableRow key={lib.key} hover>
                                                            <TableCell sx={{ textTransform: 'capitalize' }}>
                                                                {index === 0 ? category : ''}
                                                            </TableCell>
                                                            <TableCell>
                                                                {lib.name}
                                                            </TableCell>
                                                            <TableCell>
                                                                <Typography variant="body2" color="text.secondary">
                                                                    {lib.description}
                                                                </Typography>
                                                            </TableCell>
                                                            <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                                                                {lib.version}
                                                            </TableCell>
                                                        </TableRow>
                                                    ))
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </TableContainer>
                                </>
                            ) : (
                                <Alert severity="info">
                                    No frontend library version information available
                                </Alert>
                            )}
                        </>
                    )}
                </>
            )}
        </>
    );
};

export default LibraryVersionsCard;
