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

"""Hardware (rigs, rotators, cameras, SDRs) handlers."""

import asyncio
import json
import logging
import math
import sys
from bisect import bisect_left
from typing import Any, Dict, Optional, Union

import crud
from db import AsyncSessionLocal
from hardware.soapysdrbrowser import discovered_servers
from session.service import active_sdr_clients
from tracker.contracts import InvalidTrackerIdError, require_tracker_id
from tracker.runner import get_all_tracker_managers, get_tracker_manager
from workers.common import window_functions

logger = logging.getLogger("hardware-handler")

# Create a cache dictionary to store SDR parameters by SDR ID
sdr_parameters_cache: Dict[str, Dict] = {}


def _nearest_rate(sorted_rates: list[float], target: float) -> float:
    if not sorted_rates:
        return target
    idx = bisect_left(sorted_rates, target)
    if idx <= 0:
        return sorted_rates[0]
    if idx >= len(sorted_rates):
        return sorted_rates[-1]
    before = sorted_rates[idx - 1]
    after = sorted_rates[idx]
    return after if abs(after - target) < abs(target - before) else before


def _select_neat_sample_rates(rates: list[float]) -> list[float]:
    clean_rates = sorted({float(r) for r in rates if r and r > 0})
    if len(clean_rates) <= 50:
        return clean_rates

    min_rate = clean_rates[0]
    max_rate = clean_rates[-1]
    log_min = math.log10(min_rate)
    log_max = math.log10(max_rate)

    selected: set[float] = set()
    targets: list[float] = []
    for exp in range(int(math.floor(log_min)), int(math.ceil(log_max)) + 1):
        for base in (1.0, 2.0, 2.5, 5.0):
            target = base * (10**exp)
            if min_rate <= target <= max_rate:
                targets.append(target)

    for target in targets:
        nearest = _nearest_rate(clean_rates, target)
        tolerance = max(target * 0.01, 1.0)
        if abs(nearest - target) <= tolerance:
            selected.add(nearest)

    selected.add(min_rate)
    selected.add(max_rate)

    if len(selected) < 20:
        for i in range(20):
            target = 10 ** (log_min + (log_max - log_min) * (i / 19))
            selected.add(_nearest_rate(clean_rates, target))

    return sorted(selected)


