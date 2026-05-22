// Centralized frontend audio buffering constants (UI playback path)

export const AUDIO_WORKER_MAX_QUEUE_SIZE = 3;
export const AUDIO_WORKER_MAX_QUEUE_FOR_CATCHUP = 5;
export const AUDIO_WORKER_CATCHUP_RETAIN_CHUNKS = 2;

export const AUDIO_AUTO_FLUSH_MAX_BUFFER_SECONDS = 0.65;
export const AUDIO_AUTO_FLUSH_CHECK_INTERVAL_MS = 250;
