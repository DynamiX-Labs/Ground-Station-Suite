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


import numpy as np
from skyfield.api import EarthSatellite, Topos, load


def calculate_doppler_shift(
    tle_line1,
    tle_line2,
    observer_lat,
    observer_lon,
    observer_elevation,
    transmitted_freq_hz,
    time=None,
):
    """
    Calculate the Doppler shift for a satellite at a given time.

    Parameters:
    -----------
    tle_line1, tle_line2 : str
        The two-line element set for the satellite
    observer_lat, observer_lon : float
        Observer's latitude and longitude in degrees
    observer_elevation : float
        Observer's elevation in meters
    transmitted_freq_mhz : float
        Transmitted frequency in MHz
    time : skyfield.timelib.Time, optional
        Time of observation, defaults to current time

    Returns:
    --------
    observed_freq_mhz : float
        The Doppler-shifted frequency in MHz
    doppler_shift_hz : float
        The Doppler shift in Hz
    """
    # Load the timescale
    ts = load.timescale()

    # Set the time (now if not specified)
    if time is None:
        time = ts.now()

    # Create satellite object from TLEs
    satellite = EarthSatellite(tle_line1, tle_line2, name="Satellite", ts=ts)

    # Define the ground station
    topos = Topos(
        latitude_degrees=observer_lat,
        longitude_degrees=observer_lon,
        elevation_m=observer_elevation,
    )

    # Get the difference directly using the observation from the topos
    difference = satellite - topos

    # Calculate position at the specified time
    topocentric = difference.at(time)

    # Get the range rate (radial velocity) in km/s
    # The radial_velocity needs to be accessed from the velocity property
    # First, get the position and velocity vectors
    pos, vel = topocentric.position.km, topocentric.velocity.km_per_s

    # Calculate the radial velocity (component of velocity along the line of sight)
    # This is done by taking the dot product of the unit position vector and velocity vector
    pos_unit = pos / np.sqrt(np.sum(pos**2))  # Normalize position to get unit vector
    range_rate = np.dot(pos_unit, vel)  # Dot product gives radial component

    # Speed of light in km/s
    c = 299792.458  # speed of light in km/s

    # Calculate Doppler shift
    doppler_factor = 1.0 - (range_rate / c)

    # Calculate observed frequency
    observed_freq_hz = transmitted_freq_hz * doppler_factor

    # Calculate the shift in Hz
    doppler_shift_hz = observed_freq_hz - transmitted_freq_hz

    return round(float(observed_freq_hz), 0), round(float(doppler_shift_hz), 0)
