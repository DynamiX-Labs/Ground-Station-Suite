# Copyright (c) 2026 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

from tracker.runner import TrackerSupervisor


def _set_target_limit(monkeypatch, limit: int) -> None:
    monkeypatch.setattr("tracker.runner.arguments.max_tracker_targets", limit, raising=False)


def test_target_slot_allocator_reuses_lowest_free_slot(monkeypatch):
    _set_target_limit(monkeypatch, 10)
    supervisor = TrackerSupervisor()

    assert supervisor.ensure_tracker_for_rotator("rot-1")["tracker_id"] == "target-1"
    assert supervisor.ensure_tracker_for_rotator("rot-2")["tracker_id"] == "target-2"
    assert supervisor.ensure_tracker_for_rotator("rot-3")["tracker_id"] == "target-3"

    remove_reply = supervisor.remove_tracker("target-2")
    assert remove_reply["success"] is True

    reuse_reply = supervisor.ensure_tracker_for_rotator("rot-4")
    assert reuse_reply["success"] is True
    assert reuse_reply["tracker_id"] == "target-2"


def test_target_slot_allocator_enforces_configured_limit(monkeypatch):
    _set_target_limit(monkeypatch, 2)
    supervisor = TrackerSupervisor()

    assert supervisor.ensure_tracker_for_rotator("rot-1")["tracker_id"] == "target-1"
    assert supervisor.ensure_tracker_for_rotator("rot-2")["tracker_id"] == "target-2"

    limit_reply = supervisor.ensure_tracker_for_rotator("rot-3")
    assert limit_reply["success"] is False
    assert limit_reply["error"] == "tracker_slot_limit_reached"
    assert limit_reply["data"]["limit"] == 2
    assert limit_reply["data"]["active_targets"] == 2


def test_observation_slots_do_not_consume_target_slot_limit(monkeypatch):
    _set_target_limit(monkeypatch, 1)
    supervisor = TrackerSupervisor()

    observation_reply = supervisor.create_observation_tracker_slot("obs-pass-1")
    assert observation_reply["success"] is True
    observation_tracker_id = observation_reply["tracker_id"]
    assert observation_tracker_id.startswith("obs-")

    assign_reply = supervisor.assign_rotator(observation_tracker_id, "rot-obs")
    assert assign_reply["success"] is True

    target_reply = supervisor.ensure_tracker_for_rotator("rot-target")
    assert target_reply["success"] is True
    assert target_reply["tracker_id"] == "target-1"


def test_instances_payload_uses_target_number_only_for_target_slots(monkeypatch):
    _set_target_limit(monkeypatch, 5)
    supervisor = TrackerSupervisor()

    target_reply = supervisor.ensure_tracker_for_rotator("rot-1")
    observation_reply = supervisor.create_observation_tracker_slot("obs-pass-2")
    supervisor.assign_rotator(observation_reply["tracker_id"], "rot-obs-2")

    instances = supervisor.get_instances_payload()["instances"]
    target_instance = next(
        row for row in instances if row["tracker_id"] == target_reply["tracker_id"]
    )
    observation_instance = next(
        row for row in instances if row["tracker_id"] == observation_reply["tracker_id"]
    )

    assert target_instance["target_number"] == 1
    assert observation_instance["target_number"] is None
