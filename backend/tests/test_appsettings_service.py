# Copyright (c) 2026 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

import json

from common import appsettings


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")


def _read_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _build_service(tmp_path):
    service = appsettings.AppSettingsService()
    service.config_path = tmp_path / "app_config.json"
    return service


def test_get_payload_marks_cli_override_and_file_source(tmp_path, monkeypatch):
    service = _build_service(tmp_path)
    _write_json(
        service.config_path,
        {
            "host": "127.0.0.1",
            "port": 5050,
        },
    )

    monkeypatch.setattr(appsettings.arguments, "host", "127.0.0.1", raising=False)
    monkeypatch.setattr(appsettings.arguments, "port", 5050, raising=False)
    monkeypatch.setattr(appsettings, "app_config_cli_overrides", {"host"})

    payload = service.get_payload()

    assert payload["locked"]["host"] is True
    assert payload["source"]["host"] == "cli"
    assert payload["source"]["port"] == "file"
    assert payload["defined_in_file"]["host"] is True
    assert payload["defined_in_file"]["port"] is True


def test_update_rejects_unknown_settings(tmp_path):
    service = _build_service(tmp_path)

    result = service.update({"not_a_setting": 1})

    assert result["success"] is False
    assert "Unknown settings" in result["error"]


def test_update_returns_validation_errors(tmp_path):
    service = _build_service(tmp_path)

    result = service.update({"port": 99999})

    assert result["success"] is False
    assert result["error"] == "One or more settings are invalid"
    assert "port" in result["data"]["validation_errors"]


def test_update_hot_apply_updates_runtime_and_removes_legacy_alias(tmp_path, monkeypatch):
    service = _build_service(tmp_path)
    _write_json(
        service.config_path,
        {
            "tle_sync_transmitter_urls": ["https://legacy.example.com/transmitters.json"],
        },
    )
    monkeypatch.setattr(
        appsettings.arguments,
        "orbital_sync_transmitter_urls",
        ["https://legacy.example.com/transmitters.json"],
        raising=False,
    )
    monkeypatch.setattr(
        appsettings.arguments,
        "tle_sync_transmitter_urls",
        ["https://legacy.example.com/transmitters.json"],
        raising=False,
    )

    result = service.update(
        {"orbital_sync_transmitter_urls": ["https://new.example.com/transmitters.json"]}
    )

    assert result["success"] is True
    data = result["data"]
    assert data["changed_hot_keys"] == ["orbital_sync_transmitter_urls"]
    assert data["changed_restart_keys"] == []
    assert data["restart_required"] is False
    assert appsettings.arguments.orbital_sync_transmitter_urls == [
        "https://new.example.com/transmitters.json"
    ]
    assert appsettings.arguments.tle_sync_transmitter_urls == [
        "https://new.example.com/transmitters.json"
    ]

    written = _read_json(service.config_path)
    assert written["orbital_sync_transmitter_urls"] == ["https://new.example.com/transmitters.json"]
    assert "tle_sync_transmitter_urls" not in written


def test_update_restart_required_setting_persists_but_does_not_hot_apply(tmp_path, monkeypatch):
    service = _build_service(tmp_path)
    _write_json(
        service.config_path,
        {
            "host": "0.0.0.0",
        },
    )
    monkeypatch.setattr(appsettings.arguments, "host", "0.0.0.0", raising=False)

    result = service.update({"host": "127.0.0.1"})

    assert result["success"] is True
    data = result["data"]
    assert data["changed_keys"] == ["host"]
    assert data["changed_hot_keys"] == []
    assert data["changed_restart_keys"] == ["host"]
    assert data["restart_required"] is True
    # restart_required settings should not mutate runtime arguments until restart.
    assert appsettings.arguments.host == "0.0.0.0"

    written = _read_json(service.config_path)
    assert written["host"] == "127.0.0.1"
