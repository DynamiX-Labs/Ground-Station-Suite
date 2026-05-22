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
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator, Tuple

from Hamlib import Hamlib

from common.arguments import arguments as args

if TYPE_CHECKING:
    from Hamlib import Rig  # noqa: F401


class RigController:
    def __init__(
        self,
        model: int = Hamlib.RIG_MODEL_NETRIGCTL,
        host: str = "127.0.0.1",
        port: int = 4532,
        verbose: bool = False,
        timeout: float = 5.0,
    ):

        # Set up logging
        device_path = f"{host}:{port}"
        self.logger = logging.getLogger("rig-control")
        self.logger.setLevel(args.log_level)
        self.logger.info(f"Initializing RigController with model={model}, device={device_path}")

        # Initialize Hamlib
        Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_NONE)
        if verbose:
            Hamlib.rig_set_debug(Hamlib.RIG_DEBUG_VERBOSE)

        # Initialize attributes
        self.host = host
        self.port = port
        self.model = model
        self.device_path = device_path
        self.verbose = verbose
        self.rig: Any = None
        self.connected = False
        self.timeout = timeout

    async def connect(self) -> bool:

        if self.connected:
            self.logger.warning("Already connected to rig")
            return True

        try:
            # first we ping the rig
            pingcheck = await self.ping()
            assert pingcheck, "Rig did not respond to ping"

            self.logger.debug(f"Connecting to rig at {self.device_path}")
            self.rig = Hamlib.Rig(self.model)
            self.rig.set_conf("rig_pathname", self.device_path)

            # Set timeout
            self.rig.set_conf("timeout", str(int(self.timeout * 1000)))  # Convert to ms

            # Initialize the rig (opens the connection)
            self.rig.open()

            self.connected = True
            self.logger.info(f"Successfully connected to rig at {self.device_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error connecting to rig: {e}")
            raise RuntimeError(f"Error connecting to rig: {e}")

    async def disconnect(self) -> bool:

        if not self.connected or self.rig is None:
            self.logger.warning("Not connected to rig")
            return True

        try:
            close_task = asyncio.create_task(asyncio.to_thread(self.rig.close))

            # Wait with timeout
            await asyncio.wait_for(close_task, timeout=3.0)
            self.logger.info("Rig disconnected successfully")
            return True

        except asyncio.TimeoutError:
            self.logger.info("Rig disconnect operation is taking longer than expected")

            self.connected = False
            self.rig = None
            self.logger.info("Disconnected from rig")
            return True

        except Exception as e:
            self.logger.error(f"Error disconnecting from rig: {e}")
            return False

    async def close_rig(self):
        with ProcessPoolExecutor() as pool:
            return await asyncio.get_event_loop().run_in_executor(pool, self.rig.close)

    @asynccontextmanager
    async def _create_connection(self):

        reader = writer = None
        try:
            # Use asyncio's open_connection with timeout
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=self.timeout
            )
            yield reader, writer

        finally:
            # Close the connection if it was opened
            if writer is not None:
                writer.close()
                try:
                    # Wait for the writer to close, but with a timeout
                    await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
                except (asyncio.TimeoutError, Exception):
                    # Ignore errors during cleanup
                    pass

    async def ping(self):

        try:
            # Use the async connection manager
            async with self._create_connection() as (reader, writer):
                # Send frequency query command
                writer.write(b"f\n")
                await writer.drain()

                # Receive response with timeout
                response_bytes = await asyncio.wait_for(reader.read(1000), timeout=self.timeout)

                response = response_bytes.decode("utf-8", errors="replace").strip()

                # Parse the response
                if not response:
                    return False

                # Handle different response formats
                if response.startswith("RPRT"):
                    error_code = int(response.split()[1])
                    return error_code >= 0

                elif response.startswith("get_freq:"):
                    parts = response.split(":")[1].strip()
                    try:
                        float(parts)
                        return True
                    except ValueError:
                        return False

                else:
                    try:
                        float(response)
                        return True
                    except ValueError:
                        return False

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            # Handle all connection-related errors
            self.logger.exception(e)
            return False

        except Exception as e:
            # Catch all other exceptions
            self.logger.exception(e)
            return False

    async def get_frequency(self) -> float:

        self.check_connection()

        try:
            freq = await asyncio.to_thread(self.rig.get_freq)
            assert freq is not None, "Frequency is None"

            self.logger.debug(f"Current frequency: {freq} Hz")

        except Exception as e:
            self.logger.error(f"Error getting frequency: {e}")
            raise RuntimeError(f"Error getting frequency: {e}")

        return float(round(freq, 0))

    async def get_mode(self) -> Tuple[str, int]:

        self.check_connection()

        try:
            mode, bandwidth = await asyncio.to_thread(self.rig.get_mode)
            assert mode is not None, "Mode is None"

            self.logger.debug(f"Current mode: {mode}, bandwidth: {bandwidth} Hz")

        except Exception as e:
            self.logger.error(f"Error getting mode: {e}")
            raise RuntimeError(f"Error getting mode: {e}")

        return mode, bandwidth

    async def standby(self) -> bool:

        self.check_connection()

        try:
            self.logger.info("Setting rig to standby")
            status = self.rig.set_powerstat(Hamlib.RIG_POWER_STANDBY)
            self.logger.debug(f"Standby command: status={status}")

        except Exception as e:
            self.logger.error(f"Error setting rig to standby: {e}")
            raise RuntimeError(f"Error setting rig to standby: {e}")

        return True

    def check_connection(self) -> bool:

        if not self.connected or self.rig is None:
            error_msg = f"Not connected to rig (connected: {self.connected}, rig: {self.rig})"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        return True

    def __del__(self) -> None:
        """Destructor - ensure we disconnect when the object is garbage collected."""
        if self.connected and self.rig is not None:
            # Direct synchronous disconnection if possible
            try:
                self.logger.warning(
                    "Object RigController being destroyed while still connected to rig"
                )
                if hasattr(self.rig, "close"):
                    self.rig.close()
                self.connected = False
                self.rig = None
            except Exception as e:
                # Just log errors, never raise from __del__
                self.logger.error(f"Error during cleanup: {e}")

    @staticmethod
    def get_error_message(error_code: int) -> str:

        error_messages = {
            Hamlib.RIG_OK: "No error",
            Hamlib.RIG_EINVAL: "Invalid parameter",
            Hamlib.RIG_ECONF: "Invalid configuration",
            Hamlib.RIG_ENOMEM: "Memory shortage",
            Hamlib.RIG_ENIMPL: "Function not implemented",
            Hamlib.RIG_ETIMEOUT: "Communication timed out",
            Hamlib.RIG_EIO: "IO error",
            Hamlib.RIG_EINTERNAL: "Internal Hamlib error",
            Hamlib.RIG_EPROTO: "Protocol error",
            Hamlib.RIG_ERJCTED: "Command rejected",
            Hamlib.RIG_ETRUNC: "String truncated",
            Hamlib.RIG_ENAVAIL: "Function not available",
            Hamlib.RIG_ENTARGET: "Target not available",
            Hamlib.RIG_BUSERROR: "Bus error",
            Hamlib.RIG_BUSBUSY: "Bus busy",
            Hamlib.RIG_EARG: "Invalid argument",
            Hamlib.RIG_EVFO: "Invalid VFO",
            Hamlib.RIG_EDOM: "Argument out of domain",
        }

        return error_messages.get(error_code, f"Unknown error code: {error_code}")

    async def set_frequency(
        self,
        target_freq: float,
        update_interval: float = 0.5,
        freq_tolerance: float = 10.0,
        vfo: str = "1",
    ) -> AsyncGenerator[Tuple[float, bool], None]:

        # Map VFO string to Hamlib VFO constant
        vfo_map = {
            "1": Hamlib.RIG_VFO_A,
            "2": Hamlib.RIG_VFO_B,
            "none": Hamlib.RIG_VFO_A,  # Default to VFO A
        }
        hamlib_vfo = vfo_map.get(vfo, Hamlib.RIG_VFO_A)

        # Start the frequency setting operation
        self.logger.info(f"Setting rig frequency to {target_freq} Hz on VFO {vfo}")

        try:
            status = await asyncio.to_thread(self.rig.set_freq, _freq_t=target_freq, vfo=hamlib_vfo)
            self.logger.debug(f"Set frequency command: status={status}")

        except Exception as e:
            self.logger.error(f"Error setting rig frequency: {e}")
            self.logger.exception(e)
            raise RuntimeError(f"Error setting rig frequency: {e}")

        # Initial status
        current_freq = await self.get_frequency()
        freq_reached = abs(current_freq - target_freq) <= freq_tolerance
        is_tuning = not freq_reached

        # First yield with initial frequency
        yield current_freq, is_tuning

        # Keep checking frequency when a consumer requests an update
        while is_tuning:
            # Wait for the update interval
            await asyncio.sleep(update_interval)

            # Get current frequency
            current_freq = await self.get_frequency()

            # Check if we've reached the target
            freq_reached = abs(current_freq - target_freq) <= freq_tolerance
            is_tuning = not freq_reached

            # Yield the current frequency and tuning status
            yield current_freq, is_tuning

    async def set_mode(self, mode: str, bandwidth: int = 0) -> bool:

        try:
            self.logger.info(f"Setting rig mode to {mode}, bandwidth={bandwidth} Hz")
            status = await asyncio.to_thread(self.rig.set_mode, mode, bandwidth)
            self.logger.debug(f"Set mode command: status={status}")

            return True

        except Exception as e:
            self.logger.error(f"Error setting rig mode: {e}")
            self.logger.exception(e)
            raise RuntimeError(f"Error setting rig mode: {e}")
