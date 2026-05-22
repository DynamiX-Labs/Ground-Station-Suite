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
import { FormControl, InputLabel, MenuItem, Select, Button, CircularProgress, Slider, Stack, IconButton, Box, Typography } from "@mui/material";
import Grid from "@mui/material/Grid";
import { v4 as uuidv4 } from 'uuid';
import ReplayIcon from '@mui/icons-material/Replay';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import {useSelector} from 'react-redux';

const VideoWebRTCPlayer = ({ src, config = {} }) => {
    const videoRef = useRef(null);
    const videoContainerRef = useRef(null);
    const peerConnectionRef = useRef(null);
    const clientIdRef = useRef(uuidv4());
    const hideTimeoutRef = useRef(null);
    const [error, setError] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [cameras, setCameras] = useState([]);
    const [selectedCamera, setSelectedCamera] = useState("");
    const [isPlaying, setIsPlaying] = useState(true);
    const [showControls, setShowControls] = useState(false);
    const {gridEditable} = useSelector((state) => state.targetSatTrack);

    const RELAY_SERVER = `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
    const CONTROLS_HIDE_DELAY = 2000; // 2 seconds

    useEffect(() => {
        if (!videoRef.current || !src) return;

        // Clean up previous connection on component unmount
        return () => {
            if (peerConnectionRef.current) {
                peerConnectionRef.current.close();
                peerConnectionRef.current = null;
            }
        };
    }, []);

    useEffect(() => {
        connect().then(r => {
            console.info("Connected to WebRTC stream", r);
        });

        return () => {
            disconnect();
        };
    }, []);

    useEffect(() => {
        if (!videoRef.current || !src) return;

        // Connect to the new source URL when src changes
        connect().then(r => {
            console.info("Connected to WebRTC stream", r);
        });

        // Clean up previous connection when src changes or component unmounts
        return () => {
            disconnect();
        };
    }, [src]);

    // Add event listeners for playing and pausing
    useEffect(() => {
        const videoElement = videoRef.current;
        if (!videoElement) return;

        const handlePlay = () => {
            setIsPlaying(true);
            // When video starts playing, show controls briefly then hide
            setShowControls(true);
            startHideControlsTimer();
        };
        const handlePause = () => {
            setIsPlaying(false);
            // When video is paused/stopped, always show controls
            setShowControls(true);
            // Clear any hide timers
            if (hideTimeoutRef.current) {
                clearTimeout(hideTimeoutRef.current);
                hideTimeoutRef.current = null;
            }
        };

        videoElement.addEventListener('play', handlePlay);
        videoElement.addEventListener('pause', handlePause);

        return () => {
            videoElement.removeEventListener('play', handlePlay);
            videoElement.removeEventListener('pause', handlePause);
        };
    }, [videoRef.current]);

    // Clean up timeout on unmount
    useEffect(() => {
        return () => {
            if (hideTimeoutRef.current) {
                clearTimeout(hideTimeoutRef.current);
            }
        };
    }, []);

    // Start the timer to hide controls
    const startHideControlsTimer = () => {
        // Only start the timer if the video is playing
        if (isPlaying) {
            // Clear any existing timeout
            if (hideTimeoutRef.current) {
                clearTimeout(hideTimeoutRef.current);
            }

            // Set new timeout
            hideTimeoutRef.current = setTimeout(() => {
                setShowControls(false);
            }, CONTROLS_HIDE_DELAY);
        }
    };

    // Handle mouse enter/leave and control visibility
    const handleMouseEnter = () => {
        setShowControls(true);
        // Only set hide timer if video is playing
        if (isPlaying) {
            startHideControlsTimer();
        }
    };

    const handleMouseLeave = () => {
        // Only hide controls if video is playing
        if (isPlaying) {
            startHideControlsTimer();
        }
    };

    const handleMouseMove = () => {
        // Show controls on any mouse movement inside the video
        if (!showControls) {
            setShowControls(true);
        }

        // Only reset the hide timeout if video is playing
        if (isPlaying) {
            startHideControlsTimer();
        }
    };

    // Handle video toggle play/stop
    const handleTogglePlayStop = () => {
        const video = videoRef.current;
        if (!video) return;

        if (isPlaying) {
            video.pause();
            video.currentTime = 0;
            // The pause event will set isPlaying to false and ensure controls remain visible
        } else {
            video.play();
            // The play event will set isPlaying to true and start the hide timer
        }
    };

    // Handle reconnect/replay
    const handleReconnect = () => {
        connect();
    };

    const connect = async () => {
        try {
            setError(null);
            setIsLoading(true);

            // Create RTCPeerConnection
            const defaultConfig = {
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' },
                    { urls: 'stun:stun1.l.google.com:19302' }
                ],
                ...config
            };

            // Clean up any existing connection
            if (peerConnectionRef.current) {
                peerConnectionRef.current.close();
            }

            peerConnectionRef.current = new RTCPeerConnection(defaultConfig);
            const peerConnection = peerConnectionRef.current;

            // Set up event handlers
            peerConnection.ontrack = (event) => {
                if (videoRef.current && event.streams && event.streams[0]) {
                    videoRef.current.srcObject = event.streams[0];
                    setIsConnected(true);
                    setIsLoading(false);
                    setIsPlaying(true);
                    // Show controls initially when video loads, then hide after delay
                    setShowControls(true);
                    startHideControlsTimer();
                }
            };

            peerConnection.oniceconnectionstatechange = () => {
                if (peerConnection.iceConnectionState === 'failed' ||
                    peerConnection.iceConnectionState === 'disconnected') {
                    setError(`ICE connection ${peerConnection.iceConnectionState}`);
                    setIsLoading(false);
                }
            };

            // Create data channel (might be required by some servers)
            peerConnection.createDataChannel('video');

            // Create and set local description
            const offer = await peerConnection.createOffer({
                offerToReceiveAudio: false,
                offerToReceiveVideo: true
            });
            await peerConnection.setLocalDescription(offer);

            // Wait for ICE gathering to complete
            await new Promise(resolve => {
                if (peerConnection.iceGatheringState === 'complete') {
                    resolve();
                } else {
                    const checkState = () => {
                        if (peerConnection.iceGatheringState === 'complete') {
                            peerConnection.removeEventListener('icegatheringstatechange', checkState);
                            resolve();
                        }
                    };
                    peerConnection.addEventListener('icegatheringstatechange', checkState);
                    // Set a timeout to avoid hanging forever
                    setTimeout(resolve, 5000);
                }
            });

            // Send offer to relay server
            const response = await fetch(`${RELAY_SERVER}/api/webrtc/offer`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    source_url: src,
                    camera_id: selectedCamera || undefined,
                    type: peerConnection.localDescription.type,
                    sdp: peerConnection.localDescription.sdp
                })
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
            }

            const answerData = await response.json();

            // Set remote description
            await peerConnection.setRemoteDescription(new RTCSessionDescription(answerData));

        } catch (err) {
            console.error("WebRTC connection error:", err);
            setError(err.message || "Failed to connect to WebRTC stream");
            setIsLoading(false);
        }
    };

    const disconnect = () => {
        if (peerConnectionRef.current) {
            peerConnectionRef.current.close();
            peerConnectionRef.current = null;
        }
        setIsConnected(false);
    };

    // Calculate whether to show controls:
    // - Always show if video is stopped (not playing)
    // - Show based on mouse interaction if video is playing
    const shouldShowControls = !isPlaying || showControls;

    return (
        <>
            <Grid size={{xs: 12, sm: 12, md: 12}} style={{padding: '0rem 0.5rem 0rem 0.5rem'}}
                  container
                  direction="column"
                  ref={videoContainerRef}
                  sx={{
                      position: 'relative',
                      width: '100%',
                  }}
            >
                {isLoading && (
                    <Grid sx={{
                        position: 'absolute',
                        top: '50%',
                        left: '50%',
                        transform: 'translate(-50%, -50%)',
                        zIndex: 10
                    }}>
                        <CircularProgress/>
                    </Grid>
                )}

                {error && (
                    <Grid
                        item
                        sx={{
                            position: 'absolute',
                            top: '50%',
                            left: '50%',
                            transform: 'translate(-50%, -50%)',
                            color: 'error.main',
                            textAlign: 'center',
                            zIndex: 10
                        }}
                    >
                        <Typography variant="body1" color="error">
                            {error}
                        </Typography>
                        <Button
                            startIcon={<ReplayIcon/>}
                            variant="contained"
                            color="primary"
                            onClick={handleReconnect}
                            sx={{mt: 2}}
                        >
                            Reconnect
                        </Button>
                    </Grid>
                )}
                <Grid
                    sx={{ position: 'relative' }}
                    onMouseEnter={handleMouseEnter}
                    onMouseLeave={handleMouseLeave}
                    onMouseMove={handleMouseMove}
                >
                    {/* Video element */}
                    <video
                        ref={videoRef}
                        autoPlay
                        playsInline
                        style={{
                            width: '100%',
                            display: 'block',
                            cursor: 'pointer'
                        }}
                    />

                    {/* Full-size play/stop overlay button */}
                    {shouldShowControls && !isLoading && !error && (
                        <Box
                            onClick={handleTogglePlayStop}
                            sx={{
                                position: 'absolute',
                                top: 0,
                                left: 0,
                                right: 0,
                                bottom: 0,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                                cursor: 'pointer',
                                '&:hover': {
                                    backgroundColor: 'rgba(0, 0, 0, 0.4)',
                                },
                                transition: 'opacity 0.3s ease, background-color 0.3s ease',
                                zIndex: 5
                            }}
                        >
                            <Box
                                sx={{
                                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                                    borderRadius: '50%',
                                    padding: '10px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                {isPlaying ?
                                    <StopIcon sx={{ color: 'white', fontSize: '3rem' }} /> :
                                    <PlayArrowIcon sx={{ color: 'white', fontSize: '3rem' }} />
                                }
                            </Box>
                        </Box>
                    )}
                </Grid>
            </Grid>
        </>
    );
};

export default VideoWebRTCPlayer;