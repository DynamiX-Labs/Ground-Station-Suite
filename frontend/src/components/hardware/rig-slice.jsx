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

export const fetchRigs = createAsyncThunk(
    'rigs/fetchAll',
    async ({socket}, {rejectWithValue}) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit('data_request', 'get-rigs', null, (response) => {
                    if (response.success) {
                        resolve(response.data);
                    } else {
                        reject(new Error('Failed to fetch rigs'));
                    }
                });
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

export const deleteRigs = createAsyncThunk(
    'rigs/deleteRigs',
    async ({socket, selectedIds}, {rejectWithValue}) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit('data_submission', 'delete-rig', selectedIds, (response) => {
                    if (response.success) {
                        resolve(response.data);
                    } else {
                        reject(new Error('Failed to delete rigs'));
                    }
                });
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

export const submitOrEditRig = createAsyncThunk(
    'rigs/submitOrEdit',
    async ({socket, formValues}, {rejectWithValue, dispatch}) => {
        const action = formValues.id ? 'edit-rig' : 'submit-rig';
        try {
            return await new Promise((resolve, reject) => {
                socket.emit('data_submission', action, formValues, (response) => {
                    if (response.success) {
                        dispatch(setOpenAddDialog(false));
                        resolve(response.data);
                    } else {
                        reject(new Error(`Failed to ${action === 'edit-rig' ? 'edit' : 'add'} rig`));
                    }
                });
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

const defaultRig = {
    id: null,
    name: '',
    host: 'localhost',
    port: 4532,
    radiotype: 'rx',
    radio_mode: 'duplex',
    tx_control_mode: 'auto',
    retune_interval_ms: 2000,
};

const rigsSlice = createSlice({
    name: 'rigs',
    initialState: {
        rigs: [],
        status: 'idle', // 'idle' | 'loading' | 'succeeded' | 'failed'
        error: null,
        openDeleteConfirm: false,
        openAddDialog: false,
        selected: [],
        loading: false,
        pageSize: 10,
        formValues: defaultRig,
    },
    reducers: {
        setRigs: (state, action) => {
            state.rigs = action.payload;
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
            state.formValues = defaultRig;
        },
        setError: (state, action) => {
            state.error = action.payload;
        },
        setStatus: (state, action) => {
            state.status = action.payload;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchRigs.pending, (state) => {
                state.status = 'loading';
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchRigs.fulfilled, (state, action) => {
                state.status = 'succeeded';
                state.loading = false;
                state.rigs = action.payload;
            })
            .addCase(fetchRigs.rejected, (state, action) => {
                state.status = 'failed';
                state.loading = false;
                state.error = action.payload;
            })
            .addCase(deleteRigs.pending, (state) => {
                state.loading = true;
                state.error = null;
                state.status = 'loading';
            })
            .addCase(deleteRigs.fulfilled, (state, action) => {
                state.loading = false;
                state.status = 'succeeded';
                state.rigs = action.payload;
                state.openDeleteConfirm = false;
            })
            .addCase(deleteRigs.rejected, (state, action) => {
                state.loading = false;
                state.status = 'failed';
                state.error = action.payload;
            })
            .addCase(submitOrEditRig.pending, (state) => {
                state.loading = true;
                state.error = null;
                state.status = 'loading';
            })
            .addCase(submitOrEditRig.fulfilled, (state, action) => {
                state.loading = false;
                state.status = 'succeeded';
                state.rigs = action.payload;
                state.formValues = defaultRig;
            })
            .addCase(submitOrEditRig.rejected, (state, action) => {
                state.loading = false;
                state.status = 'failed';
                state.error = action.payload;
            })
    },
});

export const {
    setRigs,
    setLoading,
    setPageSize,
    setOpenDeleteConfirm,
    setOpenAddDialog,
    setSelected,
    setFormValues,
    resetFormValues,
    setError,
    setStatus,
} = rigsSlice.actions;

export default rigsSlice.reducer;
