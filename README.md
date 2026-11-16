# Steady — offline personal planner

Steady is a local-first desktop workspace for planning, habits, focus sessions, reminders, progress and reflection. It is written in Python with PySide6 and SQLite. The source remains fully editable; release builds package the same source for Linux, Windows and macOS.

## Quick start from source

Requirements: Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate       # Linux / macOS / zsh
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m steady
```

Run tests with `python -m pytest -q tests/`. Pytest is configured to discover only the project test directory.

## Project structure

```text
steady_app/
├── README.md
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── requirements-analytics.txt
├── src/steady/
│   ├── __main__.py
│   ├── app.py
│   ├── app_info.py          # edit public name, email and version here
│   ├── config.py
│   ├── database/
│   │   ├── db.py
│   │   └── schema.sql
│   ├── repositories/
│   │   ├── analytics_repository.py
│   │   ├── focus_repository.py
│   │   ├── habit_repository.py
│   │   ├── planner_repository.py
│   │   ├── reflection_repository.py
│   │   ├── settings_repository.py
│   │   └── todo_repository.py
│   ├── services/
│   │   ├── alarm_sound.py
│   │   └── duration.py
│   ├── assets/
│   │   ├── steady_alarm.wav
│   │   ├── ambient_threads.png
│   │   ├── warm_paper.png
│   │   └── steady_icon.png
│   └── ui/
│       ├── main_window.py
│       ├── theme.py
│       ├── dialogs/task_dialog.py
│       └── pages/
│           ├── dashboard_page.py
│           ├── day_page.py
│           ├── habits_page.py
│           ├── calendar_page.py
│           ├── focus_page.py
│           ├── analytics_page.py
│           ├── reflection_page.py
│           ├── settings_page.py
│           └── todo_page.py
├── packaging/               # native bundle builders and installers
│   ├── build_app.py
│   ├── package_release.py
│   ├── create_macos_icon.py
│   ├── linux/
│   └── windows/
├── .github/workflows/release.yml
└── tests/
```

## Features included in v1.2.0 source

Implemented:

- Application bootstrap and persistent SQLite initialization
- Versioned schema for tasks, habits, daily entries, focus sessions, miss reasons, reflections, reminders, and settings
- Seed data for reflection reasons and two starter habits
- Main window with keyboard-accessible sidebar navigation
- Light/dark theme switching, persisted in SQLite
- Daily Plan date selector with previous / next / today controls
- Add, edit, remove and date-scope tasks
- Copy all tasks from any chosen source date into the selected Daily Plan date; copied tasks retain planning details but reset to To do
- Dedicated one-off To-do Checklist separate from dated Daily Plan tasks, with task, deadline, done checkbox and notification controls arranged in one row
- Recurring weekly timetable matrix with Monday-to-Sunday columns and editable time blocks; each cell starts empty and opens an editor when clicked
- Custom timetable start/end times and adjustable 5–240-minute block lengths (5-minute steps), with a wider time column and horizontal scrolling for smaller windows
- Per-to-do deadline alert with selectable time (default 9:00 AM), overdue visibility and the existing bundled alarm sound
- Dashboard preview of the next open to-do deadlines
- Inline task priority, estimate and status controls
- Optional reflection prompt when a task is marked missed
- Daily habit checkboxes with per-date persistence (new day entries default to pending/unchecked)
- Task completion progress indicator
- Monthly task progress bars and a daily completion-rate line graph on the Progress page
- Monthly calendar with previous / next month and Today navigation
- Per-day task and habit completion summaries queried from the same SQLite database as Daily Plan
- Today's, selected-day and activity indicators
- Selecting a date in Calendar opens Daily Plan on that exact date
- Calendar refreshes when the page is opened, so it reflects changes made in Daily Plan
- Focus timer with configurable focus, short-break and long-break durations in minutes or hours (up to 24 hours), with the most recent duration preference saved locally
- Start, pause, resume, stop and reset controls, with optional task linking
- Focus-session history with completed, stopped and interrupted outcomes
- One-off, daily, weekday and weekly reminders with optional snooze
- Gentle non-modal in-app reminder notifications and bundled audible alarm
- Reminder polling every 10 seconds while the application is running; overdue recurring reminders advance to the next future occurrence instead of generating repeated catch-up alerts
- Non-modal in-app reminder prompts with 10-minute snooze and audible alarm
- Focus timer tracks elapsed time with a monotonic clock so wall-clock changes do not distort a session
- Active sessions are marked interrupted and retained in history when the application closes
- Text-only Save and Cancel buttons in the task dialog
- Progress page with selectable 7-, 30- and 90-day views
- Task completion and habit check-in summary cards
- Daily task progress and focus-time trend charts embedded with Matplotlib
- Task and habit completion doughnut charts with neutral empty states
- Optional missed-activity reason summary, without punitive scores
- Local-date-aware focus-time grouping and read-only analytics repository
- Improved dark-theme text contrast, chart labels, table headers, inputs and tooltips
- Daily reflection check-in with optional energy level, mood / working state and notes
- Reflection history stored by date, with update and delete support
- Missed task and habit review for 7-, 30- and 90-day periods
- Optional editing of missed-activity reasons and notes after the original entry
- Optional habit "Mark missed" action, with the ability to skip the reason
- Custom habit manager with create, edit, pause, resume, archive, restore and confirmed permanent deletion of archived habits
- Habit categories, start dates, selected weekday schedules and optional local reminder times
- Habit reminders are checked by the Focus & Reminders page and are claimed once per local scheduled day
- Monthly habit matrix with habits as rows and calendar dates as columns, scheduled-day progress calculations, and historical check-ins
- Archived habits disappear from future planning without deleting their daily check-in history until the user explicitly deletes them
- Bundled multi-note WAV alarm sound, played for scheduled reminders, habit reminders and focus/break timer completion
- Audible alarm enabled by default, with a test-sound button and a user-controlled mute setting
- Optional periodic task-switch cue during longer focus sessions, with a configurable interval and a shortcut to the Daily Plan
- Alarm sound falls back to the operating-system beep if Qt Multimedia cannot load the bundled WAV

Known limitations:

- Scheduled reminders require Steady to be running; OS-level alerts while the app is closed are not included.
- Reminder delivery across sleep/resume depends on the operating system timer behaviour.
- Reflection journal search and mood / energy filters are not included yet.


## Contact details and version

Edit `src/steady/app_info.py` to change the public application details:

- `APP_VERSION` — version displayed in Settings → About & contact.
- `AUTHOR_NAME` — name shown in the application.
- `CONTACT_EMAIL` — public contact email shown as a clickable mail link.

Before distributing, put the intended public email address in `CONTACT_EMAIL`. The public contact email is configured in the current source; verify it before publishing. The build includes the values present when it is packaged; after editing this file, rebuild the application.

## Data location and upgrades

The SQLite database is stored in the operating system's per-user application-data directory, not beside the executable and not inside the PyInstaller bundle. This means application updates do not overwrite planner data. Backups are stored beside the database in the `backups/` directory. Keep the same application identity (`APP_NAME` and `ORGANIZATION_NAME` in `src/steady/config.py`) between releases so existing installs keep using the same data directory.

The current database schema is version 4. Do not delete or manually replace the live database during an application update. Use Settings → Local data, backups & exports to create or restore backups.

## Build a click-to-launch application

PyInstaller bundles Python and the application's dependencies. Build on each target operating system; PyInstaller output is platform-specific and is not a cross-compiler. The release workflow in `.github/workflows/release.yml` builds Linux x86_64, Windows x64, macOS Apple Silicon and macOS Intel packages on native GitHub-hosted runners. [PyInstaller explains that builds must be made on the target OS](https://pyinstaller.org/en/latest/operating-mode.html), and documents its one-folder and app-bundle options [here](https://pyinstaller.org/en/latest/usage.html).

### Build locally on your current OS

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
python packaging/build_app.py
python packaging/package_release.py
```

