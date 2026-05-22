"""
Lightweight typing models for session and runtime data.

These are intended for annotations and documentation only; they do not
introduce any runtime dependencies or validation. All shapes remain JSON-safe
in public views (e.g., runtime snapshots) and keep existing behavior.
"""

from typing import Dict, List, Optional, TypedDict


class SessionConfig(TypedDict, total=False):
    """Per-session SDR configuration payload stored in active_sdr_clients.

    Note: Keys reflect current usage in handlers; this model is permissive
    (total=False) to avoid breaking callers while documenting intent.
    """

    sdr_id: str
    center_freq: float
    sample_rate: float
    gain: float
    fft_size: int
    bias_t: bool
    tuner_agc: bool
    rtl_agc: bool
    fft_window: str
    fft_averaging: int
    fft_overlap_percent: int
    fft_overlap_depth: int
    antenna: Optional[str]
    recording_path: Optional[str]
    serial_number: Optional[str]
    host: Optional[str]
    port: Optional[int]
    client_id: str
    soapy_agc: bool
    offset_freq: float


class SessionView(TypedDict, total=False):
    """Merged relationship/config view for a session."""

    session_id: str
    sdr_id: Optional[str]
    rig_id: Optional[str]
    vfo: Optional[int]
    config: SessionConfig
    is_internal: bool  # True for internal observations, False for user sessions


class ConsumerMeta(TypedDict, total=False):
    """Metadata for a running consumer (thread) instance.

    Stored internally under ProcessManager.processes for demodulators/recorders/decoders
    as a dict with at least an "instance" and a "subscription_key". The public JSON views
    do not expose the instance; they typically expose the class name per VFO.
    """

    instance: object
    subscription_key: str
    class_name: Optional[str]
    thread_name: Optional[str]
    vfo_number: Optional[int]


class SDRProcessStatus(TypedDict, total=False):
    """Basic status of an SDR worker process."""

    alive: bool
    pid: Optional[int]
    name: Optional[str]


class RuntimeSDRConsumers(TypedDict, total=False):
    """JSON-safe snapshot entry for one SDR in a runtime snapshot."""

    alive: bool
    clients: List[str]
    demodulators: Dict[str, Dict[int, Optional[str]]]
    recorders: Dict[str, Optional[str]]
    decoders: Dict[str, Dict[int, Optional[str]]]


class RuntimeSnapshot(TypedDict, total=False):
    """Top-level runtime snapshot structure."""

    sessions: Dict[str, SessionView]
    sdrs: Dict[str, RuntimeSDRConsumers]
