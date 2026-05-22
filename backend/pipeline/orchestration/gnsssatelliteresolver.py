# Copyright (c) 2026 Efstratios Goudelis
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

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from db import AsyncSessionLocal
from db.models import Satellites

_CONSTELLATION_TO_CODE = {
    "G": "G",
    "GPS": "G",
    "E": "E",
    "GALILEO": "E",
    "R": "R",
    "GLONASS": "R",
    "C": "C",
    "B": "C",
    "BEIDOU": "C",
    "BDS": "C",
    "J": "J",
    "QZSS": "J",
}

_CODE_TO_LABEL = {
    "G": "GPS",
    "E": "GALILEO",
    "R": "GLONASS",
    "C": "BEIDOU",
    "J": "QZSS",
}

_CODE_ALIASES = {
    "G": ("gps", "navstar"),
    "E": ("galileo", "gsat"),
    "R": ("glonass", "cosmos", "uragan"),
    "C": ("beidou", "bds"),
    "J": ("qzss", "qzs", "michibiki"),
}

_CODE_NAME_ALIASES = {
    "G": ("gps", "navstar"),
    "E": ("galileo",),
    "R": ("glonass", "uragan"),
    "C": ("beidou", "bds"),
    "J": ("qzss", "qzs", "michibiki"),
}


