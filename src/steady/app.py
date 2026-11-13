from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from steady.config import APP_NAME, ORGANIZATION_NAME, get_database_path
from steady.app_info import APP_VERSION
from steady.database import Database
from steady.repositories.settings_repository import SettingsRepository
from steady.services.data_management import DataManagementService
from steady.ui.main_window import MainWindow
from steady.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    icon_path = Path(__file__).resolve().parent / "assets" / "steady_icon.png"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setOrganizationDomain("local.steady.app")
    app.setStyle("Fusion")

    available_fonts = {name.casefold(): name for name in QFontDatabase.families()}
    font_family = next(
        (
            available_fonts[name.casefold()]
            for name in ("Aptos", "Avenir Next", "Noto Sans", "Inter", "Cantarell", "DejaVu Sans")
            if name.casefold() in available_fonts
        ),
        "Sans Serif",
    )
    app_font = QFont(font_family)
    app_font.setPointSizeF(12.0)
    app_font.setWeight(QFont.Weight.Normal)
    app.setFont(app_font)

    database = Database(get_database_path())
    database.initialize()
    settings = SettingsRepository(database)

    # Create one validated local backup at most every 24 hours. A backup
    # failure must not prevent the user from opening their planner.
    backup_notice: str | None = None
    data_service = DataManagementService(database)
    try:
        created_backup = data_service.automatic_backup_if_due()
        latest_backups = data_service.list_backups()
        if created_backup:
            backup_notice = f"Automatic backup created: {created_backup}"
        elif latest_backups:
            backup_notice = f"Latest local backup: {latest_backups[0]}"
        else:
            backup_notice = "No automatic backup has been created yet."
    except Exception as exc:
        backup_notice = (
            "Automatic backup could not be completed. Your planner is still available. "
            f"Details: {exc}"
        )

    current_theme = settings.get("theme", "dark") or "dark"
    if current_theme not in {"light", "dark"}:
        current_theme = "dark"
    apply_theme(app, current_theme)

    window = MainWindow(database, current_theme=current_theme, backup_notice=backup_notice)

    def handle_theme_change(mode: str) -> None:
        if mode not in {"light", "dark"}:
            return
        apply_theme(app, mode)
        settings.set("theme", mode)

    window.theme_changed.connect(handle_theme_change)
    window.show()
    return app.exec()