def _strip_sample_rate_ranges(capabilities: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(capabilities, dict):
        return capabilities
    sanitized = dict(capabilities)
    sanitized.pop("sample_rate_ranges", None)
    return sanitized


async def get_local_soapy_sdr_devices():
    """Retrieve a list of local SoapySDR devices with frequency range information"""

    reply: Dict[str, Union[bool, dict, list, str, None]] = {
        "success": None,
        "data": None,
        "error": None,
    }

    try:
        logger.info("Probing local SoapySDR devices...")
        probe_process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "from hardware.soapyenum import probe_available_usb_sdrs;"
            "import json; print(probe_available_usb_sdrs())",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(probe_process.communicate(), timeout=35)
            result = json.loads(stdout.decode().strip())

            if result["success"]:
                result = result["data"]
            else:
                raise Exception("Error enumerating local SoapySDR devices")

            reply["success"] = True
            reply["data"] = result

        except asyncio.TimeoutError:
            probe_process.kill()
            logger.error("Process timed out while probing USB SDRs")
            reply["success"] = False
            reply["error"] = "Operation timed out after 5 seconds"

    except Exception as e:
        logger.error("Error probing USB SDRs: %s", str(e))
        logger.exception(e)
        reply["success"] = False
        reply["error"] = str(e)

    logger.info("Done probing local SoapySDR devices")
    return reply


async def get_local_rtl_sdr_devices():
    """Retrieve a list of local RTL-SDR devices"""

    reply: Dict[str, Union[bool, dict, list, str, None]] = {
        "success": None,
        "data": None,
        "error": None,
    }

    try:
        logger.info("Probing local RTL-SDR devices...")
        probe_process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            "from hardware.rtlsdrenum import probe_available_rtl_sdrs;"
            "import json; print(probe_available_rtl_sdrs())",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(probe_process.communicate(), timeout=35)
            result = json.loads(stdout.decode().strip())

            if result["success"]:
                result = result["data"]
            else:
                raise Exception("Error enumerating local RTL-SDR devices")

            reply["success"] = True
            reply["data"] = result
            logger.info("Detected %d RTL-SDR device(s)", len(result))

        except asyncio.TimeoutError:
            probe_process.kill()
            logger.error("Process timed out while probing RTL-SDR devices")
            reply["success"] = False
            reply["error"] = "Operation timed out after 5 seconds"

    except Exception as e:
        logger.error("Error probing RTL-SDR devices: %s", str(e))
        logger.exception(e)
        reply["success"] = False
        reply["error"] = str(e)

    logger.info("Done probing local RTL-SDR devices")
    return reply


async def _fetch_sdr_parameters(dbsession, sdr_id, timeout=30.0):
    """Retrieve SDR parameters from the SDR process manager with caching"""

    reply: Dict[str, Union[bool, None, dict, list, str]] = {
        "success": None,
        "data": None,
        "error": None,
    }
    sdr = {}
    sdr_params = {}

    # Check if parameters for this SDR are already cached
    # For sigmfplayback, don't use cache since recording_path may have changed
    if sdr_id in sdr_parameters_cache and sdr_id != "sigmf-playback":
        logger.info("Using cached parameters for SDR with id %s", sdr_id)
        return {"success": True, "data": sdr_parameters_cache[sdr_id]}
    elif sdr_id == "sigmf-playback" and sdr_id in sdr_parameters_cache:
        logger.info("Skipping cache for sigmfplayback SDR, will re-probe")

    try:
        # Handle hardcoded SigMF playback SDR
        if sdr_id == "sigmf-playback":
            sdr = {
                "id": "sigmf-playback",
                "name": "SigMF Playback",
                "type": "sigmfplayback",
                "driver": "sigmfplayback",
                "recording_path": "",  # Will be set when recording is selected
            }
        else:
            # Fetch SDR device details from database
            sdr_device_reply = await crud.hardware.fetch_sdr(dbsession, sdr_id)

            if not sdr_device_reply["data"]:
                raise Exception(f"SDR device with id {sdr_id} not found in database")

            sdr = sdr_device_reply["data"]

        if sdr.get("type") in ["rtlsdrtcpv3", "rtlsdrusbv3", "rtlsdrtcpv4", "rtlsdrusbv4"]:

            # Common RTL-SDR gain values in dB
            gain_values = [
                0.0,
                0.9,
                1.4,
                2.7,
                3.7,
                7.7,
                8.7,
                12.5,
                14.4,
                15.7,
                16.6,
                19.7,
                20.7,
                22.9,
                25.4,
                28.0,
                29.7,
                32.8,
                33.8,
                36.4,
                37.2,
                38.6,
                40.2,
                42.1,
                43.4,
                43.9,
                44.5,
                48.0,
            ]

            # Common RTL-SDR sample rates in Hz
            sample_rate_values = [
                240000,
                300000,
                960000,
                1024000,
                1536000,
                1792000,
                1920000,
                2048000,
                2304000,
                2400000,
                2560000,
                2880000,
                3200000,
            ]

            # Common window functions
            window_function_names = list(window_functions.keys())

            # Common FFT sizes
            fft_size_values = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]

            params = {
                "gain_values": gain_values,
                "sample_rate_values": sample_rate_values,
                "fft_size_values": fft_size_values,
                "fft_window_values": window_function_names,
                "has_bias_t": True,
                "has_tuner_agc": True,
                "has_rtl_agc": True,
                "antennas": {"tx": [], "rx": ["RX"]},
            }

            sdr_parameters_cache[sdr_id] = params
            reply = {"success": True, "data": params}

        elif sdr.get("type") in ["soapysdrremote", "soapysdrlocal"]:
            if sdr.get("type") == "soapysdrremote":
                logger.info("Getting SDR parameters from SoapySDR server for SDR: %s", sdr)
                probe_process = await asyncio.create_subprocess_exec(
                    "python3",
                    "-c",
                    "from hardware.soapysdrremoteprobe import probe_remote_soapy_sdr; "
                    f"print(probe_remote_soapy_sdr({sdr}))",
                    stdout=asyncio.subprocess.PIPE,
                )

                try:
                    stdout, _ = await asyncio.wait_for(probe_process.communicate(), timeout=timeout)

                except asyncio.TimeoutError:
                    probe_process.kill()
                    raise TimeoutError(
                        "Timed out while getting SDR parameters from SoapySDR server"
                    )
            else:
                logger.info("Getting SDR parameters from local SoapySDR for SDR: %s", sdr)
                probe_process = await asyncio.create_subprocess_exec(
                    "python3",
                    "-c",
                    "from hardware.soapysdrlocalprobe import probe_local_soapy_sdr; "
                    f"print(probe_local_soapy_sdr({sdr}))",
                    stdout=asyncio.subprocess.PIPE,
                )

                try:
                    stdout, _ = await asyncio.wait_for(probe_process.communicate(), timeout=timeout)

                except asyncio.TimeoutError:
                    probe_process.kill()
                    raise TimeoutError(
                        "Timed out while getting SDR parameters from SoapySDR server"
                    )

            sdr_params_reply = eval(stdout.decode().strip())

            if sdr_params_reply["success"] is False:
                logger.error(sdr_params_reply)
                raise Exception(sdr_params_reply["error"])

            sdr_params = sdr_params_reply["data"]

            logger.debug("Got SDR parameters from SoapySDR server: %s", sdr_params)
            for log_line in sdr_params_reply["log"]:
                logger.debug(log_line)

            window_function_names = list(window_functions.keys())
            fft_size_values = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]

            params = {
                "gain_values": sdr_params["gains"],
                "sample_rate_values": _select_neat_sample_rates(sdr_params["rates"]),
                "sample_rate_values_full": sdr_params["rates"],
                "fft_size_values": fft_size_values,
                "fft_window_values": window_function_names,
                "has_soapy_agc": sdr_params["has_soapy_agc"],
                "antennas": sdr_params["antennas"],
                "frequency_ranges": sdr_params.get("frequency_ranges", {}),
                "clock_info": sdr_params.get("clock_info", {}),
                "temperature": sdr_params.get("temperature", {}),
                "capabilities": _strip_sample_rate_ranges(sdr_params.get("capabilities", {})),
            }

            # try:
            #     pretty_params = json.dumps(params, indent=2, sort_keys=True)
            #     print(
            #         f"[DEBUG] SoapySDR parameters for {sdr.get('name', sdr_id)}:\\n{pretty_params}"
            #     )
            # except Exception as e:
            #     print(
            #         f"[DEBUG] SoapySDR parameters (non-JSON) for {sdr.get('name', sdr_id)}: {params}"
            #     )
            #     print(f"[DEBUG] Pretty print failed: {e}")

            sdr_parameters_cache[sdr_id] = params
            reply = {"success": True, "data": params}

        elif sdr.get("type") in ["uhd"]:
            logger.info("Getting SDR parameters from UHD/USRP for SDR: %s", sdr)

            probe_process = await asyncio.create_subprocess_exec(
                "python3",
                "-c",
                "from hardware.uhdprobe import probe_uhd_usrp; " f"print(probe_uhd_usrp({sdr}))",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    probe_process.communicate(), timeout=timeout
                )

                if probe_process.returncode != 0:
                    error_output = stderr.decode().strip()
                    raise Exception(f"UHD probe process failed: {error_output}")

            except asyncio.TimeoutError:
                probe_process.kill()
                raise TimeoutError("Timed out while getting SDR parameters from UHD/USRP")

            sdr_params_reply = eval(stdout.decode().strip())

            if sdr_params_reply["success"] is False:
                logger.error(sdr_params_reply)
                raise Exception(sdr_params_reply["error"])

            sdr_params = sdr_params_reply["data"]

            logger.debug("Got SDR parameters from UHD/USRP: %s", sdr_params)

            window_function_names = list(window_functions.keys())
            fft_size_values = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]

            params = {
                "gain_values": sdr_params["gains"],
                "sample_rate_values": [rate for rate in sdr_params["rates"] if rate >= 100000],
                "fft_size_values": fft_size_values,
                "fft_window_values": window_function_names,
                "has_uhd_agc": sdr_params.get("has_uhd_agc", False),
                "antennas": sdr_params["antennas"],
                "frequency_ranges": sdr_params.get("frequency_ranges", {}),
                "clock_info": sdr_params.get("clock_info", {}),
                "temperature": sdr_params.get("temperature", {}),
                "capabilities": _strip_sample_rate_ranges(sdr_params.get("capabilities", {})),
            }

            sdr_parameters_cache[sdr_id] = params
            reply = {"success": True, "data": params}

        elif sdr.get("type") in ["sigmfplayback"]:
            logger.info("Getting parameters from SigMF recording for SDR: %s", sdr)

            recording_path = sdr.get("recording_path", "")

            if not recording_path:
                for client_id, session in active_sdr_clients.items():
                    if session.get("sdr_id") == sdr_id:
                        recording_path = session.get("recording_path", "")
                        break

            if not recording_path:
                logger.warning("No recording_path available yet for sigmfplayback SDR")
                window_function_names = list(window_functions.keys())
                fft_size_values = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]

                params = {
                    "gain_values": [0.0],
                    "sample_rate_values": [2048000],  # Default
                    "fft_size_values": fft_size_values,
                    "fft_window_values": window_function_names,
                    "has_agc": False,
                    "has_bias_t": False,
                    "has_tuner_agc": False,
                    "has_rtl_agc": False,
                    "has_soapy_agc": False,
                    "antennas": {"tx": [], "rx": ["RX"]},
                    "frequency_ranges": {"rx": {"min": 0, "max": 6000, "step": 0.1}},
                }

                reply = {"success": True, "data": params}
                return reply

            sdr["recording_path"] = recording_path

            probe_process = await asyncio.create_subprocess_exec(
                "python3",
                "-c",
                "from hardware.sigmfprobe import probe_sigmf_recording; "
                f"print(probe_sigmf_recording({sdr}))",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    probe_process.communicate(), timeout=timeout
                )

                if probe_process.returncode != 0:
                    error_output = stderr.decode().strip()
                    raise Exception(f"SigMF probe process failed: {error_output}")

            except asyncio.TimeoutError:
                probe_process.kill()
                raise TimeoutError("Timed out while getting parameters from SigMF recording")

            sdr_params_reply = eval(stdout.decode().strip())

            if sdr_params_reply["success"] is False:
                logger.error(sdr_params_reply)
                raise Exception(sdr_params_reply["error"])

            sdr_params = sdr_params_reply["data"]

            logger.debug("Got parameters from SigMF recording: %s", sdr_params)

            window_function_names = list(window_functions.keys())
            fft_size_values = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]

            params = {
                "gain_values": sdr_params["gains"],
                "sample_rate_values": sdr_params["rates"],
                "fft_size_values": fft_size_values,
                "fft_window_values": window_function_names,
                "has_agc": sdr_params.get("has_agc", False),
                "has_bias_t": False,
                "has_tuner_agc": False,
                "has_rtl_agc": False,
                "has_soapy_agc": False,
                "antennas": {"tx": [], "rx": ["RX"]},
                "frequency_ranges": sdr_params.get("frequency_ranges", {}),
                "metadata": sdr_params.get("metadata", {}),
                "total_samples": sdr_params.get("total_samples", 0),
                "duration": sdr_params.get("duration", 0),
            }

            sdr_parameters_cache[sdr_id] = params
            reply = {"success": True, "data": params}

    except TimeoutError:
        error_msg = (
            f"Timeout occurred while getting parameters from SDR with id {sdr_id} "
            f"within {timeout} seconds timeout"
        )
        logger.error(error_msg)
        if sdr_id in sdr_parameters_cache and sdr_id != "sigmf-playback":
            logger.warning(
                "Returning cached SDR parameters for %s after timeout: %s", sdr_id, error_msg
            )
            reply["success"] = True
            reply["data"] = sdr_parameters_cache[sdr_id]
            reply["error"] = error_msg
            return reply
        reply["success"] = False
        reply["error"] = error_msg

    except Exception as e:
        error_msg = str(e)
        logger.error("Error occurred while getting parameters from SDR with id %s", sdr_id)
        logger.error(error_msg)
        if sdr_id in sdr_parameters_cache and sdr_id != "sigmf-playback":
            logger.warning(
                "Returning cached SDR parameters for %s after error: %s", sdr_id, error_msg
            )
            reply["success"] = True
            reply["data"] = sdr_parameters_cache[sdr_id]
            reply["error"] = error_msg
            return reply
        reply["success"] = False
        reply["error"] = error_msg

    return reply


