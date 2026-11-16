from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from steady.database import Database
from steady.repositories.focus_repository import FocusRepository
from steady.repositories.planner_repository import PlannerRepository
from steady.repositories.todo_repository import TodoRepository
from .base_page import BasePage


class DashboardPage(BasePage):
    """A calm, actionable overview of today and the next few days."""

    open_day_requested = Signal(object)
    open_focus_requested = Signal()
    open_habits_requested = Signal()
    open_todo_requested = Signal()

    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(
            "Welcome back.",
            "A gentle starting point for today. You do not need to plan everything at once.",
            parent,
        )
        self.planner = PlannerRepository(database)
        self.focus = FocusRepository(database)
        self.todos = TodoRepository(database)

        self.today_card = self._make_card("Today's overview")
        today_layout = self.today_card.layout()
        self.progress_label = QLabel("Loading today's progress…")
        self.progress_label.setObjectName("muted")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setAccessibleName("Today's task completion")
        action_row = QHBoxLayout()
        open_plan = QPushButton("Open today's plan")
        open_plan.setObjectName("primaryButton")
        open_plan.clicked.connect(lambda: self.open_day_requested.emit(date.today()))
        focus_button = QPushButton("Open focus timer")
        focus_button.setObjectName("subtleButton")
        focus_button.clicked.connect(self.open_focus_requested.emit)
        action_row.addWidget(open_plan)
        action_row.addWidget(focus_button)
        action_row.addStretch(1)
        today_layout.addWidget(self.progress_label)
        today_layout.addWidget(self.progress)
        today_layout.addLayout(action_row)
        self.layout.addWidget(self.today_card)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        self.tasks_card = self._make_card("Next tasks")
        self.habits_card = self._make_card("Today's habits")
        self.reminders_card = self._make_card("Upcoming reminders")
        self.focus_card = self._make_card("Focus this week")
        grid.addWidget(self.tasks_card, 0, 0)
        grid.addWidget(self.habits_card, 0, 1)
        grid.addWidget(self.reminders_card, 1, 0)
        grid.addWidget(self.focus_card, 1, 1)
        self.layout.addLayout(grid)

        self.todo_card = self._make_card("To-do deadlines")
        self.layout.addWidget(self.todo_card)

        self.note = QLabel("A small reminder: if the plan changes, you can adjust it. Progress is not a test.")
        self.note.setObjectName("muted")
        self.note.setWordWrap(True)
        self.layout.addWidget(self.note)
        self.layout.addStretch(1)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(60_000)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start()
        self.refresh()

    @staticmethod
    def _make_card(title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        layout.addWidget(heading)
        return card

    @staticmethod
    def _clear_content(layout: QVBoxLayout) -> None:
        while layout.count() > 1:
            item = layout.takeAt(1)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                child = item.layout()
                while child.count():
                    sub = child.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def _add_empty(self, layout: QVBoxLayout, message: str) -> None:
        label = QLabel(message)
        label.setObjectName("muted")
        label.setWordWrap(True)
        layout.addWidget(label)

    def refresh(self) -> None:
        today = date.today()
        tasks = self.planner.list_tasks(today)
        active_tasks = [task for task in tasks if task["status"] != "cancelled"]
        done = sum(task["status"] == "done" for task in active_tasks)
        total = len(active_tasks)
        percent = round(done * 100 / total) if total else 0
        self.progress.setValue(percent)
        self.progress_label.setText(
            f"{done} of {total} tasks completed · {percent}%" if total
            else "No tasks planned for today yet. Start with one small next step."
        )

        tasks_layout = self.tasks_card.layout()
        self._clear_content(tasks_layout)
        upcoming = self.planner.list_upcoming_tasks(limit=6)
        if not upcoming:
            self._add_empty(tasks_layout, "No open tasks coming up. You can add one from Daily Plan.")
        for task in upcoming:
            day = date.fromisoformat(task["scheduled_date"])
            when = "Today" if day == today else day.strftime("%a, %d %b")
            row = QHBoxLayout()
            text = QLabel(f"{task['title']}\n{when} · {task['status'].replace('_', ' ').title()}")
            text.setWordWrap(True)
            text.setStyleSheet("font-weight: 600;")
            open_button = QPushButton("Open")
            open_button.setObjectName("subtleButton")
            open_button.setToolTip(f"Open plan for {day.isoformat()}")
            open_button.clicked.connect(lambda _checked=False, selected=day: self.open_day_requested.emit(selected))
            row.addWidget(text, 1)
            row.addWidget(open_button)
            tasks_layout.addLayout(row)

        habits_layout = self.habits_card.layout()
        self._clear_content(habits_layout)
        habits = self.planner.list_habits(today)
        completed_habits = sum(habit["status"] == "done" for habit in habits)
        if habits:
            summary = QLabel(f"{completed_habits} of {len(habits)} check-ins completed")
            summary.setObjectName("muted")
            habits_layout.addWidget(summary)
            for habit in habits[:6]:
                label = QLabel(("✓  " if habit["status"] == "done" else "○  ") + habit["name"])
                label.setWordWrap(True)
                habits_layout.addWidget(label)
        else:
            self._add_empty(habits_layout, "No habits scheduled for today.")
        manage = QPushButton("Manage habits")
        manage.setObjectName("subtleButton")
        manage.clicked.connect(self.open_habits_requested.emit)
        habits_layout.addWidget(manage, alignment=Qt.AlignmentFlag.AlignLeft)

        todo_layout = self.todo_card.layout()
        self._clear_content(todo_layout)
        todo_items = self.todos.list_items(include_completed=False)[:3]
        if todo_items:
            for item in todo_items:
                due = date.fromisoformat(item["deadline_date"])
                due_label = "Overdue" if due < today else due.strftime("%d %b")
                row = QHBoxLayout()
                label = QLabel(f"{item['title']}  ·  {due_label}")
                label.setToolTip(f"Deadline: {item['deadline_date']}")
                label.setStyleSheet("font-weight: 600;")
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                row.addWidget(label, 1)
                todo_layout.addLayout(row)
        else:
            self._add_empty(todo_layout, "No open to-do deadlines. Add one from the checklist.")
        open_todos = QPushButton("Open to-do checklist")
        open_todos.setObjectName("subtleButton")
        open_todos.clicked.connect(self.open_todo_requested.emit)
        todo_layout.addWidget(open_todos, alignment=Qt.AlignmentFlag.AlignLeft)

        reminders_layout = self.reminders_card.layout()
        self._clear_content(reminders_layout)
        reminders = self.focus.list_reminders(include_disabled=False)
        now = datetime.now().astimezone()
        upcoming_reminders = []
        for reminder in reminders:
            try:
                due = datetime.fromisoformat(reminder["due_at"].replace("Z", "+00:00")).astimezone()
            except (ValueError, TypeError):
                continue
            if due >= now:
                upcoming_reminders.append((due, reminder))
        if upcoming_reminders:
            for due, reminder in sorted(upcoming_reminders)[:5]:
                label = QLabel(f"{reminder['title']}\n{due.strftime('%a, %d %b · %I:%M %p')}")
                label.setWordWrap(True)
                reminders_layout.addWidget(label)
        else:
            self._add_empty(reminders_layout, "No upcoming reminders. Add one in Focus & reminders.")

        focus_layout = self.focus_card.layout()
        self._clear_content(focus_layout)
        totals = self.focus.get_focus_totals(7)
        seconds = totals["seconds"]
        minutes = seconds // 60
        hours, remaining_minutes = divmod(minutes, 60)
        duration = f"{hours}h {remaining_minutes}m" if hours else f"{remaining_minutes} min"
        metric = QLabel(duration)
        metric.setStyleSheet("font-size: 23pt; font-weight: 700;")
        detail = QLabel(f"{totals['sessions']} completed focus sessions in the last 7 days")
        detail.setObjectName("muted")
        detail.setWordWrap(True)
        focus_layout.addWidget(metric)
        focus_layout.addWidget(detail)
        open_focus = QPushButton("View focus history")
        open_focus.setObjectName("subtleButton")
        open_focus.clicked.connect(self.open_focus_requested.emit)
        focus_layout.addWidget(open_focus, alignment=Qt.AlignmentFlag.AlignLeft)
