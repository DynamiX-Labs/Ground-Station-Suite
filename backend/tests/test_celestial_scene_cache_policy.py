from datetime import datetime, timedelta, timezone

import pytest

from celestial import scene


class _DummyLogger:
    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None


def test_compute_dynamic_cache_max_age_seconds_is_bounded():
    assert (
        scene._compute_dynamic_cache_max_age_seconds(10.0)
        == scene.SKY_MOTION_DYNAMIC_TTL_MIN_SECONDS
    )
    assert (
        scene._compute_dynamic_cache_max_age_seconds(0.0)
        == scene.SKY_MOTION_DYNAMIC_TTL_MAX_SECONDS
    )


@pytest.mark.asyncio
async def test_get_vectors_snapshot_uses_dynamic_db_hit(monkeypatch):
    epoch = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "command": "Voyager 1",
        "orbit_samples_xyz_au": [[1.0, 0.0, 0.0], [1.0, 0.1, 0.0]],
        "orbit_sample_times_utc": [
            (epoch - timedelta(minutes=30)).isoformat(),
            (epoch + timedelta(minutes=30)).isoformat(),
        ],
    }
    fetch_calls = {"count": 0}

    async def _stub_load_vectors_from_db(*_args, **_kwargs):
        return None

    async def _stub_load_latest_vectors_from_db(*_args, **_kwargs):
        return {
            "payload": payload,
            "epoch_bucket_utc": epoch - timedelta(minutes=5),
        }

    def _stub_evaluate_dynamic_vectors_cache_policy(**_kwargs):
        return {
            "allowed": True,
            "reason": "ok",
            "age_seconds": 300.0,
            "max_age_seconds": 600,
            "apparent_sky_motion_deg_per_min": 0.01,
            "accuracy_target_deg": 0.25,
        }

    def _unexpected_fetch(*_args, **_kwargs):
        fetch_calls["count"] += 1
        return {"unexpected": True}

    monkeypatch.setattr(scene, "_load_vectors_from_db", _stub_load_vectors_from_db)
    monkeypatch.setattr(
        scene,
        "_load_latest_vectors_from_db",
        _stub_load_latest_vectors_from_db,
    )
    monkeypatch.setattr(
        scene,
        "_evaluate_dynamic_vectors_cache_policy",
        _stub_evaluate_dynamic_vectors_cache_policy,
    )
    monkeypatch.setattr(scene, "fetch_celestial_vectors", _unexpected_fetch)

    result = await scene._get_vectors_snapshot(
        command="Voyager 1",
        epoch=epoch,
        past_hours=1,
        future_hours=24,
        step_minutes=60,
        observer_location={"lat": 40.0, "lon": 22.0},
        force_refresh=False,
        logger=_DummyLogger(),
    )

    assert result["cache"] == "db-dynamic-hit"
    assert result["stale"] is False
    assert result["payload"]["command"] == "Voyager 1"
    assert fetch_calls["count"] == 0


@pytest.mark.asyncio
async def test_get_vectors_snapshot_fetches_when_dynamic_policy_rejects(monkeypatch):
    epoch = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    fetched_payload = {
        "command": "Voyager 1",
        "orbit_samples_xyz_au": [[1.0, 0.0, 0.0], [1.0, 0.2, 0.0]],
        "orbit_sample_times_utc": [
            (epoch - timedelta(minutes=60)).isoformat(),
            (epoch + timedelta(minutes=60)).isoformat(),
        ],
    }
    calls = {"fetch": 0, "store": 0}

    async def _stub_load_vectors_from_db(*_args, **_kwargs):
        return None

    async def _stub_load_latest_vectors_from_db(*_args, **_kwargs):
        return {
            "payload": fetched_payload,
            "epoch_bucket_utc": epoch - timedelta(minutes=40),
        }

    def _stub_evaluate_dynamic_vectors_cache_policy(**_kwargs):
        return {
            "allowed": False,
            "reason": "too-old",
            "age_seconds": 2400.0,
            "max_age_seconds": 600,
            "apparent_sky_motion_deg_per_min": 0.01,
            "accuracy_target_deg": 0.25,
        }

    def _stub_fetch_celestial_vectors(*_args, **_kwargs):
        calls["fetch"] += 1
        return dict(fetched_payload)

    async def _stub_store_vectors_in_db(*_args, **_kwargs):
        calls["store"] += 1
        return None

    monkeypatch.setattr(scene, "_load_vectors_from_db", _stub_load_vectors_from_db)
    monkeypatch.setattr(
        scene,
        "_load_latest_vectors_from_db",
        _stub_load_latest_vectors_from_db,
    )
    monkeypatch.setattr(
        scene,
        "_evaluate_dynamic_vectors_cache_policy",
        _stub_evaluate_dynamic_vectors_cache_policy,
    )
    monkeypatch.setattr(scene, "fetch_celestial_vectors", _stub_fetch_celestial_vectors)
    monkeypatch.setattr(scene, "_store_vectors_in_db", _stub_store_vectors_in_db)

    result = await scene._get_vectors_snapshot(
        command="Voyager 1",
        epoch=epoch,
        past_hours=1,
        future_hours=24,
        step_minutes=60,
        observer_location={"lat": 40.0, "lon": 22.0},
        force_refresh=False,
        logger=_DummyLogger(),
    )

    assert result["cache"] == "db-miss"
    assert result["stale"] is False
    assert result["payload"]["command"] == "Voyager 1"
    assert calls["fetch"] == 1
    assert calls["store"] == 1


