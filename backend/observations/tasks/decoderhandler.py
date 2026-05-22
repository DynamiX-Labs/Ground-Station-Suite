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

"""Decoder task handler - manages decoder VFO configuration and lifecycle."""

import traceback
from typing import Any, Dict

from sqlalchemy import select

from common.logger import logger
from db import AsyncSessionLocal
from db.models import Satellites, Transmitters
from pipeline.registries.decoderregistry import decoder_registry
from vfos.state import VFOManager


class DecoderHandler:
    """Handles decoder task configuration and lifecycle for observations."""

    def __init__(self, process_manager: Any):
        """
        Initialize the decoder handler.

        Args:
            process_manager: ProcessManager instance for decoder lifecycle
        """
        self.process_manager = process_manager

    async def start_decoder_task(
        self,
        observation_id: str,
        session_id: str,
        sdr_id: str,
        sdr_config: Dict[str, Any],
        task_config: Dict[str, Any],
        vfo_number: int,
    ) -> bool:
        """
        Start a decoder task.

        Args:
            observation_id: The observation ID
            session_id: The session ID
            sdr_id: The SDR ID
            sdr_config: SDR configuration dict
            task_config: Task configuration dict
            vfo_number: VFO number to assign (1-10)

        Returns:
            True if decoder started successfully
        """
        try:
            # Get decoder configuration
            transmitter_id = task_config.get("transmitter_id", "none")
            decoder_type = task_config.get("decoder_type", "none")
            center_freq = task_config.get("frequency", sdr_config["center_freq"])
            modulation = task_config.get("modulation", "none")
            bandwidth = task_config.get("bandwidth", 40000)

            # Fetch transmitter and satellite info from database
            transmitter_info = None
            satellite_info = None

            if transmitter_id and transmitter_id != "none":
                transmitter_info, satellite_info = await self._fetch_transmitter_info(
                    transmitter_id, center_freq, bandwidth, task_config
                )
                if transmitter_info:
                    center_freq = transmitter_info["center_frequency"]
                    modulation = transmitter_info.get("mode", modulation)

            # Fallback if no transmitter info available
            if not transmitter_info:
                transmitter_info = {
                    "description": f"Observation {observation_id} Signal",
                    "mode": decoder_type.upper(),
                    "center_frequency": center_freq,
                    "bandwidth": bandwidth,
                }
                logger.warning(
                    f"No transmitter info for observation {observation_id} - using defaults"
                )

            # Configure VFO
            vfo_manager = VFOManager()
            vfo_manager.configure_internal_vfo(
                observation_id=observation_id,
                vfo_number=vfo_number,
                center_freq=center_freq,
                bandwidth=bandwidth,
                modulation=modulation,
                decoder=decoder_type,
                locked_transmitter_id=transmitter_id,
                session_id=session_id,
            )

            logger.info(
                f"Configured VFO {vfo_number} for {decoder_type} decoder on {transmitter_id}"
            )

            # Start decoder process
            decoder_class = decoder_registry.get_decoder_class(decoder_type)
            if not decoder_class:
                logger.warning(f"Decoder class not found for type: {decoder_type}")
                return False

            process_info = self.process_manager.processes.get(sdr_id)
            if not process_info:
                logger.error(f"No SDR process found for {sdr_id}")
                return False

            data_queue = process_info["data_queue"]

            decoder_kwargs = {
                "sdr_id": sdr_id,
                "session_id": session_id,
                "decoder_class": decoder_class,
                "data_queue": data_queue,
                "audio_out_queue": None,  # No audio streaming for observations
                "output_dir": "data/decoded",
                "vfo_center_freq": center_freq,
                "vfo": vfo_number,
                "decoder_param_overrides": {},  # Use defaults from transmitter
                "caller": "decoderhandler.py:start_decoder_task",
            }

            # Add transmitter config if decoder supports it
            if decoder_registry.supports_transmitter_config(decoder_type):
                decoder_kwargs["satellite"] = satellite_info
                decoder_kwargs["transmitter"] = transmitter_info

            success = self.process_manager.start_decoder(**decoder_kwargs)
            if success:
                logger.info(f"Started {decoder_type} decoder for observation {observation_id}")
                return True
            else:
                logger.error(
                    f"Failed to start {decoder_type} decoder for observation {observation_id}"
                )
                return False

        except Exception as e:
            logger.error(f"Error starting decoder: {e}")
            logger.error(traceback.format_exc())
            return False

    def stop_decoder_task(self, sdr_id: str, session_id: str, vfo_number: int) -> bool:
        """
        Stop a decoder task.

        Args:
            sdr_id: The SDR ID
            session_id: The session ID
            vfo_number: VFO number

        Returns:
            True if decoder stopped successfully
        """
        try:
            self.process_manager.stop_decoder(sdr_id, session_id, vfo_number)
            logger.info(f"Stopped decoder for session {session_id} VFO {vfo_number}")
            return True
        except Exception as e:
            logger.warning(f"Error stopping decoder: {e}")
            return False

    async def _fetch_transmitter_info(
        self, transmitter_id: str, center_freq: float, bandwidth: float, task_config: Dict[str, Any]
    ) -> tuple:
        """
        Fetch transmitter and satellite information from database.

        Args:
            transmitter_id: Transmitter ID
            center_freq: Default center frequency
            bandwidth: Default bandwidth
            task_config: Task configuration dict

        Returns:
            Tuple of (transmitter_info, satellite_info)
        """
        try:
            async with AsyncSessionLocal() as db_session:
                # Fetch transmitter
                result = await db_session.execute(
                    select(Transmitters).where(Transmitters.id == transmitter_id)
                )
                transmitter_record = result.scalar_one_or_none()

                if not transmitter_record:
                    return None, None

                center_freq = task_config.get("frequency", transmitter_record.downlink_low)

                transmitter_info = {
                    "id": transmitter_record.id,
                    "description": transmitter_record.description,
                    "mode": transmitter_record.mode,
                    "baud": transmitter_record.baud,
                    "downlink_low": transmitter_record.downlink_low,
                    "downlink_high": transmitter_record.downlink_high,
                    "center_frequency": center_freq,
                    "bandwidth": bandwidth,
                    "norad_cat_id": transmitter_record.norad_cat_id,
                }

                # Fetch satellite info
                sat_result = await db_session.execute(
                    select(Satellites).where(Satellites.norad_id == transmitter_record.norad_cat_id)
                )
                satellite_record = sat_result.scalar_one_or_none()
                satellite_info = None
                if satellite_record:
                    satellite_info = {
                        "norad_id": satellite_record.norad_id,
                        "name": satellite_record.name,
                        "alternative_name": satellite_record.alternative_name,
                        "status": satellite_record.status,
                        "image": satellite_record.image,
                    }

                logger.info(f"Loaded transmitter {transmitter_record.description} for decoder task")
                return transmitter_info, satellite_info

        except Exception as e:
            logger.warning(f"Failed to fetch transmitter {transmitter_id}: {e}")
            logger.warning(traceback.format_exc())
            return None, None
