# Copyright (c) 2025 Efstratios Goudelis
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

import traceback
import uuid
from typing import List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.common import logger, serialize_object
from common.utils import convert_strings_to_uuids
from db.models import Groups


async def fetch_system_satellite_group_by_identifier(
    session: AsyncSession, group_identifier: str
) -> dict:
    """
    Fetch a satellite group with type='system' by its 'group_identifier'.
    """

    try:
        # Add a filter for the 'type' column
        stmt = select(Groups).filter(
            Groups.identifier == group_identifier,
            Groups.type == "system",
        )
        result = await session.execute(stmt)
        group = result.scalar_one_or_none()

        if not group:
            return {"success": False, "error": "Satellite group (type=system) not found"}

        group = serialize_object(group)
        return {"success": True, "data": group, "error": None}

    except Exception as e:
        logger.error(f"Error fetching satellite group by identifier: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def fetch_satellite_group(
    session: AsyncSession,
    group_id: Optional[Union[str, uuid.UUID]] = None,
    group_type: Optional[str] = None,
) -> dict:
    """
    Fetch satellite group records.

    If 'group_id' is provided, returns one satellite group record
    (optionally filtering by 'group_type' if given).
    Otherwise, returns all satellite group records (optionally filtered by 'group_type').
    """

    try:
        # if no group_id is given, return all groups (possibly filtered by group_type)
        if group_id is None:
            if group_type is not None:
                stmt = select(Groups).where(Groups.type == group_type)
            else:
                stmt = select(Groups)

            result = await session.execute(stmt)
            groups = result.scalars().all()
            groups = [serialize_object(g) for g in groups]
            return {"success": True, "data": groups, "error": None}

        else:
            if isinstance(group_id, str):
                group_id = uuid.UUID(group_id)

            stmt = select(Groups).where(Groups.id == group_id)
            if group_type is not None:
                stmt = stmt.where(Groups.type == group_type)

            result = await session.execute(stmt)
            group = result.scalars().first()

            group = serialize_object(group) if group else None
            return {"success": True, "data": group, "error": None}

    except Exception as e:
        logger.error(f"Error fetching satellite groups: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "data": None, "error": str(e)}


async def add_satellite_group(session: AsyncSession, data: dict) -> dict:
    """
    Add a new satellite group record.
    """
    try:
        assert "name" in data, "Name is required."

        group = Groups(**data)
        session.add(group)
        await session.commit()
        group = serialize_object(group)
        return {"success": True, "data": group, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error adding satellite groups: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "data": None, "error": str(e)}


async def edit_satellite_group(session: AsyncSession, satellite_group_id: str, data: dict) -> dict:
    """
    Edit an existing satellite group record.
    """
    try:
        # Remove 'id' from data if it exists
        data.pop("id", None)
        satellite_group_uuid = uuid.UUID(satellite_group_id)

        result = await session.execute(select(Groups).filter(Groups.id == satellite_group_uuid))
        group = result.scalars().first()

        if not group:
            return {"success": False, "data": None, "error": "Satellite group not found."}

        for key, value in data.items():
            setattr(group, key, value)

        await session.commit()
        group = serialize_object(group)
        return {"success": True, "data": group, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error editing satellite groups: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "data": None, "error": str(e)}


async def delete_satellite_group(
    session: AsyncSession, satellite_group_ids: Union[List[str], dict]
) -> dict:
    """
    Delete satellite group record(s).
    """
    try:
        satellite_group_ids = convert_strings_to_uuids(satellite_group_ids)
        result = await session.execute(select(Groups).filter(Groups.id.in_(satellite_group_ids)))
        groups = result.scalars().all()

        if not groups:
            return {"success": False, "data": None, "error": "Satellite group not found."}

        for group in groups:
            await session.delete(group)

        await session.commit()
        return {"success": True, "data": None, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting satellite groups: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "data": None, "error": str(e)}
