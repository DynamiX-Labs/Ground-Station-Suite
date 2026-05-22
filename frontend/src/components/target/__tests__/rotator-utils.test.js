/**
 * Unit tests for rotator-utils.js
 * Tests rotator state management and control logic
 */

import { describe, it, expect } from 'vitest';
import {
  getCurrentStatusofRotator,
  getConnectionStatusofRotator,
  createTrackingState,
  isRotatorConnected,
  canControlRotator,
  canStartTracking,
  canStopTracking,
  canConnectRotator,
  isRotatorSelectionDisabled,
} from '../rotator-utils';

describe('getCurrentStatusofRotator', () => {
  it('should return disconnected status when rotator is not connected', () => {
    const rotatorData = { connected: false };
    const result = getCurrentStatusofRotator(rotatorData, 'tracking');

    expect(result.key).toBe('disconnected');
    expect(result.value).toBe('-');
    expect(result.bgColor).toBe('grey.600');
    expect(result.fgColor).toBe('grey.800');
  });

  it('should return tracking status when connected and tracking', () => {
    const rotatorData = { connected: true };
    const result = getCurrentStatusofRotator(rotatorData, 'TRK');

    expect(result.key).toBe('TRK');
    expect(result.value).toBe('Tracking');
    expect(result.bgColor).toBe('success.light');
    expect(result.fgColor).toBe('success.dark');
  });

  it('should return slewing status when connected and slewing', () => {
    const rotatorData = { connected: true };
    const result = getCurrentStatusofRotator(rotatorData, 'SLEW');

    expect(result.key).toBe('SLEW');
    expect(result.value).toBe('Slewing');
    expect(result.bgColor).toBe('warning.light');
    expect(result.fgColor).toBe('warning.dark');
  });

  it('should return stopped status when connected and stopped', () => {
    const rotatorData = { connected: true };
    const result = getCurrentStatusofRotator(rotatorData, 'STOP');

    expect(result.key).toBe('STOP');
    expect(result.value).toBe('Stopped');
    expect(result.bgColor).toBe('info.light');
    expect(result.fgColor).toBe('info.dark');
  });

  it('should return minimum elevation status', () => {
    const rotatorData = { connected: true };
    const result = getCurrentStatusofRotator(rotatorData, 'EL-MIN');

    expect(result.key).toBe('EL-MIN');
    expect(result.value).toBe('Target below minimum elevation');
    expect(result.bgColor).toBe('error.light');
    expect(result.fgColor).toBe('error.dark');
  });

  it('should return out of bounds status', () => {
    const rotatorData = { connected: true };
    const result = getCurrentStatusofRotator(rotatorData, 'OOB');

    expect(result.key).toBe('OOB');
    expect(result.value).toBe('Target below the horizon');
    expect(result.bgColor).toBe('#701c49');
    expect(result.fgColor).toBe('#f8440e');
  });

  it('should return idle status for unknown event', () => {
    const rotatorData = { connected: true };
    const result = getCurrentStatusofRotator(rotatorData, 'some_unknown_event');

    expect(result.key).toBe('some_unknown_event');
    expect(result.value).toBe('Idle');
    expect(result.bgColor).toBe('grey.200');
    expect(result.fgColor).toBe('grey.800');
  });

  it('should return unknown status when no event provided', () => {
    const rotatorData = { connected: true };
    const result = getCurrentStatusofRotator(rotatorData, null);

    expect(result.key).toBe('unknown');
    expect(result.value).toBe('Unknown');
    expect(result.bgColor).toBe('grey.200');
    expect(result.fgColor).toBe('grey.800');
  });
});

describe('getConnectionStatusofRotator', () => {
  it('should return "Connected" when rotator is connected', () => {
    const rotatorData = { connected: true };
    expect(getConnectionStatusofRotator(rotatorData)).toBe('Connected');
  });

  it('should return "Not connected" when rotator is not connected', () => {
    const rotatorData = { connected: false };
    expect(getConnectionStatusofRotator(rotatorData)).toBe('Not connected');
  });

  it('should return "unknown" for undefined connection state', () => {
    const rotatorData = { connected: undefined };
    expect(getConnectionStatusofRotator(rotatorData)).toBe('unknown');
  });

  it('should return "unknown" for null connection state', () => {
    const rotatorData = { connected: null };
    expect(getConnectionStatusofRotator(rotatorData)).toBe('unknown');
  });
});