class GnssSatelliteResolver:
    """
    Resolve GNSS satellite identity (constellation + PRN) to NORAD satellite records.

    Matching is intentionally conservative: only high-confidence constellation-specific
    matches are accepted to avoid false-positive NORAD IDs in live decoder output.
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        identity_ttl_seconds: int = 3600,
        negative_identity_ttl_seconds: int = 45,
        catalog_ttl_seconds: int = 300,
    ) -> None:
        self.logger = logger or logging.getLogger("gnss-satellite-resolver")
        self.identity_ttl_seconds = max(60, identity_ttl_seconds)
        # Keep negative-cache TTL short so newly inserted aliases/rows become visible quickly.
        self.negative_identity_ttl_seconds = max(5, negative_identity_ttl_seconds)
        self.catalog_ttl_seconds = max(30, catalog_ttl_seconds)
        self._identity_cache: Dict[Tuple[str, int], Tuple[float, Optional[Dict[str, Any]]]] = {}
        self._catalog_cache: Tuple[float, List[Dict[str, Any]]] = (0.0, [])

    @staticmethod
    def _normalize_constellation(value: Any) -> Optional[str]:
        raw = str(value or "").strip().upper()
        if not raw:
            return None
        return _CONSTELLATION_TO_CODE.get(raw)

    @staticmethod
    def _parse_prn(value: Any) -> Optional[int]:
        if value is None:
            return None
        match = re.search(r"(\d{1,3})", str(value))
        if not match:
            return None
        parsed = int(match.group(1))
        return parsed if parsed > 0 else None

    def _extract_identity(self, output: Dict[str, Any]) -> Optional[Tuple[str, int]]:
        code = self._normalize_constellation(output.get("satellite_system"))
        prn = self._parse_prn(output.get("satellite_prn"))
        if code and prn:
            return code, prn

        satellite_text = str(output.get("satellite") or "")
        text_match = re.search(r"([A-Za-z]+)\s+PRN\s+([A-Za-z]?\d+)", satellite_text, re.IGNORECASE)
        if text_match:
            code = self._normalize_constellation(text_match.group(1))
            prn = self._parse_prn(text_match.group(2))
            if code and prn:
                return code, prn

        message = str(output.get("message") or "")
        acq_match = re.search(r"for satellite\s+([A-Z])\s+(\d+)", message, re.IGNORECASE)
        if acq_match:
            code = self._normalize_constellation(acq_match.group(1))
            prn = self._parse_prn(acq_match.group(2))
            if code and prn:
                return code, prn

        tracking_match = re.search(
            r"for satellite\s+([A-Za-z]+)\s+PRN\s+([A-Za-z]?\d+)",
            message,
            re.IGNORECASE,
        )
        if tracking_match:
            code = self._normalize_constellation(tracking_match.group(1))
            prn = self._parse_prn(tracking_match.group(2))
            if code and prn:
                return code, prn

        return None

    async def _get_catalog(self) -> List[Dict[str, Any]]:
        now = time.time()
        cached_ts, cached_rows = self._catalog_cache
        if cached_rows and (now - cached_ts) < self.catalog_ttl_seconds:
            return cached_rows

        rows: List[Dict[str, Any]] = []
        async with AsyncSessionLocal() as dbsession:
            result = await dbsession.execute(
                select(
                    Satellites.norad_id,
                    Satellites.name,
                    Satellites.name_other,
                    Satellites.alternative_name,
                    Satellites.sat_id,
                    Satellites.decayed,
                )
            )
            for row in result.all():
                rows.append(
                    {
                        "norad_id": row.norad_id,
                        "name": row.name or "",
                        "name_other": row.name_other or "",
                        "alternative_name": row.alternative_name or "",
                        "sat_id": row.sat_id or "",
                        "decayed": row.decayed,
                    }
                )

        self._catalog_cache = (now, rows)
        return rows

    @staticmethod
    def _score_candidate(candidate: Dict[str, Any], code: str, prn: int) -> int:
        haystack = " ".join(
            [
                str(candidate.get("name") or ""),
                str(candidate.get("name_other") or ""),
                str(candidate.get("alternative_name") or ""),
                str(candidate.get("sat_id") or ""),
            ]
        ).lower()

        alias_hit = any(alias in haystack for alias in _CODE_ALIASES.get(code, ()))
        if not alias_hit:
            return 0

        prn_pattern = re.compile(rf"\bprn\W*0*{prn}\b", re.IGNORECASE)
        code_pattern = re.compile(rf"\b{code.lower()}\W*0*{prn}\b", re.IGNORECASE)
        constellation_name_pattern = re.compile(
            rf"\b(?:{'|'.join(re.escape(alias) for alias in _CODE_NAME_ALIASES.get(code, ()))})\b"
            rf"\W*(?:prn|slot)?\W*0*{prn}\b",
            re.IGNORECASE,
        )

        score = 0

        has_prn = bool(prn_pattern.search(haystack))
        has_code = bool(code_pattern.search(haystack))
        has_constellation_number = bool(constellation_name_pattern.search(haystack))

        # Require a numeric constellation-specific identity match to avoid false positives.
        if not (has_prn or has_code or has_constellation_number):
            return 0

        score += 25

        if has_prn:
            score += 70
        if has_code:
            score += 65
        if has_constellation_number:
            score += 60

        # Prefer non-decayed records when multiple candidates share the same PRN slot.
        if candidate.get("decayed") is None:
            score += 3

        return score

    @staticmethod
    def _score_threshold(code: str) -> int:
        # Scores now require both constellation alias and numeric identity.
        # Keep threshold conservative but low enough for GALILEO "GALILEO <N>" rows.
        if code in {"G", "E", "C", "J"}:
            return 85
        return 90

    async def resolve_from_output(self, output: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(output, dict):
            return None

        identity = self._extract_identity(output)
        if not identity:
            return None
        code, prn = identity

        cache_key = (code, prn)
        cached = self._identity_cache.get(cache_key)
        now = time.time()
        if cached:
            cache_ttl = (
                self.identity_ttl_seconds
                if cached[1] is not None
                else self.negative_identity_ttl_seconds
            )
            if (now - cached[0]) < cache_ttl:
                return cached[1]

        catalog = await self._get_catalog()
        scored = []
        for entry in catalog:
            score = self._score_candidate(entry, code, prn)
            if score <= 0:
                continue
            scored.append((score, int(entry["norad_id"]), entry))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        best = scored[0][2] if scored else None
        best_score = scored[0][0] if scored else 0

        if not best or best_score < self._score_threshold(code):
            self._identity_cache[cache_key] = (now, None)
            return None

        resolved = {
            "norad_id": int(best["norad_id"]),
            "name": str(best.get("name") or ""),
            "constellation": _CODE_TO_LABEL.get(code, code),
            "prn": prn,
        }
        self._identity_cache[cache_key] = (now, resolved)
        return resolved
