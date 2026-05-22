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
import queue as queue_module

from audio.audiobroadcaster import AudioBroadcaster
from common.audio_queue_config import get_audio_queue_config
from server import runtimestate


class ConsumerManager:
    """
    Base class for managing IQ consumers (demodulators, recorders, decoders)
    """

    # Maximum number of concurrent demodulators per session (one per active VFO)
    # Set to 10 to allow 4 VFOs + internal demodulators for decoders
    MAX_CONCURRENT_DEMODULATORS_PER_SESSION = 10

    def __init__(self, processes):
        """
        Initialize the consumer manager

        Args:
            processes: Reference to the main processes dictionary from ProcessManager
        """
        self.logger = logging.getLogger("consumer-manager")
        self.processes = processes
        self.audio_cfg = get_audio_queue_config()

    def _start_iq_consumer(
        self,
        sdr_id,
        session_id,
        consumer_class,
        audio_queue,
        storage_key,
        subscription_prefix,
        vfo_number=None,
        consumer_key_override=None,
        **kwargs,
    ):
        """
        Internal method to start an IQ consumer (demodulator or recorder).

        Args:
            sdr_id: Device identifier
            session_id: Session identifier (client session ID)
            consumer_class: The consumer class to instantiate
            audio_queue: Queue where audio will be placed (None for recorders)
            storage_key: "demodulators" or "recorders"
            subscription_prefix: "demod" or "recorder"
            vfo_number: VFO number for demodulators (1-4). If None, uses session_id as key
            **kwargs: Additional arguments to pass to the consumer constructor

        Returns:
            bool: True if started successfully, False otherwise
        """
        if sdr_id not in self.processes:
            self.logger.warning(f"No SDR process found for device {sdr_id}")
            return False

        process_info = self.processes[sdr_id]

        # Create storage key based on whether this is VFO-based or session-based
        # For demodulators with VFO number, store as nested dict: demodulators[session_id][vfo_number]
        # For recorders, store as: recorders[session_id]
        # - Demodulators: processes[sdr_id]["demodulators"][session_id][vfo_number] =
        #     {"instance", "subscription_key", "class_name"}
        # - Recorders:    processes[sdr_id]["recorders"][session_id] =
        #     {"instance", "subscription_key", "class_name"}

        if storage_key == "demodulators":
            if vfo_number is None:
                self.logger.error(f"vfo_number is required for demodulators (session {session_id})")
                return False

            # Multi-VFO mode: ensure session dict exists
            if session_id not in process_info.get(storage_key, {}):
                if storage_key not in process_info:
                    process_info[storage_key] = {}
                process_info[storage_key][session_id] = {}

            consumer_key = vfo_number
            consumer_storage = process_info[storage_key][session_id]

            # Check max demodulators limit
            if len(consumer_storage) >= self.MAX_CONCURRENT_DEMODULATORS_PER_SESSION:
                self.logger.warning(
                    f"Maximum demodulators ({self.MAX_CONCURRENT_DEMODULATORS_PER_SESSION}) reached for session {session_id}"
                )
                return False
        else:
            # Recorders: use session_id as key unless overridden
            consumer_key = consumer_key_override or session_id
            consumer_storage = process_info.get(storage_key, {})

        # Check if consumer already exists
        if consumer_key in consumer_storage:
            existing_entry = consumer_storage[consumer_key]
            existing = (
                existing_entry.get("instance")
                if isinstance(existing_entry, dict)
                else existing_entry
            )
            # If same type, check if it's in internal mode
            if isinstance(existing, consumer_class):
                # Check if existing is an internal demodulator (created by decoder)
                is_internal = getattr(existing, "internal_mode", False)
                # Check if we're requesting internal mode
                requesting_internal = kwargs.get("internal_mode", False)

                # If modes match (both internal or both normal), reuse existing
                if is_internal == requesting_internal:
                    log_msg = f"{consumer_class.__name__} already running for session {session_id}"
                    if vfo_number is not None:
                        log_msg += f" VFO {vfo_number}"
                    self.logger.debug(log_msg)
                    return True
                else:
                    # Different modes: stop the old one and start a new one
                    mode_desc = "internal" if is_internal else "normal"
                    new_mode_desc = "internal" if requesting_internal else "normal"
                    log_msg = f"Switching from {mode_desc} to {new_mode_desc} {consumer_class.__name__} for session {session_id}"
                    if vfo_number is not None:
                        log_msg += f" VFO {vfo_number}"
                    self.logger.info(log_msg)

                    # Stop using the appropriate method based on storage key
                    if storage_key == "recorders":
                        self._stop_consumer(sdr_id, session_id, storage_key)
                    else:
                        self._stop_consumer(sdr_id, session_id, storage_key, vfo_number)
            else:
                # Different type, stop the old one first
                log_msg = f"Switching from {type(existing).__name__} to {consumer_class.__name__} for session {session_id}"
                if vfo_number is not None:
                    log_msg += f" VFO {vfo_number}"
                self.logger.info(log_msg)
                # Stop using the appropriate method based on storage key
                if storage_key == "recorders":
                    self._stop_consumer(sdr_id, session_id, storage_key)
                else:
                    self._stop_consumer(sdr_id, session_id, storage_key, vfo_number)

        try:
            # Get the IQ broadcaster from the process info
            iq_broadcaster = process_info.get("iq_broadcaster")
            if not iq_broadcaster:
                self.logger.error(f"No IQ broadcaster found for device {sdr_id}")
                return False

            # Create a unique subscription key to prevent sharing queues
            if vfo_number is not None:
                subscription_key = f"{subscription_prefix}:{session_id}:vfo{vfo_number}"
            else:
                subscription_key = f"{subscription_prefix}:{session_id}"
                if consumer_key_override:
                    subscription_key = f"{subscription_key}:{consumer_key_override}"

            # Subscribe to the broadcaster to get a dedicated queue
            # Increased maxsize from 3 to 10 for better burst handling on slower CPUs (RPi5)
            subscriber_queue = iq_broadcaster.subscribe(
                subscription_key, maxsize=10, session_id_hint=session_id
            )

            # Add vfo_number to kwargs for multi-VFO support
            if vfo_number is not None:
                kwargs["vfo_number"] = vfo_number

            # For demodulators, create a per-VFO AudioBroadcaster
            # This allows multiple consumers (transcription, UI, etc.) to receive audio independently
            audio_broadcaster_instance = None
            if storage_key == "demodulators":
                # Create input queue for the audio broadcaster
                broadcaster_input_queue: queue_module.Queue = queue_module.Queue(
                    maxsize=self.audio_cfg.per_vfo_audio_broadcast_input_size
                )

                # Create and start the audio broadcaster
                audio_broadcaster_instance = AudioBroadcaster(
                    broadcaster_input_queue, session_id=session_id, vfo_number=vfo_number
                )
                audio_broadcaster_instance.start()

                # Subscribe the global audio_queue (used by WebAudioStreamer) to this broadcaster
                # This allows the browser to hear the audio from this VFO
                try:
                    global_audio_queue = runtimestate.audio_queue
                    if global_audio_queue:
                        # Subscribe the existing global audio_queue to this broadcaster
                        web_audio_key = f"web_audio:{session_id}:vfo{vfo_number}"
                        audio_broadcaster_instance.subscribe_existing_queue(
                            web_audio_key, global_audio_queue
                        )
                        self.logger.info(
                            f"Subscribed global audio_queue to audio broadcaster for session {session_id} VFO {vfo_number}"
                        )
                except Exception as e:
                    self.logger.warning(
                        f"Could not subscribe global audio_queue to audio broadcaster: {e}"
                    )

                # Use broadcaster's input queue as the demodulator's output queue
                audio_queue = broadcaster_input_queue

            # Create and start the consumer with the subscriber queue
            consumer = consumer_class(subscriber_queue, audio_queue, session_id, **kwargs)
            consumer.start()

            # Store reference along with subscription key for cleanup
            if storage_key not in process_info:
                process_info[storage_key] = {}

            if storage_key == "demodulators":
                # Multi-VFO mode: store in nested dict
                if session_id not in process_info[storage_key]:
                    process_info[storage_key][session_id] = {}
                process_info[storage_key][session_id][vfo_number] = {
                    "instance": consumer,
                    "subscription_key": subscription_key,
                    "class_name": consumer_class.__name__,
                    "audio_broadcaster": audio_broadcaster_instance,  # Store audio broadcaster for transcription
                }

                # Also store audio broadcaster in global broadcasters dict for easy lookup
                if audio_broadcaster_instance:
                    if "broadcasters" not in process_info:
                        process_info["broadcasters"] = {}
                    broadcaster_key = f"audio_{session_id}_vfo{vfo_number}"
                    process_info["broadcasters"][broadcaster_key] = audio_broadcaster_instance
            else:
                # Recorders: store directly under consumer_key
                process_info[storage_key][consumer_key] = {
                    "instance": consumer,
                    "subscription_key": subscription_key,
                    "class_name": consumer_class.__name__,
                }

            log_msg = (
                f"Started {consumer_class.__name__} for session {session_id} on device {sdr_id}"
            )
            if vfo_number is not None:
                log_msg += f" VFO {vfo_number}"
            self.logger.info(log_msg)
            return True

        except Exception as e:
            self.logger.error(f"Error starting {consumer_class.__name__}: {str(e)}")
            self.logger.exception(e)
            return False

    def _stop_consumer(self, sdr_id, session_id, storage_key, vfo_number=None):
        """
        Internal method to stop a consumer. Should be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _stop_consumer")

    def flush_all_demodulator_queues(self, sdr_id):
        """
        Flush all demodulator IQ queues for an SDR.

        This should be called when sample rate changes, since all buffered
        data at the old sample rate becomes invalid and would cause
        processing errors.

        Args:
            sdr_id: Device identifier
        """
        if sdr_id not in self.processes:
            return

        process_info = self.processes[sdr_id]
        broadcaster = process_info.get("iq_broadcaster")

        if broadcaster:
            broadcaster.flush_all_queues()
            self.logger.info(
                f"Flushed all demodulator queues for SDR {sdr_id} due to sample rate change"
            )
