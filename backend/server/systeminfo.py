"""
Background task to emit live system information over Socket.IO.

This module follows the same startup task pattern used elsewhere: expose a
single `start_system_info_emitter(sio, background_tasks)` function that
registers an asyncio.Task into the provided `background_tasks` set.
"""

import asyncio
import os
from typing import Set

from common.constants import SocketEvents
from common.logger import logger
from server.version import get_system_info


def start_system_info_emitter(sio, background_tasks: Set[asyncio.Task]) -> asyncio.Task:
    """Start the live system-info emitter loop and register it in background_tasks.

    Emits `SocketEvents.SYSTEM_INFO` every N seconds (default 2) when at least
    one client is connected. Uses a non-blocking CPU percent calculation and
    includes load averages and CPU temperature when available.
    """

    async def _system_info_loop():
        interval = int(os.environ.get("SYSTEM_INFO_POLL_INTERVAL_SECONDS", 2))

        # Prime non-blocking CPU percent sequence (first call returns 0.0)
        try:
            _ = get_system_info(nonblocking_cpu=True)
        except Exception:
            pass

        while True:
            try:
                # Determine if there are any connected clients using the Socket.IO manager
                try:
                    participants = sio.manager.get_participants("/", None)
                    has_clients = any(True for _ in participants)
                except Exception:
                    has_clients = False

                if has_clients:
                    payload = get_system_info(
                        include_load_avg=True,
                        include_cpu_temp=True,
                        nonblocking_cpu=True,
                    )
                    await sio.emit(SocketEvents.SYSTEM_INFO, payload)

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"System info emitter error: {e}")
                await asyncio.sleep(interval)

    task = asyncio.create_task(_system_info_loop())
    background_tasks.add(task)
    logger.info("System-info emitter task started")
    return task
