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

/**
 * Transcription Redux Slice
 *
 * Manages real-time audio transcription data from Google Gemini API.
 * Stores the last 500 words with timestamps and metadata.
 */

// Load font size from localStorage or use default (per-VFO)
const loadFontSizeMultiplier = (vfoNumber) => {
    try {
        const saved = localStorage.getItem(`transcription_font_size_vfo${vfoNumber}`);
        if (saved) {
            const parsed = parseFloat(saved);
            if (!isNaN(parsed) && parsed >= 0.5 && parsed <= 2.0) {
                return parsed;
            }
        }
    } catch (e) {
        console.error(`Failed to load font size multiplier for VFO${vfoNumber} from localStorage:`, e);
    }
    return 1.0;
};

// Load text alignment from localStorage or use default (per-VFO)
const loadTextAlignment = (vfoNumber) => {
    try {
        const saved = localStorage.getItem(`transcription_text_alignment_vfo${vfoNumber}`);
        if (saved && ['left', 'center', 'right'].includes(saved)) {
            return saved;
        }
    } catch (e) {
        console.error(`Failed to load text alignment for VFO${vfoNumber} from localStorage:`, e);
    }
    return 'left';
};

const initialState = {
    // Array of transcription entries: [{id, text, timestamp, language, sessionId, vfoNumber}]
    entries: [],

    // Current word count across all entries
    wordCount: 0,

    // Maximum words to keep (500 words = ~3-5 minutes of speech)
    maxWords: 500,

    // Flag to indicate if transcription is actively receiving data
    isActive: false,

    // Last received timestamp
    lastUpdated: null,

    // Live accumulating transcription per session+VFO
    // {`${sessionId}_${vfoNumber}`: {id, segments, timestamp, language, startTime, sessionId, vfoNumber}}
    liveTranscription: {},

    // Per-VFO subtitle settings (persisted)
    vfoFontSizes: {
        1: loadFontSizeMultiplier(1),
        2: loadFontSizeMultiplier(2),
        3: loadFontSizeMultiplier(3),
        4: loadFontSizeMultiplier(4),
    },
    vfoTextAlignments: {
        1: loadTextAlignment(1),
        2: loadTextAlignment(2),
        3: loadTextAlignment(3),
        4: loadTextAlignment(4),
    },
};

