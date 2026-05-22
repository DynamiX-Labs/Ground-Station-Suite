import math
from datetime import datetime, timezone

import pytest

from celestial import scene


class _DummyLogger:
    def debug(self, *_args, **_kwargs):
        return None

    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None


@pytest.mark.asyncio
async def test_build_celestial_tracks_supports_sun_body_target(monkeypatch):
    async def _stub_observer_location():
        return {
            "id": "test-observer",
            "name": "Test",
            "lat": 40.5798912,
            "lon": 22.9670912,
            "alt_m": 0.0,
        }

    monkeypatch.setattr(scene, "_load_observer_location", _stub_observer_location)

    payload = {
        "epoch": datetime(2026, 6, 21, 10, 0, tzinfo=timezone.utc).isoformat(),
        "past_hours": 1,
        "future_hours": 1,
        "step_minutes": 30,
        "celestial": [{"target_type": "body", "body_id": "sun", "name": "Sun"}],
    }

    result = await scene.build_celestial_tracks(data=payload, logger=_DummyLogger())

    assert result.get("success") is True
    data = result.get("data") or {}
    rows = data.get("celestial") or []
    assert len(rows) == 1

    row = rows[0]
    assert row.get("target_type") == "body"
    assert row.get("target_key") == "body:sun"
    assert row.get("body_id") == "sun"
    assert row.get("command") == "sun"
    assert row.get("source") == "offline-solar-system"
    assert row.get("cache") == "offline"
    assert row.get("stale") is False
    assert row.get("position_xyz_au") == [0.0, 0.0, 0.0]

    sky_position = row.get("sky_position") or {}
    assert math.isfinite(float(sky_position.get("az_deg")))
    assert math.isfinite(float(sky_position.get("el_deg")))
