-- ==============================================================================
-- Last Chance — Supabase PostgreSQL Schema Migration
-- Compatible with PostgreSQL 13+ (Supabase standard)
-- ==============================================================================

-- 1. USERS & PROFILES
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT DEFAULT 'Student',
    is_active INTEGER DEFAULT 1,
    theme_preference TEXT DEFAULT 'dark',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. ACADEMIC SUBJECTS (Courses)
CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    credits INTEGER NOT NULL DEFAULT 4,
    total_lectures INTEGER NOT NULL DEFAULT 42,
    exam_date TEXT,
    priority TEXT NOT NULL DEFAULT 'NORMAL',
    color TEXT NOT NULL DEFAULT '#3b82f6',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. SYLLABUS UNITS
CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    unit_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    lecture_allocation INTEGER NOT NULL DEFAULT 6,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. SYLLABUS TOPICS
CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    unit_id INTEGER NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    estimated_minutes INTEGER NOT NULL DEFAULT 60,
    base_minutes INTEGER NOT NULL DEFAULT 60,
    mastery_level TEXT NOT NULL DEFAULT 'NOT_STARTED',
    is_mandatory INTEGER NOT NULL DEFAULT 1,
    is_official INTEGER NOT NULL DEFAULT 1,
    source_doc TEXT DEFAULT 'Official Syllabus',
    order_index INTEGER NOT NULL DEFAULT 0,
    difficulty_level TEXT DEFAULT 'MODERATE',
    needs_revision INTEGER DEFAULT 0,
    last_studied_at TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. SUBTOPICS
CREATE TABLE IF NOT EXISTS subtopics (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    order_index INTEGER NOT NULL DEFAULT 0
);

-- 6. PREREQUISITES
CREATE TABLE IF NOT EXISTS prerequisites (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    prerequisite_topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    CONSTRAINT uq_prerequisites UNIQUE(topic_id, prerequisite_topic_id)
);

