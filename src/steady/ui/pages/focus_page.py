from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, QDateTime, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from steady.database import Database
from steady.repositories.focus_repository import FocusRepository
from steady.repositories.planner_repository import PlannerRepository
from steady.repositories.settings_repository import SettingsRepository
from steady.services.alarm_sound import AlarmSound
from .base_page import BasePage


class ReminderDialog(QDialog):
    """Small editor for a one-off or recurring local reminder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add a reminder")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Take a short walk")
        self.title_input.setMaxLength(120)
        self.title_input.setAccessibleName("Reminder title")

        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Optional note")
        self.message_input.setFixedHeight(72)
        self.message_input.setAccessibleName("Reminder note")

        self.due_input = QDateTimeEdit(QDateTime.currentDateTime().addSecs(3600))
        self.due_input.setCalendarPopup(True)
        self.due_input.setDisplayFormat("ddd, d MMM yyyy  ·  h:mm AP")
        self.due_input.setAccessibleName("Reminder date and time")

        self.repeat_combo = QComboBox()
        self.repeat_combo.addItem("Does not repeat", "none")
        self.repeat_combo.addItem("Every day", "daily")
        self.repeat_combo.addItem("Weekdays", "weekdays")
        self.repeat_combo.addItem("Every week", "weekly")
        self.repeat_combo.setAccessibleName("Reminder repeat rule")

        form.addRow("Reminder", self.title_input)
        form.addRow("Note", self.message_input)
        form.addRow("Date and time", self.due_input)
        form.addRow("Repeat", self.repeat_combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.title_input.setFocus()

    def values(self) -> dict[str, Any]:
        return {
            "title": self.title_input.text().strip(),
            "message": self.message_input.toPlainText().strip(),
            "due_at": self.due_input.dateTime().toPython(),
            "repeat_rule": str(self.repeat_combo.currentData()),
        }

    def accept(self) -> None:
        if not self.title_input.text().strip():
            QMessageBox.information(self, "Reminder title needed", "Give this reminder a short name.")
            self.title_input.setFocus()
            return
        super().accept()


class ReminderAlert(QDialog):
    """Non-modal reminder notification with a simple snooze action."""

    snooze_requested = Signal()

    def __init__(self, title: str, message: str, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("Steady reminder")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(330)

        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        body = QLabel(message or "It's time for the reminder you set.")
        body.setWordWrap(True)
        body.setObjectName("muted")
        layout.addWidget(heading)
        layout.addWidget(body)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        snooze = QPushButton("Snooze 10 min")
        dismiss = QPushButton("Dismiss")
        dismiss.setObjectName("primaryButton")
        snooze.clicked.connect(self._snooze)
        dismiss.clicked.connect(self.close)
        buttons.addWidget(snooze)
        buttons.addWidget(dismiss)
        layout.addLayout(buttons)

    def _snooze(self) -> None:
        self.snooze_requested.emit()
        self.close()


class FocusPage(BasePage):
    """Focus/break timer, local reminders and focus-session history."""

    open_daily_plan_requested = Signal()

    DEFAULT_MINUTES = {"focus": 25, "short_break": 5, "long_break": 15}
    MODE_LABELS = {
        "focus": "Focus",
        "short_break": "Short break",
        "long_break": "Long break",
    }

    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(
            "Focus & reminders",
            "Gentle time cues, not noisy interruptions. Choose a useful interval and let the clock hold the time for you.",
            parent,
        )
        self.database = database
        self.repository = FocusRepository(database)
        self.planner_repository = PlannerRepository(database)
        self.settings = SettingsRepository(database)
        self.alarm_sound = AlarmSound(self)

        # Any running row left by a previous crash or forced exit is retained
        # in history as interrupted rather than being silently lost.
        self.repository.recover_open_sessions()

        self.session_id: int | None = None
        self.session_type = "focus"
        self.total_seconds = 25 * 60
        self.elapsed_before_segment = 0.0
        self.segment_started_at: float | None = None
        self.running = False
        self.paused = False
        self._alert_windows: list[ReminderAlert] = []

        self._build_content()

        self.focus_timer = QTimer(self)
        self.focus_timer.setInterval(250)
        self.focus_timer.timeout.connect(self._tick)

        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(10_000)
        self.reminder_timer.timeout.connect(self._check_due_reminders)
        self.reminder_timer.start()

        self.refresh()
        self._check_due_reminders()

    def _card(self, title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        card_layout.addWidget(heading)
        if subtitle:
            hint = QLabel(subtitle)
            hint.setObjectName("muted")
            hint.setWordWrap(True)
            card_layout.addWidget(hint)
        return card, card_layout

    def _build_content(self) -> None:
        scroll = QScrollArea()
        scroll.setObjectName("pageScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner.setObjectName("scrollContent")
        inner.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content = QVBoxLayout(inner)
        content.setContentsMargins(0, 0, 6, 4)
        content.setSpacing(14)

        self.timer_card, timer_layout = self._card(
            "Focus timer",
            "A timer is a helpful cue, not a test. You can pause or stop whenever you need.",
        )
        timer_grid = QGridLayout()
        timer_grid.setHorizontalSpacing(24)
        timer_grid.setVerticalSpacing(12)

        self.clock_label = QLabel("25:00")
        self.clock_label.setObjectName("timerClock")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.clock_label.setMinimumWidth(250)
        self.clock_label.setAccessibleName("Time remaining")
        self.clock_label.setStyleSheet("font-size: 42pt; font-weight: 750; letter-spacing: 2px;")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Focus", "focus")
        self.mode_combo.addItem("Short break", "short_break")
        self.mode_combo.addItem("Long break", "long_break")
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        self.mode_combo.setAccessibleName("Timer session type")

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 180)
        self.duration_spin.setSuffix(" min")
        self.duration_spin.setValue(25)
        self.duration_spin.setToolTip("Choose a duration from 1 to 180 minutes.")
        self.duration_spin.setAccessibleName("Session duration in minutes")
        self.duration_spin.valueChanged.connect(lambda _value: self._update_clock_preview())

        self.task_combo = QComboBox()
        self.task_combo.setMinimumWidth(220)
        self.task_combo.setAccessibleName("Optional linked task")

        self.open_plan_button = QPushButton("Open Daily Plan")
        self.open_plan_button.setObjectName("subtleButton")
        self.open_plan_button.clicked.connect(self.open_daily_plan_requested.emit)
        self.open_plan_button.setAccessibleName("Open Daily Plan")

        self.sound_checkbox = QCheckBox("Play an audible chime for reminders and timer completion")
        self.sound_checkbox.setToolTip(
            "Play Steady's short built-in two-pass chime when a reminder is due or a timer finishes."
        )
        # Audible alerts are enabled on fresh installs. A user's saved mute choice is respected.
        saved_sound = self.settings.get("focus_sound", "1") == "1"
        self.sound_checkbox.setChecked(saved_sound)
        self.sound_checkbox.toggled.connect(self._save_sound_preference)

        self.test_sound_button = QPushButton("Test sound")
        self.test_sound_button.setObjectName("subtleButton")
        self.test_sound_button.setToolTip(
            "Preview the chime. This test plays even when automatic alerts are muted."
        )
        self.test_sound_button.setAccessibleName("Test reminder and timer alarm sound")
        self.test_sound_button.clicked.connect(self.alarm_sound.play)

        controls = QFormLayout()
        controls.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        controls.addRow("Session", self.mode_combo)
        controls.addRow("Duration", self.duration_spin)
        controls.addRow("Link to today's task", self.task_combo)
        controls.addRow("", self.open_plan_button)

        timer_grid.addWidget(self.clock_label, 0, 0, 3, 1)
        timer_grid.addLayout(controls, 0, 1, 1, 1)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self._start_or_resume)
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self._pause)
        self.pause_button.setEnabled(False)
        self.stop_button = QPushButton("Stop & reset")
        self.stop_button.setObjectName("subtleButton")
        self.stop_button.clicked.connect(self._stop)
        self.stop_button.setEnabled(False)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.pause_button)
        button_row.addWidget(self.stop_button)
        timer_grid.addLayout(button_row, 1, 1)
        sound_row = QHBoxLayout()
        sound_row.addWidget(self.sound_checkbox)
        sound_row.addWidget(self.test_sound_button)
        sound_row.addStretch(1)
        timer_grid.addLayout(sound_row, 2, 1)
        timer_layout.addLayout(timer_grid)

        self.timer_progress = QProgressBar()
        self.timer_progress.setRange(0, 1000)
        self.timer_progress.setValue(0)
        self.timer_progress.setTextVisible(False)
        self.timer_progress.setAccessibleName("Timer progress")
        timer_layout.addWidget(self.timer_progress)

        self.timer_status = QLabel("Ready when you are.")
        self.timer_status.setObjectName("muted")
        self.timer_status.setWordWrap(True)
        timer_layout.addWidget(self.timer_status)
        content.addWidget(self.timer_card)

        self.reminder_card, reminder_layout = self._card(
            "Reminders",
            "Schedule a gentle prompt for a specific time. Reminders are checked while Steady is running; operating-system alerts while the app is closed are not enabled yet.",
        )
        reminder_toolbar = QHBoxLayout()
        self.reminder_summary = QLabel("No reminders yet.")
        self.reminder_summary.setObjectName("muted")
        self.add_reminder_button = QPushButton("＋  Add reminder")
        self.add_reminder_button.setObjectName("primaryButton")
        self.add_reminder_button.clicked.connect(self._add_reminder)
        reminder_toolbar.addWidget(self.reminder_summary, 1)
        reminder_toolbar.addWidget(self.add_reminder_button)
        reminder_layout.addLayout(reminder_toolbar)

        self.reminder_table = QTableWidget(0, 5)
        self.reminder_table.setHorizontalHeaderLabels(["Reminder", "When", "Repeat", "Enabled", "Action"])
        self.reminder_table.setAlternatingRowColors(True)
        self.reminder_table.setShowGrid(False)
        self.reminder_table.verticalHeader().setVisible(False)
        self.reminder_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.reminder_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.reminder_table.setMinimumHeight(150)
        header = self.reminder_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        reminder_layout.addWidget(self.reminder_table)
        self.empty_reminders = QLabel("No reminders scheduled. Add one only when a time cue would be useful.")
        self.empty_reminders.setObjectName("muted")
        reminder_layout.addWidget(self.empty_reminders)
        content.addWidget(self.reminder_card)

        self.history_card, history_layout = self._card(
            "Recent focus sessions",
            "A simple record of time spent. Stopped sessions remain visible; they are not treated as failures.",
        )
        self.history_summary = QLabel("No completed focus sessions yet.")
        self.history_summary.setObjectName("muted")
        history_layout.addWidget(self.history_summary)
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Started", "Type", "Duration", "Outcome", "Linked task"])
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setShowGrid(False)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setMinimumHeight(170)
        history_header = self.history_table.horizontalHeader()
        history_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        history_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        history_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        history_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        history_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        history_layout.addWidget(self.history_table)
        content.addWidget(self.history_card)
        content.addStretch(1)

        scroll.setWidget(inner)
        self.layout.addWidget(scroll, 1)

    # Timer controls -----------------------------------------------------
    def _mode_changed(self, _index: int) -> None:
        if self.session_id is not None:
            return
        session_type = str(self.mode_combo.currentData())
        self.duration_spin.setValue(self.DEFAULT_MINUTES[session_type])
        self._update_clock_preview()

    def _update_clock_preview(self) -> None:
        seconds = self.duration_spin.value() * 60
        self.clock_label.setText(self._format_time(seconds))
        self.timer_progress.setValue(0)

    @staticmethod
    def _format_time(seconds: int | float) -> str:
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"

    def _current_elapsed(self) -> float:
        elapsed = self.elapsed_before_segment
        if self.running and self.segment_started_at is not None:
            elapsed += max(0.0, time.monotonic() - self.segment_started_at)
        return min(float(self.total_seconds), elapsed)

    def _start_or_resume(self) -> None:
        if self.session_id is not None and self.paused:
            self._resume()
            return
        if self.session_id is not None:
            return

        self.session_type = str(self.mode_combo.currentData())
        self.total_seconds = self.duration_spin.value() * 60
        linked_task_id = self.task_combo.currentData() if self.session_type == "focus" else None
        try:
            self.session_id = self.repository.start_session(
                planned_seconds=self.total_seconds,
                session_type=self.session_type,
                linked_task_id=int(linked_task_id) if linked_task_id else None,
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not start timer", str(exc))
            return

        self.elapsed_before_segment = 0.0
        self.segment_started_at = time.monotonic()
        self.running = True
        self.paused = False
        self.focus_timer.start()
        self.timer_status.setText(f"{self.MODE_LABELS[self.session_type]} session in progress. One step at a time.")
        self._set_timer_controls(active=True)
        self._tick()

    def _pause(self) -> None:
        if not self.running:
            return
        self.elapsed_before_segment = self._current_elapsed()
        self.segment_started_at = None
        self.running = False
        self.paused = True
        self.focus_timer.stop()
        remaining = self.total_seconds - self.elapsed_before_segment
        self.clock_label.setText(self._format_time(remaining))
        self.timer_status.setText("Paused. Resume whenever you're ready.")
        self.start_button.setText("Resume")
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)

    def _resume(self) -> None:
        if not self.paused or self.session_id is None:
            return
        self.segment_started_at = time.monotonic()
        self.running = True
        self.paused = False
        self.focus_timer.start()
        self.timer_status.setText(f"{self.MODE_LABELS[self.session_type]} session resumed.")
        self._set_timer_controls(active=True)

    def _tick(self) -> None:
        if not self.running:
            return
        elapsed = self._current_elapsed()
        remaining = max(0, self.total_seconds - elapsed)
        self.clock_label.setText(self._format_time(remaining))
        progress = int((elapsed / self.total_seconds) * 1000) if self.total_seconds else 0
        self.timer_progress.setValue(max(0, min(1000, progress)))
        if remaining <= 0:
            self._complete()

    def _complete(self) -> None:
        if self.session_id is None:
            return
        session_id = self.session_id
        session_type = self.session_type
        try:
            self.repository.finish_session(
                session_id,
                outcome="completed",
                actual_seconds=self.total_seconds,
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not save session", str(exc))
        self._clear_active_timer()
        self.clock_label.setText("00:00")
        self.timer_progress.setValue(1000)
        if session_type == "focus":
            message = "Focus interval complete. Take a moment before choosing what comes next."
        else:
            message = "Break complete. Return to your next task when you're ready."
        self.timer_status.setText(message)
        self._play_alarm_if_enabled()
        self._refresh_history()

    def _stop(self) -> None:
        if self.session_id is None:
            self._reset_idle_timer()
            return
        elapsed = int(self._current_elapsed())
        session_id = self.session_id
        try:
            self.repository.finish_session(
                session_id,
                outcome="stopped",
                actual_seconds=elapsed,
                note="Stopped by the user.",
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not save session", str(exc))
        self._clear_active_timer()
        self.total_seconds = self.duration_spin.value() * 60
        self._update_clock_preview()
        self.timer_status.setText(
            f"Session stopped. {self._format_time(elapsed)} saved to your history."
        )
        self._refresh_history()

    def _clear_active_timer(self) -> None:
        self.focus_timer.stop()
        self.session_id = None
        self.running = False
        self.paused = False
        self.segment_started_at = None
        self.elapsed_before_segment = 0.0
        self._set_timer_controls(active=False)

    def _reset_idle_timer(self) -> None:
        self._clear_active_timer()
        self.total_seconds = self.duration_spin.value() * 60
        self._update_clock_preview()
        self.timer_status.setText("Ready when you are.")

    def _set_timer_controls(self, active: bool) -> None:
        self.mode_combo.setEnabled(not active)
        self.duration_spin.setEnabled(not active)
        self.task_combo.setEnabled(not active)
        self.start_button.setEnabled(not active or self.paused)
        self.start_button.setText("Resume" if self.paused else "Start")
        self.pause_button.setEnabled(self.running)
        self.stop_button.setEnabled(active)

    def _save_sound_preference(self, enabled: bool) -> None:
        self.settings.set("focus_sound", "1" if enabled else "0")

    def _play_alarm_if_enabled(self) -> None:
        """Play the bundled chime when automatic audible alerts are enabled."""
        if self.sound_checkbox.isChecked():
            self.alarm_sound.play()

    def _load_task_choices(self) -> None:
        selected = self.task_combo.currentData() if self.task_combo.count() else None
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItem("No task linked", None)
        for task in self.planner_repository.list_tasks(datetime.now().date()):
            if task["status"] in {"todo", "in_progress"}:
                self.task_combo.addItem(task["title"], task["id"])
        if selected is not None:
            index = self.task_combo.findData(selected)
            if index >= 0:
                self.task_combo.setCurrentIndex(index)
        self.task_combo.blockSignals(False)

    # Reminder management -----------------------------------------------
    def _add_reminder(self) -> None:
        dialog = ReminderDialog(self)
        if not dialog.exec():
            return
        try:
            self.repository.create_reminder(**dialog.values())
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not add reminder", str(exc))
            return
        self._refresh_reminders()
        self._check_due_reminders()

    def _refresh_reminders(self) -> None:
        reminders = self.repository.list_reminders()
        self.reminder_table.setRowCount(len(reminders))
        active_count = sum(bool(row["is_enabled"]) for row in reminders)
        self.reminder_summary.setText(
            f"{active_count} active reminder{'s' if active_count != 1 else ''}. You can pause or remove any of them."
            if reminders else "No reminders yet."
        )
        self.empty_reminders.setVisible(not reminders)
        self.reminder_table.setVisible(bool(reminders))

        repeat_labels = {
            "none": "Does not repeat",
            "daily": "Daily",
            "weekdays": "Weekdays",
            "weekly": "Weekly",
        }
        for row_index, reminder in enumerate(reminders):
            title_item = QTableWidgetItem(reminder["title"])
            title_item.setToolTip(reminder["message"] or reminder["title"])
            self.reminder_table.setItem(row_index, 0, title_item)
            self.reminder_table.setItem(
                row_index, 1,
                QTableWidgetItem(self.repository.local_datetime_text(reminder["due_at"])),
            )
            self.reminder_table.setItem(
                row_index, 2,
                QTableWidgetItem(repeat_labels.get(reminder["repeat_rule"], reminder["repeat_rule"])),
            )
            enabled = QCheckBox("On")
            enabled.setChecked(bool(reminder["is_enabled"]))
            enabled.setAccessibleName(f"Enable reminder {reminder['title']}")
            enabled.toggled.connect(
                lambda checked, reminder_id=reminder["id"]: self._toggle_reminder(reminder_id, checked)
            )
            enabled_holder = QWidget()
            enabled_layout = QHBoxLayout(enabled_holder)
            enabled_layout.setContentsMargins(6, 0, 6, 0)
            enabled_layout.addWidget(enabled)
            enabled_layout.addStretch(1)
            self.reminder_table.setCellWidget(row_index, 3, enabled_holder)

            remove = QPushButton("Remove")
            remove.setObjectName("subtleButton")
            remove.setAccessibleName(f"Remove reminder {reminder['title']}")
            remove.clicked.connect(
                lambda _checked=False, reminder_id=reminder["id"]: self._delete_reminder(reminder_id)
            )
            self.reminder_table.setCellWidget(row_index, 4, remove)
        self.reminder_table.resizeRowsToContents()

    def _toggle_reminder(self, reminder_id: int, enabled: bool) -> None:
        self.repository.set_reminder_enabled(reminder_id, enabled)
        self._refresh_reminders()

    def _delete_reminder(self, reminder_id: int) -> None:
        self.repository.delete_reminder(reminder_id)
        self._refresh_reminders()

    def _check_due_reminders(self) -> None:
        try:
            due = self.repository.due_reminders()
        except Exception:
            # A transient database lock should not terminate the GUI timer.
            return
        alerts_created = 0
        for reminder in due:
            fired = self.repository.mark_reminder_fired(reminder["id"])
            if fired is None:
                continue
            alert = ReminderAlert(fired["title"], fired["message"], self)
            alert.snooze_requested.connect(
                lambda reminder_id=fired["id"]: self._snooze_reminder(reminder_id)
            )
            alert.finished.connect(lambda _result, widget=alert: self._forget_alert(widget))
            self._alert_windows.append(alert)
            alert.show()
            alerts_created += 1
        if alerts_created:
            self._play_alarm_if_enabled()
            self._refresh_reminders()

    def _snooze_reminder(self, reminder_id: int) -> None:
        try:
            self.repository.snooze_reminder(reminder_id, 10)
            self._refresh_reminders()
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not snooze reminder", str(exc))

    def _forget_alert(self, alert: ReminderAlert) -> None:
        if alert in self._alert_windows:
            self._alert_windows.remove(alert)

    # History and lifecycle ---------------------------------------------
    def _refresh_history(self) -> None:
        sessions = self.repository.list_sessions(10)
        totals = self.repository.get_focus_totals(7)
        minutes = totals["seconds"] // 60
        self.history_summary.setText(
            f"Last 7 days: {totals['sessions']} completed focus session(s) · {minutes} minutes focused."
        )
        self.history_table.setRowCount(len(sessions))
        type_labels = {"focus": "Focus", "short_break": "Short break", "long_break": "Long break"}
        outcome_labels = {
            "completed": "Completed",
            "stopped": "Stopped early",
            "interrupted": "Interrupted",
            "running": "In progress",
        }
        for row_index, session in enumerate(sessions):
            started = self.repository.local_datetime_text(session["started_at"])
            duration = session["actual_seconds"]
            duration_text = self._format_time(duration) if duration is not None else "Not recorded"
            values = (
                started,
                type_labels.get(session["session_type"], session["session_type"]),
                duration_text,
                outcome_labels.get(session["outcome"], session["outcome"]),
                session["task_title"] or "—",
            )
            for column, value in enumerate(values):
                self.history_table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.history_table.resizeRowsToContents()

    def refresh(self) -> None:
        """Refresh reminders, task choices and recent session history."""
        self._load_task_choices()
        self._refresh_reminders()
        self._refresh_history()

    def shutdown(self) -> None:
        """Stop timers and preserve an active session before application exit."""
        self.focus_timer.stop()
        self.reminder_timer.stop()
        if self.session_id is not None:
            elapsed = int(self._current_elapsed())
            try:
                self.repository.finish_session(
                    self.session_id,
                    outcome="interrupted",
                    actual_seconds=elapsed,
                    note="Application closed while the timer was active.",
                )
            except Exception:
                pass
            self.session_id = None
