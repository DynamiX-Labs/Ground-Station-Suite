import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export const TOOLTIP_DIRECTIONS = Object.freeze(['bottom', 'right', 'left', 'top']);

const DEFAULT_TOOLTIP_SIZE = Object.freeze({ width: 220, height: 48 });
const DEFAULT_EDGE_PADDING = 8;
const DEFAULT_ANCHOR_DISTANCE = 20;

const toPositiveNumber = (value, fallback) => {
    const numericValue = Number(value);
    return Number.isFinite(numericValue) && numericValue > 0 ? numericValue : fallback;
};

const isValidContainerPoint = (point) =>
    point
    && Number.isFinite(Number(point.x))
    && Number.isFinite(Number(point.y));

const isValidMapSize = (mapSize) =>
    mapSize
    && Number.isFinite(Number(mapSize.x))
    && Number.isFinite(Number(mapSize.y))
    && Number(mapSize.x) > 0
    && Number(mapSize.y) > 0;

const normalizeTooltipSize = (tooltipSize) => ({
    width: toPositiveNumber(tooltipSize?.width, DEFAULT_TOOLTIP_SIZE.width),
    height: toPositiveNumber(tooltipSize?.height, DEFAULT_TOOLTIP_SIZE.height),
});

const getTooltipBounds = ({ direction, anchorPoint, tooltipSize, anchorDistance }) => {
    const x = Number(anchorPoint.x);
    const y = Number(anchorPoint.y);
    const width = tooltipSize.width;
    const height = tooltipSize.height;
    const distance = toPositiveNumber(anchorDistance, DEFAULT_ANCHOR_DISTANCE);

    switch (direction) {
        case 'top':
            return {
                left: x - (width / 2),
                top: y - distance - height,
                right: x + (width / 2),
                bottom: y - distance,
            };
        case 'right':
            return {
                left: x + distance,
                top: y - (height / 2),
                right: x + distance + width,
                bottom: y + (height / 2),
            };
        case 'left':
            return {
                left: x - distance - width,
                top: y - (height / 2),
                right: x - distance,
                bottom: y + (height / 2),
            };
        case 'bottom':
        default:
            return {
                left: x - (width / 2),
                top: y + distance,
                right: x + (width / 2),
                bottom: y + distance + height,
            };
    }
};

const getOverflow = ({ bounds, mapSize, edgePadding }) => {
    const safePadding = Math.max(0, Number(edgePadding) || 0);
    const minX = safePadding;
    const minY = safePadding;
    const maxX = Number(mapSize.x) - safePadding;
    const maxY = Number(mapSize.y) - safePadding;

    const overflowLeft = Math.max(0, minX - bounds.left);
    const overflowTop = Math.max(0, minY - bounds.top);
    const overflowRight = Math.max(0, bounds.right - maxX);
    const overflowBottom = Math.max(0, bounds.bottom - maxY);
    return overflowLeft + overflowTop + overflowRight + overflowBottom;
};

export const getTooltipOffsetByDirection = (direction, anchorDistance = DEFAULT_ANCHOR_DISTANCE) => {
    const distance = toPositiveNumber(anchorDistance, DEFAULT_ANCHOR_DISTANCE);
    switch (direction) {
        case 'top':
            return [0, -distance];
        case 'right':
            return [distance, 0];
        case 'left':
            return [-distance, 0];
        case 'bottom':
        default:
            return [0, distance];
    }
};

export const pickTooltipDirection = ({
    anchorPoint,
    mapSize,
    tooltipSize = DEFAULT_TOOLTIP_SIZE,
    preferredDirections = TOOLTIP_DIRECTIONS,
    anchorDistance = DEFAULT_ANCHOR_DISTANCE,
    edgePadding = DEFAULT_EDGE_PADDING,
}) => {
    if (!isValidContainerPoint(anchorPoint) || !isValidMapSize(mapSize)) {
        return TOOLTIP_DIRECTIONS[0];
    }

    const directions = Array.isArray(preferredDirections) && preferredDirections.length > 0
        ? preferredDirections.filter((direction) => TOOLTIP_DIRECTIONS.includes(direction))
        : TOOLTIP_DIRECTIONS;
    const orderedDirections = directions.length > 0 ? directions : TOOLTIP_DIRECTIONS;
    const normalizedTooltipSize = normalizeTooltipSize(tooltipSize);

    let bestDirection = orderedDirections[0];
    let smallestOverflow = Number.POSITIVE_INFINITY;

    for (const direction of orderedDirections) {
        const bounds = getTooltipBounds({
            direction,
            anchorPoint,
            tooltipSize: normalizedTooltipSize,
            anchorDistance,
        });
        const overflow = getOverflow({ bounds, mapSize, edgePadding });

        if (overflow < smallestOverflow) {
            smallestOverflow = overflow;
            bestDirection = direction;

            if (overflow === 0) {
                break;
            }
        }
    }

    return bestDirection;
};

