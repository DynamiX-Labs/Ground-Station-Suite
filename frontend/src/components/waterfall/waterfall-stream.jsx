import { useEffect, useRef, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useSocket } from '../common/socket.jsx';
import { useWaterfallEngine } from './waterfall-engine-provider.jsx';
import {
    setIsStreaming,
    setErrorMessage,
    setStartStreamingLoading,
    setFFTdataOverflow,
    setExpandedPanels,
    setStartStreamValidationErrors,
    clearStartStreamValidationErrors,
    stopRecording
} from './waterfall-slice.jsx';
import { toast } from '../../utils/toast-with-timestamp.jsx';

const useWaterfallStream = ({
    workerRef,
    waterfallRendererMode = 'worker',
    onDomTileFftData,
    targetFPSRef,
    playbackElapsedSecondsRef,
    playbackRemainingSecondsRef,
    playbackTotalSecondsRef,
    getAudioState,
    initializeAudio
}) => {
    const dispatch = useDispatch();
    const { socket } = useSocket();
    const { subscribeToFftData } = useWaterfallEngine();
    const {
        selectedSDRId,
        centerFrequency,
        sampleRate,
        gain,
        fftSize,
        sdrSettingsById,
        fftWindow,
        fftOverlapPercent,
        fftOverlapDepth,
        selectedAntenna,
        selectedOffsetValue,
        fftAveraging,
        isStreaming,
        gettingSDRParameters,
        autoDBRange,
        playbackRecordingPath,
        isRecording,
        expandedPanels,
    } = useSelector((state) => state.waterfall);

    const biasT = sdrSettingsById?.[selectedSDRId]?.draft?.biasT ?? false;
    const tunerAgc = sdrSettingsById?.[selectedSDRId]?.draft?.tunerAgc ?? false;
    const rtlAgc = sdrSettingsById?.[selectedSDRId]?.draft?.rtlAgc ?? false;
    const soapyAgc = sdrSettingsById?.[selectedSDRId]?.draft?.soapyAgc ?? false;

    const {
        vfoActive,
    } = useSelector((state) => state.vfo);

    const animationFrameRef = useRef(null);
    const bandscopeAnimationFrameRef = useRef(null);
    const timestampWindowRef = useRef([]);
    const overflowRef = useRef(false);
    const allowedIntervalRef = useRef(0);
    const lastAllowedUpdateRef = useRef(0);
    const windowSizeMs = 1000;
    const fftDataOverflowLimit = 60;

    const cancelAnimations = useCallback(() => {
        if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current);
            animationFrameRef.current = null;
        }
        if (bandscopeAnimationFrameRef.current) {
            cancelAnimationFrame(bandscopeAnimationFrameRef.current);
            bandscopeAnimationFrameRef.current = null;
        }
    }, []);

    useEffect(() => {
        if (!socket) {
            return;
        }

        // Note: sdr-config-error, sdr-error, sdr-config, and sdr-status are now handled
        // in the parent-level socket event handler (hooks/useSocketEventHandlers.jsx)
        // to ensure messages are always received even when this component unmounts

        const handleDisconnect = () => {
            cancelAnimations();
            dispatch(setIsStreaming(false));
        };

        socket.on('disconnect', handleDisconnect);

        return () => {
            socket.off('disconnect', handleDisconnect);
        };
    }, [socket, cancelAnimations, dispatch]);

    useEffect(() => {
        const unsubscribe = subscribeToFftData((frame) => {
            const now = performance.now();
            timestampWindowRef.current.push(now);
            const cutoffTime = now - windowSizeMs;
            while (timestampWindowRef.current.length > 0 && timestampWindowRef.current[0] < cutoffTime) {
                timestampWindowRef.current.shift();
            }
            const currentRate = timestampWindowRef.current.length;
            const shouldOverflow = currentRate > fftDataOverflowLimit;
            if (shouldOverflow !== overflowRef.current) {
                overflowRef.current = shouldOverflow;
                dispatch(setFFTdataOverflow(shouldOverflow));
                allowedIntervalRef.current = 1000 / fftDataOverflowLimit;
            }
            if (overflowRef.current) {
                const timeSinceLastAllowed = now - lastAllowedUpdateRef.current;
                if (timeSinceLastAllowed < allowedIntervalRef.current) {
                    timestampWindowRef.current.pop();
                    return;
                }
                lastAllowedUpdateRef.current = now;
            }
            const {
                fft,
                playbackElapsedSeconds,
                playbackRemainingSeconds,
                playbackTotalSeconds,
            } = frame;

            // Update playback timing refs without causing re-renders
            if (playbackElapsedSecondsRef) {
                playbackElapsedSecondsRef.current = playbackElapsedSeconds;
            }
            if (playbackRemainingSecondsRef) {
                playbackRemainingSecondsRef.current = playbackRemainingSeconds;
            }
            if (playbackTotalSecondsRef) {
                playbackTotalSecondsRef.current = playbackTotalSeconds;
            }

            if (waterfallRendererMode === 'dom-tiles') {
                if (onDomTileFftData) {
                    onDomTileFftData(fft);
                }
            }
        });

        return () => {
            cancelAnimations();
            unsubscribe();
        };
    }, [subscribeToFftData, cancelAnimations, dispatch, waterfallRendererMode, onDomTileFftData]);

    // Effect to handle cleanup when streaming stops (from parent handler or local stop)
    useEffect(() => {
        if (!isStreaming) {
            cancelAnimations();
        }
    }, [isStreaming, cancelAnimations]);

    const isUnsetSelection = useCallback((value) => {
        if (value === null || value === undefined) {
            return true;
        }
        if (typeof value === 'string') {
            const normalized = value.trim().toLowerCase();
            return normalized === '' || normalized === 'none';
        }
        return false;
    }, []);

    const startStreaming = useCallback(() => {
        if (!isStreaming) {
            // Toolbar play button should only handle real SDRs, not SigmfPlayback
            if (selectedSDRId === "sigmf-playback") {
                toast.error('Use the playback controls to play recordings');
                return;
            }

            const validationErrors = {
                gain: isUnsetSelection(gain),
                sampleRate: isUnsetSelection(sampleRate),
                antenna: isUnsetSelection(selectedAntenna),
            };
            if (validationErrors.gain || validationErrors.sampleRate || validationErrors.antenna) {
                dispatch(setStartStreamValidationErrors(validationErrors));
                if (!expandedPanels.includes('sdr')) {
                    dispatch(setExpandedPanels([...expandedPanels, 'sdr']));
                }
                toast.error('Select gain, sample rate, and antenna before starting stream');
                return;
            }

            dispatch(clearStartStreamValidationErrors());
            dispatch(setStartStreamingLoading(true));
            dispatch(setErrorMessage(''));

            // Proactively ensure AudioContext is resumed before streaming starts
            // This prevents the race condition where audio arrives before context is ready
            if (getAudioState && initializeAudio) {
                const audioState = getAudioState();
                if (audioState.contextState === 'suspended') {
                    console.log('AudioContext suspended - resuming before stream start');
                    initializeAudio().catch(err => {
                        console.warn('Failed to resume AudioContext proactively:', err);
                        // Continue anyway - audio will try to resume when first packet arrives
                    });
                } else if (!audioState.enabled) {
                    console.log('Audio not enabled - initializing before stream start');
                    initializeAudio().catch(err => {
                        console.warn('Failed to initialize audio proactively:', err);
                    });
                }
            }

            socket.emit('sdr_data', 'configure-sdr', {
                selectedSDRId,
                centerFrequency,
                sampleRate,
                gain,
                fftSize,
                biasT,
                tunerAgc,
                rtlAgc,
                fftWindow,
                fftOverlapPercent,
                fftOverlapDepth,
                antenna: selectedAntenna,
                offsetFrequency: selectedOffsetValue,
                soapyAgc,
                fftAveraging,
                sdrSettings: sdrSettingsById?.[selectedSDRId]?.draft || {},
            }, (response) => {
                if (response['success']) {
                    socket.emit('sdr_data', 'start-streaming', { selectedSDRId });
                }
            });
        }
    }, [isStreaming, dispatch, socket, selectedSDRId, centerFrequency, sampleRate, gain, fftSize, biasT, tunerAgc, rtlAgc, fftWindow, fftOverlapPercent, fftOverlapDepth, selectedAntenna, selectedOffsetValue, soapyAgc, fftAveraging, getAudioState, initializeAudio, isUnsetSelection, expandedPanels]);

    const stopStreaming = useCallback(async () => {
        if (isStreaming) {
            // If recording is active, stop it first
            if (isRecording) {
                try {
                    // Capture waterfall snapshot
                    let waterfallImage = null;
                    try {
                        if (window.captureWaterfallSnapshot) {
                            waterfallImage = await window.captureWaterfallSnapshot(1620);
                        }
                    } catch (captureError) {
                        console.error('Error capturing waterfall:', captureError);
                    }

                    // Stop recording and wait for it to complete
                    await dispatch(stopRecording({ socket, selectedSDRId, waterfallImage })).unwrap();
                    console.log('Recording stopped successfully before stopping stream');
                } catch (error) {
                    console.error('Error stopping recording:', error);
                    toast.error(`Failed to stop recording: ${error}`);
                }
            }

            // Now stop streaming
            socket.emit('sdr_data', 'stop-streaming', { selectedSDRId });
            dispatch(setIsStreaming(false));
            cancelAnimations();
        }
    }, [isStreaming, isRecording, socket, selectedSDRId, dispatch, cancelAnimations]);

    const playButtonEnabledOrNot = useCallback(() => {
        const isStreamingActive = isStreaming;
        const noSDRSelected = selectedSDRId === 'none';
        const isSigmfPlayback = selectedSDRId === 'sigmf-playback';
        const isLoadingParameters = gettingSDRParameters;
        return isStreamingActive || noSDRSelected || isSigmfPlayback || isLoadingParameters;
    }, [isStreaming, selectedSDRId, gettingSDRParameters]);

    return { startStreaming, stopStreaming, playButtonEnabledOrNot };
};

export default useWaterfallStream;
