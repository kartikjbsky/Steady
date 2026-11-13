from __future__ import annotations

from calendar import Calendar
from datetime import date
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from steady.database import Database
from steady.repositories.planner_repository import PlannerRepository
from .base_page import BasePage


class CalendarPage(BasePage):
    """Monthly calendar backed by the same dated records as the Daily Plan."""

    open_day_requested = Signal(object)

    WEEKDAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(
            "Calendar",
            "Choose a date to open its task and habit matrix.",
            parent,
        )
        self.repository = PlannerRepository(database)
        self.today = date.today()
        self.selected_day = self.today
        self.display_month = self.today.replace(day=1)
        self._day_buttons: dict[date, QPushButton] = {}

        self._build_month_controls()
        self._build_month_summary()
        self._build_calendar_card()
        self._build_legend()
        self.layout.addStretch(1)
        self.refresh()

    def _build_month_controls(self) -> None:
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.previous_button = QPushButton("‹")
        self.previous_button.setFixedWidth(40)
        self.previous_button.setAccessibleName("Previous month")
        self.previous_button.setToolTip("Previous month")
        self.previous_button.clicked.connect(lambda: self._change_month(-1))

        self.month_title = QLabel()
        self.month_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_title.setStyleSheet("font-size: 16pt; font-weight: 800;")
        self.month_title.setMinimumWidth(180)
        self.month_title.setAccessibleName("Displayed calendar month")

        self.next_button = QPushButton("›")
        self.next_button.setFixedWidth(40)
        self.next_button.setAccessibleName("Next month")
        self.next_button.setToolTip("Next month")
        self.next_button.clicked.connect(lambda: self._change_month(1))

        self.today_button = QPushButton("Today")
        self.today_button.setObjectName("subtleButton")
        self.today_button.setToolTip("Return to the current month")
        self.today_button.clicked.connect(self._go_to_today)

        controls.addWidget(self.previous_button)
        controls.addWidget(self.month_title, 0)
        controls.addWidget(self.next_button)
        controls.addSpacing(10)
        controls.addWidget(self.today_button)
        controls.addStretch(1)
        self.layout.addLayout(controls)

    def _build_month_summary(self) -> None:
        self.summary_card = QFrame()
        self.summary_card.setObjectName("card")
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        summary_layout.setSpacing(6)

        title = QLabel("This month")
        title.setStyleSheet("font-size: 13pt; font-weight: 800;")
        self.summary_label = QLabel("Loading your calendar…")
        self.summary_label.setObjectName("muted")
        self.summary_label.setWordWrap(True)
        self.month_progress = QLabel("")
        self.month_progress.setObjectName("muted")

        summary_layout.addWidget(title)
        summary_layout.addWidget(self.summary_label)
        summary_layout.addWidget(self.month_progress)
        self.layout.addWidget(self.summary_card)

    def _build_calendar_card(self) -> None:
        self.calendar_card = QFrame()
        self.calendar_card.setObjectName("card")
        card_layout = QVBoxLayout(self.calendar_card)
        card_layout.setContentsMargins(12, 12, 12, 14)
        card_layout.setSpacing(8)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setHorizontalSpacing(8)
        self.grid_layout.setVerticalSpacing(8)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for column, weekday in enumerate(self.WEEKDAY_LABELS):
            label = QLabel(weekday)
            label.setObjectName("muted")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-weight: 700; padding: 4px;")
            self.grid_layout.addWidget(label, 0, column)
            self.grid_layout.setColumnStretch(column, 1)

        card_layout.addWidget(self.grid_widget)
        self.layout.addWidget(self.calendar_card)

    def _build_legend(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(16)
        items = (
            ("Today", "calendarLegendToday"),
            ("Selected date", "calendarLegendSelected"),
            ("Activity recorded", "calendarLegendActivity"),
        )
        for label_text, object_name in items:
            item = QHBoxLayout()
            marker = QLabel("●")
            marker.setObjectName(object_name)
            label = QLabel(label_text)
            label.setObjectName("muted")
            item.addWidget(marker)
            item.addWidget(label)
            row.addLayout(item)
        row.addStretch(1)
        self.layout.addLayout(row)

    def _clear_day_cells(self) -> None:
        # Keep the weekday header row and remove only date buttons.
        for day_button in self._day_buttons.values():
            self.grid_layout.removeWidget(day_button)
            day_button.deleteLater()
        self._day_buttons.clear()

    def _change_month(self, offset: int) -> None:
        year = self.display_month.year
        month = self.display_month.month + offset
        if month < 1:
            year -= 1
            month = 12
        elif month > 12:
            year += 1
            month = 1
        self.display_month = date(year, month, 1)
        self.refresh()

    def _go_to_today(self) -> None:
        self.set_focus_date(date.today())

    def set_focus_date(self, selected_day: date) -> None:
        """Focus the calendar on a date, preserving a useful selected-day marker."""
        self.selected_day = selected_day
        self.display_month = selected_day.replace(day=1)
        self.today = date.today()
        self.refresh()

    def refresh(self) -> None:
        """Reload month indicators from SQLite and rebuild the month grid."""
        self.today = date.today()
        year, month = self.display_month.year, self.display_month.month
        self.month_title.setText(self.display_month.strftime("%B %Y"))
        month_data = self.repository.get_month_summary(year, month)

        task_total = sum(day["task_total"] for day in month_data.values())
        task_done = sum(day["task_done"] for day in month_data.values())
        habit_total = sum(day["habit_total"] for day in month_data.values())
        habit_done = sum(day["habit_done"] for day in month_data.values())
        self.summary_label.setText(
            f"{task_done} of {task_total} tasks completed  ·  "
            f"{habit_done} of {habit_total} habit check-ins completed"
        )
        if task_total:
            percentage = round((task_done / task_total) * 100)
            self.month_progress.setText(f"Task completion this month: {percentage}%")
        else:
            self.month_progress.setText("Add tasks from Daily Plan to see your progress here.")

        self._clear_day_cells()
        weeks = Calendar(firstweekday=0).monthdatescalendar(year, month)
        for week_row, week in enumerate(weeks, start=1):
            for column, day in enumerate(week):
                in_month = day.month == month
                counts: dict[str, Any] | None = month_data.get(day.isoformat()) if in_month else None
                button = self._make_day_button(day, counts, in_month)
                self.grid_layout.addWidget(button, week_row, column)
                self._day_buttons[day] = button

    def _make_day_button(
        self,
        day: date,
        counts: dict[str, Any] | None,
        in_month: bool,
    ) -> QPushButton:
        if counts is None:
            counts = {
                "task_total": 0,
                "task_done": 0,
                "habit_total": 0,
                "habit_done": 0,
            }

        task_total = counts["task_total"]
        task_done = counts["task_done"]
        habit_total = counts["habit_total"]
        habit_done = counts["habit_done"]

        task_text = f"Tasks {task_done}/{task_total}" if task_total else "No tasks"
        habit_text = f"Habits {habit_done}/{habit_total}" if habit_total else "No habits"
        activity = (task_done > 0) or (habit_done > 0)
        text = f"{day.day}\n{task_text}\n{habit_text}"

        button = QPushButton(text)
        button.setObjectName("calendarDay")
        button.setCursor(Qt.CursorShape.PointingHandCursor if in_month else Qt.CursorShape.ArrowCursor)
        button.setMinimumHeight(76)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        button.setEnabled(in_month)
        button.setProperty("today", day == self.today)
        button.setProperty("selected", day == self.selected_day)
        button.setProperty("outside", not in_month)
        button.setProperty("hasActivity", activity)
        button.setAccessibleName(
            f"{day.strftime('%A, %B')} {day.day}: "
            f"{task_done} of {task_total} tasks completed; "
            f"{habit_done} of {habit_total} habits completed"
        )
        button.setToolTip(
            f"{day.strftime('%A, %d %B %Y')}\n"
            f"Tasks: {task_done}/{task_total} completed\n"
            f"Habits: {habit_done}/{habit_total} completed"
            if in_month
            else day.strftime("%d %B %Y")
        )
        if in_month:
            button.clicked.connect(lambda _checked=False, selected=day: self._open_day(selected))
        return button

    def _open_day(self, selected_day: date) -> None:
        self.selected_day = selected_day
        self.open_day_requested.emit(selected_day)
