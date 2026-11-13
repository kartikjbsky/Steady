from __future__ import annotations

import csv
import json
import os
import sqlite3
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from steady.database import Database
from steady.database.db import SCHEMA_VERSION


class DataManagementError(RuntimeError):
    """Raised when a backup, restore, export or integrity operation is unsafe."""


class DataManagementService:
    """Local-only backup, restore, CSV export and SQLite integrity utilities."""

    REQUIRED_TABLES = {
        "miss_reasons",
        "tasks",
        "habits",
        "habit_entries",
        "daily_reflections",
        "reminders",
        "focus_sessions",
        "app_settings",
    }

    def __init__(self, database: Database, backup_dir: str | Path | None = None) -> None:
        self.database = database
        self.backup_dir = Path(backup_dir) if backup_dir else database.path.parent / "backups"
        self.backup_dir = self.backup_dir.expanduser()

    @staticmethod
    def _utc_stamp(value: datetime | None = None) -> str:
        return (value or datetime.now().astimezone()).strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def _readonly_connection(path: Path) -> sqlite3.Connection:
        uri = f"{path.resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    @classmethod
    def validate_database_file(cls, path: str | Path) -> dict[str, Any]:
        """Validate SQLite structure, foreign keys, schema version and required tables."""
        source = Path(path).expanduser()
        if not source.is_file() or source.stat().st_size == 0:
            raise DataManagementError("The selected file does not exist or is empty.")

        try:
            connection = cls._readonly_connection(source)
        except sqlite3.Error as exc:
            raise DataManagementError(f"Cannot open the selected SQLite file: {exc}") from exc

        try:
            integrity_rows = [
                str(row[0]) for row in connection.execute("PRAGMA integrity_check").fetchall()
            ]
            foreign_rows = [
                tuple(row)
                for row in connection.execute("PRAGMA foreign_key_check").fetchall()
            ]
            schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            tables = {
                str(row["name"])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
            }
            missing = sorted(cls.REQUIRED_TABLES - tables)
            if integrity_rows != ["ok"]:
                raise DataManagementError(
                    "The selected database failed SQLite integrity_check: "
                    + "; ".join(integrity_rows[:5])
                )
            if foreign_rows:
                raise DataManagementError(
                    f"The selected database has {len(foreign_rows)} foreign-key violation(s)."
                )
            if schema_version != SCHEMA_VERSION:
                raise DataManagementError(
                    f"This backup uses database schema {schema_version}; "
                    f"this Steady version requires schema {SCHEMA_VERSION}. "
                    "Use a backup made by a compatible Steady release."
                )
            if missing:
                raise DataManagementError(
                    "The selected database is missing required tables: " + ", ".join(missing)
                )
            return {
                "path": str(source.resolve()),
                "schema_version": schema_version,
                "tables": sorted(tables),
                "integrity": "ok",
                "foreign_key_violations": 0,
            }
        except sqlite3.Error as exc:
            raise DataManagementError(f"Could not validate the selected database: {exc}") from exc
        finally:
            connection.close()

    def integrity_report(self) -> dict[str, Any]:
        """Return integrity, foreign-key and per-table row-count information."""
        info = self.validate_database_file(self.database.path)
        connection = self._readonly_connection(self.database.path)
        try:
            counts: dict[str, int] = {}
            for table in sorted(info["tables"]):
                quoted = '"' + table.replace('"', '""') + '"'
                counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])
            return {
                **info,
                "row_counts": counts,
                "total_rows": sum(counts.values()),
            }
        finally:
            connection.close()

    def backup_to(self, destination: str | Path) -> Path:
        """Create a consistent online SQLite backup using the SQLite backup API."""
        destination = Path(destination).expanduser()
        if destination.resolve() == self.database.path.resolve():
            raise DataManagementError("Choose a different location from the live database.")
        destination.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            source = sqlite3.connect(str(self.database.path), timeout=10.0)
            target = sqlite3.connect(str(temp_path), timeout=10.0)
            try:
                source.backup(target)
                target.commit()
            finally:
                target.close()
                source.close()

            self.validate_database_file(temp_path)
            os.replace(temp_path, destination)
            return destination
        except (sqlite3.Error, OSError, DataManagementError) as exc:
            temp_path.unlink(missing_ok=True)
            if isinstance(exc, DataManagementError):
                raise
            raise DataManagementError(f"Could not create the backup: {exc}") from exc

    def automatic_backup_if_due(
        self, *, now: datetime | None = None, interval: timedelta = timedelta(hours=24),
        keep: int = 14,
    ) -> Path | None:
        """Create at most one automatic backup per interval and prune old auto backups."""
        now = now or datetime.now().astimezone()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backups = sorted(
            self.backup_dir.glob("steady_auto_*.sqlite3"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if backups:
            latest = datetime.fromtimestamp(backups[0].stat().st_mtime).astimezone()
            if now - latest < interval:
                return None

        name = f"steady_auto_{self._utc_stamp(now)}.sqlite3"
        target = self.backup_dir / name
        created = self.backup_to(target)

        backups = sorted(
            self.backup_dir.glob("steady_auto_*.sqlite3"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for old in backups[max(1, int(keep)):]:
            old.unlink(missing_ok=True)
        return created

    def list_backups(self) -> list[Path]:
        if not self.backup_dir.exists():
            return []
        return sorted(
            self.backup_dir.glob("*.sqlite3"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )

    def restore_from(self, backup_path: str | Path) -> Path:
        """Validate a backup, protect the current DB, then atomically restore it."""
        source = Path(backup_path).expanduser()
        if source.resolve() == self.database.path.resolve():
            raise DataManagementError("The selected file is already the live database.")

        self.validate_database_file(source)

        # Do not restore over an active timer, which would leave its in-memory
        # UI state disconnected from the database being replaced.
        with self.database.connect() as connection:
            running = int(
                connection.execute(
                    "SELECT COUNT(*) FROM focus_sessions WHERE outcome = 'running'"
                ).fetchone()[0]
            )
            if running:
                raise DataManagementError(
                    "A focus timer is currently running. Stop or finish it before restoring a backup."
                )
            checkpoint = connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            if checkpoint and int(checkpoint[0]) != 0:
                raise DataManagementError(
                    "SQLite is busy and could not checkpoint the database. Close other Steady windows and try again."
                )

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        safety_path = self.backup_dir / f"steady_before_restore_{self._utc_stamp()}.sqlite3"
        self.backup_to(safety_path)

        fd, temp_name = tempfile.mkstemp(
            prefix=".steady_restore_", suffix=".sqlite3", dir=self.database.path.parent
        )
        os.close(fd)
        staged = Path(temp_name)
        try:
            src = sqlite3.connect(str(source), timeout=10.0)
            dst = sqlite3.connect(str(staged), timeout=10.0)
            try:
                src.backup(dst)
                dst.commit()
            finally:
                dst.close()
                src.close()

            self.validate_database_file(staged)

            # Connections created by Database are short-lived. Ensure WAL
            # sidecars from the previous live DB cannot be replayed onto the
            # atomically replaced file.
            for suffix in ("-wal", "-shm"):
                Path(str(self.database.path) + suffix).unlink(missing_ok=True)
            os.replace(staged, self.database.path)

            # Any session that was active when the backup was taken is now a
            # historical interrupted session, not a live timer in this process.
            with self.database.connect() as connection:
                connection.execute(
                    """UPDATE focus_sessions
                       SET outcome = 'interrupted',
                           ended_at = COALESCE(ended_at, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                           actual_seconds = COALESCE(actual_seconds, 0)
                       WHERE outcome = 'running'"""
                )
            self.database.initialize()
            return safety_path
        except (sqlite3.Error, OSError, DataManagementError) as exc:
            staged.unlink(missing_ok=True)
            if isinstance(exc, DataManagementError):
                raise
            raise DataManagementError(f"Could not restore the selected backup: {exc}") from exc

    def export_csv(self, destination_directory: str | Path) -> Path:
        """Export a consistent SQLite snapshot as CSV files plus a JSON manifest."""
        destination_directory = Path(destination_directory).expanduser()
        destination_directory.mkdir(parents=True, exist_ok=True)
        export_dir = destination_directory / f"Steady_Export_{self._utc_stamp()}"
        suffix = 1
        while export_dir.exists():
            export_dir = destination_directory / f"Steady_Export_{self._utc_stamp()}_{suffix}"
            suffix += 1
        export_dir.mkdir(parents=False)

        snapshot_fd, snapshot_name = tempfile.mkstemp(
            prefix=".steady_csv_snapshot_", suffix=".sqlite3", dir=destination_directory
        )
        os.close(snapshot_fd)
        snapshot_path = Path(snapshot_name)

        try:
            source = sqlite3.connect(str(self.database.path), timeout=10.0)
            snapshot = sqlite3.connect(str(snapshot_path), timeout=10.0)
            try:
                source.backup(snapshot)
                snapshot.commit()
            finally:
                snapshot.close()
                source.close()

            connection = self._readonly_connection(snapshot_path)
            try:
                schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
                tables = [
                    str(row["name"])
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                    ).fetchall()
                ]
                manifest: dict[str, Any] = {
                    "application": "Steady",
                    "schema_version": schema_version,
                    "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "tables": {},
                }
                for table in tables:
                    quoted = '"' + table.replace('"', '""') + '"'
                    cursor = connection.execute(f"SELECT * FROM {quoted}")
                    fieldnames = [column[0] for column in cursor.description or []]
                    filename = f"{table}.csv"
                    row_count = 0
                    with (export_dir / filename).open(
                        "w", newline="", encoding="utf-8-sig"
                    ) as handle:
                        writer = csv.writer(handle)
                        writer.writerow(fieldnames)
                        for row in cursor:
                            values = []
                            for value in row:
                                values.append("hex:" + value.hex() if isinstance(value, bytes) else value)
                            writer.writerow(values)
                            row_count += 1
                    manifest["tables"][table] = {"file": filename, "rows": row_count}
            finally:
                connection.close()

            (export_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return export_dir
        except (sqlite3.Error, OSError) as exc:
            shutil.rmtree(export_dir, ignore_errors=True)
            raise DataManagementError(f"Could not export CSV files: {exc}") from exc
        finally:
            snapshot_path.unlink(missing_ok=True)
