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


import React, { useEffect, useRef, useState } from 'react';
import {getClassNamesBasedOnGridEditing, TitleBar} from "./common.jsx";
import { FormControl, InputLabel, MenuItem, Select, Button,
    CircularProgress, Slider, Stack, IconButton, Box, Typography } from "@mui/material";
import Grid from "@mui/material/Grid";
import { v4 as uuidv4 } from 'uuid';
import ReplayIcon from '@mui/icons-material/Replay';
import {useDispatch, useSelector} from 'react-redux';
import {
    setSelectedCameraId
} from "../hardware/camera-slice.jsx";
import VideoWebRTCPlayer from './video-webrtc.jsx';
import CameraAltIcon from '@mui/icons-material/CameraAlt';

const CameraView = () => {
    const dispatch = useDispatch();
    const {
        cameras,
        selectedCameraId,
        selectedCamera,
        setSelectedCamera,
    } = useSelector((state) => state.cameras);

    const {gridEditable} = useSelector((state) => state.targetSatTrack);

    useEffect(() => {
        if (cameras.length === 1 && !selectedCameraId) {
            dispatch(setSelectedCameraId(cameras[0].id));
        }
        return () => {
        };
    }, [cameras]);

    const handleCameraChange = (event) => {
        const cameraId = event.target.value;
        dispatch(setSelectedCameraId(cameraId));
    };

    return (
        <>
            <TitleBar className={getClassNamesBasedOnGridEditing(gridEditable, ["window-title-bar"])}>Camera
                view</TitleBar>
            <Grid container spacing={{xs: 1, md: 1}} columns={{xs: 12, sm: 12, md: 12}}>
                <Grid size={{xs: 12, sm: 12, md: 12}} style={{padding: '0.5rem 0.5rem 0rem 0.5rem'}}>
                    <FormControl size="small" variant={"filled"} fullWidth={true}
                                 sx={{minWidth: 200, marginTop: 0.5, marginBottom: 1}}>
                        <InputLabel htmlFor={"camera-select"} id="camera-select">camera</InputLabel>
                        <Select
                            labelId="camera-select"
                            value={cameras.length > 0 ? selectedCameraId : 'none'}
                            onChange={(e) => {
                                handleCameraChange(e);
                            }}
                            label="select camera"
                            variant={'filled'}>
                            <MenuItem value="none">
                                <em>[no camera]</em>
                            </MenuItem>
                            {cameras.map((camera) => (
                                <MenuItem key={camera.id} value={camera.id}>
                                    {camera.name}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Grid>

                {selectedCamera['type'] === 'webrtc' && (
                    <React.Suspense fallback={<CircularProgress/>}>
                        <VideoWebRTCPlayer src={selectedCamera['url']}/>
                    </React.Suspense>
                )}
                {selectedCamera['type'] === 'hls' && (
                    <React.Suspense fallback={<CircularProgress/>}>
                    </React.Suspense>
                )}
                {selectedCamera['type'] === 'mjpeg' && (
                    <React.Suspense fallback={<CircularProgress/>}>
                    </React.Suspense>
                )}
                {selectedCamera['type'] === '' && (
                    <Box display="flex" justifyContent="center" alignItems="center" margin="auto" height="100vh">
                        <CameraAltIcon style={{fontSize: '4rem', color: 'gray'}}/>
                    </Box>
                )}
            </Grid>
        </>
    );
};

export default CameraView;