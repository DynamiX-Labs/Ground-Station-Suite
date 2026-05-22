"""
Example background task for testing the multiprocessing-based background task manager.

This task:
- Runs for a specified duration (default 5 minutes)
- Emits status updates via Queue every 5 seconds
- Simulates a long-running process
- Can be interrupted gracefully

Usage (called from manager):
    await background_task_manager.start_task(
        func=example_long_task,
        args=("Task Name", 300, 5),
        name="Example Task"
    )
"""

import signal
import time
from multiprocessing import Queue
from typing import Optional


class GracefulKiller:
    """Handle SIGTERM gracefully within the process."""

    def __init__(self):
        self.kill_now = False
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGINT, self.exit_gracefully)

    def exit_gracefully(self, *args):
        self.kill_now = True


def example_long_task(
    name: str,
    duration: int = 5,
    interval: int = 1,
    fail_at: Optional[int] = None,
    _progress_queue: Optional[Queue] = None,
):
    """
    Example long-running task for testing.

    Args:
        name: Task name
        duration: Duration in seconds (default: 5)
        interval: Update interval in seconds (default: 1)
        fail_at: Fail at specific second (for testing errors)
        _progress_queue: Queue for sending progress updates (injected by manager)

    Returns:
        Dict with task completion info
    """
    killer = GracefulKiller()

    # Send initial message
    if _progress_queue:
        _progress_queue.put(
            {"type": "output", "output": f"Starting task: {name}", "stream": "stdout"}
        )
        _progress_queue.put(
            {"type": "output", "output": f"Duration: {duration} seconds", "stream": "stdout"}
        )
        _progress_queue.put(
            {"type": "output", "output": f"Update interval: {interval} seconds", "stream": "stdout"}
        )
        _progress_queue.put({"type": "output", "output": "-" * 60, "stream": "stdout"})

    start_time = time.time()
    update_count = 0

    while True:
        elapsed = time.time() - start_time

        # Check if duration is complete
        if elapsed >= duration:
            break

        if killer.kill_now:
            if _progress_queue:
                _progress_queue.put(
                    {
                        "type": "output",
                        "output": f"Task '{name}' was interrupted after {elapsed:.1f} seconds",
                        "stream": "stdout",
                    }
                )
            return {"status": "interrupted", "elapsed": elapsed, "updates": update_count}

        # Check if we should fail
        if fail_at is not None and elapsed >= fail_at:
            error_msg = f"Task '{name}' encountered an error at {elapsed:.1f} seconds!"
            if _progress_queue:
                _progress_queue.put({"type": "error", "error": error_msg, "stream": "stderr"})
            raise RuntimeError(error_msg)

        update_count += 1

        # Calculate progress
        progress_percent = min((elapsed / duration) * 100, 100)

        # Send progress updates via queue
        if _progress_queue:
            # Simulate different types of output
            if update_count % 3 == 0:
                _progress_queue.put(
                    {
                        "type": "output",
                        "output": f"Update #{update_count} | Processing frame {update_count * 100}",
                        "stream": "stdout",
                        "progress": progress_percent,
                    }
                )
            elif update_count % 3 == 1:
                _progress_queue.put(
                    {
                        "type": "output",
                        "output": f"Status: Working... | Memory: {update_count * 10}MB | CPU: {min(50 + (update_count % 30), 95)}%",
                        "stream": "stdout",
                        "progress": progress_percent,
                    }
                )
            else:
                _progress_queue.put(
                    {
                        "type": "output",
                        "output": f"Info: Processed {update_count * 50} samples | Queue size: {update_count % 10} | Active threads: 4",
                        "stream": "stdout",
                        "progress": progress_percent,
                    }
                )

            # Occasionally send warning to stderr
            if update_count % 10 == 0:
                _progress_queue.put(
                    {
                        "type": "output",
                        "output": "[WARNING] Checkpoint - Task running normally",
                        "stream": "stderr",
                        "progress": progress_percent,
                    }
                )

        # Sleep for the interval
        time.sleep(interval)

    # Task completed successfully
    elapsed = time.time() - start_time
    if _progress_queue:
        _progress_queue.put({"type": "output", "output": "-" * 60, "stream": "stdout"})
        _progress_queue.put(
            {
                "type": "output",
                "output": f"Task '{name}' completed successfully!",
                "stream": "stdout",
            }
        )
        _progress_queue.put(
            {
                "type": "output",
                "output": f"Total duration: {elapsed:.1f} seconds",
                "stream": "stdout",
            }
        )
        _progress_queue.put(
            {"type": "output", "output": f"Total updates: {update_count}", "stream": "stdout"}
        )
        _progress_queue.put(
            {"type": "output", "output": "Final progress: 100.0%", "stream": "stdout"}
        )

    return {"status": "completed", "elapsed": elapsed, "updates": update_count, "name": name}


def example_quick_task(message: str, _progress_queue: Optional[Queue] = None):
    """
    Quick example task that completes immediately.

    Args:
        message: Message to output
        _progress_queue: Queue for sending progress updates
    """
    if _progress_queue:
        _progress_queue.put(
            {"type": "output", "output": f"Quick task says: {message}", "stream": "stdout"}
        )
        _progress_queue.put(
            {"type": "output", "output": "Task completed immediately!", "stream": "stdout"}
        )

    return {"status": "completed", "message": message}


def example_failing_task(fail_message: str, _progress_queue: Optional[Queue] = None):
    """
    Example task that always fails.

    Args:
        fail_message: Error message
        _progress_queue: Queue for sending progress updates
    """
    if _progress_queue:
        _progress_queue.put(
            {"type": "output", "output": "This task will fail in 2 seconds...", "stream": "stdout"}
        )

    time.sleep(2)

    if _progress_queue:
        _progress_queue.put({"type": "error", "error": fail_message, "stream": "stderr"})

    raise RuntimeError(fail_message)
