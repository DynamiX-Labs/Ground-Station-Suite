import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

export const fetchUpdateCheck = createAsyncThunk(
    'updateCheck/fetchUpdateCheck',
    async (_, { rejectWithValue }) => {
        try {
            const response = await fetch('/api/update-check');
            if (!response.ok) {
                throw new Error('Failed to fetch update info');
            }
            return await response.json();
        } catch (error) {
            return rejectWithValue(error.message);
        }
    }
);

const updateSlice = createSlice({
    name: 'updateCheck',
    initialState: {
        data: {
            currentVersion: null,
            latestVersion: null,
            latestTag: null,
            latestUrl: null,
            publishedAt: null,
            isUpdateAvailable: false,
        },
        loading: false,
        error: null,
        lastChecked: null,
    },
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(fetchUpdateCheck.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchUpdateCheck.fulfilled, (state, action) => {
                state.loading = false;
                state.data = action.payload || state.data;
                state.lastChecked = Date.now();
            })
            .addCase(fetchUpdateCheck.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload;
            });
    },
});

export default updateSlice.reducer;
