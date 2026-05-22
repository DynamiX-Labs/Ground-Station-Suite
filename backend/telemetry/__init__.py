"""
Telemetry parsing module for Ground Station

Generic + pluggable architecture for parsing satellite telemetry.
Supports AX.25 framing with satellite-specific payload parsers.
"""

from .ax25parser import AX25Parser
from .parser import TelemetryParser

__all__ = ["TelemetryParser", "AX25Parser"]
