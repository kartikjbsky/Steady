from __future__ import annotations

from datetime import date

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from steady.database import Database
from steady.repositories.analytics_repository import AnalyticsRepository
from steady.repositories.settings_repository import SettingsRepository
from .base_page import BasePage


class AnalyticsPage(BasePage):
    """A calm, read-only overview of recent tasks, habits and focus time."""

    PERIODS = (("Last 7 days", 7), ("Last 30 days", 30), ("Last 90 days", 90))

    def __init__(self, database: Database, parent: QWidget | None = None) -> None:
        super().__init__(
            "Progress",
            "Notice what is working. These summaries are information, not grades.",
            parent,
        )
        self.database = database
        self.repository = AnalyticsRepository(database)
        self.settings = SettingsRepository(database)
        self._build_content()
        self.refresh()

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

        toolbar = QHBoxLayout()
        period_label = QLabel("Review period")
        period_label.setObjectName("muted")
        self.period_combo = QComboBox()
        for label, days in self.PERIODS:
            self.period_combo.addItem(label, days)
        self.period_combo.setAccessibleName("Analytics reporting period")
        self.period_combo.currentIndexChanged.connect(self.refresh)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("subtleButton")
        self.refresh_button.clicked.connect(self.refresh)
        toolbar.addWidget(period_label)
        toolbar.addWidget(self.period_combo)
        toolbar.addStretch(1)
        toolbar.addWidget(self.refresh_button)
        content.addLayout(toolbar)

        self.metric_grid = QGridLayout()
        self.metric_grid.setHorizontalSpacing(12)
        self.metric_grid.setVerticalSpacing(12)
        self.metric_values: dict[str, QLabel] = {}
        self.metric_notes: dict[str, QLabel] = {}
        for index, (key, title) in enumerate((
            ("tasks", "Tasks completed"),
            ("habits", "Habit check-ins"),
            ("focus", "Focus time"),
        )):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 15, 18, 15)
            card_layout.setSpacing(5)
            heading = QLabel(title)
            heading.setObjectName("muted")
            value = QLabel("—")
            value.setStyleSheet("font-size: 21pt; font-weight: 750;")
            note = QLabel("Loading period summary")
            note.setObjectName("muted")
            note.setWordWrap(True)
            card_layout.addWidget(heading)
            card_layout.addWidget(value)
            card_layout.addWidget(note)
            self.metric_values[key] = value
            self.metric_notes[key] = note
            self.metric_grid.addWidget(card, 0, index)
        content.addLayout(self.metric_grid)

        chart_card = QFrame()
        chart_card.setObjectName("card")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(12, 12, 12, 12)
        chart_layout.setSpacing(8)
        chart_heading = QLabel("Your recent patterns")
        chart_heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        chart_hint = QLabel("Daily activity is shown without streak penalties or negative scoring.")
        chart_hint.setObjectName("muted")
        chart_hint.setWordWrap(True)
        chart_layout.addWidget(chart_heading)
        chart_layout.addWidget(chart_hint)

        self.figure = Figure(figsize=(11, 7), dpi=95)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(590)
        self.canvas.setAccessibleName("Progress charts for tasks, habits and focus time")
        chart_layout.addWidget(self.canvas)
        content.addWidget(chart_card)

        reasons_card = QFrame()
        reasons_card.setObjectName("card")
        reasons_layout = QVBoxLayout(reasons_card)
        reasons_layout.setContentsMargins(18, 15, 18, 15)
        reasons_layout.setSpacing(8)
        reasons_heading = QLabel("Missed-activity reflections")
        reasons_heading.setStyleSheet("font-size: 14pt; font-weight: 800;")
        reasons_hint = QLabel(
            "Optional reasons can reveal practical patterns. No reason is treated as a failure."
        )
        reasons_hint.setObjectName("muted")
        reasons_hint.setWordWrap(True)
        reasons_layout.addWidget(reasons_heading)
        reasons_layout.addWidget(reasons_hint)
        self.reasons_table = QTableWidget(0, 2)
        self.reasons_table.setHorizontalHeaderLabels(["Reason recorded", "Times noted"])
        self.reasons_table.setAlternatingRowColors(True)
        self.reasons_table.setShowGrid(False)
        self.reasons_table.verticalHeader().setVisible(False)
        self.reasons_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.reasons_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.reasons_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.reasons_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.reasons_table.setMaximumHeight(190)
        reasons_layout.addWidget(self.reasons_table)
        self.reasons_empty = QLabel("No reasons recorded in this period. Reflection is always optional.")
        self.reasons_empty.setObjectName("muted")
        reasons_layout.addWidget(self.reasons_empty)
        content.addWidget(reasons_card)
        content.addStretch(1)

        scroll.setWidget(inner)
        self.layout.addWidget(scroll, 1)

    def refresh(self, *_args) -> None:
        days = int(self.period_combo.currentData())
        summary = self.repository.get_period_summary(days)
        self._update_metrics(summary, days)
        self._draw_charts(summary)
        self._update_reasons(days)

    def _update_metrics(self, summary: dict, days: int) -> None:
        self.metric_values["tasks"].setText(
            f"{summary['task_done']} / {summary['task_total']}"
        )
        self.metric_notes["tasks"].setText(
            f"{summary['task_percent']}% completed · {days}-day view"
            if summary["task_total"] else "No tasks scheduled in this period"
        )
        self.metric_values["habits"].setText(
            f"{summary['habit_done']} / {summary['habit_total']}"
        )
        self.metric_notes["habits"].setText(
            f"{summary['habit_percent']}% checked off · {days}-day view"
            if summary["habit_total"] else "No active habits scheduled in this period"
        )
        seconds = int(summary["focus_seconds"])
        hours, remainder = divmod(seconds, 3600)
        minutes = remainder // 60
        self.metric_values["focus"].setText(
            f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"
        )
        self.metric_notes["focus"].setText(
            f"{summary['focus_sessions']} focus session(s) with recorded time"
            if summary["focus_sessions"] else "No focus time recorded in this period"
        )

    def _draw_charts(self, summary: dict) -> None:
        dark = (self.settings.get("theme", "light") or "light") == "dark"
        if dark:
            bg, fg, muted = "#0D141B", "#F2F0DF", "#B8BDB9"
            grid, blue, green, copper, pale = (
                "#2B3741", "#A8C6D8", "#B6C7A9", "#D9CCA0", "#3D4A54"
            )
        else:
            bg, fg, muted = "#E6DBC4", "#38291F", "#6E5B48"
            grid, blue, green, copper, pale = (
                "#CDBE9F", "#718FA2", "#89936D", "#A84D47", "#D2C3A5"
            )

        self.figure.clear()
        self.figure.patch.set_facecolor(bg)
        axes = self.figure.subplots(2, 2)
        dates = [date.fromisoformat(str(row["date"])) for row in summary["days"]]
        labels = [day.strftime("%a %d") for day in dates]
        x = list(range(len(dates)))
        task_done = [int(row["task_done"]) for row in summary["days"]]
        task_total = [int(row["task_total"]) for row in summary["days"]]
        task_open = [max(0, total - done) for total, done in zip(task_total, task_done)]
        focus_minutes = [int(row["focus_seconds"]) / 60 for row in summary["days"]]

        # Daily task completion: completed and still-open work are both visible.
        ax = axes[0, 0]
        ax.set_facecolor(bg)
        if sum(task_total):
            ax.bar(x, task_done, color=green, label="Done", width=0.68)
            ax.bar(x, task_open, bottom=task_done, color=pale, label="Still open", width=0.68)
            ax.legend(frameon=False, labelcolor=muted, fontsize=8, loc="upper right")
            ax.set_ylabel("Tasks", color=muted)
            self._format_x_axis(ax, labels, len(labels), muted)
            ax.grid(axis="y", color=grid, linewidth=0.7, alpha=0.8)
            ax.set_axisbelow(True)
        else:
            self._empty_axis(ax, "No tasks in this period", fg, muted)
        ax.set_title("Daily task progress", color=fg, loc="left", fontweight="bold", pad=10)

        # Recorded focus minutes include completed and intentionally stopped sessions.
        ax = axes[0, 1]
        ax.set_facecolor(bg)
        if sum(focus_minutes):
            ax.bar(x, focus_minutes, color=copper, width=0.68)
            ax.set_ylabel("Minutes", color=muted)
            self._format_x_axis(ax, labels, len(labels), muted)
            ax.grid(axis="y", color=grid, linewidth=0.7, alpha=0.8)
            ax.set_axisbelow(True)
        else:
            self._empty_axis(ax, "No focus time recorded yet", fg, muted)
        ax.set_title("Focus time by day", color=fg, loc="left", fontweight="bold", pad=10)

        # Two neutral doughnut charts, each with a useful empty state.
        self._draw_donut(
            axes[1, 0], int(summary["task_done"]), int(summary["task_total"]),
            "Task completion", "Done", "Still open", green, pale, bg, fg, muted,
        )
        self._draw_donut(
            axes[1, 1], int(summary["habit_done"]), int(summary["habit_total"]),
            "Habit check-ins", "Checked off", "Not checked off", blue, pale, bg, fg, muted,
        )

        for ax in self.figure.axes:
            ax.tick_params(colors=muted, labelsize=8)
            for spine in ax.spines.values():
                spine.set_color(grid)
        self.figure.tight_layout(pad=2.4, h_pad=2.8, w_pad=2.4)
        self.canvas.draw_idle()

    @staticmethod
    def _format_x_axis(ax, labels: list[str], count: int, muted: str) -> None:
        if count <= 10:
            step = 1
        elif count <= 35:
            step = 5
        else:
            step = 15
        positions = list(range(0, count, step))
        ax.set_xticks(positions, [labels[index] for index in positions], rotation=0, color=muted)

    @staticmethod
    def _empty_axis(ax, message: str, fg: str, muted: str) -> None:
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(0.5, 0.52, message, transform=ax.transAxes,
                ha="center", va="center", color=muted, fontsize=9)

    @staticmethod
    def _draw_donut(
        ax, completed: int, total: int, title: str, done_label: str,
        open_label: str, done_color: str, open_color: str, bg: str, fg: str, muted: str,
    ) -> None:
        ax.set_facecolor(bg)
        ax.set_title(title, color=fg, loc="left", fontweight="bold", pad=10)
        if total <= 0:
            ax.pie([1], colors=[open_color], startangle=90,
                   wedgeprops={"width": 0.34, "edgecolor": bg})
            ax.text(0, 0, "No data", ha="center", va="center", color=muted, fontsize=9)
            return
        remaining = max(0, total - completed)
        values = [completed, remaining]
        ax.pie(
            values,
            colors=[done_color, open_color],
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.34, "edgecolor": bg, "linewidth": 2},
        )
        percent = round(completed / total * 100)
        ax.text(0, 0, f"{percent}%", ha="center", va="center",
                color=fg, fontsize=17, fontweight="bold")
        ax.legend(
            [f"{done_label}: {completed}", f"{open_label}: {remaining}"],
            loc="lower center", bbox_to_anchor=(0.5, -0.12),
            ncol=2, frameon=False, labelcolor=muted, fontsize=8,
        )

    def _update_reasons(self, days: int) -> None:
        rows = self.repository.get_missed_reason_breakdown(days)
        self.reasons_table.setRowCount(len(rows))
        self.reasons_empty.setVisible(not rows)
        self.reasons_table.setVisible(bool(rows))
        for row_index, row in enumerate(rows):
            reason_item = QTableWidgetItem(str(row["label"]))
            reason_item.setFlags(reason_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            count_item = QTableWidgetItem(str(row["total"]))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.reasons_table.setItem(row_index, 0, reason_item)
            self.reasons_table.setItem(row_index, 1, count_item)
        self.reasons_table.resizeRowsToContents()