# ============================================================================
# RIGS
# ============================================================================


async def get_rigs(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Get all radio rigs."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Getting radio rigs, data: {data}")
        rigs = await crud.hardware.fetch_rigs(dbsession)
        return {"success": rigs["success"], "data": rigs.get("data", [])}


async def submit_rig(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Add a new rig."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Adding rig, data: {data}")
        add_reply = await crud.hardware.add_rig(dbsession, data)

        rigs = await crud.hardware.fetch_rigs(dbsession)
        if add_reply.get("success"):
            for manager in get_all_tracker_managers().values():
                await manager.notify_hardware_changed(rig_id=add_reply.get("data", {}).get("id"))
        return {
            "success": (rigs["success"] & add_reply["success"]),
            "data": rigs.get("data", []),
        }


async def edit_rig(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Edit an existing rig."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Editing rig, data: {data}")
        edit_reply = await crud.hardware.edit_rig(dbsession, data)

        rigs = await crud.hardware.fetch_rigs(dbsession)
        if edit_reply.get("success") and data:
            for manager in get_all_tracker_managers().values():
                await manager.notify_hardware_changed(rig_id=data.get("id"))
        return {
            "success": (rigs["success"] & edit_reply["success"]),
            "data": rigs.get("data", []),
        }


async def delete_rig(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Delete a rig."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Delete rig, data: {data}")
        delete_reply = await crud.hardware.delete_rig(dbsession, data)

        rigs = await crud.hardware.fetch_rigs(dbsession)
        if delete_reply.get("success") and data:
            if isinstance(data, dict):
                for manager in get_all_tracker_managers().values():
                    await manager.notify_hardware_changed(rig_id=data.get("id"))
            elif isinstance(data, (list, tuple)):
                for rig_id in data:
                    for manager in get_all_tracker_managers().values():
                        await manager.notify_hardware_changed(rig_id=rig_id)
        return {
            "success": (rigs["success"] & delete_reply["success"]),
            "data": rigs.get("data", []),
        }


