# Copyright (c) 2025 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""CRUD helpers for monitored celestial targets."""

from __future__ import annotations

import colorsys
import hashlib
import re
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.common import logger, serialize_object
from db.models import MonitoredCelestial

UNIQUE_CONSTRAINT_PATTERN = re.compile(r"UNIQUE constraint failed: \w+\.(\w+)")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
DEFAULT_CELESTIAL_COLOR_PALETTE = [
    "#FF6B6B",
    "#4ECDC4",
    "#45B7D1",
    "#F7B801",
    "#6A4C93",
    "#2EC4B6",
    "#E71D36",
    "#A1C349",
    "#5E60CE",
    "#FF9F1C",
    "#3A86FF",
    "#8338EC",
]


def _normalize_color(value: Any) -> Optional[str]:
    if value is None:
        return None

    color = str(value).strip()
    if not color:
        return None

    if not HEX_COLOR_PATTERN.match(color):
        raise ValueError("Color must be a valid hex value like #1A2B3C")

    return color.upper()


def _hsl_to_hex(hue: float, saturation: float, lightness: float) -> str:
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return f"#{int(red * 255):02X}{int(green * 255):02X}{int(blue * 255):02X}"


def _deterministic_color_from_command(command: str, salt: int = 0) -> str:
    digest = hashlib.sha1(f"{command}:{salt}".encode("utf-8")).hexdigest()
    hue = (int(digest[0:8], 16) % 360) / 360.0
    saturation = 0.72
    lightness = 0.56
    return _hsl_to_hex(hue, saturation, lightness)


async def _pick_color_for_new_target(session: AsyncSession, command: str) -> str:
    result = await session.execute(select(MonitoredCelestial.color))
    rows = result.scalars().all()
    used = {
        str(color).strip().upper()
        for color in rows
        if color and HEX_COLOR_PATTERN.match(str(color).strip())
    }

    for candidate in DEFAULT_CELESTIAL_COLOR_PALETTE:
        if candidate not in used:
            return candidate

    for salt in range(0, 64):
        generated = _deterministic_color_from_command(command, salt=salt)
        if generated not in used:
            return generated

    return _deterministic_color_from_command(command, salt=128)


