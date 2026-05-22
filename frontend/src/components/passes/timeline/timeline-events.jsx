import { useCallback, useRef } from 'react';
import { Y_AXIS_WIDTH, X_AXIS_HEIGHT, Y_AXIS_TOP_MARGIN, ZOOM_FACTOR } from './timeline-constants.jsx';

// Internal constant for past offset (30 minutes)
const PAST_OFFSET_HOURS = 0.1;

/**
 * Custom hook that returns all event handlers for the timeline component
 */
export const useTimelineEvents = ({
  isPanning,
  setIsPanning,
  timeWindowHours,
  setTimeWindowHours,
  timeWindowStart,
  setTimeWindowStart,
  timeWindowHoursRef,
  timeWindowStartRef,
  timelineData,
  setHoverPosition,
  setHoverTime,
  initialTimeWindowHours,
  panStartXRef,
  panStartTimeRef,
  lastTouchDistanceRef,
  touchStartTimeRef,
  touchStartZoomLevelRef,
  timezone,
  startTime,
  endTime,
  pastOffsetHours = PAST_OFFSET_HOURS,
  nextPassesHours = initialTimeWindowHours,
  forceTimeWindowStart = null,
  forceTimeWindowEnd = null,
}) => {
  // Refs for touch direction detection
  const touchStartXRef = useRef(null);
  const touchStartYRef = useRef(null);
  const touchDirectionDeterminedRef = useRef(false);

  // Use requestAnimationFrame for smooth updates during gestures
  const rafIdRef = useRef(null);
  const isGestureActiveRef = useRef(false);

  // Cache getBoundingClientRect during gestures to avoid forced layout recalculations
  const cachedRectRef = useRef(null);

  // RAF-based update function for smooth gestures
  const scheduleUpdate = useCallback((updates) => {
    // Update refs immediately
    if (updates.timeWindowHours !== undefined) {
      timeWindowHoursRef.current = updates.timeWindowHours;
    }
    if (updates.timeWindowStart !== undefined) {
      timeWindowStartRef.current = updates.timeWindowStart;
    }

    // Cancel any pending RAF
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
    }

    // Schedule state update for next frame
    rafIdRef.current = requestAnimationFrame(() => {
      if (updates.timeWindowHours !== undefined) {
        setTimeWindowHours(updates.timeWindowHours);
      }
      if (updates.timeWindowStart !== undefined) {
        setTimeWindowStart(updates.timeWindowStart);
      }
      rafIdRef.current = null;
    });
  }, [setTimeWindowHours, setTimeWindowStart]);

  const handleMouseMove = useCallback((e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Adjust for Y-axis on left
    const xAdjusted = x - Y_AXIS_WIDTH;
    const availableWidth = rect.width - Y_AXIS_WIDTH;
    const percentage = (xAdjusted / availableWidth) * 100;
    const yPercentage = (y / rect.height) * 100;

    // Convert cursor Y to an elevation value using chart area coordinates.
    const chartTop = Y_AXIS_TOP_MARGIN;
    const chartBottom = rect.height - X_AXIS_HEIGHT;
    const chartHeight = Math.max(1, chartBottom - chartTop);
    const clampedY = Math.max(chartTop, Math.min(chartBottom, y));
    const yPercentInChart = ((clampedY - chartTop) / chartHeight) * 100;
    const cursorElevation = 90 - ((yPercentInChart / 100) * 90);

    // Handle panning
    if (isPanning && panStartXRef.current !== null && panStartTimeRef.current !== null) {
      const deltaX = x - panStartXRef.current;
      const deltaPercentage = (deltaX / availableWidth) * 100;

      // Calculate time shift
      const totalMs = timeWindowHours * 60 * 60 * 1000;
      const timeShift = -(deltaPercentage / 100) * totalMs;

      const calculatedStartTime = panStartTimeRef.current + timeShift;
      const calculatedEndTime = calculatedStartTime + totalMs;

      // Apply boundaries based on forced time window or forecast window
      let minViewStartTime, maxViewEndTime;

      if (forceTimeWindowStart && forceTimeWindowEnd) {
        // Use forced time window boundaries
        minViewStartTime = new Date(forceTimeWindowStart).getTime();
        maxViewEndTime = new Date(forceTimeWindowEnd).getTime();
      } else {
        // Use default forecast window boundaries
        const now = Date.now();
        minViewStartTime = now - (pastOffsetHours * 3600000);
        maxViewEndTime = now + (nextPassesHours * 3600000);
      }

      // Constrain the view to stay within boundaries
      let boundedStartTime = calculatedStartTime;
      if (calculatedStartTime < minViewStartTime) {
        boundedStartTime = minViewStartTime;
      } else if (calculatedEndTime > maxViewEndTime) {
        boundedStartTime = maxViewEndTime - totalMs;
      }

      setTimeWindowStart(boundedStartTime);
      // Don't return here, continue to update crosshair
    }

    // Calculate time at this position using actual timeline window
    const actualStartTime = startTime || (timeWindowStart ? new Date(timeWindowStart) : new Date());
    const actualEndTime = endTime || new Date(actualStartTime.getTime() + timeWindowHours * 60 * 60 * 1000);
    const totalMs = actualEndTime.getTime() - actualStartTime.getTime();
    const timeAtPosition = new Date(actualStartTime.getTime() + (percentage / 100) * totalMs);

    // Find best pass candidate by selecting the curve closest to cursor Y.
    let bestHoverMatch = null;
    for (const pass of timelineData) {
      // If we have elevation_curve data, check against actual curve time range
      if (pass.elevation_curve && pass.elevation_curve.length > 0) {
        const curveStartTime = new Date(pass.elevation_curve[0].time).getTime();
        const curveEndTime = new Date(pass.elevation_curve[pass.elevation_curve.length - 1].time).getTime();

        // Check if hover time is within the elevation curve's time range
        if (timeAtPosition.getTime() >= curveStartTime && timeAtPosition.getTime() <= curveEndTime) {
          // Find the two closest points in the elevation curve
          let found = false;
          for (let i = 0; i < pass.elevation_curve.length - 1; i++) {
            const point1 = pass.elevation_curve[i];
            const point2 = pass.elevation_curve[i + 1];
            const time1 = new Date(point1.time).getTime();
            const time2 = new Date(point2.time).getTime();

            if (timeAtPosition.getTime() >= time1 && timeAtPosition.getTime() <= time2) {
              // Linear interpolation between the two points
              const t = (timeAtPosition.getTime() - time1) / (time2 - time1);
              const elevation = point1.elevation + t * (point2.elevation - point1.elevation);
              const distance = Math.abs(elevation - cursorElevation);
              if (!bestHoverMatch || distance < bestHoverMatch.distance) {
                bestHoverMatch = { pass, elevation, distance };
              }
              found = true;
              break;
            }
          }

          // If not found in the middle, check if we're at the last point
          if (!found && pass.elevation_curve.length > 0) {
            const lastPoint = pass.elevation_curve[pass.elevation_curve.length - 1];
            const lastTime = new Date(lastPoint.time).getTime();

            // If hovering on or after the last point, use its elevation
            if (timeAtPosition.getTime() >= lastTime) {
              const elevation = lastPoint.elevation;
              const distance = Math.abs(elevation - cursorElevation);
              if (!bestHoverMatch || distance < bestHoverMatch.distance) {
                bestHoverMatch = { pass, elevation, distance };
              }
            }
          }
        }
      } else if (pass.left !== undefined && pass.width !== undefined) {
        // Fallback to pass.left/width if elevation_curve not available
        if (percentage >= pass.left && percentage <= (pass.left + pass.width)) {
          // Fallback to parabolic curve formula
          const positionInPass = (percentage - pass.left) / pass.width;
          const elevationRatio = 4 * positionInPass * (1 - positionInPass);
          const elevation = pass.peak_altitude * elevationRatio;
          const distance = Math.abs(elevation - cursorElevation);
          if (!bestHoverMatch || distance < bestHoverMatch.distance) {
            bestHoverMatch = { pass, elevation, distance };
          }
        }
      }
    }

    setHoverPosition({
      x: percentage,
      y: yPercentage,
      elevation: bestHoverMatch ? bestHoverMatch.elevation : null,
      passName: bestHoverMatch ? bestHoverMatch.pass.name : null,
    });
    setHoverTime(timeAtPosition);
  }, [isPanning, timeWindowHours, timeWindowStart, timelineData, panStartXRef, panStartTimeRef, setTimeWindowStart, setHoverPosition, setHoverTime, pastOffsetHours, nextPassesHours, startTime, endTime]);

  const handleMouseLeave = useCallback(() => {
    setHoverPosition(null);
    setHoverTime(null);
    setIsPanning(false);
    panStartXRef.current = null;
    panStartTimeRef.current = null;
  }, [setHoverPosition, setHoverTime, setIsPanning, panStartXRef, panStartTimeRef]);

  const handleMouseDown = useCallback((e) => {
    // Enable panning always - can pan to past and future
    setIsPanning(true);
    panStartXRef.current = e.clientX - e.currentTarget.getBoundingClientRect().left;
    const currentStartTime = timeWindowStart ? new Date(timeWindowStart) : new Date();
    panStartTimeRef.current = currentStartTime.getTime();
    e.currentTarget.style.cursor = 'grabbing';
  }, [timeWindowStart, setIsPanning, panStartXRef, panStartTimeRef]);

  const handleMouseUp = useCallback((e) => {
    if (isPanning) {
      setIsPanning(false);
      e.currentTarget.style.cursor = 'grab';
    }
  }, [isPanning, setIsPanning]);

  const handleWheel = (e) => {
    if (!e.shiftKey) return;

    e.preventDefault();

    // Get mouse position to calculate time at cursor
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const xAdjusted = x - Y_AXIS_WIDTH;
    const availableWidth = rect.width - Y_AXIS_WIDTH;
    const percentage = (xAdjusted / availableWidth) * 100;

    // Calculate time at mouse position
    const now = new Date();
    const currentStartTime = timeWindowStart ? new Date(timeWindowStart) : new Date(now);
    const totalMs = timeWindowHours * 60 * 60 * 1000;
    const timeAtMouse = new Date(currentStartTime.getTime() + (percentage / 100) * totalMs);

    // Zoom factor: wheel down = zoom out, wheel up = zoom in
    const zoomFactor = e.deltaY > 0 ? ZOOM_FACTOR : (1 / ZOOM_FACTOR);
    const newTimeWindowHours = Math.max(0.5, Math.min(initialTimeWindowHours, timeWindowHours * zoomFactor));

    // Calculate new start time to keep mouse position at the same time
    const newTotalMs = newTimeWindowHours * 60 * 60 * 1000;
    const newStartTime = new Date(timeAtMouse.getTime() - (percentage / 100) * newTotalMs);

    setTimeWindowHours(newTimeWindowHours);
    setTimeWindowStart(newStartTime.getTime());
  };

  const handleTouchStart = useCallback((e) => {
    // Cache rect at start of gesture
    cachedRectRef.current = e.currentTarget.getBoundingClientRect();

    if (e.touches.length === 1) {
      // Single touch - record starting position but don't commit to panning yet
      const touch = e.touches[0];
      const rect = cachedRectRef.current;
      const x = touch.clientX - rect.left;
      const y = touch.clientY - rect.top;

      // Store initial touch position to detect scroll direction
      panStartXRef.current = x;
      panStartTimeRef.current = timeWindowStartRef.current ? timeWindowStartRef.current : new Date().getTime();
      touchStartTimeRef.current = panStartTimeRef.current;

      // Store Y position to detect vertical vs horizontal movement
      touchStartXRef.current = x;
      touchStartYRef.current = y;
      touchDirectionDeterminedRef.current = false;

      // Don't set isPanning yet - wait for touchmove to determine direction
    } else if (e.touches.length === 2) {
      // Two touches - start pinch zoom
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const distance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );

      lastTouchDistanceRef.current = distance;
      setIsPanning(false);

      // Clear single-touch tracking to prevent interference
      touchStartXRef.current = null;
      touchStartYRef.current = null;
      touchDirectionDeterminedRef.current = false;

      // Store current time window start and zoom level for pinch zoom
      const currentStartTime = timeWindowStartRef.current ? new Date(timeWindowStartRef.current) : new Date();
      touchStartTimeRef.current = currentStartTime.getTime();
      touchStartZoomLevelRef.current = timeWindowHoursRef.current; // Store CURRENT zoom level
    }
  }, [setIsPanning]);

  const handleTouchMove = useCallback((e) => {
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      const rect = cachedRectRef.current || e.currentTarget.getBoundingClientRect();
      const x = touch.clientX - rect.left;
      const y = touch.clientY - rect.top;

      // Detect scroll direction on first move
      if (!touchDirectionDeterminedRef.current && touchStartXRef.current !== null && touchStartYRef.current !== null) {
        const deltaX = Math.abs(x - touchStartXRef.current);
        const deltaY = Math.abs(y - touchStartYRef.current);

        // Threshold to determine if user is scrolling (5px)
        if (deltaX > 5 || deltaY > 5) {
          touchDirectionDeterminedRef.current = true;

          // If more vertical than horizontal movement, allow page scroll
          if (deltaY > deltaX) {
            // Vertical scroll - don't prevent default, let page scroll
            touchStartXRef.current = null;
            touchStartYRef.current = null;
            return;
          } else {
            // Horizontal movement detected - start timeline panning and prevent default
            e.preventDefault();
            setIsPanning(true);
          }
        } else {
          // Movement too small - don't prevent default yet, allow browser to handle it
          // This allows vertical scroll to work naturally
          return;
        }
      }

      // Only handle horizontal panning if we've committed to it
      if (isPanning && panStartXRef.current !== null && panStartTimeRef.current !== null) {
        // Prevent default for horizontal panning
        e.preventDefault();

        const deltaX = x - panStartXRef.current;
        const availableWidth = rect.width - Y_AXIS_WIDTH;
        const deltaPercentage = (deltaX / availableWidth) * 100;

        const totalMs = timeWindowHoursRef.current * 60 * 60 * 1000;
        const timeShift = -(deltaPercentage / 100) * totalMs;

        const calculatedStartTime = panStartTimeRef.current + timeShift;
        const calculatedEndTime = calculatedStartTime + totalMs;

        // Apply boundaries based on forced time window or forecast window
        let minViewStartTime, maxViewEndTime;

        if (forceTimeWindowStart && forceTimeWindowEnd) {
          // Use forced time window boundaries
          minViewStartTime = new Date(forceTimeWindowStart).getTime();
          maxViewEndTime = new Date(forceTimeWindowEnd).getTime();
        } else {
          // Use default forecast window boundaries
          const now = Date.now();
          minViewStartTime = now - (pastOffsetHours * 3600000);
          maxViewEndTime = now + (nextPassesHours * 3600000);
        }

        // Constrain the view to stay within boundaries
        let boundedStartTime = calculatedStartTime;
        if (calculatedStartTime < minViewStartTime) {
          boundedStartTime = minViewStartTime;
        } else if (calculatedEndTime > maxViewEndTime) {
          boundedStartTime = maxViewEndTime - totalMs;
        }

        scheduleUpdate({ timeWindowStart: boundedStartTime });
      } else if (isPanning) {
        // We're in panning mode but refs are missing - still prevent default
        e.preventDefault();
      }
    } else if (e.touches.length === 2 && lastTouchDistanceRef.current !== null && touchStartTimeRef.current !== null && touchStartZoomLevelRef.current !== null) {
      // Prevent default for pinch zoom - ALWAYS
      e.preventDefault();
      // Two touches - pinch zoom
      const touch1 = e.touches[0];
      const touch2 = e.touches[1];
      const rect = cachedRectRef.current || e.currentTarget.getBoundingClientRect();

      const currentDistance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );

      // Calculate zoom based on pinch distance change from the STARTING zoom level
      const zoomRatio = currentDistance / lastTouchDistanceRef.current;
      const startingZoomLevel = touchStartZoomLevelRef.current;
      const newTimeWindowHours = Math.max(0.5, Math.min(initialTimeWindowHours, startingZoomLevel / zoomRatio));

      // Calculate center point between two touches
      const centerX = (touch1.clientX + touch2.clientX) / 2 - rect.left;
      const xAdjusted = centerX - Y_AXIS_WIDTH;
      const availableWidth = rect.width - Y_AXIS_WIDTH;
      const percentage = Math.max(0, Math.min(100, (xAdjusted / availableWidth) * 100));

      // Calculate time at center point using the ORIGINAL start time and zoom level
      const originalStartTime = new Date(touchStartTimeRef.current);
      const originalTotalMs = startingZoomLevel * 60 * 60 * 1000;
      const timeAtCenter = new Date(originalStartTime.getTime() + (percentage / 100) * originalTotalMs);

      // Calculate new start time to keep center point at the same time
      const newTotalMs = newTimeWindowHours * 60 * 60 * 1000;
      const newStartTime = new Date(timeAtCenter.getTime() - (percentage / 100) * newTotalMs);

      scheduleUpdate({
        timeWindowHours: newTimeWindowHours,
        timeWindowStart: newStartTime.getTime()
      });
    } else if (e.touches.length === 2) {
      // Two fingers but refs not set up - still prevent default to avoid browser gestures
      e.preventDefault();
    }
  }, [isPanning, setIsPanning, initialTimeWindowHours, scheduleUpdate, pastOffsetHours, nextPassesHours]);

  const handleTouchEnd = useCallback((e) => {
    if (e.touches.length === 0) {
      setIsPanning(false);
      lastTouchDistanceRef.current = null;
      panStartXRef.current = null;
      panStartTimeRef.current = null;

      // Clean up touch tracking
      touchStartXRef.current = null;
      touchStartYRef.current = null;
      touchDirectionDeterminedRef.current = false;
      cachedRectRef.current = null; // Clear cached rect
    } else if (e.touches.length === 1) {
      // Went from 2 touches to 1, restart panning detection
      lastTouchDistanceRef.current = null;
      const touch = e.touches[0];
      const rect = e.currentTarget.getBoundingClientRect();
      const x = touch.clientX - rect.left;
      const y = touch.clientY - rect.top;

      // Reset for new single-touch gesture
      setIsPanning(false);
      panStartXRef.current = x;
      const currentStartTime = timeWindowStartRef.current ? new Date(timeWindowStartRef.current) : new Date();
      panStartTimeRef.current = currentStartTime.getTime();

      // Store new touch start position for direction detection
      touchStartXRef.current = x;
      touchStartYRef.current = y;
      touchDirectionDeterminedRef.current = false;
    }
  }, [setIsPanning]);

  const formatHoverTime = (date) => {
    if (!date) return '';
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: timezone
    });
  };

  const handleZoomIn = () => {
    const newTimeWindowHours = Math.max(0.5, timeWindowHours / ZOOM_FACTOR);
    setTimeWindowHours(newTimeWindowHours);
  };

  const handleZoomOut = () => {
    // If forced time window is set, zoom out to that window
    if (forceTimeWindowStart && forceTimeWindowEnd) {
      const forcedStart = new Date(forceTimeWindowStart).getTime();
      const forcedEnd = new Date(forceTimeWindowEnd).getTime();
      const forcedWindowHours = (forcedEnd - forcedStart) / (60 * 60 * 1000);

      const newTimeWindowHours = Math.min(forcedWindowHours, timeWindowHours * ZOOM_FACTOR);
      setTimeWindowHours(newTimeWindowHours);

      // If we're zooming to the full forced window, align to it
      if (newTimeWindowHours >= forcedWindowHours) {
        setTimeWindowStart(forcedStart);
      }
    } else {
      const newTimeWindowHours = Math.min(initialTimeWindowHours, timeWindowHours * ZOOM_FACTOR);
      setTimeWindowHours(newTimeWindowHours);
    }
  };

  const handleResetZoom = useCallback(() => {
    // If forced time window is set, reset to that window
    if (forceTimeWindowStart && forceTimeWindowEnd) {
      const forcedStart = new Date(forceTimeWindowStart).getTime();
      const forcedEnd = new Date(forceTimeWindowEnd).getTime();
      const forcedWindowHours = (forcedEnd - forcedStart) / (60 * 60 * 1000);

      setTimeWindowHours(forcedWindowHours);
      setTimeWindowStart(forcedStart);
    } else {
      setTimeWindowHours(initialTimeWindowHours);
      // Set start time to 30 minutes in the past
      const now = new Date();
      setTimeWindowStart(now.getTime() - (PAST_OFFSET_HOURS * 60 * 60 * 1000));
    }
  }, [initialTimeWindowHours, setTimeWindowHours, setTimeWindowStart, forceTimeWindowStart, forceTimeWindowEnd]);

  return {
    handleMouseMove,
    handleMouseLeave,
    handleMouseDown,
    handleMouseUp,
    handleWheel,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    formatHoverTime,
    handleZoomIn,
    handleZoomOut,
    handleResetZoom,
  };
};
