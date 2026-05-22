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
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Tuple, cast

from Hamlib import Hamlib

from common.arguments import arguments as args


class RotatorController:
    def __init__(
        self,
        model: int = Hamlib.ROT_MODEL_SATROTCTL,
        host: str = "127.0.0.1",
        port: int = 4533,
        verbose: bool = False,
        timeout: float = 5.0,
    ):

        # Set up logging
        device_path = f"{host}:{port}"
        self.logger = logging.getLogger("rotator-control")
        self.logger.setLevel(args.log_level)
        self.logger.info(f"Initializing RotatorController with model={model}, device={device_path}")

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
        self.rotator = None
        self.connected = False
        self.timeout = timeout

    def _get_rotator(self) -> Any:
        if self.rotator is None:
            raise RuntimeError("Rotator is not initialized")
        return cast(Any, self.rotator)

    async def connect(self) -> bool:

        if self.connected:
            self.logger.warning("Already connected to rotator")
            return True

        try:
            # first we ping the rotator
            pingcheck = await self.ping()
            assert pingcheck, "Rotator did not respond to ping"

            self.logger.debug(f"Connecting to rotator at {self.device_path}")
            rotator = Hamlib.Rot(self.model)
            rotator.set_conf("rot_pathname", self.device_path)

            # Set timeout
            rotator.set_conf("timeout", str(int(self.timeout * 1000)))  # Convert to ms

            # Initialize the rotator (opens the connection)
            rotator.open()
            self.rotator = rotator

            self.connected = True
            self.logger.info(f"Successfully connected to rotator as {self.device_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error connecting to rotator: {e}")
            raise RuntimeError(f"Error connecting to rotator: {e}")

    async def disconnect(self) -> bool:

        if not self.connected or self.rotator is None:
            self.logger.warning("Not connected to rotator")
            return True

        try:
            rotator = self._get_rotator()
            result = await asyncio.wait_for(asyncio.to_thread(rotator.close), timeout=3.0)
            self.logger.debug(f"Close command: result={result}")

            self.connected = False
            self.rotator = None
            self.logger.info("Disconnected from rotator")
            return True

        except Exception as e:
            self.logger.error(f"Error disconnecting from rotator: {e}")
            return False

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
                # Send position query command

                writer.write(b"p\n")
                await writer.drain()

                # Receive response with timeout
                response_bytes = await asyncio.wait_for(reader.read(1000), timeout=self.timeout)

                response = response_bytes.decode("utf-8", errors="replace").strip()

                # Parse the response (same as before)
                if not response:
                    return False

                # Handle different response formats
                if response.startswith("RPRT"):
                    error_code = int(response.split()[1])
                    return error_code >= 0

                elif response.startswith("get_pos:"):
                    parts = response.split(":")[1].strip().split()
                    if len(parts) >= 2:
                        try:
                            float(parts[0])
                            float(parts[1])
                            return True
                        except ValueError:
                            return False
                    return False

                else:
                    parts = response.split()
                    if len(parts) >= 2:
                        try:
                            float(parts[0])
                            float(parts[1])
                            return True
                        except ValueError:
                            return False
                    return False

        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            # Handle all connection-related errors
            self.logger.exception(e)
            return False

        except Exception as e:
            # Catch all other exceptions
            self.logger.exception(e)
            return False

    async def get_position(self) -> Tuple[float, float]:
        self.check_connection()

        try:
            rotator = self._get_rotator()
            az, el = await asyncio.to_thread(rotator.get_position)
            assert az is not None, "Azimuth is None"
            assert el is not None, "Elevation is None"

            self.logger.debug(f"Current position: az={az}, el={el}")
            return round(az, 3), round(el, 3)

        except Exception as e:
            self.logger.error(f"Error getting position: {e}")
            raise RuntimeError(f"Error getting position: {e}")

    async def park(self, park_az=None, park_el=None) -> bool:
        self.check_connection()

        try:
            rotator = self._get_rotator()
            if (park_az is None) != (park_el is None):
                raise ValueError("park_az and park_el must either both be set or both be null")

            if park_az is not None and park_el is not None:
                self.logger.info(
                    "Parking rotator using configured target az=%s el=%s", park_az, park_el
                )
                status = await asyncio.to_thread(rotator.set_position, park_az, park_el)
            else:
                self.logger.info("Parking rotator")
                status = await asyncio.to_thread(rotator.park)
            self.logger.info(f"Park command: status={status}")

            # if status != Hamlib.RIG_OK:
            #    error_msg = f"Failed to park rotator: {self.get_error_message(status)}"
            #    self.logger.error(error_msg)
            #    raise RuntimeError(error_msg)

            return True

        except Exception as e:
            self.logger.error(f"Error parking rotator: {e}")
            raise RuntimeError(f"Error parking rotator: {e}")

    def check_connection(self) -> bool:

        if not self.connected or self.rotator is None:
            error_msg = (
                f"Not connected to rotator (connected: {self.connected}, rotator: {self.rotator})"
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        return True

    def __del__(self) -> None:
        """Destructor - log a warning if still connected when object is garbage collected."""
        if self.connected and hasattr(self, "logger"):
            try:
                # Just log a warning rather than trying to run async code
                self.logger.warning(
                    "Object RotatorController being garbage collected while still connected"
                )

                # If there's a synchronous way to close the underlying connection, use it
                if (
                    self.rotator is not None
                    and hasattr(self.rotator, "close")
                    and callable(self.rotator.close)
                ):
                    try:
                        # Only if close() can be called synchronously
                        self.rotator.close()
                    except Exception as e:
                        self.logger.error(f"Error during cleanup: {e}")

            except Exception:
                # Avoid any exceptions in __del__
                pass

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

    async def set_position(
        self,
        target_az: float,
        target_el: float,
        update_interval: float = 2,
        az_tolerance: float = 2.0,
        el_tolerance: float = 2.0,
    ) -> AsyncGenerator[Tuple[float, float, bool], None]:
        self.check_connection()

        # Start the slew operation
        try:
            rotator = self._get_rotator()
            self.logger.info(f"Setting rotator position to az={target_az}, el={target_el}")
            status = await asyncio.to_thread(rotator.set_position, target_az, target_el)
            self.logger.debug(f"Set position command: status={status}")

        except Exception as e:
            self.logger.error(f"Error setting rotator position: {e}")
            self.logger.exception(e)
            raise RuntimeError(f"Error setting rotator position: {e}")

        # Initial status
        current_az, current_el = await self.get_position()
        az_reached = abs(current_az - target_az) <= az_tolerance
        el_reached = abs(current_el - target_el) <= el_tolerance
        is_slewing = not (az_reached and el_reached)

        # First yield with the initial position
        yield current_az, current_el, is_slewing

        # Keep checking position when a consumer requests an update
        while is_slewing:
            # Wait for the update interval
            # await asyncio.sleep(update_interval)

            # Get the current position
            current_az, current_el = await self.get_position()

            # Check if we've reached the target
            az_reached = abs(current_az - target_az) <= az_tolerance
            el_reached = abs(current_el - target_el) <= el_tolerance
            is_slewing = not (az_reached and el_reached)

            # Yield the current position and slewing status
            yield current_az, current_el, is_slewing
