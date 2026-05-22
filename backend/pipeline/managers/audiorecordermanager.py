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

from common.audio_queue_config import get_audio_queue_config
from handlers.entities.filebrowser import emit_file_browser_state
from pipeline.managers.consumerbase import ConsumerManager


class AudioRecorderManager(ConsumerManager):
    """
    Manager for audio recorder consumers.
    Manages per-VFO audio recording threads.
    """

    def __init__(self, processes, sio=None):
        super().__init__(processes)
        self.logger = logging.getLogger("audio-recorder-manager")
        self.sio = sio  # Socket.IO instance for emitting notifications
        self.audio_cfg = get_audio_queue_config()

    def start_audio_recorder(self, sdr_id, session_id, vfo_number, recorder_class, **kwargs):
        """
        Start an audio recorder thread for a specific VFO.

        Args:
            sdr_id: Device identifier
            session_id: Session identifier (client session ID)
            vfo_number: VFO number (1-4)
            recorder_class: The recorder class to instantiate (AudioRecorder)
            **kwargs: Additional arguments (recording_path, sample_rate, etc.)

        Returns:
            bool: True if started successfully, False otherwise
        """
        if sdr_id not in self.processes:
            self.logger.warning(f"No SDR process found for device {sdr_id}")
            return False

        process_info = self.processes[sdr_id]

        # Get the AudioBroadcaster for this VFO
        # It's stored in: processes[sdr_id]["demodulators"][session_id][vfo_number]["audio_broadcaster"]
        demodulators = process_info.get("demodulators", {})
        session_demods = demodulators.get(session_id, {})
        demod_entry = session_demods.get(vfo_number)

        if not demod_entry:
            self.logger.error(f"No demodulator found for session {session_id} VFO {vfo_number}")
            return False

        audio_broadcaster = demod_entry.get("audio_broadcaster")
        if not audio_broadcaster:
            self.logger.error(
                f"No audio broadcaster found for session {session_id} VFO {vfo_number}"
            )
            return False

        # Create storage for audio recorders if needed
        if "audio_recorders" not in process_info:
            process_info["audio_recorders"] = {}
        if session_id not in process_info["audio_recorders"]:
            process_info["audio_recorders"][session_id] = {}

        audio_recorders = process_info["audio_recorders"][session_id]

        # Check if recorder already exists for this VFO
        if vfo_number in audio_recorders:
            self.logger.warning(
                f"Audio recorder already running for session {session_id} VFO {vfo_number}"
            )
            return False

        try:
            # Subscribe to the audio broadcaster to get a dedicated queue
            subscription_key = f"audio_recorder:{session_id}:vfo{vfo_number}"
            audio_queue = audio_broadcaster.subscribe(
                subscription_key, maxsize=self.audio_cfg.audio_recorder_queue_size
            )

            # Add vfo_number to kwargs
            kwargs["vfo_number"] = vfo_number

            # Create and start the audio recorder
            # audio_queue is the input, second param (unused) is for compatibility with base class
            recorder = recorder_class(audio_queue, None, session_id, **kwargs)
            recorder.start()

            # Store reference
            audio_recorders[vfo_number] = {
                "instance": recorder,
                "subscription_key": subscription_key,
                "recording_path": kwargs.get("recording_path", ""),
            }

            self.logger.info(f"Started AudioRecorder for session {session_id} VFO {vfo_number}")
            return True

        except Exception as e:
            self.logger.error(f"Error starting audio recorder: {str(e)}")
            self.logger.exception(e)
            return False

    def stop_audio_recorder(self, sdr_id, session_id, vfo_number):
        """
        Stop an audio recorder thread for a specific VFO.

        Args:
            sdr_id: Device identifier
            session_id: Session identifier
            vfo_number: VFO number

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        if sdr_id not in self.processes:
            return False

        process_info = self.processes[sdr_id]
        audio_recorders = process_info.get("audio_recorders", {}).get(session_id, {})

        if vfo_number not in audio_recorders:
            self.logger.warning(
                f"No audio recorder found for session {session_id} VFO {vfo_number}"
            )
            return False

        try:
            recorder_entry = audio_recorders[vfo_number]
            recorder = recorder_entry["instance"]
            subscription_key = recorder_entry["subscription_key"]
            recording_path = recorder_entry.get("recording_path", "")

            # Stop the recorder
            recorder.stop()
            recorder.join(timeout=2.0)

            # Unsubscribe from the audio broadcaster
            demodulators = process_info.get("demodulators", {})
            session_demods = demodulators.get(session_id, {})
            demod_entry = session_demods.get(vfo_number)

            if demod_entry:
                audio_broadcaster = demod_entry.get("audio_broadcaster")
                if audio_broadcaster:
                    audio_broadcaster.unsubscribe(subscription_key)

            # Remove from storage
            del audio_recorders[vfo_number]
            self.logger.info(f"Stopped AudioRecorder for session {session_id} VFO {vfo_number}")

            # Emit file browser state update to notify UI of new audio file
            if self.sio and recording_path:
                asyncio.create_task(self._emit_audio_stopped_notification(recording_path))

            return True

        except Exception as e:
            self.logger.error(f"Error stopping audio recorder: {str(e)}")
            self.logger.exception(e)
            return False

    async def _emit_audio_stopped_notification(self, recording_path):
        """
        Emit file browser state update for audio recording stopped.

        Args:
            recording_path: Path to the audio recording file (without extension)
        """
        try:
            await emit_file_browser_state(
                self.sio,
                {
                    "action": "audio-recording-stopped",
                    "recording_path": recording_path,
                },
                self.logger,
            )
        except Exception as e:
            self.logger.error(f"Error emitting audio-recording-stopped notification: {e}")

    def _stop_consumer(self, sdr_id, session_id, storage_key, vfo_number=None):
        """
        Implementation of base class method for stopping audio recorders.
        """
        if vfo_number is None:
            self.logger.error("vfo_number required for audio recorder")
            return False
        return self.stop_audio_recorder(sdr_id, session_id, vfo_number)

    def get_active_recorder(self, sdr_id, session_id, vfo_number):
        """
        Get the active audio recorder for a VFO.

        Args:
            sdr_id: Device identifier
            session_id: Session identifier
            vfo_number: VFO number

        Returns:
            Recorder instance or None if not found
        """
        if sdr_id not in self.processes:
            return None

        process_info = self.processes[sdr_id]
        audio_recorders = process_info.get("audio_recorders", {}).get(session_id, {})
        recorder_entry = audio_recorders.get(vfo_number)

        if recorder_entry is None:
            return None

        return recorder_entry.get("instance")

    def is_vfo_recording(self, sdr_id, session_id, vfo_number):
        """Check if a VFO is currently recording audio."""
        return self.get_active_recorder(sdr_id, session_id, vfo_number) is not None
