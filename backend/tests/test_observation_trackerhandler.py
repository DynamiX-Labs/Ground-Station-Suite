# Copyright (c) 2026 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

import pytest

from observations.tasks.trackerhandler import TrackerHandler


class _DummyTrackerManager:
    def __init__(self, tracking_state=None):
        self.tracking_state = tracking_state or {}

    async def get_tracking_state(self):
        return dict(self.tracking_state)


@pytest.mark.asyncio
async def test_start_tracker_unparks_before_tracking_when_requested(monkeypatch):
    manager = _DummyTrackerManager({"rotator_state": "parked"})
    update_calls = []

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_tracker_manager",
        lambda _tracker_id: manager,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_assigned_tracker_for_rotator",
        lambda _rotator_id: "target-1",
    )

    async def _mock_update(tracker_id, value, requester_sid=None):
        update_calls.append(
            {"tracker_id": tracker_id, "value": value, "requester_sid": requester_sid}
        )
        return {"success": True}

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )

    handler = TrackerHandler()
    result = await handler.start_tracker_task(
        observation_id="obs-1",
        satellite={"norad_id": 25544, "group_id": "grp-1", "name": "ISS"},
        rotator_config={
            "id": "rot-1",
            "tracker_id": "target-1",
            "tracking_enabled": True,
            "unpark_before_tracking": True,
        },
        tasks=[],
    )

    assert result["success"] is True
    assert len(update_calls) == 2
    assert update_calls[0]["value"]["rotator_state"] == "connected"
    assert update_calls[0]["value"]["rotator_id"] == "rot-1"
    assert update_calls[1]["value"]["rotator_state"] == "tracking"
    assert update_calls[1]["value"]["rotator_id"] == "rot-1"


@pytest.mark.asyncio
async def test_stop_tracker_parks_when_requested(monkeypatch):
    calls = []

    async def _mock_update(tracker_id, value, requester_sid=None):
        calls.append(value)
        return {"success": True}

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_assigned_tracker_for_rotator",
        lambda _rotator_id: "target-1",
    )

    handler = TrackerHandler()
    ok = await handler.stop_tracker_task(
        observation_id="obs-2",
        rotator_config={
            "id": "rot-1",
            "tracker_id": "target-1",
            "tracking_enabled": True,
            "park_after_observation": True,
        },
    )

    assert ok is True
    assert calls == [{"rotator_state": "parked", "rotator_id": "rot-1"}]


@pytest.mark.asyncio
async def test_stop_tracker_leaves_rotator_connected_by_default(monkeypatch):
    calls = []

    async def _mock_update(tracker_id, value, requester_sid=None):
        calls.append(value)
        return {"success": True}

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_assigned_tracker_for_rotator",
        lambda _rotator_id: "target-1",
    )

    handler = TrackerHandler()
    ok = await handler.stop_tracker_task(
        observation_id="obs-3",
        rotator_config={
            "id": "rot-1",
            "tracker_id": "target-1",
            "tracking_enabled": True,
            "park_after_observation": False,
        },
    )

    assert ok is True
    assert calls == []


@pytest.mark.asyncio
async def test_start_tracker_returns_rotator_in_use_error(monkeypatch):
    manager = _DummyTrackerManager({"rotator_state": "connected"})
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_tracker_manager",
        lambda _tracker_id: manager,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_assigned_tracker_for_rotator",
        lambda _rotator_id: "target-1",
    )

    async def _mock_update(tracker_id, value, requester_sid=None):
        return {
            "success": False,
            "error": "rotator_in_use",
            "message": "Rotator 'rot-1' is already assigned to tracker 'target-2'.",
            "data": {"owner_tracker_id": "target-2"},
        }

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )

    handler = TrackerHandler()
    result = await handler.start_tracker_task(
        observation_id="obs-4",
        satellite={"norad_id": 25544, "group_id": "grp-1", "name": "ISS"},
        rotator_config={
            "id": "rot-1",
            "tracker_id": "target-1",
            "tracking_enabled": True,
        },
        tasks=[],
    )

    assert result["success"] is False
    assert result["error"] == "rotator_in_use"