# ============================================================================
# ROTATORS
# ============================================================================


async def get_rotators(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Get all antenna rotators."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Getting antenna rotators, data: {data}")
        rotators = await crud.hardware.fetch_rotators(dbsession)
        return {"success": rotators["success"], "data": rotators.get("data", [])}


async def submit_rotator(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Add a new rotator."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Adding rotator, data: {data}")
        add_reply = await crud.hardware.add_rotator(dbsession, data)

        rotators = await crud.hardware.fetch_rotators(dbsession)
        if add_reply.get("success"):
            for manager in get_all_tracker_managers().values():
                await manager.notify_hardware_changed(
                    rotator_id=add_reply.get("data", {}).get("id")
                )
        return {
            "success": (rotators["success"] & add_reply["success"]),
            "data": rotators.get("data", []),
        }


async def edit_rotator(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Edit an existing rotator."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Editing rotator, data: {data}")
        edit_reply = await crud.hardware.edit_rotator(dbsession, data)
        logger.debug(f"Edit rotator reply: {edit_reply}")

        rotators = await crud.hardware.fetch_rotators(dbsession)
        logger.debug(f"Rotators: {rotators}")
        if edit_reply.get("success") and data:
            for manager in get_all_tracker_managers().values():
                await manager.notify_hardware_changed(rotator_id=data.get("id"))
        return {
            "success": (rotators["success"] & edit_reply["success"]),
            "data": rotators.get("data", []),
        }


