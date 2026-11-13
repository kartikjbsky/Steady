from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from steady.database import Database
from steady.repositories.planner_repository import PlannerRepository
from steady.ui.dialogs.copy_tasks_dialog import CopyTasksDialog
from steady.ui.dialogs.task_dialog import MissReasonDialog, TaskDialog
from .base_page import BasePage


class DayPage(BasePage):
    """A date-specific task matrix and daily habit check-in."""

    selected_date_changed = Signal(object)

    STATUS_OPTIONS = (
        ("To do", "todo"),
        ("In progress", "in_progress"),
        ("Done", "done"),
        ("Missed", "missed"),
        ("Cancelled", "cancelled"),
    )

    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(
            "Daily plan",
            "One day at a time. Choose a useful next step; the plan can change as your day changes.",
            parent,
        )
        self.repository = PlannerRepository(database)
        self.current_day = date.today()

        self._build_date_controls()
        self._build_progress_card()
        self._build_task_card()
        self._build_habit_card()
        self.layout.addStretch(1)
        self.load_day(self.current_day)

    def set_selected_day(self, selected_day: date) -> None:
        """Select a date from another page and refresh this daily plan."""
        target = QDate(selected_day.year, selected_day.month, selected_day.day)
        if self.date_input.date() == target:
            self.load_day(selected_day)
        else:
            # dateChanged calls _date_changed(), which loads and emits the date.
            self.date_input.setDate(target)

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        card_layout.addWidget(heading)
        self.layout.addWidget(card)
        return card, card_layout

    def _build_date_controls(self) -> None:
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.previous_button = QPushButton("‹")
        self.previous_button.setAccessibleName("Previous day")
        self.previous_button.setToolTip("Previous day")
        self.previous_button.setFixedWidth(38)
        self.previous_button.clicked.connect(lambda: self._move_day(-1))

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("ddd, d MMM yyyy")
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setAccessibleName("Selected date")
        self.date_input.dateChanged.connect(self._date_changed)
        self.date_input.setFixedWidth(180)

        self.next_button = QPushButton("›")
        self.next_button.setAccessibleName("Next day")
        self.next_button.setToolTip("Next day")
        self.next_button.setFixedWidth(38)
        self.next_button.clicked.connect(lambda: self._move_day(1))

        self.today_button = QPushButton("Today")
        self.today_button.clicked.connect(lambda: self.date_input.setDate(QDate.currentDate()))

        controls.addWidget(self.previous_button)
        controls.addWidget(self.date_input)
        controls.addWidget(self.next_button)
        controls.addWidget(self.today_button)
        controls.addStretch(1)
        self.layout.addLayout(controls)

    def _build_progress_card(self) -> None:
        self.progress_card, card_layout = self._card("Your day at a glance")
        row = QHBoxLayout()
        self.progress_text = QLabel("No tasks planned yet")
        self.progress_text.setObjectName("muted")
        self.progress_percent = QLabel("0%")
        self.progress_percent.setStyleSheet("font-weight: 700; font-size: 13pt;")
        row.addWidget(self.progress_text)
        row.addStretch(1)
        row.addWidget(self.progress_percent)
        self.task_progress = QProgressBar()
        self.task_progress.setRange(0, 100)
        self.task_progress.setValue(0)
        self.task_progress.setTextVisible(False)
        self.task_progress.setAccessibleName("Task completion progress")
        card_layout.addLayout(row)
        card_layout.addWidget(self.task_progress)

    def _build_task_card(self) -> None:
        self.task_card, card_layout = self._card("Tasks")
        toolbar = QHBoxLayout()
        hint = QLabel("Keep tasks small and specific. You can edit a task by double-clicking its name.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        self.copy_tasks_button = QPushButton("Copy from date")
        self.copy_tasks_button.setObjectName("subtleButton")
        self.copy_tasks_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_tasks_button.setToolTip("Add a copy of the tasks from another date")
        self.copy_tasks_button.clicked.connect(self._copy_tasks)

        self.add_task_button = QPushButton("＋  Add task")
        self.add_task_button.setObjectName("primaryButton")
        self.add_task_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_task_button.clicked.connect(self._add_task)
        toolbar.addWidget(hint, 1)
        toolbar.addWidget(self.copy_tasks_button)
        toolbar.addWidget(self.add_task_button)
        card_layout.addLayout(toolbar)

        self.task_table = QTableWidget(0, 5)
        self.task_table.setHorizontalHeaderLabels(["Task", "Priority", "Estimate", "Status", ""])
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setShowGrid(False)
        self.task_table.setWordWrap(True)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.verticalHeader().setDefaultSectionSize(48)
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.task_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.task_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.task_table.setAccessibleName("Tasks for selected date")
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.itemDoubleClicked.connect(self._edit_task_from_item)
        card_layout.addWidget(self.task_table)

        self.empty_tasks_label = QLabel("Nothing scheduled here yet. Add one small task to get started.")
        self.empty_tasks_label.setObjectName("muted")
        self.empty_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_tasks_label.setMinimumHeight(48)
        card_layout.addWidget(self.empty_tasks_label)

    def _build_habit_card(self) -> None:
        self.habit_card, card_layout = self._card("Daily habits")
        description = QLabel("Small check-ins count. Leave a habit unticked when you haven't done it yet.")
        description.setObjectName("muted")
        description.setWordWrap(True)
        card_layout.addWidget(description)
        self.habit_list_layout = QVBoxLayout()
        self.habit_list_layout.setSpacing(8)
        card_layout.addLayout(self.habit_list_layout)
        self.empty_habits_label = QLabel("No habits are scheduled for this day.")
        self.empty_habits_label.setObjectName("muted")
        card_layout.addWidget(self.empty_habits_label)

    def _move_day(self, offset: int) -> None:
        self.date_input.setDate(self.date_input.date().addDays(offset))

    def _date_changed(self, selected: QDate) -> None:
        self.load_day(date(selected.year(), selected.month(), selected.day()))

    def load_day(self, selected_day: date) -> None:
        self.current_day = selected_day
        self.copy_tasks_button.setEnabled(selected_day >= date.today())
        self.copy_tasks_button.setToolTip(
            "Add a copy of the tasks from another date"
            if selected_day >= date.today()
            else "Past dates are read-only"
        )
        self.selected_date_changed.emit(selected_day)
        tasks = self.repository.list_tasks(selected_day)
        habits = self.repository.list_habits(selected_day)
        self._populate_tasks(tasks)
        self._populate_habits(habits)
        done_count = sum(task["status"] == "done" for task in tasks)
        total = len(tasks)
        percentage = round((done_count / total) * 100) if total else 0
        self.progress_text.setText(
            f"{done_count} of {total} tasks completed" if total else "No tasks planned yet"
        )
        self.progress_percent.setText(f"{percentage}%")
        self.task_progress.setValue(percentage)

    def _populate_tasks(self, tasks: list[dict[str, Any]]) -> None:
        self.task_table.setRowCount(0)
        self.empty_tasks_label.setVisible(not tasks)
        self.task_table.setVisible(bool(tasks))

        for row, task in enumerate(tasks):
            self.task_table.insertRow(row)
            title_item = QTableWidgetItem(task["title"])
            title_item.setData(Qt.ItemDataRole.UserRole, task["id"])
            if task["status"] == "done":
                title_item.setForeground(Qt.GlobalColor.gray)
                title_item.setToolTip("Completed. Double-click to edit this task.")
            else:
                title_item.setToolTip("Double-click to edit this task.")
            self.task_table.setItem(row, 0, title_item)

            priority = QComboBox()
            for label, value in (("Low", 1), ("Normal", 2), ("High", 3)):
                priority.addItem(label, value)
            priority.setCurrentIndex(priority.findData(task["priority"]))
            priority.setAccessibleName(f"Priority for {task['title']}")
            priority.currentIndexChanged.connect(
                lambda _index, task_id=task["id"], widget=priority: self._update_task_field(
                    task_id, "priority", int(widget.currentData())
                )
            )
            self.task_table.setCellWidget(row, 1, priority)

            estimate = QSpinBox()
            estimate.setRange(0, 1440)
            estimate.setSpecialValueText("—")
            estimate.setSuffix(" min")
            estimate.setValue(int(task["estimate_minutes"] or 0))
            estimate.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            estimate.setAccessibleName(f"Estimated minutes for {task['title']}")
            estimate.valueChanged.connect(
                lambda value, task_id=task["id"]: self._update_task_field(
                    task_id, "estimate_minutes", value if value > 0 else None
                )
            )
            self.task_table.setCellWidget(row, 2, estimate)

            status = QComboBox()
            for label, value in self.STATUS_OPTIONS:
                status.addItem(label, value)
            status.setCurrentIndex(status.findData(task["status"]))
            status.setAccessibleName(f"Status for {task['title']}")
            status.currentIndexChanged.connect(
                lambda _index, task_id=task["id"], widget=status, previous=task["status"]:
                    self._update_task_status(task_id, str(widget.currentData()), previous)
            )
            self.task_table.setCellWidget(row, 3, status)

            remove_button = QPushButton("Remove")
            remove_button.setObjectName("subtleButton")
            remove_button.setToolTip(f"Remove {task['title']}")
            remove_button.setAccessibleName(f"Remove task {task['title']}")
            remove_button.clicked.connect(lambda _checked=False, task_id=task["id"]: self._remove_task(task_id))
            self.task_table.setCellWidget(row, 4, remove_button)

    def _populate_habits(self, habits: list[dict[str, Any]]) -> None:
        while self.habit_list_layout.count():
            item = self.habit_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.empty_habits_label.setVisible(not habits)

        for habit in habits:
            row = QFrame()
            row.setObjectName("habitRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(10, 8, 10, 8)

            checkbox = QCheckBox(habit["name"])
            checkbox.setChecked(habit["status"] == "done")
            checkbox.setAccessibleName(f"Mark {habit['name']} complete")
            checkbox.toggled.connect(
                lambda checked, habit_id=habit["id"]: self._set_habit_done(habit_id, checked)
            )
            layout.addWidget(checkbox, 1)

            if habit["description"]:
                note = QLabel(habit["description"])
                note.setObjectName("muted")
                note.setWordWrap(True)
                layout.addWidget(note)
            self.habit_list_layout.addWidget(row)

    def _copy_tasks(self) -> None:
        dialog = CopyTasksDialog(self.current_day, self)
        if not dialog.exec():
            return

        source_day = dialog.source_day()
        if source_day == self.current_day:
            QMessageBox.information(
                self, "Choose another date",
                "The source date must be different from the selected date.",
            )
            return

        source_tasks = self.repository.list_tasks(source_day)
        if not source_tasks:
            QMessageBox.information(
                self, "No tasks to copy",
                f"There are no tasks planned for {source_day.strftime('%a, %d %b %Y')}.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Copy tasks?",
            f"Copy {len(source_tasks)} task(s) from "
            f"{source_day.strftime('%a, %d %b %Y')} to "
            f"{self.current_day.strftime('%a, %d %b %Y')}?\n\n"
            "They will be added to the existing task list with status set to To do.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            copied = self.repository.copy_tasks(source_day, self.current_day)
            self.load_day(self.current_day)
            QMessageBox.information(
                self, "Tasks copied",
                f"Added {copied} task(s) to the selected date.",
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not copy tasks", str(exc))

    def _add_task(self) -> None:
        dialog = TaskDialog(self)
        if dialog.exec():
            try:
                self.repository.add_task(day=self.current_day, **dialog.values())
                self.load_day(self.current_day)
            except (ValueError, RuntimeError) as exc:
                QMessageBox.warning(self, "Could not add task", str(exc))

    def _edit_task_from_item(self, item: QTableWidgetItem) -> None:
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = next((row for row in self.repository.list_tasks(self.current_day) if row["id"] == task_id), None)
        if task is None:
            return
        dialog = TaskDialog(self, task=task)
        if dialog.exec():
            try:
                self.repository.update_task(task_id, **dialog.values())
                self.load_day(self.current_day)
            except (ValueError, RuntimeError) as exc:
                QMessageBox.warning(self, "Could not update task", str(exc))

    def _update_task_field(self, task_id: int, field: str, value: Any) -> None:
        try:
            self.repository.update_task(task_id, **{field: value})
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update task", str(exc))
            self.load_day(self.current_day)

    def _update_task_status(self, task_id: int, status: str, previous_status: str) -> None:
        changes: dict[str, Any] = {"status": status, "miss_reason_id": None, "reflection_note": ""}
        if status == "missed":
            dialog = MissReasonDialog(self.repository.list_miss_reasons(), self)
            if dialog.exec():
                reason_id, note = dialog.values()
                changes["miss_reason_id"] = reason_id
                changes["reflection_note"] = note
        try:
            self.repository.update_task(task_id, **changes)
            self.load_day(self.current_day)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update task", str(exc))
            self.load_day(self.current_day)

    def _remove_task(self, task_id: int) -> None:
        answer = QMessageBox.question(
            self,
            "Remove task?",
            "Remove this task from the selected day?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.repository.delete_task(task_id)
            self.load_day(self.current_day)

    def _set_habit_done(self, habit_id: int, checked: bool) -> None:
        try:
            self.repository.set_habit_status(
                habit_id, self.current_day, "done" if checked else "pending"
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update habit", str(exc))
            self.load_day(self.current_day)