@pytest.mark.asyncio
async def test_start_tracker_uses_observation_slot_when_rotator_unassigned(monkeypatch):
    called = {"update": False, "manager": False}

    manager = _DummyTrackerManager({"rotator_state": "connected"})
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_tracker_manager",
        lambda _tracker_id: (called.__setitem__("manager", True), manager)[1],
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_assigned_tracker_for_rotator",
        lambda _rotator_id: None,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.create_observation_tracker_slot",
        lambda _observation_id: {"success": True, "tracker_id": "obs-5", "created": True},
    )

    async def _mock_update(tracker_id, value, requester_sid=None):
        called["update"] = True
        assert tracker_id == "obs-5"
        return {"success": True}

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )

    handler = TrackerHandler()
    result = await handler.start_tracker_task(
        observation_id="obs-5",
        satellite={"norad_id": 25544, "group_id": "grp-1", "name": "ISS"},
        rotator_config={
            "id": "2fb00a81-c0fd-4848-ab40-3101751d0534",
            "tracking_enabled": True,
        },
        tasks=[],
    )

    assert result["success"] is True
    assert result["tracker_id"] == "obs-5"
    assert result["ephemeral"] is True
    assert result["created"] is True
    assert called["manager"] is True
    assert called["update"] is True


@pytest.mark.asyncio
async def test_start_tracker_emits_tracker_instances_snapshot(monkeypatch):
    manager = _DummyTrackerManager({"rotator_state": "connected"})
    captured = {"emitted": False, "sio": None}

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_tracker_manager",
        lambda _tracker_id: manager,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_assigned_tracker_for_rotator",
        lambda _rotator_id: None,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.create_observation_tracker_slot",
        lambda _observation_id: {"success": True, "tracker_id": "obs-emit", "created": True},
    )

    async def _mock_update(tracker_id, value, requester_sid=None):
        return {"success": True}

    async def _mock_emit_tracker_instances(sio):
        captured["emitted"] = True
        captured["sio"] = sio

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.emit_tracker_instances",
        _mock_emit_tracker_instances,
    )

    fake_sio = object()
    handler = TrackerHandler(sio=fake_sio)
    result = await handler.start_tracker_task(
        observation_id="obs-emit",
        satellite={"norad_id": 25544, "group_id": "grp-1", "name": "ISS"},
        rotator_config={
            "id": "rot-2",
            "tracking_enabled": True,
        },
        tasks=[],
    )

    assert result["success"] is True
    assert captured["emitted"] is True
    assert captured["sio"] is fake_sio


@pytest.mark.asyncio
async def test_start_tracker_without_rotator_starts_ephemeral_context_tracker(monkeypatch):
    manager = _DummyTrackerManager({"rotator_state": "disconnected"})
    update_calls = []

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.create_observation_tracker_slot",
        lambda _observation_id: {"success": True, "tracker_id": "obs-no-rotator", "created": True},
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_tracker_manager",
        lambda _tracker_id: manager,
    )

    async def _mock_update(tracker_id, value, requester_sid=None):
        update_calls.append(
            {"tracker_id": tracker_id, "value": value, "requester_sid": requester_sid}
        )
        return {"success": True}

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )

    handler = TrackerHandler()
    result = await handler.start_tracker_task(
        observation_id="obs-no-rotator",
        satellite={"norad_id": 25338, "group_id": "grp-no-rotator", "name": "NOAA-15"},
        rotator_config={"tracking_enabled": False},
        tasks=[{"type": "decoder", "config": {"transmitter_id": "tx-1"}}],
    )

    assert result["success"] is True
    assert result["tracker_id"] == "obs-no-rotator"
    assert result["ephemeral"] is True
    assert result["created"] is True
    assert len(update_calls) == 1
    assert update_calls[0]["value"]["rotator_state"] == "disconnected"
    assert update_calls[0]["value"]["rotator_id"] == "none"
    assert update_calls[0]["value"]["transmitter_id"] == "tx-1"


