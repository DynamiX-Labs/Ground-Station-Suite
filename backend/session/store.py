"""Session configuration store shared by session modules."""

from __future__ import annotations

from typing import Any, Dict, Optional

active_sdr_clients: Dict[str, Dict[str, Any]] = {}


def add_sdr_session(sid: str, sdr_config: Dict[str, Any]) -> Dict[str, Any]:
    active_sdr_clients[sid] = sdr_config
    return active_sdr_clients[sid]


def get_sdr_session(sid: str) -> Optional[Dict[str, Any]]:
    return active_sdr_clients.get(sid)
