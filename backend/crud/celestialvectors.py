# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""CRUD helpers for persisted celestial vectors cache."""

from __future__ import annotations

import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from common.common import logger, serialize_object
from db.models import CelestialVectorsCache


def _normalize_entry(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "command": row.get("command"),
        "epoch_bucket_utc": row.get("epoch_bucket_utc"),
        "past_hours": row.get("past_hours"),
        "future_hours": row.get("future_hours"),
        "step_minutes": row.get("step_minutes"),
        "payload": row.get("payload"),
        "source": row.get("source"),
        "error": row.get("error"),
        "fetched_at": row.get("fetched_at"),
        "expires_at": row.get("expires_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


async def fetch_celestial_vectors_cache_entry(
    session: AsyncSession,
    command: str,
    epoch_bucket_utc: datetime,
    past_hours: int,
    future_hours: int,
    step_minutes: int,
    valid_only: bool = True,
    as_of: Optional[datetime] = None,
) -> dict:
    """Fetch one cached vectors row by unique lookup key."""
    try:
        now_utc = as_of or datetime.now(timezone.utc)
        stmt = select(CelestialVectorsCache).where(
            CelestialVectorsCache.command == command,
            CelestialVectorsCache.epoch_bucket_utc == epoch_bucket_utc,
            CelestialVectorsCache.past_hours == int(past_hours),
            CelestialVectorsCache.future_hours == int(future_hours),
            CelestialVectorsCache.step_minutes == int(step_minutes),
        )
        if valid_only:
            stmt = stmt.where(CelestialVectorsCache.expires_at >= now_utc)
        stmt = stmt.order_by(CelestialVectorsCache.fetched_at.desc())

        result = await session.execute(stmt)
        row = result.scalars().first()
        if not row:
            return {"success": True, "data": None, "error": None}

        return {"success": True, "data": _normalize_entry(serialize_object(row)), "error": None}
    except Exception as e:
        logger.error(f"Error fetching celestial vectors cache entry: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def fetch_latest_celestial_vectors_cache_entry(
    session: AsyncSession,
    command: str,
    past_hours: int,
    future_hours: int,
    step_minutes: int,
    valid_only: bool = False,
    as_of: Optional[datetime] = None,
) -> dict:
    """Fetch the latest cached vectors row for command + projection window."""
    try:
        now_utc = as_of or datetime.now(timezone.utc)
        stmt = select(CelestialVectorsCache).where(
            CelestialVectorsCache.command == command,
            CelestialVectorsCache.past_hours == int(past_hours),
            CelestialVectorsCache.future_hours == int(future_hours),
            CelestialVectorsCache.step_minutes == int(step_minutes),
        )
        if valid_only:
            stmt = stmt.where(CelestialVectorsCache.expires_at >= now_utc)
        stmt = stmt.order_by(
            CelestialVectorsCache.epoch_bucket_utc.desc(),
            CelestialVectorsCache.fetched_at.desc(),
        )

        result = await session.execute(stmt)
        row = result.scalars().first()
        if not row:
            return {"success": True, "data": None, "error": None}

        return {"success": True, "data": _normalize_entry(serialize_object(row)), "error": None}
    except Exception as e:
        logger.error(f"Error fetching latest celestial vectors cache entry: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def fetch_latest_celestial_vectors_cache_entry_for_command(
    session: AsyncSession,
    command: str,
    valid_only: bool = False,
    as_of: Optional[datetime] = None,
) -> dict:
    """Fetch the latest cached vectors row for a command regardless of projection options."""
    try:
        now_utc = as_of or datetime.now(timezone.utc)
        stmt = select(CelestialVectorsCache).where(
            CelestialVectorsCache.command == command,
        )
        if valid_only:
            stmt = stmt.where(CelestialVectorsCache.expires_at >= now_utc)
        stmt = stmt.order_by(
            CelestialVectorsCache.fetched_at.desc(),
            CelestialVectorsCache.epoch_bucket_utc.desc(),
        )

        result = await session.execute(stmt)
        row = result.scalars().first()
        if not row:
            return {"success": True, "data": None, "error": None}

        return {"success": True, "data": _normalize_entry(serialize_object(row)), "error": None}
    except Exception as e:
        logger.error(f"Error fetching latest celestial vectors cache entry by command: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def upsert_celestial_vectors_cache_entry(
    session: AsyncSession,
    data: Dict[str, Any],
) -> dict:
    """Insert or update a cached vectors row by its unique lookup key."""
    try:
        command = str(data.get("command") or "").strip()
        epoch_bucket_utc = data.get("epoch_bucket_utc")
        payload = data.get("payload")
        if not command:
            return {"success": False, "error": "command is required"}
        if not isinstance(epoch_bucket_utc, datetime):
            return {"success": False, "error": "epoch_bucket_utc datetime is required"}
        if payload is None:
            return {"success": False, "error": "payload is required"}

        past_hours = int(data.get("past_hours", 24))
        future_hours = int(data.get("future_hours", 24))
        step_minutes = int(data.get("step_minutes", 60))
        now_utc = datetime.now(timezone.utc)
        insert_values = {
            "id": str(data.get("id") or uuid.uuid4()),
            "command": command,
            "epoch_bucket_utc": epoch_bucket_utc,
            "past_hours": past_hours,
            "future_hours": future_hours,
            "step_minutes": step_minutes,
            "payload": payload,
            "source": str(data.get("source") or "horizons"),
            "error": data.get("error"),
            "fetched_at": data.get("fetched_at") or now_utc,
            "expires_at": data.get("expires_at"),
            "created_at": now_utc,
            "updated_at": now_utc,
        }

        stmt = sqlite_insert(CelestialVectorsCache).values(**insert_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                CelestialVectorsCache.command,
                CelestialVectorsCache.epoch_bucket_utc,
                CelestialVectorsCache.past_hours,
                CelestialVectorsCache.future_hours,
                CelestialVectorsCache.step_minutes,
            ],
            set_={
                "payload": insert_values["payload"],
                "source": insert_values["source"],
                "error": insert_values["error"],
                "fetched_at": insert_values["fetched_at"],
                "expires_at": insert_values["expires_at"],
                "updated_at": now_utc,
            },
        )
        await session.execute(stmt)
        await session.commit()

        result = await session.execute(
            select(CelestialVectorsCache).where(
                CelestialVectorsCache.command == command,
                CelestialVectorsCache.epoch_bucket_utc == epoch_bucket_utc,
                CelestialVectorsCache.past_hours == past_hours,
                CelestialVectorsCache.future_hours == future_hours,
                CelestialVectorsCache.step_minutes == step_minutes,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return {"success": False, "error": "Upsert completed but row was not found"}
        return {"success": True, "data": _normalize_entry(serialize_object(row)), "error": None}
    except Exception as e:
        await session.rollback()
        logger.error(f"Error upserting celestial vectors cache entry: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}
