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

"""VFO updates for satellite tracking - applies doppler correction to internal VFOs."""

import logging

from vfos.state import INTERNAL_VFO_NUMBER, VFOManager

logger = logging.getLogger("vfo-state")


async def handle_vfo_updates_for_tracking(sockio, tracking_data):
    """
    Apply doppler correction to internal observation VFOs.

    User VFOs: Managed entirely in the UI (client-side)
    Internal VFOs: Updated here with doppler-corrected frequencies for automated observations

    This function is called by tracker/messages.py whenever new doppler data arrives
    from the tracker process. It updates the center frequency of any internal VFO
    that is locked to a transmitter.

    Args:
        sockio: Socket.IO server instance (unused here, but available)
        tracking_data: Dictionary containing rig_data with transmitters doppler data
                      Format: {"rig_data": {"transmitters": [...]}, ...}
    """
    # Extract transmitter doppler data
    rig_data = tracking_data.get("rig_data", {})
    transmitters = rig_data.get("transmitters", [])

    if not transmitters:
        return

    # Get VFO manager instance
    vfo_manager = VFOManager()

    # Get all internal observation sessions
    # Internal sessions have IDs like "internal:observation-uuid"
    all_sessions = vfo_manager.get_all_session_ids()
    internal_sessions = [s for s in all_sessions if VFOManager.is_internal_session(s)]

    if not internal_sessions:
        return

    # For each internal session, check all VFOs (1-INTERNAL_VFO_NUMBER)
    updates_applied = 0
    for session_id in internal_sessions:
        for vfo_num in range(1, INTERNAL_VFO_NUMBER + 1):  # VFOs numbered 1-INTERNAL_VFO_NUMBER
            vfo_state = vfo_manager.get_vfo_state(session_id, vfo_num)

            # Skip if VFO doesn't exist or is not active
            if not vfo_state or not vfo_state.active:
                continue

            # Skip if VFO is not locked to a transmitter
            locked_tx_id = vfo_state.locked_transmitter_id
            if locked_tx_id == "none":
                continue

            # Find matching transmitter in doppler data
            for transmitter in transmitters:
                if transmitter.get("id") == locked_tx_id:
                    # Get doppler-corrected downlink frequency
                    doppler_freq = transmitter.get("downlink_observed_freq", 0)

                    if doppler_freq > 0:
                        # Only update if frequency changed by more than 10 Hz
                        # This prevents unnecessary updates and log spam
                        freq_diff = abs(doppler_freq - vfo_state.center_freq)
                        if freq_diff > 10:
                            # Update VFO frequency with doppler-corrected value
                            vfo_manager.update_vfo_state(
                                session_id=session_id,
                                vfo_id=vfo_num,
                                center_freq=int(doppler_freq),
                            )

                            updates_applied += 1
                            logger.debug(
                                f"Applied doppler correction to internal VFO: "
                                f"session={session_id}, vfo={vfo_num}, "
                                f"tx={locked_tx_id}, freq={doppler_freq/1e6:.6f} MHz "
                                f"(diff={freq_diff/1e3:.2f} kHz)"
                            )
                    break

    # Log summary if updates were applied (debug level to reduce log spam)
    if updates_applied > 0:
        logger.debug(
            f"Applied doppler correction to {updates_applied} internal VFO(s) "
            f"across {len(internal_sessions)} observation session(s)"
        )
