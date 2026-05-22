import errno
import logging
import socket
import struct
import time
from typing import Optional

import numpy as np


class RtlSdrTcpClient:
    """
    A client for interacting with an RTL-SDR device via an rtl_tcp server.

    Mimics some basic functionality of the pyrtlsdr library for remote devices.
    """

    # RTL_TCP command codes (based on common rtl_tcp implementations)
    _CMD_SET_FREQ: int = 0x01
    _CMD_SET_SAMPLE_RATE: int = 0x02
    _CMD_SET_GAIN_MODE: int = 0x03
    _CMD_SET_GAIN: int = 0x04
    _CMD_SET_FREQ_CORRECTION: int = 0x05
    # _CMD_SET_IF_GAIN: int = 0x06 # Less common, often handled by set_gain
    # _CMD_SET_TEST_MODE: int = 0x07 # Not typically needed for basic use
    _CMD_SET_AGC_MODE: int = 0x08  # RTL AGC
    _CMD_SET_DIRECT_SAMPLING: int = 0x09
    _CMD_SET_OFFSET_TUNING: int = 0x0A
    # _CMD_SET_RTL_XTAL: int = 0x0B # Less common modification
    # _CMD_SET_TUNER_XTAL: int = 0x0C # Less common modification
    _CMD_SET_TUNER_GAIN_BY_INDEX: int = 0x0D  # Alternative gain setting
    _CMD_SET_BIAS_TEE: int = 0x0E
    _CMD_SET_TUNER_AGC: int = 0x0F  # Tuner AGC (requires specific gain modes)

    # Tuner type mapping
    _TUNER_TYPES = {1: "E4000", 2: "FC0012", 3: "FC0013", 4: "FC2580", 5: "R820T", 6: "R828D"}

    DEFAULT_PORT: int = 1234
    CONNECT_TIMEOUT: float = 5.0  # Seconds
    READ_TIMEOUT: float = 10.0  # Seconds for sample reads
    READ_CHUNK_SIZE: int = 16384  # Bytes to read per recv call

    def __init__(self, hostname: str, port: int = DEFAULT_PORT, verbose: bool = False):
        """
        Initialize the RTL-SDR TCP client.

        Args:
            hostname: The hostname or IP address of the rtl_tcp server.
            port: The port number of the rtl_tcp server.
            verbose: If True, enable DEBUG level logging.
        """
        self.server_host: str = hostname
        self.server_port: int = port
        self._sock: Optional[socket.socket] = None
        self._connected: bool = False
        self._tuner_type_id: Optional[int] = None
        self._tuner_type_name: Optional[str] = None
        self._tuner_gain_count: Optional[int] = None  # Info from server
        self._logger = logging.getLogger("rtlsdr-tcp-client")
        if verbose:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

        # Internal state for properties
        self._center_freq: Optional[float] = None
        self._sample_rate: Optional[float] = None
        self._gain: Optional[float] = None
        self._freq_correction: Optional[int] = None
        # Keep track of modes as well if needed for logic, e.g. gain_mode
        self._gain_mode_manual: Optional[bool] = None
        self._agc_mode_enabled: Optional[bool] = None
        self._tuner_agc_enabled: Optional[bool] = None
        self._direct_sampling_mode: Optional[int] = None
        self._offset_tuning_enabled: Optional[bool] = None
        self._bias_tee_enabled: Optional[bool] = None

    def connect(self) -> bool:
        """
        Connect to the rtl_tcp server and retrieve dongle information.

        Returns:
            True if connection was successful, False otherwise.
        """
        if self._connected and self._sock:
            self._logger.info("Already connected.")
            return True

        self._logger.info(f"Attempting to connect to {self.server_host}:{self.server_port}...")
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.CONNECT_TIMEOUT)

        try:
            self._sock.connect((self.server_host, self.server_port))
            self._logger.debug("Socket connected. Reading dongle info...")

            # Read the 12-byte dongle information header
            dongle_info = self._sock.recv(12)
            if len(dongle_info) != 12:
                raise IOError(
                    f"Failed to receive complete dongle info (got {len(dongle_info)} bytes)."
                )

            # Unpack: Magic (4s), Tuner Type (I), Gain Count (I) - Network Byte Order (!)
            magic, self._tuner_type_id, self._tuner_gain_count = struct.unpack("!4sII", dongle_info)

            if magic != b"RTL0":
                self._logger.warning(
                    f"Received unexpected magic bytes: {magic!r}. Expected b'RTL0'."
                )
                # Continue anyway, but log the warning

            if self._tuner_type_id is not None:
                self._tuner_type_name = self._TUNER_TYPES.get(
                    self._tuner_type_id, f"Unknown ({self._tuner_type_id})"
                )
            else:
                self._tuner_type_name = "Unknown"

            self._logger.info(
                f"Connected successfully. Tuner: {self._tuner_type_name}, Gain Count: {self._tuner_gain_count}"
            )
            self._connected = True

            # Disable the timeout for normal operation
            self._sock.settimeout(None)

            # Reset internal state upon successful connection (as device state is unknown)
            self._center_freq = None
            self._sample_rate = None
            self._gain = None
            self._freq_correction = None
            self._gain_mode_manual = None
            self._agc_mode_enabled = None
            self._tuner_agc_enabled = None
            self._direct_sampling_mode = None
            self._offset_tuning_enabled = None
            self._bias_tee_enabled = None

            return True

        except socket.timeout:
            self._logger.error(f"Connection timed out after {self.CONNECT_TIMEOUT} seconds.")
            self._cleanup()
            raise

        except ConnectionRefusedError:
            self._logger.error("Connection refused. Is the rtl_tcp server running?")
            self._cleanup()
            raise

        except socket.gaierror:
            self._logger.error(f"Could not resolve hostname: {self.server_host}")
            self._cleanup()

            raise

        except (OSError, IOError) as e:
            self._logger.error(f"Connection failed: {e}")
            self._cleanup()

            raise

        except Exception as e:
            self._logger.error(f"An unexpected error occurred during connection: {e}")
            self._cleanup()
            raise

    def _cleanup(self):
        # Cleanup on failure
        if self._sock:
            self._sock.close()
            self._sock = None

        self._connected = False
        # Ensure state is None if connection failed
        self._center_freq = None
        self._sample_rate = None
        self._gain = None
        self._freq_correction = None
        self._gain_mode_manual = None
        self._agc_mode_enabled = None
        self._tuner_agc_enabled = None
        self._direct_sampling_mode = None
        self._offset_tuning_enabled = None
        self._bias_tee_enabled = None

    def _ensure_connected(self) -> None:
        """Checks connection status and attempts to reconnect if necessary."""
        if not self._connected or self._sock is None:
            self._logger.info("Not connected. Attempting to reconnect...")
            if not self.connect():
                raise ConnectionError("Failed to establish connection with rtl_tcp server.")

    def _send_command(self, command: int, value: int) -> None:
        """
        Sends a command and a 4-byte integer value to the rtl_tcp server.

        Args:
            command: The command code byte.
            value: The integer parameter for the command.

        Raises:
            ConnectionError: If not connected or sending fails.
            IOError: If sending data over the socket fails.
        """
        self._ensure_connected()
        if self._sock is None:  # Should be caught by _ensure_connected, but double-check
            raise ConnectionError("Socket is unexpectedly None after connection check.")

        try:
            # Pack command (Byte) and value (Unsigned Int) in Network Order (> or !)
            packed_cmd = struct.pack(">BI", command, value)
            self._logger.debug(
                f"Sending command 0x{command:02X} with value {value} ({packed_cmd.hex()})"
            )
            self._sock.sendall(packed_cmd)

        except (OSError, IOError) as e:
            self._logger.error(f"Failed to send command 0x{command:02X}: {e}")
            self.close()  # Assume the connection is broken
            raise IOError(f"Socket error while sending command: {e}") from e

        except Exception as e:
            self._logger.error(f"Unexpected error sending command 0x{command:02X}: {e}")
            self.close()
            raise

    @property
    def center_freq(self) -> Optional[float]:
        """Gets the last successfully set center frequency."""
        # self._logger.warning("Cannot get center_freq from rtl_tcp, protocol is write-only.")
        # return None # Or store last set value if desired
        return self._center_freq

    @center_freq.setter
    def center_freq(self, freq_hz: float) -> None:
        """Sets the tuner center frequency."""
        freq_int = int(freq_hz)
        self._logger.info(f"Setting center frequency to {freq_int} Hz")
        self._send_command(self._CMD_SET_FREQ, freq_int)
        # Update internal state *after* successful send
        self._center_freq = float(freq_int)

    @property
    def sample_rate(self) -> Optional[float]:
        """Gets the last successfully set sample rate."""
        # self._logger.warning("Cannot get sample_rate from rtl_tcp, protocol is write-only.")
        # return None
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, rate_sps: float) -> None:
        """Sets the sample rate."""
        rate_int = int(rate_sps)
        self._logger.info(f"Setting sample rate to {rate_int} Sps")
        self._send_command(self._CMD_SET_SAMPLE_RATE, rate_int)
        # Update internal state *after* successful send
        self._sample_rate = float(rate_int)

    @property
    def gain(self) -> Optional[float]:
        """Gets the last successfully set gain in dB."""
        # self._logger.warning("Cannot get gain from rtl_tcp, protocol is write-only.")
        # return None
        # Note: If gain mode is auto, this value might not reflect actual gain.
        if self._gain_mode_manual is False:
            self._logger.warning(
                "Gain mode is Auto. Returned value is the last *manually set* gain, not the current automatic gain."
            )
        return self._gain

    @gain.setter
    def gain(self, gain_db: float) -> None:
        """Sets the tuner gain in dB. Uses tenths of dB for the command."""
        gain_tenth_db = int(gain_db * 10)
        # Ensure gain is non-negative before sending
        if gain_tenth_db < 0:
            self._logger.warning(
                f"Requested gain {gain_db} dB is negative, setting to 0 dB (0 tenths)."
            )
            gain_tenth_db = 0
            gain_db = 0.0  # Update the value we store as well

        self._logger.info(f"Setting gain to {gain_db} dB ({gain_tenth_db}/10 dB)")
        self._send_command(self._CMD_SET_GAIN, gain_tenth_db)
        # Update internal state *after* successful send
        self._gain = gain_db
        # Setting manual gain often implies switching to manual gain mode
        # Consider uncommenting this if setting gain should always force manual mode:
        # if self._gain_mode_manual is not True:
        #    self.set_gain_mode(manual=True)

    def set_gain_mode(self, manual: bool = True) -> None:
        """Sets the gain mode (Manual or Auto)."""
        # rtl_tcp: 0 = manual, 1 = auto
        # mode = 0 if manual else 1
        mode = 1 if manual else 0
        self._logger.info(f"Setting gain mode to {'Manual' if manual else 'Auto'}")
        self._send_command(self._CMD_SET_GAIN_MODE, mode)
        # Update internal state *after* successful send
        self._gain_mode_manual = manual

    def set_manual_gain_enabled(self, enabled: bool = True) -> None:
        """Sets manual gain mode. Wrapper for set_gain_mode() for compatibility."""
        self.set_gain_mode(manual=enabled)

    # Expose gain_mode as a property
    @property
    def gain_mode_manual(self) -> Optional[bool]:
        """Gets the last set gain mode (True for Manual, False for Auto). Returns None if never set."""
        return self._gain_mode_manual

    @property
    def freq_correction(self) -> Optional[int]:
        """Gets the last successfully set frequency correction in PPM."""
        # self._logger.warning("Cannot get freq_correction from rtl_tcp, protocol is write-only.")
        # return None
        return self._freq_correction

    @freq_correction.setter
    def freq_correction(self, ppm: int) -> None:
        """Sets the frequency correction in parts-per-million (PPM)."""
        ppm_int = int(ppm)
        self._logger.info(f"Setting frequency correction to {ppm_int} PPM")
        self._send_command(self._CMD_SET_FREQ_CORRECTION, ppm_int)
        # Update internal state *after* successful send
        self._freq_correction = ppm_int

    def set_agc_mode(self, enable: bool = True) -> None:
        """Enables or disables the RTL chip's Automatic Gain Control (AGC)."""
        value = 1 if enable else 0
        self._logger.info(f"{'Enabling' if enable else 'Disabling'} RTL AGC")
        self._send_command(self._CMD_SET_AGC_MODE, value)
        # Update internal state *after* successful send
        self._agc_mode_enabled = enable

    # Expose agc_mode as a property
    @property
    def agc_mode(self) -> Optional[bool]:
        """Gets the last set state of the RTL AGC (True if enabled). Returns None if never set."""
        return self._agc_mode_enabled

    def set_tuner_agc(self, enable: bool = True) -> None:
        """Enables or disables the Tuner's Automatic Gain Control (AGC)."""
        value = int(enable)  # Convert boolean to 0/1
        self._logger.info(f"{'Enabling' if enable else 'Disabling'} Tuner AGC")

        try:
            # Set gain mode to manual first
            self.set_gain_mode(manual=True)
            # Then set tuner AGC
            self._send_command(self._CMD_SET_TUNER_AGC, value)
            self._tuner_agc_enabled = enable

        except (IOError, ConnectionError) as e:
            self._logger.warning(f"Could not set Tuner AGC: {e}. Command may not be supported.")
            # Reset internal state since command failed
            self._tuner_agc_enabled = None
            raise

        except Exception as e:
            self._logger.error(f"Unexpected error setting Tuner AGC: {e}")
            self._tuner_agc_enabled = None
            raise

    # Expose tuner_agc as a property
    @property
    def tuner_agc(self) -> Optional[bool]:
        """Gets the last successfully set state of the Tuner AGC (True if enabled). Returns None if never set or failed."""
        return self._tuner_agc_enabled

    def set_direct_sampling(self, mode: int) -> None:
        """
        Sets the direct sampling mode.

        Args:
            mode: 0=Off, 1=I-ADC, 2=Q-ADC
        """
        if mode not in [0, 1, 2]:
            raise ValueError("Invalid direct sampling mode. Must be 0, 1, or 2.")
        self._logger.info(f"Setting direct sampling mode to {mode}")
        self._send_command(self._CMD_SET_DIRECT_SAMPLING, mode)
        # Update internal state *after* successful send
        self._direct_sampling_mode = mode

    # Expose direct_sampling as a property
    @property
    def direct_sampling(self) -> Optional[int]:
        """Gets the last set direct sampling mode (0=Off, 1=I-ADC, 2=Q-ADC). Returns None if never set."""
        return self._direct_sampling_mode

    def set_offset_tuning(self, enable: bool = True) -> None:
        """Enables or disables offset tuning (center frequency offset)."""
        value = 1 if enable else 0
        self._logger.info(f"{'Enabling' if enable else 'Disabling'} offset tuning")
        self._send_command(self._CMD_SET_OFFSET_TUNING, value)
        # Update internal state *after* successful send
        self._offset_tuning_enabled = enable

    # Expose offset_tuning as a property
    @property
    def offset_tuning(self) -> Optional[bool]:
        """Gets the last set state of offset tuning (True if enabled). Returns None if never set."""
        return self._offset_tuning_enabled

    def set_bias_tee(self, enable: bool = True) -> None:
        """Enables or disables the bias tee output."""
        value = 1 if enable else 0
        self._logger.info(f"{'Enabling' if enable else 'Disabling'} bias tee")
        try:
            self._send_command(self._CMD_SET_BIAS_TEE, value)
            # Update internal state *only if* command succeeds
            self._bias_tee_enabled = enable
        except (IOError, ConnectionError) as e:
            self._logger.warning(
                f"Could not set Bias Tee: {e}. Command may not be supported. State not updated."
            )
            # Do not update state if command failed
        except Exception as e:
            self._logger.error(f"Unexpected error setting Bias Tee: {e}")
            # Do not update state if command failed
            raise

    # Expose bias_tee as a property
    @property
    def bias_tee(self) -> Optional[bool]:
        """Gets the last successfully set state of the bias tee (True if enabled). Returns None if never set or failed."""
        return self._bias_tee_enabled

    def read_samples(self, num_samples: int = 16384) -> np.ndarray:
        """
        Reads the specified number of complex samples from the SDR.

        Args:
            num_samples: The number of complex (I/Q) samples to read.

        Returns:
            A numpy array of complex64 samples.

        Raises:
            ConnectionError: If not connected or reading fails.
            IOError: If a socket error occurs during reading.
            TimeoutError: If reading takes longer than READ_TIMEOUT.
        """
        self._ensure_connected()
        if self._sock is None:
            raise ConnectionError("Socket is unexpectedly None after connection check.")

        bytes_to_read = num_samples * 2  # 2 bytes (I and Q) per complex sample
        buffer = bytearray()
        start_time = time.monotonic()
        original_timeout = self._sock.gettimeout()

        self._logger.debug(f"Attempting to read {num_samples} samples ({bytes_to_read} bytes)...")

        try:
            # Set a read timeout for this operation
            self._sock.settimeout(self.READ_TIMEOUT)

            while len(buffer) < bytes_to_read:
                # Check overall timeout
                elapsed_time = time.monotonic() - start_time
                if elapsed_time > self.READ_TIMEOUT:
                    raise TimeoutError(
                        f"Read timed out after {elapsed_time:.2f}s waiting for samples ({len(buffer)}/{bytes_to_read} bytes received)."
                    )

                remaining_bytes = bytes_to_read - len(buffer)
                chunk_size = min(self.READ_CHUNK_SIZE, remaining_bytes)

                try:
                    data = self._sock.recv(chunk_size)
                    if not data:
                        # Server closed the connection
                        raise ConnectionError("Connection closed by server while reading samples.")
                    buffer.extend(data)
                    # Reset start time slightly if data received to allow continuous streams
                    # Or keep original start_time for a strict overall timeout
                    # start_time = time.monotonic() # Uncomment to reset timeout on activity

                except socket.timeout:
                    # recv timed out, but overall timeout might not be hit yet.
                    # Log it but continue the loop to check overall timeout.
                    self._logger.debug(
                        f"Socket recv timed out waiting for chunk, elapsed {elapsed_time:.2f}s."
                    )
                    continue  # Let the outer loop check the main timeout

                except (OSError, IOError) as e:
                    self._logger.error(f"Socket error during sample read: {e}")
                    self.close()  # Assume the connection is broken
                    raise IOError(f"Socket error while reading samples: {e}") from e

            # If we exit the loop, we should have enough bytes
            if len(buffer) < bytes_to_read:
                # This case should ideally be caught by a timeout or connection errors, but handle defensively.
                raise IOError(
                    f"Insufficient data received: got {len(buffer)}, expected {bytes_to_read}."
                )

            self._logger.debug(f"Successfully read {len(buffer)} bytes.")

            # Convert bytes to samples
            # rtl_tcp sends unsigned 8-bit integers (0-255)
            iq_uint8 = np.frombuffer(buffer, dtype=np.uint8)

            # Convert to float32 and normalize to [-1.0, 1.0]
            # Subtract 127.5 to center around 0, divide by 127.5 to scale
            iq_float = (iq_uint8.astype(np.float32) - 127.5) / 127.5

            # De-interleave I and Q samples and combine into complex numbers
            complex_samples = iq_float[0::2] + 1j * iq_float[1::2]

            return complex_samples.astype(np.complex64)  # Use standard complex64

        finally:
            # Always restore the original socket timeout
            if self._sock and self._connected:  # Check if socket still exists and connected
                try:
                    self._sock.settimeout(original_timeout)
                except OSError as e:
                    # Ignore error if socket was closed during read (e.g., by close() in except block)
                    if e.errno != errno.EBADF:
                        self._logger.warning(f"Could not restore original socket timeout: {e}")

    def close(self) -> None:
        """Closes the connection to the rtl_tcp server."""
        if self._sock:
            self._logger.info("Closing connection...")
            # Mark as disconnected immediately
            self._connected = False
            # Clear state on close
            self._center_freq = None
            self._sample_rate = None
            self._gain = None
            self._freq_correction = None
            self._gain_mode_manual = None
            self._agc_mode_enabled = None
            self._tuner_agc_enabled = None
            self._direct_sampling_mode = None
            self._offset_tuning_enabled = None
            self._bias_tee_enabled = None
            try:
                # Politely signal shutdown before closing
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError as e:
                # Ignore errors like "not connected" if already closed
                if e.errno != errno.ENOTCONN and e.errno != errno.EBADF:
                    self._logger.warning(f"Error during socket shutdown: {e} (errno {e.errno})")
            except Exception as e:
                self._logger.warning(f"Unexpected error during socket shutdown: {e}")
            finally:
                try:
                    self._sock.close()
                except Exception as e:
                    self._logger.warning(f"Error closing socket: {e}")

        self._sock = None
        # Ensure connected is False even if sock was None
        self._connected = False
        self._logger.info(f"Connection to {self.server_host}:{self.server_port} closed.")

    # --- Context Manager ---
    def __enter__(self):
        """Enter context management."""
        if not self._connected:
            self.connect()  # Attempt connection on entering context
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context management, ensuring connection is closed."""
        self.close()

    # --- Properties for Info ---
    @property
    def is_connected(self) -> bool:
        """Returns True if the client is currently connected."""
        # Check both flag and socket object existence
        return self._connected and self._sock is not None

    @property
    def tuner(self) -> Optional[str]:
        """Returns the name of the detected tuner type."""
        return self._tuner_type_name
