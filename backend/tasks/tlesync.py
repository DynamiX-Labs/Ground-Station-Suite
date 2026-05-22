"""
Orbital data synchronization background task.

This task synchronizes satellite orbital data from configured sources (e.g., Celestrak)
and satellite/transmitter metadata from SATNOGS. It's designed to run as a background
task with comprehensive progress reporting.
"""

import asyncio
import logging
import multiprocessing
import signal
import sys
from multiprocessing import Queue
from typing import Optional

try:
    import setproctitle

    HAS_SETPROCTITLE = True
except ImportError:
    HAS_SETPROCTITLE = False

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db import create_subprocess_engine
from tlesync.logic import synchronize_satellite_data_internal

logger = logging.getLogger("tlesync-task")


class GracefulKiller:
    """Handle SIGTERM gracefully within the process."""

    def __init__(self):
        self.kill_now = False
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGINT, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True


def orbital_sync_background_task(_progress_queue: Optional[Queue] = None):
    """
    Synchronize orbital and satellite data as a background task.

    This task:
    - Fetches orbital data from configured sources (Celestrak, etc.)
    - Fetches satellite metadata from SATNOGS
    - Fetches transmitter data from SATNOGS
    - Updates the database with all changes
    - Tracks newly added, modified, and removed satellites/transmitters
    - Reports detailed progress via queue

    Args:
        _progress_queue: Queue for sending progress updates (injected by manager)

    Returns:
        Dict with synchronization results and statistics
    """
    # Set process name
    if HAS_SETPROCTITLE:
        setproctitle.setproctitle("DynamiX-Labs - Orbital-Sync")
    multiprocessing.current_process().name = "DynamiX-Labs - Orbital-Sync"

    killer = GracefulKiller()

    if _progress_queue:
        _progress_queue.put(
            {
                "type": "output",
                "output": "Starting orbital data synchronization...",
                "stream": "stdout",
                "progress": 0,
            }
        )

    # Create new event loop for this process
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Configure logging for this subprocess
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stdout,
        )

        async def run_sync():
            """Run the actual synchronization with progress callbacks."""
            try:
                # Create a new engine for this subprocess to avoid sharing connections
                subprocess_engine = create_subprocess_engine()
                SubprocessSessionLocal = async_sessionmaker(
                    bind=subprocess_engine, expire_on_commit=False, class_=AsyncSession
                )

                async with SubprocessSessionLocal() as session:
                    # Create progress callback that forwards state to queue
                    def emit_callback(state):
                        """
                        Callback function to emit state updates.

                        This replaces the direct sio.emit() calls in the original function.
                        """
                        if killer.kill_now:
                            raise InterruptedError("Orbital sync cancelled by user")

                        if _progress_queue:
                            # Send the complete sync state to the manager
                            _progress_queue.put(
                                {
                                    "type": "orbital_sync_state",
                                    "state": state,
                                    "progress": state.get("progress", 0),
                                }
                            )

                    # Run the synchronization with our callback
                    # Use logger (local) instead of main_logger (from parent process)
                    await synchronize_satellite_data_internal(session, logger, emit_callback)
            except Exception as e:
                logger.error(f"Error in run_sync: {e}", exc_info=True)
                raise

        # Execute the sync
        loop.run_until_complete(run_sync())

        if _progress_queue:
            _progress_queue.put(
                {
                    "type": "output",
                    "output": "Orbital data synchronization completed successfully",
                    "stream": "stdout",
                    "progress": 100,
                }
            )

        return {"status": "completed"}

    except InterruptedError as e:
        # User cancelled the task
        if _progress_queue:
            _progress_queue.put(
                {
                    "type": "output",
                    "output": f"Orbital data synchronization cancelled: {str(e)}",
                    "stream": "stdout",
                }
            )
        return {"status": "cancelled"}

    except Exception as e:
        error_msg = f"Orbital data synchronization failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if _progress_queue:
            _progress_queue.put({"type": "error", "error": error_msg, "stream": "stderr"})
        # Don't re-raise - let the manager handle it through the queue
        return {"status": "failed", "error": str(e)}

    finally:
        loop.close()


# Backward-compatible alias for legacy callers/registry keys.
tle_sync_background_task = orbital_sync_background_task