def _normalize_entry(row: dict) -> dict:
    target_type = str(row.get("target_type") or "mission").strip().lower() or "mission"
    command = row.get("command")
    body_id = row.get("body_id")
    target_key = ""
    if target_type == "body":
        target_key = f"body:{body_id}" if body_id else ""
    else:
        target_key = f"mission:{command}" if command else ""
    return {
        "id": row.get("id"),
        "target_type": target_type,
        "target_key": target_key,
        "display_name": row.get("display_name") or "",
        "command": command or "",
        "body_id": body_id or "",
        "color": row.get("color"),
        "enabled": bool(row.get("enabled", True)),
        "last_refresh_at": row.get("last_refresh_at"),
        "last_error": row.get("last_error"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


async def fetch_monitored_celestial(
    session: AsyncSession,
    target_id: Optional[str] = None,
    enabled_only: bool = False,
) -> dict:
    """Fetch one monitored target by ID, or all targets."""
    try:
        if target_id:
            stmt = select(MonitoredCelestial).where(MonitoredCelestial.id == target_id)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                return {"success": True, "data": None, "error": None}
            return {
                "success": True,
                "data": _normalize_entry(serialize_object(row)),
                "error": None,
            }

        stmt = select(MonitoredCelestial)
        if enabled_only:
            stmt = stmt.where(MonitoredCelestial.enabled.is_(True))
        stmt = stmt.order_by(MonitoredCelestial.created_at)

        result = await session.execute(stmt)
        rows = result.scalars().all()
        data = [_normalize_entry(serialize_object(row)) for row in rows]
        return {"success": True, "data": data, "error": None}

    except Exception as e:
        logger.error(f"Error fetching monitored celestial targets: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def add_monitored_celestial(session: AsyncSession, data: dict) -> dict:
    """Create a monitored celestial target."""
    try:
        target_id = data.get("id") or str(uuid.uuid4())
        target_type = (
            str(data.get("target_type") or data.get("targetType") or "mission").strip().lower()
        )
        if target_type not in {"mission", "body"}:
            return {"success": False, "error": "target_type must be either 'mission' or 'body'"}

        command = str(data.get("command") or "").strip()
        body_id = str(data.get("body_id") or data.get("bodyId") or "").strip()
        default_display = body_id if target_type == "body" else command
        display_name = str(
            data.get("display_name") or data.get("displayName") or default_display
        ).strip()

        if target_type == "mission" and not command:
            return {"success": False, "error": "Command is required for mission targets"}
        if target_type == "body" and not body_id:
            return {"success": False, "error": "body_id is required for body targets"}
        if not display_name:
            return {"success": False, "error": "Display name is required"}
        try:
            color = _normalize_color(data.get("color"))
        except ValueError as exc:
            return {"success": False, "error": str(exc)}
        color_seed_key = command if target_type == "mission" else body_id
        if not color:
            color = await _pick_color_for_new_target(session, color_seed_key)

        payload = {
            "id": target_id,
            "target_type": target_type,
            "display_name": display_name,
            "command": command if target_type == "mission" else None,
            "body_id": body_id if target_type == "body" else None,
            "color": color,
            "enabled": bool(data.get("enabled", True)),
            "last_refresh_at": data.get("last_refresh_at"),
            "last_error": data.get("last_error"),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        stmt = insert(MonitoredCelestial).values(**payload).returning(MonitoredCelestial)
        result = await session.execute(stmt)
        await session.commit()

        row = result.scalar_one()
        return {
            "success": True,
            "data": _normalize_entry(serialize_object(row)),
            "error": None,
        }

    except IntegrityError as e:
        await session.rollback()
        logger.warning(f"Database integrity error creating monitored celestial target: {e}")
        error_str = str(e.orig) if hasattr(e, "orig") else str(e)
        match = UNIQUE_CONSTRAINT_PATTERN.search(error_str)
        if match and match.group(1) in {"command", "body_id"}:
            return {
                "success": False,
                "error": "A target with this command/body already exists.",
            }
        return {"success": False, "error": f"Database constraint violation: {error_str}"}
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating monitored celestial target: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def edit_monitored_celestial(session: AsyncSession, data: dict) -> dict:
    """Update a monitored celestial target."""
    try:
        target_id = data.get("id")
        if not target_id:
            return {"success": False, "error": "Target ID is required"}

        existing_stmt = select(MonitoredCelestial).where(MonitoredCelestial.id == target_id)
        existing_result = await session.execute(existing_stmt)
        existing_row = existing_result.scalar_one_or_none()
        if not existing_row:
            return {"success": False, "error": "Monitored celestial target not found"}

        existing_payload = serialize_object(existing_row)
        update_data: Dict[str, Any] = {}
        target_type = (
            str(
                data.get("target_type")
                or data.get("targetType")
                or existing_payload.get("target_type")
                or "mission"
            )
            .strip()
            .lower()
        )
        if target_type not in {"mission", "body"}:
            return {"success": False, "error": "target_type must be either 'mission' or 'body'"}
        update_data["target_type"] = target_type
        if "display_name" in data or "displayName" in data:
            update_data["display_name"] = str(
                data.get("display_name") or data.get("displayName") or ""
            ).strip()
        if "command" in data:
            update_data["command"] = str(data.get("command") or "").strip()
        if "body_id" in data or "bodyId" in data:
            update_data["body_id"] = str(data.get("body_id") or data.get("bodyId") or "").strip()
        if "color" in data:
            try:
                update_data["color"] = _normalize_color(data.get("color"))
            except ValueError as exc:
                return {"success": False, "error": str(exc)}
        if "enabled" in data:
            update_data["enabled"] = bool(data.get("enabled"))
        if "last_refresh_at" in data:
            update_data["last_refresh_at"] = data.get("last_refresh_at")
        if "last_error" in data:
            update_data["last_error"] = data.get("last_error")

        final_command = str(
            update_data.get("command", existing_payload.get("command") or "")
        ).strip()
        final_body_id = str(
            update_data.get("body_id", existing_payload.get("body_id") or "")
        ).strip()
        if target_type == "mission" and not final_command:
            return {"success": False, "error": "Command is required for mission targets"}
        if target_type == "body" and not final_body_id:
            return {"success": False, "error": "body_id is required for body targets"}
        if target_type == "mission":
            update_data["command"] = final_command
            update_data["body_id"] = None
        else:
            update_data["command"] = None
            update_data["body_id"] = final_body_id
        if "display_name" in update_data and not update_data["display_name"]:
            return {"success": False, "error": "Display name is required"}

        update_data["updated_at"] = datetime.now(timezone.utc)

        stmt = (
            update(MonitoredCelestial)
            .where(MonitoredCelestial.id == target_id)
            .values(**update_data)
            .returning(MonitoredCelestial)
        )
        result = await session.execute(stmt)
        await session.commit()

        row = result.scalar_one_or_none()
        if not row:
            return {"success": False, "error": "Monitored celestial target not found"}

        return {
            "success": True,
            "data": _normalize_entry(serialize_object(row)),
            "error": None,
        }

    except IntegrityError as e:
        await session.rollback()
        logger.warning(f"Database integrity error updating monitored celestial target: {e}")
        error_str = str(e.orig) if hasattr(e, "orig") else str(e)
        match = UNIQUE_CONSTRAINT_PATTERN.search(error_str)
        if match and match.group(1) in {"command", "body_id"}:
            return {
                "success": False,
                "error": "A target with this command/body already exists.",
            }
        return {"success": False, "error": f"Database constraint violation: {error_str}"}
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating monitored celestial target: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def delete_monitored_celestial(session: AsyncSession, ids: List[str]) -> dict:
    """Delete one or more monitored celestial targets."""
    try:
        if not ids:
            return {"success": False, "error": "IDs are required"}

        stmt = delete(MonitoredCelestial).where(MonitoredCelestial.id.in_(ids))
        result = await session.execute(stmt)
        await session.commit()

        return {
            "success": True,
            "data": {"deleted": result.rowcount or 0, "ids": ids},
            "error": None,
        }
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting monitored celestial targets: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def toggle_monitored_celestial_enabled(
    session: AsyncSession,
    target_id: str,
    enabled: bool,
) -> dict:
    """Toggle monitored celestial target enabled state."""
    try:
        stmt = (
            update(MonitoredCelestial)
            .where(MonitoredCelestial.id == target_id)
            .values(enabled=enabled, updated_at=datetime.now(timezone.utc))
        )
        result = await session.execute(stmt)
        await session.commit()

        if result.rowcount == 0:
            return {"success": False, "error": "Monitored celestial target not found"}

        return {"success": True, "data": {"id": target_id, "enabled": enabled}, "error": None}
    except Exception as e:
        await session.rollback()
        logger.error(f"Error toggling monitored celestial target: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def update_monitored_celestial_refresh_state(
    session: AsyncSession,
    updates: List[dict],
) -> dict:
    """Persist refresh timestamp/error metadata for monitored celestial targets."""
    try:
        now_utc = datetime.now(timezone.utc)
        for item in updates:
            target_id = item.get("id")
            if not target_id:
                continue

            stmt = (
                update(MonitoredCelestial)
                .where(MonitoredCelestial.id == str(target_id))
                .values(
                    last_refresh_at=item.get("last_refresh_at"),
                    last_error=item.get("last_error"),
                    updated_at=now_utc,
                )
            )
            await session.execute(stmt)

        await session.commit()
        return {"success": True, "error": None}
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating monitored celestial refresh state: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}
