#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telemetry parser plugins package.

Contains satellite- or protocol-specific payload parsers that plug into
the generic TelemetryParser. Parsers should expose a class with a
`parse(payload: bytes, **kwargs) -> Dict[str, Any]` method.
"""

from .colibri_s import ColibriSGeoscanAx25Parser
from .registry import register_builtin_payload_parsers
from .rs52s import RS52SGeoscanAx25Parser

__all__ = [
    "ColibriSGeoscanAx25Parser",
    "RS52SGeoscanAx25Parser",
    "register_builtin_payload_parsers",
]
