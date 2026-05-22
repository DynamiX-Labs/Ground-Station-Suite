"""
SessionService façade centralizing session lifecycle operations.

Phase 2: route handlers through this service to make SessionTracker the
single source of truth for session presence/relationships while keeping
active_sdr_clients as the backing store for configuration.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, cast

from server import runtimestate
from session.store import active_sdr_clients, add_sdr_session, get_sdr_session
from session.tracker import session_tracker
from vfos.state import VFOManager

logger = logging.getLogger("session-service")


def _get_process_manager():
    """Get process manager from runtime state (set during startup)."""
    return runtimestate.process_manager


async def cleanup_sdr_session(sid: str) -> None:
    """Clean up and release resources associated with an SDR client session."""
    if sid in active_sdr_clients:
        client = get_sdr_session(sid)
        sdr_id = client.get("sdr_id") if client else None

        if sdr_id:
            process_manager = _get_process_manager()
            if not process_manager:
                logger.warning("ProcessManager not initialized while cleaning session %s", sid)
            else:
                await process_manager.stop_sdr_process(sdr_id, sid)

                if process_manager.transcription_manager:
                    process_manager.transcription_manager.stop_all_for_session(sid)
                    logger.info("Stopped all transcription consumers for session %s", sid)

        del active_sdr_clients[sid]

    else:
        logger.debug(
            "Client %s not found in active clients during cleanup. "
            "This is normal for sessions that never started streaming.",
            sid,
        )

        process_manager = _get_process_manager()
        if process_manager and process_manager.transcription_manager:
            process_manager.transcription_manager.stop_all_for_session(sid)

    session_tracker.clear_session(sid)


class SessionService:
    """
    A small façade to coordinate updates between SessionTracker,
    ProcessManager, and the configuration store (active_sdr_clients).
    """

    # -------------------- Query helpers --------------------
    def get_session_config(self, session_id: str) -> Optional[Dict[str, Any]]:
        # get_sdr_session is dynamically typed; cast to our declared return type
        return cast(Optional[Dict[str, Any]], get_sdr_session(session_id))

    def session_exists(self, session_id: str) -> bool:
        return session_id in active_sdr_clients

    def list_active_session_ids(self) -> List[str]:
        # Keys are session IDs (str), but the dict is dynamically typed
        return cast(List[str], list(active_sdr_clients.keys()))

    # -------------------- Lifecycle (write) APIs --------------------
    async def configure_sdr(
        self, session_id: str, sdr_device: Dict[str, Any], sdr_config: Dict[str, Any]
    ) -> None:
        """
        Register/update session configuration and tracker bindings.
        Does not start the SDR process; call start_streaming for that.
        """
        # Store/replace configuration
        add_sdr_session(session_id, sdr_config)

        # Update tracker relationship (session -> sdr)
        sdr_id = sdr_config.get("sdr_id")
        if sdr_id:
            session_tracker.register_session_streaming(session_id, sdr_id)

    async def start_streaming(self, session_id: str, sdr_device: Dict[str, Any]) -> Optional[str]:
        """Start or join the SDR worker process for the configured session."""
        cfg = self.get_session_config(session_id)
        if not cfg:
            return None
        sdr_id = cfg.get("sdr_id")
        process_manager = _get_process_manager()
        if not process_manager:
            logger.error("ProcessManager not initialized; cannot start streaming")
            return None

        # ProcessManager API may be untyped; cast result to Optional[str]
        started_id = cast(
            Optional[str], await process_manager.start_sdr_process(sdr_device, cfg, session_id)
        )
        # Ensure tracker binding is set
        if sdr_id:
            session_tracker.register_session_streaming(session_id, sdr_id)
        return started_id

    async def stop_streaming(self, session_id: str, sdr_id: Optional[str]) -> None:
        """Stop/leave the SDR worker process for the session (if any)."""
        if not sdr_id:
            cfg = self.get_session_config(session_id)
            sdr_id = cfg.get("sdr_id") if cfg else None
        if sdr_id:
            process_manager = _get_process_manager()
            if not process_manager:
                logger.error("ProcessManager not initialized; cannot stop streaming")
                return
            await process_manager.stop_sdr_process(sdr_id, session_id)
            # Unregister streaming relationship from tracker, but keep the session alive
            session_tracker.unregister_session_streaming(session_id)

    async def select_vfo(self, session_id: str, vfo_number: Optional[int]) -> None:
        """Update the selected VFO in SessionTracker (normalized Optional[int])."""
        session_tracker.set_session_vfo_int(session_id, vfo_number)

    async def cleanup_session(self, session_id: str) -> None:
        """
        Cleanup all resources associated with the session:
        - Clean up WebAudioStreamer session stats
        - Stop consumers/process if needed (delegated to utils)
        - Clear SessionTracker relationships
        - Remove configuration entry
        """
        # Clean up WebAudioStreamer session stats
        try:
            if runtimestate.audio_consumer:
                runtimestate.audio_consumer.cleanup_session(session_id)
        except Exception as e:
            # Log but don't fail - continue with other cleanup
            logger.warning(f"Failed to cleanup WebAudioStreamer for session {session_id}: {e}")

        # Delegate to existing idempotent cleanup function which also clears tracker
        await cleanup_sdr_session(session_id)

    # -------------------- Read-only views --------------------
    def get_runtime_snapshot(self) -> Dict[str, dict]:
        process_manager = _get_process_manager()
        if not process_manager:
            return {"sessions": {}, "sdrs": {}}
        # Tracker returns a mapping structure; cast to declared type for mypy
        return cast(Dict[str, dict], session_tracker.get_runtime_snapshot(process_manager))

    # -------------------- Internal observation support --------------------
    async def register_internal_observation(
        self,
        observation_id: str,
        sdr_device: Dict[str, Any],
        sdr_config: Dict[str, Any],
        vfo_number: int,
        metadata: Optional[Dict[str, Any]] = None,
        session_key: Optional[str] = None,
    ) -> str:
        """
        Register and start an internal observation session.

        This is the high-level entry point for ObservationScheduler.

        Args:
            observation_id: Unique observation identifier
            sdr_device: SDR device dictionary
            sdr_config: SDR configuration dictionary
            vfo_number: VFO number (1-4)
            metadata: Optional additional metadata for the observation

        Returns:
            Internal session ID (e.g., "internal:obs-abc-123")
        """
        session_id = VFOManager.make_internal_session_id(observation_id, session_key)

        # Register in tracker
        session_tracker.register_internal_session(
            observation_id, sdr_config["sdr_id"], vfo_number, metadata, session_key=session_key
        )

        # Configure SDR
        await self.configure_sdr(session_id, sdr_device, sdr_config)

        # Start streaming
        await self.start_streaming(session_id, sdr_device)

        return str(session_id)

    async def cleanup_internal_observation(
        self, observation_id: str, session_key: Optional[str] = None
    ) -> None:
        """
        Cleanup internal observation session.

        Stops SDR, clears tracker, removes config.

        Args:
            observation_id: Unique observation identifier
        """
        session_id = VFOManager.make_internal_session_id(observation_id, session_key)

        # Full cleanup (stops SDR, clears tracker, removes config)
        await self.cleanup_session(session_id)

        # Unregister from internal session set
        session_tracker.unregister_internal_session(observation_id, session_key=session_key)


# Singleton instance
session_service = SessionService()
