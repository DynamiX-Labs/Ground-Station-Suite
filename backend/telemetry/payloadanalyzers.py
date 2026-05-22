#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Payload Analyzers - Multiple interpretation views for unknown telemetry formats

Provides different views of raw payload data to help reverse engineer formats.
"""

import struct
from typing import Any, Dict, List


class PayloadAnalyzer:
    """Analyze payload bytes with multiple interpretation strategies"""

    @staticmethod
    def analyze(payload: bytes) -> Dict[str, Any]:
        """
        Analyze payload with multiple interpretations

        Returns dict with different views:
        - hex_dump: Structured hex display
        - as_floats: Interpret as float32 sequence
        - as_uint16: Interpret as uint16 sequence
        - as_uint32: Interpret as uint32 sequence
        - as_strings: Interpret as text strings with multiple encodings
        - probable_fields: Auto-detected field types
        """
        return {
            "hex_dump": PayloadAnalyzer.hex_dump(payload),
            "as_floats": PayloadAnalyzer.as_float32(payload),
            "as_uint16": PayloadAnalyzer.as_uint16(payload),
            "as_uint32": PayloadAnalyzer.as_uint32(payload),
            "as_strings": PayloadAnalyzer.as_strings(payload),
            "probable_fields": PayloadAnalyzer.detect_fields(payload),
        }

    @staticmethod
    def hex_dump(payload: bytes, bytes_per_line: int = 16) -> List[Dict]:
        """
        Generate hex dump with ASCII

        Returns list of lines:
        [{'offset': 0, 'hex': '00 01 02...', 'ascii': '...'}]
        """
        lines = []
        for i in range(0, len(payload), bytes_per_line):
            chunk = payload[i : i + bytes_per_line]
            hex_str = " ".join(f"{b:02x}" for b in chunk)
            ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append({"offset": i, "hex": hex_str, "ascii": ascii_str})
        return lines

    @staticmethod
    def as_float32(payload: bytes) -> List[Dict]:
        """
        Interpret as little-endian float32 sequence

        Returns list of floats with offsets
        """
        floats = []
        for i in range(0, len(payload) - 3, 4):
            try:
                value = struct.unpack("<f", payload[i : i + 4])[0]
                # Check if it's a reasonable value (not NaN, not huge)
                if abs(value) < 1e6 and not (value != value):  # not NaN
                    floats.append(
                        {
                            "offset": i,
                            "value": round(value, 4),
                            "hex": payload[i : i + 4].hex(),
                            "type": "float32_le",
                        }
                    )
            except Exception:
                pass
        return floats

    @staticmethod
    def as_uint16(payload: bytes) -> List[Dict]:
        """Interpret as little-endian uint16 sequence"""
        values = []
        for i in range(0, len(payload) - 1, 2):
            try:
                value = struct.unpack("<H", payload[i : i + 2])[0]
                values.append(
                    {
                        "offset": i,
                        "value": value,
                        "hex": payload[i : i + 2].hex(),
                        "type": "uint16_le",
                    }
                )
            except Exception:
                pass
        return values

    @staticmethod
    def as_uint32(payload: bytes) -> List[Dict]:
        """Interpret as little-endian uint32 sequence"""
        values = []
        for i in range(0, len(payload) - 3, 4):
            try:
                value = struct.unpack("<I", payload[i : i + 4])[0]
                values.append(
                    {
                        "offset": i,
                        "value": value,
                        "hex": payload[i : i + 4].hex(),
                        "type": "uint32_le",
                    }
                )
            except Exception:
                pass
        return values

    @staticmethod
    def detect_fields(payload: bytes) -> List[Dict]:
        """
        Auto-detect probable field types based on value ranges

        Heuristics:
        - 0-10V range -> voltage
        - -50 to +100°C range -> temperature
        - 0-5A range -> current
        - Very large uint32 -> timestamp
        """
        probable = []

        # Check as floats
        for i in range(0, len(payload) - 3, 4):
            try:
                value = struct.unpack("<f", payload[i : i + 4])[0]
                if abs(value) < 1e6 and not (value != value):
                    field_type = None
                    if 0 < value < 10:
                        field_type = "voltage?"
                    elif -50 < value < 100:
                        field_type = "temperature?"
                    elif 0 < value < 5:
                        field_type = "current?"

                    if field_type:
                        probable.append(
                            {
                                "offset": i,
                                "value": round(value, 4),
                                "type": field_type,
                                "data_type": "float32_le",
                            }
                        )
            except Exception:
                pass

        # Check as uint32 for timestamps
        for i in range(0, len(payload) - 3, 4):
            try:
                value = struct.unpack("<I", payload[i : i + 4])[0]
                # Unix timestamp range (year 2000-2100)
                if 946684800 < value < 4102444800:
                    probable.append(
                        {
                            "offset": i,
                            "value": value,
                            "type": "timestamp?",
                            "data_type": "uint32_le",
                        }
                    )
            except Exception:
                pass

        return probable

    @staticmethod
    def as_strings(payload: bytes, min_length: int = 3) -> Dict[str, Any]:
        """
        Extract and analyze strings from payload with multiple encodings

        Args:
            payload: Raw bytes to analyze
            min_length: Minimum string length to consider

        Returns:
            dict with:
            - strings: List of detected strings with metadata
            - statistics: Overall string content statistics
        """
        strings = []
        encodings_to_try = ["ascii", "utf-8", "latin-1"]

        # 1. Extract contiguous printable ASCII sequences
        current_string: List[int] = []
        start_offset = 0

        for i, byte in enumerate(payload):
            # Printable ASCII range (space to ~)
            if 32 <= byte <= 126:
                if not current_string:
                    start_offset = i
                current_string.append(byte)
            else:
                # End of string - process if long enough
                if len(current_string) >= min_length:
                    strings.append(
                        PayloadAnalyzer._analyze_string_segment(
                            bytes(current_string), start_offset, encodings_to_try
                        )
                    )
                current_string = []

        # Handle final string
        if len(current_string) >= min_length:
            strings.append(
                PayloadAnalyzer._analyze_string_segment(
                    bytes(current_string), start_offset, encodings_to_try
                )
            )

        # 2. Look for null-terminated strings
        null_terminated = PayloadAnalyzer._find_null_terminated_strings(payload, min_length)
        for nt_string in null_terminated:
            # Avoid duplicates
            if not any(
                s["offset"] == nt_string["offset"] and s["content"] == nt_string["content"]
                for s in strings
            ):
                strings.append(nt_string)

        # 3. Try length-prefixed strings (common format: 1 byte length + data)
        length_prefixed = PayloadAnalyzer._find_length_prefixed_strings(payload, min_length)
        for lp_string in length_prefixed:
            if not any(
                s["offset"] == lp_string["offset"] and s["content"] == lp_string["content"]
                for s in strings
            ):
                strings.append(lp_string)

        # Sort by offset
        strings.sort(key=lambda x: x["offset"])

        # Calculate statistics
        total_printable = sum(1 for b in payload if 32 <= b <= 126)
        total_null = sum(1 for b in payload if b == 0)

        statistics = {
            "total_bytes": len(payload),
            "printable_ascii_count": total_printable,
            "printable_ascii_percent": round(
                (total_printable / len(payload) * 100) if payload else 0, 1
            ),
            "null_bytes": total_null,
            "strings_found": len(strings),
        }

        return {"strings": strings, "statistics": statistics}

    @staticmethod
    def _analyze_string_segment(
        segment: bytes, offset: int, encodings: List[str]
    ) -> Dict[str, Any]:
        """Analyze a string segment and determine best encoding and type"""
        result = {
            "offset": offset,
            "length": len(segment),
            "hex": segment.hex(),
        }

        # Try each encoding
        decoded_variants = {}
        for encoding in encodings:
            try:
                decoded = segment.decode(encoding)
                decoded_variants[encoding] = decoded
            except Exception:
                pass

        # Use ASCII as primary if available
        content: str = decoded_variants.get(
            "ascii", decoded_variants.get("utf-8", decoded_variants.get("latin-1", ""))
        )
        result["content"] = content
        result["encoding"] = "ascii" if "ascii" in decoded_variants else "utf-8"

        # Detect string type patterns
        result["detected_type"] = PayloadAnalyzer._detect_string_type(content)
        result["confidence"] = PayloadAnalyzer._string_confidence(content, segment)

        return result

    @staticmethod
    def _detect_string_type(content: str) -> str:
        """Detect what type of string this might be"""
        content_upper = content.upper()

        # Callsign pattern (amateur radio)
        if len(content) >= 3 and content.replace("-", "").replace(" ", "").isalnum():
            if any(c.isdigit() for c in content) and any(c.isalpha() for c in content):
                return "callsign?"

        # Version string
        if any(content.lower().startswith(prefix) for prefix in ["v", "ver", "fw", "version"]):
            return "version?"

        # Status messages
        status_keywords = [
            "OK",
            "ERROR",
            "FAIL",
            "READY",
            "INIT",
            "START",
            "STOP",
            "ON",
            "OFF",
        ]
        if content_upper in status_keywords:
            return "status?"

        # Date/time patterns
        if any(sep in content for sep in [":", "-", "/"]) and any(c.isdigit() for c in content):
            if content.count(":") >= 1 or content.count("-") >= 2:
                return "datetime?"

        # Mostly digits (could be counter/ID)
        if content.isdigit():
            return "numeric?"

        # Mixed alphanumeric (identifiers, codes)
        if content.isalnum():
            return "identifier?"

        return "text"

    @staticmethod
    def _string_confidence(content: str, segment: bytes) -> str:
        """Assign confidence level to detected string"""
        # High confidence: common English words, known patterns
        common_words = [
            "ok",
            "error",
            "test",
            "ready",
            "data",
            "status",
            "version",
            "time",
            "temp",
            "voltage",
            "current",
        ]
        if any(word in content.lower() for word in common_words):
            return "high"

        # Medium confidence: mostly letters/numbers with spaces
        if len(content) >= 5 and (content.replace(" ", "").replace("-", "").isalnum()):
            return "medium"

        # Low confidence: very short or unusual patterns
        if len(content) < 5:
            return "low"

        return "medium"

    @staticmethod
    def _find_null_terminated_strings(payload: bytes, min_length: int) -> List[Dict]:
        """Find null-terminated C-style strings"""
        strings = []
        i = 0

        while i < len(payload):
            # Look for start of printable sequence
            if 32 <= payload[i] <= 126:
                start = i
                while i < len(payload) and 32 <= payload[i] <= 126:
                    i += 1

                # Check if followed by null terminator
                if i < len(payload) and payload[i] == 0:
                    segment = payload[start:i]
                    if len(segment) >= min_length:
                        try:
                            content = segment.decode("ascii")
                            strings.append(
                                {
                                    "offset": start,
                                    "length": len(segment),
                                    "content": content,
                                    "encoding": "ascii",
                                    "detected_type": PayloadAnalyzer._detect_string_type(content),
                                    "confidence": PayloadAnalyzer._string_confidence(
                                        content, segment
                                    ),
                                    "format": "null-terminated",
                                    "hex": segment.hex(),
                                }
                            )
                        except Exception:
                            pass
            i += 1

        return strings

    @staticmethod
    def _find_length_prefixed_strings(payload: bytes, min_length: int) -> List[Dict]:
        """Find length-prefixed strings (1-byte length prefix)"""
        strings = []

        for i in range(len(payload) - min_length):
            length = payload[i]

            # Reasonable length values (3-50 bytes)
            if min_length <= length <= 50 and i + 1 + length <= len(payload):
                segment = payload[i + 1 : i + 1 + length]

                # Check if all bytes are printable ASCII
                if all(32 <= b <= 126 for b in segment):
                    try:
                        content = segment.decode("ascii")
                        strings.append(
                            {
                                "offset": i + 1,
                                "length": length,
                                "content": content,
                                "encoding": "ascii",
                                "detected_type": PayloadAnalyzer._detect_string_type(content),
                                "confidence": PayloadAnalyzer._string_confidence(content, segment),
                                "format": "length-prefixed",
                                "hex": segment.hex(),
                            }
                        )
                    except Exception:
                        pass

        return strings
