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

"""Library version information utilities."""

import importlib.metadata
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

import gnuradio

from common.logger import logger

# Cache for library versions to avoid repeated expensive operations
_backend_library_versions_cache: Optional[Dict[str, Any]] = None
_frontend_library_versions_cache: Optional[Dict[str, Any]] = None


def get_package_version(package_name: str) -> Optional[str]:
    """
    Get the version of an installed Python package.

    Args:
        package_name: Name of the package

    Returns:
        Version string or None if package is not installed
    """
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def get_system_library_version(command: List[str]) -> Optional[str]:
    """
    Get the version of a system library by running a command.

    Args:
        command: Command to execute (e.g., ['uhd_find_devices', '--version'])

    Returns:
        Version string or None if command fails
    """
    try:
        result = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5
        )
        output = result.stdout + result.stderr
        return output.strip() if output else None
    except (subprocess.SubprocessError, FileNotFoundError, TimeoutError):
        return None


def get_python_version() -> str:
    """Get the Python version."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_library_versions(use_cache: bool = True) -> Dict[str, Any]:
    """
    Get versions of all important libraries and dependencies.

    Args:
        use_cache: If True, return cached results if available. If False, force refresh.

    Returns:
        Dictionary containing categorized library information
    """
    global _backend_library_versions_cache

    # Return cached version if available and use_cache is True
    if use_cache and _backend_library_versions_cache is not None:
        logger.debug("Returning cached backend library versions")
        return _backend_library_versions_cache

    logger.info("Fetching backend library versions (no cache)")

    libraries: Dict[str, Dict[str, Any]] = {
        "python": {
            "name": "Python",
            "version": get_python_version(),
            "category": "runtime",
            "description": "Python interpreter",
        },
        # Core web framework
        "fastapi": {
            "name": "FastAPI",
            "version": get_package_version("fastapi"),
            "category": "web",
            "description": "Web framework",
        },
        "uvicorn": {
            "name": "Uvicorn",
            "version": get_package_version("uvicorn"),
            "category": "web",
            "description": "ASGI server",
        },
        "python-socketio": {
            "name": "Python-SocketIO",
            "version": get_package_version("python-socketio"),
            "category": "web",
            "description": "WebSocket communication",
        },
        # Database
        "sqlalchemy": {
            "name": "SQLAlchemy",
            "version": get_package_version("sqlalchemy"),
            "category": "database",
            "description": "SQL toolkit and ORM",
        },
        "alembic": {
            "name": "Alembic",
            "version": get_package_version("alembic"),
            "category": "database",
            "description": "Database migrations",
        },
        # SDR libraries
        "pyrtlsdr": {
            "name": "pyrtlsdr",
            "version": get_package_version("pyrtlsdr"),
            "category": "sdr",
            "description": "RTL-SDR Python bindings",
        },
        # Scientific computing
        "numpy": {
            "name": "NumPy",
            "version": get_package_version("numpy"),
            "category": "scientific",
            "description": "Numerical computing",
        },
        "scipy": {
            "name": "SciPy",
            "version": get_package_version("scipy"),
            "category": "scientific",
            "description": "Scientific computing",
        },
        "scikit-learn": {
            "name": "scikit-learn",
            "version": get_package_version("scikit-learn"),
            "category": "scientific",
            "description": "Machine learning",
        },
        # Satellite tracking
        "skyfield": {
            "name": "Skyfield",
            "version": get_package_version("skyfield"),
            "category": "tracking",
            "description": "Astronomy and satellite tracking",
        },
        "sgp4": {
            "name": "SGP4",
            "version": get_package_version("sgp4"),
            "category": "tracking",
            "description": "Satellite position calculations",
        },
        # Audio processing
        "sounddevice": {
            "name": "sounddevice",
            "version": get_package_version("sounddevice"),
            "category": "audio",
            "description": "Audio I/O",
        },
        # Image processing
        "pillow": {
            "name": "Pillow",
            "version": get_package_version("pillow"),
            "category": "image",
            "description": "Image processing",
        },
        # Task scheduling
        "apscheduler": {
            "name": "APScheduler",
            "version": get_package_version("apscheduler"),
            "category": "scheduling",
            "description": "Task scheduling",
        },
        # Error correction
        "reedsolo": {
            "name": "reedsolo",
            "version": get_package_version("reedsolo"),
            "category": "encoding",
            "description": "Reed-Solomon error correction",
        },
        # HTTP client
        "requests": {
            "name": "Requests",
            "version": get_package_version("requests"),
            "category": "networking",
            "description": "HTTP library",
        },
        "httpx": {
            "name": "HTTPX",
            "version": get_package_version("httpx"),
            "category": "networking",
            "description": "Async HTTP client",
        },
        # Security
        "cryptography": {
            "name": "Cryptography",
            "version": get_package_version("cryptography"),
            "category": "security",
            "description": "Cryptographic primitives",
        },
        "pyjwt": {
            "name": "PyJWT",
            "version": get_package_version("pyjwt"),
            "category": "security",
            "description": "JSON Web Token implementation",
        },
    }

    # Try to get system library versions
    system_libraries: Dict[str, Dict[str, Any]] = {}

    # UHD (USRP Hardware Driver)
    # Try uhd_config_info --version first, then fall back to checking if any uhd command exists
    uhd_version = get_system_library_version(["uhd_config_info", "--version"])
    if not uhd_version:
        # Try alternative: check if uhd_find_devices exists
        uhd_check = get_system_library_version(["which", "uhd_find_devices"])
        if uhd_check:
            uhd_version = "installed"

    if uhd_version:
        # Extract just the version number if it's in the output
        version_str = uhd_version.split("\n")[0] if "\n" in uhd_version else uhd_version
        # Clean up the version string (remove extra text)
        if "UHD" in version_str:
            # Extract version number from strings like "UHD 4.x.x.x"
            parts = version_str.split()
            for part in parts:
                if part[0].isdigit():
                    version_str = part
                    break

        system_libraries["uhd"] = {
            "name": "UHD",
            "version": version_str.strip(),
            "category": "sdr",
            "description": "USRP Hardware Driver",
        }

    # SoapySDR
    soapy_version = get_system_library_version(["SoapySDRUtil", "--info"])
    if soapy_version:
        # Extract version from output
        for line in soapy_version.split("\n"):
            if "Lib Version" in line:
                version = line.split(":")[-1].strip()
                system_libraries["soapysdr"] = {
                    "name": "SoapySDR",
                    "version": version,
                    "category": "sdr",
                    "description": "Vendor-neutral SDR support library",
                }
                break

    # RTL-SDR library (check if rtl_test exists)
    rtlsdr_version = get_system_library_version(["rtl_test", "-h"])
    if rtlsdr_version:
        system_libraries["rtl-sdr"] = {
            "name": "rtl-sdr",
            "version": "installed",
            "category": "sdr",
            "description": "RTL-SDR library",
        }

    # GNU Radio
    gnuradio_version = get_system_library_version(["gnuradio-config-info", "--version"])
    if gnuradio_version:
        system_libraries["gnuradio"] = {
            "name": "GNU Radio",
            "version": gnuradio_version.strip(),
            "category": "sdr",
            "description": "Software-defined radio framework",
        }
    else:
        # Fallback to Python import
        system_libraries["gnuradio"] = {
            "name": "GNU Radio",
            "version": gnuradio.__version__ if hasattr(gnuradio, "__version__") else "installed",
            "category": "sdr",
            "description": "Software-defined radio framework",
        }

    # VOLK (Vector-Optimized Library of Kernels)
    volk_version = get_system_library_version(["volk_profile", "--version"])
    if volk_version:
        # Extract version from output
        for line in volk_version.split("\n"):
            if "volk" in line.lower() and any(c.isdigit() for c in line):
                parts = line.split()
                for part in parts:
                    if part[0].isdigit() or part.startswith("v"):
                        system_libraries["volk"] = {
                            "name": "VOLK",
                            "version": part.lstrip("v"),
                            "category": "sdr",
                            "description": "Vector-Optimized Library of Kernels",
                        }
                        break
                break

    # LimeSuite
    lime_version = get_system_library_version(["LimeUtil", "--info"])
    if lime_version:
        for line in lime_version.split("\n"):
            if "library version" in line.lower():
                parts = line.split(":")
                if len(parts) > 1:
                    system_libraries["limesuite"] = {
                        "name": "LimeSuite",
                        "version": parts[1].strip(),
                        "category": "sdr",
                        "description": "LimeSDR driver and tools",
                    }
                    break

    # SDRplay API (check for libsdrplay_api.so)
    sdrplay_version = None
    # Try to find the library file to extract version
    sdrplay_lib_path = "/usr/local/lib/libsdrplay_api.so.3.15"
    if os.path.exists(sdrplay_lib_path):
        # Extract version from the library filename
        basename = os.path.basename(sdrplay_lib_path)
        if basename.startswith("libsdrplay_api.so."):
            sdrplay_version = basename.replace("libsdrplay_api.so.", "")
    else:
        # Fallback: check if any libsdrplay_api.so exists
        for lib_path in ["/usr/local/lib/libsdrplay_api.so", "/usr/lib/libsdrplay_api.so"]:
            if os.path.exists(lib_path):
                sdrplay_version = "installed"
                break

    if sdrplay_version:
        system_libraries["sdrplay-api"] = {
            "name": "SDRplay RSP API",
            "version": sdrplay_version,
            "category": "sdr",
            "description": "SDRplay RSP hardware driver API",
        }

    # SoapySDR modules (check which are installed and their versions)
    soapy_modules = get_system_library_version(["SoapySDRUtil", "--info"])
    if soapy_modules:
        # Parse module information from "Module found:" lines
        for line in soapy_modules.split("\n"):
            if "Module found:" in line:
                # Format: Module found: /path/libNAMESupport.so  (VERSION)
                try:
                    # Extract library name from path
                    if "libHackRFSupport.so" in line or "hackrf" in line.lower():
                        version = line.split("(")[1].split(")")[0] if "(" in line else "installed"
                        system_libraries["soapysdr-hackrf"] = {
                            "name": "SoapyHackRF",
                            "version": version,
                            "category": "sdr",
                            "description": "SoapySDR HackRF support",
                        }
                    elif "libLMS7Support.so" in line or "lime" in line.lower():
                        version = line.split("(")[1].split(")")[0] if "(" in line else "installed"
                        system_libraries["soapysdr-lime"] = {
                            "name": "SoapyLimeSDR",
                            "version": version,
                            "category": "sdr",
                            "description": "SoapySDR LimeSDR support",
                        }
                    elif "libairspySupport.so" in line or "airspy" in line.lower():
                        version = line.split("(")[1].split(")")[0] if "(" in line else "installed"
                        system_libraries["soapysdr-airspy"] = {
                            "name": "SoapyAirspy",
                            "version": version,
                            "category": "sdr",
                            "description": "SoapySDR Airspy support",
                        }
                    elif "libuhdSupport.so" in line or (
                        "uhd" in line.lower() and "Support.so" in line
                    ):
                        version = line.split("(")[1].split(")")[0] if "(" in line else "installed"
                        system_libraries["soapysdr-uhd"] = {
                            "name": "SoapyUHD",
                            "version": version,
                            "category": "sdr",
                            "description": "SoapySDR UHD/USRP support",
                        }
                    elif "libremoteSupport.so" in line or "remote" in line.lower():
                        version = line.split("(")[1].split(")")[0] if "(" in line else "installed"
                        system_libraries["soapysdr-remote"] = {
                            "name": "SoapyRemote",
                            "version": version,
                            "category": "sdr",
                            "description": "SoapySDR remote access",
                        }
                    elif "librtlsdrSupport.so" in line or "rtlsdr" in line.lower():
                        version = line.split("(")[1].split(")")[0] if "(" in line else "installed"
                        system_libraries["soapysdr-rtlsdr"] = {
                            "name": "SoapyRTLSDR",
                            "version": version,
                            "category": "sdr",
                            "description": "SoapySDR RTL-SDR support",
                        }
                    elif "libsdrPlaySupport.so" in line or "sdrplay" in line.lower():
                        version = line.split("(")[1].split(")")[0] if "(" in line else "installed"
                        system_libraries["soapysdr-sdrplay"] = {
                            "name": "SoapySDRPlay",
                            "version": version,
                            "category": "sdr",
                            "description": "SoapySDR SDRplay support",
                        }
                    elif "libbladeRFSupport.so" in line or "bladerf" in line.lower():
                        version = line.split("(")[1].split(")")[0] if "(" in line else "installed"
                        system_libraries["soapysdr-bladerf"] = {
                            "name": "SoapyBladeRF",
                            "version": version,
                            "category": "sdr",
                            "description": "SoapySDR BladeRF support",
                        }
                except (IndexError, ValueError):
                    # If parsing fails, skip this module
                    pass

    # Combine all libraries
    all_libraries: Dict[str, Dict[str, Any]] = {**libraries, **system_libraries}

    # Filter out libraries that are not installed (None version)
    installed_libraries: Dict[str, Dict[str, Any]] = {
        key: value for key, value in all_libraries.items() if value["version"] is not None
    }

    # Categorize libraries
    categorized: Dict[str, List[Dict[str, str]]] = {}
    for lib_key, lib_info in installed_libraries.items():
        category: str = lib_info["category"]
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(
            {
                "key": lib_key,
                "name": lib_info["name"],
                "version": lib_info["version"],
                "description": lib_info["description"],
            }
        )

    # Sort categories and libraries within categories
    result: Dict[str, List[Dict[str, str]]] = {}
    for category in sorted(categorized.keys()):
        result[category] = sorted(categorized[category], key=lambda x: x["name"])

    logger.info(f"Retrieved version information for {len(installed_libraries)} libraries")

    result_dict = {"categories": result, "total_count": len(installed_libraries)}

    # Cache the result
    _backend_library_versions_cache = result_dict

    return result_dict


def get_frontend_library_versions(use_cache: bool = True) -> Dict[str, Any]:
    """
    Get versions of frontend libraries from package.json.

    Args:
        use_cache: If True, return cached results if available. If False, force refresh.

    Returns:
        Dictionary containing categorized frontend library information
    """
    global _frontend_library_versions_cache

    # Return cached version if available and use_cache is True
    if use_cache and _frontend_library_versions_cache is not None:
        logger.debug("Returning cached frontend library versions")
        return _frontend_library_versions_cache

    logger.info("Fetching frontend library versions (no cache)")

    # Path to frontend package.json relative to backend directory
    package_json_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "frontend", "package.json"
    )
    package_json_path = os.path.abspath(package_json_path)

    if not os.path.exists(package_json_path):
        logger.error(f"Frontend package.json not found at {package_json_path}")
        return {"categories": {}, "total_count": 0}

    try:
        with open(package_json_path, "r") as f:
            package_data = json.load(f)

        dependencies = package_data.get("dependencies", {})
        dev_dependencies = package_data.get("devDependencies", {})

        # Categorize frontend libraries
        categorized: Dict[str, List[Dict[str, str]]] = {
            "ui": [],
            "state": [],
            "routing": [],
            "data-viz": [],
            "maps": [],
            "utilities": [],
            "build": [],
            "testing": [],
        }

        # Map packages to categories
        category_mapping = {
            # UI Frameworks & Components
            "react": "ui",
            "react-dom": "ui",
            "@emotion/react": "ui",
            "@emotion/styled": "ui",
            "@mui/material": "ui",
            "@mui/icons-material": "ui",
            "@mui/joy": "ui",
            "@mui/lab": "ui",
            "@toolpad/core": "ui",
            "hugeicons-react": "ui",
            "react-icons": "ui",
            "react-toastify": "ui",
            "react-full-screen": "ui",
            "react-grid-layout": "ui",
            "react-resize-detector": "ui",
            "react-window": "ui",
            "react-virtuoso": "ui",
            "react-zoom-pan-pinch": "ui",
            # State Management
            "@reduxjs/toolkit": "state",
            "react-redux": "state",
            "redux-persist": "state",
            "immer": "state",
            # Routing
            "react-router": "routing",
            "react-router-dom": "routing",
            # Data Visualization
            "@mui/x-charts": "data-viz",
            "@mui/x-data-grid": "data-viz",
            # Maps & Geolocation
            "leaflet": "maps",
            "leaflet-fullscreen": "maps",
            "react-leaflet": "maps",
            "satellite.js": "maps",
            "suncalc": "maps",
            "cities.json": "maps",
            # Utilities
            "socket.io-client": "utilities",
            "socket.io": "utilities",
            "i18next": "utilities",
            "react-i18next": "utilities",
            "moment-timezone": "utilities",
            "lodash": "utilities",
            "uuid": "utilities",
            "hls.js": "utilities",
            # Build Tools
            "vite": "build",
            "@vitejs/plugin-react": "build",
            # Testing
            "vitest": "testing",
            "@vitest/ui": "testing",
            "@vitest/coverage-v8": "testing",
            "@playwright/test": "testing",
            "@testing-library/react": "testing",
            "@testing-library/jest-dom": "testing",
            "@testing-library/user-event": "testing",
            "jsdom": "testing",
            "eslint": "testing",
            "@eslint/js": "testing",
            "eslint-plugin-react": "testing",
            "eslint-plugin-react-hooks": "testing",
            "eslint-plugin-react-refresh": "testing",
        }

        # Process dependencies
        for package_name, version in dependencies.items():
            category = category_mapping.get(package_name, "utilities")
            # Clean version (remove ^ ~ etc)
            clean_version = version.lstrip("^~>=<")
            categorized[category].append(
                {
                    "key": package_name,
                    "name": package_name,
                    "version": clean_version,
                    "description": "Production dependency",
                }
            )

        # Process dev dependencies
        for package_name, version in dev_dependencies.items():
            category = category_mapping.get(package_name, "build")
            clean_version = version.lstrip("^~>=<")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(
                {
                    "key": package_name,
                    "name": package_name,
                    "version": clean_version,
                    "description": "Development dependency",
                }
            )

        # Remove empty categories and sort
        result: Dict[str, List[Dict[str, str]]] = {}
        total_count = 0
        for category in sorted(categorized.keys()):
            if categorized[category]:
                result[category] = sorted(categorized[category], key=lambda x: x["name"])
                total_count += len(result[category])

        logger.info(f"Retrieved frontend version information for {total_count} packages")

        result_dict = {"categories": result, "total_count": total_count}

        # Cache the result
        _frontend_library_versions_cache = result_dict

        return result_dict

    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading frontend package.json: {e}")
        return {"categories": {}, "total_count": 0}
