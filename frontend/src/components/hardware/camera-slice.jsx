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

export const fetchCameras = createAsyncThunk(
    'cameras/fetchAll',
    async ({ socket }, { rejectWithValue }) => {
        try {
            // Example: you could wrap socket events with a Promise
            return await new Promise((resolve, reject) => {
                socket.emit('data_request', 'get-cameras', null, (res) => {
                    if (res.success) {
                        resolve(res.data);
                    } else {
                        reject(new Error('Failed to fetch cameras'));
                    }
                });
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

export const deleteCameras = createAsyncThunk(
    'cameras/deleteCameras',
    async ({ socket, selectedIds }, { rejectWithValue }) => {
        try {
            // Wrap your socket call in a Promise
            return await new Promise((resolve, reject) => {
                socket.emit('data_submission', 'delete-camera', selectedIds, (response) => {
                    if (response.success) {
                        resolve(response.data);
                    } else {
                        reject(new Error('Failed to delete cameras'));
                    }
                });
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

export const submitOrEditCamera = createAsyncThunk(
    'cameras/submitOrEdit',
    async ({socket, formValues}, {rejectWithValue, dispatch}) => {
        const action = formValues.id ? 'edit-camera' : 'submit-camera';
        try {
            return await new Promise((resolve, reject) => {
                socket.emit('data_submission', action, formValues, (response) => {
                    if (response.success) {
                        dispatch(setOpenAddDialog(false));
                        resolve(response.data);
                    } else {
                        reject(new Error(`Failed to ${action === 'edit-camera' ? 'edit' : 'add'} camera`));
                    }
                });
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

const defaultCamera = {
    id: null,
    name: '',
    url: '',
    type: '',
};

const camerasSlice = createSlice({
    name: 'cameras',
    initialState: {
        selectedCamera: defaultCamera,
        selectedCameraId: "",
        cameras: [],
        status: 'idle', // 'idle' | 'loading' | 'succeeded' | 'failed'
        error: null,
        openDeleteConfirm: false,
        openAddDialog: false,
        selected: [],
        loading: false,
        pageSize: 10,
        formValues: defaultCamera,
    },
    reducers: {
        setCameras: (state, action) => {
            state.cameras = action.payload;
        },
        setLoading: (state, action) => {
            state.loading = action.payload;
        },
        setPageSize: (state, action) => {
            state.pageSize = action.payload;
        },
        setOpenDeleteConfirm: (state, action) => {
            state.openDeleteConfirm = action.payload;
        },
        setOpenAddDialog: (state, action) => {
            state.openAddDialog = action.payload;
        },
        setSelected: (state, action) => {
            state.selected = action.payload;
        },
        setFormValues: (state, action) => {
            state.formValues = {
                ...state.formValues,
                ...action.payload,
            };
        },
        resetFormValues: (state) => {
            state.formValues = defaultCamera;
        },
        setError: (state, action) => {
            state.error = action.payload;
        },
        setStatus: (state, action) => {
            state.status = action.payload;
        },
        setSelectedCameraId: (state, action) => {
            state.selectedCameraId = action.payload;
            state.selectedCamera = state.cameras.find(camera => camera.id === action.payload) || defaultCamera;
        },
    },
    extraReducers: (builder) => {
        builder
            // When the thunk is pending, mark status/loading states
            .addCase(fetchCameras.pending, (state) => {
                state.status = 'loading';
                state.loading = true;
                state.error = null;
            })
            // When the thunk completes successfully
            .addCase(fetchCameras.fulfilled, (state, action) => {
                state.status = 'succeeded';
                state.loading = false;
                state.cameras = action.payload; // the data returned by the thunk
            })
            // If the thunk fails
            .addCase(fetchCameras.rejected, (state, action) => {
                state.status = 'failed';
                state.loading = false;
                state.error = action.payload;
            })
            // Pending: set loading, clear errors as needed
            .addCase(deleteCameras.pending, (state) => {
                state.loading = true;
                state.error = null;
                state.status = 'loading';
            })
            // Fulfilled: update the state with the new data from the server
            .addCase(deleteCameras.fulfilled, (state, action) => {
                state.loading = false;
                state.status = 'succeeded';
                state.cameras = action.payload; // Updated camera list from server
                state.openDeleteConfirm = false;
            })
            // Rejected: store the error
            .addCase(deleteCameras.rejected, (state, action) => {
                state.loading = false;
                state.status = 'failed';
                state.error = action.payload;
            })
            // Pending: set loading state and clear errors as needed
            .addCase(submitOrEditCamera.pending, (state) => {
                state.loading = true;
                state.error = null;
                state.status = 'loading';
            })
            // Fulfilled: update the state and reset formValues
            .addCase(submitOrEditCamera.fulfilled, (state, action) => {
                state.loading = false;
                state.status = 'succeeded';
                state.cameras = action.payload; // Add a new camera or update existing
                state.formValues = defaultCamera; // Reset the form values
            })
            // Rejected: store the error message
            .addCase(submitOrEditCamera.rejected, (state, action) => {
                state.loading = false;
                state.status = 'failed';
                state.error = action.payload;
            })
    },
});

export const {
    setCameras,
    setLoading,
    setPageSize,
    setOpenDeleteConfirm,
    setOpenAddDialog,
    setSelected,
    setFormValues,
    resetFormValues,
    setError,
    setStatus,
    setSelectedCameraId,
} = camerasSlice.actions;

export default camerasSlice.reducer;