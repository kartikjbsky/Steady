from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from typing import Any

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from steady.database import Database
from steady.repositories.settings_repository import SettingsRepository
from steady.repositories.timetable_repository import TimetableRepository
from steady.services.timetable_slots import normalise_time_slots
from .base_page import BasePage


class TimetableEntryDialog(QDialog):
    """Add or edit the activity occupying one recurring weekly time slot."""

    def __init__(
        self,
        *,
        weekday_name: str,
        slot_label: str,
        entry: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.entry = entry
        self.clear_requested = False
        self.setWindowTitle("Edit timetable block" if entry else "Add to timetable")
        self.setMinimumWidth(430)

        layout = QVBoxLayout(self)
        heading = QLabel(f"{weekday_name} · {slot_label}")
        heading.setStyleSheet("font-size: 13pt; font-weight: 800;")
        layout.addWidget(heading)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.title_input = QLineEdit(entry["title"] if entry else "")
        self.title_input.setPlaceholderText("e.g. Quantum mechanics, lecture, lunch…")
        self.title_input.setMaxLength(120)
        self.title_input.setAccessibleName("Timetable activity")

        self.notes_input = QTextEdit()
        self.notes_input.setPlainText(entry["notes"] if entry else "")
        self.notes_input.setPlaceholderText("Optional details")
        self.notes_input.setMaximumHeight(90)
        self.notes_input.setAccessibleName("Timetable activity notes")

        form.addRow("Task / activity", self.title_input)
        form.addRow("Notes", self.notes_input)
        layout.addLayout(form)

        self.clear_button = QPushButton("Clear this box")
        self.clear_button.setObjectName("dangerButton")
        self.clear_button.setVisible(entry is not None)
        self.clear_button.clicked.connect(self._request_clear)
        layout.addWidget(self.clear_button, alignment=Qt.AlignmentFlag.AlignLeft)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.title_input.setFocus()

    def values(self) -> dict[str, str]:
        return {
            "title": self.title_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip(),
        }

    def _request_clear(self) -> None:
        self.clear_requested = True
        self.accept()

    def accept(self) -> None:
        if not self.clear_requested and not self.title_input.text().strip():
            QMessageBox.information(self, "Activity needed", "Enter a task or activity for this time slot.")
            self.title_input.setFocus()
            return
        super().accept()


class TimetableSettingsDialog(QDialog):
    """Edit every timetable period independently with custom start and end times."""

    def __init__(
        self,
        *,
        slots: list[tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit timetable times")
        self.setMinimumSize(510, 430)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Create your own periods. Each row can have a different start and end time; "
            "for example, 7:00–8:30, then 9:00–10:15. Periods cannot overlap."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.slots_table = QTableWidget(0, 2)
        self.slots_table.setHorizontalHeaderLabels(["Starts at", "Ends at"])
        self.slots_table.verticalHeader().setVisible(False)
        self.slots_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.slots_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.slots_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.slots_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.slots_table.setMinimumHeight(230)
        layout.addWidget(self.slots_table, 1)

        controls = QHBoxLayout()
        self.add_slot_button = QPushButton("Add time period")
        self.add_slot_button.clicked.connect(self._add_slot)
        self.remove_slot_button = QPushButton("Remove selected")
        self.remove_slot_button.setObjectName("dangerButton")
        self.remove_slot_button.clicked.connect(self._remove_selected)
        controls.addWidget(self.add_slot_button)
        controls.addWidget(self.remove_slot_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        note = QLabel(
            "You can use any minute value. Existing activities are kept; Steady will stop a change "
            "that would hide a saved activity."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for start_time, end_time in slots:
            self._add_slot(start_time, end_time)

    @staticmethod
    def _make_time_input(value: str) -> QTimeEdit:
        parsed = time.fromisoformat(value)
        control = QTimeEdit(QTime(parsed.hour, parsed.minute))
        control.setDisplayFormat("h:mm AP")
        control.setMinimumWidth(170)
        control.setKeyboardTracking(False)
        return control

    def _add_slot(self, start_time: str | None = None, end_time: str | None = None) -> None:
        if start_time is None or end_time is None:
            if self.slots_table.rowCount():
                last_end_control = self.slots_table.cellWidget(self.slots_table.rowCount() - 1, 1)
                last_end = last_end_control.time()
                start_minutes = last_end.hour() * 60 + last_end.minute()
            else:
                start_minutes = 7 * 60
            end_minutes = min(start_minutes + 60, 23 * 60 + 59)
            if start_minutes >= 23 * 60 + 59:
                QMessageBox.information(self, "No more room today", "The last period already ends at the end of the day.")
                return
            start_time = f"{start_minutes // 60:02d}:{start_minutes % 60:02d}"
            end_time = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"

        row = self.slots_table.rowCount()
        self.slots_table.insertRow(row)
        self.slots_table.setCellWidget(row, 0, self._make_time_input(start_time))
        self.slots_table.setCellWidget(row, 1, self._make_time_input(end_time))
        self.slots_table.setRowHeight(row, 48)
        self.slots_table.selectRow(row)

    def _remove_selected(self) -> None:
        row = self.slots_table.currentRow()
        if row >= 0:
            self.slots_table.removeRow(row)

    def values(self) -> dict[str, Any]:
        rows: list[tuple[str, str]] = []
        for row in range(self.slots_table.rowCount()):
            start = self.slots_table.cellWidget(row, 0).time()
            end = self.slots_table.cellWidget(row, 1).time()
            rows.append((f"{start.hour():02d}:{start.minute():02d}", f"{end.hour():02d}:{end.minute():02d}"))
        return {"slots": normalise_time_slots(rows)}

    def accept(self) -> None:
        try:
            self.values()
        except ValueError as exc:
            QMessageBox.information(self, "Check the timetable times", str(exc))
            return
        super().accept()


class TimetablePage(BasePage):
    """An editable, recurring Monday-to-Sunday timetable matrix."""

    DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    DEFAULT_START = "07:00"
    DEFAULT_END = "19:00"
    DEFAULT_INTERVAL = 60

    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(
            "Weekly timetable",
            "Build a gentle weekly structure. Every box starts empty; click a time and day to add an activity.",
            parent,
        )
        self.repository = TimetableRepository(database)
        self.settings = SettingsRepository(database)
        self.slots = self._load_saved_slots()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        inner = QWidget()
        inner.setObjectName("scrollContent")
        inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content = QVBoxLayout(inner)
        content.setContentsMargins(0, 0, 6, 5)
        content.setSpacing(13)

        toolbar = QHBoxLayout()
        self.range_label = QLabel("")
        self.range_label.setObjectName("muted")
        toolbar.addWidget(self.range_label)
        toolbar.addStretch(1)
        configure_button = QPushButton("Edit individual time periods")
        configure_button.setObjectName("subtleButton")
        configure_button.setAccessibleName("Edit, add or remove individual timetable time periods")
        configure_button.setToolTip("Set a separate start and end time for every timetable row. Periods can have different lengths.")
        configure_button.clicked.connect(self._configure_timetable)
        toolbar.addWidget(configure_button)
        content.addLayout(toolbar)
        settings_hint = QLabel("Choose your own time periods. Every row can have a different start and end time; the timetable starts empty.")
        settings_hint.setObjectName("muted")
        settings_hint.setWordWrap(True)
        content.addWidget(settings_hint)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 13, 14, 14)
        card_layout.setSpacing(8)
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["Time", *self.DAY_NAMES])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for column in range(1, 8):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        # Keep the full seven-day matrix readable on smaller windows.
        # A horizontal scrollbar appears when the viewport cannot fit the matrix.
        self.table.setMinimumWidth(1320)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setAccessibleName("Weekly timetable matrix. Select any day and time cell to add or edit an activity.")
        self.table.cellClicked.connect(self._cell_clicked)
        self.table.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout.addWidget(self.table)
        content.addWidget(card)

        hint = QLabel("Activities repeat every week. Leave a box blank when you have nothing planned; you can edit each period independently, as long as saved activities remain visible.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        content.addWidget(hint)
        content.addStretch(1)
        scroll.setWidget(inner)
        self.layout.addWidget(scroll, 1)
        self.refresh()

    @staticmethod
    def _make_slots(start_time: str, end_time: str, interval_minutes: int) -> list[tuple[str, str]]:
        start = datetime.combine(date.today(), time.fromisoformat(start_time))
        end = datetime.combine(date.today(), time.fromisoformat(end_time))
        slots: list[tuple[str, str]] = []
        cursor = start
        while cursor < end:
            next_cursor = min(cursor + timedelta(minutes=interval_minutes), end)
            slots.append((cursor.strftime("%H:%M"), next_cursor.strftime("%H:%M")))
            cursor = next_cursor
        return slots

    def _load_saved_slots(self) -> list[tuple[str, str]]:
        raw = self.settings.get("timetable_custom_slots", "") or ""
        if raw:
            try:
                parsed = json.loads(raw)
                slots = normalise_time_slots((str(item[0]), str(item[1])) for item in parsed)
                return slots
            except (ValueError, TypeError, IndexError, KeyError):
                pass

        # Read settings saved by the earlier uniform-block timetable version.
        start = self.settings.get("timetable_start_time", self.DEFAULT_START) or self.DEFAULT_START
        end = self.settings.get("timetable_end_time", self.DEFAULT_END) or self.DEFAULT_END
        try:
            interval = int(self.settings.get("timetable_interval_minutes", str(self.DEFAULT_INTERVAL)) or self.DEFAULT_INTERVAL)
            if interval <= 0:
                interval = self.DEFAULT_INTERVAL
            return normalise_time_slots(self._make_slots(start, end, interval))
        except (ValueError, TypeError):
            return self._make_slots(self.DEFAULT_START, self.DEFAULT_END, self.DEFAULT_INTERVAL)

    @staticmethod
    def _format_time(value: str) -> str:
        parsed = time.fromisoformat(value)
        return parsed.strftime("%I:%M %p").lstrip("0")

    def _format_slot(self, start: str, end: str) -> str:
        return f"{self._format_time(start)} – {self._format_time(end)}"

    def refresh(self) -> None:
        slots = self.slots
        self.range_label.setText(
            f"{self._format_time(slots[0][0])} to {self._format_time(slots[-1][1])} · {len(slots)} custom time periods"
        )
        entries = {
            (int(item["weekday"]), item["start_time"]): item
            for item in self.repository.list_entries()
        }
        self.table.clearContents()
        self.table.setRowCount(len(slots))
        for row, (slot_start, slot_end) in enumerate(slots):
            full_slot_label = self._format_slot(slot_start, slot_end)
            time_item = QTableWidgetItem(full_slot_label)
            time_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            time_item.setToolTip(full_slot_label)
            self.table.setItem(row, 0, time_item)
            for weekday in range(7):
                entry = entries.get((weekday, slot_start))
                title = entry["title"] if entry else ""
                cell = QTableWidgetItem(title)
                cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cell.setToolTip(
                    (entry["notes"] or entry["title"]) if entry
                    else f"Click to add an activity for {self.DAY_NAMES[weekday]}"
                )
                cell.setData(Qt.ItemDataRole.UserRole, entry["id"] if entry else None)
                cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(row, weekday + 1, cell)
            self.table.setRowHeight(row, 50)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 245)
        self.table.setFixedHeight(self.table.horizontalHeader().height() + sum(self.table.rowHeight(i) for i in range(len(slots))) + 4)
        for column in range(1, 8):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)

    def _cell_clicked(self, row: int, column: int) -> None:
        if column < 1 or column > 7:
            return
        slots = self.slots
        if row < 0 or row >= len(slots):
            return
        slot_start, slot_end = slots[row]
        weekday = column - 1
        entry = self.repository.get_slot(weekday, slot_start)
        dialog = TimetableEntryDialog(
            weekday_name=self.DAY_NAMES[weekday],
            slot_label=self._format_slot(slot_start, slot_end),
            entry=entry,
            parent=self,
        )
        if not dialog.exec():
            return
        if dialog.clear_requested:
            answer = QMessageBox.question(
                self,
                "Clear timetable box",
                f"Remove the activity from {self.DAY_NAMES[weekday]} at {self._format_time(slot_start)}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.repository.clear_slot(weekday, slot_start)
        else:
            try:
                self.repository.save_slot(
                    weekday=weekday,
                    start_time=slot_start,
                    **dialog.values(),
                )
            except (ValueError, RuntimeError) as exc:
                QMessageBox.warning(self, "Could not save timetable block", str(exc))
        self.refresh()

    def _configure_timetable(self) -> None:
        dialog = TimetableSettingsDialog(slots=self.slots, parent=self)
        if not dialog.exec():
            return
        try:
            values = dialog.values()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid timetable times", str(exc))
            return
        allowed_starts = {start for start, _end in values["slots"]}
        hidden_entries = [
            entry for entry in self.repository.list_entries()
            if entry["start_time"] not in allowed_starts
        ]
        if hidden_entries:
            QMessageBox.warning(
                self,
                "Saved timetable blocks would be hidden",
                f"These settings would hide {len(hidden_entries)} saved block(s). "
                "Your entries would remain in the database, but would not appear in the grid. "
                "Keep the existing hours or move those blocks before changing the timetable.",
            )
            return

        self.slots = values["slots"]
        self.settings.set("timetable_custom_slots", json.dumps(self.slots))
        self.refresh()
