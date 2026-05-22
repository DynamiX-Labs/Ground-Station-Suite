# Copyright (c) 2026 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

import pytest

from tracker.stateupdate import update_tracking_state_with_ownership


class _DummyManager:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    async def update_tracking_state(self, requester_sid=None, **kwargs):
        self.calls.append({"requester_sid": requester_sid, "kwargs": kwargs})
        return dict(self.reply)


@pytest.mark.asyncio
async def test_update_tracking_state_with_ownership_rejects_in_use_rotator(monkeypatch):
    monkeypatch.setattr(
        "tracker.stateupdate.assign_rotator_to_tracker",
        lambda tracker_id, rotator_id: {
            "success": False,
            "owner_tracker_id": "target-2",
        },
    )

    def _unexpected_manager(_tracker_id):
        raise AssertionError("get_tracker_manager should not be called on ownership conflict")

    monkeypatch.setattr("tracker.stateupdate.get_tracker_manager", _unexpected_manager)

    result = await update_tracking_state_with_ownership(
        tracker_id="target-1",
        value={"rotator_id": "rot-1", "rotator_state": "tracking"},
        requester_sid="sid-1",
    )

    assert result["success"] is False
    assert result["error"] == "rotator_in_use"
    assert result["data"]["owner_tracker_id"] == "target-2"


@pytest.mark.asyncio
async def test_update_tracking_state_with_ownership_rolls_back_on_failure(monkeypatch):
    manager = _DummyManager({"success": False, "error": "db_write_failed"})
    restore_calls = []

    monkeypatch.setattr(
        "tracker.stateupdate.get_assigned_rotator_for_tracker",
        lambda _tracker_id: "rot-prev",
    )
    monkeypatch.setattr(
        "tracker.stateupdate.assign_rotator_to_tracker",
        lambda tracker_id, rotator_id: {"success": True},
    )
    monkeypatch.setattr("tracker.stateupdate.get_tracker_manager", lambda _tracker_id: manager)
    monkeypatch.setattr(
        "tracker.stateupdate.restore_tracker_rotator_assignment",
        lambda tracker_id, rotator_id: restore_calls.append((tracker_id, rotator_id)),
    )

    result = await update_tracking_state_with_ownership(
        tracker_id="target-1",
        value={"rotator_id": "rot-1", "rotator_state": "tracking"},
        requester_sid="sid-2",
    )

    assert result["success"] is False
    assert result["error"] == "db_write_failed"
    assert restore_calls == [("target-1", "rot-prev")]


@pytest.mark.asyncio
async def test_update_tracking_state_with_ownership_success(monkeypatch):
    manager = _DummyManager({"success": True, "command_id": "cmd-1"})
    monkeypatch.setattr(
        "tracker.stateupdate.assign_rotator_to_tracker",
        lambda tracker_id, rotator_id: {"success": True},
    )
    monkeypatch.setattr("tracker.stateupdate.get_tracker_manager", lambda _tracker_id: manager)

    result = await update_tracking_state_with_ownership(
        tracker_id="target-1",
        value={"rotator_id": "rot-1", "rotator_state": "tracking"},
        requester_sid="sid-3",
    )

    assert result["success"] is True
    assert result["result"]["command_id"] == "cmd-1"
    assert manager.calls[0]["kwargs"]["rotator_state"] == "tracking"
