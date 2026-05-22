# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


import logging
import time
from typing import Any, Dict

import numpy as np
import psutil

from fft.averager import FFTAverager
from workers.common import window_functions

logger = logging.getLogger("fft-processor")


def fft_processor_process(iq_queue, data_queue, stop_event, client_id):
    """
    Separate process that consumes IQ data and produces FFT results.

    This decouples FFT computation from SDR acquisition, allowing the SDR worker
    to focus solely on reading samples without blocking.

    Args:
        iq_queue: Queue for receiving IQ samples from the SDR worker
        data_queue: Queue for sending FFT results back to the main process
        stop_event: Event to signal the process to stop
        client_id: Client identifier for this processing session
    """

    logger.info(f"FFT processor started for client {client_id}")

    # Configuration state
    fft_size = 16384
    fft_window = "hanning"
    fft_averaging = 6
    fft_overlap_percent = 50
    fft_overlap_depth = 16

    # Initialize FFT averager
    fft_averager = FFTAverager(logger, averaging_factor=fft_averaging)

    # Performance monitoring stats
    stats: Dict[str, Any] = {
        "iq_chunks_in": 0,
        "iq_samples_in": 0,
        "fft_results_out": 0,
        "queue_timeouts": 0,
        "last_activity": None,
        "errors": 0,
        "cpu_percent": 0.0,
        "memory_mb": 0.0,
        "memory_percent": 0.0,
    }
    last_stats_send = time.time()
    stats_send_interval = 1.0  # Send stats every second

    # CPU and memory monitoring
    process = psutil.Process()
    last_cpu_check = time.time()
    cpu_check_interval = 0.5  # Update CPU usage every 0.5 seconds

    try:
        while not stop_event.is_set():
            try:
                # Update CPU and memory usage periodically
                current_time = time.time()
                if current_time - last_cpu_check >= cpu_check_interval:
                    try:
                        cpu_percent = process.cpu_percent()

                        # Get memory usage
                        mem_info = process.memory_info()
                        memory_mb = mem_info.rss / (1024 * 1024)  # Convert bytes to MB
                        memory_percent = process.memory_percent()

                        stats["cpu_percent"] = cpu_percent
                        stats["memory_mb"] = memory_mb
                        stats["memory_percent"] = memory_percent
                        last_cpu_check = current_time
                    except Exception as e:
                        logger.debug(f"Error updating CPU/memory usage: {e}")

                # Get IQ data from queue with timeout
                # Message format: {'samples': ndarray, 'center_freq': float,
                #                  'sample_rate': float, 'timestamp': float, 'config': dict}
                # Using a short timeout allows checking stop_event frequently
                try:
                    iq_message = iq_queue.get(timeout=0.1)
                except Exception:
                    # Timeout or queue closed - check stop_event and continue
                    continue

                # Update stats
                stats["iq_chunks_in"] += 1
                stats["last_activity"] = time.time()

                # Handle configuration updates
                if "config" in iq_message:
                    config = iq_message["config"]

                    # Handle reset command (e.g., on sample rate change)
                    if config.get("reset_averager", False):
                        fft_averager.reset()
                        logger.info("FFT averager reset due to sample rate change")
                        continue  # Skip processing this empty message

                    if (
                        "fft_size" in config
                        and config["fft_size"] is not None
                        and config["fft_size"] != fft_size
                    ):
                        fft_size = config["fft_size"]
                        logger.info(f"Updated FFT size: {fft_size}")

                    if (
                        "fft_window" in config
                        and config["fft_window"] is not None
                        and config["fft_window"] != fft_window
                    ):
                        fft_window = config["fft_window"]
                        logger.info(f"Updated FFT window: {fft_window}")

                    if (
                        "fft_averaging" in config
                        and config["fft_averaging"] is not None
                        and config["fft_averaging"] != fft_averaging
                    ):
                        fft_averaging = config["fft_averaging"]
                        fft_averager.update_averaging_factor(fft_averaging)
                        logger.info(f"Updated FFT averaging: {fft_averaging}")

                    if (
                        "fft_overlap_percent" in config
                        and config["fft_overlap_percent"] is not None
                    ):
                        raw_percent = config["fft_overlap_percent"]
                        try:
                            next_percent = int(raw_percent)
                        except (TypeError, ValueError):
                            next_percent = fft_overlap_percent
                        next_percent = max(0, min(90, next_percent))
                        if next_percent != fft_overlap_percent:
                            fft_overlap_percent = next_percent
                            logger.info(f"Updated FFT overlap percent: {fft_overlap_percent}%")

                    if "fft_overlap_depth" in config and config["fft_overlap_depth"] is not None:
                        raw_depth = config["fft_overlap_depth"]
                        try:
                            next_depth = int(raw_depth)
                        except (TypeError, ValueError):
                            next_depth = fft_overlap_depth
                        next_depth = max(1, min(64, next_depth))
                        if next_depth != fft_overlap_depth:
                            fft_overlap_depth = next_depth
                            logger.info(f"Updated FFT overlap depth: {fft_overlap_depth}")

                # Extract samples
                samples = iq_message.get("samples")
                if samples is None or len(samples) == 0:
                    continue

                # Update sample count
                stats["iq_samples_in"] += len(samples)

                # Calculate the number of samples needed for the FFT
                actual_fft_size = fft_size

                # Apply window function
                window_func = window_functions.get(fft_window.lower(), np.hanning)
                window = window_func(actual_fft_size)

                # When UI FFT averaging is "None" (factor=1), avoid heavy hidden
                # intra-block smoothing. Still honor overlap so the toggle has
                # visible impact.
                if fft_averaging <= 1:
                    if len(samples) < actual_fft_size:
                        logger.debug(
                            f"Not enough samples for instantaneous FFT: {len(samples)} < {actual_fft_size}"
                        )
                        continue

                    N = actual_fft_size
                    window_correction = np.sum(window**2) / N
                    normalization = (N**2) * window_correction

                    overlap_enabled = fft_overlap_percent > 0
                    if overlap_enabled:
                        # Use a short trailing set of overlapped segments so overlap
                        # remains visually meaningful without reintroducing heavy smoothing.
                        overlap_step = max(
                            1, int(actual_fft_size * (1 - (fft_overlap_percent / 100.0)))
                        )
                        num_segments = 1 + max(0, (len(samples) - actual_fft_size) // overlap_step)
                        if num_segments <= 0:
                            logger.debug(
                                f"Not enough samples for instantaneous FFT with overlap: {len(samples)} < {actual_fft_size}"
                            )
                            continue

                        # Use user-selected depth of recent overlapped segments.
                        segments_to_use = min(num_segments, fft_overlap_depth)
                        start_segment = num_segments - segments_to_use

                        power_acc = np.zeros(actual_fft_size, dtype=np.float64)
                        for i in range(start_segment, num_segments):
                            start_idx = i * overlap_step
                            segment = samples[start_idx : start_idx + actual_fft_size]
                            windowed_segment = segment * window
                            fft_segment = np.fft.fftshift(np.fft.fft(windowed_segment))
                            power_acc += (np.abs(fft_segment) ** 2) / normalization

                        avg_power = power_acc / segments_to_use
                        fft_result = 10 * np.log10(avg_power + 1e-10)
                    else:
                        # No overlap: use only the most recent full segment.
                        start_idx = len(samples) - actual_fft_size
                        segment = samples[start_idx : start_idx + actual_fft_size]
                        windowed_segment = segment * window
                        fft_segment = np.fft.fftshift(np.fft.fft(windowed_segment))
                        fft_result = 10 * np.log10(
                            (np.abs(fft_segment) ** 2) / normalization + 1e-10
                        )
                else:
                    # Calculate FFT segments based on overlap setting
                    overlap_enabled = fft_overlap_percent > 0
                    if overlap_enabled:
                        overlap_step = max(
                            1, int(actual_fft_size * (1 - (fft_overlap_percent / 100.0)))
                        )
                        num_segments = 1 + max(0, (len(samples) - actual_fft_size) // overlap_step)
                    else:
                        # No overlap - use non-overlapping segments
                        overlap_step = actual_fft_size
                        num_segments = len(samples) // actual_fft_size

                    if num_segments <= 0:
                        overlap_type = (
                            f"with overlap ({fft_overlap_percent}%)"
                            if overlap_enabled
                            else "without overlap"
                        )
                        logger.debug(
                            f"Not enough samples for FFT {overlap_type}: {len(samples)} < {actual_fft_size}"
                        )
                        continue

                    fft_result = np.zeros(actual_fft_size)

                    for i in range(num_segments):
                        start_idx = i * overlap_step
                        segment = samples[start_idx : start_idx + actual_fft_size]

                        windowed_segment = segment * window

                        # Perform FFT
                        fft_segment = np.fft.fft(windowed_segment)

                        # Shift DC to center
                        fft_segment = np.fft.fftshift(fft_segment)

                        # Proper power normalization
                        N = len(fft_segment)
                        if overlap_enabled:
                            # Use simpler correction for overlapped FFTs
                            window_correction = 1.0
                        else:
                            # Use proper window correction for non-overlapped FFTs
                            window_correction = np.sum(window**2) / N

                        # FFT output magnitude scales with N; use N^2 to keep power levels
                        # normalized across FFT sizes.
                        normalization = (N**2) * window_correction
                        power = 10 * np.log10((np.abs(fft_segment) ** 2) / normalization + 1e-10)
                        fft_result += power

                    # Average the segments
                    if num_segments > 0:
                        fft_result /= num_segments

                # Convert to Float32 for efficiency in transmission
                fft_result = fft_result.astype(np.float32)

                # Add FFT to averager and send only when ready
                averaged_fft = fft_averager.add_fft(fft_result)
                if averaged_fft is not None:
                    # Update stats
                    stats["fft_results_out"] += 1

                    # Send the averaged result back to the main process
                    # Use non-blocking put with timeout to avoid hanging if main process stops
                    try:
                        fft_message = {
                            "type": "fft_data",
                            "client_id": client_id,
                            "data": averaged_fft.tobytes(),
                            "timestamp": time.time(),
                        }

                        # Pass through playback timing info if present (for playback mode)
                        if "recording_datetime" in iq_message:
                            fft_message["recording_datetime"] = iq_message["recording_datetime"]
                        if "playback_elapsed_seconds" in iq_message:
                            fft_message["playback_elapsed_seconds"] = iq_message[
                                "playback_elapsed_seconds"
                            ]
                        if "playback_remaining_seconds" in iq_message:
                            fft_message["playback_remaining_seconds"] = iq_message[
                                "playback_remaining_seconds"
                            ]
                        if "playback_total_seconds" in iq_message:
                            fft_message["playback_total_seconds"] = iq_message[
                                "playback_total_seconds"
                            ]

                        data_queue.put(fft_message, timeout=0.5)
                    except Exception as e:
                        # Queue full or closed - log and continue
                        # This prevents FFT processor from hanging if main process stops reading
                        logger.debug(f"Failed to send FFT data to queue: {e}")
                        stats["queue_timeouts"] += 1

                # Periodically send stats to main process
                current_time = time.time()
                if current_time - last_stats_send >= stats_send_interval:
                    try:
                        data_queue.put(
                            {
                                "type": "stats",
                                "client_id": client_id,
                                "stats": stats.copy(),
                                "timestamp": current_time,
                            },
                            timeout=0.5,
                        )
                        last_stats_send = current_time
                    except Exception as e:
                        # Queue full or closed - log and continue
                        logger.debug(f"Failed to send stats to queue: {e}")
                        stats["queue_timeouts"] += 1

            except Exception as e:
                if not stop_event.is_set():
                    logger.error(f"Error processing IQ data for FFT: {str(e)}")
                    logger.exception(e)
                    stats["errors"] += 1
                time.sleep(0.1)

    except Exception as e:
        logger.error(f"Fatal error in FFT processor: {str(e)}")
        logger.exception(e)
    finally:
        logger.info(f"FFT processor terminated for client {client_id}")
