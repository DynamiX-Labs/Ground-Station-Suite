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

export const fetchSatelliteGroups = createAsyncThunk(
    'satelliteGroups/fetch',
    async ({ socket }, { rejectWithValue }) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit(
                    'data_request',
                    'get-satellite-groups-user',
                    (response) => {
                        if (response && response.data) {
                            resolve(response.data);
                        } else {
                            reject(new Error('Fetch failed.'));
                        }
                    }
                );
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

export const deleteSatelliteGroups = createAsyncThunk(
    'satelliteGroups/delete',
    async ({ socket, groupIds }, { rejectWithValue }) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit(
                    'data_submission',
                    'delete-satellite-group',
                    groupIds,
                    (response) => {
                        if (response.success) {
                            resolve(response.data);
                        } else {
                            reject(
                                new Error(response.error || 'Delete operation failed.')
                            );
                        }
                    }
                );
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);


export const AddOrEditSatelliteGroup = createAsyncThunk(
    'satelliteGroups/upsert',
    async ({socket, groupData}, {rejectWithValue}) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit('data_submission', groupData.id ? 'edit-satellite-group' : 'add-satellite-group', groupData,
                    (response) => {
                        if (response.success) {
                            resolve(response.data);
                        } else {
                            reject(
                                new Error(response.error || 'Upsert operation failed.')
                            );
                        }
                    }
                );
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);


const groupsSlice = createSlice({
    name: 'satelliteGroups',
    initialState: {
        groups: [],
        selected: [],
        satGroup: {},         // for storing the row being edited, if needed
        formDialogOpen: false,
        formErrorStatus: false,
        loading: false,
        error: null,
        deleteConfirmDialogOpen: false,
    },
    reducers: {
        setSelected: (state, action) => {
            state.selected = action.payload;
        },
        setSatGroup: (state, action) => {
            state.satGroup = action.payload;
        },
        setFormDialogOpen: (state, action) => {
            state.formDialogOpen = action.payload;
        },
        setFormErrorStatus: (state, action) => {
            state.formErrorStatus = action.payload;
        },
        setGroups: (state, action) => {
            state.groups = action.payload;
        },
        setDeleteConfirmDialogOpen: (state, action) => {
            state.deleteConfirmDialogOpen = action.payload;
        },
    },
    extraReducers: (builder) => {
        builder
            // Fetch
            .addCase(fetchSatelliteGroups.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchSatelliteGroups.fulfilled, (state, action) => {
                state.loading = false;
                state.groups = action.payload;
            })
            .addCase(fetchSatelliteGroups.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload;
            })
            .addCase(deleteSatelliteGroups.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(deleteSatelliteGroups.fulfilled, (state, action) => {
                state.loading = false;
                state.groups = action.payload; // or filter out deleted
            })
            .addCase(deleteSatelliteGroups.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload;
            })
            .addCase(AddOrEditSatelliteGroup.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(AddOrEditSatelliteGroup.fulfilled, (state, action) => {
                state.loading = false;
                state.groups = action.payload;
            })
            .addCase(AddOrEditSatelliteGroup.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload;
            });
    },
});

export const {
    setSelected,
    setSatGroup,
    setFormDialogOpen,
    setFormErrorStatus,
    setGroups,
    setDeleteConfirmDialogOpen
} = groupsSlice.actions;

export default groupsSlice.reducer;