import json
import os
import platform
import re
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict, cast

import psutil
import requests

from common.logger import logger

# Path to the version.json file containing the base version
VERSION_JSON_PATH = os.path.join(os.path.dirname(__file__), "version.json")

# Path to store version info during build
VERSION_FILE_PATH = os.path.join(os.path.dirname(__file__), "version-info.json")


# Singleton instance of version info
class UpdateCheckData(TypedDict):
    currentVersion: str
    latestVersion: str
    latestTag: Optional[str]
    latestUrl: Optional[str]
    publishedAt: Optional[str]
    isUpdateAvailable: bool


class UpdateCheckCache(TypedDict):
    timestamp: float
    data: Optional[UpdateCheckData]


_version_info = None
_update_check_cache: UpdateCheckCache = {"timestamp": 0.0, "data": None}

# GitHub releases endpoint (public)
GITHUB_RELEASES_URL = "https://api.github.com/repos/sgoudelis/ground-station/releases/latest"


def _normalize_version(raw: str) -> str:
    """Normalize a version string to 'major.minor.patch' if possible."""
    if not raw:
        return "0.0.0"
    value = raw.strip()
    if value.startswith(("v", "V")):
        value = value[1:]
    # Drop build metadata and pre-release suffixes
    value = value.split("+", 1)[0].split("-", 1)[0]
    # Keep only digits and dots
    value = re.sub(r"[^0-9.]", "", value)
    # Ensure at least 3 segments
    parts = [p for p in value.split(".") if p != ""]
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:3]) if parts else "0.0.0"


def _compare_versions(a: str, b: str) -> int:
    """Compare two normalized semantic versions. Returns 1 if a>b, -1 if a<b, 0 if equal."""

    def to_tuple(v: str) -> tuple[int, int, int]:
        parts = v.split(".")
        nums = []
        for part in parts[:3]:
            try:
                nums.append(int(part))
            except ValueError:
                nums.append(0)
        while len(nums) < 3:
            nums.append(0)
        return (nums[0], nums[1], nums[2])

    ta = to_tuple(_normalize_version(a))
    tb = to_tuple(_normalize_version(b))
    if ta > tb:
        return 1
    if ta < tb:
        return -1
    return 0


def _fetch_latest_release() -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ground-station",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(GITHUB_RELEASES_URL, headers=headers, timeout=5)
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


def get_update_check(cache_ttl_seconds: int = 21600) -> UpdateCheckData:
    """Return update availability based on GitHub releases with in-memory caching."""
    now = time.time()
    cached = _update_check_cache.get("data")
    if cached and now - _update_check_cache["timestamp"] < cache_ttl_seconds:
        return cached

    current_base = _normalize_version(get_version_base())
    data: UpdateCheckData = {
        "currentVersion": current_base,
        "latestVersion": current_base,
        "latestTag": None,
        "latestUrl": None,
        "publishedAt": None,
        "isUpdateAvailable": False,
    }

    try:
        release = _fetch_latest_release()
        tag = release.get("tag_name") or release.get("name") or ""
        latest_version = _normalize_version(tag)
        data.update(
            {
                "latestVersion": latest_version,
                "latestTag": tag or None,
                "latestUrl": release.get("html_url"),
                "publishedAt": release.get("published_at"),
                "isUpdateAvailable": _compare_versions(latest_version, current_base) > 0,
            }
        )
    except Exception as exc:
        logger.warning(f"Update check failed: {exc}")

    _update_check_cache["timestamp"] = now
    _update_check_cache["data"] = data
    return data


def get_version_base():
    """Get the base version from version.json file."""
    try:
        if os.path.exists(VERSION_JSON_PATH):
            with open(VERSION_JSON_PATH, "r") as f:
                version_data = json.load(f)
                return version_data.get("version", "0.0.0")
        else:
            logger.warning(f"Version file not found: {VERSION_JSON_PATH}, using default version")
            return "0.0.0"
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading version file: {e}")
        return "0.0.0"


