import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';

const normalizeMonitoredEntry = (entry) => ({
    id: entry?.id,
    targetType: entry?.target_type ?? entry?.targetType ?? 'mission',
    targetKey: entry?.target_key ?? entry?.targetKey ?? '',
    displayName: entry?.display_name ?? entry?.displayName ?? '',
    command: entry?.command ?? '',
    bodyId: entry?.body_id ?? entry?.bodyId ?? '',
    color: entry?.color ?? null,
    sourceMode: entry?.source_mode ?? entry?.sourceMode ?? null,
    enabled: entry?.enabled !== false,
    lastRefreshAt: entry?.last_refresh_at ?? entry?.lastRefreshAt ?? null,
    lastError: entry?.last_error ?? entry?.lastError ?? null,
});

export const fetchMonitoredCelestial = createAsyncThunk(
    'celestialMonitored/fetchMonitoredCelestial',
    async ({ socket }, { rejectWithValue }) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit('data_request', 'get-monitored-celestial', null, (response) => {
                    if (response?.success) {
                        resolve((response.data || []).map(normalizeMonitoredEntry));
                    } else {
                        reject(new Error(response?.error || 'Failed to fetch monitored celestial targets'));
                    }
                });
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    },
);

export const createMonitoredCelestial = createAsyncThunk(
    'celestialMonitored/createMonitoredCelestial',
    async ({ socket, entry }, { rejectWithValue }) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit(
                    'data_submission',
                    'create-monitored-celestial',
                    {
                        target_type: entry.targetType || 'mission',
                        display_name: entry.displayName,
                        command: entry.targetType === 'mission' ? entry.command : null,
                        body_id: entry.targetType === 'body' ? entry.bodyId : null,
                        enabled: entry.enabled ?? true,
                        source_mode: entry.sourceMode || 'catalog',
                    },
                    (response) => {
                        if (response?.success) {
                            resolve(normalizeMonitoredEntry(response.data));
                        } else {
                            reject(new Error(response?.error || 'Failed to create monitored celestial target'));
                        }
                    },
                );
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    },
);

export const updateMonitoredCelestial = createAsyncThunk(
    'celestialMonitored/updateMonitoredCelestial',
    async ({ socket, entry }, { rejectWithValue }) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit(
                    'data_submission',
                    'update-monitored-celestial',
                    {
                        id: entry.id,
                        target_type: entry.targetType || 'mission',
                        display_name: entry.displayName,
                        command: entry.targetType === 'mission' ? entry.command : null,
                        body_id: entry.targetType === 'body' ? entry.bodyId : null,
                        color: entry.color ?? null,
                        enabled: entry.enabled,
                    },
                    (response) => {
                        if (response?.success) {
                            resolve(normalizeMonitoredEntry(response.data));
                        } else {
                            reject(new Error(response?.error || 'Failed to update monitored celestial target'));
                        }
                    },
                );
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    },
);

export const deleteMonitoredCelestial = createAsyncThunk(
    'celestialMonitored/deleteMonitoredCelestial',
    async ({ socket, ids }, { rejectWithValue }) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit('data_submission', 'delete-monitored-celestial', { ids }, (response) => {
                    if (response?.success) {
                        resolve(ids);
                    } else {
                        reject(new Error(response?.error || 'Failed to delete monitored celestial target(s)'));
                    }
                });
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    },
);

export const toggleMonitoredCelestialEnabled = createAsyncThunk(
    'celestialMonitored/toggleMonitoredCelestialEnabled',
    async ({ socket, id, enabled }, { rejectWithValue }) => {
        try {
            return await new Promise((resolve, reject) => {
                socket.emit(
                    'data_submission',
                    'toggle-monitored-celestial-enabled',
                    { id, enabled },
                    (response) => {
                        if (response?.success) {
                            resolve({ id, enabled });
                        } else {
                            reject(new Error(response?.error || 'Failed to toggle monitored celestial target'));
                        }
                    },
                );
            });
        } catch (error) {
            return rejectWithValue(error.message);
        }
    },
);

