from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from PySide6.QtCore import Qt, QDate, QTime, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from steady.database import Database
from steady.repositories.settings_repository import SettingsRepository
from steady.repositories.todo_repository import TodoRepository
from steady.services.alarm_sound import AlarmSound
from .base_page import BasePage


class TodoDialog(QDialog):
    """Editor for one workspace to-do item and its deadline alert."""

    def __init__(self, item: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Edit to-do" if item else "Add a to-do")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.title_input = QLineEdit(item["title"] if item else "")
        self.title_input.setPlaceholderText("e.g. Submit book")
        self.title_input.setMaxLength(120)
        self.title_input.setAccessibleName("To-do task")

        self.deadline_input = QDateEdit()
        self.deadline_input.setCalendarPopup(True)
        self.deadline_input.setDisplayFormat("ddd, d MMM yyyy")
        initial_date = date.fromisoformat(item["deadline_date"]) if item else date.today()
        self.deadline_input.setDate(QDate(initial_date.year, initial_date.month, initial_date.day))
        self.deadline_input.setAccessibleName("To-do deadline")

        self.notify_input = QCheckBox("Notify me on the deadline")
        self.notify_input.setChecked(bool(item["notification_enabled"]) if item else True)
        self.notify_input.setAccessibleName("Enable deadline notification")

        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("h:mm AP")
        notify_time = time.fromisoformat(item["notification_time"]) if item else time(9, 0)
        self.time_input.setTime(QTime(notify_time.hour, notify_time.minute))
        self.time_input.setAccessibleName("Deadline notification time")
        self.time_input.setEnabled(self.notify_input.isChecked())
        self.notify_input.toggled.connect(self.time_input.setEnabled)

        form.addRow("Task", self.title_input)
        form.addRow("Deadline", self.deadline_input)
        form.addRow("Notification", self.notify_input)
        form.addRow("Alert time", self.time_input)
        layout.addLayout(form)

        hint = QLabel("Notifications are shown while Steady is running. The default alert time is 9:00 AM.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.title_input.setFocus()

    def values(self) -> dict[str, Any]:
        selected_date = self.deadline_input.date()
        selected_time = self.time_input.time()
        return {
            "title": self.title_input.text().strip(),
            "deadline_date": date(selected_date.year(), selected_date.month(), selected_date.day()),
            "notification_enabled": self.notify_input.isChecked(),
            "notification_time": time(selected_time.hour(), selected_time.minute()),
        }

    def accept(self) -> None:
        if not self.title_input.text().strip():
            QMessageBox.information(self, "Task needed", "Give this to-do item a short name.")
            self.title_input.setFocus()
            return
        super().accept()


class TodoAlert(QDialog):
    """Non-modal alert summarising one or more due checklist items."""

    def __init__(self, items: list[dict[str, Any]], parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Tool)
        self.setWindowTitle("Steady deadline reminder")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        heading = QLabel("A to-do deadline has arrived" if len(items) == 1 else f"{len(items)} to-do deadlines have arrived")
        heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        layout.addWidget(heading)

        lines = []
        for item in items[:8]:
            due = date.fromisoformat(item["deadline_date"]).strftime("%d %b %Y")
            lines.append(f"• {item['title']} — {due}")
        if len(items) > 8:
            lines.append(f"…and {len(items) - 8} more")
        body = QLabel("\n".join(lines))
        body.setWordWrap(True)
        body.setObjectName("muted")
        layout.addWidget(body)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        dismiss = QPushButton("Dismiss")
        dismiss.setObjectName("primaryButton")
        dismiss.clicked.connect(self.close)
        buttons.addWidget(dismiss)
        layout.addLayout(buttons)


class TodoPage(BasePage):
    """Single-line workspace checklist with optional deadline notifications."""

    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(
            "To-do checklist",
            "Keep important one-off tasks and deadlines together. Check them off when they are done.",
            parent,
        )
        self.repository = TodoRepository(database)
        self.settings = SettingsRepository(database)
        self.alarm_sound = AlarmSound(self)
        self._alerts: list[TodoAlert] = []

        toolbar = QHBoxLayout()
        self.summary = QLabel("Your open to-do items")
        self.summary.setObjectName("muted")
        toolbar.addWidget(self.summary)
        toolbar.addStretch(1)
        add_button = QPushButton("＋ Add task")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._add_item)
        toolbar.addWidget(add_button)
        self.layout.addLayout(toolbar)

        self.empty_label = QLabel("Your checklist is empty. Add a task with a deadline to get started.")
        self.empty_label.setObjectName("muted")
        self.empty_label.setWordWrap(True)
        self.layout.addWidget(self.empty_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Task", "Deadline", "Done", "Notification", "Actions"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3, 4):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(150)
        self.table.setMaximumHeight(520)
        self.table.setAccessibleName("To-do checklist")
        self.layout.addWidget(self.table)

        note = QLabel("Alerts are delivered while Steady is open. If a deadline passes while the app is closed, its alert appears the next time Steady runs.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        self.layout.addWidget(note)
        self.layout.addStretch(1)

        self.notification_timer = QTimer(self)
        self.notification_timer.setInterval(30_000)
        self.notification_timer.timeout.connect(self._check_due_notifications)
        self.notification_timer.start()
        # Defer the startup check until MainWindow has adopted this page so
        # deadline alerts are parented to the visible application window.
        QTimer.singleShot(1_000, self._check_due_notifications)

        self.refresh()

    def refresh(self) -> None:
        items = self.repository.list_items()
        open_count = sum(not item["is_completed"] for item in items)
        completed_count = len(items) - open_count
        self.summary.setText(
            f"{open_count} open · {completed_count} completed · {len(items)} total"
            if items else "No to-do items yet. Add one important thing to remember."
        )
        self.empty_label.setVisible(not items)
        self.table.setVisible(bool(items))
        self.table.setRowCount(len(items))
        today = date.today()

        for row, item in enumerate(items):
            title_cell = QTableWidgetItem(item["title"])
            title_cell.setToolTip(item["title"])
            title_cell.setData(Qt.ItemDataRole.UserRole, item["id"])
            self.table.setItem(row, 0, title_cell)

            deadline_value = date.fromisoformat(item["deadline_date"])
            deadline_text = deadline_value.strftime("%d %b %Y")
            if not item["is_completed"] and deadline_value < today:
                deadline_text = f"Overdue · {deadline_text}"
            deadline_cell = QTableWidgetItem(deadline_text)
            deadline_cell.setToolTip(f"Deadline: {item['deadline_date']}")
            self.table.setItem(row, 1, deadline_cell)

            done_box = QCheckBox("Done")
            done_box.setChecked(bool(item["is_completed"]))
            done_box.setAccessibleName(f"Mark {item['title']} completed")
            done_box.toggled.connect(
                lambda checked, item_id=item["id"]: self._set_completed(item_id, checked)
            )
            self._put_widget(row, 2, done_box)

            notify_holder = QWidget()
            notify_layout = QHBoxLayout(notify_holder)
            notify_layout.setContentsMargins(5, 0, 5, 0)
            notify_layout.setSpacing(5)
            notify_box = QCheckBox("Yes")
            notify_box.setChecked(bool(item["notification_enabled"]))
            notify_box.setText("Yes" if item["notification_enabled"] else "No")
            notify_box.setAccessibleName(f"Notify for {item['title']}")
            notify_time = QTimeEdit()
            notify_time.setDisplayFormat("h:mm AP")
            parsed_time = time.fromisoformat(item["notification_time"])
            notify_time.setTime(QTime(parsed_time.hour, parsed_time.minute))
            notify_time.setFixedWidth(92)
            notify_time.setEnabled(bool(item["notification_enabled"]))
            notify_box.toggled.connect(
                lambda enabled, box=notify_box, editor=notify_time, item_id=item["id"]:
                    self._toggle_notification(item_id, enabled, box, editor)
            )
            notify_time.editingFinished.connect(
                lambda editor=notify_time, item_id=item["id"]: self._save_notification_time(item_id, editor)
            )
            notify_layout.addWidget(notify_box)
            notify_layout.addWidget(notify_time)
            self.table.setCellWidget(row, 3, notify_holder)

            actions_holder = QWidget()
            actions_layout = QHBoxLayout(actions_holder)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(4)
            edit_button = QPushButton("Edit")
            edit_button.setObjectName("subtleButton")
            edit_button.clicked.connect(lambda _checked=False, data=item: self._edit_item(data))
            remove_button = QPushButton("Remove")
            remove_button.setObjectName("subtleButton")
            remove_button.clicked.connect(
                lambda _checked=False, item_id=item["id"]: self._delete_item(item_id)
            )
            actions_layout.addWidget(edit_button)
            actions_layout.addWidget(remove_button)
            self.table.setCellWidget(row, 4, actions_holder)
            self.table.setRowHeight(row, 44)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

    def _put_widget(self, row: int, column: int, widget: QWidget) -> None:
        holder = QWidget()
        layout = QHBoxLayout(holder)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.addWidget(widget)
        layout.addStretch(1)
        self.table.setCellWidget(row, column, holder)

    def _add_item(self) -> None:
        dialog = TodoDialog(parent=self)
        if not dialog.exec():
            return
        try:
            self.repository.create(**dialog.values())
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not add to-do", str(exc))
            return
        self.refresh()
        self._check_due_notifications()

    def _edit_item(self, item: dict[str, Any]) -> None:
        dialog = TodoDialog(item, self)
        if not dialog.exec():
            return
        try:
            self.repository.update(item["id"], **dialog.values())
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update to-do", str(exc))
            return
        self.refresh()
        self._check_due_notifications()

    def _set_completed(self, item_id: int, completed: bool) -> None:
        try:
            self.repository.set_completed(item_id, completed)
            self.refresh()
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update to-do", str(exc))

    def _toggle_notification(
        self, item_id: int, enabled: bool, checkbox: QCheckBox, time_editor: QTimeEdit
    ) -> None:
        checkbox.setText("Yes" if enabled else "No")
        time_editor.setEnabled(enabled)
        try:
            self.repository.set_notification_enabled(item_id, enabled)
            self.refresh()
            if enabled:
                self._check_due_notifications()
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update notification", str(exc))

    def _save_notification_time(self, item_id: int, editor: QTimeEdit) -> None:
        selected = editor.time()
        try:
            self.repository.update(item_id, notification_time=time(selected.hour(), selected.minute()))
            self.refresh()
            self._check_due_notifications()
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update notification time", str(exc))

    def _delete_item(self, item_id: int) -> None:
        answer = QMessageBox.question(
            self,
            "Remove to-do",
            "Remove this item from your checklist?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.repository.delete(item_id)
        self.refresh()

    def _check_due_notifications(self) -> None:
        try:
            due_items = self.repository.due_notifications()
            newly_due = [item for item in due_items if self.repository.mark_notified(item["id"])]
        except Exception:
            return
        if not newly_due:
            return

        if self.settings.get("focus_sound", "1") == "1":
            self.alarm_sound.play()
        alert = TodoAlert(newly_due, self.window())
        alert.finished.connect(lambda _result, widget=alert: self._forget_alert(widget))
        self._alerts.append(alert)
        alert.show()

    def _forget_alert(self, alert: TodoAlert) -> None:
        if alert in self._alerts:
            self._alerts.remove(alert)
