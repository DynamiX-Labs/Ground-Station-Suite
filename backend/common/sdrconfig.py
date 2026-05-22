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
from typing import Any, Dict, Optional, Union

Number = Union[int, float]
Gain = Union[int, float, str]
SerialNumber = Union[int, str]


@dataclass
class SDRConfig:
    center_freq: Number
    sample_rate: Number
    gain: Gain
    fft_size: Optional[int]
    bias_t: Union[bool, int]
    tuner_agc: bool
    rtl_agc: bool
    fft_window: Optional[str]
    fft_averaging: Optional[int]
    sdr_id: str
    fft_overlap_percent: Optional[int] = None
    fft_overlap_depth: Optional[int] = None
    recording_path: Optional[str] = None
    serial_number: Optional[SerialNumber] = None
    host: Optional[str] = None
    port: Optional[int] = None
    client_id: Optional[str] = None
    connection_type: Optional[str] = None
    driver: Optional[str] = None
    soapy_agc: Optional[bool] = None
    offset_freq: Optional[Number] = None
    antenna: Optional[str] = None
    ppm_error: Optional[Number] = None
    loop_playback: Optional[bool] = None
    sdr_settings: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "center_freq": self.center_freq,
            "sample_rate": self.sample_rate,
            "gain": self.gain,
            "bias_t": self.bias_t,
            "tuner_agc": self.tuner_agc,
            "rtl_agc": self.rtl_agc,
            "sdr_id": self.sdr_id,
        }

        if self.fft_size is not None:
            payload["fft_size"] = self.fft_size
        if self.fft_window is not None:
            payload["fft_window"] = self.fft_window
        if self.fft_averaging is not None:
            payload["fft_averaging"] = self.fft_averaging
        if self.fft_overlap_percent is not None:
            payload["fft_overlap_percent"] = self.fft_overlap_percent
        if self.fft_overlap_depth is not None:
            payload["fft_overlap_depth"] = self.fft_overlap_depth
        if self.recording_path is not None:
            payload["recording_path"] = self.recording_path
        if self.serial_number is not None:
            payload["serial_number"] = self.serial_number
        if self.host is not None:
            payload["host"] = self.host
        if self.port is not None:
            payload["port"] = self.port
        if self.client_id is not None:
            payload["client_id"] = self.client_id
        if self.connection_type is not None:
            payload["connection_type"] = self.connection_type
        if self.driver is not None:
            payload["driver"] = self.driver
        if self.soapy_agc is not None:
            payload["soapy_agc"] = self.soapy_agc
        if self.offset_freq is not None:
            payload["offset_freq"] = self.offset_freq
        if self.antenna is not None:
            payload["antenna"] = self.antenna
        if self.ppm_error is not None:
            payload["ppm_error"] = self.ppm_error
        if self.loop_playback is not None:
            payload["loop_playback"] = self.loop_playback
        if self.sdr_settings is not None:
            payload["sdr_settings"] = self.sdr_settings
        else:
            payload["sdr_settings"] = {}

        return payload