@pytest.mark.asyncio
async def test_start_tracker_reuses_existing_rotator_slot_when_tracking_disabled(monkeypatch):
    manager = _DummyTrackerManager({"rotator_state": "connected"})
    update_calls = []

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_assigned_tracker_for_rotator",
        lambda _rotator_id: "target-9",
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_tracker_manager",
        lambda _tracker_id: manager,
    )

    async def _mock_update(tracker_id, value, requester_sid=None):
        update_calls.append({"tracker_id": tracker_id, "value": value})
        return {"success": True}

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )

    handler = TrackerHandler()
    result = await handler.start_tracker_task(
        observation_id="obs-reuse-slot",
        satellite={"norad_id": 25544, "group_id": "grp-1", "name": "ISS"},
        rotator_config={"id": "rot-reused", "tracking_enabled": False},
        tasks=[],
    )

    assert result["success"] is True
    assert result["tracker_id"] == "target-9"
    assert result["ephemeral"] is False
    assert result["created"] is False
    assert result["reused_existing"] is True
    assert len(update_calls) == 1
    assert update_calls[0]["value"]["rotator_state"] == "disconnected"
    assert update_calls[0]["value"]["rotator_id"] == "rot-reused"


@pytest.mark.asyncio
async def test_stop_tracker_removes_ephemeral_tracker_instance(monkeypatch):
    remove_calls = []

    async def _mock_remove(self, tracker_id):
        remove_calls.append(tracker_id)
        return True

    async def _unexpected_update(_tracker_id, _value, requester_sid=None):
        raise AssertionError("update_tracking_state_with_ownership should not be called")

    monkeypatch.setattr(
        TrackerHandler,
        "_remove_observation_tracker_instance",
        _mock_remove,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _unexpected_update,
    )

    handler = TrackerHandler()
    ok = await handler.stop_tracker_task(
        observation_id="obs-ephemeral-stop",
        rotator_config={},
        tracker_context={"tracker_id": "obs-11", "ephemeral": True},
    )

    assert ok is True
    assert remove_calls == ["obs-11"]


@pytest.mark.asyncio
async def test_stop_tracker_returns_true_when_tracker_id_missing_and_no_owner(monkeypatch):
    called = {"update": False}

    async def _mock_update(tracker_id, value, requester_sid=None):
        called["update"] = True
        return {"success": True}

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_assigned_tracker_for_rotator",
        lambda _rotator_id: None,
    )

    handler = TrackerHandler()
    ok = await handler.stop_tracker_task(
        observation_id="obs-6",
        rotator_config={
            "id": "2fb00a81-c0fd-4848-ab40-3101751d0534",
            "tracking_enabled": True,
            "park_after_observation": True,
        },
    )

    assert ok is True
    assert called["update"] is False


@pytest.mark.asyncio
async def test_stop_tracker_ignores_stale_tracker_id_and_uses_current_rotator_owner(monkeypatch):
    calls = []

    async def _mock_update(tracker_id, value, requester_sid=None):
        calls.append({"tracker_id": tracker_id, "value": value, "requester_sid": requester_sid})
        return {"success": True}

    monkeypatch.setattr(
        "observations.tasks.trackerhandler.update_tracking_state_with_ownership",
        _mock_update,
    )
    monkeypatch.setattr(
        "observations.tasks.trackerhandler.get_assigned_tracker_for_rotator",
        lambda _rotator_id: "target-9",
    )

    handler = TrackerHandler()
    ok = await handler.stop_tracker_task(
        observation_id="obs-7",
        rotator_config={
            "id": "2fb00a81-c0fd-4848-ab40-3101751d0534",
            "tracker_id": "target-1",
            "tracking_enabled": True,
            "park_after_observation": True,
        },
    )

    assert ok is True
    assert len(calls) == 1
    assert calls[0]["tracker_id"] == "target-9"
    assert calls[0]["value"] == {
        "rotator_state": "parked",
        "rotator_id": "2fb00a81-c0fd-4848-ab40-3101751d0534",
    }
