import { describe, it, expect } from 'vitest';
import { determineAzimuthArcFlags } from '../rotator-gauges.jsx';

describe('determineAzimuthArcFlags', () => {
  it('chooses short clockwise arc when peak is on that arc', () => {
    expect(determineAzimuthArcFlags(90, 180, 179.9)).toEqual([0, 1]);
  });

  it('includes end boundary peak and keeps correct short arc', () => {
    expect(determineAzimuthArcFlags(90, 180, 180)).toEqual([0, 1]);
  });

  it('includes start boundary peak and keeps correct short arc', () => {
    expect(determineAzimuthArcFlags(180, 90, 180)).toEqual([0, 0]);
  });

  it('handles north crossing with endpoint peak', () => {
    expect(determineAzimuthArcFlags(350, 10, 10)).toEqual([0, 1]);
  });

  it('falls back to shortest arc when peak is missing', () => {
    expect(determineAzimuthArcFlags(270, 90, null)).toEqual([0, 1]);
  });
});
