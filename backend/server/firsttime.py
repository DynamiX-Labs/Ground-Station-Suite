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

"""First-time initialization logic for new database setup."""

import asyncio
import random
import string

from common.logger import logger
from db import AsyncSessionLocal
from db.models import OrbitalSources
from tasks.registry import get_task

# Orbital sync is now handled by background task manager
# from tlesync.logic import synchronize_satellite_data


async def first_time_initialization():
    """Function called on first server start to populate database with default data."""
    logger.info("Filling in initial data like orbital sources and default location...")
    async with AsyncSessionLocal() as session:
        try:

            def generate_identifier(length=16):
                """Generate a random identifier similar to what the CRUD does."""
                return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

            logger.info("FIRSTTIME - Populating database with default data...")
            # Add default orbital sources
            default_sources = [
                (
                    "Cubesats",
                    "https://celestrak.org/NORAD/elements/gp.php?GROUP=cubesat&FORMAT=omm",
                    "omm",
                ),
                (
                    "Amateur",
                    "https://celestrak.org/NORAD/elements/gp.php?GROUP=amateur&FORMAT=omm",
                    "omm",
                ),
                (
                    "Space stations",
                    "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=omm",
                    "omm",
                ),
                (
                    "Weather",
                    "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=omm",
                    "omm",
                ),
                (
                    "TinyGS",
                    "https://api.tinygs.com/v1/tinygs_supported.txt",
                    "3le",
                ),
            ]

            for source_name, source_url, source_format in default_sources:
                # Seed directly via ORM (without CRUD normalization), so keep adapter
                # aligned with source format for tlesync adapter dispatch.
                source_adapter = "http_omm" if source_format == "omm" else "http_3le"
                source = OrbitalSources(
                    name=source_name,
                    identifier=generate_identifier(),
                    url=source_url,
                    format=source_format,
                    adapter=source_adapter,
                )
                session.add(source)

            # System groups are created and updated by orbital sync based on
            # current source contents; avoid pre-seeding curated duplicates here.

            await session.commit()
            logger.info(
                "Initial data populated successfully with default orbital sources: "
                "Cubesats, Amateur, Space stations, Weather, TinyGS."
            )

        except Exception as e:
            logger.error(f"Error populating initial data: {e}")
            await session.rollback()
            raise


async def run_initial_sync(background_task_manager):
    """
    Run the initial satellite data synchronization after delay as a background task.

    This runs on first-time setup after database creation to populate orbital data.
    Uses the background task manager for consistency with other sync triggers.

    Args:
        background_task_manager: BackgroundTaskManager instance
    """
    try:
        logger.info("Waiting 5 seconds before starting initial synchronization...")
        await asyncio.sleep(5)
        logger.info("Starting initial satellite data synchronization as background task...")

        # Get the orbital sync task function
        orbital_sync_task = get_task("orbital_sync")

        # Start as background task
        task_id = await background_task_manager.start_task(
            func=orbital_sync_task,
            args=(),
            kwargs={},
            name="Initial Orbital Data Sync",
            task_id=None,
        )

        logger.info(f"Initial orbital sync started as background task: {task_id}")

    except Exception as e:
        logger.error(f"Error starting initial satellite synchronization: {e}")
        logger.exception(e)