export const useTooltipOrientation = ({
    map,
    markerRef = null,
    position,
    preferredDirections = TOOLTIP_DIRECTIONS,
    anchorDistance = DEFAULT_ANCHOR_DISTANCE,
    edgePadding = DEFAULT_EDGE_PADDING,
}) => {
    const directionOrder = useMemo(() => (
        Array.isArray(preferredDirections) && preferredDirections.length > 0
            ? preferredDirections
            : TOOLTIP_DIRECTIONS
    ), [preferredDirections]);
    const [direction, setDirection] = useState(directionOrder[0] || TOOLTIP_DIRECTIONS[0]);
    const pendingRetryFrameRef = useRef(null);
    const retryCountRef = useRef(0);

    const getTooltipElement = useCallback(() => (
        markerRef?.current?.getTooltip?.()?.getElement?.() || null
    ), [markerRef]);

    const clearPendingRetry = useCallback(() => {
        if (pendingRetryFrameRef.current != null) {
            cancelAnimationFrame(pendingRetryFrameRef.current);
            pendingRetryFrameRef.current = null;
        }
    }, []);

    const updateOrientation = useCallback(() => {
        if (!map || !Array.isArray(position) || position.length !== 2) {
            return;
        }

        const lat = Number(position[0]);
        const lon = Number(position[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
            return;
        }

        const mapSize = map.getSize?.();
        if (!isValidMapSize(mapSize)) {
            return;
        }

        const anchorPoint = map.latLngToContainerPoint([lat, lon]);
        if (!isValidContainerPoint(anchorPoint)) {
            return;
        }

        const tooltipElement = getTooltipElement();
        const tooltipSize = tooltipElement
            ? { width: tooltipElement.offsetWidth, height: tooltipElement.offsetHeight }
            : DEFAULT_TOOLTIP_SIZE;

        if (!tooltipElement) {
            // Tooltip DOM for permanent tooltips may appear a tick later than marker mount.
            // Retry a few frames so we can measure the real element instead of default size.
            if (retryCountRef.current < 8) {
                retryCountRef.current += 1;
                clearPendingRetry();
                pendingRetryFrameRef.current = requestAnimationFrame(() => {
                    pendingRetryFrameRef.current = null;
                    updateOrientation();
                });
            }
        } else {
            retryCountRef.current = 0;
        }

        const nextDirection = pickTooltipDirection({
            anchorPoint,
            mapSize,
            tooltipSize,
            preferredDirections: directionOrder,
            anchorDistance,
            edgePadding,
        });

        setDirection((currentDirection) => (
            currentDirection === nextDirection ? currentDirection : nextDirection
        ));
    }, [anchorDistance, clearPendingRetry, directionOrder, edgePadding, getTooltipElement, map, position]);

    useEffect(() => {
        if (!map) {
            return undefined;
        }

        let animationFrameId = requestAnimationFrame(updateOrientation);
        const scheduleOrientationUpdate = () => {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = requestAnimationFrame(updateOrientation);
        };

        map.on('moveend zoomend resize', scheduleOrientationUpdate);
        return () => {
            cancelAnimationFrame(animationFrameId);
            map.off('moveend zoomend resize', scheduleOrientationUpdate);
            clearPendingRetry();
        };
    }, [clearPendingRetry, map, updateOrientation]);

    useEffect(() => {
        const animationFrameId = requestAnimationFrame(updateOrientation);
        return () => cancelAnimationFrame(animationFrameId);
    }, [updateOrientation]);

    useEffect(() => {
        const tooltipElement = getTooltipElement();
        if (!tooltipElement || typeof ResizeObserver === 'undefined') {
            return undefined;
        }

        const resizeObserver = new ResizeObserver(() => {
            updateOrientation();
        });
        resizeObserver.observe(tooltipElement);
        return () => resizeObserver.disconnect();
    }, [direction, getTooltipElement, updateOrientation]);

    useEffect(() => () => {
        clearPendingRetry();
    }, [clearPendingRetry]);

    const offset = useMemo(
        () => getTooltipOffsetByDirection(direction, anchorDistance),
        [anchorDistance, direction],
    );

    return {
        direction,
        offset,
    };
};
