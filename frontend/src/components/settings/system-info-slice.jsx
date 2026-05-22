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

import { createSlice } from '@reduxjs/toolkit';

const initialState = {
    cpu: {
        architecture: null,
        processor: null,
        cores: { physical: null, logical: null },
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
    load_avg: null,
    cpu_temp_c: null,
    temperatures: {
        cpu_c: null,
        gpus_c: [],
        disks_c: {},
    },
};

const systemInfoSlice = createSlice({
    name: 'systemInfo',
    initialState,
    reducers: {
        setSystemInfo: (state, action) => {
            return { ...state, ...action.payload };
        },
        clearSystemInfo: () => initialState,
    },
});

export const { setSystemInfo, clearSystemInfo } = systemInfoSlice.actions;
export default systemInfoSlice.reducer;
