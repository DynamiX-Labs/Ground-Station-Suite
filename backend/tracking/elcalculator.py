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
# You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Calculate elevation crossing times for satellite passes."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from skyfield.api import EarthSatellite, Loader, Topos

from orbits import CentralBody, OrbitServiceError, get_propagation_input

logger = logging.getLogger("passes-worker")


def calculate_elevation_crossing_time(
    satellite_tle: dict,
    home_location: dict,
    aos_time: datetime,
    los_time: datetime,
    target_elevation: float,
) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    Calculate the times when a satellite crosses a specific elevation during a pass.

    This function samples the satellite's elevation at regular intervals during the pass
    and finds when it crosses the target elevation threshold on both the ascending portion
    (from AOS to peak) and descending portion (from peak to LOS).

    Args:
        satellite_tle: Dictionary containing 'tle1' and 'tle2' keys with TLE lines
        home_location: Dictionary containing 'lat' and 'lon' keys for observer location
        aos_time: Acquisition of Signal time (start of pass)
        los_time: Loss of Signal time (end of pass)
        target_elevation: Target elevation in degrees (e.g., 10.0)

    Returns:
        Tuple of (ascending_crossing_time, descending_crossing_time)
        Either or both can be None if elevation is never reached
    """
    try:
        # Validate inputs
        if not satellite_tle:
            logger.error("Invalid satellite TLE data (missing or None)")
            return (None, None)
        try:
            propagation_input = get_propagation_input(satellite_tle, central_body=CentralBody.EARTH)
        except OrbitServiceError as e:
            logger.error("Invalid satellite orbit data: %s", e)
            return (None, None)

        if (
            not home_location
            or home_location.get("lat") is None
            or home_location.get("lon") is None
        ):
            logger.error("Invalid home location data (missing or None)")
            return (None, None)

        # Setup Skyfield
        skyfieldloader = Loader("/tmp/skyfield-data")
        ts = skyfieldloader.timescale()

        # Create observer location
        homelat = float(home_location["lat"])
        homelon = float(home_location["lon"])
        observer = Topos(latitude_degrees=homelat, longitude_degrees=homelon)

        # Create satellite object
        satellite = EarthSatellite(propagation_input.tle1, propagation_input.tle2, ts=ts)

        # Convert datetime objects to Skyfield time
        t_aos = ts.from_datetime(aos_time)
        t_los = ts.from_datetime(los_time)

        # Sample points during the pass (every 10 seconds for precision)
        pass_duration_seconds = (los_time - aos_time).total_seconds()
        num_samples = int(pass_duration_seconds / 10) + 1  # 10 second intervals

        # Create sample times using numpy linspace (same approach as passes.py)
        t_points = t_aos + np.linspace(0, (t_los - t_aos), num_samples)

        # Create corresponding datetime objects for later use
        sample_times = [
            aos_time + timedelta(seconds=pass_duration_seconds * i / num_samples)
            for i in range(num_samples)
        ]

        # Calculate elevations at each sample point
        difference = satellite - observer
        topocentric = difference.at(t_points)
        alt, az, distance = topocentric.altaz()
        elevations = alt.degrees

        # Find peak elevation time (for reference)
        peak_idx = np.argmax(elevations)

        # Search for target elevation crossing on the ascending portion (AOS to peak)
        ascending_time = None
        for i in range(peak_idx):
            if elevations[i] >= target_elevation:
                # Found the ascending crossing point!
                ascending_time = sample_times[i]
                logger.info(
                    f"Satellite reaches {target_elevation}° elevation (ascending) at "
                    f"{ascending_time.strftime('%Y-%m-%d %H:%M:%S UTC')} "
                    f"({(ascending_time - aos_time).total_seconds():.0f}s after AOS)"
                )
                break

        # Search for target elevation crossing on the descending portion (peak to LOS)
        descending_time = None
        for i in range(peak_idx, num_samples):
            if elevations[i] <= target_elevation:
                # Found the descending crossing point!
                descending_time = sample_times[i]
                logger.info(
                    f"Satellite crosses {target_elevation}° elevation (descending) at "
                    f"{descending_time.strftime('%Y-%m-%d %H:%M:%S UTC')} "
                    f"({(los_time - descending_time).total_seconds():.0f}s before LOS)"
                )
                break

        # Log warnings if elevation never reached
        if not ascending_time and not descending_time:
            peak_el = elevations[peak_idx]
            logger.warning(
                f"Satellite never reaches {target_elevation}° elevation "
                f"(peak elevation: {peak_el:.1f}°)"
            )

        return (ascending_time, descending_time)

    except Exception as e:
        logger.error(f"Error calculating elevation crossing time: {e}")
        return (None, None)
