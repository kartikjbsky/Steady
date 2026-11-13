# Steady Changelog

## 0.9.5 — Dark/light theme isolation
- Fixed light parchment backgrounds persisting in scrollable pages after switching back to dark mode.
- Added explicit dark backgrounds and cleared light-only background images for stacked pages, scroll areas, viewports, and scroll-content widgets.
- Named and styled page scroll-content widgets consistently across Habits, Focus & Reminders, Progress, and Reflection.
- Kept the parchment texture and warm surfaces confined to light mode.
- No database schema or user-data changes.

# Steady Changelog

## 0.9.4 — Warm parchment light theme
- Replaced bright white light-mode panels with low-glare parchment, sand and taupe surfaces.
- Added a subtle paper-grain background texture and explicitly themed page stack/scroll viewports to prevent black gaps.
- Added restrained burgundy primary actions and muted olive progress accents.
- Matched analytics charts to the parchment palette.
- Moved habit checkbox visuals into the shared theme so they render correctly in both light and dark modes.
- Preserved database schema v3 and all existing data.

# Steady Changelog

## 0.9.3 — Habit matrix and typography refinement
- Fixed the monthly habit matrix viewport height so every habit row is fully visible.
- Removed nested table-level scrollbars; the matrix now scrolls horizontally in one place while the page scrolls vertically.
- Standardised habit row heights and enlarged checkbox hit targets remain fully inside each row.
- Increased global body text and secondary-label sizes, navigation text, and table headers.
- Made page titles, card headings, and section headings larger and bolder.
- Preserved the v0.9.2 visual identity, bundled background, existing theme preference, and SQLite schema v3.

# Steady Changelog

## 0.9.2 — Visual refresh
- Added a restrained optical-fibre / luminous-thread background inspired by the supplied reference.
- Refined dark and light palettes, typography, page spacing, sidebar navigation, cards, forms, tables, and scrollbars.
- Added runtime selection of an installed modern sans-serif font; no font files are bundled.
- Updated analytics chart colours and habit-matrix checkbox accents to match the new visual identity.
- Bundled the PNG background as package data and added it to PyInstaller instructions.
- No database schema or data changes.

# Steady Changelog

## 0.9.1 — Archived habit delete-dialog hotfix
- Replaced unsupported QMessageBox.StandardButton.Delete with a custom “Delete permanently” button using Qt's DestructiveRole.
- Kept Cancel as the default choice; deletion still requires explicit confirmation.
- No database or data-format changes.

# Steady Changelog

## 0.9.0 — Data reliability and habit archive management
- Added daily automatic SQLite backups using the SQLite online backup API; keeps the latest 14 automatic backups.
- Added manual backup creation from Settings.
- Added validated backup restore with a safety backup of the current database before replacement.
- Restore checks SQLite integrity, foreign keys, required tables and schema version; it refuses to overwrite a running focus session.
- Added CSV export for all application tables with a JSON manifest.
- Added database integrity and row-count report.
- Added permanent deletion for archived habits only, with confirmation; dependent check-ins are removed by the existing foreign-key cascade.
- Retained SQLite schema version 3; no migration is required.

# Steady Changelog

## 0.8.2.2 — Habit matrix interaction and readability fix
- Replaced literal backslash-n strings in day headings with actual line breaks.
- Increased checkbox indicator size and contrast, added hover state and a larger click target.
- Centered day controls and improved month header alignment.
- Existing habit status records are unchanged; no database migration is needed.

# Steady Changelog

## 0.8.2.1 — Habits page startup hotfix
- Imported QProgressBar in the monthly Habits matrix page.
- Retained the v0.8.2 monthly matrix behaviour and SQLite schema version 3.

# Steady Changelog

## 0.8.2 — Monthly habit matrix
- Replaced the one-day completion column with a month grid: habits as rows and days as columns.
- Added month navigation, per-habit completion counts and a monthly progress total.
- Completion is calculated only over scheduled days that have occurred; future dates do not reduce progress.
- Past habit check-ins can be backfilled; future dates are disabled.
- Paused habits are view-only and excluded from progress; archived habits retain their pre-archive history.
- Preserved add, edit, pause, archive and restore controls below the matrix.

# Steady Changelog

## 0.8.1.2 — Startup hotfix
- Removed an invalid signal connection from MainWindow to DayPage.
- Retained the v0.8.1 database schema version (3) and v1→v2→v3 migrations.
- Kept the Habits page's Done today checkbox and shared habit_entries records.

# Changelog

## 0.8.1
- Added a "Done today" checkbox to each habit row in the Habits manager.
- Habit check-ins are saved to the shared `habit_entries` table, so Daily Plan, Calendar and Progress stay in sync.
- Habits not scheduled or active today show a disabled check-in.
- Renamed the sidebar item to "Focus & Reminders" (no underscore).
- Added a regression test proving a Habits-page check-in contributes to Progress analytics.

# Changelog

## 0.8.0 — Dashboard and forward-only task planning

