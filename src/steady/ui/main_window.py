from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from pathlib import Path

from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from steady.database import Database
from steady.repositories.settings_repository import SettingsRepository
from steady.ui.pages.analytics_page import AnalyticsPage
from steady.ui.pages.calendar_page import CalendarPage
from steady.ui.pages.dashboard_page import DashboardPage
from steady.ui.pages.day_page import DayPage
from steady.ui.pages.focus_page import FocusPage
from steady.ui.pages.habits_page import HabitManagerPage
from steady.ui.pages.reflection_page import ReflectionPage
from steady.ui.pages.settings_page import SettingsPage
from steady.ui.pages.timetable_page import TimetablePage
from steady.ui.pages.todo_page import TodoPage


class MainWindow(QMainWindow):
    theme_changed = Signal(str)

    NAV_ITEMS = (
        ("Dashboard", "Alt+1"),
        ("Daily plan", "Alt+2"),
        ("To-do checklist", "Alt+3"),
        ("Timetable", "Alt+4"),
        ("Habits", "Alt+5"),
        ("Calendar", "Alt+6"),
        ("Focus & Reminders", "Alt+7"),
        ("Progress", "Alt+8"),
        ("Reflection", "Alt+9"),
        ("Settings", "Alt+0"),
    )

    def __init__(self, database: Database, current_theme: str = "dark", backup_notice: str | None = None) -> None:
        super().__init__()
        self.database = database
        self.setWindowTitle("Steady — Daily Planner")
        self.resize(1280, 820)
        self.setMinimumSize(1000, 660)

        root = QWidget()
        root.setObjectName("root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(232)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(21, 27, 19, 22)
        sidebar_layout.setSpacing(5)

        # Use the supplied full wordmark in the sidebar; the icon-only asset is
        # used for the application window and platform-specific package icons.
        logo_path = Path(__file__).resolve().parents[1] / "assets" / "steady_wordmark.png"
        logo = QLabel()
        logo.setAccessibleName("Steady logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(190, 190)
        logo_pixmap = QPixmap(str(logo_path))
        if not logo_pixmap.isNull():
            logo.setPixmap(
                logo_pixmap.scaled(
                    190,
                    190,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            logo.setText("STEADY")
            logo.setObjectName("brand")
        sidebar_layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)

        copyright = QLabel("© 2026 Kartikkumar Bagilavaidya\nAll rights reserved.")
        copyright.setObjectName("muted")
        copyright.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright.setWordWrap(True)
        copyright.setStyleSheet("font-size: 7.5pt; line-height: 1.2;")
        sidebar_layout.addWidget(copyright)

        strapline = QLabel("A calmer way to organise your day")
        strapline.setObjectName("muted")
        strapline.setWordWrap(True)
        strapline.setMaximumWidth(175)
        sidebar_layout.addWidget(strapline)
        sidebar_layout.addSpacing(8)

        sidebar_rule = QFrame()
        sidebar_rule.setObjectName("sidebarDivider")
        sidebar_rule.setFrameShape(QFrame.Shape.HLine)
        sidebar_layout.addWidget(sidebar_rule)
        sidebar_layout.addSpacing(12)

        section_label = QLabel("YOUR WORKSPACE")
        section_label.setObjectName("muted")
        section_label.setStyleSheet("font-size: 9.5pt; font-weight: 800; letter-spacing: 1px;")
        sidebar_layout.addWidget(section_label)

        self.stack = QStackedWidget()
        self.pages = [
            DashboardPage(database),
            DayPage(database),
            TodoPage(database),
            TimetablePage(database),
            HabitManagerPage(database),
            CalendarPage(database),
            FocusPage(database),
            AnalyticsPage(database),
            ReflectionPage(database),
            SettingsPage(database, current_theme=current_theme, backup_notice=backup_notice),
        ]
        self.pages[-1].theme_changed.connect(self.theme_changed.emit)
        self.pages[-1].data_restored.connect(self._after_data_restore)
        self.page_titles = [
            "Dashboard", "Daily plan", "To-do checklist", "Timetable", "Habits",
            "Calendar", "Focus & Reminders", "Progress", "Reflection", "Settings"
        ]
        for page in self.pages:
            self.stack.addWidget(page)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons: list[QPushButton] = []
        for index, (label, shortcut) in enumerate(self.NAV_ITEMS):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setAccessibleName(f"Navigate to {label}")
            button.setToolTip(f"{label} ({shortcut})")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.nav_group.addButton(button, index)
            self.nav_buttons.append(button)
            button.setMinimumHeight(43)
            sidebar_layout.addWidget(button)
            QShortcut(QKeySequence(shortcut), self, activated=lambda i=index: self.navigate(i))
        sidebar_layout.addStretch(1)

        footer = QLabel("PRIVATE BY DESIGN  ·  OFFLINE")
        footer.setObjectName("muted")
        footer.setStyleSheet("font-size: 8.5pt; letter-spacing: 0.5px;")
        footer.setWordWrap(True)
        sidebar_layout.addWidget(footer)

        root_layout.addWidget(sidebar)
        self.stack.setObjectName("pageStack")
        root_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.nav_group.idClicked.connect(self.navigate)
        self.pages[0].open_day_requested.connect(self.open_day_from_dashboard)
        self.pages[0].open_todo_requested.connect(lambda: self.navigate(2))
        self.pages[0].open_focus_requested.connect(lambda: self.navigate(6))
        self.pages[0].open_habits_requested.connect(lambda: self.navigate(4))
        self.pages[1].selected_date_changed.connect(self.pages[5].set_focus_date)
        self.pages[4].habits_changed.connect(self._on_habits_changed)
        self.pages[5].open_day_requested.connect(self.open_day_from_calendar)
        self.pages[6].open_daily_plan_requested.connect(lambda: self.navigate(1))
        self.navigate(0)

    def closeEvent(self, event) -> None:
        """Persist an active timer as interrupted when the window closes."""
        focus_page = self.pages[6]
        if hasattr(focus_page, "shutdown"):
            focus_page.shutdown()
        super().closeEvent(event)

    def open_day_from_dashboard(self, selected_day: object) -> None:
        """Open the Daily Plan for a date selected on the dashboard."""
        self.pages[1].set_selected_day(selected_day)
        self.navigate(1)

    def open_day_from_calendar(self, selected_day: object) -> None:
        """Open the Daily Plan on the exact date selected in the calendar."""
        self.pages[1].set_selected_day(selected_day)
        self.navigate(1)

    def _on_habits_changed(self) -> None:
        """Refresh every screen that derives information from habit definitions."""
        self.pages[1].load_day(self.pages[1].current_day)
        self.pages[0].refresh()
        self.pages[5].refresh()
        self.pages[7].refresh()
        self.pages[8].refresh()
        self.pages[6].refresh()

    def _after_data_restore(self) -> None:
        """Refresh all database-backed pages after a validated restore."""
        self.database.initialize()
        settings = SettingsRepository(self.database)
        mode = settings.get("theme", "light") or "light"
        if mode not in {"light", "dark"}:
            mode = "light"
        self.pages[9].set_current_theme(mode)
        self.theme_changed.emit(mode)

        self.pages[0].refresh()
        self.pages[1].load_day(self.pages[1].current_day)
        self.pages[2].refresh()
        self.pages[3].refresh()
        self.pages[4].refresh()
        self.pages[5].refresh()
        self.pages[6].refresh()
        self.pages[7].refresh()
        self.pages[8].refresh()

    def navigate(self, index: int) -> None:
        if not 0 <= index < self.stack.count():
            return
        refresh_by_index = {
            0: self.pages[0].refresh,
            2: self.pages[2].refresh,
            3: self.pages[3].refresh,
            4: self.pages[4].refresh,
            5: self.pages[5].refresh,
            6: self.pages[6].refresh,
            7: self.pages[7].refresh,
            8: self.pages[8].refresh,
        }
        refresh = refresh_by_index.get(index)
        if refresh is not None:
            refresh()
        self.stack.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        self.setWindowTitle(f"Steady — {self.page_titles[index]}")
