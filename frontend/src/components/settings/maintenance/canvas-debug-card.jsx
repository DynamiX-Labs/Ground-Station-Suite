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
import { Typography, Divider } from '@mui/material';
import Grid from '@mui/material/Grid';

const CanvasDebugCard = () => {
    return (
        <>
            <Typography variant="h6" gutterBottom>
                Canvas Rendering Debug Information
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Information about canvas rendering environment for debugging text distortion issues
            </Typography>

            <Grid container spacing={2} columns={16}>
                <Grid size={16}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                        Display Information
                    </Typography>
                    <Divider sx={{ mb: 1 }} />
                </Grid>

                <Grid size={8}>
                    Device Pixel Ratio
                    <Typography variant="body2" color="text.secondary">
                        Scale factor between CSS pixels and physical pixels
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="h6" color="primary">
                        {window.devicePixelRatio || 'N/A'}
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Window Inner Dimensions
                    <Typography variant="body2" color="text.secondary">
                        Viewport width and height in CSS pixels
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {window.innerWidth} × {window.innerHeight} px
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Screen Resolution
                    <Typography variant="body2" color="text.secondary">
                        Physical screen dimensions
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {window.screen.width} × {window.screen.height} px
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Available Screen Space
                    <Typography variant="body2" color="text.secondary">
                        Screen size minus OS toolbars/taskbar
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {window.screen.availWidth} × {window.screen.availHeight} px
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Color Depth
                    <Typography variant="body2" color="text.secondary">
                        Bits per pixel for color representation
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {window.screen.colorDepth} bits
                    </Typography>
                </Grid>

                <Grid size={16}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                        Browser Information
                    </Typography>
                    <Divider sx={{ mb: 1 }} />
                </Grid>

                <Grid size={8}>
                    User Agent
                    <Typography variant="body2" color="text.secondary">
                        Browser identification string
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body2" sx={{ wordBreak: 'break-word' }}>
                        {navigator.userAgent}
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Platform
                    <Typography variant="body2" color="text.secondary">
                        Operating system platform
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {navigator.platform}
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Language
                    <Typography variant="body2" color="text.secondary">
                        Browser language setting
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {navigator.language}
                    </Typography>
                </Grid>

                <Grid size={16}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom sx={{ mt: 2 }}>
                        Hardware Information
                    </Typography>
                    <Divider sx={{ mb: 1 }} />
                </Grid>

                <Grid size={8}>
                    Hardware Concurrency
                    <Typography variant="body2" color="text.secondary">
                        Number of logical processor cores
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {navigator.hardwareConcurrency || 'N/A'} cores
                    </Typography>
                </Grid>

                <Grid size={8}>
                    Max Touch Points
                    <Typography variant="body2" color="text.secondary">
                        Maximum simultaneous touch points supported
                    </Typography>
                </Grid>
                <Grid size={8}>
                    <Typography variant="body1">
                        {navigator.maxTouchPoints || 0}
                    </Typography>
                </Grid>
            </Grid>
        </>
    );
};

export default CanvasDebugCard;
