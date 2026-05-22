import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const fetchVersionInfo = createAsyncThunk(
    'version/fetchVersionInfo',
    async (_, { rejectWithValue }) => {
        try {
            const response = await fetch('/api/version');
            if (!response.ok) {
                throw new Error('Failed to fetch version info');
            }
            return await response.json();
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);


const versionSlice = createSlice({
    name: 'version',
    initialState: {
        data: {
            version: null,
            buildDate: null,
            gitCommit: null,
            environment: null,
            system: {
                cpu: {
                    architecture: null,
                    processor: null,
                    cores: {
                        physical: null,
                        logical: null,
                    },
                    usage_percent: null,
                },
                memory: {
                    total_gb: null,
                    available_gb: null,
                    used_gb: null,
                    usage_percent: null,
                },
                disk: {
                    total_gb: null,
                    available_gb: null,
                    used_gb: null,
                    usage_percent: null,
                },
                os: {
                    system: null,
                    release: null,
                    version: null,
                },
            },
        },
        previousVersion: null,
        loading: false,
        error: null,
        hasVersionChanged: false,
    },
    reducers: {
        clearVersionChangeFlag: (state) => {
            state.hasVersionChanged = false;
        },
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchVersionInfo.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchVersionInfo.fulfilled, (state, action) => {
                state.loading = false;

                // Only trigger version change if the version string actually changed
                // Ignore system info changes (CPU/memory usage fluctuates)
                const currentVersion = state.data?.version;
                const newVersion = action.payload?.version;

                if (currentVersion && newVersion && currentVersion !== newVersion) {
                    state.previousVersion = currentVersion;
                    state.hasVersionChanged = true;
                }

                state.data = action.payload;
            })
            .addCase(fetchVersionInfo.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload;
            });
    },
});

export const { clearVersionChangeFlag } = versionSlice.actions;
export default versionSlice.reducer;