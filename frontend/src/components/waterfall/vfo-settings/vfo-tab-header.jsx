/**
 * VFO Tab Header Component
 *
 * Individual VFO tab with status indicators (lock, audio, active)
 */

import React from 'react';
import { Box, Tab } from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import VolumeMuteIcon from '@mui/icons-material/VolumeMute';

/**
 * VFO Tab Component with status indicators
 */
export const VfoTab = ({
    index,
    vfoColors,
    vfoMarkers,
    vfoActive,
    streamingVFOs,
    vfoMutedRedux
}) => {
    const vfoIndex = index + 1;
    const isLocked = vfoMarkers[vfoIndex]?.lockedTransmitterId && vfoMarkers[vfoIndex]?.lockedTransmitterId !== 'none';
    const isStreaming = streamingVFOs?.includes(vfoIndex) || false;
    const isMuted = vfoMutedRedux?.[vfoIndex] || false;
    const isActive = vfoActive?.[vfoIndex] || false;

    return (
        <Tab
            value={index}
            label={
                <Box sx={{ position: 'relative', width: '100%', height: '100%' }}>
                    {vfoIndex}
                    {/* Lock icon */}
                    {isLocked && (
                        <LockIcon
                            sx={{
                                position: 'absolute',
                                top: -4,
                                right: -8,
                                fontSize: '0.75rem',
                                pointerEvents: 'none',
                            }}
                        />
                    )}
                    {/* Audio icon with three states:
                        1. Gray VolumeMute (no waves): No audio data reached browser
                        2. Green VolumeMute (with slash): Audio reached, muted from UI
                        3. Green VolumeUp (with waves): Audio reached and playing
                    */}
                    {!isStreaming && (
                        <VolumeMuteIcon
                            sx={{
                                position: 'absolute',
                                bottom: -2,
                                right: -6,
                                fontSize: '0.75rem',
                                pointerEvents: 'none',
                                color: '#888888', // Gray for no audio
                            }}
                        />
                    )}
                    {isStreaming && isMuted && (
                        <VolumeMuteIcon
                            sx={{
                                position: 'absolute',
                                bottom: -2,
                                right: -6,
                                fontSize: '0.75rem',
                                pointerEvents: 'none',
                                color: '#00ff00', // Green for muted but streaming
                            }}
                        />
                    )}
                    {isStreaming && !isMuted && (
                        <VolumeUpIcon
                            sx={{
                                position: 'absolute',
                                bottom: -2,
                                right: -6,
                                fontSize: '0.75rem',
                                pointerEvents: 'none',
                                color: '#00ff00', // Green for playing
                            }}
                        />
                    )}
                    {/* Active VFO indicator (small status dot) */}
                    {isActive && (
                        <Box
                            aria-label={`VFO ${vfoIndex} active`}
                            sx={{
                                position: 'absolute',
                                top: -4,
                                left: -8,
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                bgcolor: 'success.main',
                                boxShadow: 1,
                            }}
                        />
                    )}
                </Box>
            }
            sx={{
                minWidth: '25%',
                backgroundColor: `${vfoColors?.[index] || '#000000'}40`, // 40 = ~25% opacity in hex
                '&.Mui-selected': {
                    fontWeight: 'bold',
                    borderBottom: 'none',
                    color: 'text.primary',
                },
            }}
        />
    );
};
