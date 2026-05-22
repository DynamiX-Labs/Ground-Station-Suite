import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Box, Typography } from '@mui/material';
import { useTheme } from '@mui/material/styles';

const PLANET_COLORS = {
    mercury: '#c2b280',
    venus: '#d6b57d',
    earth: '#4f8cff',
    moon: '#cfd8dc',
    mars: '#c04f3d',
    jupiter: '#d2a679',
    io: '#f4e6b3',
    europa: '#d8d8cf',
    ganymede: '#bfae95',
    callisto: '#a89f91',
    saturn: '#d9c188',
    enceladus: '#dbe9f4',
    rhea: '#c9c1b6',
    titan: '#d8b078',
    iapetus: '#b8b0a2',
    uranus: '#76c7c0',
    neptune: '#5a7bd8',
};

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const MIN_ZOOM = 1;
const MAX_ZOOM = 20000;
const WHEEL_COMMIT_DELAY_MS = 180;
const FOCUS_ANIMATION_DURATION_MS = 420;
const DEFAULT_VIEWPORT = { zoom: 18, panX: 0, panY: 0 };
const OFFSCREEN_TARGET_EDGE_INSET_PX = 12;
const OFFSCREEN_TARGET_VISIBILITY_PADDING_PX = 6;
const OFFSCREEN_TARGET_ARROW_LENGTH_PX = 14;
const OFFSCREEN_TARGET_LABEL_GAP_PX = 18;
const OFFSCREEN_TARGET_STAGGER_PX = 14;
const OFFSCREEN_TARGET_LABEL_DEPTH_STEP_PX = 9;
const OFFSCREEN_TARGET_LABEL_SEARCH_STEPS = 7;
const OFFSCREEN_TARGET_LABEL_SAFE_MARGIN_PX = 4;
const MAX_BACKGROUND_RING_RADIUS_PX = 12000;
const MAX_ZONE_LABEL_RADIUS_PX = 3600;
const DEFAULT_DISPLAY_OPTIONS = {
    showGrid: true,
    showPlanets: true,
    showPlanetLabels: true,
    showPlanetOrbits: true,
    showTrackedObjects: true,
    showTrackedOrbits: true,
    showTrackedLabels: true,
    showAsteroidZones: true,
    showZoneLabels: true,
    showResonanceMarkers: true,
    showTimestamp: true,
    showScaleIndicator: true,
    showGestureHint: true,
};
const normalizeViewport = (viewport) => ({
    zoom: clamp(Number(viewport?.zoom ?? DEFAULT_VIEWPORT.zoom), MIN_ZOOM, MAX_ZOOM),
    panX: Number(viewport?.panX ?? DEFAULT_VIEWPORT.panX) || 0,
    panY: Number(viewport?.panY ?? DEFAULT_VIEWPORT.panY) || 0,
});
const formatAu = (value) => {
    if (value >= 1) return `${value.toFixed(value >= 10 ? 0 : 1)} AU`;
    return `${value.toFixed(2)} AU`;
};
const hexToRgba = (hex, alpha) => {
    const value = String(hex || '').trim().replace('#', '');
    if (!/^[0-9a-fA-F]{6}$/.test(value)) return `rgba(120,150,190,${alpha})`;
    const r = Number.parseInt(value.slice(0, 2), 16);
    const g = Number.parseInt(value.slice(2, 4), 16);
    const b = Number.parseInt(value.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${alpha})`;
};
const resolveTrackedColor = (body, fallbackHex) => {
    const value = String(body?.color || '').trim();
    if (/^#[0-9a-fA-F]{6}$/.test(value)) {
        return value;
    }
    return fallbackHex;
};
const ASTEROID_ZONE_FALLBACK_COLORS = {
    imb: '#4F8CFF',
    mmb: '#4FC3A1',
    omb: '#E0A458',
    tjn: '#D97AA8',
    kuiper: '#5EC8E5',
    scattered: '#8BA6FF',
};
const resolveAsteroidZoneColor = (zone) => {
    if (zone?.color_hex) return zone.color_hex;

    const normalizedId = String(zone?.id || '').trim().toLowerCase();
    if (ASTEROID_ZONE_FALLBACK_COLORS[normalizedId]) {
        return ASTEROID_ZONE_FALLBACK_COLORS[normalizedId];
    }

    const normalizedClass = String(zone?.class_code || '').trim().toLowerCase();
    if (ASTEROID_ZONE_FALLBACK_COLORS[normalizedClass]) {
        return ASTEROID_ZONE_FALLBACK_COLORS[normalizedClass];
    }

    const normalizedName = String(zone?.name || '').trim().toLowerCase();
    if (normalizedName.includes('inner')) return ASTEROID_ZONE_FALLBACK_COLORS.imb;
    if (normalizedName.includes('middle')) return ASTEROID_ZONE_FALLBACK_COLORS.mmb;
    if (normalizedName.includes('outer')) return ASTEROID_ZONE_FALLBACK_COLORS.omb;
    if (normalizedName.includes('trojan')) return ASTEROID_ZONE_FALLBACK_COLORS.tjn;
    if (normalizedName.includes('kuiper')) return ASTEROID_ZONE_FALLBACK_COLORS.kuiper;
    if (normalizedName.includes('scattered')) return ASTEROID_ZONE_FALLBACK_COLORS.scattered;
    return '#7F9CB8';
};
const getTwoPointerGesture = (pointerMap) => {
    if (pointerMap.size < 2) return null;
    const points = Array.from(pointerMap.values());
    const p1 = points[0];
    const p2 = points[1];
    const centerX = (p1.x + p2.x) / 2;
    const centerY = (p1.y + p2.y) / 2;
    const distance = Math.hypot(p2.x - p1.x, p2.y - p1.y);
    return {
        centerX,
        centerY,
        distance,
    };
};
const hasFiniteXYZ = (position) =>
    Array.isArray(position)
    && position.length >= 3
    && Number.isFinite(Number(position[0]))
    && Number.isFinite(Number(position[1]))
    && Number.isFinite(Number(position[2]));

const hasFiniteXY = (position) =>
    Array.isArray(position)
    && position.length >= 2
    && Number.isFinite(Number(position[0]))
    && Number.isFinite(Number(position[1]));

const resolveTargetKey = (body) => {
    const explicit = String(body?.target_key || '').trim();
    if (explicit) return explicit;
    const type = String(body?.target_type || 'mission').toLowerCase();
    if (type === 'body') {
        const bodyId = String(body?.body_id || body?.command || '').toLowerCase();
        return bodyId ? `body:${bodyId}` : '';
    }
    const command = String(body?.command || '').trim();
    return command ? `mission:${command}` : '';
};

const drawArrowHead = (ctx, fromX, fromY, toX, toY, color) => {
    const dx = toX - fromX;
    const dy = toY - fromY;
    const length = Math.hypot(dx, dy);
    if (length < 0.01) return;

    const ux = dx / length;
    const uy = dy / length;
    const arrowLength = 8;
    const arrowWidth = 5;
    const baseX = toX - ux * arrowLength;
    const baseY = toY - uy * arrowLength;
    const perpX = -uy;
    const perpY = ux;

    ctx.beginPath();
    ctx.moveTo(toX, toY);
    ctx.lineTo(baseX + perpX * arrowWidth, baseY + perpY * arrowWidth);
    ctx.lineTo(baseX - perpX * arrowWidth, baseY - perpY * arrowWidth);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
};
const drawTextOnArc = (ctx, text, cx, cy, radius, centerAngle, style = {}) => {
    const value = String(text || '');
    if (!value || radius <= 0) return;

    const {
        font = '10px monospace',
        color = 'rgba(220,230,240,0.42)',
        clockwise = true,
    } = style;

    ctx.save();
    ctx.font = font;
    ctx.fillStyle = color;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const chars = Array.from(value);
    const charWidths = chars.map((char) => Math.max(1, ctx.measureText(char).width));
    const totalArc = charWidths.reduce((sum, width) => sum + (width / radius), 0);
    let angle = centerAngle - totalArc / 2;

    chars.forEach((char, index) => {
        const charArc = charWidths[index] / radius;
        const charAngle = angle + charArc / 2;
        const x = cx + radius * Math.cos(charAngle);
        const y = cy + radius * Math.sin(charAngle);

        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(charAngle + (clockwise ? Math.PI / 2 : -Math.PI / 2));
        ctx.fillText(char, 0, 0);
        ctx.restore();

        angle += charArc;
    });

    ctx.restore();
};
const isPointInsideViewport = (x, y, width, height, padding = 0) => (
    x >= padding
    && x <= (width - padding)
    && y >= padding
    && y <= (height - padding)
);
const projectToViewportEdge = ({
    fromX,
    fromY,
    toX,
    toY,
    minX,
    minY,
    maxX,
    maxY,
}) => {
    const dx = toX - fromX;
    const dy = toY - fromY;
    if (Math.abs(dx) < 0.0001 && Math.abs(dy) < 0.0001) return null;

    const tx = Math.abs(dx) < 0.0001 ? Infinity : (dx > 0 ? (maxX - fromX) / dx : (minX - fromX) / dx);
    const ty = Math.abs(dy) < 0.0001 ? Infinity : (dy > 0 ? (maxY - fromY) / dy : (minY - fromY) / dy);
    const t = Math.min(tx, ty);
    if (!Number.isFinite(t) || t <= 0) return null;

    return {
        x: fromX + dx * t,
        y: fromY + dy * t,
    };
};

const SolarSystemCanvas = ({
    scene,
    selectedTargetKeys = [],
    fitAllSignal = 0,
    focusTargetSignal = 0,
    focusTargetKey = '',
    instantFocus = false,
    zoomInSignal = 0,
    zoomOutSignal = 0,
    resetZoomSignal = 0,
    initialViewport = null,
    onViewportCommit = null,
    displayOptions = DEFAULT_DISPLAY_OPTIONS,
}) => {
    const theme = useTheme();
    const containerRef = useRef(null);
    const canvasRef = useRef(null);
    const wheelCommitTimeoutRef = useRef(null);
    const viewportAnimationRef = useRef(null);
    const lastFitSignalRef = useRef(fitAllSignal);
    const lastFocusTargetSignalRef = useRef(focusTargetSignal);
    const lastZoomInSignalRef = useRef(zoomInSignal);
    const lastZoomOutSignalRef = useRef(zoomOutSignal);
    const lastResetZoomSignalRef = useRef(resetZoomSignal);
    const hasPersistentViewportRef = useRef(!!initialViewport);
    const viewportRef = useRef(DEFAULT_VIEWPORT);
    const activePointersRef = useRef(new Map());
    const gestureRef = useRef({
        mode: null,
        lastCenterX: 0,
        lastCenterY: 0,
        lastDistance: 0,
    });
    const touchGestureRef = useRef({
        active: false,
        lastCenterX: 0,
        lastCenterY: 0,
        lastDistance: 0,
    });

    const [viewport, setViewport] = useState(() => normalizeViewport(initialViewport || DEFAULT_VIEWPORT));

    const planets = scene?.planets || [];
    const tracked = scene?.celestial || [];
    const selectedTargetKeySet = useMemo(
        () => new Set((selectedTargetKeys || []).map((value) => String(value || '').trim()).filter(Boolean)),
        [selectedTargetKeys],
    );
    const hasTrackedSelection = selectedTargetKeySet.size > 0;
    const asteroidZones = scene?.asteroid_zones || [];
    const asteroidResonanceGaps = scene?.asteroid_resonance_gaps || [];
    const effectiveDisplayOptions = {
        ...DEFAULT_DISPLAY_OPTIONS,
        ...(displayOptions || {}),
    };

    const commitViewport = useCallback((nextViewport) => {
        hasPersistentViewportRef.current = true;
        if (onViewportCommit) {
            onViewportCommit(normalizeViewport(nextViewport));
        }
    }, [onViewportCommit]);

    const cancelViewportAnimation = useCallback(() => {
        if (viewportAnimationRef.current !== null) {
            window.cancelAnimationFrame(viewportAnimationRef.current);
            viewportAnimationRef.current = null;
        }
    }, []);

    const animateViewportTo = useCallback((nextViewport, durationMs = FOCUS_ANIMATION_DURATION_MS) => {
        cancelViewportAnimation();
        const target = normalizeViewport(nextViewport);
        const start = viewportRef.current;
        const duration = Math.max(80, Number(durationMs) || FOCUS_ANIMATION_DURATION_MS);
        const startedAt = performance.now();
        const easeInOutCubic = (t) =>
            t < 0.5 ? 4 * t * t * t : 1 - ((-2 * t + 2) ** 3) / 2;

        const tick = (now) => {
            const elapsed = now - startedAt;
            const progress = Math.min(1, elapsed / duration);
            const eased = easeInOutCubic(progress);
            const interpolated = {
                zoom: start.zoom + (target.zoom - start.zoom) * eased,
                panX: start.panX + (target.panX - start.panX) * eased,
                panY: start.panY + (target.panY - start.panY) * eased,
            };
            viewportRef.current = interpolated;
            setViewport(interpolated);

            if (progress < 1) {
                viewportAnimationRef.current = window.requestAnimationFrame(tick);
                return;
            }

            viewportAnimationRef.current = null;
            viewportRef.current = target;
            setViewport(target);
            commitViewport(target);
        };

        viewportAnimationRef.current = window.requestAnimationFrame(tick);
    }, [cancelViewportAnimation, commitViewport]);

    const fitAll = useCallback(() => {
        const container = containerRef.current;
        if (!container) return;

        const rect = container.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        const points = [];
        planets.forEach((planet) => {
            if (Array.isArray(planet.position_xyz_au)) {
                points.push(planet.position_xyz_au);
            }
            const samples = planet.orbit_samples_xyz_au || [];
            samples.forEach((sample) => {
                if (Array.isArray(sample)) points.push(sample);
            });
        });
        tracked.forEach((body) => {
            if (hasFiniteXYZ(body.position_xyz_au)) {
                points.push(body.position_xyz_au);
            }
            const samples = body.orbit_samples_xyz_au || [];
            samples.forEach((sample) => {
                if (hasFiniteXY(sample)) points.push(sample);
            });
        });

        if (!points.length) {
            const fallbackViewport = normalizeViewport(DEFAULT_VIEWPORT);
            setViewport(fallbackViewport);
            commitViewport(fallbackViewport);
            return;
        }

        let minX = Infinity;
        let maxX = -Infinity;
        let minY = Infinity;
        let maxY = -Infinity;
        points.forEach((p) => {
            const x = Number(p[0] || 0);
            const y = Number(p[1] || 0);
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        });

        const spanX = Math.max(0.1, maxX - minX);
        const spanY = Math.max(0.1, maxY - minY);
        const padding = 0.88;
        const zoomX = (rect.width * padding) / spanX;
        const zoomY = (rect.height * padding) / spanY;
        const nextZoom = clamp(Math.min(zoomX, zoomY), MIN_ZOOM, MAX_ZOOM);

        const worldCenterX = (minX + maxX) / 2;
        const worldCenterY = (minY + maxY) / 2;

        const nextViewport = {
            zoom: nextZoom,
            panX: -worldCenterX * nextZoom,
            panY: worldCenterY * nextZoom,
        };
        setViewport(nextViewport);
        commitViewport(nextViewport);
    }, [planets, tracked, commitViewport]);

    const fitTarget = useCallback((targetKey) => {
        const key = String(targetKey || '').trim();
        if (!key) return;
        const container = containerRef.current;
        if (!container) return;
        const rect = container.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        const selectedBody = tracked.find((body) => resolveTargetKey(body) === key);
        if (!selectedBody) return;

        const points = [];
        if (hasFiniteXYZ(selectedBody.position_xyz_au)) {
            points.push(selectedBody.position_xyz_au);
        }
        const samples = Array.isArray(selectedBody.orbit_samples_xyz_au)
            ? selectedBody.orbit_samples_xyz_au
            : [];
        samples.forEach((sample) => {
            if (hasFiniteXY(sample)) points.push(sample);
        });
        if (!points.length) return;

        let minX = Infinity;
        let maxX = -Infinity;
        let minY = Infinity;
        let maxY = -Infinity;
        points.forEach((point) => {
            const x = Number(point[0] || 0);
            const y = Number(point[1] || 0);
            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;
        });

        const spanX = Math.max(0.02, maxX - minX);
        const spanY = Math.max(0.02, maxY - minY);
        const padding = 0.78;
        const zoomX = (rect.width * padding) / spanX;
        const zoomY = (rect.height * padding) / spanY;
        const nextZoom = clamp(Math.min(zoomX, zoomY), MIN_ZOOM, MAX_ZOOM);

        const worldCenterX = (minX + maxX) / 2;
        const worldCenterY = (minY + maxY) / 2;
        const nextViewport = {
            zoom: nextZoom,
            panX: -worldCenterX * nextZoom,
            panY: worldCenterY * nextZoom,
        };
        if (instantFocus) {
            cancelViewportAnimation();
            viewportRef.current = nextViewport;
            setViewport(nextViewport);
            commitViewport(nextViewport);
            return;
        }
        animateViewportTo(nextViewport, FOCUS_ANIMATION_DURATION_MS);
    }, [tracked, animateViewportTo, cancelViewportAnimation, commitViewport, instantFocus]);

    const applyZoomAtScreenPoint = useCallback((zoomFactor, anchorX, anchorY) => {
        const container = containerRef.current;
        if (!container || !Number.isFinite(zoomFactor) || zoomFactor <= 0) return null;

        const rect = container.getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;
        if (width <= 0 || height <= 0) return null;

        const prev = viewportRef.current;
        const nextZoom = clamp(prev.zoom * zoomFactor, MIN_ZOOM, MAX_ZOOM);
        const prevCx = width / 2 + prev.panX;
        const prevCy = height / 2 + prev.panY;

        const worldX = (anchorX - prevCx) / prev.zoom;
        const worldY = (prevCy - anchorY) / prev.zoom;
        const nextCx = anchorX - worldX * nextZoom;
        const nextCy = anchorY + worldY * nextZoom;

        const next = {
            zoom: nextZoom,
            panX: nextCx - width / 2,
            panY: nextCy - height / 2,
        };
        viewportRef.current = next;
        setViewport(next);
        return next;
    }, []);

    const drawScene = useCallback(() => {
        const container = containerRef.current;
        const canvas = canvasRef.current;
        if (!container || !canvas) return;

        const rect = container.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        const dpr = window.devicePixelRatio || 1;
        const width = Math.floor(rect.width);
        const height = Math.floor(rect.height);

        if (canvas.width !== Math.floor(width * dpr) || canvas.height !== Math.floor(height * dpr)) {
            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            canvas.style.width = `${width}px`;
            canvas.style.height = `${height}px`;
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, width, height);

        // Background.
        ctx.fillStyle = theme.palette.background.default;
        ctx.fillRect(0, 0, width, height);

        const cx = width / 2 + viewport.panX;
        const cy = height / 2 + viewport.panY;
        const scale = viewport.zoom;
        const nearestViewportX = clamp(cx, 0, width);
        const nearestViewportY = clamp(cy, 0, height);
        const minDistanceToViewportPx = Math.hypot(nearestViewportX - cx, nearestViewportY - cy);
        const maxDistanceX = Math.max(Math.abs(cx), Math.abs(width - cx));
        const maxDistanceY = Math.max(Math.abs(cy), Math.abs(height - cy));
        const maxDistanceToViewportPx = Math.hypot(maxDistanceX, maxDistanceY);

        const toScreen = (position) => {
            const x = cx + (position?.[0] || 0) * scale;
            const y = cy - (position?.[1] || 0) * scale;
            return [x, y];
        };
        const solarBodyIds = new Set(
            (Array.isArray(planets) ? planets : [])
                .map((body) => String(body?.id || '').trim().toLowerCase())
                .filter(Boolean),
        );
        const shouldHideTrackedLabelAsDuplicate = (body) => {
            const bodyId = String(body?.body_id || '').trim().toLowerCase();
            if (bodyId && solarBodyIds.has(bodyId)) return true;
            const command = String(body?.command || '').trim().toLowerCase();
            if (command && solarBodyIds.has(command)) return true;
            const name = String(body?.name || '').trim().toLowerCase();
            if (name && solarBodyIds.has(name)) return true;
            return false;
        };

        const placedLabelBoxes = [];
        const LABEL_FONT = '11px monospace';
        const LABEL_LINE_HEIGHT = 10;
        const LABEL_ROW_STEP = 8;
        const LABEL_INDENT_STEP = 6;
        const LABEL_PADDING = 1;

        const boxesOverlap = (a, b) => !(
            (a.x + a.w) < b.x
            || (b.x + b.w) < a.x
            || (a.y + a.h) < b.y
            || (b.y + b.h) < a.y
        );

        const placeLabel = (text, baseX, baseY) => {
            const label = String(text || '');
            if (!label) return null;

            ctx.save();
            ctx.font = LABEL_FONT;
            const width = Math.max(4, ctx.measureText(label).width);
            ctx.restore();

            const maxRows = 10;
            for (let row = 0; row <= maxRows; row += 1) {
                const y = baseY + row * LABEL_ROW_STEP;
                const x = row > 0 ? baseX + LABEL_INDENT_STEP : baseX;
                const box = {
                    x: x - LABEL_PADDING,
                    y: y - LABEL_PADDING,
                    w: width + LABEL_PADDING * 2,
                    h: LABEL_LINE_HEIGHT + LABEL_PADDING * 2,
                };
                if (!placedLabelBoxes.some((existing) => boxesOverlap(existing, box))) {
                    return { x, y, row, box };
                }
            }

            const y = baseY + maxRows * LABEL_ROW_STEP;
            const x = maxRows > 0 ? baseX + LABEL_INDENT_STEP : baseX;
            return {
                x,
                y,
                row: maxRows,
                box: {
                    x: x - LABEL_PADDING,
                    y: y - LABEL_PADDING,
                    w: width + LABEL_PADDING * 2,
                    h: LABEL_LINE_HEIGHT + LABEL_PADDING * 2,
                },
            };
        };

        const drawLabelWithAutoOffset = (text, anchorX, anchorY, color) => {
            const label = String(text || '');
            if (!label) return;

            const placement = placeLabel(label, anchorX + 6, anchorY - 6);
            if (!placement) return;

            ctx.save();
            ctx.font = LABEL_FONT;
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';
            ctx.fillStyle = color;
            ctx.fillText(label, placement.x, placement.y);
            ctx.restore();

            placedLabelBoxes.push(placement.box);
        };
        const findOffscreenLabelPlacement = ({
            baseX,
            baseY,
            ux,
            uy,
            perpX,
            perpY,
            textWidth,
            textHeight,
            baseSideShift = 0,
        }) => {
            const bgPadX = 4;
            const bgPadY = 2;
            const sideCandidates = [baseSideShift];

            for (let step = 1; step <= OFFSCREEN_TARGET_LABEL_SEARCH_STEPS; step += 1) {
                const delta = step * OFFSCREEN_TARGET_STAGGER_PX;
                sideCandidates.push(baseSideShift + delta);
                sideCandidates.push(baseSideShift - delta);
            }

            const minLabelX = OFFSCREEN_TARGET_EDGE_INSET_PX + textWidth / 2 + OFFSCREEN_TARGET_LABEL_SAFE_MARGIN_PX;
            const maxLabelX = width - OFFSCREEN_TARGET_EDGE_INSET_PX - textWidth / 2 - OFFSCREEN_TARGET_LABEL_SAFE_MARGIN_PX;
            const minLabelY = OFFSCREEN_TARGET_EDGE_INSET_PX + textHeight / 2 + OFFSCREEN_TARGET_LABEL_SAFE_MARGIN_PX;
            const maxLabelY = height - OFFSCREEN_TARGET_EDGE_INSET_PX - textHeight / 2 - OFFSCREEN_TARGET_LABEL_SAFE_MARGIN_PX;

            // Probe outward from the preferred spot until we find a free label box.
            for (let depthStep = 0; depthStep <= OFFSCREEN_TARGET_LABEL_SEARCH_STEPS; depthStep += 1) {
                const inwardDistance = OFFSCREEN_TARGET_LABEL_GAP_PX + depthStep * OFFSCREEN_TARGET_LABEL_DEPTH_STEP_PX;
                for (const sideShift of sideCandidates) {
                    const rawX = baseX - ux * inwardDistance + perpX * sideShift;
                    const rawY = baseY - uy * inwardDistance + perpY * sideShift;
                    const centerX = clamp(rawX, minLabelX, maxLabelX);
                    const centerY = clamp(rawY, minLabelY, maxLabelY);
                    const box = {
                        x: centerX - textWidth / 2 - bgPadX,
                        y: centerY - textHeight / 2 - bgPadY,
                        w: textWidth + bgPadX * 2,
                        h: textHeight + bgPadY * 2,
                    };

                    if (!placedLabelBoxes.some((existing) => boxesOverlap(existing, box))) {
                        return { centerX, centerY, box };
                    }
                }
            }

            return null;
        };

        // World-space grid (moves with pan/zoom).
        if (effectiveDisplayOptions.showGrid) {
            const gridStepAu = scale > 80 ? 0.5 : scale > 30 ? 1 : scale > 12 ? 2 : 5;
            const worldMinX = (0 - cx) / scale;
            const worldMaxX = (width - cx) / scale;
            const worldMaxY = (cy - 0) / scale;
            const worldMinY = (cy - height) / scale;
            const startGridX = Math.floor(worldMinX / gridStepAu) * gridStepAu;
            const startGridY = Math.floor(worldMinY / gridStepAu) * gridStepAu;

            ctx.strokeStyle = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
            ctx.lineWidth = 1;

            for (let gx = startGridX; gx <= worldMaxX; gx += gridStepAu) {
                const sx = cx + gx * scale;
                ctx.beginPath();
                ctx.moveTo(sx, 0);
                ctx.lineTo(sx, height);
                ctx.stroke();
            }
            for (let gy = startGridY; gy <= worldMaxY; gy += gridStepAu) {
                const sy = cy - gy * scale;
                ctx.beginPath();
                ctx.moveTo(0, sy);
                ctx.lineTo(width, sy);
                ctx.stroke();
            }
        }

        // Static asteroid zone annuli (subtle background guides).
        if (effectiveDisplayOptions.showAsteroidZones && Array.isArray(asteroidZones) && asteroidZones.length) {
            asteroidZones.forEach((zone) => {
                const innerAu = Math.max(0, Number(zone?.a_min_au) || 0);
                const outerAu = Math.max(innerAu, Number(zone?.a_max_au) || innerAu);
                const innerPx = innerAu * scale;
                const outerPx = outerAu * scale;
                if (outerPx <= 2) return;
                // Avoid expensive giant-radius arcs at high zoom and skip rings
                // that cannot intersect the viewport.
                if (outerPx > MAX_BACKGROUND_RING_RADIUS_PX) return;
                if (outerPx < (minDistanceToViewportPx - 1)) return;
                if (innerPx > (maxDistanceToViewportPx + 1)) return;

                ctx.beginPath();
                ctx.arc(cx, cy, outerPx, 0, Math.PI * 2);
                ctx.arc(cx, cy, innerPx, 0, Math.PI * 2, true);
                ctx.closePath();
                ctx.fillStyle = hexToRgba(resolveAsteroidZoneColor(zone), theme.palette.mode === 'dark' ? 0.14 : 0.1);
                ctx.fill();

                const midRadiusPx = ((innerAu + outerAu) / 2) * scale;
                if (
                    effectiveDisplayOptions.showZoneLabels
                    && midRadiusPx > 55
                    && midRadiusPx <= MAX_ZONE_LABEL_RADIUS_PX
                ) {
                    drawTextOnArc(
                        ctx,
                        zone?.name || '',
                        cx,
                        cy,
                        midRadiusPx,
                        -Math.PI / 4,
                        {
                            font: '10px monospace',
                            color: theme.palette.mode === 'dark'
                                ? 'rgba(220,230,240,0.42)'
                                : 'rgba(55,70,90,0.38)',
                            clockwise: true,
                        },
                    );
                }
            });
        }

        // Kirkwood gap markers (subtle dashed annuli).
        if (effectiveDisplayOptions.showResonanceMarkers && Array.isArray(asteroidResonanceGaps) && asteroidResonanceGaps.length) {
            ctx.setLineDash([5, 6]);
            ctx.lineWidth = 1;
            asteroidResonanceGaps.forEach((gap) => {
                const radiusPx = (Number(gap?.a_au) || 0) * scale;
                if (radiusPx <= 3) return;
                if (radiusPx > MAX_BACKGROUND_RING_RADIUS_PX) return;
                if (radiusPx < (minDistanceToViewportPx - 1)) return;
                if (radiusPx > (maxDistanceToViewportPx + 1)) return;
                ctx.beginPath();
                ctx.arc(cx, cy, radiusPx, 0, Math.PI * 2);
                ctx.strokeStyle = theme.palette.mode === 'dark'
                    ? 'rgba(245,200,120,0.28)'
                    : 'rgba(158,116,40,0.2)';
                ctx.stroke();
            });
            ctx.setLineDash([]);
        }

        // Sun.
        ctx.beginPath();
        ctx.arc(cx, cy, 8, 0, Math.PI * 2);
        ctx.fillStyle = '#f9c74f';
        ctx.fill();
        ctx.strokeStyle = '#f4a261';
        ctx.stroke();

        if (effectiveDisplayOptions.showPlanets && effectiveDisplayOptions.showPlanetOrbits) {
            // Planet orbits (sampled paths).
            ctx.lineWidth = 1;
            planets.forEach((planet) => {
                const samples = planet.orbit_samples_xyz_au || [];
                if (!samples.length) return;
                ctx.beginPath();
                samples.forEach((sample, index) => {
                    const [sx, sy] = toScreen(sample);
                    if (index === 0) ctx.moveTo(sx, sy);
                    else ctx.lineTo(sx, sy);
                });
                ctx.closePath();
                ctx.strokeStyle = theme.palette.mode === 'dark' ? 'rgba(180,180,200,0.35)' : 'rgba(90,90,120,0.3)';
                ctx.stroke();
            });
        }

        if (effectiveDisplayOptions.showPlanets) {
            // Planets.
            planets.forEach((planet) => {
                const id = String(planet.id || '').toLowerCase();
                const color = PLANET_COLORS[id] || '#bbbbbb';
                const [sx, sy] = toScreen(planet.position_xyz_au);

                ctx.beginPath();
                ctx.arc(sx, sy, 4, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();

                if (effectiveDisplayOptions.showPlanetLabels) {
                    drawLabelWithAutoOffset(planet.name || id, sx, sy, theme.palette.text.secondary);
                }
            });
        }

        // Tracked objects from Horizons.
        if (effectiveDisplayOptions.showTrackedObjects) tracked.forEach((body) => {
            if (!hasFiniteXYZ(body.position_xyz_au)) return;
            const samples = body.orbit_samples_xyz_au || [];
            if (!samples.length || !effectiveDisplayOptions.showTrackedOrbits) return;
            const targetKey = resolveTargetKey(body);
            const isSelected = hasTrackedSelection && selectedTargetKeySet.has(targetKey);
            const isDimmed = hasTrackedSelection && !isSelected;

            const trackedHexColor = resolveTrackedColor(body, body.stale ? '#EF476F' : '#06D6A0');
            const trackedStrokeColor = isSelected
                ? hexToRgba(trackedHexColor, 0.95)
                : isDimmed
                    ? hexToRgba(trackedHexColor, 0.16)
                    : hexToRgba(trackedHexColor, body.stale ? 0.35 : 0.45);
            ctx.beginPath();
            samples.forEach((sample, index) => {
                const [sx, sy] = toScreen(sample);
                if (index === 0) ctx.moveTo(sx, sy);
                else ctx.lineTo(sx, sy);
            });
            ctx.strokeStyle = trackedStrokeColor;
            ctx.lineWidth = isSelected ? 2.2 : 1;
            ctx.setLineDash([3, 4]);
            ctx.stroke();
            ctx.setLineDash([]);

            // Direction arrows at both endpoints in forward time direction.
            if (samples.length >= 2) {
                const [startX, startY] = toScreen(samples[0]);
                const [startNextX, startNextY] = toScreen(samples[1]);
                drawArrowHead(ctx, startX, startY, startNextX, startNextY, trackedStrokeColor);

                const lastIndex = samples.length - 1;
                const [endPrevX, endPrevY] = toScreen(samples[lastIndex - 1]);
                const [endX, endY] = toScreen(samples[lastIndex]);
                const dirX = endX - endPrevX;
                const dirY = endY - endPrevY;
                const dirLen = Math.hypot(dirX, dirY);
                if (dirLen > 0.001) {
                    const ux = dirX / dirLen;
                    const uy = dirY / dirLen;
                    const arrowTipX = endX + ux * 8;
                    const arrowTipY = endY + uy * 8;
                    drawArrowHead(ctx, endX, endY, arrowTipX, arrowTipY, trackedStrokeColor);
                }
            }
        });

        // Tracked object markers from Horizons.
        if (effectiveDisplayOptions.showTrackedObjects) {
            tracked.forEach((body) => {
                if (!hasFiniteXYZ(body.position_xyz_au)) return;
                const [sx, sy] = toScreen(body.position_xyz_au);
                const targetKey = resolveTargetKey(body);
                const isSelected = hasTrackedSelection && selectedTargetKeySet.has(targetKey);
                const isDimmed = hasTrackedSelection && !isSelected;
                const trackedHexColor = resolveTrackedColor(body, body.stale ? '#EF476F' : '#06D6A0');

                ctx.fillStyle = isDimmed ? hexToRgba(trackedHexColor, 0.28) : trackedHexColor;
                const markerSize = isSelected ? 8 : 6;
                ctx.fillRect(sx - markerSize / 2, sy - markerSize / 2, markerSize, markerSize);
                if (isSelected) {
                    ctx.strokeStyle = hexToRgba('#ffffff', theme.palette.mode === 'dark' ? 0.9 : 0.75);
                    ctx.lineWidth = 1.25;
                    ctx.strokeRect(sx - markerSize / 2 - 1, sy - markerSize / 2 - 1, markerSize + 2, markerSize + 2);
                }

                if (effectiveDisplayOptions.showTrackedLabels) {
                    if (shouldHideTrackedLabelAsDuplicate(body)) return;
                    const labelColor = isSelected
                        ? theme.palette.text.primary
                        : isDimmed
                            ? hexToRgba(theme.palette.text.secondary, 0.45)
                            : theme.palette.text.secondary;
                    drawLabelWithAutoOffset(body.name || body.command || 'object', sx, sy, labelColor);
                }
            });
        }

        const drawOffscreenDirectionIndicator = (target, offsetIndex = 0) => {
            const screenX = Number(target?.x);
            const screenY = Number(target?.y);
            if (!Number.isFinite(screenX) || !Number.isFinite(screenY)) return;

            if (isPointInsideViewport(
                screenX,
                screenY,
                width,
                height,
                OFFSCREEN_TARGET_VISIBILITY_PADDING_PX,
            )) {
                return;
            }

            const centerX = width / 2;
            const centerY = height / 2;
            const edgePoint = projectToViewportEdge({
                fromX: centerX,
                fromY: centerY,
                toX: screenX,
                toY: screenY,
                minX: OFFSCREEN_TARGET_EDGE_INSET_PX,
                minY: OFFSCREEN_TARGET_EDGE_INSET_PX,
                maxX: width - OFFSCREEN_TARGET_EDGE_INSET_PX,
                maxY: height - OFFSCREEN_TARGET_EDGE_INSET_PX,
            });
            if (!edgePoint) return;

            const dx = screenX - centerX;
            const dy = screenY - centerY;
            const distance = Math.hypot(dx, dy);
            if (distance < 0.001) return;

            const ux = dx / distance;
            const uy = dy / distance;
            const perpX = -uy;
            const perpY = ux;
            const stagger = offsetIndex * OFFSCREEN_TARGET_STAGGER_PX;

            const tipX = clamp(
                edgePoint.x,
                OFFSCREEN_TARGET_EDGE_INSET_PX,
                width - OFFSCREEN_TARGET_EDGE_INSET_PX,
            );
            const tipY = clamp(
                edgePoint.y,
                OFFSCREEN_TARGET_EDGE_INSET_PX,
                height - OFFSCREEN_TARGET_EDGE_INSET_PX,
            );
            const baseX = tipX - ux * OFFSCREEN_TARGET_ARROW_LENGTH_PX;
            const baseY = tipY - uy * OFFSCREEN_TARGET_ARROW_LENGTH_PX;

            ctx.save();
            ctx.strokeStyle = target.color;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(baseX, baseY);
            ctx.lineTo(tipX, tipY);
            ctx.stroke();
            drawArrowHead(ctx, baseX, baseY, tipX, tipY, target.color);

            const text = String(target.label || '').trim();
            if (text) {
                ctx.font = '11px monospace';
                const textWidth = Math.max(8, ctx.measureText(text).width);
                const textHeight = 10;
                const labelPlacement = findOffscreenLabelPlacement({
                    baseX,
                    baseY,
                    ux,
                    uy,
                    perpX,
                    perpY,
                    textWidth,
                    textHeight,
                    baseSideShift: stagger,
                });
                if (!labelPlacement) {
                    ctx.restore();
                    return;
                }
                const boxX = labelPlacement.box.x;
                const boxY = labelPlacement.box.y;
                const boxWidth = labelPlacement.box.w;
                const boxHeight = labelPlacement.box.h;

                ctx.fillStyle = theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.52)' : 'rgba(255,255,255,0.76)';
                ctx.fillRect(boxX, boxY, boxWidth, boxHeight);
                ctx.strokeStyle = hexToRgba(target.color, 0.62);
                ctx.lineWidth = 1;
                ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);

                ctx.fillStyle = target.color;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(text, labelPlacement.centerX, labelPlacement.centerY + 0.5);

                placedLabelBoxes.push(labelPlacement.box);
            }
            ctx.restore();
        };

        const offscreenAnchors = [];
        offscreenAnchors.push({
            label: 'Sun',
            color: '#f9c74f',
            x: cx,
            y: cy,
        });
        const earthPlanet = planets.find((planet) => String(planet?.id || '').trim().toLowerCase() === 'earth');
        if (earthPlanet && hasFiniteXYZ(earthPlanet.position_xyz_au)) {
            const [earthX, earthY] = toScreen(earthPlanet.position_xyz_au);
            offscreenAnchors.push({
                label: 'Earth',
                color: PLANET_COLORS.earth,
                x: earthX,
                y: earthY,
            });
        }

        const hiddenAnchors = offscreenAnchors.filter((target) => !isPointInsideViewport(
            target.x,
            target.y,
            width,
            height,
            OFFSCREEN_TARGET_VISIBILITY_PADDING_PX,
        ));

        // Keep labels readable when both Sun and Earth are hidden in the same direction.
        hiddenAnchors.forEach((target, index) => {
            const offsetIndex = index - (hiddenAnchors.length - 1) / 2;
            drawOffscreenDirectionIndicator(target, offsetIndex);
        });
    }, [
        asteroidResonanceGaps,
        asteroidZones,
        displayOptions,
        planets,
        tracked,
        selectedTargetKeySet,
        hasTrackedSelection,
        theme.palette.background.default,
        theme.palette.mode,
        theme.palette.text.primary,
        theme.palette.text.secondary,
        viewport.panX,
        viewport.panY,
        viewport.zoom,
    ]);

    useEffect(() => {
        drawScene();
    }, [drawScene]);

    useEffect(() => {
        viewportRef.current = viewport;
    }, [viewport]);

    useEffect(() => {
        if (fitAllSignal === lastFitSignalRef.current) return;
        lastFitSignalRef.current = fitAllSignal;
        fitAll();
    }, [fitAllSignal, fitAll]);

    useEffect(() => {
        if (focusTargetSignal === lastFocusTargetSignalRef.current) return;
        lastFocusTargetSignalRef.current = focusTargetSignal;
        fitTarget(focusTargetKey);
    }, [focusTargetSignal, focusTargetKey, fitTarget]);

    useEffect(() => {
        if (zoomInSignal === lastZoomInSignalRef.current) return;
        lastZoomInSignalRef.current = zoomInSignal;
        hasPersistentViewportRef.current = true;

        const container = containerRef.current;
        if (!container) return;
        const rect = container.getBoundingClientRect();
        const next = applyZoomAtScreenPoint(1.08, rect.width / 2, rect.height / 2);
        if (next) commitViewport(next);
    }, [zoomInSignal, applyZoomAtScreenPoint, commitViewport]);

    useEffect(() => {
        if (zoomOutSignal === lastZoomOutSignalRef.current) return;
        lastZoomOutSignalRef.current = zoomOutSignal;
        hasPersistentViewportRef.current = true;

        const container = containerRef.current;
        if (!container) return;
        const rect = container.getBoundingClientRect();
        const next = applyZoomAtScreenPoint(0.92, rect.width / 2, rect.height / 2);
        if (next) commitViewport(next);
    }, [zoomOutSignal, applyZoomAtScreenPoint, commitViewport]);

    useEffect(() => {
        if (resetZoomSignal === lastResetZoomSignalRef.current) return;
        lastResetZoomSignalRef.current = resetZoomSignal;
        hasPersistentViewportRef.current = true;

        const next = {
            ...viewportRef.current,
            zoom: DEFAULT_VIEWPORT.zoom,
        };
        viewportRef.current = next;
        setViewport(next);
        commitViewport(next);
    }, [resetZoomSignal, commitViewport]);

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const observer = new ResizeObserver(() => {
            drawScene();
        });
        observer.observe(container);
        return () => observer.disconnect();
    }, [drawScene]);

    useEffect(() => {
        return () => {
            cancelViewportAnimation();
            if (wheelCommitTimeoutRef.current) {
                window.clearTimeout(wheelCommitTimeoutRef.current);
            }
        };
    }, [cancelViewportAnimation]);

    const handlePointerDown = (event) => {
        if (event.pointerType === 'touch') return;
        if (event.pointerType === 'mouse' && event.button !== 0) return;
        hasPersistentViewportRef.current = true;
        event.currentTarget.setPointerCapture?.(event.pointerId);
        activePointersRef.current.set(event.pointerId, {
            x: event.clientX,
            y: event.clientY,
        });

        const activeCount = activePointersRef.current.size;
        if (activeCount === 1) {
            gestureRef.current.mode = 'pan';
            gestureRef.current.lastCenterX = event.clientX;
            gestureRef.current.lastCenterY = event.clientY;
            gestureRef.current.lastDistance = 0;
            return;
        }

        if (activeCount >= 2) {
            const gesture = getTwoPointerGesture(activePointersRef.current);
            if (!gesture) return;
            gestureRef.current.mode = 'pinch';
            gestureRef.current.lastCenterX = gesture.centerX;
            gestureRef.current.lastCenterY = gesture.centerY;
            gestureRef.current.lastDistance = gesture.distance;
        }
    };

    const handlePointerMove = (event) => {
        if (!activePointersRef.current.has(event.pointerId)) return;
        activePointersRef.current.set(event.pointerId, {
            x: event.clientX,
            y: event.clientY,
        });

        if (activePointersRef.current.size === 1 && gestureRef.current.mode === 'pan') {
            const dx = event.clientX - gestureRef.current.lastCenterX;
            const dy = event.clientY - gestureRef.current.lastCenterY;
            gestureRef.current.lastCenterX = event.clientX;
            gestureRef.current.lastCenterY = event.clientY;
            setViewport((prev) => {
                const next = {
                    ...prev,
                    panX: prev.panX + dx,
                    panY: prev.panY + dy,
                };
                viewportRef.current = next;
                return next;
            });
            return;
        }

        if (activePointersRef.current.size >= 2) {
            const gesture = getTwoPointerGesture(activePointersRef.current);
            const container = containerRef.current;
            if (!gesture || !container || gestureRef.current.lastDistance <= 0) return;

            const rect = container.getBoundingClientRect();
            const width = rect.width;
            const height = rect.height;
            const zoomRatio = gesture.distance / gestureRef.current.lastDistance;
            const anchorX = gestureRef.current.lastCenterX - rect.left;
            const anchorY = gestureRef.current.lastCenterY - rect.top;
            const nextCenterX = gesture.centerX - rect.left;
            const nextCenterY = gesture.centerY - rect.top;

            setViewport((prev) => {
                const nextZoom = clamp(prev.zoom * zoomRatio, MIN_ZOOM, MAX_ZOOM);
                const prevCx = width / 2 + prev.panX;
                const prevCy = height / 2 + prev.panY;
                const worldX = (anchorX - prevCx) / prev.zoom;
                const worldY = (prevCy - anchorY) / prev.zoom;
                const nextCx = nextCenterX - worldX * nextZoom;
                const nextCy = nextCenterY + worldY * nextZoom;

                const next = {
                    zoom: nextZoom,
                    panX: nextCx - width / 2,
                    panY: nextCy - height / 2,
                };
                viewportRef.current = next;
                return next;
            });

            gestureRef.current.lastCenterX = gesture.centerX;
            gestureRef.current.lastCenterY = gesture.centerY;
            gestureRef.current.lastDistance = Math.max(gesture.distance, 0.0001);
        }
    };

    const handlePointerUp = (event) => {
        activePointersRef.current.delete(event.pointerId);

        if (!activePointersRef.current.size) {
            if (gestureRef.current.mode) {
                commitViewport(viewportRef.current);
            }
            gestureRef.current.mode = null;
            gestureRef.current.lastCenterX = 0;
            gestureRef.current.lastCenterY = 0;
            gestureRef.current.lastDistance = 0;
            return;
        }

        if (activePointersRef.current.size === 1) {
            const remainingPointer = Array.from(activePointersRef.current.values())[0];
            gestureRef.current.mode = 'pan';
            gestureRef.current.lastCenterX = remainingPointer.x;
            gestureRef.current.lastCenterY = remainingPointer.y;
            gestureRef.current.lastDistance = 0;
            return;
        }

        const gesture = getTwoPointerGesture(activePointersRef.current);
        if (gesture) {
            gestureRef.current.mode = 'pinch';
            gestureRef.current.lastCenterX = gesture.centerX;
            gestureRef.current.lastCenterY = gesture.centerY;
            gestureRef.current.lastDistance = gesture.distance;
        }
    };

    const handleTouchStart = (event) => {
        if (event.touches.length < 2) return;
        hasPersistentViewportRef.current = true;
        const touch1 = event.touches[0];
        const touch2 = event.touches[1];
        touchGestureRef.current.active = true;
        touchGestureRef.current.lastCenterX = (touch1.clientX + touch2.clientX) / 2;
        touchGestureRef.current.lastCenterY = (touch1.clientY + touch2.clientY) / 2;
        touchGestureRef.current.lastDistance = Math.max(
            Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY),
            0.0001,
        );
        event.preventDefault();
    };

    const handleTouchMove = (event) => {
        if (event.touches.length < 2 || !touchGestureRef.current.active) return;
        const container = containerRef.current;
        if (!container) return;

        const touch1 = event.touches[0];
        const touch2 = event.touches[1];
        const centerX = (touch1.clientX + touch2.clientX) / 2;
        const centerY = (touch1.clientY + touch2.clientY) / 2;
        const distance = Math.max(Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY), 0.0001);
        const rect = container.getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;
        const zoomRatio = distance / touchGestureRef.current.lastDistance;
        const anchorX = touchGestureRef.current.lastCenterX - rect.left;
        const anchorY = touchGestureRef.current.lastCenterY - rect.top;
        const nextCenterX = centerX - rect.left;
        const nextCenterY = centerY - rect.top;

        setViewport((prev) => {
            const nextZoom = clamp(prev.zoom * zoomRatio, MIN_ZOOM, MAX_ZOOM);
            const prevCx = width / 2 + prev.panX;
            const prevCy = height / 2 + prev.panY;
            const worldX = (anchorX - prevCx) / prev.zoom;
            const worldY = (prevCy - anchorY) / prev.zoom;
            const nextCx = nextCenterX - worldX * nextZoom;
            const nextCy = nextCenterY + worldY * nextZoom;

            const next = {
                zoom: nextZoom,
                panX: nextCx - width / 2,
                panY: nextCy - height / 2,
            };
            viewportRef.current = next;
            return next;
        });

        touchGestureRef.current.lastCenterX = centerX;
        touchGestureRef.current.lastCenterY = centerY;
        touchGestureRef.current.lastDistance = distance;
        event.preventDefault();
    };

    const handleTouchEnd = (event) => {
        if (event.touches.length >= 2) {
            const touch1 = event.touches[0];
            const touch2 = event.touches[1];
            touchGestureRef.current.active = true;
            touchGestureRef.current.lastCenterX = (touch1.clientX + touch2.clientX) / 2;
            touchGestureRef.current.lastCenterY = (touch1.clientY + touch2.clientY) / 2;
            touchGestureRef.current.lastDistance = Math.max(
                Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY),
                0.0001,
            );
            return;
        }

        if (touchGestureRef.current.active) {
            touchGestureRef.current.active = false;
            touchGestureRef.current.lastCenterX = 0;
            touchGestureRef.current.lastCenterY = 0;
            touchGestureRef.current.lastDistance = 0;
            commitViewport(viewportRef.current);
        }
    };

    const handleWheel = (event) => {
        if (!event.shiftKey) {
            return;
        }
        event.preventDefault();
        hasPersistentViewportRef.current = true;
        const container = containerRef.current;
        if (!container) return;

        const rect = container.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;
        const zoomFactor = event.deltaY > 0 ? 0.92 : 1.08;
        applyZoomAtScreenPoint(zoomFactor, mouseX, mouseY);

        if (wheelCommitTimeoutRef.current) {
            window.clearTimeout(wheelCommitTimeoutRef.current);
        }
        wheelCommitTimeoutRef.current = window.setTimeout(() => {
            commitViewport(viewportRef.current);
        }, WHEEL_COMMIT_DELAY_MS);
    };

    const timestampText = useMemo(() => {
        if (!scene?.timestamp_utc) return 'No epoch';
        return `Epoch: ${scene.timestamp_utc}`;
    }, [scene?.timestamp_utc]);

    const scaleIndicator = useMemo(() => {
        const zoom = viewport.zoom;
        const gridStepAu = zoom > 80 ? 0.5 : zoom > 30 ? 1 : zoom > 12 ? 2 : 5;
        const pixels = gridStepAu * zoom;
        return {
            label: `Scale: ${formatAu(gridStepAu)} / square`,
            barWidthPx: clamp(pixels, 40, 180),
        };
    }, [viewport.zoom]);

    return (
        <Box sx={{ width: '100%', height: '100%', position: 'relative' }}>
            <Box
                ref={containerRef}
                sx={{ width: '100%', height: '100%', cursor: 'grab', touchAction: 'pan-x pan-y' }}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                onPointerCancel={handlePointerUp}
                onWheel={handleWheel}
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleTouchEnd}
                onTouchCancel={handleTouchEnd}
            >
                <canvas ref={canvasRef} style={{ display: 'block', width: '100%', height: '100%' }} />
            </Box>
            {effectiveDisplayOptions.showTimestamp ? (
                <Typography
                    variant="caption"
                    sx={{
                        position: 'absolute',
                        left: 10,
                        top: 8,
                        color: 'text.secondary',
                        backgroundColor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.35)' : 'rgba(255,255,255,0.6)',
                        px: 0.8,
                        py: 0.3,
                        borderRadius: 0.5,
                        fontFamily: 'monospace',
                    }}
                >
                    {timestampText}
                </Typography>
            ) : null}
            {effectiveDisplayOptions.showGestureHint ? (
                <Box
                    sx={{
                        position: 'absolute',
                        left: 10,
                        bottom: 8,
                        color: 'text.secondary',
                        backgroundColor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.28)' : 'rgba(255,255,255,0.52)',
                        px: 0.8,
                        py: 0.35,
                        borderRadius: 0.5,
                        fontFamily: 'monospace',
                        opacity: 0.9,
                    }}
                >
                    <Typography variant="caption" sx={{ fontFamily: 'inherit', lineHeight: 1.1 }}>
                        Touch: 2-finger pan/zoom | Mouse: drag + Shift+wheel
                    </Typography>
                </Box>
            ) : null}
            {effectiveDisplayOptions.showScaleIndicator ? (
                <Box
                    sx={{
                        position: 'absolute',
                        right: 10,
                        bottom: 8,
                        color: 'text.secondary',
                        backgroundColor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.35)' : 'rgba(255,255,255,0.6)',
                        px: 0.8,
                        py: 0.5,
                        borderRadius: 0.5,
                        fontFamily: 'monospace',
                    }}
                >
                    <Typography variant="caption" sx={{ fontFamily: 'inherit', lineHeight: 1.1 }}>
                        {scaleIndicator.label}
                    </Typography>
                </Box>
            ) : null}
        </Box>
    );
};

export default React.memo(SolarSystemCanvas);