Output is written to `release/`:

- Linux: `Steady-1.2.0-Linux-x86_64.tar.gz`. Extract it and run `./install.sh` to create an application-menu entry, or run `./app/Steady` directly.
- Windows: `Steady-1.2.0-Windows-x64.zip`. Extract the full folder and double-click `Steady.exe`. Optional `Create-Shortcut.ps1` creates a desktop shortcut.
- macOS: `Steady-1.2.0-macOS-<arch>.zip`. Extract and move `Steady.app` into Applications.

The build uses one-folder mode intentionally. It is easier to troubleshoot and avoids the repeated extraction delay of a one-file build. Do not separate the executable from its `_internal` support folder.

### Build all platforms automatically with GitHub Actions

1. Create a GitHub repository and push the complete `steady_app` source folder.
2. Edit `src/steady/app_info.py` and set `CONTACT_EMAIL` before a public release.
3. Push a version tag, for example:

   ```bash
   git add .
   git commit -m "Prepare Steady 1.2.0 release"
   git tag v1.2.0
   git push origin main --tags
   ```

4. Open the repository's **Actions** tab. The workflow tests and builds each platform. When all builds pass, it creates a GitHub Release with the downloadable archives and `SHA256SUMS.txt`.

A manually started workflow also creates build artifacts without publishing a GitHub Release.