@pytest.mark.asyncio
async def test_get_vectors_snapshot_cache_only_uses_latest_without_network(monkeypatch):
    epoch = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "command": "Voyager 1",
        "orbit_samples_xyz_au": [[1.0, 0.0, 0.0], [1.0, 0.1, 0.0]],
        "orbit_sample_times_utc": [
            (epoch - timedelta(minutes=30)).isoformat(),
            (epoch + timedelta(minutes=30)).isoformat(),
        ],
    }
    fetch_calls = {"count": 0}

    async def _stub_load_vectors_from_db(*_args, **_kwargs):
        return None

    async def _stub_load_latest_vectors_from_db(*_args, **_kwargs):
        return {
            "payload": payload,
            "epoch_bucket_utc": epoch - timedelta(minutes=50),
        }

    async def _stub_load_latest_vectors_for_command_from_db(*_args, **_kwargs):
        return None

    def _unexpected_fetch(*_args, **_kwargs):
        fetch_calls["count"] += 1
        return {"unexpected": True}

    monkeypatch.setattr(scene, "_load_vectors_from_db", _stub_load_vectors_from_db)
    monkeypatch.setattr(scene, "_load_latest_vectors_from_db", _stub_load_latest_vectors_from_db)
    monkeypatch.setattr(
        scene,
        "_load_latest_vectors_for_command_from_db",
        _stub_load_latest_vectors_for_command_from_db,
    )
    monkeypatch.setattr(scene, "fetch_celestial_vectors", _unexpected_fetch)

    result = await scene._get_vectors_snapshot(
        command="Voyager 1",
        epoch=epoch,
        past_hours=1,
        future_hours=24,
        step_minutes=60,
        observer_location={"lat": 40.0, "lon": 22.0},
        force_refresh=True,
        logger=_DummyLogger(),
        allow_network_fetch=False,
    )

    assert result["cache"] == "db-cache-only-latest-hit"
    assert result["stale"] is False
    assert result["payload"]["command"] == "Voyager 1"
    assert fetch_calls["count"] == 0


@pytest.mark.asyncio
async def test_get_vectors_snapshot_cache_only_falls_back_to_latest_command(monkeypatch):
    epoch = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "command": "Voyager 1",
        "orbit_samples_xyz_au": [[1.0, 0.0, 0.0], [1.0, 0.1, 0.0]],
        "orbit_sample_times_utc": [
            (epoch - timedelta(minutes=60)).isoformat(),
            (epoch + timedelta(minutes=60)).isoformat(),
        ],
    }

    async def _stub_load_vectors_from_db(*_args, **_kwargs):
        return None

    async def _stub_load_latest_vectors_from_db(*_args, **_kwargs):
        return None

    async def _stub_load_latest_vectors_for_command_from_db(*_args, **_kwargs):
        return {"payload": payload}

    monkeypatch.setattr(scene, "_load_vectors_from_db", _stub_load_vectors_from_db)
    monkeypatch.setattr(scene, "_load_latest_vectors_from_db", _stub_load_latest_vectors_from_db)
    monkeypatch.setattr(
        scene,
        "_load_latest_vectors_for_command_from_db",
        _stub_load_latest_vectors_for_command_from_db,
    )

    result = await scene._get_vectors_snapshot(
        command="Voyager 1",
        epoch=epoch,
        past_hours=12,
        future_hours=12,
        step_minutes=120,
        observer_location={"lat": 40.0, "lon": 22.0},
        force_refresh=True,
        logger=_DummyLogger(),
        allow_network_fetch=False,
    )

    assert result["cache"] == "db-cache-only-command-hit"
    assert result["stale"] is False
    assert result["payload"]["command"] == "Voyager 1"