async def delete_rotator(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Delete rotators."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Delete rotator, data: {data}")
        delete_reply = await crud.hardware.delete_rotators(dbsession, data)

        rotators = await crud.hardware.fetch_rotators(dbsession)
        if delete_reply.get("success") and data:
            if isinstance(data, dict):
                for manager in get_all_tracker_managers().values():
                    await manager.notify_hardware_changed(rotator_id=data.get("id"))
            elif isinstance(data, (list, tuple)):
                for rotator_id in data:
                    for manager in get_all_tracker_managers().values():
                        await manager.notify_hardware_changed(rotator_id=rotator_id)
        return {
            "success": (rotators["success"] & delete_reply["success"]),
            "data": rotators.get("data", []),
        }


async def nudge_rotator(sio: Any, data: Optional[Dict], logger: Any, sid: str) -> Dict[str, Any]:
    """Nudge rotator position."""
    logger.info(f"Nudging rotator, data: {data}")
    cmd = data.get("cmd", None) if data else None
    try:
        tracker_id = require_tracker_id((data or {}).get("tracker_id"))
    except InvalidTrackerIdError:
        return {
            "success": False,
            "error": "tracker_id_required",
            "message": "tracker_id is required",
            "data": None,
        }
    manager = get_tracker_manager(tracker_id)
    manager.send_command(cmd, data=None)
    return {"success": True, "data": None}


