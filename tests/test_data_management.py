from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from steady.database import Database
from steady.repositories.planner_repository import PlannerRepository
from steady.services.data_management import DataManagementError, DataManagementService


def make_service(tmp_path: Path):
    database = Database(tmp_path / "steady.sqlite3")
    database.initialize()
    return database, DataManagementService(database)


def test_backup_creates_valid_snapshot_and_integrity_report(tmp_path: Path):
    database, service = make_service(tmp_path)
    planner = PlannerRepository(database)
    planner.add_task(title="Keep this task", day=__import__("datetime").date.today())

    saved = service.backup_to(tmp_path / "manual-backup.sqlite3")
    validation = service.validate_database_file(saved)
    report = service.integrity_report()

    assert saved.exists()
    assert validation["integrity"] == "ok"
    assert validation["schema_version"] == 3
    assert report["row_counts"]["tasks"] == 1
    assert report["foreign_key_violations"] == 0


def test_restore_replaces_data_and_keeps_a_safety_copy(tmp_path: Path):
    database, service = make_service(tmp_path)
    planner = PlannerRepository(database)
    today = __import__("datetime").date.today()
    planner.add_task(title="Task in backup", day=today)
    backup = service.backup_to(tmp_path / "known-good.sqlite3")

    planner.add_task(title="Task added afterwards", day=today)
    safety = service.restore_from(backup)

    task_titles = [item["title"] for item in planner.list_tasks(today)]
    assert task_titles == ["Task in backup"]
    assert safety.exists()
    assert service.validate_database_file(safety)["integrity"] == "ok"
    assert service.integrity_report()["schema_version"] == 3


def test_restore_rejects_invalid_file_without_changing_live_database(tmp_path: Path):
    database, service = make_service(tmp_path)
    before = service.integrity_report()["total_rows"]
    invalid = tmp_path / "not-a-database.sqlite3"
    invalid.write_text("not sqlite", encoding="utf-8")

    with pytest.raises(DataManagementError):
        service.restore_from(invalid)

    assert service.integrity_report()["total_rows"] == before


def test_restore_refuses_while_a_focus_session_is_running(tmp_path: Path):
    database, service = make_service(tmp_path)
    backup = service.backup_to(tmp_path / "backup.sqlite3")
    database.execute(
        """INSERT INTO focus_sessions
           (started_at, planned_seconds, outcome, session_type)
           VALUES ('2026-11-13T04:00:00Z', 600, 'running', 'focus')"""
    )

    with pytest.raises(DataManagementError, match="focus timer is currently running"):
        service.restore_from(backup)


def test_csv_export_contains_each_table_and_manifest(tmp_path: Path):
    database, service = make_service(tmp_path)
    PlannerRepository(database).add_task(
        title="CSV export check", day=__import__("datetime").date.today()
    )

    export_dir = service.export_csv(tmp_path / "exports")
    manifest = json.loads((export_dir / "manifest.json").read_text(encoding="utf-8"))
    assert (export_dir / "tasks.csv").exists()
    assert (export_dir / "habits.csv").exists()
    assert manifest["schema_version"] == 3
    assert manifest["tables"]["tasks"]["rows"] == 1

    with (export_dir / "tasks.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["title"] == "CSV export check"


def test_automatic_backup_runs_at_most_once_per_24_hours(tmp_path: Path):
    _, service = make_service(tmp_path)
    now = datetime.now().astimezone()
    first = service.automatic_backup_if_due(now=now)
    second = service.automatic_backup_if_due(now=now + timedelta(hours=1))
    third = service.automatic_backup_if_due(now=now + timedelta(hours=25))

    assert first is not None and first.exists()
    assert second is None
    assert third is not None and third.exists()
    assert len(list(service.backup_dir.glob("steady_auto_*.sqlite3"))) == 2