- Replaced the Dashboard placeholder with a live overview of today's task completion, upcoming open tasks, today's habit check-ins, upcoming reminders, and completed focus time over the last seven days.
- Added direct navigation from Dashboard to the selected task date, Daily Plan, Habits, and Focus & reminders.
- Added a refresh timer to keep dashboard information current while Steady is open.
- Made task records dated before the local current date read-only in the UI and repository layer.
- Disabled task editing, status changes, removal, and habit check-in controls when reviewing past dates. Historical records remain visible.
- Added task rescheduling from the task editor; tasks can be moved to today or a future date, never into the past.
- Added upcoming-task repository query and regression tests for historical immutability and rescheduling.


## v0.4.0 — Focus timer and reminders

- Added configurable focus, short-break and long-break timer modes.
- Added start, pause, resume and stop/reset controls with monotonic elapsed-time tracking.
- Added optional linking of focus sessions to today's tasks.
- Added focus-session history and 7-day completed-focus totals.
- Added one-off, daily, weekday and weekly local reminders.
- Added non-modal in-app reminder notifications and optional system beep.
- Added 10-minute reminder snooze and reminder enable/disable controls.
- Added SQLite schema v2 migration for focus session types.
- Active sessions are finalised as interrupted when the app closes.


## 0.3.0 — Monthly calendar

- Replaced the Calendar placeholder with a working monthly date grid.
- Added previous-month, next-month, and Today navigation.
- Added per-day task and habit completion summaries from the shared SQLite database.
- Added visual markers for today, selected date, and dates with completed activity.
- Selecting a date opens Daily Plan on that exact date.
- Calendar refreshes whenever it is displayed, while retaining the month the user browsed to.
- Daily Plan date changes synchronise the calendar focus.
- Daily task completion excludes cancelled tasks, matching calendar totals.
- Clarified the task-table column headers.
- Replaced platform-styled task-dialog buttons with clean text-only Save and Cancel buttons.
- Kept new habit entries pending/unchecked until the user marks them done.
- Added tests for month summaries, cancelled tasks, and weekday-specific habit schedules.

The database schema has not changed in this release, so existing local database files remain compatible.


## v0.5.0 — Duration units and Progress analytics

- Added Minutes / Hours selection to the focus timer duration control.
- Duration can be configured from one minute to 24 hours; the selected amount and unit are saved locally.
- Switching between minutes and hours preserves the entered duration to within normal display rounding.
- Implemented the Progress page with 7-, 30- and 90-day reporting windows.
- Added task and habit progress summary cards, task/focus trends and completion doughnut charts.
- Added an optional, non-punitive missed-reason breakdown.
- Added a read-only AnalyticsRepository with local-date-aware focus-session aggregation.
- Added Matplotlib as a standard application dependency for embedded Qt charts.
- Added analytics and duration-conversion tests.

## v0.6.0 — Contrast refinement and Reflection journal

- Improved dark-theme secondary text, table headers, input text, tooltips and scrollbar contrast while preserving the existing navy/slate palette.
- Increased Matplotlib axis and legend label readability in the Progress page and gave chart backgrounds, gridlines and data colours more separation.
- Replaced the Reflection placeholder with a functional daily check-in for energy, mood/working state and optional notes.
- Added daily reflection create, update, load and delete operations using the existing `daily_reflections` SQLite table; no schema migration is required.
- Added a 7-, 30- and 90-day missed-activity log combining tasks and habits.
- Added editing of missed-activity reasons and notes after the original missed status was recorded.
- Added an optional "Mark missed" action for daily habits; the reason can be skipped.
- Kept reflection inputs optional and non-punitive. No score or streak penalty is generated.
- Added repository tests for daily reflection persistence, validation, missed activity aggregation, reason editing and habit miss records.


## v0.7.0 — Custom habits and audible cues

- Added a dedicated Habits page with active, paused, archived and all filters.
- Added habit creation/editing with category, start date, weekday schedule and optional reminder time.
- Added pause/resume, archive and restore actions; historical habit entries are retained.
- Connected the Habit Manager to Daily Plan, Calendar, Progress, Reflection and Focus task choices.
- Added SQLite schema v3 migration for existing v0.6 databases.
- Added a bundled three-note WAV alarm, test-sound control and a default-enabled audible alert preference. The chime plays twice per alert for better noticeability without a harsh continuous alarm.
- Audible cues fire for scheduled reminders, habit reminders, focus/break timer completion and periodic task-switch prompts.
- Added optional periodic task-switch cues during long focus sessions, including an Open Daily Plan action.
- Added an operating-system beep fallback when Qt Multimedia or the bundled sound cannot load.
- Added repository, migration and audio-asset tests.
- Added regression coverage for archived-habit history in calendar and analytics summaries.

## 1.0.0 — Cross-platform packaging foundation

- Added editable public application metadata (`app_info.py`) and an About & Contact section in Settings.
- Added a Steady application icon for window chrome and platform bundles.
- Added a native PyInstaller one-folder build script for Linux, Windows and macOS.
- Added Linux install/uninstall scripts and an application-menu launcher, a Windows executable folder and shortcut helper, and macOS `.app` packaging.
- Added GitHub Actions workflows for tests and native release builds on Linux x86_64, Windows x64, macOS Apple Silicon and macOS Intel.
- Added release archives with platform-specific SHA-256 checksum manifests.
- Kept the SQLite schema at version 3 and kept user data outside the application bundle.
- Added third-party licensing notes and a public-release checklist.
