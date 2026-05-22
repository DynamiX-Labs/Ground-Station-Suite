"""
Task Registry - Registry of available background tasks.

This module maintains a registry of functions that can be executed as background tasks.
Only registered functions can be started via Socket.IO to prevent arbitrary code execution.
"""

from typing import Callable, Dict

from tasks.exampletask import example_failing_task, example_long_task, example_quick_task
from tasks.satdumpprocessor import satdump_process_recording
from tasks.soapysdrdiscovery import soapysdr_discovery_task, soapysdr_quick_refresh_task
from tasks.tlesync import orbital_sync_background_task, tle_sync_background_task
from tasks.waterfallgenerator import generate_waterfall_task

# Registry of available background tasks
# Format: {"task_name": function_reference}
TASK_REGISTRY: Dict[str, Callable] = {
    # Example tasks for testing
    "example_long_task": example_long_task,
    "example_quick_task": example_quick_task,
    "example_failing_task": example_failing_task,
    # Real tasks
    "generate_waterfall": generate_waterfall_task,
    "satdump_process": satdump_process_recording,
    "soapysdr_discovery": soapysdr_discovery_task,
    "soapysdr_quick_refresh": soapysdr_quick_refresh_task,
    "orbital_sync": orbital_sync_background_task,
    "tle_sync": tle_sync_background_task,
}


def get_task(task_name: str) -> Callable:
    """
    Get a task function by name.

    Args:
        task_name: Name of the registered task

    Returns:
        Task function

    Raises:
        KeyError: If task not found in registry
    """
    if task_name not in TASK_REGISTRY:
        raise KeyError(f"Task '{task_name}' not found in registry")

    return TASK_REGISTRY[task_name]


def list_tasks() -> list[str]:
    """
    List all available task names.

    Returns:
        List of registered task names
    """
    return list(TASK_REGISTRY.keys())


def register_task(name: str, func: Callable):
    """
    Register a new task function.

    Args:
        name: Task name
        func: Task function

    Raises:
        ValueError: If task name already registered
    """
    if name in TASK_REGISTRY:
        raise ValueError(f"Task '{name}' is already registered")

    TASK_REGISTRY[name] = func
