import { describe, expect, it } from 'vitest';

import { getTooltipOffsetByDirection, pickTooltipDirection } from '../tooltip-orientation.js';

describe('pickTooltipDirection', () => {
    const mapSize = { x: 400, y: 300 };
    const tooltipSize = { width: 160, height: 60 };

    it('keeps bottom orientation when tooltip fits inside the map', () => {
        const direction = pickTooltipDirection({
            anchorPoint: { x: 200, y: 120 },
            mapSize,
            tooltipSize,
            anchorDistance: 20,
            edgePadding: 8,
        });

        expect(direction).toBe('bottom');
    });

    it('switches to top when the marker is close to the bottom edge', () => {
        const direction = pickTooltipDirection({
            anchorPoint: { x: 200, y: 280 },
            mapSize,
            tooltipSize,
            anchorDistance: 20,
            edgePadding: 8,
        });

        expect(direction).toBe('top');
    });

    it('switches to right when the marker is close to the left edge', () => {
        const direction = pickTooltipDirection({
            anchorPoint: { x: 10, y: 140 },
            mapSize,
            tooltipSize,
            anchorDistance: 20,
            edgePadding: 8,
        });

        expect(direction).toBe('right');
    });

    it('switches to left when the marker is close to the right edge', () => {
        const direction = pickTooltipDirection({
            anchorPoint: { x: 390, y: 140 },
            mapSize,
            tooltipSize,
            anchorDistance: 20,
            edgePadding: 8,
        });

        expect(direction).toBe('left');
    });
});

describe('getTooltipOffsetByDirection', () => {
    it('returns offsets aligned to cardinal directions', () => {
        expect(getTooltipOffsetByDirection('top', 24)).toEqual([0, -24]);
        expect(getTooltipOffsetByDirection('right', 24)).toEqual([24, 0]);
        expect(getTooltipOffsetByDirection('bottom', 24)).toEqual([0, 24]);
        expect(getTooltipOffsetByDirection('left', 24)).toEqual([-24, 0]);
    });
});
