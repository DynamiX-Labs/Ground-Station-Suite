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


import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const fetchPreferences = createAsyncThunk(
    'preferences/fetchPreferences',
    async ({socket}, {rejectWithValue}) => {
        return new Promise((resolve, reject) => {
            socket.emit('data_request', 'fetch-preferences', (response) => {
                if (response['success']) {
                    resolve(response.data);
                } else {
                    reject(rejectWithValue('Could not fetch preferences'));
                }
            });
        });
    }
);


export const updatePreferences = createAsyncThunk(
    'preferences/updatePreferences',
    async ({ socket }, {getState, rejectWithValue}) => {
        return new Promise((resolve, reject) => {
            const preferences = getState().preferences;
            socket.emit('data_submission', 'update-preferences', [...preferences.preferences], (response) => {
                if (response['success']) {
                    resolve(response.data);
                } else {
                    reject(rejectWithValue('Failed to set preferences'));
                }
            });
        });
    }
);


const preferencesSlice = createSlice({
    name: 'preferences',
    initialState: {
        loading: false,
        preferences: [
            {
                id: null,
                name: 'language',
                value: 'en_US',
            },
            {
                id: null,
                name: 'theme',
                value: 'auto',
            },
            {
                id: null,
                name: 'celestial_enabled',
                value: 'false',
            },
            {
                id: null,
                value: 'Europe/Athens',
                name: 'timezone',
            },
            {
                id: null,
                name: 'stadia_maps_api_key',
                value: "",
            },
            {
                id: null,
                name: 'toast_position',
                value: 'bottom-center',
            },
            {
                id: null,
                name: 'gemini_api_key',
                value: '',
            },
            {
                id: null,
                name: 'deepgram_api_key',
                value: '',
            },
            {
                id: null,
                name: 'google_translate_api_key',
                value: '',
            }
        ],
        status: 'idle',
        error: null,

    },
    reducers: {
        setPreference: (state, action) => {
            const {name, value} = action.payload;
            const preference = state.preferences.find((pref) => pref.name === name);
            if (preference) {
                preference.value = value;
            }
        },
        setLoading: (state, action) => {
            state.loading = action.payload;
        },
    },
    extraReducers: (builder) => {
        builder
            // fetchPreferences
            .addCase(fetchPreferences.pending, (state) => {
                state.status = 'loading';
            })
            .addCase(fetchPreferences.fulfilled, (state, action) => {
                state.status = 'succeeded';
                action.payload.forEach((preference) => {
                    const existingPreference = state.preferences.find((pref) => pref.name === preference.name);
                    if (existingPreference) {
                        existingPreference.value = preference.value;
                    } else {
                        // Add new preference from backend if it doesn't exist in state
                        state.preferences.push(preference);
                    }
                });
            })
            .addCase(fetchPreferences.rejected, (state, action) => {
                state.status = 'failed';
                state.error = action.payload;
            })
            .addCase(updatePreferences.pending, (state) => {
                state.status = 'loading';
            })
            .addCase(updatePreferences.fulfilled, (state, action) => {
                state.status = 'succeeded';
                state.preferences = action.payload;
            })
            .addCase(updatePreferences.rejected, (state, action) => {
                state.status = 'failed';
                state.error = action.payload;
            });
    },
});


export const {
    setPreference,
} = preferencesSlice.actions;


export default preferencesSlice.reducer;