const monitoredSlice = createSlice({
    name: 'celestialMonitored',
    initialState: {
        monitored: [],
        selectedIds: [],
        addDialogOpen: false,
        manageDialogOpen: false,
        form: {
            targetType: 'mission',
            displayName: '',
            command: '',
            bodyId: '',
        },
        formError: '',
        loading: false,
        saveLoading: false,
        error: null,
        openGridSettingsDialog: false,
        tableColumnVisibility: {
            displayName: true,
            targetType: true,
            color: true,
            command: true,
            source: true,
            sourceMode: true,
            enabled: true,
            elevationDeg: true,
            azimuthDeg: true,
            distanceFromSunAu: true,
            speedKmS: true,
            lightTimeMinutes: true,
            lastRefreshAt: true,
            lastRefreshAge: true,
            projectionSpan: true,
            cacheStatus: true,
            stale: true,
            sampleCount: true,
            lastError: true,
        },
        tablePageSize: 10,
        tableSortModel: [{ field: 'elevationDeg', sort: 'desc' }, { field: 'displayName', sort: 'asc' }],
    },
    reducers: {
        openAddDialog: (state) => {
            state.addDialogOpen = true;
            state.formError = '';
        },
        closeAddDialog: (state) => {
            state.addDialogOpen = false;
            state.formError = '';
            state.form.targetType = 'mission';
            state.form.displayName = '';
            state.form.command = '';
            state.form.bodyId = '';
        },
        openManageDialog: (state) => {
            state.manageDialogOpen = true;
        },
        closeManageDialog: (state) => {
            state.manageDialogOpen = false;
        },
        setMonitoredFormField: (state, action) => {
            const { field, value } = action.payload;
            if (field in state.form) {
                state.form[field] = value;
            }
        },
        setMonitoredFormError: (state, action) => {
            state.formError = action.payload || '';
        },
        setSelectedMonitoredIds: (state, action) => {
            const next = Array.isArray(action.payload) ? action.payload : [];
            state.selectedIds = next.length ? [next[0]] : [];
        },
        setOpenGridSettingsDialog: (state, action) => {
            state.openGridSettingsDialog = action.payload;
        },
        setMonitoredTableColumnVisibility: (state, action) => {
            state.tableColumnVisibility = action.payload;
        },
        setMonitoredTablePageSize: (state, action) => {
            state.tablePageSize = action.payload;
        },
        setMonitoredTableSortModel: (state, action) => {
            state.tableSortModel = action.payload || [];
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchMonitoredCelestial.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchMonitoredCelestial.fulfilled, (state, action) => {
                state.loading = false;
                state.monitored = action.payload;
                const validIds = new Set(action.payload.map((entry) => entry.id));
                state.selectedIds = state.selectedIds.filter((id) => validIds.has(id));
            })
            .addCase(fetchMonitoredCelestial.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload || action.error?.message || 'Unknown error';
            })
            .addCase(createMonitoredCelestial.pending, (state) => {
                state.saveLoading = true;
                state.formError = '';
            })
            .addCase(createMonitoredCelestial.fulfilled, (state, action) => {
                state.saveLoading = false;
                state.monitored.push(action.payload);
                state.selectedIds = [action.payload.id];
                state.addDialogOpen = false;
                state.form.displayName = '';
                state.form.command = '';
                state.form.bodyId = '';
                state.formError = '';
            })
            .addCase(createMonitoredCelestial.rejected, (state, action) => {
                state.saveLoading = false;
                state.formError = action.payload || action.error?.message || 'Failed to create target';
            })
            .addCase(updateMonitoredCelestial.fulfilled, (state, action) => {
                state.saveLoading = false;
                const index = state.monitored.findIndex((entry) => entry.id === action.payload.id);
                if (index !== -1) {
                    state.monitored[index] = action.payload;
                }
            })
            .addCase(updateMonitoredCelestial.pending, (state) => {
                state.saveLoading = true;
            })
            .addCase(updateMonitoredCelestial.rejected, (state) => {
                state.saveLoading = false;
            })
            .addCase(deleteMonitoredCelestial.fulfilled, (state, action) => {
                const idsToDelete = new Set(action.payload || []);
                state.monitored = state.monitored.filter((entry) => !idsToDelete.has(entry.id));
                state.selectedIds = state.selectedIds.filter((id) => !idsToDelete.has(id));
            })
            .addCase(toggleMonitoredCelestialEnabled.fulfilled, (state, action) => {
                const entry = state.monitored.find((item) => item.id === action.payload.id);
                if (entry) {
                    entry.enabled = action.payload.enabled;
                }
            });
    },
});

export const {
    openAddDialog,
    closeAddDialog,
    openManageDialog,
    closeManageDialog,
    setMonitoredFormField,
    setMonitoredFormError,
    setSelectedMonitoredIds,
    setOpenGridSettingsDialog,
    setMonitoredTableColumnVisibility,
    setMonitoredTablePageSize,
    setMonitoredTableSortModel,
} = monitoredSlice.actions;

export default monitoredSlice.reducer;
