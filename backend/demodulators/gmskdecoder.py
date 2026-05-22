# Ground Station - GMSK Decoder using GNU Radio
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
# GMSK decoder implementation based on gr-satellites by Daniel Estevez
# https://github.com/daniestevez/gr-satellites
# Copyright 2019 Daniel Estevez <daniel@destevez.net>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# GMSK (Gaussian Minimum Shift Keying) is a specific variant of FSK with
# Gaussian pulse shaping and modulation index = 0.5. It uses the same
# FSK demodulator from gr-satellites.
#
# This extends the FSK decoder with modulation_subtype="GMSK"
# for clarity when dealing with GMSK-specific satellites.

from .fskdecoder import DecoderStatus, FSKDecoder, FSKFlowgraph, FSKMessageHandler

# Create aliases for GMSK (backward compatibility)
GMSKFlowgraph = FSKFlowgraph
GMSKMessageHandler = FSKMessageHandler


class GMSKDecoder(FSKDecoder):
    """
    Real-time GMSK decoder using GNU Radio

    GMSK (Gaussian Minimum Shift Keying) uses the same demodulation
    as FSK/GFSK. The difference is in the modulation parameters (BT parameter
    and modulation index), but the receiver processing is identical.

    This class extends FSKDecoder with modulation_subtype="GMSK" for proper
    identification in logs and metadata.
    """

    def __init__(
        self,
        iq_queue,
        data_queue,
        session_id,
        config,  # Pre-resolved DecoderConfig from DecoderConfigService
        output_dir="data/decoded",
        vfo=None,
        batch_interval=5.0,
    ):
        # Initialize parent FSK decoder with GMSK modulation subtype
        super().__init__(
            iq_queue=iq_queue,
            data_queue=data_queue,
            session_id=session_id,
            config=config,
            output_dir=output_dir,
            vfo=vfo,
            batch_interval=batch_interval,
            modulation_subtype="GMSK",  # ← Specify GMSK variant
        )

        # Update thread name for GMSK
        self.name = f"GMSKDecoder-{session_id}"

        # Override transmitter mode if not already set
        if not self.transmitter_mode or self.transmitter_mode in ["GFSK", "FSK"]:
            self.transmitter_mode = (config.transmitter or {}).get("mode") or "GMSK"


# Export all necessary components
__all__ = [
    "DecoderStatus",
    "GMSKFlowgraph",
    "GMSKMessageHandler",
    "GMSKDecoder",
]
