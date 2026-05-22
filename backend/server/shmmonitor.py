# Ground Station - Shared Memory Monitor Utility
# Developed by Claude (Anthropic AI) for the Ground Station project
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
#
# Utility to monitor shared memory usage by GNU Radio.
#
# GNU Radio creates shared memory segments (or mmap files) for circular buffers
# between blocks. This utility monitors segment count and usage to help detect
# memory issues.
#
# With vmcirc_mmap_tmpfile configured, segments should remain low/stable.
# With vmcirc_sysv_shm (shmget), segments accumulate and require cleanup.

import logging
import subprocess
import threading
import time

logger = logging.getLogger("shm-monitor")


class SharedMemoryMonitor:
    """Background thread that periodically monitors shared memory usage."""

    def __init__(self, monitor_interval=30):
        """
        Initialize the monitor thread.

        Args:
            monitor_interval: Seconds between monitoring checks (default: 30)
        """
        self.monitor_interval = monitor_interval
        self.running = False
        self.thread = None
        self._last_segment_count = 0
        self._peak_segment_count = 0
        self._orphaned_segments_cleaned = 0

    def start(self):
        """Start the monitor thread."""
        if self.running:
            logger.warning("Monitor thread already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True, name="SHM-Monitor")
        self.thread.start()
        logger.info(f"Started shared memory monitor thread (interval: {self.monitor_interval}s)")

    def stop(self):
        """Stop the monitor thread."""
        if not self.running:
            return

        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        logger.info(
            f"Stopped shared memory monitor (peak: {self._peak_segment_count} segments, "
            f"cleaned: {self._orphaned_segments_cleaned} orphaned)"
        )

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                # Get current segment count
                segment_count = self._get_segment_count()
                orphaned_count = self._get_orphaned_count()

                # Track peak usage
                if segment_count > self._peak_segment_count:
                    self._peak_segment_count = segment_count

                # Log if count changed significantly or if there are orphaned segments
                if segment_count != self._last_segment_count:
                    if orphaned_count > 0:
                        logger.warning(
                            f"Shared memory: {segment_count} segments "
                            f"({orphaned_count} orphaned, peak: {self._peak_segment_count})"
                        )
                        # Optionally clean up orphaned segments if using shmget
                        cleaned = self._cleanup_orphaned_segments()
                        if cleaned > 0:
                            self._orphaned_segments_cleaned += cleaned
                            logger.info(f"Cleaned {cleaned} orphaned segments")
                    else:
                        logger.info(
                            f"Shared memory: {segment_count} segments (peak: {self._peak_segment_count})"
                        )
                    self._last_segment_count = segment_count

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            # Sleep in short intervals to allow quick shutdown
            for _ in range(self.monitor_interval * 2):
                if not self.running:
                    break
                time.sleep(0.5)

    def _cleanup_orphaned_segments(self):
        """
        Remove orphaned shared memory segments (nattch=0).

        Returns:
            Number of segments removed
        """
        try:
            # Get list of orphaned segment IDs (column 2, where column 6 nattch==0)
            # Skip first 3 header lines with NR>3
            result = subprocess.run(
                ["sh", "-c", "ipcs -m | awk 'NR>3 && $6==0 {print $2}'"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                logger.error(f"Failed to list shared memory segments: {result.stderr}")
                return 0

            segment_ids = [
                line.strip() for line in result.stdout.strip().split("\n") if line.strip()
            ]

            if not segment_ids:
                return 0

            # Remove each orphaned segment
            removed = 0
            for seg_id in segment_ids:
                try:
                    subprocess.run(
                        ["ipcrm", "-m", seg_id],
                        capture_output=True,
                        timeout=2,
                        check=True,
                    )
                    removed += 1
                except subprocess.CalledProcessError:
                    # Segment may have been removed by another process
                    pass
                except Exception as e:
                    logger.debug(f"Failed to remove segment {seg_id}: {e}")

            return removed

        except Exception as e:
            logger.error(f"Error cleaning orphaned segments: {e}")
            return 0

    def _get_segment_count(self):
        """Get current number of allocated shared memory segments."""
        try:
            result = subprocess.run(
                ["sh", "-c", "ipcs -m -u | grep 'segments allocated' | awk '{print $3}'"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
        except Exception:
            pass
        return 0

    def _get_orphaned_count(self):
        """Get count of orphaned shared memory segments (nattch=0)."""
        try:
            result = subprocess.run(
                ["sh", "-c", "ipcs -m | awk 'NR>3 && $6==0' | wc -l"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip())
        except Exception:
            pass
        return 0


# Global singleton instance
_monitor_instance = None
_monitor_lock = threading.Lock()


def start_monitor_thread(monitor_interval=30):
    """
    Start the global shared memory monitor thread.

    Args:
        monitor_interval: Seconds between monitoring checks (default: 30)
    """
    global _monitor_instance

    with _monitor_lock:
        if _monitor_instance is None:
            _monitor_instance = SharedMemoryMonitor(monitor_interval=monitor_interval)
            _monitor_instance.start()
        else:
            logger.debug("Monitor thread already started")


def stop_monitor_thread():
    """Stop the global shared memory monitor thread."""
    global _monitor_instance

    with _monitor_lock:
        if _monitor_instance is not None:
            _monitor_instance.stop()
            _monitor_instance = None


# Backwards compatibility aliases
start_cleanup_thread = start_monitor_thread
stop_cleanup_thread = stop_monitor_thread
