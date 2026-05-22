# Ground Station - GFSK Decoder using GNU Radio
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
# GFSK decoder implementation based on gr-satellites by Daniel Estevez
# https://github.com/daniestevez/gr-satellites
# Copyright 2019 Daniel Estevez <daniel@destevez.net>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# GFSK (Gaussian Frequency Shift Keying) is very similar to GMSK but with
# a wider Gaussian filter (BT >= 0.5). Both are demodulated using the same
# FSK demodulator from gr-satellites.
#
# This is essentially an alias to the FSK decoder with modulation_subtype="GFSK"
# for clarity when dealing with GFSK-specific satellites.

from .fskdecoder import DecoderStatus, FSKDecoder, FSKFlowgraph, FSKMessageHandler

# Create aliases for GFSK (backward compatibility)
GFSKFlowgraph = FSKFlowgraph
GFSKMessageHandler = FSKMessageHandler


class GFSKDecoder(FSKDecoder):
    """
    Real-time GFSK decoder using GNU Radio

    GFSK (Gaussian Frequency Shift Keying) uses the same demodulation
    as FSK/GMSK. The difference is in the modulation parameters (BT parameter),
    but the receiver processing is identical.

    This class extends FSKDecoder with modulation_subtype="GFSK" for proper
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
        # Initialize parent FSK decoder with GFSK modulation subtype
        super().__init__(
            iq_queue=iq_queue,
            data_queue=data_queue,
            session_id=session_id,
            config=config,
            output_dir=output_dir,
            vfo=vfo,
            batch_interval=batch_interval,
            modulation_subtype="GFSK",  # ← Specify GFSK variant
        )

        # Update thread name for GFSK
        self.name = f"GFSKDecoder-{session_id}"

        # Override transmitter mode if not already set
        if not self.transmitter_mode or self.transmitter_mode in ["GMSK", "FSK"]:
            self.transmitter_mode = (config.transmitter or {}).get("mode") or "GFSK"


# Export all necessary components
__all__ = [
    "DecoderStatus",
    "GFSKFlowgraph",
    "GFSKMessageHandler",
    "GFSKDecoder",
]
