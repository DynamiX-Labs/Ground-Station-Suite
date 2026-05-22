#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Built-in telemetry payload parser registration.

This module centralizes parser registration so new payload parsers can be
added without modifying TelemetryParser internals.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Tuple, Type

from .colibri_s import ColibriSGeoscanAx25Parser
from .rs52s import RS52SGeoscanAx25Parser

logger = logging.getLogger("telemetry.parsers.registry")


def _iter_builtin_ax25_parsers() -> Iterable[Tuple[str, Type[Any]]]:
    """
    Yield built-in AX.25 callsign-keyed payload parser bindings.

    Keys are matched by TelemetryParser against AX.25 source callsign variants.
    """
    return (
        ("RS52S", RS52SGeoscanAx25Parser),
        ("RS67S", ColibriSGeoscanAx25Parser),
        ("COLIBRI-S", ColibriSGeoscanAx25Parser),
    )


def register_builtin_payload_parsers(target: Any) -> None:
    """
    Register built-in payload parsers on a TelemetryParser-like target.

    The target is expected to expose:
      - `payload_parsers` dictionary
      - `register_payload_parser(identifier, parser)`
    """
    for key, parser_cls in _iter_builtin_ax25_parsers():
        try:
            if key in target.payload_parsers:
                continue
            target.register_payload_parser(key, parser_cls())
        except Exception as e:
            logger.warning("Failed to register payload parser '%s': %s", key, e)
