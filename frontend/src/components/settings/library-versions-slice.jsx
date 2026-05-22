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

export const fetchLibraryVersions = createAsyncThunk(
    'libraryVersions/fetchLibraryVersions',
    async ({socket}, {rejectWithValue}) => {
        return new Promise((resolve, reject) => {
            socket.emit('data_request', 'fetch_library_versions', null, (response) => {
                if (response && response.success) {
                    resolve({ type: 'backend', data: response.data });
                } else {
                    reject(rejectWithValue(response?.error || 'Could not fetch library versions'));
                }
            });
        });
    }
);

export const fetchFrontendLibraryVersions = createAsyncThunk(
    'libraryVersions/fetchFrontendLibraryVersions',
    async ({socket}, {rejectWithValue}) => {
        return new Promise((resolve, reject) => {
            socket.emit('data_request', 'fetch_frontend_library_versions', null, (response) => {
                if (response && response.success) {
                    resolve({ type: 'frontend', data: response.data });
                } else {
                    reject(rejectWithValue(response?.error || 'Could not fetch frontend library versions'));
                }
            });
        });
    }
);

const libraryVersionsSlice = createSlice({
    name: 'libraryVersions',
    initialState: {
        backend: {
            loading: false,
            error: null,
            categories: {},
            totalCount: 0,
        },
        frontend: {
            loading: false,
            error: null,
            categories: {},
            totalCount: 0,
        },
    },
    reducers: {
        clearError: (state) => {
            state.backend.error = null;
            state.frontend.error = null;
        },
    },
    extraReducers: (builder) => {
        builder
            // Backend library versions
            .addCase(fetchLibraryVersions.pending, (state) => {
                state.backend.loading = true;
                state.backend.error = null;
            })
            .addCase(fetchLibraryVersions.fulfilled, (state, action) => {
                state.backend.loading = false;
                state.backend.categories = action.payload.data.categories || {};
                state.backend.totalCount = action.payload.data.total_count || 0;
            })
            .addCase(fetchLibraryVersions.rejected, (state, action) => {
                state.backend.loading = false;
                state.backend.error = action.payload || 'Failed to fetch library versions';
            })
            // Frontend library versions
            .addCase(fetchFrontendLibraryVersions.pending, (state) => {
                state.frontend.loading = true;
                state.frontend.error = null;
            })
            .addCase(fetchFrontendLibraryVersions.fulfilled, (state, action) => {
                state.frontend.loading = false;
                state.frontend.categories = action.payload.data.categories || {};
                state.frontend.totalCount = action.payload.data.total_count || 0;
            })
            .addCase(fetchFrontendLibraryVersions.rejected, (state, action) => {
                state.frontend.loading = false;
                state.frontend.error = action.payload || 'Failed to fetch frontend library versions';
            });
    },
});

export const { clearError } = libraryVersionsSlice.actions;
export default libraryVersionsSlice.reducer;
