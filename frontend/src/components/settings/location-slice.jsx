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



import {createSlice, createAsyncThunk} from '@reduxjs/toolkit';
import { toast } from '../../utils/toast-with-timestamp.jsx';
import {getMaidenhead} from '../common/common.jsx';


export const fetchLocationForUserId = createAsyncThunk(
    'location/fetchLocationForUser',
    async ({socket}, {rejectWithValue}) => {
        return new Promise((resolve, reject) => {
            socket.emit(
                'data_request',
                'get-locations',
                null,
                (response) => {
                    if (response.success) {
                        if (response.data && response.data.length > 0) {
                            // Return the first location from the list
                            resolve(response.data[0]);
                        } else {
                            toast.warning('No location found in the backend, please set one');
                            resolve(null); // or resolve({}) if no data
                        }
                    } else {
                        toast.error('Failed to get location from backend');
                        reject(rejectWithValue('Failed to get location'));
                    }
                }
            );
        });
    }
);


export const storeLocation = createAsyncThunk(
    'location/handleSetLocation',
    async ({socket, location, altitude, locationId}, {rejectWithValue}) => {
        return new Promise((resolve, reject) => {
            const command = locationId ? 'edit-location' : 'submit-location';
            const data = {...location, alt: altitude, name: "home"};
            if (locationId) {
                data.id = locationId;
            }

            socket.emit('data_submission', command, data, (response) => {
                if (response['success']) {
                    toast.success('Location set successfully');
                    resolve(response.data || data);
                } else {
                    toast.error('Failed to set location');
                    reject(rejectWithValue('Failed to set location'));
                }
            });
        });
    }
);


const locationSlice = createSlice({
    name: 'location',
    initialState: {
        locationSaving: false,
        locationLoading: false,
        location: null,
        altitude: 0,
        locationId: null,
        qth: '',
        polylines: [],
        error: null,
    },
    reducers: {
        setLocation: (state, action) => {
            state.location = action.payload;
        },
        setLocationId: (state, action) => {
            state.locationId = action.payload;
        },
        setQth: (state, action) => {
            state.qth = action.payload;
        },
        setPolylines: (state, action) => {
            state.polylines = action.payload;
        },
        setLocationLoading: (state, action) => {
            state.locationLoading = action.payload;
        },
        setLocationSaving: (state, action) => {
            state.locationSaving = action.payload;
        },
        setAltitude: (state, action) => {
            state.altitude = action.payload;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchLocationForUserId.pending, (state) => {
                state.locationLoading = true;
                state.error = null;
            })
            .addCase(fetchLocationForUserId.fulfilled, (state, action) => {
                state.locationLoading = false;
                if (action.payload) {
                    const payload = action.payload;
                    state.location = action.payload;
                    state.locationId = action.payload.id;
                    state.altitude = action.payload.alt || 0;
                    state.qth = getMaidenhead(parseFloat(payload.lat), parseFloat(payload.lon));
                } else {
                    // If no location from backend, clear persisted location data
                    state.location = null;
                    state.locationId = null;
                    state.altitude = 0;
                    state.qth = '';
                }
            })
            .addCase(fetchLocationForUserId.rejected, (state, action) => {
                state.locationLoading = false;
                state.error = action.payload;
            })
            .addCase(storeLocation.pending, (state) => {
                state.error = null;
                state.locationSaving = true;
            })
            .addCase(storeLocation.fulfilled, (state, action) => {
                state.locationLoading = false;
                if (action.payload) {
                    const payload = action.payload;
                    state.location = action.payload;
                    state.locationId = action.payload.id;
                    state.altitude = action.payload.alt || state.altitude;
                    state.qth = getMaidenhead(parseFloat(payload.lat), parseFloat(payload.lon));
                    state.locationSaving = false;
                }
            })
            .addCase(storeLocation.rejected, (state, action) => {
                state.locationLoading = false;
                state.error = action.payload;
                state.locationSaving = false;
            });
    },
});

export const {
    setLocation,
    setLocationId,
    setQth,
    setPolylines,
    setLocationLoading,
    setAltitude,
} = locationSlice.actions;

export default locationSlice.reducer;