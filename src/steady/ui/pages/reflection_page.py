from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from steady.database import Database
from steady.repositories.reflection_repository import ReflectionRepository
from steady.ui.dialogs.task_dialog import MissReasonDialog
from .base_page import BasePage


class ReflectionPage(BasePage):
    """Optional daily check-ins and a searchable-by-period missed-activity log."""

    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(
            "Reflection",
            "Notice patterns with curiosity, not judgement. You can leave any field blank.",
            parent,
        )
        self.repository = ReflectionRepository(database)
        self.current_day = date.today()

        scroll = QScrollArea()
        scroll.setObjectName("pageScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner.setObjectName("scrollContent")
        inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.content_layout = QVBoxLayout(inner)
        self.content_layout.setContentsMargins(0, 0, 6, 4)
        self.content_layout.setSpacing(14)
        scroll.setWidget(inner)
        self.layout.addWidget(scroll, 1)

        self._build_checkin_card()
        self._build_missed_card()
        self.content_layout.addStretch(1)
        self.load_day(self.current_day)
        self.refresh_missed_activities()

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        layout.addWidget(heading)
        self.content_layout.addWidget(card)
        return card, layout

    def _build_checkin_card(self) -> None:
        _card, layout = self._card("Daily check-in")
        intro = QLabel(
            "A short note can help you understand what supports your day. "
            "This is for observation, not scoring."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        date_row = QHBoxLayout()
        date_label = QLabel("Reflection date")
        date_label.setObjectName("fieldLabel")
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("ddd, d MMM yyyy")
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setFixedWidth(190)
        self.date_input.setAccessibleName("Date for daily reflection")
        self.date_input.dateChanged.connect(self._date_changed)
        date_row.addWidget(date_label)
        date_row.addWidget(self.date_input)
        date_row.addStretch(1)
        layout.addLayout(date_row)

        fields = QHBoxLayout()
        fields.setSpacing(14)
        energy_column = QVBoxLayout()
        energy_label = QLabel("Energy level")
        energy_label.setObjectName("fieldLabel")
        self.energy_input = QComboBox()
        self.energy_input.addItem("Not recorded", None)
        for label, value in (
            ("Very low", 1),
            ("Low", 2),
            ("Steady", 3),
            ("Good", 4),
            ("High", 5),
        ):
            self.energy_input.addItem(label, value)
        self.energy_input.setAccessibleName("Energy level from very low to high")
        energy_column.addWidget(energy_label)
        energy_column.addWidget(self.energy_input)

        mood_column = QVBoxLayout()
        mood_label = QLabel("Mood / working state")
        mood_label.setObjectName("fieldLabel")
        self.mood_input = QComboBox()
        self.mood_input.addItems((
            "Not recorded", "Calm", "Focused", "Neutral", "Motivated",
            "Restless", "Stressed", "Tired", "Overwhelmed",
        ))
        self.mood_input.setAccessibleName("Optional mood or working state")
        mood_column.addWidget(mood_label)
        mood_column.addWidget(self.mood_input)
        fields.addLayout(energy_column, 1)
        fields.addLayout(mood_column, 1)
        layout.addLayout(fields)

        note_label = QLabel("Notes")
        note_label.setObjectName("fieldLabel")
        self.note_input = QTextEdit()
        self.note_input.setAcceptRichText(False)
        self.note_input.setPlaceholderText(
            "What helped you get started? What made things harder? "
            "What would make the next step easier?"
        )
        self.note_input.setMinimumHeight(112)
        self.note_input.setMaximumHeight(170)
        self.note_input.setAccessibleName("Daily reflection notes")
        layout.addWidget(note_label)
        layout.addWidget(self.note_input)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("Save check-in")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self._save_daily_reflection)
        self.delete_button = QPushButton("Delete saved check-in")
        self.delete_button.setObjectName("subtleButton")
        self.delete_button.clicked.connect(self._delete_daily_reflection)
        self.saved_label = QLabel("No check-in saved for this date.")
        self.saved_label.setObjectName("muted")
        button_row.addWidget(self.saved_label, 1)
        button_row.addWidget(self.delete_button)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

    def _build_missed_card(self) -> None:
        _card, layout = self._card("Missed-activity notes")
        hint = QLabel(
            "Review what got in the way, or update a reason later. "
            "Leaving a reason unrecorded is completely fine."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        toolbar = QHBoxLayout()
        self.period_combo = QComboBox()
        self.period_combo.addItem("Last 7 days", 7)
        self.period_combo.addItem("Last 30 days", 30)
        self.period_combo.addItem("Last 90 days", 90)
        self.period_combo.setAccessibleName("Missed activity review period")
        self.period_combo.currentIndexChanged.connect(self.refresh_missed_activities)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("subtleButton")
        self.refresh_button.clicked.connect(self.refresh_missed_activities)
        toolbar.addWidget(QLabel("Review period"))
        toolbar.addWidget(self.period_combo)
        toolbar.addStretch(1)
        toolbar.addWidget(self.refresh_button)
        layout.addLayout(toolbar)

        self.missed_table = QTableWidget(0, 6)
        self.missed_table.setHorizontalHeaderLabels(
            ["Date", "Type", "Activity", "Reason", "Note", "Action"]
        )
        self.missed_table.setAlternatingRowColors(True)
        self.missed_table.setShowGrid(False)
        self.missed_table.setWordWrap(True)
        self.missed_table.verticalHeader().setVisible(False)
        self.missed_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.missed_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.missed_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.missed_table.setAccessibleName("Missed tasks and habits with optional reasons")
        header = self.missed_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.missed_table.setMinimumHeight(190)
        layout.addWidget(self.missed_table)

        self.empty_missed_label = QLabel(
            "No missed activities in this period. Keep going at your own pace."
        )
        self.empty_missed_label.setObjectName("muted")
        self.empty_missed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_missed_label.setMinimumHeight(48)
        layout.addWidget(self.empty_missed_label)

    def _date_changed(self, selected: QDate) -> None:
        self.load_day(date(selected.year(), selected.month(), selected.day()))

    def refresh(self) -> None:
        """Refresh the selected date and missed-activity list when the page opens."""
        self.load_day(self.current_day)
        self.refresh_missed_activities()

    def load_day(self, selected_day: date) -> None:
        self.current_day = selected_day
        record = self.repository.get_daily_reflection(selected_day)
        self.energy_input.blockSignals(True)
        self.mood_input.blockSignals(True)
        energy_value = record.get("energy_level") if record else None
        self.energy_input.setCurrentIndex(
            max(0, self.energy_input.findData(energy_value))
        )
        mood = str(record.get("mood_label", "") if record else "")
        mood_index = self.mood_input.findText(mood) if mood else 0
        self.mood_input.setCurrentIndex(max(0, mood_index))
        self.note_input.setPlainText(str(record.get("note", "") if record else ""))
        self.energy_input.blockSignals(False)
        self.mood_input.blockSignals(False)
        self.delete_button.setEnabled(record is not None)
        self.saved_label.setText(
            "Saved locally for this date." if record else "No check-in saved for this date."
        )

    def _save_daily_reflection(self) -> None:
        try:
            energy = self.energy_input.currentData()
            mood = self.mood_input.currentText()
            if mood == "Not recorded":
                mood = ""
            self.repository.save_daily_reflection(
                self.current_day,
                energy_level=int(energy) if energy is not None else None,
                mood_label=mood,
                note=self.note_input.toPlainText(),
            )
            self.delete_button.setEnabled(True)
            self.saved_label.setText("Saved locally for this date.")
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not save check-in", str(exc))

    def _delete_daily_reflection(self) -> None:
        answer = QMessageBox.question(
            self,
            "Delete this check-in?",
            "Delete the saved reflection for this date?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.repository.delete_daily_reflection(self.current_day)
        self.load_day(self.current_day)

    def refresh_missed_activities(self, *_args) -> None:
        days = int(self.period_combo.currentData())
        rows = self.repository.list_missed_activities(days)
        self.missed_table.setRowCount(len(rows))
        self.missed_table.setVisible(bool(rows))
        self.empty_missed_label.setVisible(not rows)
        for row_index, record in enumerate(rows):
            values = (
                str(record["activity_date"]),
                str(record["activity_type"]),
                str(record["activity"]),
                str(record["reason"]),
                str(record["note"]),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, record)
                item.setToolTip(value or "Not recorded")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.missed_table.setItem(row_index, column, item)
            edit_button = QPushButton("Edit note")
            edit_button.setObjectName("subtleButton")
            edit_button.setAccessibleName(
                f"Edit missed-activity reason for {record['activity']}"
            )
            edit_button.clicked.connect(
                lambda _checked=False, item_record=record: self._edit_missed_activity(item_record)
            )
            self.missed_table.setCellWidget(row_index, 5, edit_button)
        self.missed_table.resizeRowsToContents()

    def _edit_missed_activity(self, record: dict[str, Any]) -> None:
        dialog = MissReasonDialog(
            self.repository.list_miss_reasons(),
            self,
            initial_reason_id=record.get("miss_reason_id"),
            initial_note=str(record.get("note", "")),
        )
        if not dialog.exec():
            return
        reason_id, note = dialog.values()
        try:
            self.repository.update_missed_activity(
                str(record["activity_type"]),
                int(record["activity_id"]),
                miss_reason_id=reason_id,
                note=note,
            )
            self.refresh_missed_activities()
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update reflection", str(exc))
