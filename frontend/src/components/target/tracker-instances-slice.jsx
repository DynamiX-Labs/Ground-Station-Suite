import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';

export const fetchTrackerInstances = createAsyncThunk(
    'trackerInstances/fetchTrackerInstances',
    async ({ socket }, { rejectWithValue }) => {
        return new Promise((resolve, reject) => {
            socket.emit('data_request', 'get-tracker-instances', null, (response) => {
                if (response?.success) {
                    resolve(response?.data || {});
                } else {
                    reject(
                        rejectWithValue(
                            response?.message
                            || response?.error
                            || 'Failed to fetch tracker instances'
                        )
                    );
                }
            });
        });
    }
);

export const deleteTrackerInstance = createAsyncThunk(
    'trackerInstances/deleteTrackerInstance',
    async ({ socket, trackerId }, { rejectWithValue }) => {
        return new Promise((resolve, reject) => {
            socket.emit(
                'data_submission',
                'delete-tracker-instance',
                { tracker_id: trackerId },
                async (response) => {
                    if (response?.success) {
                        try {
                            const instances = Array.isArray(response?.data?.instances)
                                ? response.data.instances
                                : [];
                            const nextTrackerId = String(instances?.[0]?.tracker_id || '').trim();
                            if (nextTrackerId) {
                                await new Promise((requestResolve) => {
                                    socket.emit(
                                        'data_request',
                                        'get-tracking-state',
                                        { tracker_id: nextTrackerId },
                                        () => requestResolve()
                                    );
                                });
                            }
                        } catch (_error) {
                            // Keep delete operation successful even if refresh fails.
                        }
                        resolve(response?.data || {});
                    } else {
                        reject(
                            rejectWithValue(
                                response?.message
                                || response?.error
                                || 'Failed to delete tracker instance'
                            )
                        );
                    }
                }
            );
        });
    }
);

const trackerInstancesSlice = createSlice({
    name: 'trackerInstances',
    initialState: {
        instances: [],
        updatedAt: null,
        loading: false,
        error: null,
    },
    reducers: {
        setTrackerInstances(state, action) {
            const payload = action.payload || {};
            state.instances = Array.isArray(payload.instances) ? payload.instances : [];
            state.updatedAt = payload.updated_at || Date.now() / 1000;
            state.error = null;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchTrackerInstances.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchTrackerInstances.fulfilled, (state, action) => {
                state.loading = false;
                const payload = action.payload || {};
                state.instances = Array.isArray(payload.instances) ? payload.instances : [];
                state.updatedAt = payload.updated_at || Date.now() / 1000;
                state.error = null;
            })
            .addCase(fetchTrackerInstances.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload || action.error?.message || 'Failed to fetch tracker instances';
            })
            .addCase(deleteTrackerInstance.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(deleteTrackerInstance.fulfilled, (state, action) => {
                state.loading = false;
                state.error = null;
                const payload = action.payload || {};
                const payloadInstances = Array.isArray(payload.instances) ? payload.instances : null;
                const deletedTrackerId = String(
                    payload.tracker_id
                    || action.meta?.arg?.trackerId
                    || ''
                ).trim();
                if (payloadInstances) {
                    state.instances = deletedTrackerId
                        ? payloadInstances.filter(
                            (instance) => String(instance?.tracker_id || '').trim() !== deletedTrackerId
                        )
                        : payloadInstances;
                    state.updatedAt = payload.updated_at || Date.now() / 1000;
                    return;
                }
                if (deletedTrackerId) {
                    state.instances = state.instances.filter(
                        (instance) => String(instance?.tracker_id || '').trim() !== deletedTrackerId
                    );
                    state.updatedAt = Date.now() / 1000;
                }
            })
            .addCase(deleteTrackerInstance.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload || action.error?.message || 'Failed to delete tracker instance';
            });
    },
});

export const { setTrackerInstances } = trackerInstancesSlice.actions;
export default trackerInstancesSlice.reducer;