# ============================================================================
# CAMERAS
# ============================================================================


async def get_cameras(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Get all cameras."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Getting cameras, data: {data}")
        cameras = await crud.hardware.fetch_cameras(dbsession)
        return {"success": cameras["success"], "data": cameras.get("data", [])}


async def submit_camera(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Add a new camera."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Adding camera, data: {data}")
        add_reply = await crud.hardware.add_camera(dbsession, data)

        cameras = await crud.hardware.fetch_cameras(dbsession)
        return {
            "success": (cameras["success"] & add_reply["success"]),
            "data": cameras.get("data", []),
        }


async def edit_camera(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Edit an existing camera."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Editing camera, data: {data}")
        edit_reply = await crud.hardware.edit_camera(dbsession, data)
        logger.debug(f"Edit camera reply: {edit_reply}")

        cameras = await crud.hardware.fetch_cameras(dbsession)
        logger.debug(f"Cameras: {cameras}")
        return {
            "success": (cameras["success"] & edit_reply["success"]),
            "data": cameras.get("data", []),
        }


async def delete_camera(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Delete cameras."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Delete camera, data: {data}")
        delete_reply = await crud.hardware.delete_cameras(dbsession, data)

        cameras = await crud.hardware.fetch_cameras(dbsession)
        return {
            "success": (cameras["success"] & delete_reply["success"]),
            "data": cameras.get("data", []),
        }


# ============================================================================
# SDRs
# ============================================================================


async def get_sdrs(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Get all SDRs."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Getting SDRs, data: {data}")
        sdrs = await crud.hardware.fetch_sdrs(dbsession)

        # Add hardcoded SigMF Playback SDR for recording playback
        sdrs_list = sdrs.get("data", [])
        sigmf_playback_sdr = {
            "id": "sigmf-playback",
            "name": "SigMF Playback",
            "type": "sigmfplayback",
            "driver": "sigmfplayback",
            "serial": None,
            "host": None,
            "port": None,
            "frequency_min": 0,
            "frequency_max": 6000000000,
        }
        sdrs_list.append(sigmf_playback_sdr)

        return {"success": sdrs["success"], "data": sdrs_list}


async def submit_sdr(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Add a new SDR."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Adding SDR, data: {data}")
        add_reply = await crud.hardware.add_sdr(dbsession, data)
        logger.info(add_reply)

        sdrs = await crud.hardware.fetch_sdrs(dbsession)
        if add_reply.get("success"):
            for manager in get_all_tracker_managers().values():
                await manager.notify_hardware_changed(rig_id=add_reply.get("data", {}).get("id"))

        return {
            "success": (sdrs["success"] & add_reply["success"]),
            "data": sdrs.get("data", []),
        }


