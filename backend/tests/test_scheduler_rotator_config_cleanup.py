# Copyright (c) 2026 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

from crud import monitoredsatellites, scheduledobservations


def test_scheduled_transform_to_db_strips_rotator_tracker_id():
    data = {
        "id": "obs-1",
        "name": "OBS",
        "enabled": True,
        "status": "scheduled",
        "satellite": {"norad_id": 25544, "name": "ISS", "group_id": "grp"},
        "pass": {},
        "rotator": {"id": None, "tracker_id": "target-3", "tracking_enabled": True},
        "rig": {},
        "transmitter": {},
        "sessions": [{"sdr": {"id": None}, "tasks": []}],
    }

    transformed = scheduledobservations._transform_to_db_format(data)
    assert "tracker_id" not in transformed["hardware_config"]["rotator"]


def test_scheduled_transform_from_db_strips_rotator_tracker_id():
    db_obj = {
        "id": "obs-1",
        "name": "OBS",
        "enabled": True,
        "status": "scheduled",
        "norad_id": 25544,
        "hardware_config": {
            "rotator": {"id": "rot-1", "tracker_id": "target-3", "tracking_enabled": True},
            "rig": {},
            "transmitter": {},
        },
        "satellite_config": {"name": "ISS", "group_id": "grp"},
        "pass_config": {},
        "sessions": [],
        "task_start": None,
        "task_end": None,
        "event_start": None,
        "event_end": None,
        "created_at": None,
        "updated_at": None,
    }

    transformed = scheduledobservations._transform_from_db_format(db_obj)
    assert "tracker_id" not in transformed["rotator"]


def test_monitored_transform_to_db_strips_rotator_tracker_id():
    data = {
        "id": "mon-1",
        "enabled": True,
        "satellite": {"norad_id": 25544, "name": "ISS", "group_id": "grp"},
        "rotator": {"id": None, "tracker_id": "target-4", "tracking_enabled": True},
        "rig": {},
        "sessions": [{"sdr": {"id": None}, "tasks": []}],
    }

    transformed = monitoredsatellites._transform_to_db_format(data)
    assert "tracker_id" not in transformed["hardware_config"]["rotator"]


def test_monitored_transform_from_db_strips_rotator_tracker_id():
    db_obj = {
        "id": "mon-1",
        "enabled": True,
        "norad_id": 25544,
        "hardware_config": {
            "rotator": {"id": "rot-1", "tracker_id": "target-4", "tracking_enabled": True},
            "rig": {},
        },
        "satellite_config": {"name": "ISS", "group_id": "grp"},
        "generation_config": {},
        "sessions": [],
        "created_at": None,
        "updated_at": None,
    }

    transformed = monitoredsatellites._transform_from_db_format(db_obj)
    assert "tracker_id" not in transformed["rotator"]
