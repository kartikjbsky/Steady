from __future__ import annotations

from typing import Any

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDateEdit,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class TaskDialog(QDialog):
    """Small add/edit dialog. Keeps the form intentionally short."""

    def __init__(self, parent: QWidget | None = None, task: dict[str, Any] | None = None) -> None:
        super().__init__(parent)
        self.task = task or {}
        self.setWindowTitle("Edit task" if task else "Add a task")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(12)

        self.title_input = QLineEdit(str(self.task.get("title", "")))
        self.title_input.setPlaceholderText("e.g. Read one research paper")
        self.title_input.setAccessibleName("Task title")

        self.description_input = QTextEdit()
        self.description_input.setPlainText(str(self.task.get("description", "")))
        self.description_input.setPlaceholderText("Optional details or the first small step")
        self.description_input.setFixedHeight(76)
        self.description_input.setAccessibleName("Task description")

        self.priority_input = QComboBox()
        for label, value in (("Low", 1), ("Normal", 2), ("High", 3)):
            self.priority_input.addItem(label, value)
        self.priority_input.setCurrentIndex(max(0, self.priority_input.findData(int(self.task.get("priority", 2)))))

        self.estimate_input = QSpinBox()
        self.estimate_input.setRange(0, 1440)
        self.estimate_input.setSpecialValueText("Not set")
        self.estimate_input.setSuffix(" min")
        estimate = self.task.get("estimate_minutes")
        self.estimate_input.setValue(int(estimate) if estimate else 0)
        self.estimate_input.setToolTip("An estimate is a guide, not a deadline.")

        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("ddd, d MMM yyyy")
        self.date_input.setMinimumDate(QDate.currentDate())
        self.date_input.setAccessibleName("Task scheduled date")
        if self.task.get("scheduled_date"):
            self.date_input.setDate(QDate.fromString(str(self.task["scheduled_date"]), "yyyy-MM-dd"))

        form.addRow("Task name", self.title_input)
        form.addRow("Details", self.description_input)
        form.addRow("Priority", self.priority_input)
        form.addRow("Estimated time", self.estimate_input)
        if task:
            form.addRow("Scheduled date", self.date_input)
        layout.addLayout(form)

        # Custom text-only buttons avoid platform-provided emoji-style icons.
        buttons = QDialogButtonBox()
        save_button = buttons.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)
        cancel_button = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        save_button.setObjectName("primaryButton")
        cancel_button.setObjectName("subtleButton")
        save_button.clicked.connect(self._validate_and_accept)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.title_input.setFocus()

    def _validate_and_accept(self) -> None:
        if not self.title_input.text().strip():
            QMessageBox.information(self, "Add a task name", "Enter a short name for this task.")
            self.title_input.setFocus()
            return
        self.accept()

    def values(self) -> dict[str, Any]:
        estimate = self.estimate_input.value()
        values = {
            "title": self.title_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "priority": int(self.priority_input.currentData()),
            "estimate_minutes": estimate if estimate > 0 else None,
        }
        if self.task:
            values["scheduled_date"] = self.date_input.date().toPython()
        return values


class MissReasonDialog(QDialog):
    """Optional, non-judgemental reflection when a task is marked missed."""

    def __init__(
        self,
        reasons: list[dict[str, Any]],
        parent: QWidget | None = None,
        *,
        initial_reason_id: int | None = None,
        initial_note: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("A gentle check-in")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)

        from PySide6.QtWidgets import QLabel

        intro = QLabel("Would it be useful to note what got in the way? This is optional.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.reason_input = QComboBox()
        self.reason_input.addItem("Skip this question", None)
        for reason in reasons:
            self.reason_input.addItem(reason["label"], reason["id"])
        selected_index = self.reason_input.findData(initial_reason_id)
        self.reason_input.setCurrentIndex(max(0, selected_index))
        layout.addWidget(self.reason_input)

        self.note_input = QLineEdit()
        self.note_input.setText(initial_note)
        self.note_input.setPlaceholderText("Optional note")
        self.note_input.setAccessibleName("Optional reflection note")
        layout.addWidget(self.note_input)

        buttons = QDialogButtonBox()
        save_button = buttons.addButton("Save reflection", QDialogButtonBox.ButtonRole.AcceptRole)
        skip_button = buttons.addButton("No reason", QDialogButtonBox.ButtonRole.ActionRole)
        cancel_button = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        save_button.clicked.connect(self.accept)
        skip_button.clicked.connect(self._accept_without_reason)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_without_reason(self) -> None:
        self.reason_input.setCurrentIndex(0)
        self.note_input.clear()
        self.accept()

    def values(self) -> tuple[int | None, str]:
        return self.reason_input.currentData(), self.note_input.text().strip()
