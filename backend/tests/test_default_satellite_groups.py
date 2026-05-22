# Copyright (c) 2026 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

from server.default_satellite_groups import DEFAULT_SYSTEM_SATELLITE_GROUPS


def test_default_system_satellite_groups_are_non_empty_and_unique():
    identifiers = set()
    for group in DEFAULT_SYSTEM_SATELLITE_GROUPS:
        identifiers.add(group["identifier"])
        satellite_ids = group["satellite_ids"]
        assert satellite_ids
        assert len(satellite_ids) == len(set(satellite_ids))

    assert identifiers == {
        "curated-amateur",
        "curated-cubesats",
        "curated-stations",
        "curated-tinygs",
        "curated-weather",
    }
