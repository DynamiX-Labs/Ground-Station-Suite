"""Shared helpers for transcription-related entity handlers."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select

from db import AsyncSessionLocal
from db.models import Satellites, Transmitters


async def fetch_transmitter_and_satellite(
    transmitter_id: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Fetch transmitter and satellite dictionaries from database."""
    try:
        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(
                select(Transmitters).where(Transmitters.id == transmitter_id)
            )
            transmitter_record = result.scalar_one_or_none()
            if not transmitter_record:
                return None, None

            transmitter_dict: Dict[str, Any] = {
                "id": transmitter_record.id,
                "description": transmitter_record.description,
                "mode": transmitter_record.mode,
                "baud": transmitter_record.baud,
                "downlink_low": transmitter_record.downlink_low,
                "downlink_high": transmitter_record.downlink_high,
                "norad_cat_id": transmitter_record.norad_cat_id,
            }

            sat_result = await db_session.execute(
                select(Satellites).where(Satellites.norad_id == transmitter_record.norad_cat_id)
            )
            satellite_record = sat_result.scalar_one_or_none()
            satellite_dict = None
            if satellite_record:
                satellite_dict = {
                    "norad_id": satellite_record.norad_id,
                    "name": satellite_record.name,
                    "alternative_name": satellite_record.alternative_name,
                    "status": satellite_record.status,
                    "image": satellite_record.image,
                }

            return transmitter_dict, satellite_dict
    except Exception as e:
        logger = logging.getLogger("transcription-helpers")
        logger.error(f"Failed to fetch transmitter/satellite info: {e}", exc_info=True)
        return None, None
