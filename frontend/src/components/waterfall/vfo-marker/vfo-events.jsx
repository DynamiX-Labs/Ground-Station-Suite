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

import { useCallback, useEffect } from 'react';
import { calculateBandwidthChange } from './vfo-utils.js';
import { getBandwidthConfig } from './vfo-config.js';

/**
 * Custom hook for VFO drag operations
 */
export const useVFODragHandlers = ({
    activeMarker,
    vfoMarkers,
    actualWidth,
    freqRange,
    dragMode,
    startFreq,
    endFreq,
    updateVFOProperty,
    canvasRef,
    getDecoderInfoForVFO
}) => {
    const handleDragMovement = useCallback((deltaX) => {
        if (!activeMarker) return;

        const marker = vfoMarkers[activeMarker];
        if (!marker) return;

        const rect = canvasRef.current.getBoundingClientRect();
        const scaleFactor = actualWidth / rect.width;
        const scaledDelta = deltaX * scaleFactor;
        const freqDelta = (scaledDelta / actualWidth) * freqRange;

        if (dragMode === 'body') {
            const newFrequency = marker.frequency + freqDelta;
            const limitedFreq = Math.round(Math.max(startFreq, Math.min(newFrequency, endFreq)));
            updateVFOProperty(parseInt(activeMarker), { frequency: limitedFreq });
        } else {
            // Get bandwidth limits for this VFO's configured mode
            const bandwidthConfig = getBandwidthConfig(marker.mode);

            const currentBandwidth = marker.bandwidth || bandwidthConfig.default;
            const limitedBandwidth = calculateBandwidthChange(
                currentBandwidth,
                freqDelta,
                dragMode,
                bandwidthConfig.min,
                bandwidthConfig.max
            );
            updateVFOProperty(parseInt(activeMarker), { bandwidth: limitedBandwidth });
        }
    }, [activeMarker, vfoMarkers, actualWidth, freqRange, dragMode, startFreq, endFreq, updateVFOProperty, canvasRef, getDecoderInfoForVFO]);

    return { handleDragMovement };
};

/**
 * Custom hook for VFO mouse event handlers
 */
export const useVFOMouseHandlers = ({
    canvasRef,
    getHoverElement,
    isDragging,
    setActiveMarker,
    setDragMode,
    setIsDragging,
    setCursor,
    lastClientXRef,
    dispatch,
    setSelectedVFO
}) => {
    const handleMouseMove = useCallback((e) => {
        if (isDragging) return;

        const rect = canvasRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const { element } = getHoverElement(x, y);

        if (element === 'body') {
            setCursor('ew-resize');
        } else if (element === 'leftEdge' || element === 'rightEdge') {
            setCursor('col-resize');
        } else {
            setCursor('default');
        }
    }, [getHoverElement, isDragging, canvasRef, setCursor]);

    const handleMouseLeave = useCallback(() => {
        if (!isDragging) {
            setCursor('default');
        }
    }, [isDragging, setCursor]);

    const handleMouseDown = useCallback((e) => {
        if (e.button !== 0) return;

        const rect = canvasRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const { key, element } = getHoverElement(x, y);

        if (key && (element === 'body' || element === 'leftEdge' || element === 'rightEdge')) {
            setActiveMarker(key);
            setDragMode(element);
            setIsDragging(true);
            setCursor(element === 'body' ? 'ew-resize' : 'col-resize');
            lastClientXRef.current = e.clientX;

            e.preventDefault();
            e.stopPropagation();
        }

        dispatch(setSelectedVFO(parseInt(key) || null));
    }, [canvasRef, getHoverElement, setActiveMarker, setDragMode, setIsDragging, setCursor, lastClientXRef, dispatch, setSelectedVFO]);

    const handleClick = useCallback((e) => {
        // Click handling is done in mousedown
    }, []);

    const handleDoubleClick = useCallback((e) => {
        // Disabled for now
        return false;
    }, []);

    return {
        handleMouseMove,
        handleMouseLeave,
        handleMouseDown,
        handleClick,
        handleDoubleClick
    };
};

/**
 * Custom hook for VFO touch event handlers
 */
