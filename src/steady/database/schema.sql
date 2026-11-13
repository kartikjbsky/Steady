-- Steady schema v2. Dates use local YYYY-MM-DD calendar dates.
-- All *_at timestamps are UTC ISO-8601 strings.

CREATE TABLE IF NOT EXISTS miss_reasons (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    label           TEXT NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    sort_order      INTEGER NOT NULL DEFAULT 0
);

-- A task row is a dated occurrence. This keeps rescheduling/history simple:
-- editing tomorrow's task does not rewrite yesterday's record.
CREATE TABLE IF NOT EXISTS tasks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL CHECK (length(trim(title)) > 0),
    description         TEXT NOT NULL DEFAULT '',
    scheduled_date      TEXT NOT NULL
                        CHECK (date(scheduled_date) IS NOT NULL
                               AND date(scheduled_date) = scheduled_date),
    priority            INTEGER NOT NULL DEFAULT 2 CHECK (priority BETWEEN 1 AND 3),
    estimate_minutes    INTEGER CHECK (estimate_minutes IS NULL OR estimate_minutes > 0),
    status              TEXT NOT NULL DEFAULT 'todo'
                        CHECK (status IN ('todo', 'in_progress', 'done', 'missed', 'cancelled')),
    sort_order          INTEGER NOT NULL DEFAULT 0,
    miss_reason_id      INTEGER REFERENCES miss_reasons(id) ON DELETE SET NULL,
    reflection_note     TEXT NOT NULL DEFAULT '',
    completed_at        TEXT,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_tasks_date_status ON tasks(scheduled_date, status, sort_order);

CREATE TABLE IF NOT EXISTS habits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
    description     TEXT NOT NULL DEFAULT '',
    -- Seven-character Monday-to-Sunday mask, e.g. 1111100 for weekdays.
    weekday_mask    TEXT NOT NULL DEFAULT '1111111'
                    CHECK (length(weekday_mask) = 7 AND weekday_mask NOT GLOB '*[^01]*'),
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    is_builtin      INTEGER NOT NULL DEFAULT 0 CHECK (is_builtin IN (0, 1)),
    category        TEXT NOT NULL DEFAULT 'other'
                    CHECK (category IN ('study', 'research', 'wellbeing', 'health', 'personal', 'other')),
    start_date      TEXT NOT NULL DEFAULT '1970-01-01'
                    CHECK (date(start_date) IS NOT NULL AND date(start_date) = start_date),
    reminder_enabled INTEGER NOT NULL DEFAULT 0 CHECK (reminder_enabled IN (0, 1)),
    reminder_time   TEXT,
    reminder_last_fired_date TEXT,
    archived_at     TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS habit_entries (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id            INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    entry_date          TEXT NOT NULL
                        CHECK (date(entry_date) IS NOT NULL
                               AND date(entry_date) = entry_date),
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'done', 'missed', 'not_applicable')),
    miss_reason_id      INTEGER REFERENCES miss_reasons(id) ON DELETE SET NULL,
    reflection_note     TEXT NOT NULL DEFAULT '',
    completed_at        TEXT,
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (habit_id, entry_date)
);
CREATE INDEX IF NOT EXISTS idx_habit_entries_date_status ON habit_entries(entry_date, status);

-- Optional end-of-day reflection, separate from missed-task explanations.
CREATE TABLE IF NOT EXISTS daily_reflections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    reflection_date TEXT NOT NULL UNIQUE
                    CHECK (date(reflection_date) IS NOT NULL
                           AND date(reflection_date) = reflection_date),
    energy_level    INTEGER CHECK (energy_level IS NULL OR energy_level BETWEEN 1 AND 5),
    mood_label      TEXT NOT NULL DEFAULT '',
    note            TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS reminders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL CHECK (length(trim(title)) > 0),
    message         TEXT NOT NULL DEFAULT '',
    due_at          TEXT NOT NULL,
    is_enabled      INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
    repeat_rule     TEXT NOT NULL DEFAULT 'none'
                    CHECK (repeat_rule IN ('none', 'daily', 'weekdays', 'weekly')),
    last_fired_at   TEXT,
    dismissed_at    TEXT,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_reminders_due_enabled ON reminders(is_enabled, due_at);

-- Focus-session history supports focus-time summaries and interruption patterns.
CREATE TABLE IF NOT EXISTS focus_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    linked_task_id      INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    started_at          TEXT NOT NULL,
    ended_at            TEXT,
    planned_seconds     INTEGER NOT NULL CHECK (planned_seconds > 0),
    actual_seconds      INTEGER CHECK (actual_seconds IS NULL OR actual_seconds >= 0),
    outcome             TEXT NOT NULL DEFAULT 'running'
                        CHECK (outcome IN ('running', 'completed', 'stopped', 'interrupted')),
    session_type        TEXT NOT NULL DEFAULT 'focus'
                        CHECK (session_type IN ('focus', 'short_break', 'long_break')),
    note                TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_focus_sessions_started_at ON focus_sessions(started_at);

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key     TEXT PRIMARY KEY,
    setting_value   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_habits_reminder ON habits(is_active, reminder_enabled, reminder_time);
