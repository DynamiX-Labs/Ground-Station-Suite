"""Background task scheduler for the ground station."""

import logging
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import observations.events as obs_events
from celestial.scene import refresh_monitored_celestial_vectors_cache
from common.arguments import arguments
from common.logger import logger
from db import AsyncSessionLocal
from observations.constants import DEFAULT_AUTO_GENERATE_INTERVAL_HOURS
from observations.generator import generate_observations_for_monitored_satellites
from tasks.registry import get_task

# Suppress apscheduler internal INFO logs (only show warnings and errors)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


async def sync_satellite_data_job(background_task_manager):
    """
    Job wrapper for orbital synchronization that uses the background task manager.

    This runs orbital sync as a background task, making it:
    - Visible in the task manager UI
    - Cancellable by users
    - Consistent with manual sync triggers
    """
    try:
        logger.info("Running scheduled satellite data synchronization as background task...")

        # Get the orbital sync task function
        orbital_sync_task = get_task("orbital_sync")

        # Start as background task
        task_id = await background_task_manager.start_task(
            func=orbital_sync_task,
            args=(),
            kwargs={},
            name="Scheduled Orbital Data Sync",
            task_id=None,
        )

        logger.info(f"Scheduled orbital sync started as background task: {task_id}")

    except ValueError as e:
        # Singleton task already running (likely a manual sync is in progress)
        logger.info(f"Skipping scheduled orbital sync: {e}")

    except Exception as e:
        logger.error(f"Error starting scheduled satellite synchronization: {e}")
        logger.exception(e)


def check_and_restart_decoders_job(process_manager):
    """Job to check decoder health and restart if needed."""
    try:
        restarted = process_manager.decoder_manager.check_and_restart_decoders()
        if restarted > 0:
            logger.info(f"Decoder health check: {restarted} decoder(s) restarted")
    except Exception as e:
        logger.error(f"Error during decoder health check: {e}")
        logger.exception(e)


async def generate_observations_job():
    """Job to automatically generate scheduled observations from monitored satellites."""
    try:
        logger.info("Running automatic observation generation...")
        async with AsyncSessionLocal() as session:
            result = await generate_observations_for_monitored_satellites(session)

            if result["success"]:
                stats = result.get("data", {})
                logger.info(
                    f"Automatic observation generation completed: "
                    f"{stats.get('generated', 0)} created, "
                    f"{stats.get('updated', 0)} updated, "
                    f"{stats.get('skipped', 0)} skipped, "
                    f"{stats.get('satellites_processed', 0)} satellites processed"
                )

                # Emit event to all clients if observations were changed
                if stats.get("generated", 0) > 0 or stats.get("updated", 0) > 0:
                    await obs_events.emit_scheduled_observations_changed()

                    # Sync all observations to APScheduler
                    if obs_events.observation_sync:
                        sync_result = await obs_events.observation_sync.sync_all_observations()
                        if sync_result["success"]:
                            sync_stats = sync_result.get("stats", {})
                            logger.info(
                                f"APScheduler sync complete: {sync_stats.get('scheduled', 0)} scheduled"
                            )
            else:
                logger.error(f"Automatic observation generation failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error during automatic observation generation: {e}")
        logger.exception(e)


async def run_initial_observation_generation():
    """Run observation generation once on startup."""
    try:
        logger.info("Running initial observation generation on startup...")
        async with AsyncSessionLocal() as session:
            result = await generate_observations_for_monitored_satellites(session)

            if result["success"]:
                stats = result.get("data", {})
                logger.info(
                    f"Initial observation generation completed: "
                    f"{stats.get('generated', 0)} created, "
                    f"{stats.get('updated', 0)} updated, "
                    f"{stats.get('skipped', 0)} skipped, "
                    f"{stats.get('satellites_processed', 0)} satellites processed"
                )

                # Emit event to all clients if observations were changed
                if stats.get("generated", 0) > 0 or stats.get("updated", 0) > 0:
                    await obs_events.emit_scheduled_observations_changed()

                # Note: Sync to APScheduler is handled by startup.py after this completes
            else:
                logger.error(f"Initial observation generation failed: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error during initial observation generation: {e}")
        logger.exception(e)


