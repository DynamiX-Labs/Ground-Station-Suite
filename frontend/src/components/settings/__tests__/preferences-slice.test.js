/**
 * Example Redux slice test
 */

import { describe, it, expect } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import preferencesReducer from '../preferences-slice';

describe('preferences slice', () => {
  it('should return the initial state', () => {
    const store = configureStore({
      reducer: {
        preferences: preferencesReducer,
      },
    });

    const state = store.getState().preferences;
    expect(state).toBeDefined();
  });

  // Add more tests for your actions and reducers
  it('should handle preference updates', () => {
    // Example test - adjust based on your actual slice actions
    const store = configureStore({
      reducer: {
        preferences: preferencesReducer,
      },
    });

    //const initialState = store.getState().preferences;

    // Dispatch an action and test the state change
    // store.dispatch(updatePreference({ key: 'theme', value: 'dark' }));

    // const newState = store.getState().preferences;
    // expect(newState.theme).toBe('dark');
  });
});