def get_git_revision_short_hash():
    """Get the git revision short hash, if available."""
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("ascii").strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If we're not in a git repository or git isn't installed
        return "unknown"


def get_build_date():
    """Get the build date in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def get_version_info():
    """Get complete version information."""
    # First check if we have a version-info.json file (created during build)
    if os.path.exists(VERSION_FILE_PATH):
        try:
            with open(VERSION_FILE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file exists but is invalid, continue with normal version generation
            pass

    # Determine environment (development by default)
    environment = os.environ.get("GS_ENVIRONMENT", "development")

    # Check if version is provided by environment (e.g., from the CI pipeline)
    if "BUILD_VERSION" in os.environ:
        version_info = {
            "version": os.environ["BUILD_VERSION"],
            "buildDate": os.environ.get("BUILD_DATE", get_build_date()),
            "gitCommit": os.environ.get("GIT_COMMIT", "unknown"),
            "environment": environment,
        }
    else:
        # Otherwise generate a version from components
        git_hash = get_git_revision_short_hash()
        build_date = get_build_date()
        version_base = get_version_base()

        # Include environment indicator in dev builds
        env_suffix = "" if environment == "production" else f"-{environment}"
        version = f"{version_base}{env_suffix}-{build_date}-{git_hash}"

        version_info = {
            "version": version,
            "buildDate": build_date,
            "gitCommit": git_hash,
            "environment": environment,
        }

    return version_info


def _get_cpu_usage_percent_nonblocking(prime: bool = False) -> float:
    """Return CPU usage percent using a non-blocking approach.

    psutil.cpu_percent(interval=None) returns the percent since last call.
    The first call returns a meaningless 0.0, so we allow a priming call.
    """
    if prime:
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass
        return 0.0
    try:
        return float(psutil.cpu_percent(interval=None))
    except Exception:
        return 0.0


def get_system_info(
    include_load_avg: bool = False, include_cpu_temp: bool = False, nonblocking_cpu: bool = False
):
    """Get system information (CPU, memory, disk usage).

    Args:
        include_load_avg: Include 1m/5m/15m load averages if available.
        include_cpu_temp: Include CPU temperature in Celsius if available.
        nonblocking_cpu: Use non-blocking CPU percent calculation.
    """
    try:
        # CPU information
        cpu_usage = (
            _get_cpu_usage_percent_nonblocking()
            if nonblocking_cpu
            else psutil.cpu_percent(interval=0.1)
        )
        cpu_info = {
            "architecture": platform.machine(),  # e.g., 'x86_64', 'aarch64', 'armv7l'
            "processor": platform.processor(),
            "cores": {
                "physical": psutil.cpu_count(logical=False),
                "logical": psutil.cpu_count(logical=True),
            },
            "usage_percent": cpu_usage,
        }

        # Memory information
        memory = psutil.virtual_memory()
        memory_info = {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "usage_percent": memory.percent,
        }

        # Disk information for root partition
        disk = psutil.disk_usage("/")
        disk_info = {
            "total_gb": round(disk.total / (1024**3), 2),
            "available_gb": round(disk.free / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "usage_percent": disk.percent,
        }

        # OS information
        os_info = {
            "system": platform.system(),  # e.g., 'Linux', 'Darwin', 'Windows'
            "release": platform.release(),
            "version": platform.version(),
        }
        result = {
            "cpu": cpu_info,
            "memory": memory_info,
            "disk": disk_info,
            "os": os_info,
        }
        if include_load_avg:
            try:
                la1, la5, la15 = os.getloadavg()
                result["load_avg"] = {
                    "1m": round(la1, 2),
                    "5m": round(la5, 2),
                    "15m": round(la15, 2),
                }
            except Exception:
                # Not available on all platforms — omit the key to avoid Optional typing issues
                pass

        if include_cpu_temp:
            cpu_temp_c = None
            gpu_temps = []
            disk_temps = {}
            try:
                temps = psutil.sensors_temperatures(fahrenheit=False) or {}
                # CPU temperatures (average across cores if multiple)
                for key in ("coretemp", "cpu_thermal", "k10temp", "acpitz"):
                    if key in temps and temps[key]:
                        entries = temps[key]
                        vals = [
                            t.current for t in entries if getattr(t, "current", None) is not None
                        ]
                        if vals:
                            cpu_temp_c = round(sum(vals) / len(vals), 1)
                            break

                # GPU temperatures
                # Common groups: 'amdgpu', 'nvidia', 'nouveau', sometimes vendor-specific
                for key in ("amdgpu", "nvidia", "nouveau", "gpu"):
                    if key in temps and temps[key]:
                        for t in temps[key]:
                            cur = getattr(t, "current", None)
                            if cur is not None:
                                try:
                                    gpu_temps.append(round(float(cur), 1))
                                except Exception:
                                    pass

                # Disk temperatures
                # Common groups: 'nvme', 'hddtemp', 'drivetemp', plus nvme-pci-* keys
                for key, entries in temps.items():
                    if not entries:
                        continue
                    key_lower = key.lower()
                    if (
                        key_lower in ("nvme", "hddtemp", "drivetemp")
                        or key_lower.startswith("nvme")
                        or "disk" in key_lower
                    ):
                        for t in entries:
                            cur = getattr(t, "current", None)
                            label = getattr(t, "label", None) or getattr(t, "device", None) or key
                            if cur is not None and label:
                                try:
                                    disk_temps[str(label)] = round(float(cur), 1)
                                except Exception:
                                    pass
            except Exception:
                # If sensors not available, keep defaults (None/empty)
                pass

            # Backward compatibility: keep cpu_temp_c at top level when available
            if cpu_temp_c is not None:
                result["cpu_temp_c"] = cpu_temp_c
            # New structured temperatures section
            result["temperatures"] = {
                "cpu_c": cpu_temp_c,
                "gpus_c": gpu_temps,
                "disks_c": disk_temps,
            }

        return result
    except Exception as e:
        logger.error(f"Error gathering system information: {e}")
        return {
            "error": f"Failed to gather system info: {str(e)}",
        }


def get_version():
    """Get the current version string."""
    global _version_info
    if _version_info is None:
        _version_info = get_version_info()
    return _version_info["version"]


def get_full_version_info():
    """Get the complete version information dictionary (no live system stats).

    Note: Live system stats have been moved to Socket.IO `system-info` emissions.
    We keep CPU architecture as a top-level field for other features.
    """
    global _version_info
    if _version_info is None:
        _version_info = get_version_info()

    # Do not include live system info here; only provide static version data
    full_info = _version_info.copy()
    try:
        full_info["cpuArchitecture"] = platform.machine()
    except Exception:
        full_info["cpuArchitecture"] = "unknown"

    now_utc = datetime.now(timezone.utc)
    full_info["serverTimeEpochMs"] = int(now_utc.timestamp() * 1000)
    full_info["serverTimeIsoUtc"] = now_utc.isoformat()

    return full_info


def write_version_info_during_build(version_info_override=None):
    """
    CLI utility to write version info during the build process.
    This allows capturing the git commit at build time rather than runtime.

    Args:
        version_info_override (dict, optional): Dictionary with version info values to override.
                                              Any keys provided will override the corresponding values
                                              from get_version_info().
    """
    version_info = get_version_info()

    # Apply overrides if provided
    if version_info_override:
        version_info.update(version_info_override)

    with open(VERSION_FILE_PATH, "w") as f:
        json.dump(version_info, f)
    logger.info(
        f"Version information written to {VERSION_FILE_PATH}: {version_info} with overrides: "
        f"{version_info_override}"
    )
    return version_info