async def edit_sdr(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Edit an existing SDR."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Editing SDR, data: {data}")
        edit_reply = await crud.hardware.edit_sdr(dbsession, data)
        logger.debug(f"Edit SDR reply: {edit_reply}")

        sdrs = await crud.hardware.fetch_sdrs(dbsession)
        logger.debug(f"SDRs: {sdrs}")
        if edit_reply.get("success") and data:
            for manager in get_all_tracker_managers().values():
                await manager.notify_hardware_changed(rig_id=data.get("id"))
        return {
            "success": (sdrs["success"] & edit_reply["success"]),
            "data": sdrs.get("data", []),
        }


async def delete_sdr(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list, str]]:
    """Delete SDRs."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug(f"Delete SDR, data: {data}")
        if not data:
            return {"success": False, "data": [], "error": "No data provided"}

        delete_reply = await crud.hardware.delete_sdrs(dbsession, list(data))

        sdrs = await crud.hardware.fetch_sdrs(dbsession)
        if delete_reply.get("success") and data:
            for sdr_id in list(data):
                for manager in get_all_tracker_managers().values():
                    await manager.notify_hardware_changed(rig_id=sdr_id)
        return {
            "success": (sdrs["success"] & delete_reply["success"]),
            "data": sdrs.get("data", []),
        }


async def get_soapy_servers(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list]]:
    """Get discovered SoapySDR servers."""
    logger.debug("Getting discovered SoapySDR servers")
    return {"success": True, "data": discovered_servers}


async def get_sdr_parameters(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list, str]]:
    """Get SDR parameters."""
    async with AsyncSessionLocal() as dbsession:
        logger.debug("Getting SDR parameters")
        parameters = await _fetch_sdr_parameters(dbsession, data)
        return {
            "success": parameters["success"],
            "data": parameters.get("data", []),
            "error": parameters.get("error", None),
        }


async def get_local_soapy_sdr_devices_handler(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list, str]]:
    """Get local SoapySDR devices."""
    logger.debug("Getting local SoapySDR devices")
    devices = await get_local_soapy_sdr_devices()
    return {
        "success": devices["success"],
        "data": devices["data"],
        "error": devices["error"],
    }


async def get_local_rtl_sdr_devices_handler(
    sio: Any, data: Optional[Dict], logger: Any, sid: str
) -> Dict[str, Union[bool, list, str]]:
    """Get local RTL-SDR devices."""
    logger.debug("Getting local RTL-SDR devices")
    devices = await get_local_rtl_sdr_devices()
    return {
        "success": devices["success"],
        "data": devices["data"],
        "error": devices["error"],
    }


def register_handlers(registry):
    """Register hardware handlers with the command registry."""
    registry.register_batch(
        {
            # Rigs
            "get-rigs": (get_rigs, "data_request"),
            "submit-rig": (submit_rig, "data_submission"),
            "edit-rig": (edit_rig, "data_submission"),
            "delete-rig": (delete_rig, "data_submission"),
            # Rotators
            "get-rotators": (get_rotators, "data_request"),
            "submit-rotator": (submit_rotator, "data_submission"),
            "edit-rotator": (edit_rotator, "data_submission"),
            "delete-rotator": (delete_rotator, "data_submission"),
            "nudge-rotator": (nudge_rotator, "data_submission"),
            # Cameras
            "get-cameras": (get_cameras, "data_request"),
            "submit-camera": (submit_camera, "data_submission"),
            "edit-camera": (edit_camera, "data_submission"),
            "delete-camera": (delete_camera, "data_submission"),
            # SDRs
            "get-sdrs": (get_sdrs, "data_request"),
            "submit-sdr": (submit_sdr, "data_submission"),
            "edit-sdr": (edit_sdr, "data_submission"),
            "delete-sdr": (delete_sdr, "data_submission"),
            "get-soapy-servers": (get_soapy_servers, "data_request"),
            "get-sdr-parameters": (get_sdr_parameters, "data_request"),
            "get-local-soapy-sdr-devices": (get_local_soapy_sdr_devices_handler, "data_request"),
            "get-local-rtl-sdr-devices": (get_local_rtl_sdr_devices_handler, "data_request"),
        }
    )
