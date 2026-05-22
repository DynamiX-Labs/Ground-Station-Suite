"""Centralized audio queue and buffer sizing for low-latency tuning."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioQueueConfig:
    # Demodulator output buffering (chunks of 1024 samples per channel at 44.1kHz)
    demod_audio_internal_buffer_chunks: int = 7

    # Per-VFO AudioBroadcaster input queue (demodulator -> broadcaster)
    per_vfo_audio_broadcast_input_size: int = 6

    # Global web audio path queues
    global_audio_queue_size: int = 6
    web_audio_playback_queue_size: int = 6

    # AudioBroadcaster subscribers for non-playback audio consumers
    audio_decoder_queue_size: int = 10
    audio_recorder_queue_size: int = 20
    transcription_queue_size: int = 50


_AUDIO_QUEUE_CONFIG = AudioQueueConfig()


def get_audio_queue_config() -> AudioQueueConfig:
    """Return singleton audio queue sizing configuration."""
    return _AUDIO_QUEUE_CONFIG
