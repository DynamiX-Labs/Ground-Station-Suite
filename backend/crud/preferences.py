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
from datetime import datetime, timezone
from typing import List, Union

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.common import logger, serialize_object
from db.models import Preferences, TrackingState


async def fetch_preference(session: AsyncSession, preference_id: Union[uuid.UUID, str]) -> dict:
    """
    Fetch a single preference by its UUID.
    """
    try:
        # Convert to UUID if it's a string
        if isinstance(preference_id, str):
            preference_id = uuid.UUID(preference_id)

        stmt = select(Preferences).filter(Preferences.id == preference_id)
        result = await session.execute(stmt)
        preference = result.scalar_one_or_none()
        preference = serialize_object(preference)
        return {"success": True, "data": preference, "error": None}

    except Exception as e:
        logger.error(f"Error fetching a preference users: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def fetch_all_preferences(session: AsyncSession) -> dict:
    """
    Fetch all preferences from the database.
    If a preference does not exist for a key in the defaults, use the default value.
    """

    defaults = {
        "timezone": "Europe/Athens",
        "locale": "browser",  # Locale for date/time/number formatting (e.g., en-US, en-GB, el-GR)
        "language": "en_US",
        "theme": "auto",
        "celestial_enabled": "false",
        "stadia_maps_api_key": "",
        "toast_position": "bottom-center",
        "gemini_api_key": "",  # Google Gemini API key for transcription
        "deepgram_api_key": "",  # Deepgram API key for transcription
        "google_translate_api_key": "",  # Google Cloud Translation API key for translating Deepgram transcriptions
    }

    try:
        stmt = select(Preferences)
        result = await session.execute(stmt)
        preferences = result.scalars().all()

        # Create a dictionary mapping name to the full preference object
        preferences_map = {pref.name: pref for pref in preferences}

        # Combine defaults with existing preferences
        combined_preferences = [
            {
                "id": preferences_map[key].id if key in preferences_map else None,
                "name": key,
                "value": preferences_map[key].value if key in preferences_map else value,
            }
            for key, value in defaults.items()
        ]

        combined_preferences = serialize_object(combined_preferences)
        return {"success": True, "data": combined_preferences, "error": None}

    except Exception as e:
        logger.error(f"Error fetching preferences: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def add_preference(session: AsyncSession, data: dict) -> dict:
    """
    Create and add a new preference record.
    """
    try:
        new_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        stmt = (
            insert(Preferences)
            .values(
                id=new_id,
                name=data["name"],
                value=data["value"],
                added=now,
                updated=now,
            )
            .returning(Preferences)
        )
        result = await session.execute(stmt)
        await session.commit()
        new_preference = result.scalar_one()
        new_preference = serialize_object(new_preference)
        return {"success": True, "data": new_preference, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error adding a preference: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def edit_preference(session: AsyncSession, data: dict) -> dict:
    """
    Edit an existing preference record by updating provided fields.
    """
    try:
        # extract preference_id from data
        preference_id = data.pop("id", None)
        if not preference_id:
            raise ValueError("Preference id cannot be empty.")

        if isinstance(preference_id, str):
            preference_id = uuid.UUID(preference_id)

        # Confirm the preference exists first
        stmt = select(Preferences).filter(Preferences.id == preference_id)
        result = await session.execute(stmt)
        preference = result.scalar_one_or_none()
        if not preference:
            return {"success": False, "error": f"Preference with id {preference_id} not found."}

        # Update the timestamp
        data["updated"] = datetime.now(timezone.utc)

        upd_stmt = (
            update(Preferences)
            .where(Preferences.id == preference_id)
            .values(**data)
            .returning(Preferences)
        )
        upd_result = await session.execute(upd_stmt)
        await session.commit()
        updated_preference = upd_result.scalar_one_or_none()
        updated_preference = serialize_object(updated_preference)
        return {"success": True, "data": updated_preference, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error editing a preference: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def set_preferences(session: AsyncSession, preferences: List[dict]) -> dict:
    """
    Edit or upsert preference records for provided fields.
    """
    try:
        updated_preferences = []

        for data in preferences:
            preference_id = data.pop("id", None)
            preference_name = data.get("name")

            if not preference_name:
                raise ValueError("Preference name is required")

            if preference_id:
                if isinstance(preference_id, str):
                    preference_id = uuid.UUID(preference_id)

                # Confirm the preference exists by ID
                stmt = select(Preferences).filter(Preferences.id == preference_id)
                result = await session.execute(stmt)
                preference = result.scalar_one_or_none()

                if preference:
                    # Update existing preference
                    data.pop("added", None)
                    data["updated"] = datetime.now(timezone.utc)
                    upd_stmt = (
                        update(Preferences)
                        .where(Preferences.id == preference_id)
                        .values(**data)
                        .returning(Preferences)
                    )
                    upd_result = await session.execute(upd_stmt)
                    updated_preferences.append(upd_result.scalar_one_or_none())

                else:
                    # Check if a preference with this name already exists
                    stmt = select(Preferences).filter(Preferences.name == preference_name)
                    result = await session.execute(stmt)
                    existing_by_name = result.scalar_one_or_none()

                    if existing_by_name:
                        # Update the existing preference by name
                        data.pop("added", None)
                        data["updated"] = datetime.now(timezone.utc)
                        upd_stmt = (
                            update(Preferences)
                            .where(Preferences.name == preference_name)
                            .values(**data)
                            .returning(Preferences)
                        )
                        upd_result = await session.execute(upd_stmt)
                        updated_preferences.append(upd_result.scalar_one_or_none())
                    else:
                        # Insert a new preference (upsert case)
                        now = datetime.now(timezone.utc)
                        data["id"] = preference_id
                        data["added"] = now
                        data["updated"] = now
                        stmt = insert(Preferences).values(**data).returning(Preferences)
                        result = await session.execute(stmt)
                        updated_preferences.append(result.scalar_one())

            else:
                # No ID provided - check if preference exists by name
                stmt = select(Preferences).filter(Preferences.name == preference_name)
                result = await session.execute(stmt)
                existing_by_name = result.scalar_one_or_none()

                if existing_by_name:
                    # Update the existing preference
                    data.pop("added", None)
                    data["updated"] = datetime.now(timezone.utc)
                    upd_stmt = (
                        update(Preferences)
                        .where(Preferences.name == preference_name)
                        .values(**data)
                        .returning(Preferences)
                    )
                    upd_result = await session.execute(upd_stmt)
                    updated_preferences.append(upd_result.scalar_one_or_none())
                else:
                    # Insert a new preference
                    new_id = uuid.uuid4()
                    now = datetime.now(timezone.utc)
                    data["id"] = new_id
                    data["added"] = now
                    data["updated"] = now
                    stmt = insert(Preferences).values(**data).returning(Preferences)
                    result = await session.execute(stmt)
                    updated_preferences.append(result.scalar_one())

        await session.commit()
        updated_preferences = serialize_object(updated_preferences)
        return {"success": True, "data": updated_preferences, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error setting multiple preferences: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def delete_preference(session: AsyncSession, preference_id: Union[uuid.UUID, str]) -> dict:
    """
    Delete a preference record by its UUID.
    """
    try:
        # Convert to UUID if it's a string
        if isinstance(preference_id, str):
            preference_id = uuid.UUID(preference_id)

        stmt = delete(Preferences).where(Preferences.id == preference_id).returning(Preferences)
        result = await session.execute(stmt)
        deleted = result.scalar_one_or_none()
        if not deleted:
            return {"success": False, "error": f"Preference with id {preference_id} not found."}
        await session.commit()
        return {"success": True, "data": None, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting a preference: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


async def set_map_settings(session: AsyncSession, data: dict) -> dict:
    """
    Updates satellite tracking state or inserts new settings into the database.

    This function handles updating settings for satellite tracking by name. If a
    record with the given name exists, it will update the existing record. Otherwise,
    it will insert a new record with the provided data. The updated/created record
    is serialized and returned alongside the success status. In case of errors,
    a failure status and error message are returned, and the transaction is rolled back.

    :param session:
        An AsyncSession instance for handling database operations.
    :param data:
        A dictionary containing the satellite tracking settings to set. The keys
        must include 'name' and 'value'. Additional keys will be used to update
        or insert the record.
    :return:
        A dictionary containing the success status, serialized record data if
        successful, and error information in case of failure.
    """
    try:
        assert data.get("name", None) is not None, "name is required when setting map settings"
        assert data.get("value", None) is not None, "value is required when setting map settings"

        now = datetime.now(timezone.utc)
        data["updated"] = now

        existing_rows_result = await session.execute(
            select(TrackingState).where(TrackingState.name == data["name"])
        )
        existing_rows = existing_rows_result.scalars().all()
        existing_record = None
        duplicate_ids = []

        if existing_rows:
            # Keep the most recently updated row as canonical and remove duplicates.
            ordered = sorted(
                existing_rows,
                key=lambda row: row.updated
                or row.added
                or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            existing_record = ordered[0]
            duplicate_ids = [row.id for row in ordered[1:]]
            if duplicate_ids:
                await session.execute(
                    delete(TrackingState).where(TrackingState.id.in_(duplicate_ids))
                )
                logger.warning(
                    f"Removed {len(duplicate_ids)} duplicate tracking_state rows for name='{data['name']}'"
                )

        if existing_record:
            for key, value in data.items():
                setattr(existing_record, key, value)
            new_record = existing_record
        else:
            new_record = TrackingState(**data)

        await session.merge(new_record)
        await session.commit()
        new_record = serialize_object(new_record)
        return {"success": True, "data": new_record, "error": None}

    except Exception as e:
        await session.rollback()
        logger.error(f"Error storing map settings: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "data": None, "error": str(e)}


async def get_map_settings(session: AsyncSession, name: str) -> dict:
    """
    Retrieve map settings for the given name.

    This asynchronous function queries the database to fetch the map
    settings related to satellite tracking state. If data is successfully
    retrieved, it returns the settings in a structured format. If no data is
    found, an empty dictionary is provided. In case of an error during
    execution, the function logs the error and returns a failure response.

    :param session: Database session instance to execute queries
    :param name: The name identifier related to the map settings
    :return: A dictionary containing either the map settings 'data'
        or an empty dictionary and a 'success' status indicating
        the operation's outcome
    """
    try:
        # Query map settings from the database using the provided name
        map_settings = await session.execute(
            select(TrackingState).where(TrackingState.name == name)
        )
        map_settings_rows = map_settings.scalars().all()

        if not map_settings_rows:
            return {"success": True, "data": {}}

        ordered = sorted(
            map_settings_rows,
            key=lambda row: row.updated or row.added or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        map_settings_row = ordered[0]

        # Best-effort cleanup of duplicates for this key.
        duplicate_ids = [row.id for row in ordered[1:]]
        if duplicate_ids:
            await session.execute(delete(TrackingState).where(TrackingState.id.in_(duplicate_ids)))
            await session.commit()
            logger.warning(
                f"Removed {len(duplicate_ids)} duplicate tracking_state rows while reading name='{name}'"
            )

        map_settings_row = serialize_object(map_settings_row)
        return {"success": True, "data": map_settings_row}

    except Exception as e:
        logger.error(f"Error retrieving map settings: {str(e)}")
        logger.exception(e)
        return {"success": False, "data": {}, "error": str(e)}
