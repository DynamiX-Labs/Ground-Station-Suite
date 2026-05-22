#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Satellite Configuration Service
#
# Loads satellite decoder configuration from:
# 1. gr-satellites YAML database (381 satellites)
# 2. User overrides (data/configs/satellite_overrides.json)
#
# Priority: User overrides > YAML > Smart defaults

import json
import logging
import pathlib
from typing import Any, Dict, Optional

try:
    from satellites.satyaml.satyaml import SatYAML
except Exception:
    SatYAML = None

from constants import GR_SATELLITES_FRAMING_MAP, FramingType

logger = logging.getLogger("satellite-config")


class SatelliteConfigService:
    """
    Service to load and manage satellite decoder configurations.

    Combines data from:
    - gr-satellites YAML database (official satellite configs)
    - User overrides (tested/verified configurations)

    Priority order:
    1. User override (if exists) - manually verified configs
    2. YAML deviation (if specified) - official satellite team data
    3. Smart default (estimated) - industry standard heuristics
    4. Fallback - last resort defaults
    """

    def __init__(self, overrides_path: str = "backend/data/configs/satellite_overrides.json"):
        """
        Initialize satellite config service.

        Args:
            overrides_path: Path to user overrides JSON file (relative to project root)
        """
        self.overrides_path = pathlib.Path(overrides_path)
        self.overrides = self._load_overrides()

        # Initialize gr-satellites YAML parser
        if SatYAML is None:
            logger.warning("SatYAML unavailable; satellite YAML lookup disabled")
            self.satyaml = None
        else:
            try:
                self.satyaml = SatYAML()
                logger.info(
                    f"Loaded gr-satellites database with {len(list(self.satyaml.yaml_files()))} satellites"
                )
            except Exception as e:
                logger.error(f"Failed to initialize SatYAML: {e}")
                self.satyaml = None

    def _load_overrides(self) -> Dict[str, Any]:
        """Load user overrides from JSON file."""
        if not self.overrides_path.exists():
            logger.info(f"No overrides file found at {self.overrides_path}")
            return {}

        try:
            with open(self.overrides_path, "r") as f:
                overrides: Dict[str, Any] = json.load(f)
            logger.info(
                f"Loaded overrides for {len(overrides)} satellites from {self.overrides_path}"
            )
            return overrides
        except Exception as e:
            logger.error(f"Failed to load overrides: {e}")
            return {}

    def save_overrides(self):
        """Save current overrides to JSON file."""
        try:
            # Create directory if it doesn't exist
            self.overrides_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.overrides_path, "w") as f:
                json.dump(self.overrides, f, indent=2)
            logger.info(f"Saved overrides to {self.overrides_path}")
        except Exception as e:
            logger.error(f"Failed to save overrides: {e}")

    def get_satellite_by_norad(self, norad_id: int) -> Optional[Dict[str, Any]]:
        """
        Get satellite configuration by NORAD ID from gr-satellites.

        Args:
            norad_id: NORAD catalog number

        Returns:
            Satellite config dict or None if not found
        """
        if not self.satyaml:
            logger.warning("SatYAML not available")
            return None

        try:
            result: Optional[Dict[str, Any]] = self.satyaml.search_norad(norad_id)
            return result
        except ValueError:
            logger.debug(f"Satellite with NORAD {norad_id} not found in gr-satellites")
            return None
        except Exception as e:
            logger.error(f"Error loading satellite {norad_id}: {e}")
            return None

    def get_satellite_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get satellite configuration by name from gr-satellites.
        Uses fuzzy matching (case-insensitive, ignores punctuation/spaces).

        Args:
            name: Satellite name (e.g., "ARCCUBE-1", "AO-73")

        Returns:
            Satellite config dict or None if not found
        """
        if not self.satyaml:
            logger.warning("SatYAML not available")
            return None

        try:
            result: Optional[Dict[str, Any]] = self.satyaml.search_name(name)
            return result
        except ValueError:
            logger.debug(f"Satellite '{name}' not found in gr-satellites")
            return None
        except Exception as e:
            logger.error(f"Error loading satellite '{name}': {e}")
            return None

    def get_transmitter_config(
        self, norad_id: int, frequency: Optional[float] = None, baudrate: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get best matching transmitter configuration for given parameters.

        Args:
            norad_id: NORAD catalog number
            frequency: Downlink frequency in Hz (optional)
            baudrate: Baud rate (optional)

        Returns:
            Transmitter config dict or None if satellite not found
        """
        sat = self.get_satellite_by_norad(norad_id)
        if not sat or "transmitters" not in sat:
            return None

        transmitters = sat["transmitters"]

        # Match by frequency (within 100 kHz tolerance)
        if frequency:
            for tx_name, tx in transmitters.items():
                freq_match: Dict[str, Any] = tx
                if abs(freq_match.get("frequency", 0) - frequency) < 100e3:
                    return freq_match

        # Match by baudrate
        if baudrate:
            for tx_name, tx in transmitters.items():
                baud_match: Dict[str, Any] = tx
                if baud_match.get("baudrate") == baudrate:
                    return baud_match

        # Return first transmitter as fallback
        first_tx: Dict[str, Any] = list(transmitters.values())[0]
        return first_tx

    def get_decoder_parameters(
        self, norad_id: int, baudrate: int, frequency: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get decoder parameters for a satellite, with priority system:
        1. User overrides (if exist)
        2. gr-satellites YAML (if deviation specified)
        3. Smart defaults (estimated from baudrate/modulation)
        4. Fallback defaults

        Args:
            norad_id: NORAD catalog number
            baudrate: Baud rate
            frequency: Downlink frequency in Hz (optional, helps match transmitter)

        Returns:
            Dict with decoder parameters:
            - baudrate: int
            - modulation: str
            - framing: str
            - deviation: float
            - precoding: str (optional)
            - frame_size: int (optional)
            - source: str (where config came from)
        """
        params = {
            "baudrate": baudrate,
            "modulation": "FSK",
            "framing": FramingType.AX25,
            "deviation": 5000,  # Fallback
            "source": "fallback",
        }

        # Check user overrides first
        norad_str = str(norad_id)
        if norad_str in self.overrides:
            override = self.overrides[norad_str]
            baudrate_str = str(baudrate)

            if "transmitters" in override and baudrate_str in override["transmitters"]:
                tx_override = override["transmitters"][baudrate_str]
                logger.info(f"Using override config for NORAD {norad_id} @ {baudrate} baud")

                # Apply overrides
                if "deviation" in tx_override:
                    params["deviation"] = tx_override["deviation"]
                    params["source"] = "user_override"
                if "framing" in tx_override:
                    params["framing"] = tx_override["framing"]
                if "modulation" in tx_override:
                    params["modulation"] = tx_override["modulation"]

                return params

        # Load from gr-satellites YAML
        tx = self.get_transmitter_config(norad_id, frequency, baudrate)
        if tx:
            # Found satellite in gr-satellites database
            sat = self.get_satellite_by_norad(norad_id)
            sat_name = sat.get("name", f"NORAD-{norad_id}") if sat else f"NORAD-{norad_id}"

            params["modulation"] = tx.get("modulation", "FSK")
            params["framing"] = self._map_framing(tx.get("framing", "AX.25"))

            # Use YAML deviation if specified, otherwise estimate from satellite's baudrate
            if "deviation" in tx:
                params["deviation"] = tx["deviation"]
                params["source"] = "satellite_config"
                source_label = "gr-satellites (explicit)"
            else:
                # Estimate from satellite's modulation and baudrate
                # Still considered satellite_config since we found the satellite in database
                params["deviation"] = self._estimate_deviation(tx)
                params["source"] = "satellite_config"
                source_label = "gr-satellites (estimated deviation)"

            logger.info(
                f"{sat_name} (NORAD {norad_id}) | "
                f"{params['modulation']}, {baudrate}bd, dev={params['deviation']}Hz, {params['framing']} | src: {source_label}"
            )

            # Optional parameters
            if "precoding" in tx:
                params["precoding"] = tx["precoding"]
            if "frame size" in tx:
                params["frame_size"] = tx["frame size"]
        else:
            # No YAML data, use smart defaults
            logger.warning(
                f"NORAD {norad_id} not found in gr-satellites database, using smart defaults"
            )
            params["deviation"] = baudrate / 2  # Narrow FSK default
            params["source"] = "smart_default"

        return params

    def _map_framing(self, gr_sat_framing: str) -> str:
        """
        Map gr-satellites framing to decoder framing protocol.

        Args:
            gr_sat_framing: Framing name from gr-satellites YAML

        Returns:
            Decoder framing protocol: 'ax25', 'usp', 'geoscan', etc.
        """
        result = GR_SATELLITES_FRAMING_MAP.get(gr_sat_framing, FramingType.AX25)
        return str(result)

    def _estimate_deviation(self, tx: Dict[str, Any]) -> float:
        """
        Estimate deviation if not specified in YAML.
        Uses industry-standard heuristics based on modulation and baudrate.

        Args:
            tx: Transmitter config dict

        Returns:
            Estimated deviation in Hz
        """
        modulation = tx.get("modulation", "FSK")
        baudrate = tx.get("baudrate", 9600)

        if modulation in ["FSK", "GMSK"]:
            # Narrow FSK: deviation ≈ baudrate/2
            # This gives modulation index h = 0.5 (typical for MSK/GMSK)
            return float(baudrate / 2)

        elif modulation == "AFSK":
            # Wide AFSK: use af_carrier if available, else baudrate * 2
            if "af_carrier" in tx:
                # AFSK deviation is typically larger
                af_carrier: float = float(tx["af_carrier"])
                # Common AFSK uses ±deviation around af_carrier
                # Example: 1200 baud AFSK with 1200/2200 Hz tones → deviation ~500 Hz
                return float(abs(tx.get("deviation", af_carrier / 3)))
            return float(baudrate * 2)  # Fallback: wide deviation

        elif modulation in ["BPSK", "DBPSK", "BPSK Manchester", "DBPSK Manchester"]:
            # BPSK doesn't use frequency deviation, but return something
            # reasonable for compatibility
            return 5000.0  # Not used, but prevents errors

        # Unknown modulation: conservative default
        logger.warning(f"Unknown modulation '{modulation}', using conservative default")
        return float(baudrate / 2)

    def add_override(
        self,
        norad_id: int,
        baudrate: int,
        deviation: float,
        framing: Optional[str] = None,
        verified: bool = False,
        notes: Optional[str] = None,
    ):
        """
        Add or update a user override for a satellite transmitter.

        Args:
            norad_id: NORAD catalog number
            baudrate: Baud rate
            deviation: Deviation in Hz
            framing: Framing protocol (optional)
            verified: Whether this config is verified to work
            notes: User notes about this configuration
        """
        norad_str = str(norad_id)
        baudrate_str = str(baudrate)

        # Initialize satellite entry if needed
        if norad_str not in self.overrides:
            # Try to get satellite name from gr-satellites
            sat = self.get_satellite_by_norad(norad_id)
            sat_name = sat.get("name", f"NORAD-{norad_id}") if sat else f"NORAD-{norad_id}"

            self.overrides[norad_str] = {"name": sat_name, "norad": norad_id, "transmitters": {}}

        # Add transmitter override
        if "transmitters" not in self.overrides[norad_str]:
            self.overrides[norad_str]["transmitters"] = {}

        self.overrides[norad_str]["transmitters"][baudrate_str] = {
            "deviation": deviation,
            "verified": verified,
        }

        if framing:
            self.overrides[norad_str]["transmitters"][baudrate_str]["framing"] = framing

        if notes:
            self.overrides[norad_str]["notes"] = notes

        logger.info(
            f"Added override for NORAD {norad_id} @ {baudrate} baud: deviation={deviation} Hz"
        )
        self.save_overrides()
