from __future__ import annotations

from pathlib import Path
from html import escape
from urllib.parse import quote

from PySide6.QtCore import Qt, Signal, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from steady.database import Database
from steady.app_info import APP_VERSION, AUTHOR_NAME, CONTACT_EMAIL, APP_DESCRIPTION
from steady.services.data_management import DataManagementError, DataManagementService
from .base_page import BasePage


FEEDBACK_FORM_URL = (
    "https://docs.google.com/forms/d/e/1FAIpQLSe_Cbsx-IOLbVw8Yd8RrK_ZdqPmG7C_C7G6KZoBWvQbm7lhWA/viewform?usp=publish-editor"
)


class SettingsPage(BasePage):
    theme_changed = Signal(str)
    data_restored = Signal()

    def __init__(
        self,
        database: Database,
        current_theme: str = "dark",
        backup_notice: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "Settings",
            "Keep the interface comfortable, protect your data and make Steady predictable.",
            parent,
        )
        self.database = database
        self.data_service = DataManagementService(database)

        appearance = self.add_card(
            "Appearance",
            "Choose a theme with comfortable contrast. This setting is stored locally on this device.",
        )
        appearance_row = QHBoxLayout()
        theme_label = QLabel("Colour theme")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.addItem("Dark", "dark")
        selected_index = self.theme_combo.findData(current_theme)
        self.theme_combo.setCurrentIndex(max(0, selected_index))
        self.theme_combo.setAccessibleName("Colour theme")
        self.theme_combo.currentIndexChanged.connect(
            lambda: self.theme_changed.emit(str(self.theme_combo.currentData()))
        )
        appearance_row.addWidget(theme_label)
        appearance_row.addStretch(1)
        appearance_row.addWidget(self.theme_combo)
        appearance.layout().addLayout(appearance_row)

        about_card = self.add_card(
            "About & contact",
            APP_DESCRIPTION,
        )
        about_layout = about_card.layout()
        version_label = QLabel(f"Steady version {escape(APP_VERSION)}")
        version_label.setObjectName("muted")
        about_layout.addWidget(version_label)
        author_label = QLabel(f"Created by: {escape(AUTHOR_NAME)}")
        about_layout.addWidget(author_label)
        contact_label = QLabel()
        contact_label.setTextFormat(Qt.TextFormat.RichText)
        contact_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        contact_label.setOpenExternalLinks(True)
        contact_label.setWordWrap(True)
        if CONTACT_EMAIL.strip():
            safe_email = escape(CONTACT_EMAIL.strip())
            mailto = quote(CONTACT_EMAIL.strip(), safe="@.+-_")
            contact_label.setText(
                f'Contact: <a href="mailto:{mailto}">{safe_email}</a>'
            )
        else:
            contact_label.setObjectName("muted")
            contact_label.setText(
                "Contact email: not configured. Before publishing, edit "
                "CONTACT_EMAIL in src/steady/app_info.py and rebuild."
            )
        about_layout.addWidget(contact_label)
        source_hint = QLabel(" ")
        source_hint.setObjectName("muted")
        source_hint.setWordWrap(True)
        about_layout.addWidget(source_hint)

        feedback_card = self.add_card(
            "Feedback",
            "Help improve Steady. Share suggestions, report a problem or tell us what is working well.",
        )
        feedback_layout = feedback_card.layout()
        feedback_hint = QLabel("Your feedback helps shape future improvements.")
        feedback_hint.setObjectName("muted")
        feedback_hint.setWordWrap(True)
        feedback_layout.addWidget(feedback_hint)

        # Use the supplied terracotta banner itself as the clickable control.
        # It is deliberately centred and prominent, rather than a small text
        # button tucked into the corner of the Feedback card.
        feedback_image_path = (
            Path(__file__).resolve().parents[2]
            / "assets"
            / "feedback_form_button.png"
        )
        self.feedback_button = QPushButton()
        self.feedback_button.setObjectName("feedbackImageButton")
        self.feedback_button.setAccessibleName("Open the Steady feedback Google Form")
        self.feedback_button.setToolTip("Open the Steady feedback form in your web browser")
        self.feedback_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.feedback_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.feedback_button.setFlat(True)
        if feedback_image_path.is_file():
            self.feedback_button.setIcon(QIcon(str(feedback_image_path)))
            self.feedback_button.setIconSize(QSize(570, 190))
            self.feedback_button.setFixedSize(590, 200)
        else:
            # Keep a usable fallback if an asset is accidentally omitted from a build.
            self.feedback_button.setText("Open feedback form")
            self.feedback_button.setObjectName("primaryButton")
        self.feedback_button.setStyleSheet(
            "QPushButton#feedbackImageButton { background: transparent; border: 2px solid transparent; padding: 0px; }"
            "QPushButton#feedbackImageButton:hover { background: rgba(179, 76, 72, 18); border-color: rgba(179, 76, 72, 100); border-radius: 12px; }"
            "QPushButton#feedbackImageButton:focus { border: 2px solid #b34c48; border-radius: 12px; }"
            "QPushButton#feedbackImageButton:pressed { background: rgba(179, 76, 72, 35); }"
        )
        self.feedback_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(FEEDBACK_FORM_URL))
        )
        feedback_button_row = QHBoxLayout()
        feedback_button_row.addStretch(1)
        feedback_button_row.addWidget(self.feedback_button)
        feedback_button_row.addStretch(1)
        feedback_layout.addLayout(feedback_button_row)

        data_card = self.add_card(
            "Local data, backups & exports",
            "Your planner stays on this device. Automatic backups are created at most once every 24 hours.",
        )
        data_layout = data_card.layout()
        self.database_path_label = QLabel(f"Database: {self.database.path}")
        self.database_path_label.setObjectName("muted")
        self.database_path_label.setWordWrap(True)
        data_layout.addWidget(self.database_path_label)

        self.backup_status = QLabel(backup_notice or "Automatic backup status will appear here.")
        self.backup_status.setObjectName("muted")
        self.backup_status.setWordWrap(True)
        data_layout.addWidget(self.backup_status)

        backup_row = QHBoxLayout()
        self.backup_button = QPushButton("Back up now")
        self.backup_button.setObjectName("primaryButton")
        self.backup_button.clicked.connect(self._backup_now)
        self.restore_button = QPushButton("Restore backup…")
        self.restore_button.setObjectName("subtleButton")
        self.restore_button.clicked.connect(self._restore_backup)
        self.export_button = QPushButton("Export CSV…")
        self.export_button.setObjectName("subtleButton")
        self.export_button.clicked.connect(self._export_csv)
        self.check_button = QPushButton("Check database")
        self.check_button.setObjectName("subtleButton")
        self.check_button.clicked.connect(self._check_integrity)
        backup_row.addWidget(self.backup_button)
        backup_row.addWidget(self.restore_button)
        backup_row.addWidget(self.export_button)
        backup_row.addWidget(self.check_button)
        backup_row.addStretch(1)
        data_layout.addLayout(backup_row)

        self.operation_status = QLabel("")
        self.operation_status.setObjectName("muted")
        self.operation_status.setWordWrap(True)
        data_layout.addWidget(self.operation_status)
        self.layout.addStretch(1)

    def set_current_theme(self, mode: str) -> None:
        index = self.theme_combo.findData(mode)
        if index >= 0:
            previous = self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(index)
            self.theme_combo.blockSignals(previous)

    def _backup_now(self) -> None:
        default_name = f"Steady_Backup_{self.data_service._utc_stamp()}.sqlite3"
        destination, _ = QFileDialog.getSaveFileName(
            self, "Save Steady backup", str(Path.home() / default_name),
            "Steady SQLite backup (*.sqlite3)",
        )
        if not destination:
            return
        if not destination.lower().endswith(".sqlite3"):
            destination += ".sqlite3"
        try:
            saved = self.data_service.backup_to(destination)
        except DataManagementError as exc:
            QMessageBox.critical(self, "Backup failed", str(exc))
            return
        self.operation_status.setText(f"Backup created successfully: {saved}")
        QMessageBox.information(self, "Backup complete", f"Your backup was saved to:\n{saved}")

    def _restore_backup(self) -> None:
        source, _ = QFileDialog.getOpenFileName(
            self, "Choose a Steady backup", str(Path.home()),
            "Steady SQLite backup (*.sqlite3 *.db *.sqlite);;All files (*)",
        )
        if not source:
            return
        try:
            self.data_service.validate_database_file(source)
        except DataManagementError as exc:
            QMessageBox.critical(self, "Backup cannot be restored", str(exc))
            return

        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setWindowTitle("Restore this backup?")
        confirm.setText(
            "Restoring replaces the current planner data with the selected backup. "
            "Steady will first create a safety backup of the current database. "
            "A running focus session must be stopped before restoring. Continue?"
        )
        restore_button = confirm.addButton("Restore", QMessageBox.ButtonRole.AcceptRole)
        confirm.addButton(QMessageBox.StandardButton.Cancel)
        confirm.setDefaultButton(QMessageBox.StandardButton.Cancel)
        confirm.exec()
        if confirm.clickedButton() is not restore_button:
            return
        try:
            safety_copy = self.data_service.restore_from(source)
        except DataManagementError as exc:
            QMessageBox.critical(self, "Restore failed", str(exc))
            return

        self.operation_status.setText(
            f"Backup restored. Safety copy of the previous database: {safety_copy}"
        )
        self.data_restored.emit()
        QMessageBox.information(
            self, "Restore complete",
            f"The selected backup has been restored. Your previous database was preserved at:\n{safety_copy}",
        )

    def _export_csv(self) -> None:
        destination = QFileDialog.getExistingDirectory(
            self, "Choose a folder for CSV export", str(Path.home())
        )
        if not destination:
            return
        try:
            export_dir = self.data_service.export_csv(destination)
        except DataManagementError as exc:
            QMessageBox.critical(self, "CSV export failed", str(exc))
            return
        self.operation_status.setText(f"CSV export created: {export_dir}")
        QMessageBox.information(
            self, "CSV export complete", f"All planner tables were exported to:\n{export_dir}"
        )

    def _check_integrity(self) -> None:
        try:
            report = self.data_service.integrity_report()
        except DataManagementError as exc:
            QMessageBox.critical(self, "Database check failed", str(exc))
            return

        counts = report["row_counts"]
        count_lines = "\n".join(f"  {name}: {count}" for name, count in counts.items())
        message = (
            "SQLite integrity check: OK\n"
            "Foreign-key check: OK\n"
            f"Schema version: {report['schema_version']}\n"
            f"Total rows: {report['total_rows']}\n\n"
            f"Rows by table:\n{count_lines}"
        )
        self.operation_status.setText(
            f"Database check passed. {report['total_rows']} rows across {len(counts)} tables."
        )
        QMessageBox.information(self, "Database integrity", message)
