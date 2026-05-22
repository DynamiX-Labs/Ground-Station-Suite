# Ground Station - Base Decoder Process
# Developed by Claude (Anthropic AI) for the Ground Station project
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
#
# Base class for multiprocessing-based decoders with shared memory monitoring.

import logging
import multiprocessing
import subprocess
import time
import uuid
from typing import Any, Dict

from demodulators.basedecoder import BaseDecoder

logger = logging.getLogger("basedecoderprocess")


class BaseDecoderProcess(BaseDecoder, multiprocessing.Process):
    """
    Base class for multiprocessing-based decoders.

    Combines BaseDecoder's packet processing logic with multiprocessing.Process
    for process isolation. Provides shared memory monitoring and restart signaling.

    Key differences from threading.Thread based decoders:
    - Runs in separate process (isolated memory space)
    - Uses multiprocessing.Lock instead of threading.Lock
    - Uses multiprocessing.Value for cross-process communication
    - Monitors GNU Radio shared memory segments
    - Can signal restart requests to parent process

    Subclasses must:
    - Call super().__init__() with all required parameters
    - Implement _get_decoder_type_for_init() returning decoder type string
    - Initialize stats in run() method (not __init__)
    - Initialize TelemetryParser and VFOManager in run() method (not __init__)
    """

    def __init__(
        self,
        iq_queue,
        data_queue,
        session_id,
        config,
        output_dir="data/decoded",
        vfo=None,
        shm_monitor_interval=10,
        shm_restart_threshold=200,
        **kwargs,
    ):
        """
        Initialize base decoder process.

        Args:
            iq_queue: Queue for receiving IQ or audio samples
            data_queue: Queue for sending decoded data/stats
            session_id: Unique session identifier
            config: DecoderConfig object with satellite/transmitter metadata
            output_dir: Directory for decoded output files
            vfo: VFO number (for multi-VFO mode)
            shm_monitor_interval: Seconds between SHM checks (default: 10)
            shm_restart_threshold: SHM segment count to trigger restart (default: 1000)
            **kwargs: Additional parameters for BaseDecoder
        """
        # Get decoder type from subclass for process naming
        decoder_type = self._get_decoder_type_for_init()

        # Generate unique decoder instance ID for tracking across restarts
        self.decoder_id = str(uuid.uuid4())

        # Initialize multiprocessing.Process
        multiprocessing.Process.__init__(
            self, daemon=False, name=f"{decoder_type}Decoder-{session_id}-VFO{vfo}"
        )

        # Store queue references (will work across process boundary)
        self.iq_queue = iq_queue
        self.data_queue = data_queue
        self.session_id = session_id
        self.config = config
        self.output_dir = output_dir
        self.vfo = vfo

        # Shared memory monitoring configuration
        self.shm_monitor_interval = shm_monitor_interval
        self.shm_restart_threshold = shm_restart_threshold
        self._last_shm_check = 0.0
        self._shm_segment_count = 0

        # Cross-process communication using multiprocessing.Value
        # These can be accessed from parent process
        self.running = multiprocessing.Value("i", 1)  # 1=running, 0=stop
        self.restart_requested = multiprocessing.Value("i", 0)  # 1=restart needed

        # Use multiprocessing.Lock for stats (not threading.Lock)
        self.stats_lock = multiprocessing.Lock()

        # Note: stats dict will be initialized in run() method (subprocess)
        # DO NOT initialize stats here - it won't be accessible across process boundary
        self.stats: Dict[str, Any] = {}

        # Extract metadata from config (these are simple types that pickle correctly)
        self.satellite = config.satellite if config else {}
        self.transmitter = config.transmitter if config else {}
        self.norad_id = self.satellite.get("norad_id") if self.satellite else None
        self.satellite_name = self.satellite.get("name", "Unknown") if self.satellite else "Unknown"
        self.transmitter_description = (
            self.transmitter.get("description", "") if self.transmitter else ""
        )
        self.transmitter_mode = self.transmitter.get("mode", "") if self.transmitter else ""

        # Extract downlink frequency (handle both low/high and single frequency)
        if self.transmitter:
            downlink_low = self.transmitter.get("downlink_low")
            downlink_high = self.transmitter.get("downlink_high")
            if downlink_low and downlink_high:
                self.transmitter_downlink_freq = (downlink_low + downlink_high) / 2
            elif downlink_low:
                self.transmitter_downlink_freq = downlink_low
            else:
                self.transmitter_downlink_freq = None
        else:
            self.transmitter_downlink_freq = None

        self.config_source = config.config_source if config else "unknown"
        self.framing = config.framing if config else "ax25"

        # Initialize packet counter
        self.packet_count = 0

        # Note: DO NOT initialize telemetry_parser or vfo_manager here
        # They must be initialized in run() method (in the subprocess)
        self.telemetry_parser = None
        self.vfo_manager = None

    def _get_decoder_type_for_init(self) -> str:
        """
        Get decoder type string for process naming.

        Subclasses must implement this to return their decoder type
        (e.g., "FSK", "BPSK", "AFSK", "LoRa").

        This is separate from _get_decoder_type() because it's called
        during __init__ before BaseDecoder is fully initialized.
        """
        raise NotImplementedError("Subclass must implement _get_decoder_type_for_init()")

    def _check_shared_memory(self) -> int:
        """
        Check current number of shared memory segments.

        Uses 'ipcs -m' to count active System V shared memory segments.
        GNU Radio creates these for circular buffers and doesn't always clean them up.

        Returns:
            int: Number of shared memory segments, or 0 if check fails
        """
        try:
            result = subprocess.run(["ipcs", "-m"], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                # Count lines starting with "0x" (shared memory segment IDs)
                lines = result.stdout.split("\n")
                segments = [line for line in lines if line.strip().startswith("0x")]
                count = len(segments)
                self._shm_segment_count = count
                return count
            else:
                logger.warning(f"ipcs command failed: {result.stderr}")
                return 0

        except subprocess.TimeoutExpired:
            logger.warning("ipcs command timed out")
            return 0
        except Exception as e:
            logger.warning(f"Error checking shared memory: {e}")
            return 0

    def _monitor_shared_memory(self):
        """
        Monitor shared memory usage and request restart if threshold exceeded.

        Call this periodically from run() loop (e.g., every 100 chunks).
        Checks SHM segments at configured interval and signals restart if needed.
        """

        current_time = time.time()

        # Check at configured interval
        if current_time - self._last_shm_check >= self.shm_monitor_interval:
            self._last_shm_check = current_time

            segment_count = self._check_shared_memory()

            # Only request restart if not already requested (prevent spam)
            if segment_count > self.shm_restart_threshold and self.restart_requested.value == 0:
                self.request_restart(
                    f"SHM segments exceeded threshold: {segment_count} > {self.shm_restart_threshold}"
                )
                logger.warning(
                    f"{self.name}: SHM segments ({segment_count}) exceeded threshold "
                    f"({self.shm_restart_threshold}), restart requested"
                )

    def get_shm_segment_count(self) -> int:
        """
        Get the most recent shared memory segment count.

        Returns the cached value from last _check_shared_memory() call.
        Call _check_shared_memory() directly for an updated count.

        Returns:
            int: Number of shared memory segments
        """
        return self._shm_segment_count

    def request_restart(self, reason: str = "unknown"):
        """
        Signal that this decoder needs to be restarted.

        Sets the restart flag, sends message to parent via data_queue, and stops the run loop.
        The parent process (ProcessLifecycleManager) will detect the message and restart immediately.

        Args:
            reason: Human-readable reason for restart request
        """
        logger.info(f"{self.name}: Restart requested - {reason}")
        self.restart_requested.value = 1

        # Send restart request message to parent via data_queue for immediate handling
        if hasattr(self, "data_queue") and self.data_queue:
            try:
                restart_msg = {
                    "type": "decoder-restart-request",
                    "session_id": self.session_id,
                    "vfo": self.vfo,  # Use self.vfo (set in __init__)
                    "reason": reason,
                    "shm_count": (
                        self._shm_segment_count if hasattr(self, "_shm_segment_count") else None
                    ),
                }
                self.data_queue.put_nowait(restart_msg)
                logger.debug(f"{self.name}: Sent restart request message to parent")
            except Exception as e:
                logger.warning(f"{self.name}: Failed to send restart request message: {e}")

        self.running.value = 0

    def should_restart(self) -> bool:
        """
        Check if decoder has requested restart.

        Can be called from parent process to check restart status.

        Returns:
            bool: True if restart was requested
        """
        return bool(self.restart_requested.value == 1)

    def stop(self):
        """
        Signal the decoder process to stop.

        Sets running flag to 0, which should cause run() loop to exit.
        """
        logger.info(f"{self.name}: Stop requested")
        self.running.value = 0

    def run(self):
        """
        Main process loop.

        Subclasses must override this and:
        1. Initialize telemetry_parser and vfo_manager IN THE SUBPROCESS
        2. Initialize stats dict IN THE SUBPROCESS
        3. Process samples in a loop checking self.running.value
        4. Call self._monitor_shared_memory() periodically
        5. Handle exceptions and cleanup
        """
        raise NotImplementedError("Subclass must implement run()")


__all__ = ["BaseDecoderProcess"]
