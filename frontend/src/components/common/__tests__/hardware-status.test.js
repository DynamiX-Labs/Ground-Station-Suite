import { describe, expect, it } from 'vitest';
import {
    hasAssignedHardwareId,
    resolveAssignedHardwareId,
} from '../hardware-status.js';

describe('resolveAssignedHardwareId', () => {
    it('falls back when preferred source is empty string', () => {
        expect(resolveAssignedHardwareId('', 'rig-2', 'rig-3')).toBe('rig-2');
    });

    it('keeps explicit "none" assignment', () => {
        expect(resolveAssignedHardwareId('none', 'rig-2')).toBe('none');
    });

    it('returns "none" when every source is unset', () => {
        expect(resolveAssignedHardwareId('', null, undefined)).toBe('none');
    });
});

describe('hasAssignedHardwareId', () => {
    it('treats normal IDs as assigned', () => {
        expect(hasAssignedHardwareId('rig-2')).toBe(true);
    });

    it('treats "none" as unassigned', () => {
        expect(hasAssignedHardwareId('none')).toBe(false);
    });
});