@pytest.mark.asyncio
async def test_get_vectors_snapshot_force_refresh_uses_latest_on_fetch_failure(monkeypatch):
    epoch = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "command": "Voyager 1",
        "position_xyz_au": [1.0, 0.0, 0.0],
        "orbit_samples_xyz_au": [[1.0, 0.0, 0.0], [1.0, 0.1, 0.0]],
        "orbit_sample_times_utc": [
            (epoch - timedelta(minutes=30)).isoformat(),
            (epoch + timedelta(minutes=30)).isoformat(),
        ],
    }

    async def _stub_load_vectors_from_db(*_args, **_kwargs):
        return None

    async def _stub_load_latest_vectors_from_db(*_args, **_kwargs):
        return {"payload": payload}

    async def _stub_load_latest_vectors_for_command_from_db(*_args, **_kwargs):
        return None

    def _failing_fetch(*_args, **_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(scene, "_load_vectors_from_db", _stub_load_vectors_from_db)
    monkeypatch.setattr(scene, "_load_latest_vectors_from_db", _stub_load_latest_vectors_from_db)
    monkeypatch.setattr(
        scene,
        "_load_latest_vectors_for_command_from_db",
        _stub_load_latest_vectors_for_command_from_db,
    )
    monkeypatch.setattr(scene, "fetch_celestial_vectors", _failing_fetch)

    result = await scene._get_vectors_snapshot(
        command="Voyager 1",
        epoch=epoch,
        past_hours=1,
        future_hours=24,
        step_minutes=60,
        observer_location={"lat": 40.0, "lon": 22.0},
        force_refresh=True,
        logger=_DummyLogger(),
        allow_network_fetch=True,
    )

    assert result["cache"] == "db-stale-latest"
    assert result["stale"] is True
    assert result["payload"]["command"] == "Voyager 1"
    assert "network down" in str(result["error"])


@pytest.mark.asyncio
async def test_fetch_celestial_with_cache_preserves_stale_computed_hits(monkeypatch):
    epoch = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    targets = [
        {
            "target_type": "mission",
            "target_key": "mission:Voyager 1",
            "command": "Voyager 1",
            "name": "Voyager 1",
        }
    ]
    calls = {"snapshot": 0}

    async def _stub_get_vectors_snapshot(*_args, **_kwargs):
        calls["snapshot"] += 1
        return {
            "payload": {
                "command": "Voyager 1",
                "position_xyz_au": [1.0, 0.0, 0.0],
                "orbit_samples_xyz_au": [[1.0, 0.0, 0.0], [1.0, 0.1, 0.0]],
                "orbit_sample_times_utc": [
                    (epoch - timedelta(minutes=30)).isoformat(),
                    (epoch + timedelta(minutes=30)).isoformat(),
                ],
                "source": "horizons",
            },
            "cache": "db-stale",
            "stale": True,
            "error": "fetch failed",
        }

    monkeypatch.setattr(scene, "_get_vectors_snapshot", _stub_get_vectors_snapshot)
    scene._computed_cache.clear()

    first = await scene._fetch_celestial_with_cache(
        targets=targets,
        epoch=epoch,
        past_hours=1,
        future_hours=1,
        step_minutes=60,
        observer_location=None,
        earth_position_xyz_au=None,
        body_snapshot_by_id={},
        force_refresh=False,
        allow_network_fetch=True,
        logger=_DummyLogger(),
    )

    second = await scene._fetch_celestial_with_cache(
        targets=targets,
        epoch=epoch,
        past_hours=1,
        future_hours=1,
        step_minutes=60,
        observer_location=None,
        earth_position_xyz_au=None,
        body_snapshot_by_id={},
        force_refresh=False,
        allow_network_fetch=True,
        logger=_DummyLogger(),
    )

    scene._computed_cache.clear()

    assert calls["snapshot"] == 1
    assert first[0]["stale"] is True
    assert first[0]["cache"] == "db-stale"
    assert second[0]["cache"] == "computed-hit"
    assert second[0]["stale"] is True
    assert second[0]["error"] == "fetch failed"
