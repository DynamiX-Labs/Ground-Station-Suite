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

import { useCallback } from 'react';
import { toast } from '../../utils/toast-with-timestamp.jsx';

/**
 * Custom hook for waterfall event handlers
 */
export const useWaterfallEventHandlers = ({
    waterfallControlRef,
    workerRef,
    dispatch,
    setShowRotatorDottedLines,
    setAutoScalePreset
}) => {

    const handleZoomIn = useCallback(() => {
        if (waterfallControlRef.current) {
            const containerWidth = waterfallControlRef.current.getContainerWidth?.() || window.innerWidth;
            waterfallControlRef.current.zoomOnXAxisOnly(0.5, containerWidth / 2);
        }
    }, [waterfallControlRef]);

    const handleZoomOut = useCallback(() => {
        if (waterfallControlRef.current) {
            const containerWidth = waterfallControlRef.current.getContainerWidth?.() || window.innerWidth;
            waterfallControlRef.current.zoomOnXAxisOnly(-0.5, containerWidth / 2);
        }
    }, [waterfallControlRef]);

    const handleZoomReset = useCallback(() => {
        if (waterfallControlRef.current) {
            waterfallControlRef.current.resetCustomTransform();
        }
    }, [waterfallControlRef]);

    const toggleRotatorDottedLines = useCallback((value) => {
        console.log("Toggle Rotator Dotted Lines", value);
        dispatch(setShowRotatorDottedLines(value));

        // Send the toggle command to the worker
        if (workerRef.current) {
            workerRef.current.postMessage({
                cmd: 'toggleRotatorDottedLines',
                show: value,
            });
        }
    }, [dispatch, setShowRotatorDottedLines, workerRef]);

    const handleSetAutoScalePreset = useCallback((preset) => {
        console.log("Set Auto-Scale Preset:", preset);

        // Update Redux state
        dispatch(setAutoScalePreset(preset));

        // Send the preset to the worker
        if (workerRef.current) {
            workerRef.current.postMessage({
                cmd: 'setAutoScalePreset',
                preset: preset,
            });
        }
    }, [dispatch, setAutoScalePreset, workerRef]);

    return {
        handleZoomIn,
        handleZoomOut,
        handleZoomReset,
        toggleRotatorDottedLines,
        handleSetAutoScalePreset
    };
};

/**
 * Custom hook for snapshot functionality
 */
export const useSnapshotHandlers = ({
    captureSnapshot,
    generateSnapshotName,
    socket,
    dispatch,
    saveWaterfallSnapshot
}) => {

    const captureSnapshotWithOverlay = useCallback(async (setShowSnapshotOverlay, targetWidth = 1620) => {
        try {
            // Show snapshot overlay
            setShowSnapshotOverlay(true);

            // Use original method
            const compositeImage = await captureSnapshot(targetWidth);

            // Hide overlay after capture
            setShowSnapshotOverlay(false);

            return compositeImage;
        } catch (error) {
            console.error('Error capturing snapshot with overlay:', error);
            setShowSnapshotOverlay(false);
            return null;
        }
    }, [captureSnapshot]);

    const takeSnapshot = useCallback(async (setShowSnapshotOverlay) => {
        try {
            const compositeImage = await captureSnapshotWithOverlay(setShowSnapshotOverlay, 1620);
            if (!compositeImage) {
                return;
            }

            // Generate snapshot name
            const snapshotName = generateSnapshotName();

            // Send snapshot to backend using Redux async thunk
            dispatch(saveWaterfallSnapshot({ socket, waterfallImage: compositeImage, snapshotName }))
                .unwrap()
                .then(() => {
                    toast.success('Waterfall snapshot saved successfully', { autoClose: 3000 });
                })
                .catch((error) => {
                    console.error('Failed to save snapshot:', error);
                    toast.error('Failed to save snapshot');
                });
        } catch (error) {
            console.error('Error in takeSnapshot:', error);
            toast.error('Error capturing snapshot');
        }
    }, [captureSnapshot, generateSnapshotName, socket, dispatch, saveWaterfallSnapshot]);

    return {
        captureSnapshotWithOverlay,
        takeSnapshot
    };
};