describe('createTrackingState', () => {
  it('should create valid tracking state object', () => {
    const params = {
      satelliteId: '25544',
      groupId: 'group1',
      rotatorState: 'tracking',
      rigState: 'connected',
      selectedRadioRig: 'rig1',
      selectedRotator: 'rotator1',
      selectedTransmitter: 'tx1'
    };

    const result = createTrackingState(params);

    expect(result).toEqual({
      norad_id: '25544',
      group_id: 'group1',
      rotator_state: 'tracking',
      rig_state: 'connected',
      rig_id: 'rig1',
      rotator_id: 'rotator1',
      transmitter_id: 'tx1'
    });
  });

  it('should handle empty string values', () => {
    const params = {
      satelliteId: '',
      groupId: '',
      rotatorState: '',
      rigState: '',
      selectedRadioRig: '',
      selectedRotator: '',
      selectedTransmitter: ''
    };

    const result = createTrackingState(params);

    expect(result.norad_id).toBe('');
    expect(result.group_id).toBe('');
  });
});

describe('isRotatorConnected', () => {
  it('should return true when rotator is not disconnected', () => {
    expect(isRotatorConnected({ rotator_state: 'tracking' })).toBe(true);
    expect(isRotatorConnected({ rotator_state: 'stopped' })).toBe(true);
    expect(isRotatorConnected({ rotator_state: 'slewing' })).toBe(true);
    expect(isRotatorConnected({ rotator_state: 'connected' })).toBe(true);
  });

  it('should return false when rotator is disconnected', () => {
    expect(isRotatorConnected({ rotator_state: 'disconnected' })).toBe(false);
  });
});

describe('canControlRotator', () => {
  it('should return true when connected and not tracking', () => {
    const rotatorData = { connected: true };
    const trackingState = { rotator_state: 'stopped' };

    expect(canControlRotator(rotatorData, trackingState)).toBe(true);
  });

  it('should return false when not connected', () => {
    const rotatorData = { connected: false };
    const trackingState = { rotator_state: 'stopped' };

    expect(canControlRotator(rotatorData, trackingState)).toBe(false);
  });

  it('should return false when tracking', () => {
    const rotatorData = { connected: true };
    const trackingState = { rotator_state: 'tracking' };

    expect(canControlRotator(rotatorData, trackingState)).toBe(false);
  });
});

describe('canStartTracking', () => {
  it('should return true when all conditions are met', () => {
    const trackingState = { rotator_state: 'stopped' };
    const satelliteId = '25544';
    const selectedRotator = 'rotator1';

    expect(canStartTracking(trackingState, satelliteId, selectedRotator)).toBe(true);
  });

  it('should return false when already tracking', () => {
    const trackingState = { rotator_state: 'tracking' };
    const satelliteId = '25544';
    const selectedRotator = 'rotator1';

    expect(canStartTracking(trackingState, satelliteId, selectedRotator)).toBe(false);
  });

  it('should return false when disconnected', () => {
    const trackingState = { rotator_state: 'disconnected' };
    const satelliteId = '25544';
    const selectedRotator = 'rotator1';

    expect(canStartTracking(trackingState, satelliteId, selectedRotator)).toBe(false);
  });

  it('should return false when no satellite selected', () => {
    const trackingState = { rotator_state: 'stopped' };
    const satelliteId = '';
    const selectedRotator = 'rotator1';

    expect(canStartTracking(trackingState, satelliteId, selectedRotator)).toBe(false);
  });

  it('should return true for mission targets with command and no satellite id', () => {
    const trackingState = {
      rotator_state: 'stopped',
      target_type: 'mission',
      command: 'Voyager 1',
      body_id: null,
      norad_id: null,
    };
    const satelliteId = '';
    const selectedRotator = 'rotator1';

    expect(canStartTracking(trackingState, satelliteId, selectedRotator)).toBe(true);
  });

  it('should return true for body targets with body_id and no satellite id', () => {
    const trackingState = {
      rotator_state: 'stopped',
      target_type: 'body',
      command: null,
      body_id: 'rhea',
      norad_id: null,
    };
    const satelliteId = '';
    const selectedRotator = 'rotator1';

    expect(canStartTracking(trackingState, satelliteId, selectedRotator)).toBe(true);
  });

  it('should return false when no rotator selected', () => {
    const trackingState = { rotator_state: 'stopped' };
    const satelliteId = '25544';

    expect(canStartTracking(trackingState, satelliteId, 'none')).toBe(false);
    expect(canStartTracking(trackingState, satelliteId, '')).toBe(false);
  });
});

