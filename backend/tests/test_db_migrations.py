# Copyright (c) 2026 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

import os
from pathlib import Path

from db import migrations


def test_backup_rotation_keeps_latest_five(tmp_path):
    db_path = tmp_path / "gs.db"
    db_path.write_bytes(b"db")

    for index in range(6):
        old_backup = tmp_path / f"gs.db.pre-migration-20260101-00000{index}.bak"
        old_backup.write_bytes(f"old-{index}".encode("ascii"))
        os.utime(old_backup, (1 + index, 1 + index))

    created_backup = migrations._backup_db_before_migration(db_path)

    assert created_backup is not None
    backups = sorted(tmp_path.glob("gs.db.pre-migration-*.bak"))
    assert len(backups) == 5
    assert created_backup in backups


def test_run_migrations_creates_backup_only_when_pending(monkeypatch, tmp_path):
    db_path = tmp_path / "gs.db"
    db_path.write_bytes(b"db")

    calls = {"backup": 0, "upgrade": 0}

    monkeypatch.setattr(migrations, "get_alembic_config", lambda: object())
    monkeypatch.setattr(migrations, "_resolve_db_path", lambda: db_path)

    def _mock_backup(_db_path: Path):
        calls["backup"] += 1
        return _db_path.with_suffix(".bak")

    monkeypatch.setattr(migrations, "_backup_db_before_migration", _mock_backup)

    def _mock_upgrade(_cfg, _head):
        calls["upgrade"] += 1

    monkeypatch.setattr(migrations.command, "upgrade", _mock_upgrade)

    monkeypatch.setattr(migrations, "_has_pending_migrations", lambda _cfg, _db_path: False)
    migrations.run_migrations()
    assert calls["backup"] == 0
    assert calls["upgrade"] == 1

    monkeypatch.setattr(migrations, "_has_pending_migrations", lambda _cfg, _db_path: True)
    migrations.run_migrations()
    assert calls["backup"] == 1
    assert calls["upgrade"] == 2