### First-run platform notes

- **Linux:** the release archive includes `install.sh` and `uninstall.sh`. Uninstalling the app deliberately leaves the personal database and backups in place.
- **Windows:** this first release is not Authenticode-signed; Windows SmartScreen may show an unfamiliar-app warning.
- **macOS:** the workflow creates `.app` bundles for Apple Silicon and Intel. They are not Developer ID signed or notarized yet; Gatekeeper may require the user to approve the app on first launch. Public distribution should add Apple Developer ID signing and notarization.

## Editing the project in future

Keep the source repository as the canonical project. Most feature changes belong under `src/steady/`: UI pages in `ui/pages/`, database access in `repositories/`, and reusable business logic in `services/`. Change public name/email/version in `app_info.py`. Update tests under `tests/`, run `python -m pytest -q`, then create a new tag to build fresh platform packages. Do not edit files inside `dist/` or the installed app bundle; those are generated outputs.

## Licensing before public distribution

No application-specific `LICENSE` file has been added because the intended license for Steady's own source has not been selected. PySide6/Qt for Python is available under LGPLv3/GPLv3 or a commercial Qt license; review the applicable terms for the exact modules and build you redistribute. PyInstaller has a GPL license with a bootloader exception for bundling applications, subject to dependency licenses. See `THIRD_PARTY_NOTICES.md` before publishing.

## Database notes

- SQLite foreign-key enforcement is enabled on every connection.
- WAL mode is enabled for safer concurrent reads and writes.
- Dates are stored as ISO `YYYY-MM-DD` local calendar dates.
- Timestamps are stored as UTC ISO-8601 strings.
- `PRAGMA user_version` records the schema version. The current schema is version 4 and includes in-place migrations from earlier project releases.
- Create a manual backup before testing a new application build or updating an existing installation.

## Tests

```bash
python -m pytest -q tests/
```

The suite covers database initialization/migrations, dated tasks, the workspace to-do checklist and deadline notifications, habit schedules and monthly check-ins, focus sessions, reminders, analytics, reflections, backup/restore/export, release metadata and packaging configuration.

## Dependencies and licence notes

Runtime dependencies are declared in `pyproject.toml`. Build/test tools are in the `dev` extra. See `THIRD_PARTY_NOTICES.md` before redistributing binaries; choose a license for Steady's own source before publishing the repository publicly.


## User data and distribution privacy

Steady stores each person's tasks, habits, reflections, reminders, focus history,
and settings in a SQLite database under that person's operating-system application
data directory. The database is created on first launch. It is not stored inside
the source repository or executable bundle. Every new user therefore starts with
a separate, empty planner (apart from the built-in default habits and reflection
reason options). No developer testing tasks or reflections are shipped.

The PyInstaller build explicitly bundles only the application assets and the SQL
schema, never a live SQLite database or the backups directory. Repository ignore
rules exclude SQLite files, local backups, and CSV export folders. Do not add real
user databases or backup files to GitHub or a public ZIP.

The public About & Contact details are configured in `src/steady/app_info.py`.
Current public contact: `kartikjbsky@gmail.com`. Changing that file is enough for
source runs; rebuild the executable archives after changing public metadata.


## Branding and feedback

Steady uses the exact supplied full wordmark in the workspace sidebar and the icon-only mark for the application window and platform application icons. The Settings page displays the supplied terracotta Feedback Form banner as a large, centred clickable image that opens the project feedback Google Form in the user's default browser.