describe('canStopTracking', () => {
  it('should return true when tracking', () => {
    const trackingState = { rotator_state: 'tracking' };
    const satelliteId = '25544';
    const selectedRotator = 'rotator1';

    expect(canStopTracking(trackingState, satelliteId, selectedRotator)).toBe(true);
  });

  it('should return true when slewing', () => {
    const trackingState = { rotator_state: 'slewing' };
    const satelliteId = '25544';
    const selectedRotator = 'rotator1';

    expect(canStopTracking(trackingState, satelliteId, selectedRotator)).toBe(true);
  });

  it('should return false when already stopped', () => {
    const trackingState = { rotator_state: 'stopped' };
    const satelliteId = '25544';
    const selectedRotator = 'rotator1';

    expect(canStopTracking(trackingState, satelliteId, selectedRotator)).toBe(false);
  });

  it('should return false when parked', () => {
    const trackingState = { rotator_state: 'parked' };
    const satelliteId = '25544';
    const selectedRotator = 'rotator1';

    expect(canStopTracking(trackingState, satelliteId, selectedRotator)).toBe(false);
  });

  it('should return false when disconnected', () => {
    const trackingState = { rotator_state: 'disconnected' };
    const satelliteId = '25544';
    const selectedRotator = 'rotator1';

    expect(canStopTracking(trackingState, satelliteId, selectedRotator)).toBe(false);
  });

  it('should return false when no satellite selected', () => {
    const trackingState = { rotator_state: 'tracking' };
    const satelliteId = '';
    const selectedRotator = 'rotator1';

    expect(canStopTracking(trackingState, satelliteId, selectedRotator)).toBe(false);
  });

  it('should return true for mission targets while tracking with no satellite id', () => {
    const trackingState = {
      rotator_state: 'tracking',
      target_type: 'mission',
      command: 'Voyager 1',
      body_id: null,
      norad_id: null,
    };
    const satelliteId = '';
    const selectedRotator = 'rotator1';

    expect(canStopTracking(trackingState, satelliteId, selectedRotator)).toBe(true);
  });

  it('should return true for body targets while tracking with no satellite id', () => {
    const trackingState = {
      rotator_state: 'tracking',
      target_type: 'body',
      command: null,
      body_id: 'rhea',
      norad_id: null,
    };
    const satelliteId = '';
    const selectedRotator = 'rotator1';

    expect(canStopTracking(trackingState, satelliteId, selectedRotator)).toBe(true);
  });

  it('should return false when no rotator selected', () => {
    const trackingState = { rotator_state: 'tracking' };
    const satelliteId = '25544';

    expect(canStopTracking(trackingState, satelliteId, 'none')).toBe(false);
    expect(canStopTracking(trackingState, satelliteId, '')).toBe(false);
  });
});

describe('canConnectRotator', () => {
  it('should return true when not connected and rotator selected', () => {
    const rotatorData = { connected: false };
    const selectedRotator = 'rotator1';

    expect(canConnectRotator(rotatorData, selectedRotator)).toBe(true);
  });

  it('should return false when already connected', () => {
    const rotatorData = { connected: true };
    const selectedRotator = 'rotator1';

    expect(canConnectRotator(rotatorData, selectedRotator)).toBe(false);
  });

  it('should return false when no rotator selected', () => {
    const rotatorData = { connected: false };

    expect(canConnectRotator(rotatorData, 'none')).toBe(false);
    expect(canConnectRotator(rotatorData, '')).toBe(false);
  });
});

describe('isRotatorSelectionDisabled', () => {
  it('should return true when tracking', () => {
    expect(isRotatorSelectionDisabled({ rotator_state: 'tracking' })).toBe(true);
  });

  it('should return true when connected', () => {
    expect(isRotatorSelectionDisabled({ rotator_state: 'connected' })).toBe(true);
  });

  it('should return true when stopped', () => {
    expect(isRotatorSelectionDisabled({ rotator_state: 'stopped' })).toBe(true);
  });

  it('should return true when parked', () => {
    expect(isRotatorSelectionDisabled({ rotator_state: 'parked' })).toBe(true);
  });

  it('should return false when disconnected', () => {
    expect(isRotatorSelectionDisabled({ rotator_state: 'disconnected' })).toBe(false);
  });

  it('should return false for other states', () => {
    expect(isRotatorSelectionDisabled({ rotator_state: 'slewing' })).toBe(false);
    expect(isRotatorSelectionDisabled({ rotator_state: 'unknown' })).toBe(false);
  });
});