-- 7. APPLICATION SETTINGS
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 8. STUDY SCHEDULES (5 Daily Shifts + Wrapup)
CREATE TABLE IF NOT EXISTS study_schedules (
    id SERIAL PRIMARY KEY,
    scheduled_date TEXT NOT NULL,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    duration_minutes INTEGER NOT NULL,
    planned_start_time TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    task_type TEXT NOT NULL DEFAULT 'NEW_LEARNING',
    priority TEXT NOT NULL DEFAULT 'NORMAL',
    learning_objectives TEXT,
    suggested_breakdown TEXT,
    study_method TEXT,
    actual_minutes INTEGER DEFAULT 0,
    completion_percentage INTEGER DEFAULT 0,
    confidence_rating INTEGER DEFAULT 0,
    notes TEXT,
    blockers TEXT,
    practice_attempted INTEGER DEFAULT 0,
    completed_at TEXT,
    reasoning TEXT,
    shift_number INTEGER DEFAULT 1,
    original_date TEXT,
    task_description TEXT,
    unit_name TEXT,
    remaining_minutes INTEGER DEFAULT 45,
    is_wrapup INTEGER DEFAULT 0,
    rescheduled_count INTEGER DEFAULT 0,
    rescheduled_reason TEXT,
    is_interrupted INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. STUDY SESSIONS (Live Timer & Focus Tracking)
CREATE TABLE IF NOT EXISTS study_sessions (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    schedule_id INTEGER REFERENCES study_schedules(id) ON DELETE SET NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_seconds INTEGER DEFAULT 0,
    notes TEXT,
    confidence_rating INTEGER DEFAULT 0,
    completion_percentage INTEGER DEFAULT 0,
    actual_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. SCHEDULE CHANGE AUDIT LOGS
CREATE TABLE IF NOT EXISTS schedule_change_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT NOT NULL,
    changes_summary TEXT NOT NULL,
    affected_dates_json TEXT
);

-- 11. REVISION ITEMS
CREATE TABLE IF NOT EXISTS revision_items (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    scheduled_date TEXT NOT NULL,
    interval_days INTEGER NOT NULL DEFAULT 1,
    revision_type TEXT NOT NULL DEFAULT 'RECALL',
    status TEXT NOT NULL DEFAULT 'PENDING',
    confidence_recorded INTEGER DEFAULT 0,
    completed_at TEXT
);

-- 12. DSA QUESTIONS
CREATE TABLE IF NOT EXISTS dsa_questions (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'Medium',
    description TEXT NOT NULL,
    problem_statement TEXT,
    concept TEXT NOT NULL,
    hints_json TEXT,
    hint_1 TEXT,
    hint_2 TEXT,
    solution TEXT NOT NULL,
    solution_approach TEXT,
    solution_code TEXT,
    approach_notes TEXT,
    time_complexity TEXT DEFAULT 'O(N)',
    space_complexity TEXT DEFAULT 'O(1)',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 13. DAILY DSA ASSIGNMENTS (2 Questions/Day)
CREATE TABLE IF NOT EXISTS daily_dsa_assignments (
    id SERIAL PRIMARY KEY,
    assigned_date TEXT NOT NULL,
    question_id INTEGER NOT NULL REFERENCES dsa_questions(id) ON DELETE CASCADE,
    slot_number INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'Pending',
    user_approach TEXT,
    approach_notes TEXT,
    time_spent_minutes INTEGER DEFAULT 0,
    mistakes_notes TEXT,
    mistakes TEXT,
    completed_at TEXT,
    topic_name TEXT,
    CONSTRAINT uq_daily_dsa UNIQUE(assigned_date, question_id)
);

-- 14. ENGLISH SPEAKING TOPICS
CREATE TABLE IF NOT EXISTS english_speaking_topics (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    objective TEXT NOT NULL,
    vocabulary_json TEXT NOT NULL,
    starter_phrases_json TEXT,
    prompt_questions_json TEXT,
    vocabulary TEXT,
    speaking_prompts TEXT
);

-- 15. DAILY ENGLISH PRACTICE LOGS
CREATE TABLE IF NOT EXISTS daily_english_logs (
    id SERIAL PRIMARY KEY,
    assigned_date TEXT UNIQUE,
    log_date TEXT UNIQUE,
    topic_id INTEGER NOT NULL REFERENCES english_speaking_topics(id) ON DELETE CASCADE,
    duration_seconds INTEGER DEFAULT 0,
    time_spent_seconds INTEGER DEFAULT 0,
    notes TEXT,
    completed INTEGER NOT NULL DEFAULT 0,
    is_completed INTEGER NOT NULL DEFAULT 0,
    streak_count INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    actual_minutes INTEGER DEFAULT 0,
    shortfall_minutes INTEGER DEFAULT 0
);

-- 16. DAILY QUOTES
CREATE TABLE IF NOT EXISTS daily_quotes (
    id SERIAL PRIMARY KEY,
    quote TEXT NOT NULL,
    quote_text TEXT,
    category TEXT NOT NULL,
    author TEXT DEFAULT 'Unknown',
    is_favorite INTEGER NOT NULL DEFAULT 0,
    day_offset INTEGER NOT NULL DEFAULT 0
);

-- 17. CALENDAR EVENTS
CREATE TABLE IF NOT EXISTS calendar_events (
    id SERIAL PRIMARY KEY,
    event_date TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    event_type TEXT NOT NULL DEFAULT 'study',
    start_time TEXT,
    end_time TEXT,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    subject_code TEXT,
    color TEXT,
    notes TEXT,
    is_completed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 18. WASTED TIME LOGS
CREATE TABLE IF NOT EXISTS wasted_time_logs (
    id SERIAL PRIMARY KEY,
    log_date TEXT NOT NULL,
    minutes INTEGER NOT NULL,
    reason TEXT,
    category TEXT NOT NULL DEFAULT 'Unproductive Time',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 19. HANDOUTS & STUDY MATERIALS (Supabase Storage Integrated)
CREATE TABLE IF NOT EXISTS handouts (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    unit_id INTEGER REFERENCES units(id) ON DELETE SET NULL,
    topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    file_path TEXT NOT NULL,
    storage_path TEXT,
    is_remote INTEGER DEFAULT 0,
    upload_date TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 20. DOUBTS & ACADEMIC QUESTIONS
CREATE TABLE IF NOT EXISTS doubts (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER REFERENCES study_schedules(id) ON DELETE SET NULL,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
    doubt_text TEXT NOT NULL,
    answer_text TEXT,
    status TEXT NOT NULL DEFAULT 'UNRESOLVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT
);

-- 21. RESCHEDULED HISTORY
CREATE TABLE IF NOT EXISTS rescheduled_history (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER NOT NULL REFERENCES study_schedules(id) ON DELETE CASCADE,
    original_date TEXT NOT NULL,
    from_date TEXT NOT NULL,
    to_date TEXT NOT NULL,
    reason TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 22. QUOTE FAVORITES
CREATE TABLE IF NOT EXISTS quote_favorites (
    id SERIAL PRIMARY KEY,
    quote_text TEXT NOT NULL UNIQUE,
    author TEXT DEFAULT 'Unknown',
    category TEXT DEFAULT 'Inspiration',
    favorited_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 23. REDO / PRACTICE AGAIN TASKS
CREATE TABLE IF NOT EXISTS redo_tasks (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER REFERENCES study_schedules(id) ON DELETE SET NULL,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    topic_title TEXT NOT NULL,
    course_code TEXT,
    course_name TEXT,
    unit_number INTEGER,
    unit_title TEXT,
    original_completion_date TEXT,
    added_to_redo_date TEXT NOT NULL,
    due_date TEXT,
    priority TEXT DEFAULT 'MEDIUM',
    reason TEXT,
    status TEXT DEFAULT 'PENDING',
    redo_count INTEGER DEFAULT 0,
    last_practiced_at TEXT,
    completed_at TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_study_schedules_date ON study_schedules(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_study_schedules_topic ON study_schedules(topic_id);
CREATE INDEX IF NOT EXISTS idx_study_schedules_status ON study_schedules(status);
CREATE INDEX IF NOT EXISTS idx_topics_unit ON topics(unit_id);
CREATE INDEX IF NOT EXISTS idx_units_subject ON units(subject_id);
CREATE INDEX IF NOT EXISTS idx_handouts_hierarchy ON handouts(subject_id, unit_id);
CREATE INDEX IF NOT EXISTS idx_daily_dsa_date ON daily_dsa_assignments(assigned_date);
CREATE INDEX IF NOT EXISTS idx_daily_english_date ON daily_english_logs(log_date);
CREATE INDEX IF NOT EXISTS idx_redo_tasks_status ON redo_tasks(status);