const transcriptionSlice = createSlice({
    name: 'transcription',
    initialState,
    reducers: {
        /**
         * Add a new transcription fragment
         * Continuously appends to live transcription, never-ending stream
         */
        addTranscription: (state, action) => {
            const { text, sessionId, vfoNumber, language, is_final } = action.payload;
            const trimmedText = text.trim();

            console.log('[Redux] addTranscription called:', { text: trimmedText, sessionId, vfoNumber, language, is_final });

            // Skip empty text
            if (!trimmedText) {
                console.log('[Redux] Skipping empty text');
                return;
            }

            // Create composite key for session + VFO
            const transcriptionKey = `${sessionId}_${vfoNumber}`;

            // Initialize or update live transcription for this session+VFO
            if (!state.liveTranscription[transcriptionKey]) {
                console.log('[Redux] Initializing new live transcription for session/VFO:', transcriptionKey);
                state.liveTranscription[transcriptionKey] = {
                    id: Date.now() + Math.random(),
                    segments: [{
                        text: trimmedText,
                        timestamp: Date.now(),
                    }],
                    timestamp: new Date().toISOString(),
                    startTime: new Date().toISOString(),
                    sessionId,
                    vfoNumber,
                    language: language || 'auto',
                };
            } else {
                console.log('[Redux] Appending to existing transcription. Adding segment:', trimmedText.length, 'chars');
                // Append new segment with timestamp
                state.liveTranscription[transcriptionKey].segments.push({
                    text: trimmedText,
                    timestamp: Date.now(),
                });
                state.liveTranscription[transcriptionKey].timestamp = new Date().toISOString();
                state.liveTranscription[transcriptionKey].language = language || state.liveTranscription[transcriptionKey].language;
            }

            console.log('[Redux] Live transcription updated. Total segments:', state.liveTranscription[transcriptionKey].segments.length);

            state.lastUpdated = new Date().toISOString();
            state.isActive = true;

            // Clean up old transcriptions (older than 5 minutes)
            const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
            Object.keys(state.liveTranscription).forEach(key => {
                const transcription = state.liveTranscription[key];
                const lastUpdate = new Date(transcription.timestamp).getTime();
                if (lastUpdate < fiveMinutesAgo && key !== transcriptionKey) {
                    console.log('[Redux] Removing old transcription for key:', key);
                    delete state.liveTranscription[key];
                }
            });
        },

        /**
         * Clear all transcription entries and live transcriptions
         * Or clear specific VFO if vfoNumber provided
         */
        clearTranscriptions: (state, action) => {
            const { vfoNumber } = action.payload || {};

            if (vfoNumber) {
                // Clear specific VFO
                Object.keys(state.liveTranscription).forEach(key => {
                    if (state.liveTranscription[key].vfoNumber === vfoNumber) {
                        delete state.liveTranscription[key];
                    }
                });
            } else {
                // Clear all
                state.entries = [];
                state.wordCount = 0;
                state.lastUpdated = null;
                state.isActive = false;
                state.liveTranscription = {}; // Clear all live transcriptions
            }
        },

        /**
         * Set transcription active state
         */
        setTranscriptionActive: (state, action) => {
            state.isActive = action.payload;
        },

        /**
         * Update max words limit
         */
        setMaxWords: (state, action) => {
            state.maxWords = action.payload;

            // Trim if necessary
            while (state.wordCount > state.maxWords && state.entries.length > 1) {
                const removed = state.entries.pop();
                const removedWords = removed.text.split(/\s+/).length;
                state.wordCount -= removedWords;
            }
        },

        /**
         * Remove specific entry by ID
         */
        removeTranscription: (state, action) => {
            const id = action.payload;
            const index = state.entries.findIndex(entry => entry.id === id);

            if (index !== -1) {
                const removed = state.entries.splice(index, 1)[0];
                const removedWords = removed.text.split(/\s+/).length;
                state.wordCount -= removedWords;
            }
        },

        /**
         * Clear transcriptions for a specific session
         */
        clearSessionTranscriptions: (state, action) => {
            const sessionId = action.payload;
            const remainingEntries = state.entries.filter(entry => entry.sessionId !== sessionId);

            // Recalculate word count
            state.wordCount = remainingEntries.reduce((count, entry) => {
                return count + entry.text.split(/\s+/).length;
            }, 0);

            state.entries = remainingEntries;

            if (state.entries.length === 0) {
                state.isActive = false;
                state.lastUpdated = null;
            }
        },

        /**
         * Increase subtitle font size for specific VFO
         */
        increaseFontSize: (state, action) => {
            const { vfoNumber } = action.payload;
            if (state.vfoFontSizes[vfoNumber]) {
                state.vfoFontSizes[vfoNumber] = Math.min(state.vfoFontSizes[vfoNumber] + 0.1, 2.0);
                localStorage.setItem(`transcription_font_size_vfo${vfoNumber}`, state.vfoFontSizes[vfoNumber].toString());
            }
        },

        /**
         * Decrease subtitle font size for specific VFO
         */
        decreaseFontSize: (state, action) => {
            const { vfoNumber } = action.payload;
            if (state.vfoFontSizes[vfoNumber]) {
                state.vfoFontSizes[vfoNumber] = Math.max(state.vfoFontSizes[vfoNumber] - 0.1, 0.5);
                localStorage.setItem(`transcription_font_size_vfo${vfoNumber}`, state.vfoFontSizes[vfoNumber].toString());
            }
        },

        /**
         * Set text alignment for specific VFO
         */
        setTextAlignment: (state, action) => {
            const { vfoNumber, alignment } = action.payload;
            if (state.vfoTextAlignments[vfoNumber] && ['left', 'center', 'right'].includes(alignment)) {
                state.vfoTextAlignments[vfoNumber] = alignment;
                localStorage.setItem(`transcription_text_alignment_vfo${vfoNumber}`, alignment);
            }
        },
    },
});

// Export actions
export const {
    addTranscription,
    clearTranscriptions,
    setTranscriptionActive,
    setMaxWords,
    removeTranscription,
    clearSessionTranscriptions,
    increaseFontSize,
    decreaseFontSize,
    setTextAlignment,
} = transcriptionSlice.actions;

// Selectors
export const selectTranscriptionEntries = (state) => state.transcription.entries;
export const selectTranscriptionWordCount = (state) => state.transcription.wordCount;
export const selectTranscriptionIsActive = (state) => state.transcription.isActive;
export const selectTranscriptionLastUpdated = (state) => state.transcription.lastUpdated;
export const selectTranscriptionMaxWords = (state) => state.transcription.maxWords;

// Get all transcriptions as a single continuous text (newest first)
export const selectTranscriptionText = (state) => {
    return state.transcription.entries.map(entry => entry.text).join(' ');
};

// Get transcriptions for a specific session
export const selectSessionTranscriptions = (sessionId) => (state) => {
    return state.transcription.entries.filter(entry => entry.sessionId === sessionId);
};

// Get recent transcriptions (last N entries)
export const selectRecentTranscriptions = (count) => (state) => {
    return state.transcription.entries.slice(0, count);
};

export default transcriptionSlice.reducer;
