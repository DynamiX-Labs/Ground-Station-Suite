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


from dataclasses import dataclass
from typing import List, Optional, Type

from demodulators.amdemodulator import AMDemodulator
from demodulators.fmdemodulator import FMDemodulator
from demodulators.fmstereodemodulator import FMStereoDemodulator
from demodulators.ssbdemodulator import SSBDemodulator


@dataclass
class DemodulatorCapabilities:
    """Capabilities and requirements for a demodulator"""

    name: str
    demodulator_class: Type
    default_bandwidth: int  # Default bandwidth in Hz
    modes: List[str]  # Supported modes (e.g., ["usb", "lsb", "cw"] for SSB)
    description: str

    def supports_mode(self, mode: str) -> bool:
        """Check if this demodulator supports a specific mode"""
        return mode in self.modes if self.modes else True


class DemodulatorRegistry:
    """
    Singleton registry for audio demodulators.

    This centralizes all demodulator capabilities and requirements,
    making it easy to add new demodulators and maintain consistency.

    Demodulators convert IQ samples to audio samples.
    """

    _instance: Optional["DemodulatorRegistry"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Define capabilities for each demodulator
        self._demodulators = {
            "fm": DemodulatorCapabilities(
                name="fm",
                demodulator_class=FMDemodulator,
                default_bandwidth=12500,  # 12.5 kHz for narrow FM
                modes=[],  # FM has no sub-modes
                description="Frequency Modulation demodulator",
            ),
            "wfm": DemodulatorCapabilities(
                name="wfm",
                demodulator_class=FMStereoDemodulator,
                default_bandwidth=200000,  # 200 kHz for wide FM broadcast
                modes=[],  # WFM has no sub-modes
                description="Wide FM Stereo demodulator for broadcast",
            ),
            "am": DemodulatorCapabilities(
                name="am",
                demodulator_class=AMDemodulator,
                default_bandwidth=10000,  # 10 kHz for AM
                modes=[],  # AM has no sub-modes
                description="Amplitude Modulation demodulator",
            ),
            "ssb": DemodulatorCapabilities(
                name="ssb",
                demodulator_class=SSBDemodulator,
                default_bandwidth=2500,  # 2.5 kHz for SSB/CW
                modes=["usb", "lsb", "cw"],  # SSB supports multiple modes
                description="Single Sideband demodulator (USB/LSB/CW)",
            ),
        }

        self._initialized = True

    def get_capabilities(self, demod_name: str) -> Optional[DemodulatorCapabilities]:
        """Get capabilities for a demodulator by name"""
        return self._demodulators.get(demod_name)

    def get_demodulator_class(self, demod_name: str) -> Optional[Type]:
        """Get demodulator class by name"""
        caps = self.get_capabilities(demod_name)
        return caps.demodulator_class if caps else None

    def get_default_bandwidth(self, demod_name: str) -> Optional[int]:
        """Get default bandwidth for a demodulator"""
        caps = self.get_capabilities(demod_name)
        return caps.default_bandwidth if caps else None

    def supports_mode(self, demod_name: str, mode: str) -> bool:
        """Check if demodulator supports a specific mode"""
        caps = self.get_capabilities(demod_name)
        return caps.supports_mode(mode) if caps else False

    def list_demodulators(self) -> List[str]:
        """List all available demodulator names"""
        return list(self._demodulators.keys())

    def exists(self, demod_name: str) -> bool:
        """Check if a demodulator exists in the registry"""
        return demod_name in self._demodulators


# Singleton instance
demodulator_registry = DemodulatorRegistry()
