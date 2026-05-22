import React, { createContext, useContext, useRef, useState, useEffect, useCallback, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { toast } from '../../utils/toast-with-timestamp.jsx';
import { registerFlushCallback, unregisterFlushCallback } from './audio-service.js';
import { setVfoMuted } from '../waterfall/vfo-marker/vfo-slice.jsx';
import {
    AUDIO_AUTO_FLUSH_CHECK_INTERVAL_MS,
    AUDIO_AUTO_FLUSH_MAX_BUFFER_SECONDS
} from './audio-buffer-config.js';

const AudioContext = createContext({
    audioEnabled: false,
    volume: 0.5,
    initializeAudio: () => {},
    playAudioSamples: () => {},
    setAudioVolume: () => {},
    setVfoMute: () => {},
    setVfoVolume: () => {},
    stopAudio: () => {},
    getAudioState: () => {},
    flushAudioBuffers: () => {},
    getAudioBufferLength: () => {},
    getVfoAudioLevel: () => {},
    getVfoRfPower: () => {},
    getVfoSquelchDebug: () => null
});

export const useAudio = () => {
    const context = useContext(AudioContext);
    if (!context) {
        throw new Error('useAudio must be used within an AudioProvider');
    }
    return context;
};

export const AudioProvider = ({ children }) => {
    const dispatch = useDispatch();

    // Get persisted mute state from Redux
    const vfoMutedRedux = useSelector(state => state.vfo.vfoMuted || {
        1: false,
        2: false,
        3: false,
        4: false
    });

    // Audio context for Web Audio API (must stay in main thread)
    const audioContextRef = useRef(null);
    const [audioEnabled, setAudioEnabled] = useState(false);
    const [volume, setVolume] = useState(0.5);

    // Per-VFO state (supports 4 VFOs: 1-4)
    const vfoGainNodesRef = useRef({}); // { 1: GainNode, 2: GainNode, ... }
    const vfoWorkersRef = useRef({}); // { 1: Worker, 2: Worker, ... }
    const vfoNextPlayTimeRef = useRef({}); // { 1: time, 2: time, ... }
    const vfoMutedRef = useRef({}); // { 1: false, 2: false, ... }
    const vfoVolumeRef = useRef({}); // { 1: 1.0, 2: 1.0, ... } - individual VFO volumes
    const vfoAudioLevelRef = useRef({}); // { 1: 0.0, 2: 0.0, ... } - RMS audio levels
    const vfoRfPowerRef = useRef({}); // { 1: -100, 2: -100, ... } - RF power in dB
    const vfoSquelchDebugRef = useRef({}); // { 1: {...}, 2: {...}, ... } - squelch diagnostics

    // Callback ref to handle audio from workers - must be defined before workers
    const playProcessedAudioRef = useRef(null);

    // Initialize Web Workers - one per VFO (4 VFOs: 1-4)
    const initializeWorkers = useCallback(() => {
        try {
            for (let vfoNumber = 1; vfoNumber <= 4; vfoNumber++) {
                const worker = new Worker(
                    new URL('./audio-worker.js', import.meta.url),
                    { type: 'module' }
                );

                worker.onmessage = (e) => {
                    const { type, batch, status, error, level } = e.data;

                    switch (type) {
                        case 'AUDIO_BATCH':
                            // Process the batch from worker - use ref to avoid stale closure
                            if (playProcessedAudioRef.current) {
                                batch.forEach(audioData => playProcessedAudioRef.current(audioData, vfoNumber));
                            }
                            break;
                        case 'QUEUE_STATUS':
                            //console.log(`VFO ${vfoNumber} audio queue status:`, status);
                            break;
                        case 'AUDIO_LEVEL':
                            vfoAudioLevelRef.current[vfoNumber] = level;
                            break;
                        case 'ERROR':
                            console.error(`VFO ${vfoNumber} audio worker error:`, error);
                            break;
                    }
                };

                worker.onerror = (error) => {
                    console.error(`VFO ${vfoNumber} audio worker error:`, error);
                    toast.error(`VFO ${vfoNumber} audio worker failed`);
                };

                vfoWorkersRef.current[vfoNumber] = worker;
            }

            console.log('Audio workers initialized for 4 VFOs');
        } catch (error) {
            console.warn('Failed to initialize audio workers:', error);
        }
    }, []);

    // Initialize audio context
    const initializeAudio = useCallback(async () => {
        try {
            await new Promise(resolve => {
                if (window.requestIdleCallback) {
                    window.requestIdleCallback(resolve);
                } else {
                    setTimeout(resolve, 0);
                }
            });

            // Configure AudioContext for low latency
            const contextOptions = {
                latencyHint: 'interactive', // Request lowest latency
                sampleRate: 44100
            };

            audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)(contextOptions);

            // Create separate GainNode for each VFO (4 VFOs: 1-4)
            for (let vfoNumber = 1; vfoNumber <= 4; vfoNumber++) {
                const gainNode = audioContextRef.current.createGain();
                gainNode.connect(audioContextRef.current.destination);

                // Initialize per-VFO state from Redux (for mute) or defaults
                const isMuted = vfoMutedRedux[vfoNumber] || false;
                vfoMutedRef.current[vfoNumber] = isMuted;
                vfoVolumeRef.current[vfoNumber] = 1.0;

                // Set gain based on mute state
                gainNode.gain.value = isMuted ? 0 : volume;
                vfoGainNodesRef.current[vfoNumber] = gainNode;

                vfoNextPlayTimeRef.current[vfoNumber] = audioContextRef.current.currentTime;
                vfoAudioLevelRef.current[vfoNumber] = 0.0;
            }

            if (audioContextRef.current.state === 'suspended') {
                await audioContextRef.current.resume();
            }

            // Initialize workers after audio context is ready
            initializeWorkers();

            setAudioEnabled(true);

            console.log(`Audio initialized - Base latency: ${audioContextRef.current.baseLatency}s, Output latency: ${audioContextRef.current.outputLatency}s`);

        } catch (error) {
            console.error('Failed to initialize audio:', error);
            toast.error(`Failed to initialize audio: ${error.message}`);
        }
    }, [volume, initializeWorkers, vfoMutedRedux]);

    // Play processed audio from worker (main thread only) - per VFO
    const playProcessedAudio = useCallback((processedData, vfoNumber) => {
        if (!audioContextRef.current || !vfoGainNodesRef.current[vfoNumber]) return;

        // Note: Don't return early if muted - let audio flow through GainNode with gain=0
        // This allows instant mute/unmute without audio gaps

        try {
            const { samples, sample_rate, channels } = processedData;

            // Calculate number of frames (samples per channel)
            const numFrames = channels === 2 ? samples.length / 2 : samples.length;

            const audioBuffer = audioContextRef.current.createBuffer(
                channels,
                numFrames,
                sample_rate
            );

            if (channels === 1) {
                // Mono: copy samples directly
                const channelData = audioBuffer.getChannelData(0);
                channelData.set(samples);
            } else if (channels === 2) {
                // Stereo: de-interleave L and R channels
                // Input format: [L0, R0, L1, R1, L2, R2, ...]
                const leftChannel = audioBuffer.getChannelData(0);
                const rightChannel = audioBuffer.getChannelData(1);

                for (let i = 0; i < numFrames; i++) {
                    leftChannel[i] = samples[i * 2];     // Even indices = left
                    rightChannel[i] = samples[i * 2 + 1]; // Odd indices = right
                }
            }

            const source = audioContextRef.current.createBufferSource();
            source.buffer = audioBuffer;

            // Connect to VFO-specific GainNode
            const gainNode = vfoGainNodesRef.current[vfoNumber];
            source.connect(gainNode);

            const currentTime = audioContextRef.current.currentTime;
            const vfoNextPlayTime = vfoNextPlayTimeRef.current[vfoNumber];

            // Schedule audio continuously without gaps
            if (vfoNextPlayTime < currentTime) {
                // If we're behind, start immediately
                vfoNextPlayTimeRef.current[vfoNumber] = currentTime;
            }

            source.start(vfoNextPlayTimeRef.current[vfoNumber]);

            // Next chunk starts exactly when this one ends (no gap)
            vfoNextPlayTimeRef.current[vfoNumber] += audioBuffer.duration;

        } catch (error) {
            console.error(`Error playing processed audio for VFO ${vfoNumber}:`, error);
        }
    }, []);

    // Keep ref updated with latest playProcessedAudio function
    useEffect(() => {
        playProcessedAudioRef.current = playProcessedAudio;
    }, [playProcessedAudio]);

    // Play audio samples - route to correct VFO worker
    const playAudioSamples = useCallback((audioData) => {
        if (!audioContextRef.current) return;

        if (audioContextRef.current.state === 'suspended') {
            audioContextRef.current.resume().then(() => {
                playAudioSamples(audioData);
            }).catch(err => {
                console.error('Failed to resume AudioContext:', err);
            });
            return;
        }

        if (!audioEnabled) {
            setAudioEnabled(true);
        }

        // Extract VFO number from audio data (backend sends 1-4)
        const vfoNumber = audioData.vfo?.vfo_number;
        if (vfoNumber === undefined || vfoNumber < 1 || vfoNumber > 4) {
            console.warn('Invalid or missing vfo_number in audio data:', audioData);
            return;
        }

        // Extract and store RF power measurement if present
        if (audioData.rf_power_db !== undefined && audioData.rf_power_db !== null) {
            vfoRfPowerRef.current[vfoNumber] = audioData.rf_power_db;
        }
        if (audioData.squelch_debug !== undefined && audioData.squelch_debug !== null) {
            vfoSquelchDebugRef.current[vfoNumber] = audioData.squelch_debug;
        }

        // Send to the correct VFO worker for processing
        const worker = vfoWorkersRef.current[vfoNumber];
        if (worker) {
            worker.postMessage({
                type: 'AUDIO_DATA',
                data: audioData
            });
        }
    }, [audioEnabled]);

    // Set master volume (affects all VFOs)
    const setAudioVolume = useCallback((newVolume) => {
        setVolume(newVolume);
        // Apply to all VFO gain nodes
        Object.values(vfoGainNodesRef.current).forEach(gainNode => {
            if (gainNode && !vfoMutedRef.current[gainNode.vfoNumber]) {
                gainNode.gain.value = newVolume * (vfoVolumeRef.current[gainNode.vfoNumber] || 1.0);
            }
        });
    }, []);

    // Set individual VFO volume
    const setVfoVolume = useCallback((vfoNumber, vfoVolume) => {
        if (vfoNumber < 1 || vfoNumber > 4) return;

        vfoVolumeRef.current[vfoNumber] = vfoVolume;
        const gainNode = vfoGainNodesRef.current[vfoNumber];

        if (gainNode && !vfoMutedRef.current[vfoNumber]) {
            gainNode.gain.value = volume * vfoVolume;
        }
    }, [volume]);

    // Flush audio buffers (clear all VFO worker queues and reset audio scheduling)
    const flushAudioBuffers = useCallback((vfoNumber = null) => {
        if (vfoNumber !== null) {
            // Flush specific VFO
            const worker = vfoWorkersRef.current[vfoNumber];
            if (worker) {
                worker.postMessage({ type: 'CLEAR_QUEUE' });
            }
            if (audioContextRef.current) {
                vfoNextPlayTimeRef.current[vfoNumber] = audioContextRef.current.currentTime;
            }
        } else {
            // Flush all VFOs
            Object.values(vfoWorkersRef.current).forEach(worker => {
                if (worker) {
                    worker.postMessage({ type: 'CLEAR_QUEUE' });
                }
            });

            if (audioContextRef.current) {
                const currentTime = audioContextRef.current.currentTime;
                for (let i = 1; i <= 4; i++) {
                    vfoNextPlayTimeRef.current[i] = currentTime;
                }
            }
        }
    }, []);

    // Mute/unmute individual VFO
    // VFO numbers are 1-4 (from UI/backend), matching audio routing
    const setVfoMute = useCallback((vfoNumber, muted) => {
        if (vfoNumber < 1 || vfoNumber > 4) return;

        vfoMutedRef.current[vfoNumber] = muted;
        const gainNode = vfoGainNodesRef.current[vfoNumber];

        if (gainNode) {
            gainNode.gain.value = muted ? 0 : volume * (vfoVolumeRef.current[vfoNumber] || 1.0);
        }

        // Update Redux state so UI can reflect mute status
        dispatch(setVfoMuted({ vfoNumber, muted }));

        // Flush the audio buffer for this VFO when muting/unmuting
        flushAudioBuffers(vfoNumber);
    }, [volume, flushAudioBuffers, dispatch]);

    // Stop audio - terminate all VFO workers
    const stopAudio = useCallback(() => {
        // Terminate all VFO workers
        Object.values(vfoWorkersRef.current).forEach(worker => {
            if (worker) {
                worker.postMessage({ type: 'CLEAR_QUEUE' });
                worker.terminate();
            }
        });
        vfoWorkersRef.current = {};

        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }

        vfoGainNodesRef.current = {};
        vfoNextPlayTimeRef.current = {};
        vfoMutedRef.current = {};
        vfoVolumeRef.current = {};

        setAudioEnabled(false);
    }, []);

    // Get audio context state
    const getAudioState = useCallback(() => {
        // Get worker queue status for all VFOs
        Object.values(vfoWorkersRef.current).forEach(worker => {
            if (worker) {
                worker.postMessage({ type: 'GET_QUEUE_STATUS' });
            }
        });

        return {
            enabled: audioEnabled,
            volume: volume,
            contextState: audioContextRef.current?.state || 'closed',
            vfoWorkersActive: Object.keys(vfoWorkersRef.current).length,
            vfoMuted: { ...vfoMutedRef.current },
            vfoVolumes: { ...vfoVolumeRef.current }
        };
    }, [audioEnabled, volume]);

    // Get browser audio buffer length in seconds (per VFO or max across all)
    const getAudioBufferLength = useCallback((vfoNumber = null) => {
        if (!audioContextRef.current) {
            return 0;
        }
        const currentTime = audioContextRef.current.currentTime;

        if (vfoNumber !== null) {
            // Get buffer length for specific VFO
            const bufferLength = Math.max(0, vfoNextPlayTimeRef.current[vfoNumber] - currentTime);
            return bufferLength;
        } else {
            // Get max buffer length across all VFOs
            let maxBufferLength = 0;
            for (let i = 1; i <= 4; i++) {
                const bufferLength = Math.max(0, vfoNextPlayTimeRef.current[i] - currentTime);
                maxBufferLength = Math.max(maxBufferLength, bufferLength);
            }
            return maxBufferLength;
        }
    }, []);

    // Get VFO audio level (RMS, range 0.0 to 1.0)
    const getVfoAudioLevel = useCallback((vfoNumber) => {
        if (vfoNumber < 1 || vfoNumber > 4) return 0;

        // Request latest audio level from worker
        const worker = vfoWorkersRef.current[vfoNumber];
        if (worker) {
            worker.postMessage({ type: 'GET_AUDIO_LEVEL' });
        }

        return vfoAudioLevelRef.current[vfoNumber] || 0;
    }, []);

    // Get VFO RF power in dB
    const getVfoRfPower = useCallback((vfoNumber) => {
        if (vfoNumber < 1 || vfoNumber > 4) return null;
        return vfoRfPowerRef.current[vfoNumber] || null;
    }, []);

    // Get VFO squelch diagnostics
    const getVfoSquelchDebug = useCallback((vfoNumber) => {
        if (vfoNumber < 1 || vfoNumber > 4) return null;
        return vfoSquelchDebugRef.current[vfoNumber] || null;
    }, []);

    // Register flush callback for use by middleware
    useEffect(() => {
        registerFlushCallback(flushAudioBuffers);
        return () => {
            unregisterFlushCallback();
        };
    }, [flushAudioBuffers]);

    // Automatic buffer monitoring - flush if buffer gets too large
    useEffect(() => {
        if (!audioEnabled) return;

        const monitorInterval = setInterval(() => {
            for (let vfoNumber = 1; vfoNumber <= 4; vfoNumber++) {
                const bufferLength = getAudioBufferLength(vfoNumber);
                if (bufferLength > AUDIO_AUTO_FLUSH_MAX_BUFFER_SECONDS) {
                    console.warn(`VFO ${vfoNumber} buffer too large (${bufferLength.toFixed(2)}s), flushing to prevent lag`);
                    flushAudioBuffers(vfoNumber);
                }
            }
        }, AUDIO_AUTO_FLUSH_CHECK_INTERVAL_MS);

        return () => clearInterval(monitorInterval);
    }, [audioEnabled, getAudioBufferLength, flushAudioBuffers]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            // Terminate all VFO workers
            Object.values(vfoWorkersRef.current).forEach(worker => {
                if (worker) {
                    worker.postMessage({ type: 'CLEAR_QUEUE' });
                    worker.terminate();
                }
            });
            if (audioContextRef.current) {
                audioContextRef.current.close();
            }
        };
    }, []);

    const value = useMemo(() => ({
        audioEnabled,
        volume,
        initializeAudio,
        playAudioSamples,
        setAudioVolume,
        setVfoMute,
        setVfoVolume,
        stopAudio,
        getAudioState,
        flushAudioBuffers,
        getAudioBufferLength,
        getVfoAudioLevel,
        getVfoRfPower,
        getVfoSquelchDebug
    }), [audioEnabled, volume, initializeAudio, playAudioSamples, setAudioVolume, setVfoMute, setVfoVolume, stopAudio, getAudioState, flushAudioBuffers, getAudioBufferLength, getVfoAudioLevel, getVfoRfPower, getVfoSquelchDebug]);

    return (
        <AudioContext.Provider value={value}>
            {children}
        </AudioContext.Provider>
    );
};