export const useVFOTouchHandlers = ({
    canvasRef,
    getHoverElement,
    isDragging,
    setActiveMarker,
    setDragMode,
    setIsDragging,
    isDraggingRef,
    lastTouchXRef,
    touchStartTimeoutRef,
    dispatch,
    setSelectedVFO
}) => {
    const handleTouchStart = useCallback((e) => {
        if (e.touches.length !== 1) return;

        const touch = e.touches[0];
        const rect = canvasRef.current.getBoundingClientRect();
        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;

        const { key, element } = getHoverElement(x, y);

        if (key && element) {
            setActiveMarker(key);
            setDragMode(element);
            setIsDragging(true);
            isDraggingRef.current = true;
            lastTouchXRef.current = touch.clientX;

            e.preventDefault();
            e.stopPropagation();
        }

        dispatch(setSelectedVFO(parseInt(key) || null));

        return { key, element };
    }, [canvasRef, getHoverElement, setActiveMarker, setDragMode, setIsDragging, isDraggingRef, lastTouchXRef, dispatch, setSelectedVFO]);

    const handleTouchMove = useCallback((e, touchStartTimeoutRef, handleDragMovement) => {
        if (touchStartTimeoutRef.current) {
            clearTimeout(touchStartTimeoutRef.current);
            touchStartTimeoutRef.current = null;
        }

        if (!isDragging || e.touches.length !== 1) return;

        e.preventDefault();
        e.stopPropagation();

        const touch = e.touches[0];
        const deltaX = touch.clientX - lastTouchXRef.current;
        lastTouchXRef.current = touch.clientX;

        handleDragMovement(deltaX);
    }, [isDragging, lastTouchXRef]);

    const handleTouchEnd = useCallback((e, touchStartTimeoutRef, endDragOperation) => {
        if (touchStartTimeoutRef.current) {
            clearTimeout(touchStartTimeoutRef.current);
            touchStartTimeoutRef.current = null;
        }

        if (isDragging) {
            e.preventDefault();
            e.stopPropagation();
            endDragOperation();
        }
    }, [isDragging]);

    const handleTouchCancel = useCallback((e, touchStartTimeoutRef, endDragOperation) => {
        if (isDragging) {
            e.preventDefault();
            e.stopPropagation();
            endDragOperation();
        }
    }, [isDragging]);

    const handleTap = useCallback((e) => {
        if (isDragging) return;

        if (!e || !e.touches || e.touches.length !== 1) return;

        const touch = e.touches[0];
        if (!touch || touch.clientX === undefined || touch.clientY === undefined) return;

        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;

        const x = touch.clientX - rect.left;
        const y = touch.clientY - rect.top;

        const { key } = getHoverElement(x, y);

        if (key) {
            dispatch(setSelectedVFO(parseInt(key) || null));

            if (e.preventDefault) e.preventDefault();
            if (e.stopPropagation) e.stopPropagation();
        }
    }, [isDragging, canvasRef, getHoverElement, dispatch, setSelectedVFO]);

    return {
        handleTouchStart,
        handleTouchMove,
        handleTouchEnd,
        handleTouchCancel,
        handleTap
    };
};

/**
 * Custom hook for VFO mousewheel frequency adjustment
 */
export const useVFOWheelHandler = ({
    canvasRef,
    selectedVFO,
    vfoMarkers,
    vfoActive,
    startFreq,
    endFreq,
    updateVFOProperty
}) => {
    const handleWheel = useCallback((e) => {
        if (e.shiftKey) {
            return;
        }

        if (selectedVFO === null || !vfoMarkers[selectedVFO] || !vfoActive[selectedVFO]) {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        const marker = vfoMarkers[selectedVFO];
        const freqChange = -Math.sign(e.deltaY) * marker.stepSize;

        // Check if VFO is locked to a transmitter
        const isLocked = marker.lockedTransmitterId && marker.lockedTransmitterId !== 'none';

        if (isLocked) {
            // When locked, adjust the frequency offset instead of absolute frequency
            const currentOffset = marker.frequencyOffset || 0;
            const newOffset = Math.round(currentOffset + freqChange);

            updateVFOProperty(selectedVFO, {
                frequencyOffset: newOffset,
            });
        } else {
            // When unlocked, adjust absolute frequency as before
            const newFrequency = marker.frequency + freqChange;
            const limitedFreq = Math.round(Math.max(startFreq, Math.min(newFrequency, endFreq)));

            updateVFOProperty(selectedVFO, {
                frequency: limitedFreq,
            });
        }

    }, [selectedVFO, vfoMarkers, vfoActive, startFreq, endFreq, updateVFOProperty]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        canvas.addEventListener('wheel', handleWheel, { passive: false });

        return () => {
            canvas.removeEventListener('wheel', handleWheel);
        };
    }, [handleWheel, canvasRef]);

    return { handleWheel };
};

/**
 * Custom hook for managing drag state across mouse and touch events
 */
export const useVFODragState = ({
    isDragging,
    activeMarker,
    handleDragMovement,
    endDragOperation,
    lastClientXRef,
    lastTouchXRef
}) => {
    // Mouse drag effect
    useEffect(() => {
        if (isDragging && activeMarker) {
            const handleMouseMoveEvent = (e) => {
                if (e.sourceCapabilities && e.sourceCapabilities.firesTouchEvents) {
                    return;
                }

                e.preventDefault();
                e.stopPropagation();

                const deltaX = e.clientX - lastClientXRef.current;
                lastClientXRef.current = e.clientX;

                handleDragMovement(deltaX);
            };

            const handleMouseUp = () => {
                endDragOperation();
            };

            document.addEventListener('mousemove', handleMouseMoveEvent);
            document.addEventListener('mouseup', handleMouseUp);

            return () => {
                document.removeEventListener('mousemove', handleMouseMoveEvent);
                document.removeEventListener('mouseup', handleMouseUp);
            };
        }
    }, [isDragging, activeMarker, handleDragMovement, endDragOperation, lastClientXRef]);

    // Touch drag effect
    useEffect(() => {
        if (!isDragging) return;

        const handleDocumentTouchMove = (e) => {
            e.preventDefault();
            e.stopPropagation();

            if (e.touches.length !== 1) return;

            const touch = e.touches[0];
            const deltaX = touch.clientX - lastTouchXRef.current;
            lastTouchXRef.current = touch.clientX;

            handleDragMovement(deltaX);
        };

        const handleDocumentTouchEnd = (e) => {
            e.preventDefault();
            e.stopPropagation();
            endDragOperation();
        };

        document.addEventListener('touchmove', handleDocumentTouchMove, { capture: true, passive: false });
        document.addEventListener('touchend', handleDocumentTouchEnd, { capture: true, passive: false });
        document.addEventListener('touchcancel', handleDocumentTouchEnd, { capture: true, passive: false });

        return () => {
            document.removeEventListener('touchmove', handleDocumentTouchMove, { capture: true });
            document.removeEventListener('touchend', handleDocumentTouchEnd, { capture: true });
            document.removeEventListener('touchcancel', handleDocumentTouchEnd, { capture: true });
        };
    }, [isDragging, handleDragMovement, endDragOperation, lastTouchXRef]);
};
