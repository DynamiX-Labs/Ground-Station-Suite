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
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

from common.arguments import arguments as args
from vfos.state import VFOManager


class SDRController:
    """
    Controller for SDR (Software-Defined Radio) devices used in satellite tracking.

    IMPORTANT ARCHITECTURAL NOTE:
    This controller is a STUB/PLACEHOLDER and does NOT control SDR center frequency during tracking.

    Why SDRs are different from hardware rigs:
    - Hardware rigs (righamlib.py, rig.py): Physically tune VFO1/VFO2 to doppler-corrected frequencies
    - SDRs: User manually sets center frequency ONCE, then VFO software windows are updated

    How SDR tracking works:
    1. User manually sets SDR center frequency from UI (e.g., 437.000 MHz)
    2. SDR streams I/Q data continuously at that fixed center frequency
    3. When tracking, only the VFO overlay markers are updated with doppler shifts
    4. VFO updates happen in main process via handle_vfo_updates_for_tracking() in vfos/updates.py
    5. Multiple sessions can track different transmitters on the same SDR stream

    This controller exists for:
    - Type compatibility with RigController/HamlibController interfaces
    - Future SDR control features (gain, sample rate, antenna switching)
    - VFO manager integration (update_vfo_with_doppler method)

    If you want to add SDR control features:
    - Gain control: Add methods to communicate with process_manager
    - Sample rate changes: Use process_manager.update_configuration()
    - Antenna switching: Add hamlib-style commands for SDRs that support it
    - Don't add center frequency updates during tracking (breaks multi-session tracking)

    Related files:
    - backend/vfos/updates.py:handle_vfo_updates_for_tracking() - Where VFO doppler updates happen
    - backend/sdr/processmanager.py - Manages SDR worker processes
    - backend/tracker/logic.py:_control_rig_frequency() - Distinguishes SDR vs hardware rig behavior
    - backend/session/tracker.py - Tracks which sessions are using which SDRs/VFOs
    """

    def __init__(
        self,
        sdr_details: Optional[Dict[str, Any]] = None,
        verbose: bool = False,
        timeout: float = 3.0,
    ):

        assert sdr_details is not None, "SDR details must be provided"
        assert isinstance(sdr_details, dict), "SDR details must be a dictionary"

        # Set up logging
        self.logger: logging.Logger = logging.getLogger("sdr-controller")
        self.logger.setLevel(args.log_level)

        # Initialize attributes
        self.verbose: bool = verbose
        self.connected: bool = False
        self.timeout: float = timeout

        # Setup init values from SDR details
        self.sdr_details: Dict[str, Any] = sdr_details
        self.sdr_id: Any = sdr_details["id"]
        self.sdr_name: Any = sdr_details["name"]
        self.sdr_type: Any = sdr_details["type"]
        self.sdr_serial: Any = sdr_details["serial"]
        self.sdr_host: Any = sdr_details["host"]
        self.sdr_port: Any = sdr_details["port"]
        self.sdr_driver: Any = sdr_details["driver"]
        self.frequency_range: Dict[str, Any] = {
            "min": sdr_details["frequency_min"],
            "max": sdr_details["frequency_max"],
        }

        # VFO management (session-specific)
        self.vfo_manager: VFOManager = VFOManager()

        self.logger.info(f"Initialized SDRController for SDR with id {self.sdr_id}")

    async def connect(self) -> bool:
        """Connect to the SDR device.

        Returns:
            bool: True if connected successfully, False otherwise
        """
        if self.connected:
            self.logger.warning("Already connected to SDR")
            return True

        try:
            # TODO: Implement SDR connection logic here

            self.logger.debug("Connecting to SDR")

            # Placeholder for connection implementation

            self.connected = True
            self.logger.info("Successfully connected to SDR")
            return True

        except Exception as e:
            self.logger.error(f"Error connecting to SDR: {e}")
            raise RuntimeError(f"Error connecting to SDR: {e}")

    async def disconnect(self) -> bool:
        """Disconnect from the SDR device.

        Returns:
            bool: True if disconnected successfully
        """
        if not self.connected:
            self.logger.warning("Not connected to SDR")
            return True

        try:
            # TODO: Implement SDR disconnection logic here

            self.connected = False
            self.logger.info("Disconnected from SDR")
            return True

        except Exception as e:
            self.logger.error(f"Error disconnecting from SDR: {e}")
            return False

    async def ping(self) -> bool:
        """Check if the SDR is responsive.

        Returns:
            bool: True if SDR responds, False otherwise
        """
        try:
            # TODO: Implement ping/check logic for the SDR

            # Placeholder for ping implementation
            return True

        except Exception as e:
            # Catch all exceptions during ping
            self.logger.exception(e)
            return False

    def check_connection(self) -> bool:
        """Check if connected to the SDR.

        Returns:
            bool: True if connected

        Raises:
            RuntimeError: If not connected
        """
        if not self.connected:
            error_msg = f"Not connected to SDR (connected: {self.connected})"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        return True

    async def get_frequency(self) -> float:
        """Get the current frequency of the SDR.

        Returns:
            float: Current frequency in Hz
        """
        self.check_connection()

        try:
            # TODO: Implement get frequency logic for the SDR

            # Placeholder: return a dummy frequency
            return 100000000.0  # 100 MHz

        except Exception as e:
            self.logger.error(f"Error getting frequency: {e}")
            raise RuntimeError(f"Error getting frequency: {e}")

    async def set_frequency(
        self, target_freq: float, update_interval: float = 0.5, freq_tolerance: float = 10.0
    ) -> AsyncGenerator[Tuple[float, bool], None]:
        """Set the SDR frequency and yield updates until it reaches the target.

        Args:
            target_freq: Target frequency in Hz
            update_interval: Time between updates in seconds
            freq_tolerance: Frequency tolerance in Hz

        Yields:
            Tuple[float, bool]: Current frequency and whether still tuning
        """
        self.check_connection()
        self.logger.debug(f"Setting SDR frequency to {target_freq} Hz")

        try:
            # TODO: Implement set frequency logic for the SDR

            # Initial status (placeholder)
            current_freq = target_freq  # Assume immediate tuning in this stub
            is_tuning = False

            # First yield with initial frequency
            yield current_freq, is_tuning

        except Exception as e:
            self.logger.error(f"Error setting SDR frequency: {e}")
            self.logger.exception(e)
            raise RuntimeError(f"Error setting SDR frequency: {e}")

    async def get_mode(self) -> Tuple[str, int]:
        """Get the current mode and bandwidth.

        Returns:
            Tuple[str, int]: Mode name and bandwidth in Hz
        """
        self.check_connection()

        try:
            # TODO: Implement get mode logic for the SDR

            # Placeholder: return dummy mode and bandwidth
            mode = "AM"
            bandwidth = 6000
            self.logger.debug(f"Current mode: {mode}, bandwidth: {bandwidth} Hz")
            return mode, bandwidth

        except Exception as e:
            self.logger.error(f"Error getting mode: {e}")
            raise RuntimeError(f"Error getting mode: {e}")

    async def set_mode(self, mode: str, bandwidth: int = 0) -> bool:
        """Set the SDR mode and bandwidth.

        Args:
            mode: Demodulation mode (AM, FM, etc.)
            bandwidth: Filter bandwidth in Hz

        Returns:
            bool: True if successful
        """
        self.check_connection()

        try:
            self.logger.info(f"Setting SDR mode to {mode}, bandwidth={bandwidth} Hz")

            # TODO: Implement set mode logic for the SDR

            return True

        except Exception as e:
            self.logger.error(f"Error setting SDR mode: {e}")
            self.logger.exception(e)
            raise RuntimeError(f"Error setting SDR mode: {e}")

    def __del__(self) -> None:
        """Destructor - ensure we disconnect when the object is garbage collected."""
        if hasattr(self, "connected") and self.connected:
            # Just log a warning
            if hasattr(self, "logger"):
                self.logger.warning(
                    "Object SDRController being destroyed while still connected to SDR"
                )

    async def update_vfo_with_doppler(
        self,
        sio,
        session_id: str,
        vfo_id: str,
        downlink_observed_freq: float,
        doppler_shift: float,
        original_freq: float,
        bandwidth: Optional[int] = None,
        modulation: Optional[str] = None,
    ) -> None:
        """Update a specific VFO for a session with doppler-corrected frequency.

        Args:
            sio: Socket.IO server instance for emitting updates
            session_id: Session ID to update
            vfo_id: VFO number ("1", "2", "3", or "4")
            downlink_observed_freq: Doppler-corrected downlink frequency
            doppler_shift: Doppler shift value
            original_freq: Original transmitted frequency
            bandwidth: Optional bandwidth to set
            modulation: Optional modulation to set
        """
        try:
            # Convert vfo_id string to int for VFOManager
            vfo_number = int(vfo_id) if vfo_id != "none" else None

            if vfo_number is None:
                self.logger.debug(f"Skipping VFO update for session {session_id} - no VFO selected")
                return

            # Update VFO state in the manager
            self.vfo_manager.update_vfo_state(
                session_id=session_id,
                vfo_id=vfo_number,
                center_freq=int(downlink_observed_freq),
                bandwidth=bandwidth,
                modulation=modulation,
                active=True,
            )

            # Emit updated VFO states to the session
            await self.vfo_manager.emit_vfo_states(sio, session_id)

            self.logger.debug(
                f"Updated VFO {vfo_id} for session {session_id}: "
                f"freq={downlink_observed_freq:.0f} Hz, doppler={doppler_shift:.0f} Hz"
            )

        except Exception as e:
            self.logger.error(f"Error updating VFO for session {session_id}: {e}")
            self.logger.exception(e)

    def get_vfo_manager(self) -> VFOManager:
        """Get the VFO manager instance.

        Returns:
            VFOManager: The VFO manager for this SDR controller
        """
        return self.vfo_manager

    @staticmethod
    def get_error_message(error_code: int) -> str:
        """Map error codes to messages.

        Args:
            error_code: Error code to translate

        Returns:
            str: Human-readable error message
        """
        error_messages = {
            0: "No error",
            -1: "Invalid parameter",
            -2: "Invalid configuration",
            -3: "Memory shortage",
            -4: "Function not implemented",
            -5: "Communication timed out",
            -6: "IO error",
            -7: "Internal error",
            -8: "Protocol error",
            -9: "Command rejected",
            -10: "String truncated",
            -11: "Function not available",
            -12: "Target not available",
            -13: "Device error",
            -14: "Device busy",
            -15: "Invalid argument",
            -16: "Invalid device",
            -17: "Argument out of domain",
        }

        return error_messages.get(error_code, f"Unknown error code: {error_code}")
