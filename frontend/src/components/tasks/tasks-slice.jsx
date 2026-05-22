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

export const stopBackgroundTask = createAsyncThunk(
    'backgroundTasks/stopBackgroundTask',
    async ({ socket, task_id, timeout = 5.0 }, { rejectWithValue }) => {
        try {
            const response = await new Promise((resolve, reject) => {
                socket.emit(
                    'background_task:stop',
                    { task_id, timeout },
                    (result) => {
                        if (result?.success) {
                            resolve(result);
                        } else {
                            reject(new Error(result?.error || 'Unknown error'));
                        }
                    }
                );
            });
            return response;
        } catch (error) {
            return rejectWithValue(error.message || 'Failed to stop background task');
        }
    }
);

const initialState = {
    tasks: {}, // { task_id: TaskInfo }
    runningTaskIds: [], // Array of running task IDs
    completedTaskIds: [], // Array of recently completed task IDs
};

const tasksSlice = createSlice({
    name: 'backgroundTasks',
    initialState,
    reducers: {
        taskStarted: (state, action) => {
            const { task_id, name, command, args, pid, start_time } = action.payload;
            state.tasks[task_id] = {
                task_id,
                name,
                command,
                args,
                pid,
                start_time,
                status: 'running',
                output_lines: [],
                progress: 0,
                end_time: null,
                return_code: null,
            };
            state.runningTaskIds.push(task_id);
            // Remove from completed if it was there
            state.completedTaskIds = state.completedTaskIds.filter(id => id !== task_id);
        },

        taskProgress: (state, action) => {
            const { task_id, stream, output, progress } = action.payload;
            if (state.tasks[task_id]) {
                // Initialize output_lines if it doesn't exist
                if (!state.tasks[task_id].output_lines) {
                    state.tasks[task_id].output_lines = [];
                }
                state.tasks[task_id].output_lines.push({ stream, output, timestamp: Date.now() });
                // Keep only last 1000 lines to avoid memory issues
                if (state.tasks[task_id].output_lines.length > 1000) {
                    state.tasks[task_id].output_lines.shift();
                }
                // Update progress if provided
                if (progress !== undefined && progress !== null) {
                    state.tasks[task_id].progress = progress;
                }
            }
        },

        taskCompleted: (state, action) => {
            const { task_id, status, return_code, duration } = action.payload;
            if (state.tasks[task_id]) {
                state.tasks[task_id].status = status;
                state.tasks[task_id].return_code = return_code;
                state.tasks[task_id].end_time = Date.now();
                state.tasks[task_id].duration = duration;

                // Move from running to completed
                state.runningTaskIds = state.runningTaskIds.filter(id => id !== task_id);
                if (!state.completedTaskIds.includes(task_id)) {
                    state.completedTaskIds.unshift(task_id);
                    // Keep only last 20 completed tasks
                    if (state.completedTaskIds.length > 20) {
                        const removed = state.completedTaskIds.pop();
                        delete state.tasks[removed];
                    }
                }
            }
        },

        taskStopped: (state, action) => {
            const { task_id, duration } = action.payload;
            if (state.tasks[task_id]) {
                state.tasks[task_id].status = 'stopped';
                state.tasks[task_id].end_time = Date.now();
                state.tasks[task_id].duration = duration;

                // Move from running to completed
                state.runningTaskIds = state.runningTaskIds.filter(id => id !== task_id);
                if (!state.completedTaskIds.includes(task_id)) {
                    state.completedTaskIds.unshift(task_id);
                    // Keep only last 20 completed tasks
                    if (state.completedTaskIds.length > 20) {
                        const removed = state.completedTaskIds.pop();
                        delete state.tasks[removed];
                    }
                }
            }
        },

        taskError: (state, action) => {
            const { task_id, error } = action.payload;
            if (state.tasks[task_id]) {
                state.tasks[task_id].error = error;
                state.tasks[task_id].status = 'failed';
            }
        },

        setTaskList: (state, action) => {
            const { tasks } = action.payload;
            // Merge incoming task list with existing tasks
            tasks.forEach(task => {
                state.tasks[task.task_id] = task;
                if (task.status === 'running' && !state.runningTaskIds.includes(task.task_id)) {
                    state.runningTaskIds.push(task.task_id);
                }
            });
        },

        clearCompletedTasks: (state) => {
            state.completedTaskIds.forEach(task_id => {
                delete state.tasks[task_id];
            });
            state.completedTaskIds = [];
        },

        removeTask: (state, action) => {
            const task_id = action.payload;
            delete state.tasks[task_id];
            state.runningTaskIds = state.runningTaskIds.filter(id => id !== task_id);
            state.completedTaskIds = state.completedTaskIds.filter(id => id !== task_id);
        },
    },
});

export const {
    taskStarted,
    taskProgress,
    taskCompleted,
    taskStopped,
    taskError,
    setTaskList,
    clearCompletedTasks,
    removeTask,
} = tasksSlice.actions;

export default tasksSlice.reducer;
