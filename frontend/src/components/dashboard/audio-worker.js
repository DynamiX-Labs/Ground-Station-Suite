import {
    AUDIO_WORKER_CATCHUP_RETAIN_CHUNKS,
    AUDIO_WORKER_MAX_QUEUE_FOR_CATCHUP,
    AUDIO_WORKER_MAX_QUEUE_SIZE,
} from './audio-buffer-config.js';

class AudioProcessor {
    constructor() {
        this.audioQueue = [];
        this.processingQueue = false;
        this.maxQueueSize = AUDIO_WORKER_MAX_QUEUE_SIZE;
        // Track peak audio level (RMS) for VU meter
        this.currentAudioLevel = 0;
    }

    processAudioData(audioData) {
        try {
            const { samples, sample_rate, channels = 1, vfo } = audioData;

            if (!samples || samples.length === 0) {
                return null;
            }

            // Validate and normalize samples
            const normalizedSamples = new Float32Array(samples.length);
            let sumSquares = 0;
            for (let i = 0; i < samples.length; i++) {
                // Clamp values between -1 and 1
                normalizedSamples[i] = Math.max(-1, Math.min(1, samples[i]));
                sumSquares += normalizedSamples[i] * normalizedSamples[i];
            }

            // Calculate RMS (Root Mean Square) audio level
            const rms = Math.sqrt(sumSquares / samples.length);
            this.currentAudioLevel = rms;

            return {
                samples: normalizedSamples,
                sample_rate,
                channels,
                vfo_number: vfo?.vfo_number, // Preserve VFO number for routing
                duration: samples.length / sample_rate,
                timestamp: Date.now()
            };
        } catch (error) {
            self.postMessage({
                type: 'ERROR',
                error: error.message
            });
            return null;
        }
    }

    addToQueue(audioData) {
        const processedData = this.processAudioData(audioData);
        if (!processedData) return;

        this.audioQueue.push(processedData);

        // Limit queue size aggressively
        while (this.audioQueue.length > this.maxQueueSize) {
            this.audioQueue.shift(); // Remove oldest
        }

        this.scheduleProcessing();
    }

    scheduleProcessing() {
        if (this.processingQueue || this.audioQueue.length === 0) {
            return;
        }

        this.processingQueue = true;

        // Process immediately without delay for real-time audio
        this.processQueue();
    }

    processQueue() {
        // Catchup mode: if queue is too large, jump to live audio
        if (this.audioQueue.length > AUDIO_WORKER_MAX_QUEUE_FOR_CATCHUP) {
            // Drop everything except last 2 chunks to get back to live audio
            console.warn(`Audio queue overrun (${this.audioQueue.length} chunks), jumping to live audio`);
            this.audioQueue = this.audioQueue.slice(-AUDIO_WORKER_CATCHUP_RETAIN_CHUNKS);
        }

        // Process all available chunks at once for continuous audio
        const batch = [];

        while (this.audioQueue.length > 0) {
            const audioData = this.audioQueue.shift();
            if (audioData) {
                batch.push(audioData);
            }
        }

        if (batch.length > 0) {
            self.postMessage({
                type: 'AUDIO_BATCH',
                batch: batch
            });
        }

        this.processingQueue = false;
    }

    getQueueStatus() {
        return {
            queueLength: this.audioQueue.length,
            processing: this.processingQueue
        };
    }

    getAudioLevel() {
        return this.currentAudioLevel;
    }
}

const processor = new AudioProcessor();

self.onmessage = function(e) {
    const { type, data } = e.data;

    switch (type) {
        case 'AUDIO_DATA':
            processor.addToQueue(data);
            break;

        case 'GET_QUEUE_STATUS':
            self.postMessage({
                type: 'QUEUE_STATUS',
                status: processor.getQueueStatus()
            });
            break;

        case 'GET_AUDIO_LEVEL':
            self.postMessage({
                type: 'AUDIO_LEVEL',
                level: processor.getAudioLevel()
            });
            break;

        case 'CLEAR_QUEUE':
            processor.audioQueue = [];
            processor.processingQueue = false;
            break;

        default:
            console.warn('Unknown message type:', type);
    }
};
