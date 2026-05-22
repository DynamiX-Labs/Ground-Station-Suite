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

from pipeline.managers.consumerbase import ConsumerManager


class DemodulatorManager(ConsumerManager):
    """
    Manager for demodulator consumers
    """

    def __init__(self, processes):
        super().__init__(processes)
        self.logger = logging.getLogger("demodulator-manager")

    def start_demodulator(
        self, sdr_id, session_id, demodulator_class, audio_queue, vfo_number=None, **kwargs
    ):
        """
        Start a demodulator thread for a specific session and VFO.

        Args:
            sdr_id: Device identifier
            session_id: Session identifier (client session ID)
            demodulator_class: The demodulator class to instantiate (e.g., FMDemodulator, AMDemodulator, SSBDemodulator)
            audio_queue: Queue where demodulated audio will be placed
            vfo_number: VFO number (1-4). If None, uses session_id as key for backward compatibility
            **kwargs: Additional arguments to pass to the demodulator constructor

        Returns:
            bool: True if started successfully, False otherwise
        """
        return self._start_iq_consumer(
            sdr_id,
            session_id,
            demodulator_class,
            audio_queue,
            "demodulators",
            "demod",
            vfo_number=vfo_number,
            **kwargs,
        )

    def stop_demodulator(self, sdr_id, session_id, vfo_number=None):
        """
        Stop a demodulator thread for a specific session and VFO.

        Args:
            sdr_id: Device identifier
            session_id: Session identifier
            vfo_number: VFO number (1-4). If None, stops all demodulators for session

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        if sdr_id not in self.processes:
            return False

        process_info = self.processes[sdr_id]
        demodulators = process_info.get("demodulators", {})

        if session_id not in demodulators:
            return False

        try:
            demod_entry = demodulators[session_id]

            if vfo_number is not None:
                # Stop specific VFO
                if vfo_number not in demod_entry:
                    self.logger.warning(
                        f"No demodulator found for session {session_id} VFO {vfo_number}"
                    )
                    return False

                vfo_entry = demod_entry[vfo_number]
                demodulator = vfo_entry["instance"]
                subscription_key = vfo_entry["subscription_key"]
                audio_broadcaster = vfo_entry.get("audio_broadcaster")

                demod_name = type(demodulator).__name__
                demodulator.stop()
                demodulator.join(timeout=2.0)  # Wait up to 2 seconds

                # Stop audio broadcaster if it exists
                if audio_broadcaster:
                    # Unsubscribe global audio_queue from this broadcaster
                    web_audio_key = f"web_audio:{session_id}:vfo{vfo_number}"
                    try:
                        audio_broadcaster.unsubscribe(web_audio_key)
                        self.logger.info(
                            f"Unsubscribed global audio_queue from audio broadcaster for session {session_id} VFO {vfo_number}"
                        )
                    except Exception as e:
                        self.logger.debug(f"Could not unsubscribe global audio_queue: {e}")

                    audio_broadcaster.stop()
                    audio_broadcaster.join(timeout=2.0)
                    # Remove from broadcasters dict
                    broadcaster_key = f"audio_{session_id}_vfo{vfo_number}"
                    if (
                        "broadcasters" in process_info
                        and broadcaster_key in process_info["broadcasters"]
                    ):
                        del process_info["broadcasters"][broadcaster_key]
                    self.logger.info(
                        f"Stopped audio broadcaster for session {session_id} VFO {vfo_number}"
                    )

                # Unsubscribe from the IQ broadcaster
                iq_broadcaster = process_info.get("iq_broadcaster")
                if iq_broadcaster:
                    iq_broadcaster.unsubscribe(subscription_key)

                # Remove from storage
                del demod_entry[vfo_number]
                self.logger.info(f"Stopped {demod_name} for session {session_id} VFO {vfo_number}")

                # Clean up empty session dict
                if not demod_entry:
                    del demodulators[session_id]

                return True
            else:
                # Stop all VFOs for this session
                iq_broadcaster = process_info.get("iq_broadcaster")
                stopped_count = 0

                for vfo_num in list(demod_entry.keys()):
                    vfo_entry = demod_entry[vfo_num]
                    demodulator = vfo_entry["instance"]
                    subscription_key = vfo_entry["subscription_key"]
                    audio_broadcaster = vfo_entry.get("audio_broadcaster")

                    demod_name = type(demodulator).__name__
                    demodulator.stop()
                    demodulator.join(timeout=2.0)

                    # Stop audio broadcaster if it exists
                    if audio_broadcaster:
                        # Unsubscribe global audio_queue from this broadcaster
                        web_audio_key = f"web_audio:{session_id}:vfo{vfo_num}"
                        try:
                            audio_broadcaster.unsubscribe(web_audio_key)
                        except Exception as e:
                            self.logger.debug(f"Could not unsubscribe global audio_queue: {e}")

                        audio_broadcaster.stop()
                        audio_broadcaster.join(timeout=2.0)
                        # Remove from broadcasters dict
                        broadcaster_key = f"audio_{session_id}_vfo{vfo_num}"
                        if (
                            "broadcasters" in process_info
                            and broadcaster_key in process_info["broadcasters"]
                        ):
                            del process_info["broadcasters"][broadcaster_key]

                    if iq_broadcaster:
                        iq_broadcaster.unsubscribe(subscription_key)

                    stopped_count += 1
                    self.logger.info(f"Stopped {demod_name} for session {session_id} VFO {vfo_num}")

                del demodulators[session_id]
                self.logger.info(f"Stopped {stopped_count} demodulator(s) for session {session_id}")
                return True

        except Exception as e:
            self.logger.error(f"Error stopping demodulator: {str(e)}")
            return False

    def _stop_consumer(self, sdr_id, session_id, storage_key, vfo_number=None):
        """
        Implementation of base class method for stopping demodulators
        """
        return self.stop_demodulator(sdr_id, session_id, vfo_number)

    def get_active_demodulator(self, sdr_id, session_id, vfo_number=None):
        """
        Get the active demodulator for a session and VFO.

        Args:
            sdr_id: Device identifier
            session_id: Session identifier
            vfo_number: VFO number (1-4). If None, returns first available demodulator (legacy)

        Returns:
            Demodulator instance or None if not found
        """
        if sdr_id not in self.processes:
            return None

        process_info = self.processes[sdr_id]
        demodulators = process_info.get("demodulators", {})
        session_demods = demodulators.get(session_id)

        if session_demods is None:
            return None

        # Multi-VFO mode: session_demods is a dict of {vfo_number: demod_entry}
        if isinstance(session_demods, dict):
            # If vfo_number specified, get that specific VFO's demodulator
            if vfo_number is not None:
                demod_entry = session_demods.get(vfo_number)
                if demod_entry and isinstance(demod_entry, dict):
                    return demod_entry.get("instance")
                return None
            # Legacy: return first available demodulator
            else:
                for vfo_num, demod_entry in session_demods.items():
                    if isinstance(demod_entry, dict):
                        return demod_entry.get("instance")
                return None

        # Old format (shouldn't happen with new code, but handle it)
        return session_demods
