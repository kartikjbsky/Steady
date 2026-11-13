from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QStandardPaths

APP_NAME = "Steady"
ORGANIZATION_NAME = "Steady Planner"
DATABASE_FILENAME = "steady.sqlite3"


def get_app_data_dir() -> Path:
    """Return a writable, per-user app-data directory."""
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if not location:
        # Fallback should rarely be needed, but remains writable and user-local.
        location = str(Path.home() / ".steady")
    path = Path(location)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_path() -> Path:
    return get_app_data_dir() / DATABASE_FILENAME
