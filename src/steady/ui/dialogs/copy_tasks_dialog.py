from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class CopyTasksDialog(QDialog):
    """Choose the source date for copying tasks into the selected Daily Plan."""

    def __init__(
        self,
        target_day: date,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.target_day = target_day
        self.setWindowTitle("Copy tasks from another date")
        self.setMinimumWidth(390)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        target_label = QLabel(
            f"Tasks will be added to {target_day.strftime('%a, %d %b %Y')}."
        )
        target_label.setWordWrap(True)
        layout.addWidget(target_label)

        source_label = QLabel("Copy tasks from")
        layout.addWidget(source_label)

        self.source_date_input = QDateEdit()
        self.source_date_input.setCalendarPopup(True)
        self.source_date_input.setDisplayFormat("ddd, d MMM yyyy")
        self.source_date_input.setDate(QDate(target_day.year, target_day.month, target_day.day).addDays(-1))
        self.source_date_input.setAccessibleName("Date to copy tasks from")
        layout.addWidget(self.source_date_input)

        note = QLabel(
            "All tasks from that date will be added to the selected day. "
            "Existing tasks will stay, and copied tasks will start as To do."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)

        buttons = QDialogButtonBox()
        copy_button = buttons.addButton("Continue", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        copy_button.setObjectName("primaryButton")
        cancel_button.setObjectName("subtleButton")
        copy_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def source_day(self) -> date:
        selected = self.source_date_input.date()
        return date(selected.year(), selected.month(), selected.day())
