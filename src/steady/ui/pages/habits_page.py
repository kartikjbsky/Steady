from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QDate, QTime, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
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
    QProgressBar,
    QTableWidget,
    QScrollArea,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from steady.database import Database
from steady.repositories.habit_repository import HabitRepository
from steady.repositories.planner_repository import PlannerRepository
from .base_page import BasePage


class HabitDialog(QDialog):
    """Create or edit a habit, its weekly schedule and optional local reminder."""

    DAY_LABELS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    CATEGORY_LABELS = (
        ("Study", "study"),
        ("Research", "research"),
        ("Wellbeing", "wellbeing"),
        ("Health", "health"),
        ("Personal", "personal"),
        ("Other", "other"),
    )

    def __init__(self, habit: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.habit = habit
        self.setWindowTitle("Edit habit" if habit else "Create a habit")
        self.setMinimumWidth(490)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.name_input = QLineEdit()
        self.name_input.setMaxLength(100)
        self.name_input.setPlaceholderText("e.g. Practise Qiskit")
        self.name_input.setAccessibleName("Habit name")
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Optional short description")
        self.description_input.setAccessibleName("Habit description")

        self.category_combo = QComboBox()
        for label, value in self.CATEGORY_LABELS:
            self.category_combo.addItem(label, value)
        self.category_combo.setAccessibleName("Habit category")

        self.start_date_input = QDateEdit(QDate.currentDate())
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat("ddd, d MMM yyyy")
        self.start_date_input.setAccessibleName("Habit start date")

        form.addRow("Name", self.name_input)
        form.addRow("Description", self.description_input)
        form.addRow("Category", self.category_combo)
        form.addRow("Start date", self.start_date_input)
        layout.addLayout(form)

        schedule_card = QFrame()
        schedule_card.setObjectName("innerCard")
        schedule_layout = QVBoxLayout(schedule_card)
        schedule_layout.setContentsMargins(12, 10, 12, 10)
        schedule_layout.setSpacing(8)
        schedule_title = QLabel("Scheduled days")
        schedule_title.setStyleSheet("font-weight: 700;")
        schedule_layout.addWidget(schedule_title)
        day_row = QHBoxLayout()
        day_row.setSpacing(6)
        self.day_checks: list[QCheckBox] = []
        for label in self.DAY_LABELS:
            checkbox = QCheckBox(label[:2])
            checkbox.setToolTip(label)
            checkbox.setAccessibleName(f"Schedule on {label}")
            checkbox.setChecked(True)
            self.day_checks.append(checkbox)
            day_row.addWidget(checkbox)
        schedule_layout.addLayout(day_row)
        hint = QLabel("Only selected days appear in your Daily Plan and habit statistics.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        schedule_layout.addWidget(hint)
        layout.addWidget(schedule_card)

        reminder_card = QFrame()
        reminder_card.setObjectName("innerCard")
        reminder_layout = QVBoxLayout(reminder_card)
        reminder_layout.setContentsMargins(12, 10, 12, 10)
        reminder_layout.setSpacing(8)
        self.reminder_checkbox = QCheckBox("Remind me at a specific time")
        self.reminder_checkbox.setAccessibleName("Enable habit reminder")
        self.reminder_time = QTimeEdit(QTime(9, 0))
        self.reminder_time.setDisplayFormat("h:mm AP")
        self.reminder_time.setAccessibleName("Habit reminder time")
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Reminder time"))
        time_row.addStretch(1)
        time_row.addWidget(self.reminder_time)
        reminder_layout.addWidget(self.reminder_checkbox)
        reminder_layout.addLayout(time_row)
        self.reminder_checkbox.toggled.connect(self.reminder_time.setEnabled)
        layout.addWidget(reminder_card)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if habit:
            self._load_habit(habit)
        else:
            self.reminder_time.setEnabled(False)
        self.name_input.setFocus()

    def _load_habit(self, habit: dict[str, Any]) -> None:
        self.name_input.setText(str(habit["name"]))
        self.description_input.setText(str(habit["description"]))
        category_index = self.category_combo.findData(habit["category"])
        if category_index >= 0:
            self.category_combo.setCurrentIndex(category_index)
        start = date.fromisoformat(habit["start_date"])
        self.start_date_input.setDate(QDate(start.year, start.month, start.day))
        for index, checkbox in enumerate(self.day_checks):
            checkbox.setChecked(habit["weekday_mask"][index] == "1")
        enabled = bool(habit["reminder_enabled"])
        self.reminder_checkbox.setChecked(enabled)
        if habit["reminder_time"]:
            hour, minute = map(int, habit["reminder_time"].split(":"))
            self.reminder_time.setTime(QTime(hour, minute))
        self.reminder_time.setEnabled(enabled)

    def values(self) -> dict[str, Any]:
        day_mask = "".join("1" if checkbox.isChecked() else "0" for checkbox in self.day_checks)
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.text().strip(),
            "category": str(self.category_combo.currentData()),
            "weekday_mask": day_mask,
            "start_date": self.start_date_input.date().toPython(),
            "reminder_enabled": self.reminder_checkbox.isChecked(),
            "reminder_time": self.reminder_time.time().toString("HH:mm") if self.reminder_checkbox.isChecked() else None,
        }

    def accept(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.information(self, "Habit name needed", "Give this habit a short name.")
            self.name_input.setFocus()
            return
        if not any(item.isChecked() for item in self.day_checks):
            QMessageBox.information(self, "Choose scheduled days", "Select at least one day of the week.")
            return
        super().accept()


class HabitManagerPage(BasePage):
    """Monthly habit matrix plus tools for managing reusable habits."""

    habits_changed = Signal()

    FILTERS = (("Active", "active"), ("Paused", "paused"), ("Archived", "archived"), ("All", "all"))
    CATEGORY_LABELS = {
        "study": "Study", "research": "Research", "wellbeing": "Wellbeing",
        "health": "Health", "personal": "Personal", "other": "Other",
    }
    DAY_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(
            "Habits",
            "Track each habit across the month. Check a day when you complete it; progress is calculated from scheduled days.",
            parent,
        )
        self.repository = HabitRepository(database)
        self.planner_repository = PlannerRepository(database)
        self.month_start = date.today().replace(day=1)
        self._building_matrix = False
        self._build_content()
        self.refresh()

    def _build_content(self) -> None:
        # The 31-column matrix needs horizontal scrolling, and the management
        # table sits beneath it. A page-level scroll area keeps both usable.
        self.page_scroll = QScrollArea()
        self.page_scroll.setObjectName("pageScrollArea")
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        inner = QWidget()
        inner.setObjectName("scrollContent")
        inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.content_layout = QVBoxLayout(inner)
        self.content_layout.setContentsMargins(2, 2, 10, 8)
        self.content_layout.setSpacing(13)
        self.page_scroll.setWidget(inner)
        self.layout.addWidget(self.page_scroll, 1)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.previous_month_button = QPushButton("‹")
        self.previous_month_button.setFixedWidth(38)
        self.previous_month_button.setAccessibleName("Previous month")
        self.previous_month_button.clicked.connect(lambda: self._move_month(-1))

        self.month_label = QLabel()
        self.month_label.setMinimumWidth(145)
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_label.setStyleSheet("font-size: 14pt; font-weight: 800;")

        self.next_month_button = QPushButton("›")
        self.next_month_button.setFixedWidth(38)
        self.next_month_button.setAccessibleName("Next month")
        self.next_month_button.clicked.connect(lambda: self._move_month(1))

        self.today_button = QPushButton("This month")
        self.today_button.setObjectName("subtleButton")
        self.today_button.clicked.connect(self._go_to_current_month)

        self.filter_combo = QComboBox()
        for label, value in self.FILTERS:
            self.filter_combo.addItem(label, value)
        self.filter_combo.setAccessibleName("Habit list filter")
        self.filter_combo.currentIndexChanged.connect(self.refresh)

        self.add_button = QPushButton("＋  Add habit")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self._add_habit)

        toolbar.addWidget(self.previous_month_button)
        toolbar.addWidget(self.month_label)
        toolbar.addWidget(self.next_month_button)
        toolbar.addWidget(self.today_button)
        toolbar.addSpacing(16)
        toolbar.addWidget(QLabel("Show"))
        toolbar.addWidget(self.filter_combo)
        toolbar.addStretch(1)
        toolbar.addWidget(self.add_button)
        self.content_layout.addLayout(toolbar)

        summary_card = QFrame()
        summary_card.setObjectName("card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        summary_layout.setSpacing(7)
        summary_heading = QLabel("Monthly progress")
        summary_heading.setStyleSheet("font-size: 13pt; font-weight: 800;")
        self.summary_label = QLabel("Loading habit progress…")
        self.summary_label.setObjectName("muted")
        self.summary_label.setWordWrap(True)
        self.month_progress = QProgressBar()
        self.month_progress.setRange(0, 100)
        self.month_progress.setTextVisible(False)
        self.month_progress.setAccessibleName("Monthly habit completion")
        summary_layout.addWidget(summary_heading)
        summary_layout.addWidget(self.summary_label)
        summary_layout.addWidget(self.month_progress)
        self.content_layout.addWidget(summary_card)

        matrix_card = QFrame()
        matrix_card.setObjectName("card")
        matrix_layout = QVBoxLayout(matrix_card)
        matrix_layout.setContentsMargins(14, 12, 14, 12)
        matrix_layout.setSpacing(8)
        matrix_heading = QLabel("Habit tracker")
        matrix_heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        matrix_hint = QLabel(
            "Habits are rows and calendar days are columns. Check a box when you complete a habit. "
            "Past days can be filled in later; future days stay unavailable."
        )
        matrix_hint.setObjectName("muted")
        matrix_hint.setWordWrap(True)
        matrix_layout.addWidget(matrix_heading)
        matrix_layout.addWidget(matrix_hint)

        self.matrix_table = QTableWidget(0, 2)
        self.matrix_table.setAccessibleName("Monthly habit completion matrix")
        self.matrix_table.setAlternatingRowColors(True)
        self.matrix_table.setShowGrid(True)
        self.matrix_table.setWordWrap(False)
        self.matrix_table.verticalHeader().setVisible(False)
        self.matrix_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.matrix_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.matrix_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.matrix_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.matrix_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.matrix_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.matrix_table.setMinimumHeight(210)
        self.matrix_scroll = QScrollArea()
        self.matrix_scroll.setWidgetResizable(False)
        self.matrix_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.matrix_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.matrix_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.matrix_scroll.setMinimumHeight(232)
        self.matrix_scroll.setWidget(self.matrix_table)
        matrix_layout.addWidget(self.matrix_scroll)
        self.content_layout.addWidget(matrix_card)

        manager_card = QFrame()
        manager_card.setObjectName("card")
        manager_layout = QVBoxLayout(manager_card)
        manager_layout.setContentsMargins(14, 12, 14, 12)
        manager_layout.setSpacing(8)
        manager_heading = QLabel("Manage habits")
        manager_heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        self.manager_summary = QLabel("")
        self.manager_summary.setObjectName("muted")
        self.manager_summary.setWordWrap(True)
        manager_layout.addWidget(manager_heading)
        manager_layout.addWidget(self.manager_summary)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Habit", "Category", "Schedule", "Reminder", "State", "Actions"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAccessibleName("Habit management list")
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for index in range(1, 6):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)
        manager_layout.addWidget(self.table)

        self.empty_label = QLabel("No habits in this view. Add a habit or choose another filter.")
        self.empty_label.setObjectName("muted")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMinimumHeight(48)
        manager_layout.addWidget(self.empty_label)
        self.content_layout.addWidget(manager_card)
        self.content_layout.addStretch(1)

    @classmethod
    def _format_schedule(cls, mask: str) -> str:
        selected = [label for label, enabled in zip(cls.DAY_SHORT, mask) if enabled == "1"]
        if len(selected) == 7:
            return "Every day"
        if mask == "1111100":
            return "Weekdays"
        if mask == "0000011":
            return "Weekends"
        return ", ".join(selected)

    def _move_month(self, offset: int) -> None:
        month_index = self.month_start.year * 12 + (self.month_start.month - 1) + offset
        year, month_zero = divmod(month_index, 12)
        self.month_start = date(year, month_zero + 1, 1)
        self.refresh()

    def _go_to_current_month(self) -> None:
        self.month_start = date.today().replace(day=1)
        self.refresh()

    def refresh(self, *_args: Any) -> None:
        state = str(self.filter_combo.currentData())
        habits = self.repository.list_habits(state)
        active = len(self.repository.list_habits("active"))
        paused = len(self.repository.list_habits("paused"))
        archived = len(self.repository.list_habits("archived"))

        self.month_label.setText(self.month_start.strftime("%B %Y"))
        self.manager_summary.setText(
            f"{active} active · {paused} paused · {archived} archived. "
            "Pause or archive a habit without deleting its historical check-ins."
        )

        entries = self.repository.list_month_entries(self.month_start.year, self.month_start.month)
        from steady.services.habit_matrix import compute_month_progress
        progress = compute_month_progress(
            habits, entries, self.month_start.year, self.month_start.month
        )
        self.summary_label.setText(
            f"{progress['done']} of {progress['scheduled']} scheduled check-ins completed "
            f"· {progress['percent']}% for {self.month_start.strftime('%B %Y')}. "
            "Future days are not counted yet; paused habits are excluded."
        )
        self.month_progress.setValue(int(progress["percent"]))

        self._populate_matrix(habits, entries, progress)
        self._populate_management(habits)

    def _populate_matrix(
        self,
        habits: list[dict[str, Any]],
        entries: dict[tuple[int, str], str],
        progress: dict[str, Any],
    ) -> None:
        from calendar import monthrange

        day_count = monthrange(self.month_start.year, self.month_start.month)[1]
        self._building_matrix = True
        self.matrix_table.clear()
        self.matrix_table.setColumnCount(day_count + 2)
        self.matrix_table.setRowCount(len(habits))

        headers = ["Habit"]
        for day_number in range(1, day_count + 1):
            cell_day = date(self.month_start.year, self.month_start.month, day_number)
            headers.append(f"{day_number:02d}\n{self.DAY_SHORT[cell_day.weekday()]}")
        headers.append("Done / planned")
        self.matrix_table.setHorizontalHeaderLabels(headers)

        header = self.matrix_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.matrix_table.setColumnWidth(0, 210)
        for column in range(1, day_count + 1):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.matrix_table.setColumnWidth(column, 50)
        header.setSectionResizeMode(day_count + 1, QHeaderView.ResizeMode.Fixed)
        self.matrix_table.setColumnWidth(day_count + 1, 126)
        header.setMinimumHeight(48)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        today = date.today()
        for row_index, habit in enumerate(habits):
            habit_id = int(habit["id"])
            name_item = QTableWidgetItem(str(habit["name"]))
            name_item.setToolTip(
                f"{habit['name']} · {self.CATEGORY_LABELS.get(habit['category'], 'Other')} · "
                f"{self._format_schedule(habit['weekday_mask'])}"
            )
            self.matrix_table.setItem(row_index, 0, name_item)

            row_progress = progress["habits"].get(
                habit_id, {"scheduled": 0, "done": 0, "percent": 0}
            )
            is_archived = bool(habit["archived_at"])
            is_active = bool(habit["is_active"]) and not is_archived
            is_paused = not is_active and not is_archived
            archived_day = date.fromisoformat(str(habit["archived_at"])[:10]) if is_archived else None
            start_day = date.fromisoformat(str(habit["start_date"]))

            for day_number in range(1, day_count + 1):
                cell_day = date(self.month_start.year, self.month_start.month, day_number)
                day_text = cell_day.isoformat()
                status = entries.get((habit_id, day_text), "pending")
                is_scheduled = (
                    cell_day >= start_day
                    and str(habit["weekday_mask"])[cell_day.weekday()] == "1"
                    and (archived_day is None or cell_day <= archived_day)
                )

                if not is_scheduled:
                    cell = QLabel("·")
                    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setObjectName("muted")
                    if status == "done":
                        cell.setText("✓")
                        cell.setStyleSheet("color: #83B39A; font-weight: 700;")
                        cell.setToolTip("A historical completion is recorded for this date.")
                    self.matrix_table.setCellWidget(row_index, day_number, cell)
                    continue

                check = QCheckBox()
                check.setChecked(status == "done")
                check.setTristate(False)
                check.setCursor(Qt.CursorShape.PointingHandCursor)
                check.setMinimumSize(38, 36)
                check.setAccessibleName(
                    f"{habit['name']} on {cell_day.strftime('%A, %d %B %Y')}"
                )
                check.setToolTip(
                    f"{habit['name']} · {cell_day.strftime('%d %B %Y')}: "
                    f"{'completed' if status == 'done' else 'not completed'}. "
                    "Select the square to toggle this check-in."
                )
                # Active habits can be backfilled through today. Paused and
                # archived habits remain visible but their history is read-only.
                editable = is_active and cell_day <= today
                check.setEnabled(editable)
                check.toggled.connect(
                    lambda checked, hid=habit_id, entry_day=cell_day:
                        self._set_habit_day(hid, entry_day, checked)
                )

                # Center the checkbox in the day cell and give the full
                # control a generous hit target for mouse and touch input.
                check_host = QWidget()
                check_layout = QHBoxLayout(check_host)
                check_layout.setContentsMargins(1, 1, 1, 1)
                check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                check_layout.addWidget(check)
                self.matrix_table.setCellWidget(row_index, day_number, check_host)

            completion = QTableWidgetItem(
                f"{row_progress['done']} / {row_progress['scheduled']} "
                f"({row_progress['percent']}%)"
                if row_progress["scheduled"]
                else ("Paused" if is_paused else "—")
            )
            completion.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_active:
                completion.setToolTip("Completed scheduled days / scheduled days elapsed so far.")
            elif is_archived:
                completion.setToolTip("Historical progress up to the archive date.")
            else:
                completion.setToolTip("Paused habits are excluded from progress totals.")
            self.matrix_table.setItem(row_index, day_count + 1, completion)

        # Give every row a predictable height so checkbox hit targets are not
        # clipped by Qt's size-hint calculation. The page scrolls vertically;
        # this inner area scrolls horizontally only.
        header_height = max(52, self.matrix_table.horizontalHeader().sizeHint().height())
        self.matrix_table.horizontalHeader().setFixedHeight(header_height)
        row_height = 50
        for row_index in range(len(habits)):
            self.matrix_table.setRowHeight(row_index, row_height)

        table_width = 210 + day_count * 50 + 126
        self.matrix_table.setFixedWidth(table_width)
        table_height = (
            self.matrix_table.horizontalHeader().height()
            + sum(self.matrix_table.rowHeight(i) for i in range(len(habits)))
            + 2 * self.matrix_table.frameWidth()
            + 4
        )
        self.matrix_table.setFixedHeight(table_height)

        # The scroll-area viewport must contain the complete table plus its
        # horizontal scrollbar; otherwise the last habit row is visibly cut.
        horizontal_bar_height = self.matrix_scroll.horizontalScrollBar().sizeHint().height()
        self.matrix_scroll.setFixedHeight(table_height + horizontal_bar_height + 6)
        self._building_matrix = False

    def _populate_management(self, habits: list[dict[str, Any]]) -> None:
        self.table.setRowCount(len(habits))
        self.table.setVisible(bool(habits))
        self.empty_label.setVisible(not habits)

        for row_index, habit in enumerate(habits):
            self.table.setItem(row_index, 0, QTableWidgetItem(str(habit["name"])))
            self.table.setItem(
                row_index, 1,
                QTableWidgetItem(self.CATEGORY_LABELS.get(habit["category"], "Other")),
            )
            self.table.setItem(
                row_index, 2,
                QTableWidgetItem(self._format_schedule(habit["weekday_mask"])),
            )
            reminder = habit["reminder_time"] if habit["reminder_enabled"] else "Off"
            self.table.setItem(row_index, 3, QTableWidgetItem(reminder or "Off"))
            if habit["archived_at"]:
                state_text = "Archived"
            else:
                state_text = "Active" if habit["is_active"] else "Paused"
            self.table.setItem(row_index, 4, QTableWidgetItem(state_text))

            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(3, 2, 3, 2)
            action_layout.setSpacing(5)
            edit = QPushButton("Edit")
            edit.setObjectName("subtleButton")
            edit.setAccessibleName(f"Edit habit {habit['name']}")
            edit.clicked.connect(lambda _checked=False, item=habit: self._edit_habit(item))
            action_layout.addWidget(edit)

            if habit["archived_at"]:
                state_button = QPushButton("Restore")
                state_button.setObjectName("primaryButton")
                state_button.clicked.connect(
                    lambda _checked=False, habit_id=habit["id"]: self._restore_habit(habit_id)
                )
                delete_button = QPushButton("Delete permanently")
                delete_button.setObjectName("dangerButton")
                delete_button.setToolTip(
                    "Permanently delete this archived habit and all of its check-in history."
                )
                delete_button.setAccessibleName(
                    f"Delete archived habit {habit['name']} permanently"
                )
                delete_button.clicked.connect(
                    lambda _checked=False, habit_id=habit["id"], name=habit["name"]:
                        self._delete_archived_habit(habit_id, name)
                )
                action_layout.addWidget(delete_button)
            else:
                state_button = QPushButton("Pause" if habit["is_active"] else "Resume")
                state_button.setObjectName("subtleButton")
                state_button.clicked.connect(
                    lambda _checked=False, habit_id=habit["id"], enabled=not bool(habit["is_active"]):
                        self._set_active(habit_id, enabled)
                )
                archive = QPushButton("Archive")
                archive.setObjectName("subtleButton")
                archive.clicked.connect(
                    lambda _checked=False, habit_id=habit["id"]: self._archive_habit(habit_id)
                )
                action_layout.addWidget(archive)
            action_layout.addWidget(state_button)
            self.table.setCellWidget(row_index, 5, actions)
        self.table.resizeRowsToContents()

    def _set_habit_day(self, habit_id: int, selected_day: date, checked: bool) -> None:
        try:
            self.planner_repository.set_habit_status(
                habit_id, selected_day, "done" if checked else "pending"
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update habit check-in", str(exc))
            self.refresh()
            return
        self._changed()

    def _add_habit(self) -> None:
        dialog = HabitDialog(parent=self)
        if not dialog.exec():
            return
        try:
            self.repository.create_habit(**dialog.values())
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not create habit", str(exc))
            return
        self._changed()

    def _edit_habit(self, habit: dict[str, Any]) -> None:
        dialog = HabitDialog(habit=habit, parent=self)
        if not dialog.exec():
            return
        try:
            self.repository.update_habit(int(habit["id"]), **dialog.values())
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update habit", str(exc))
            return
        self._changed()

    def _set_active(self, habit_id: int, active: bool) -> None:
        try:
            self.repository.set_active(habit_id, active)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update habit", str(exc))
            return
        self._changed()

    def _archive_habit(self, habit_id: int) -> None:
        answer = QMessageBox.question(
            self, "Archive habit?",
            "Hide this habit from future daily plans? Its historical check-ins will be kept.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.repository.archive(habit_id)
        self._changed()

    def _restore_habit(self, habit_id: int) -> None:
        self.repository.restore(habit_id)
        self._changed()

    def _delete_archived_habit(self, habit_id: int, name: str) -> None:
        # QMessageBox.StandardButton has no Delete enum in Qt 6. Use an
        # explicitly labelled custom button with the destructive role.
        confirmation = QMessageBox(self)
        confirmation.setIcon(QMessageBox.Icon.Warning)
        confirmation.setWindowTitle("Delete archived habit permanently?")
        confirmation.setText(
            f"Delete “{name}” permanently? This also deletes every saved daily check-in "
            "for this habit. This action cannot be undone. Consider making a backup first."
        )
        delete_button = confirmation.addButton(
            "Delete permanently", QMessageBox.ButtonRole.DestructiveRole
        )
        cancel_button = confirmation.addButton(QMessageBox.StandardButton.Cancel)
        confirmation.setDefaultButton(cancel_button)
        confirmation.exec()
        if confirmation.clickedButton() is not delete_button:
            return
        try:
            self.repository.delete_archived(habit_id)
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not delete habit", str(exc))
            return
        self._changed()

    def _changed(self) -> None:
        self.refresh()
        self.habits_changed.emit()