async def sync_celestial_vectors_cache_job():
    """Periodic cache-fill job that prefetches monitored mission vectors from Horizons."""
    try:
        result = await refresh_monitored_celestial_vectors_cache(logger=logger)
        if result.get("success"):
            logger.info(
                "Scheduled celestial vectors sync completed: refreshed=%s failed=%s count=%s",
                result.get("refreshed", 0),
                result.get("failed", 0),
                result.get("count", 0),
            )
            return
        if result.get("skipped"):
            logger.info("Scheduled celestial vectors sync skipped: %s", result.get("error"))
            return
        logger.warning(
            "Scheduled celestial vectors sync completed with errors: %s", result.get("error")
        )
    except Exception as e:
        logger.error(f"Error during scheduled celestial vectors sync: {e}")
        logger.exception(e)


def start_scheduler(sio, process_manager, background_task_manager):
    """Initialize and start the background task scheduler."""
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already started")
        return scheduler

    scheduler = AsyncIOScheduler()

    # Schedule satellite data synchronization every 24 hours
    scheduler.add_job(
        sync_satellite_data_job,
        trigger=IntervalTrigger(hours=24),
        args=[background_task_manager],
        id="sync_satellite_data",
        name="Synchronize satellite data",
        replace_existing=True,
    )

    # Schedule decoder health check every 60 seconds as a safety net
    # Primary restart mechanism is event-driven via data_queue (immediate response)
    # This is a backup in case message delivery fails
    scheduler.add_job(
        check_and_restart_decoders_job,
        trigger=IntervalTrigger(seconds=60),
        args=[process_manager],
        id="check_restart_decoders",
        name="Check and restart decoders (fallback)",
        replace_existing=True,
    )

    # Schedule automatic observation generation
    # Default: every 12 hours (configurable via preferences)
    scheduler.add_job(
        generate_observations_job,
        trigger=IntervalTrigger(hours=DEFAULT_AUTO_GENERATE_INTERVAL_HOURS),
        id="generate_observations",
        name="Generate scheduled observations",
        replace_existing=True,
    )

    celestial_sync_enabled = bool(getattr(arguments, "celestial_periodic_sync_enabled", True))
    try:
        celestial_sync_interval_minutes = int(
            getattr(arguments, "celestial_periodic_sync_interval_minutes", 60)
        )
    except (TypeError, ValueError):
        celestial_sync_interval_minutes = 60
    celestial_sync_interval_minutes = max(5, celestial_sync_interval_minutes)
    if celestial_sync_enabled:
        # Run once immediately at startup, then continue at the configured interval.
        scheduler.add_job(
            sync_celestial_vectors_cache_job,
            trigger=IntervalTrigger(minutes=celestial_sync_interval_minutes),
            id="sync_celestial_vectors_cache",
            name="Synchronize celestial vectors cache",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            next_run_time=datetime.now(timezone.utc),
        )

    scheduler.start()

    # Consolidated startup log with job details
    jobs = scheduler.get_jobs()
    job_count = len(jobs)
    logger.info(
        f"Background task scheduler started: {job_count} job{'s' if job_count != 1 else ''} scheduled"
    )
    for job in jobs:
        # Format next run time without microseconds for cleaner display
        next_run = (
            job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z") if job.next_run_time else "N/A"
        )
        logger.info(f"  - {job.name} → next run: {next_run}")

    return scheduler


def stop_scheduler():
    """Stop the background task scheduler."""
    global scheduler

    if scheduler is None:
        return

    logger.info("Stopping background task scheduler...")
    scheduler.shutdown(wait=False)
    scheduler = None
    logger.info("Background task scheduler stopped")
