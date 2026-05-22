# Copyright (c) 2026 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

import json

import pytest
import requests

from tlesync.source_adapters import (
    build_space_track_norad_source_batches,
    fetch_source_orbit_records,
)


class _DummyResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def _sample_omm_row() -> dict:
    return {
        "OBJECT_NAME": "ISS (ZARYA)",
        "OBJECT_ID": "1998-067A",
        "EPOCH": "2025-01-01T12:00:00.000000",
        "MEAN_MOTION": "15.50000000",
        "ECCENTRICITY": "0.0006703",
        "INCLINATION": "51.6416",
        "RA_OF_ASC_NODE": "247.4627",
        "ARG_OF_PERICENTER": "130.5360",
        "MEAN_ANOMALY": "325.0288",
        "EPHEMERIS_TYPE": "0",
        "CLASSIFICATION_TYPE": "U",
        "NORAD_CAT_ID": "25544",
        "ELEMENT_SET_NO": "999",
        "REV_AT_EPOCH": "12345",
        "BSTAR": "0.00021914",
        "MEAN_MOTION_DOT": "0.00012345",
        "MEAN_MOTION_DDOT": "0.0",
    }


def test_fetch_http_3le_adapter(monkeypatch):
    tle_text = """ISS (ZARYA)
1 25544U 98067A   25001.50000000  .00012345  00000-0  21914-3 0  9999
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.50000000999999"""

    monkeypatch.setattr(requests, "get", lambda *_args, **_kwargs: _DummyResponse(tle_text))
    records = fetch_source_orbit_records(
        {
            "id": "f8d50d5f-e96f-4ccc-8faa-65af0403ef39",
            "adapter": "http_3le",
            "format": "3le",
            "url": "https://example.com/tle.txt",
            "central_body": "earth",
        }
    )

    assert len(records) == 1
    assert records[0]["model_kind"] == "tle"
    assert records[0]["norad_id"] == 25544
    assert records[0]["line1"].startswith("1 25544U")
    assert records[0]["line2"].startswith("2 25544")


def test_fetch_http_omm_adapter(monkeypatch):
    payload = json.dumps([_sample_omm_row()])
    monkeypatch.setattr(requests, "get", lambda *_args, **_kwargs: _DummyResponse(payload))
    records = fetch_source_orbit_records(
        {
            "id": "f8d50d5f-e96f-4ccc-8faa-65af0403ef39",
            "adapter": "http_omm",
            "format": "omm",
            "url": "https://example.com/omm.json",
            "central_body": "earth",
        }
    )

    assert len(records) == 1
    assert records[0]["model_kind"] == "omm"
    assert records[0]["norad_id"] == 25544
    assert records[0]["line1"].startswith("1 25544U")
    assert records[0]["line2"].startswith("2 25544")
    assert isinstance(records[0]["orbit_payload"], dict)
    assert records[0]["orbit_payload"]["NORAD_CAT_ID"] == "25544"


def test_fetch_space_track_adapter_requires_credentials():
    with pytest.raises(ValueError, match="requires username and password"):
        fetch_source_orbit_records(
            {
                "adapter": "space_track_gp",
                "format": "omm",
                "url": "https://www.space-track.org/basicspacedata/query/class/gp/NORAD_CAT_ID/25544/format/json",
                "auth_type": "basic",
                "username": "demo-user",
            }
        )


def test_fetch_space_track_adapter_rejects_unfiltered_gp_url():
    with pytest.raises(ValueError, match="Refusing to fetch unfiltered Space-Track GP"):
        fetch_source_orbit_records(
            {
                "adapter": "space_track_gp",
                "format": "omm",
                "url": "https://www.space-track.org/basicspacedata/query/class/gp",
                "auth_type": "basic",
                "username": "demo-user",
                "password": "demo-pass",
            }
        )


def test_fetch_space_track_adapter_rejects_unfiltered_gp_url_with_format():
    with pytest.raises(ValueError, match="Refusing to fetch unfiltered Space-Track GP"):
        fetch_source_orbit_records(
            {
                "adapter": "space_track_gp",
                "format": "omm",
                "url": "https://www.space-track.org/basicspacedata/query/class/gp/orderby/NORAD_CAT_ID/format/json",
                "auth_type": "basic",
                "username": "demo-user",
                "password": "demo-pass",
            }
        )


def test_fetch_space_track_adapter_with_basic_auth_3le(monkeypatch):
    tle_text = """ISS (ZARYA)
1 25544U 98067A   25001.50000000  .00012345  00000-0  21914-3 0  9999
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.50000000999999"""

    class _DummySession:
        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            return None

        def post(self, url, data=None, timeout=None):
            assert "ajaxauth/login" in url
            assert data == {"identity": "demo-user", "password": "demo-pass"}
            assert timeout is not None
            return _DummyResponse("ok")

        def get(self, url, timeout=None):
            assert "space-track.org" in url
            assert timeout is not None
            return _DummyResponse(tle_text)

    monkeypatch.setattr(requests, "Session", _DummySession)
    records = fetch_source_orbit_records(
        {
            "id": "f8d50d5f-e96f-4ccc-8faa-65af0403ef39",
            "adapter": "space_track_gp",
            "format": "3le",
            "url": "https://www.space-track.org/basicspacedata/query/class/gp/NORAD_CAT_ID/25544/format/tle",
            "auth_type": "basic",
            "username": "demo-user",
            "password": "demo-pass",
            "central_body": "earth",
        }
    )

    assert len(records) == 1
    assert records[0]["model_kind"] == "tle"
    assert records[0]["norad_id"] == 25544


def test_build_space_track_norad_batches():
    batches = build_space_track_norad_source_batches(
        {
            "adapter": "space_track_gp",
            "provider": "space_track",
            "format": "omm",
            "url": "https://www.space-track.org/basicspacedata/query/class/gp",
        },
        [25544, "43017", 25544, 0, "bad", 57172],
    )

    assert len(batches) == 1
    assert batches[0]["source_object_ids"] == [25544, 43017, 57172]
    assert "/NORAD_CAT_ID/25544,43017,57172/" in batches[0]["url"]
    assert batches[0]["url"].endswith("/orderby/NORAD_CAT_ID/format/json")


def test_build_space_track_norad_template_url():
    batches = build_space_track_norad_source_batches(
        {
            "adapter": "space_track_gp",
            "provider": "space_track",
            "format": "3le",
            "url": "https://example.test/query/NORAD_CAT_ID/{norad_ids}/format/{format}",
        },
        [25544],
    )

    assert batches[0]["url"] == "https://example.test/query/NORAD_CAT_ID/25544/format/tle"


def test_build_space_track_norad_batches_from_source_field():
    batches = build_space_track_norad_source_batches(
        {
            "adapter": "space_track_gp",
            "provider": "space_track",
            "format": "omm",
            "url": "https://www.space-track.org/basicspacedata/query/class/gp",
            "norad_ids": "25544, 43017 25544\n57172",
        }
    )

    assert len(batches) == 1
    assert batches[0]["source_object_ids"] == [25544, 43017, 57172]
