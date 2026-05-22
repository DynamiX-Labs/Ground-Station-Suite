from datetime import datetime, timezone

from celestial.observermath import compute_observer_sky_position
from celestial.solarsystem import compute_body_position_heliocentric_au


def test_sun_is_above_horizon_for_midday_observer_sample():
    """
    Regression guard for Earth-vector orientation in local az/el projection.

    At Thessaloniki around local noon near summer solstice, the Sun must be
    comfortably above the horizon. If Earth's heliocentric vector sign flips,
    this elevation becomes strongly negative.
    """
    epoch = datetime(2026, 6, 21, 10, 0, tzinfo=timezone.utc)
    earth_position = compute_body_position_heliocentric_au("earth", epoch)

    observer_view = compute_observer_sky_position(
        target_heliocentric_xyz_au=[0.0, 0.0, 0.0],
        earth_heliocentric_xyz_au=earth_position,
        epoch=epoch,
        observer_lat_deg=40.5798912,
        observer_lon_deg=22.9670912,
    )

    sky_position = observer_view.get("sky_position") or {}
    elevation_deg = float(sky_position.get("el_deg"))
    assert elevation_deg > 40.0
