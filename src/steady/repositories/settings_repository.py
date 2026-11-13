from __future__ import annotations

from steady.database import Database


class SettingsRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def get(self, key: str, default: str | None = None) -> str | None:
        rows = self.database.fetch_all(
            "SELECT setting_value FROM app_settings WHERE setting_key = ?", (key,)
        )
        return str(rows[0]["setting_value"]) if rows else default

    def set(self, key: str, value: str) -> None:
        self.database.execute(
            """INSERT INTO app_settings(setting_key, setting_value) VALUES (?, ?)
               ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value""",
            (key, value),
        )
