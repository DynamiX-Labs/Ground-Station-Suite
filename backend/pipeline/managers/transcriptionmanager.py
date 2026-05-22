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

import asyncio
import logging
import threading
import time
from typing import Any, Dict, Optional

from audio.deepgramtranscriptionworker import DeepgramTranscriptionWorker
from audio.geminitranscriptionworker import GeminiTranscriptionWorker
from common.audio_queue_config import get_audio_queue_config
from handlers.entities.filebrowser import emit_file_browser_state


class TranscriptionManager:
    """
    Manager for per-VFO transcription workers.

    Each VFO can have its own transcription worker with independent:
    - Provider selection (Gemini, Deepgram, etc.)
    - API connection
    - Language settings
    - Translation settings
    - Audio queue subscription
    """

    def __init__(self, processes, sio, event_loop):
        """
        Initialize the transcription manager.

        Args:
            processes: Reference to the main processes dictionary from ProcessManager
            sio: Socket.IO server instance for emitting to frontend
            event_loop: Asyncio event loop
        """
        self.logger = logging.getLogger("transcription-manager")
        self.processes = processes
        self.sio = sio
        self.event_loop = event_loop
        self.audio_cfg = get_audio_queue_config()

        # API keys for different providers
        self.gemini_api_key = None
        self.deepgram_api_key = None
        self.google_translate_api_key = None

        # Race condition prevention (similar to decoder manager)
        self._start_locks = {}  # Per (sdr_id, session_id, vfo_number) locks
        self._start_in_progress = {}  # Track starts in progress
        self._last_start_ts = {}  # Timestamp of last start

    def set_gemini_api_key(self, api_key: str):
        """
        Update the Gemini API key for all future transcription workers.

        Args:
            api_key: Google Gemini API key
        """
        self.gemini_api_key = api_key
        self.logger.info("Gemini API key updated for transcription manager")

    def set_deepgram_api_key(self, api_key: str):
        """
        Update the Deepgram API key for all future transcription workers.

        Args:
            api_key: Deepgram API key
        """
        self.deepgram_api_key = api_key
        self.logger.info("Deepgram API key updated for transcription manager")

    def set_google_translate_api_key(self, api_key: str):
        """
        Update the Google Translate API key for all future transcription workers.

        Args:
            api_key: Google Cloud Translation API key
        """
        self.google_translate_api_key = api_key
        self.logger.info("Google Translate API key updated for transcription manager")

    def start_transcription(
        self,
        sdr_id: str,
        session_id: str,
        vfo_number: int,
        language: str = "auto",
        translate_to: str = "none",
        provider: str = "gemini",
        satellite: Optional[Dict[str, Any]] = None,
        transmitter: Optional[Dict[str, Any]] = None,
    ):
        """
        Start a transcription worker for a specific VFO.

        Args:
            sdr_id: Device identifier
            session_id: Session identifier (client session ID)
            vfo_number: VFO number (1-4)
            language: Source language code (e.g., "en", "es", "auto")
            translate_to: Target language code for translation (e.g., "en", "none")
            provider: Transcription provider ("gemini", "deepgram")
            satellite: Satellite information dict (optional)
            transmitter: Transmitter information dict (optional)

        Returns:
            bool: True if started successfully, False otherwise
        """
        if sdr_id not in self.processes:
            self.logger.warning(f"No SDR process found for device {sdr_id}")
            return False

        # Get API key for the selected provider
        if provider == "gemini":
            api_key = self.gemini_api_key
            if not api_key:
                self.logger.warning("No Gemini API key configured, cannot start transcription")
                return False
        elif provider == "deepgram":
            api_key = self.deepgram_api_key
            if not api_key:
                self.logger.warning("No Deepgram API key configured, cannot start transcription")
                return False
        else:
            self.logger.error(f"Unknown transcription provider: {provider}")
            return False

        process_info = self.processes[sdr_id]

        # Find per-VFO audio broadcaster created by the demodulator
        # Each demodulator now creates its own AudioBroadcaster regardless of whether it has a decoder
        broadcasters = process_info.get("broadcasters", {})
        audio_broadcaster = None

        # Look for broadcaster by key pattern: audio_{session_id}_vfo{vfo_number}
        broadcaster_key = f"audio_{session_id}_vfo{vfo_number}"
        audio_broadcaster = broadcasters.get(broadcaster_key)

        if not audio_broadcaster:
            self.logger.warning(
                f"No audio broadcaster found for session {session_id} VFO {vfo_number}. "
                f"Transcription requires an active demodulator."
            )
            return False

        # Initialize transcription_consumers storage if it doesn't exist
        if "transcription_consumers" not in process_info:
            process_info["transcription_consumers"] = {}

        if session_id not in process_info["transcription_consumers"]:
            process_info["transcription_consumers"][session_id] = {}

        consumer_storage = process_info["transcription_consumers"][session_id]

        # Race condition prevention: Use a lock per (sdr_id, session_id, vfo_number)
        lock_key = (sdr_id, session_id, vfo_number)
        lock = self._start_locks.get(lock_key)
        if lock is None:
            lock = threading.Lock()
            self._start_locks[lock_key] = lock

        with lock:
            # Debounce: Check if a start is already in progress or happened recently
            key = (sdr_id, session_id, vfo_number)
            now_ms = int(time.time() * 1000)
            in_progress = bool(self._start_in_progress.get(key, False))
            last_ts = int(self._last_start_ts.get(key, 0))

            # If a start is in progress, reject
            if in_progress:
                self.logger.info(
                    f"Transcription start already in progress for {session_id} VFO {vfo_number}, skipping duplicate request"
                )
                return False

            # If a start happened within last 1000ms, debounce
            if now_ms - last_ts < 1000:
                self.logger.info(
                    f"Transcription start requested too soon after last start for {session_id} VFO {vfo_number}, debouncing"
                )
                return False

            # Mark start in progress
            self._start_in_progress[key] = True

            try:
                # Check if transcription worker already exists for this VFO
                if vfo_number in consumer_storage:
                    existing = consumer_storage[vfo_number]
                    if existing["instance"].is_alive():
                        # Check if settings changed - if so, restart the worker
                        settings_changed = (
                            existing.get("language") != language
                            or existing.get("translate_to") != translate_to
                            or existing.get("provider") != provider
                        )
                        if settings_changed:
                            self.logger.info(
                                f"Transcription settings changed for session {session_id} VFO {vfo_number}, "
                                f"restarting worker (old: provider={existing.get('provider')}, "
                                f"language={existing.get('language')}, translate_to={existing.get('translate_to')} -> "
                                f"new: provider={provider}, language={language}, translate_to={translate_to})"
                            )
                            # Stop the existing worker
                            self._stop_consumer_entry(existing, session_id, vfo_number)
                            del consumer_storage[vfo_number]
                            # Continue to start new worker with updated settings
                        else:
                            self.logger.debug(
                                f"Transcription worker already running for session {session_id} VFO {vfo_number} "
                                f"with same settings"
                            )
                            return True
                    else:
                        # Clean up dead worker
                        self.logger.info(
                            f"Cleaning up dead transcription worker for session {session_id} VFO {vfo_number}"
                        )
                        self._cleanup_consumer(existing)
                        del consumer_storage[vfo_number]

                # Subscribe to the audio broadcaster
                subscription_key = f"transcription:{session_id}_vfo{vfo_number}"
                transcription_queue = audio_broadcaster.subscribe(
                    subscription_key, maxsize=self.audio_cfg.transcription_queue_size
                )

                # Create the appropriate worker based on provider
                try:
                    if provider == "gemini":
                        transcription_worker = GeminiTranscriptionWorker(
                            transcription_queue=transcription_queue,
                            sio=self.sio,
                            loop=self.event_loop,
                            api_key=api_key,
                            session_id=session_id,
                            vfo_number=vfo_number,
                            language=language,
                            translate_to=translate_to,
                            satellite=satellite,
                            transmitter=transmitter,
                        )
                    elif provider == "deepgram":
                        transcription_worker = DeepgramTranscriptionWorker(
                            transcription_queue=transcription_queue,
                            sio=self.sio,
                            loop=self.event_loop,
                            api_key=api_key,
                            session_id=session_id,
                            vfo_number=vfo_number,
                            language=language,
                            translate_to=translate_to,
                            google_translate_api_key=self.google_translate_api_key,
                            satellite=satellite,
                            transmitter=transmitter,
                        )
                    else:
                        raise ValueError(f"Unknown provider: {provider}")

                    transcription_worker.start()

                    # Store the worker info
                    consumer_storage[vfo_number] = {
                        "instance": transcription_worker,
                        "subscription_key": subscription_key,
                        "audio_broadcaster": audio_broadcaster,
                        "language": language,
                        "translate_to": translate_to,
                        "provider": provider,
                        "satellite": satellite,
                        "transmitter": transmitter,
                    }

                    self.logger.info(
                        f"Started {provider} transcription worker for session {session_id} VFO {vfo_number} "
                        f"(language={language}, translate_to={translate_to})"
                    )

                    # Emit file browser state update to notify UI that transcription started
                    if self.sio:
                        asyncio.run_coroutine_threadsafe(
                            self._emit_transcription_started_notification(),
                            self.event_loop,
                        )

                    # Update timestamp
                    self._last_start_ts[key] = now_ms
                    return True

                except Exception as e:
                    self.logger.error(f"Failed to start transcription worker: {e}", exc_info=True)
                    # Clean up subscription if worker creation failed
                    if audio_broadcaster:
                        audio_broadcaster.unsubscribe(subscription_key)
                    return False
            finally:
                # Clear in-progress flag
                self._start_in_progress[key] = False

    def stop_transcription(self, sdr_id: str, session_id: str, vfo_number: Optional[int] = None):
        """
        Stop transcription worker(s) for a session.

        Args:
            sdr_id: Device identifier
            session_id: Session identifier
            vfo_number: VFO number (1-4). If None, stops all transcription workers for session

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        if sdr_id not in self.processes:
            return False

        process_info = self.processes[sdr_id]
        transcription_consumers = process_info.get("transcription_consumers", {})

        if session_id not in transcription_consumers:
            return False

        try:
            consumer_storage = transcription_consumers[session_id]

            if vfo_number is not None:
                # Stop specific VFO
                if vfo_number not in consumer_storage:
                    self.logger.warning(
                        f"No transcription worker found for session {session_id} VFO {vfo_number}"
                    )
                    return False

                consumer_entry = consumer_storage[vfo_number]
                self._stop_consumer_entry(consumer_entry, session_id, vfo_number)
                del consumer_storage[vfo_number]

                # Clean up empty session dict
                if not consumer_storage:
                    del transcription_consumers[session_id]

                return True
            else:
                # Stop all VFOs for this session
                stopped_count = 0
                for vfo_num in list(consumer_storage.keys()):
                    consumer_entry = consumer_storage[vfo_num]
                    self._stop_consumer_entry(consumer_entry, session_id, vfo_num)
                    stopped_count += 1

                del transcription_consumers[session_id]
                self.logger.info(
                    f"Stopped {stopped_count} transcription worker(s) for session {session_id}"
                )
                return True

        except Exception as e:
            self.logger.error(f"Error stopping transcription worker: {e}", exc_info=True)
            return False

    def _stop_consumer_entry(self, consumer_entry: dict, session_id: str, vfo_number: int):
        """
        Stop a single transcription worker entry.

        Args:
            consumer_entry: Worker entry dict with instance, subscription_key, etc.
            session_id: Session identifier
            vfo_number: VFO number
        """
        worker = consumer_entry["instance"]
        subscription_key = consumer_entry["subscription_key"]
        audio_broadcaster = consumer_entry.get("audio_broadcaster")
        provider = consumer_entry.get("provider", "unknown")

        # Get transcription file path before stopping (if available)
        transcription_file_path = getattr(worker, "transcription_file_path", None)

        # Stop the worker thread (non-blocking)
        worker.stop()
        # Don't join - let it stop asynchronously to avoid blocking

        # Unsubscribe from audio broadcaster
        if audio_broadcaster:
            try:
                audio_broadcaster.unsubscribe(subscription_key)
            except Exception as e:
                self.logger.warning(f"Failed to unsubscribe from audio broadcaster: {e}")

        self.logger.info(
            f"Stopped {provider} transcription worker for session {session_id} VFO {vfo_number}"
        )

        # Emit file browser state update to notify UI of new transcription file
        if self.sio and transcription_file_path:
            asyncio.run_coroutine_threadsafe(
                self._emit_transcription_stopped_notification(transcription_file_path),
                self.event_loop,
            )

    async def _emit_transcription_started_notification(self):
        """
        Emit file browser state update for transcription started.
        """
        try:
            await emit_file_browser_state(
                self.sio,
                {
                    "action": "transcription-started",
                },
                self.logger,
            )
        except Exception as e:
            self.logger.error(f"Error emitting transcription-started notification: {e}")

    async def _emit_transcription_stopped_notification(self, transcription_file_path):
        """
        Emit file browser state update for transcription stopped.

        Args:
            transcription_file_path: Path to the transcription file
        """
        try:
            await emit_file_browser_state(
                self.sio,
                {
                    "action": "transcription-stopped",
                    "transcription_file_path": transcription_file_path,
                },
                self.logger,
            )
        except Exception as e:
            self.logger.error(f"Error emitting transcription-stopped notification: {e}")

    def _cleanup_consumer(self, consumer_entry: dict):
        """
        Clean up a worker entry (for dead/stale workers).

        Args:
            consumer_entry: Worker entry dict
        """
        try:
            worker = consumer_entry["instance"]
            if worker.is_alive():
                worker.stop()
                # Don't join - let it stop asynchronously

            subscription_key = consumer_entry.get("subscription_key")
            audio_broadcaster = consumer_entry.get("audio_broadcaster")
            if audio_broadcaster and subscription_key:
                audio_broadcaster.unsubscribe(subscription_key)
        except Exception as e:
            self.logger.warning(f"Error during worker cleanup: {e}")

    def get_active_transcription_consumer(self, sdr_id: str, session_id: str, vfo_number: int):
        """
        Get the active transcription worker for a session/VFO.

        Args:
            sdr_id: Device identifier
            session_id: Session identifier
            vfo_number: VFO number (1-4)

        Returns:
            TranscriptionWorker instance or None
        """
        if sdr_id not in self.processes:
            return None

        process_info = self.processes[sdr_id]
        transcription_consumers = process_info.get("transcription_consumers", {})

        if session_id not in transcription_consumers:
            return None

        consumer_storage = transcription_consumers[session_id]
        if vfo_number not in consumer_storage:
            return None

        return consumer_storage[vfo_number].get("instance")

    def stop_all_for_session(self, session_id: str):
        """
        Stop all transcription workers for a session across all SDRs.

        Args:
            session_id: Session identifier
        """
        for sdr_id in list(self.processes.keys()):
            self.stop_transcription(sdr_id, session_id)
