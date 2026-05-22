import logging
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

# Configure logging for the worker process
logger = logging.getLogger("vfo-state")

# How many VFOs
USER_VFO_NUMBER = 4
INTERNAL_VFO_NUMBER = 10


@dataclass
class VFOState:
    vfo_number: int = 0
    center_freq: int = 0
    bandwidth: int = 10000
    modulation: str = "FM"
    active: bool = False
    selected: bool = False
    volume: int = 50
    squelch: int = -150
    squelch_mode: str = "carrier"  # carrier, voice, hybrid
    vad_sensitivity: str = "medium"  # low, medium, high
    vad_close_delay_ms: int = 300  # 50-500 ms hangover
    transcription_enabled: bool = False  # Enable/disable transcription for this VFO
    transcription_provider: str = "gemini"  # Transcription provider (gemini, deepgram)
    transcription_language: str = "auto"  # Language code for transcription (auto-detect by default)
    transcription_translate_to: str = (
        "none"  # Target language for translation (none = no translation)
    )
    decoder: str = "none"  # Decoder type: none, sstv, afsk, fsk, gmsk, gfsk, bpsk, morse, gnss
    locked_transmitter_id: str = "none"
    parameters_enabled: bool = True  # Enable/disable custom decoder parameters


class VFOManager:
    _instance = None
    _session_vfo_states: Dict[str, Dict[int, VFOState]] = {}

    # Internal observation namespace prefix
    INTERNAL_PREFIX = "internal:"
    SQUELCH_MODES = {"carrier", "voice", "hybrid"}
    VAD_SENSITIVITY_LEVELS = {"low", "medium", "high"}
    VAD_CLOSE_DELAY_MS_MIN = 50
    VAD_CLOSE_DELAY_MS_MAX = 500

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VFOManager, cls).__new__(cls)
            cls._instance._session_vfo_states = {}
        return cls._instance

    def _ensure_session_vfos(self, session_id: str) -> None:
        """Ensure VFOs exist for the given session_id."""
        if session_id not in self._session_vfo_states:
            self._session_vfo_states[session_id] = {}
            vfo_limit = self.get_session_vfo_limit(session_id)
            # Initialize VFOs with default values for this session
            for i in range(vfo_limit):
                self._session_vfo_states[session_id][i + 1] = VFOState(vfo_number=i + 1)

    def get_all_session_ids(self) -> List[str]:
        """Returns a list of all session IDs currently in the VFOManager."""
        return list(self._session_vfo_states.keys())

    def get_vfo_state(self, session_id: str, vfo_id: int) -> Optional[VFOState]:
        self._ensure_session_vfos(session_id)
        return self._session_vfo_states[session_id].get(vfo_id)

    def update_vfo_state(
        self,
        session_id: str,
        vfo_id: int,
        center_freq: Optional[int] = None,
        bandwidth: Optional[int] = None,
        modulation: Optional[str] = None,
        active: Optional[bool] = None,
        selected: Optional[bool] = None,
        volume: Optional[int] = None,
        squelch: Optional[int] = None,
        squelch_mode: Optional[str] = None,
        vad_sensitivity: Optional[str] = None,
        vad_close_delay_ms: Optional[int] = None,
        transcription_enabled: Optional[bool] = None,
        transcription_provider: Optional[str] = None,
        transcription_language: Optional[str] = None,
        transcription_translate_to: Optional[str] = None,
        decoder: Optional[str] = None,
        locked_transmitter_id: Optional[str] = None,
        parameters_enabled: Optional[bool] = None,
    ) -> None:

        assert session_id is not None, "session_id is required"

        self._ensure_session_vfos(session_id)
        session_vfos = self._session_vfo_states[session_id]

        # Check if the user deselected all VFOs
        if vfo_id == 0 and selected is not None:
            # deselect all VFOs for this session
            for _vfo_id in session_vfos:
                session_vfos[_vfo_id].selected = False
            return

        if vfo_id not in session_vfos:
            return

        vfo_state = session_vfos[vfo_id]

        # update center frequency
        if center_freq is not None:
            vfo_state.center_freq = center_freq

        # update bandwidth
        if bandwidth is not None:
            vfo_state.bandwidth = bandwidth

        # update modulation
        if modulation is not None:
            vfo_state.modulation = modulation

        # check if active
        if active is not None:
            vfo_state.active = active

        # check volume
        if volume is not None:
            vfo_state.volume = volume

        # check squelch
        if squelch is not None:
            vfo_state.squelch = squelch

        # Check squelch mode
        if squelch_mode is not None:
            normalized_squelch_mode = str(squelch_mode).lower().strip()
            if normalized_squelch_mode in self.SQUELCH_MODES:
                vfo_state.squelch_mode = normalized_squelch_mode

        # Check VAD sensitivity
        if vad_sensitivity is not None:
            normalized_vad_sensitivity = str(vad_sensitivity).lower().strip()
            if normalized_vad_sensitivity in self.VAD_SENSITIVITY_LEVELS:
                vfo_state.vad_sensitivity = normalized_vad_sensitivity

        # Check VAD close delay
        if vad_close_delay_ms is not None:
            try:
                parsed_close_delay = int(vad_close_delay_ms)
            except (TypeError, ValueError):
                parsed_close_delay = vfo_state.vad_close_delay_ms

            clamped_close_delay = max(
                self.VAD_CLOSE_DELAY_MS_MIN,
                min(self.VAD_CLOSE_DELAY_MS_MAX, parsed_close_delay),
            )
            vfo_state.vad_close_delay_ms = clamped_close_delay

        # check if selected
        if selected is not None:
            # Only deselect other VFOs if this VFO is being selected (not deselected)
            if selected:
                # since a VFO is now selected set the other VFOs to not selected for this session
                for _vfo_id in session_vfos:
                    session_vfos[_vfo_id].selected = False

            vfo_state.selected = selected

        # check transcription settings
        if transcription_enabled is not None:
            vfo_state.transcription_enabled = transcription_enabled

        if transcription_provider is not None:
            vfo_state.transcription_provider = transcription_provider

        if transcription_language is not None:
            vfo_state.transcription_language = transcription_language

        if transcription_translate_to is not None:
            vfo_state.transcription_translate_to = transcription_translate_to

        # check decoder setting
        if decoder is not None:
            vfo_state.decoder = decoder

        # check locked transmitter ID
        if locked_transmitter_id is not None:
            vfo_state.locked_transmitter_id = locked_transmitter_id

        # check parameters enabled
        if parameters_enabled is not None:
            vfo_state.parameters_enabled = parameters_enabled

        # logger.info(f"vfo states for session {session_id}: {session_vfos}")

    def get_all_vfo_states(self, session_id: str) -> Dict[int, VFOState]:
        self._ensure_session_vfos(session_id)
        return self._session_vfo_states[session_id].copy()

    def get_active_vfos(self, session_id: str) -> List[VFOState]:
        """Returns list of all active VFO states for a session."""
        self._ensure_session_vfos(session_id)
        session_vfos = self._session_vfo_states[session_id]

        return [vfo_state for vfo_state in session_vfos.values() if vfo_state.active]

    def get_selected_vfo(self, session_id: str) -> Optional[VFOState]:
        """
        DEPRECATED: Returns the currently selected VFO state or None if no VFO is selected.

        This method is deprecated and should not be used. Legacy mode has been removed.
        Use get_vfo_state(session_id, vfo_number) with explicit VFO number instead.
        """
        logger.warning(
            "get_selected_vfo() is deprecated. Use get_vfo_state() with explicit vfo_number instead."
        )
        self._ensure_session_vfos(session_id)
        session_vfos = self._session_vfo_states[session_id]

        for vfo_state in session_vfos.values():
            if vfo_state.selected:
                return vfo_state

        return None

    async def emit_vfo_states(self, sio, session_id: str) -> None:
        """Emit all VFO states for a specific session to that session's room."""
        self._ensure_session_vfos(session_id)
        session_vfos = self._session_vfo_states[session_id]

        # Convert VFO states to dictionaries for JSON serialization
        vfo_states_dict = {vfo_id: asdict(vfo_state) for vfo_id, vfo_state in session_vfos.items()}

        await sio.emit(
            "vfo-states",
            vfo_states_dict,
            room=session_id,
        )

    async def emit_vfo_frequency_update(self, sio, session_id: str, vfo_id: int) -> None:
        """Emit only frequency update for a specific VFO to avoid overwriting user's other settings."""
        self._ensure_session_vfos(session_id)
        vfo_state = self._session_vfo_states[session_id].get(vfo_id)

        if vfo_state:
            await sio.emit(
                "vfo-frequency-update",
                {
                    "vfo_id": vfo_id,
                    "frequency": vfo_state.center_freq,
                },
                room=session_id,
            )

    # ============================================================
    # INTERNAL OBSERVATION SUPPORT
    # Methods for automated/programmatic observations
    # ============================================================

    @staticmethod
    def make_internal_session_id(observation_id: str, session_key: Optional[str] = None) -> str:
        """
        Generate internal session ID for an automated observation.

        Args:
            observation_id: Unique observation identifier (UUID)
            session_key: Optional suffix to distinguish multiple sessions

        Returns:
            Internal session ID (e.g., "internal:obs-abc-123" or "internal:obs-abc-123:rx1")

        Example:
            >>> VFOManager.make_internal_session_id("550e8400-e29b-41d4-a716-446655440000")
            "internal:550e8400-e29b-41d4-a716-446655440000"
        """
        if session_key:
            return f"{VFOManager.INTERNAL_PREFIX}{observation_id}:{session_key}"
        return f"{VFOManager.INTERNAL_PREFIX}{observation_id}"

    @staticmethod
    def is_internal_session(session_id: str) -> bool:
        """
        Check if a session ID belongs to an internal/automated observation.

        Args:
            session_id: Session ID to check

        Returns:
            True if internal observation, False if user session

        Example:
            >>> VFOManager.is_internal_session("internal:obs-123")
            True
            >>> VFOManager.is_internal_session("user-session-abc")
            False
        """
        return session_id.startswith(VFOManager.INTERNAL_PREFIX)

    @staticmethod
    def get_session_vfo_limit(session_id: str) -> int:
        """
        Get the VFO limit for a session.

        Internal observations use INTERNAL_VFO_NUMBER; user sessions use USER_VFO_NUMBER.
        """
        if VFOManager.is_internal_session(session_id):
            return INTERNAL_VFO_NUMBER
        return USER_VFO_NUMBER

    def create_internal_vfos(self, observation_id: str, session_key: Optional[str] = None) -> str:
        """
        Initialize a new set of VFOs for an automated observation.

        Creates internal VFOs with default state, isolated from user VFOs.

        Args:
            observation_id: Unique observation identifier

        Returns:
            Internal session ID that was created

        Example:
            >>> vfo_mgr = VFOManager()
            >>> session_id = vfo_mgr.create_internal_vfos("obs-123")
            >>> print(session_id)
            "internal:obs-123"
        """
        session_id = self.make_internal_session_id(observation_id, session_key)
        self._ensure_session_vfos(session_id)
        logger.info(
            f"Created internal VFOs for observation {observation_id} (session: {session_id})"
        )
        return session_id

    def cleanup_internal_vfos(self, observation_id: str, session_key: Optional[str] = None) -> bool:
        """
        Remove VFOs when automated observation completes.

        Args:
            observation_id: Unique observation identifier

        Returns:
            True if VFOs were found and removed, False otherwise

        Example:
            >>> vfo_mgr.cleanup_internal_vfos("obs-123")
            True
        """
        session_id = self.make_internal_session_id(observation_id, session_key)

        if session_id in self._session_vfo_states:
            del self._session_vfo_states[session_id]
            logger.debug(f"Cleaned up internal VFOs for observation {observation_id}")
            return True

        logger.warning(f"No internal VFOs found for observation {observation_id}")
        return False

    def configure_internal_vfo(
        self,
        observation_id: str,
        vfo_number: int,
        center_freq: int,
        bandwidth: int,
        modulation: str,
        decoder: str = "none",
        locked_transmitter_id: str = "none",
        squelch: int = -150,
        squelch_mode: str = "carrier",
        vad_sensitivity: str = "medium",
        vad_close_delay_ms: int = 300,
        volume: int = 50,
        session_key: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Configure a VFO for automated observation with sensible defaults.

        This is a convenience wrapper around update_vfo_state() with defaults
        appropriate for unattended observations.

        Args:
            observation_id: Unique observation identifier
        vfo_number: VFO number (1-10)
            center_freq: Center frequency in Hz
            bandwidth: Bandwidth in Hz
            modulation: Modulation type (FM, AM, SSB, etc.)
            decoder: Decoder type (afsk, bpsk, fsk, gmsk, gfsk, sstv, morse, gnss, none)
            locked_transmitter_id: Transmitter ID for doppler tracking (default: "none")
            squelch: Squelch level in dB (default: -150, wide open)
            volume: Audio volume 0-100 (default: 50)
            squelch_mode: Squelch mode (carrier, voice, hybrid)
            vad_sensitivity: Voice squelch sensitivity (low, medium, high)
            vad_close_delay_ms: Voice squelch close delay in milliseconds
            session_key: Optional suffix to identify the internal session
            session_id: Optional full internal session ID override

        Example:
            >>> vfo_mgr.configure_internal_vfo(
            ...     observation_id="obs-123",
            ...     vfo_number=1,
            ...     center_freq=137_500_000,  # 137.5 MHz
            ...     bandwidth=40_000,          # 40 kHz
            ...     modulation="FM",
            ...     decoder="none",
            ...     locked_transmitter_id="noaa-18-apt"
            ... )
        """
        internal_session_id = session_id or self.make_internal_session_id(
            observation_id, session_key
        )

        # Ensure VFOs exist for this observation
        self._ensure_session_vfos(internal_session_id)

        # Configure VFO with sensible defaults for automation
        self.update_vfo_state(
            session_id=internal_session_id,
            vfo_id=vfo_number,
            center_freq=center_freq,
            bandwidth=bandwidth,
            modulation=modulation,
            active=True,  # Always active for observations
            selected=False,  # Not relevant for internal VFOs
            volume=volume,
            squelch=squelch,
            squelch_mode=squelch_mode,
            vad_sensitivity=vad_sensitivity,
            vad_close_delay_ms=vad_close_delay_ms,
            decoder=decoder,
            locked_transmitter_id=locked_transmitter_id,
            parameters_enabled=True,
            transcription_enabled=False,  # Disable transcription by default
        )

        logger.info(
            f"Configured internal VFO {vfo_number} for observation {observation_id}: "
            f"freq={center_freq/1e6:.3f}MHz, bw={bandwidth/1e3:.1f}kHz, "
            f"mod={modulation}, decoder={decoder}, locked_tx={locked_transmitter_id}"
        )

    def get_all_internal_sessions(self) -> List[str]:
        """
        Get all internal/automated observation session IDs.

        Returns:
            List of internal session IDs

        Example:
            >>> vfo_mgr.get_all_internal_sessions()
            ["internal:obs-123", "internal:obs-456"]
        """
        return [
            session_id
            for session_id in self._session_vfo_states.keys()
            if self.is_internal_session(session_id)
        ]

    def get_all_user_sessions(self) -> List[str]:
        """
        Get all user/UI session IDs (excludes internal observations).

        Returns:
            List of user session IDs

        Example:
            >>> vfo_mgr.get_all_user_sessions()
            ["session-abc-123", "session-def-456"]
        """
        return [
            session_id
            for session_id in self._session_vfo_states.keys()
            if not self.is_internal_session(session_id)
        ]

    def get_internal_vfo_count(self) -> int:
        """
        Get count of active internal observation sessions.

        Returns:
            Number of internal sessions

        Example:
            >>> vfo_mgr.get_internal_vfo_count()
            2
        """
        return len(self.get_all_internal_sessions())
