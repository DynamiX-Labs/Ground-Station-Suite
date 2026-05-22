"""
Background task management system.

This module provides infrastructure for running long-running external processes
with real-time progress updates via Socket.IO.
"""

from tasks.manager import BackgroundTaskManager, TaskInfo, TaskStatus

__all__ = ["BackgroundTaskManager", "TaskInfo", "TaskStatus"]
