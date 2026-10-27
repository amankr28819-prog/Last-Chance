import sqlite3
import json
import os
import shutil
import re
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DATA_DIR, "lastchance.db")
OLD_DB_PATH = os.path.join(DATA_DIR, "studypilot.db")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

TABLES_WITH_ID = {
    'users', 'subjects', 'units', 'topics', 'subtopics', 'prerequisites',
    'study_schedules', 'study_sessions', 'schedule_change_logs', 'revision_items',
    'dsa_questions', 'daily_dsa_assignments', 'english_speaking_topics',
    'daily_english_logs', 'daily_quotes', 'calendar_events', 'wasted_time_logs',
    'handouts', 'doubts', 'rescheduled_history', 'quote_favorites', 'redo_tasks'
}

def translate_query_for_postgres(query: str) -> tuple[str, bool]:
    """Translates SQLite query syntax into PostgreSQL compatible query syntax."""
    # 1. Translate datetime('now') -> CURRENT_TIMESTAMP
    q = re.sub(r"datetime\('now'\)", "CURRENT_TIMESTAMP", query, flags=re.IGNORECASE)

    # 2. Translate placeholders ? -> %s safely (outside single and double quotes)
    tokens = []
    in_single = False
    in_double = False
    i = 0
    while i < len(q):
        c = q[i]
        if c == "'" and not in_double:
            in_single = not in_single
            tokens.append(c)
        elif c == '"' and not in_single:
            in_double = not in_double
            tokens.append(c)
        elif c == '?' and not in_single and not in_double:
            tokens.append('%s')
        else:
            tokens.append(c)
        i += 1
    translated = ''.join(tokens)

    # 3. Check for INSERT needing RETURNING id for lastrowid compatibility
    has_returning = False
    stripped = translated.strip().rstrip(';')
    if re.match(r'^\s*INSERT\s+INTO\s+', stripped, re.IGNORECASE):
        m = re.match(r'^\s*INSERT\s+INTO\s+([\"`\w]+)', stripped, re.IGNORECASE)
        if m:
            tbl = m.group(1).strip('"`').lower()
            if tbl in TABLES_WITH_ID and 'RETURNING' not in stripped.upper():
                stripped += ' RETURNING id'
                has_returning = True
    return stripped, has_returning

class PostgresCursorWrapper:
    def __init__(self, real_cursor):
        self._cursor = real_cursor
        self.lastrowid = None

    def execute(self, query, params=None):
        pg_query, has_returning = translate_query_for_postgres(query)
        if params is not None:
            if isinstance(params, list):
                params = tuple(params)
            self._cursor.execute(pg_query, params)
        else:
            self._cursor.execute(pg_query)

        if has_returning:
            try:
                res = self._cursor.fetchone()
                if res is not None:
                    self.lastrowid = res["id"] if isinstance(res, dict) or hasattr(res, "get") else res[0]
            except Exception:
                pass
        return self

    def executemany(self, query, seq_of_params):
        pg_query, _ = translate_query_for_postgres(query)
        self._cursor.executemany(pg_query, seq_of_params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size else self._cursor.fetchmany()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def close(self):
        self._cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class PostgresConnectionWrapper:
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        import psycopg2.extras
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PostgresCursorWrapper(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def execute(self, query, params=None):
        cur = self.cursor()
        return cur.execute(query, params)

    def executescript(self, script):
        with self._conn.cursor() as cur:
            cur.execute(script)
        self._conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def is_postgres() -> bool:
    return bool(os.environ.get("DATABASE_URL", "").strip())

def get_connection(db_path: str = DB_PATH):
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if db_url:
        import psycopg2
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        raw_conn = psycopg2.connect(db_url)
        return PostgresConnectionWrapper(raw_conn)

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Safe migration: if old studypilot.db exists and lastchance.db does not, migrate it
    if db_path == DB_PATH and not os.path.exists(db_path) and os.path.exists(OLD_DB_PATH):
        try:
            shutil.copy2(OLD_DB_PATH, db_path)
        except Exception:
            pass

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db(db_path: str = DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if is_postgres():
        schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations", "001_supabase_schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
        seed_initial_data_if_empty(conn)
        seed_dsa_questions_if_empty(conn)
        seed_english_topics_if_empty(conn)
        seed_quotes_if_empty(conn)
        return

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        credits INTEGER NOT NULL DEFAULT 4,
        total_lectures INTEGER NOT NULL DEFAULT 42,
        exam_date TEXT,
        priority TEXT NOT NULL DEFAULT 'NORMAL', -- 'NORMAL', 'HIGH', 'URGENT'
        color TEXT NOT NULL DEFAULT '#6366f1',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        unit_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        lecture_allocation INTEGER NOT NULL DEFAULT 6,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        estimated_minutes INTEGER NOT NULL DEFAULT 60,
        base_minutes INTEGER NOT NULL DEFAULT 60,
        mastery_level TEXT NOT NULL DEFAULT 'NOT_STARTED', -- NOT_STARTED, STUDIED_ONCE, PARTIALLY_UNDERSTOOD, NEEDS_REVISION, CONFIDENT, MASTERED
        is_mandatory INTEGER NOT NULL DEFAULT 1,
        is_official INTEGER NOT NULL DEFAULT 1,
        source_doc TEXT DEFAULT 'Official Syllabus',
        order_index INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS subtopics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        order_index INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS prerequisites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        prerequisite_topic_id INTEGER NOT NULL,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
        FOREIGN KEY (prerequisite_topic_id) REFERENCES topics(id) ON DELETE CASCADE,
        UNIQUE(topic_id, prerequisite_topic_id)
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS study_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheduled_date TEXT NOT NULL,
        topic_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        duration_minutes INTEGER NOT NULL,
        planned_start_time TEXT,
        status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, COMPLETED, PARTIALLY_COMPLETED, MISSED
        task_type TEXT NOT NULL DEFAULT 'NEW_LEARNING', -- NEW_LEARNING, PRACTICE, REVISION, TEST
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
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        schedule_id INTEGER,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        duration_seconds INTEGER DEFAULT 0,
        notes TEXT,
        confidence_rating INTEGER DEFAULT 0,
        completion_percentage INTEGER DEFAULT 0,
        actual_minutes INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
        FOREIGN KEY (schedule_id) REFERENCES study_schedules(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS schedule_change_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        reason TEXT NOT NULL,
        changes_summary TEXT NOT NULL,
        affected_dates_json TEXT
    );

    CREATE TABLE IF NOT EXISTS revision_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        scheduled_date TEXT NOT NULL,
        interval_days INTEGER NOT NULL DEFAULT 1,
        revision_type TEXT NOT NULL DEFAULT 'RECALL', -- RECALL, PROBLEM_SOLVING, CODE_PRACTICE, FORMULA, MOCK_TEST
        status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, COMPLETED, SKIPPED
        confidence_recorded INTEGER DEFAULT 0,
        completed_at TEXT,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
    );

    -- New Dedicated Tables for Personalized Routine
    CREATE TABLE IF NOT EXISTS dsa_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL DEFAULT 'Medium', -- Easy, Medium, Hard
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
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS daily_dsa_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assigned_date TEXT NOT NULL,
        question_id INTEGER NOT NULL,
        slot_number INTEGER DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'Pending', -- Pending, Attempted, Solved, Needs Revision
        user_approach TEXT,
        approach_notes TEXT,
        time_spent_minutes INTEGER DEFAULT 0,
        mistakes_notes TEXT,
        mistakes TEXT,
        completed_at TEXT,
        FOREIGN KEY (question_id) REFERENCES dsa_questions(id) ON DELETE CASCADE,
        UNIQUE(assigned_date, question_id)
    );

    CREATE TABLE IF NOT EXISTS english_speaking_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        objective TEXT NOT NULL,
        vocabulary_json TEXT NOT NULL,
        starter_phrases_json TEXT,
        prompt_questions_json TEXT,
        vocabulary TEXT,
        speaking_prompts TEXT
    );

    CREATE TABLE IF NOT EXISTS daily_english_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assigned_date TEXT UNIQUE,
        log_date TEXT UNIQUE,
        topic_id INTEGER NOT NULL,
        duration_seconds INTEGER DEFAULT 0,
        time_spent_seconds INTEGER DEFAULT 0,
        notes TEXT,
        completed INTEGER NOT NULL DEFAULT 0,
        is_completed INTEGER NOT NULL DEFAULT 0,
        streak_count INTEGER NOT NULL DEFAULT 0,
        completed_at TEXT,
        FOREIGN KEY (topic_id) REFERENCES english_speaking_topics(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS daily_quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote TEXT NOT NULL,
        quote_text TEXT,
        category TEXT NOT NULL,
        author TEXT DEFAULT 'Unknown',
        is_favorite INTEGER NOT NULL DEFAULT 0,
        day_offset INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        event_type TEXT NOT NULL DEFAULT 'study', -- study, college, holiday, exam, personal
        start_time TEXT,
        end_time TEXT,
        duration_minutes INTEGER NOT NULL DEFAULT 60,
        subject_code TEXT,
        color TEXT,
        notes TEXT,
        is_completed INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS wasted_time_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        minutes INTEGER NOT NULL,
        reason TEXT,
        category TEXT NOT NULL DEFAULT 'Unproductive Time',
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS handouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_filename TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER NOT NULL DEFAULT 0,
        subject_id INTEGER NOT NULL,
        unit_id INTEGER,
        topic_id INTEGER,
        file_path TEXT NOT NULL,
        upload_date TEXT NOT NULL DEFAULT (datetime('now')),
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
        FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS doubts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id INTEGER,
        subject_id INTEGER NOT NULL,
        topic_id INTEGER,
        doubt_text TEXT NOT NULL,
        answer_text TEXT,
        status TEXT NOT NULL DEFAULT 'UNRESOLVED', -- UNRESOLVED, RESOLVED
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        resolved_at TEXT,
        FOREIGN KEY (schedule_id) REFERENCES study_schedules(id) ON DELETE SET NULL,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS rescheduled_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id INTEGER NOT NULL,
        original_date TEXT NOT NULL,
        from_date TEXT NOT NULL,
        to_date TEXT NOT NULL,
        reason TEXT,
        status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, UNDONE
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (schedule_id) REFERENCES study_schedules(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS quote_favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote_text TEXT NOT NULL,
        author TEXT DEFAULT 'Unknown',
        category TEXT DEFAULT 'Inspiration',
        favorited_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(quote_text)
    );

    CREATE TABLE IF NOT EXISTS redo_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id INTEGER,
        topic_id INTEGER,
        subject_id INTEGER,
        topic_title TEXT NOT NULL,
        course_code TEXT,
        course_name TEXT,
        unit_number INTEGER,
        unit_title TEXT,
        original_completion_date TEXT,
        added_to_redo_date TEXT NOT NULL,
        due_date TEXT,
        priority TEXT DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH', 'URGENT'
        reason TEXT,
        status TEXT DEFAULT 'PENDING', -- 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'POSTPONED'
        redo_count INTEGER DEFAULT 0,
        last_practiced_at TEXT,
        completed_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (schedule_id) REFERENCES study_schedules(id) ON DELETE SET NULL,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        password_hash TEXT NOT NULL,
        full_name TEXT DEFAULT 'Student',
        is_active INTEGER DEFAULT 1,
        theme_preference TEXT DEFAULT 'dark',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    conn.commit()

    # Safe backwards-compatible column additions
    def add_col_if_missing(table_name, col_name, col_def):
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = [r["name"] for r in cursor.fetchall()]
        if col_name not in cols:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
            conn.commit()

    add_col_if_missing("daily_english_logs", "actual_minutes", "INTEGER DEFAULT 0")
    add_col_if_missing("daily_english_logs", "shortfall_minutes", "INTEGER DEFAULT 0")
    add_col_if_missing("daily_dsa_assignments", "topic_name", "TEXT")
    add_col_if_missing("wasted_time_logs", "notes", "TEXT")
    
    # Study schedules extra columns for timetable & shifts
    add_col_if_missing("study_schedules", "shift_number", "INTEGER DEFAULT 1")
    add_col_if_missing("study_schedules", "original_date", "TEXT")
    add_col_if_missing("study_schedules", "task_description", "TEXT")
    add_col_if_missing("study_schedules", "unit_name", "TEXT")
    add_col_if_missing("study_schedules", "remaining_minutes", "INTEGER DEFAULT 45")
    add_col_if_missing("study_schedules", "is_wrapup", "INTEGER DEFAULT 0")
    add_col_if_missing("study_schedules", "rescheduled_count", "INTEGER DEFAULT 0")
    add_col_if_missing("study_schedules", "rescheduled_reason", "TEXT")
    add_col_if_missing("study_schedules", "is_interrupted", "INTEGER DEFAULT 0")

    # Topics extra columns for weak topics & revision
    add_col_if_missing("topics", "difficulty_level", "TEXT DEFAULT 'MODERATE'")
    add_col_if_missing("topics", "needs_revision", "INTEGER DEFAULT 0")
    add_col_if_missing("topics", "last_studied_at", "TEXT")
    add_col_if_missing("topics", "notes", "TEXT")

    seed_initial_data_if_empty(conn)
    seed_dsa_questions_if_empty(conn)
    seed_english_topics_if_empty(conn)
    seed_quotes_if_empty(conn)

    # Clean any legacy reversed or cross-course prerequisite entries
    try:
        cursor.execute("UPDATE OR IGNORE prerequisites SET topic_id = 131, prerequisite_topic_id = 116 WHERE topic_id = 116 AND prerequisite_topic_id = 131")
        cursor.execute("DELETE FROM prerequisites WHERE topic_id = 116 AND prerequisite_topic_id = 131")
        cursor.execute("UPDATE OR IGNORE prerequisites SET topic_id = 103, prerequisite_topic_id = 102 WHERE topic_id = 102 AND prerequisite_topic_id = 43")
        cursor.execute("DELETE FROM prerequisites WHERE topic_id = 102 AND prerequisite_topic_id = 43")
        conn.commit()
    except Exception:
        pass

    # Ensure standard aliases for targets are populated
    for k, v in [("daily_academic_target_minutes", 240), ("english_speaking_target_minutes", 30), ("daily_dsa_count", 2)]:
        if get_setting(conn, k) is None:
            set_setting(conn, k, v)

    conn.close()

def get_setting(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    if row:
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]
    return default

def set_setting(conn: sqlite3.Connection, key: str, value: Any):
    cursor = conn.cursor()
    val_str = json.dumps(value) if not isinstance(value, str) else value
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, val_str))
    conn.commit()

def seed_initial_data_if_empty(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM subjects")
    has_subjects = cursor.fetchone()["count"] > 0

    # Default Settings
    default_settings = {
        "app_name": "Last Chance",
        "first_exam_date": "2026-11-26",
        "syllabus_deadline": "2026-11-19",
        "revision_buffer_days": 7,
        "is_buffer_mandatory": True,
        # Daily study targets strictly separated
        "academic_daily_target_minutes": 240, # 4 Hours main academic study
        "daily_academic_target_minutes": 240,
        "english_daily_target_minutes": 30,    # 30 Minutes English speaking
        "english_speaking_target_minutes": 30,
        "dsa_daily_question_count": 2,         # 2 DSA questions daily
        "daily_dsa_count": 2,
        # College schedule
        "college_working_day_hours": 3.0,     # 3 hours on working days
        "college_holiday_hours": 5.0,         # 5 hours on holidays if marked
        "working_days": ["mon", "tue", "wed", "thu", "fri"],
        "weekly_holidays": ["sat", "sun"],
        # Special 7-day holiday (6-11 Dec inclusive = 6 days, option for 7th)
        "special_break_start": "2026-12-06",
        "special_break_end": "2026-12-11",
        "special_break_include_7th_day": False,
        "special_break_notice": "Note: Dec 6 to Dec 11 inclusive contains 6 calendar days. You can optionally include Dec 12 as the 7th day in Settings.",
        "weekday_minutes": 240,  # 4 hours academic study
        "weekend_minutes": 240,  # 4 hours academic study
        "college_hours": "09:00 - 12:00",
        "commute_minutes": 30,
        "sleep_hours": "23:30 - 06:30",
        "study_windows": [
            {"name": "Morning Slot", "start": "06:45", "end": "08:15", "minutes": 90, "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"name": "Evening Slot", "start": "18:00", "end": "19:30", "minutes": 90, "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"name": "Night Slot", "start": "20:30", "end": "21:30", "minutes": 60, "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"name": "Weekend Morning", "start": "08:00", "end": "11:00", "minutes": 180, "days": ["sat", "sun"]},
            {"name": "Weekend Evening", "start": "16:00", "end": "18:00", "minutes": 120, "days": ["sat", "sun"]}
        ],
        "blocked_dates": [],
        "session_duration": 60,
        "max_consecutive_minutes": 90,
        "break_duration": 15,
        "subjects_per_day": 2,
        "study_style": "INTERLEAVED",
        "daily_practice": True,
        "spaced_revision": True,
        "onboarding_completed": True,
        "theme": "dark",
        "time_zone": "Asia/Kolkata"
    }

    for k, v in default_settings.items():
        cursor.execute("SELECT value FROM settings WHERE key = ?", (k,))
        if not cursor.fetchone():
            val_str = json.dumps(v) if not isinstance(v, str) else v
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, val_str))

    if has_subjects:
        return

    # Seed the 4 official subjects
    subjects_data = [
        {
            "code": "CSN 3003",
            "name": "Discrete Structures for Computer Science",
            "credits": 4,
            "total_lectures": 42,
            "color": "#6366f1",
            "priority": "HIGH",
            "exam_date": "2026-11-26",
            "units": [
                {
                    "unit_number": 1,
                    "title": "Mathematical Reasoning",
                    "lecture_allocation": 8,
                    "topics": [
                        ("Mathematical reasoning", 60, ["Logic structures", "Deductive vs inductive reasoning"]),
                        ("Propositions", 45, ["Declarative statements", "Truth values"]),
                        ("Negation", 30, ["Truth inversion", "Logical NOT operator"]),
                        ("Disjunction and conjunction", 45, ["Logical OR, AND", "Truth conditions"]),
                        ("Implication and equivalence", 60, ["Conditional statements", "Biconditional", "Converse, inverse, contrapositive"]),
                        ("Truth tables", 60, ["Table construction", "Tautologies", "Contradictions", "Contingencies"]),
                        ("Predicates", 45, ["Propositional functions", "Domain of discourse"]),
                        ("Quantifiers", 60, ["Universal quantifier", "Existential quantifier", "Negating quantified expressions"]),
                        ("Natural deduction", 90, ["Inference rules", "Derivation trees", "Hypothetical reasoning"]),
                        ("Rules of inference", 75, ["Modus Ponens", "Modus Tollens", "Hypothetical Syllogism", "Disjunctive Syllogism"]),
                        ("Methods of proofs", 90, ["Direct proof", "Proof by contraposition", "Proof by contradiction", "Exhaustive proof"]),
                        ("Resolution principle", 75, ["Clausal form", "Unification", "Resolution refutation"]),
                        ("Application to PROLOG", 60, ["Facts and rules", "Query evaluation", "Prolog horn clauses"])
                    ]
                },
                {
                    "unit_number": 2,
                    "title": "Set Theory",
                    "lecture_allocation": 8,
                    "topics": [
                        ("Paradoxes in set theory", 45, ["Russell's paradox", "Naive set theory limitations"]),
                        ("Inductive definition of sets", 60, ["Base case", "Inductive step", "Closure"]),
                        ("Proof by induction", 75, ["Mathematical induction", "Strong induction", "Well-ordering principle"]),
                        ("Peano postulates", 60, ["Axioms for natural numbers", "Successor function"]),
                        ("Relations", 45, ["Binary relations", "Domain and range", "Matrix and digraph representation"]),
                        ("Properties of relations", 60, ["Reflexive", "Symmetric", "Transitive", "Antisymmetric"]),
                        ("Equivalence relations and partitions", 75, ["Equivalence classes", "Quotient sets", "Fundamental partition theorem"]),
                        ("Partial orderings", 60, ["Reflexive, antisymmetric, transitive relations", "Comparability"]),
                        ("POSETs", 60, ["Partially ordered sets", "Hasse diagrams", "Maximal/minimal elements"]),
                        ("Linear and well-ordered sets", 60, ["Total order", "Well-ordered sets", "Lexicographic ordering"])
                    ]
                },
                {
                    "unit_number": 3,
                    "title": "Functions",
                    "lecture_allocation": 6,
                    "topics": [
                        ("Functions", 45, ["Definition", "Domain, codomain, range"]),
                        ("Mappings", 45, ["Total vs partial mappings", "Image and preimage"]),
                        ("Injection", 45, ["One-to-one functions", "Horizontal line test"]),
                        ("Surjections", 45, ["Onto functions", "Codomain coverage"]),
                        ("Composition of functions", 60, ["Associativity of composition", "Identity mapping"]),
                        ("Inversions", 60, ["Bijections", "Inverse function properties"]),
                        ("Special functions", 60, ["Floor and ceiling", "Mod function", "Characteristic function"]),
                        ("Recursive function theory", 75, ["Primitive recursive functions", "Ackermann function", "Computability"])
                    ]
                },
                {
                    "unit_number": 4,
                    "title": "Combinatorics",
                    "lecture_allocation": 9,
                    "topics": [
                        ("Elementary combinatorics", 45, ["Sum rule", "Product rule", "Inclusion-exclusion principle"]),
                        ("Pigeonhole principle", 60, ["Standard form", "Generalized pigeonhole principle", "Applications"]),
                        ("Permutations and combinations", 75, ["Formulas", "Combinations with repetitions", "Binomial coefficients"]),
                        ("Counting techniques", 60, ["Circular permutations", "Derangements", "Partitions of integers"]),
                        ("Recurrence relations", 60, ["Formulating recurrences", "Initial conditions"]),
                        ("Solving linear recurrence relations", 90, ["Homogeneous linear recurrences", "Particular solutions", "Characteristic roots"]),
                        ("Generating functions", 90, ["Ordinary generating functions", "Solving recurrences using generating functions"])
                    ]
                },
                {
                    "unit_number": 5,
                    "title": "Graph Theory, Groups, Rings and Fields",
                    "lecture_allocation": 8,
                    "topics": [
                        ("Elements of graph theory", 60, ["Vertices, edges, degrees", "Handshaking lemma", "Subgraphs"]),
                        ("Graph isomorphism", 60, ["Adjacency matrix equivalence", "Invariants of isomorphism"]),
                        ("Euler graph", 60, ["Eulerian path and circuit", "Euler's theorem", "Fleury's algorithm"]),
                        ("Hamiltonian paths", 60, ["Hamiltonian circuits", "Dirac's theorem", "Ore's theorem"]),
                        ("Trees", 60, ["Tree definitions", "Properties of trees", "Rooted trees"]),
                        ("Tree traversals", 60, ["Inorder, preorder, postorder traversals in graph contexts"]),
                        ("Spanning trees", 60, ["Cut property", "Cycle property", "Fundamental cycles"]),
                        ("Representation of relations by graphs", 45, ["Directed graph of a relation", "Transitive closure and Warshall's algorithm"]),
                        ("Definition and elementary properties of groups", 75, ["Closure, associativity, identity, inverse", "Abelian groups"]),
                        ("Semigroups", 45, ["Associative binary operation", "Subsemigroups"]),
                        ("Monoids", 45, ["Semigroup with identity element", "Submonoids"]),
                        ("Rings", 60, ["Ring definition", "Distributive laws", "Zero divisors", "Integral domains"]),
                        ("Fields", 60, ["Field definition", "Finite fields / Galois fields", "Inverses in fields"]),
                        ("Vector spaces", 60, ["Axioms", "Subspaces", "Linear independence", "Basis and dimension"]),
                        ("Lattices", 60, ["POSET as lattice", "Meet and join operations", "Distributive and modular lattices"])
                    ]
                },
                {
                    "unit_number": 6,
                    "title": "Discrete Probability",
                    "lecture_allocation": 3,
                    "topics": [
                        ("Introduction to probability", 45, ["Sample spaces", "Events", "Axioms of probability"]),
                        ("Probability theory", 60, ["Conditional probability", "Independence of events"]),
                        ("Bayes' theorem", 75, ["Law of total probability", "Posterior probability calculation"]),
                        ("Expected value and variance", 60, ["Expectation of random variables", "Properties of variance"]),
                        ("Discrete random variables", 60, ["Bernoulli, Binomial, and Geometric distributions"])
                    ]
                }
            ]
        },
        {
            "code": "CSN 3001",
            "name": "Data Structures",
            "credits": 4,
            "total_lectures": 42,
            "color": "#10b981",
            "priority": "HIGH",
            "exam_date": "2026-11-28",
            "units": [
                {
                    "unit_number": 1,
                    "title": "Review",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Classes", 45, ["Class structure", "Data encapsulation", "Constructors in C++"]),
                        ("Pointers", 60, ["Pointer arithmetic", "Dynamic memory", "Dangling pointers"]),
                        ("Recursion", 60, ["Base cases", "Recursive call stacks", "Tail recursion"]),
                        ("Time and space complexity of algorithms", 75, ["Big-O, Omega, Theta notations", "Worst, average, best case analysis"]),
                        ("Recurrence relations", 60, ["Formulating recursive equations for algorithms"]),
                        ("Solving recurrence relations using the substitution method", 75, ["Mathematical induction verification", "Master theorem intro"])
                    ]
                },
                {
                    "unit_number": 2,
                    "title": "Linked Lists",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Introduction to linked lists", 45, ["Node structure", "Singly linked list representation"]),
                        ("Insertion", 60, ["Insert at beginning, end, and given position", "Edge cases"]),
                        ("Deletion", 60, ["Delete by value, delete at position", "Memory deallocation"]),
                        ("Searching in linked lists", 45, ["Linear search", "Traversal efficiency"]),
                        ("Doubly linked lists", 60, ["Forward and backward pointers", "Insertion and deletion in DLL"]),
                        ("Circular linked lists", 60, ["Circular singly and doubly linked lists", "Split and traversal"]),
                        ("Sparse matrix storage", 60, ["Sparse matrix representation using linked lists", "Memory comparison"]),
                        ("Polynomial operations", 75, ["Polynomial addition and multiplication using linked lists"])
                    ]
                },
                {
                    "unit_number": 3,
                    "title": "Stacks",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Introduction to stacks", 45, ["LIFO principle", "Push, pop, peek operations"]),
                        ("Stack implementation using arrays", 60, ["Fixed and dynamic arrays", "Stack overflow and underflow"]),
                        ("Stack implementation using linked lists", 60, ["Top pointer management", "Dynamic size"]),
                        ("Balanced brackets", 60, ["Parentheses matching algorithm", "Multi-bracket verification"]),
                        ("Infix to postfix conversion", 75, ["Operator precedence and associativity", "Shunting-yard stack algorithm"]),
                        ("Postfix evaluation", 60, ["Operand evaluation using stack", "Handling multiple operators"])
                    ]
                },
                {
                    "unit_number": 4,
                    "title": "Queues",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Introduction to queues", 45, ["FIFO principle", "Enqueue and dequeue operations"]),
                        ("Queue implementation using arrays", 60, ["Linear queue and circular queue to prevent waste of space"]),
                        ("Queue implementation using linked lists", 60, ["Front and rear pointer operations"]),
                        ("Job scheduling in CPU", 75, ["Round robin queue implementation", "Ready queue management"])
                    ]
                },
                {
                    "unit_number": 5,
                    "title": "Trees",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Introduction to trees", 45, ["Root, leaves, internal nodes", "Subtrees and parent-child relations"]),
                        ("Tree terminology", 45, ["Height, depth, level, degree of node"]),
                        ("Tree representations", 60, ["Array representation", "First-child next-sibling representation"]),
                        ("Tree implementation", 60, ["Node structures in C++", "Memory layout"]),
                        ("Binary trees", 60, ["Full, complete, and degenerate binary trees", "Properties"]),
                        ("Traversals in binary trees", 75, ["Preorder, Inorder, Postorder recursive traversals"]),
                        ("BFS in binary trees", 75, ["Level order traversal using queue", "Spiral level order"]),
                        ("DFS in binary trees", 75, ["Iterative traversal using explicit stack"])
                    ]
                },
                {
                    "unit_number": 6,
                    "title": "Binary Search Trees",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Binary search trees", 60, ["BST property", "Search operation", "Min and max elements"]),
                        ("Insertion in BST", 60, ["Recursive and iterative insertion", "Maintaining BST property"]),
                        ("Deletion in BST", 90, ["Node with 0, 1, or 2 children", "Inorder predecessor/successor replacement"]),
                        ("AVL trees", 100, ["Balance factor", "LL, RR, LR, RL rotations", "AVL insertion and deletion"]),
                        ("B-trees", 90, ["Multiway search tree", "Order of B-tree", "Search, insert, and split operations"])
                    ]
                },
                {
                    "unit_number": 7,
                    "title": "Graphs",
                    "lecture_allocation": 6,
                    "topics": [
                        ("Introduction to graphs", 45, ["Directed vs undirected", "Weighted vs unweighted"]),
                        ("Graph terminology", 45, ["Degree, path, cycle, connectivity, components"]),
                        ("Graph representations", 60, ["Adjacency matrix", "Adjacency list", "Space-time comparison"]),
                        ("Graph implementation", 60, ["C++ representation with vectors and lists"]),
                        ("Graph traversal", 75, ["Breadth First Search (BFS)", "Depth First Search (DFS)", "Cycle detection"]),
                        ("Dijkstra's algorithm for single-source shortest paths", 90, ["Greedy approach", "Priority queue implementation", "Relaxation"]),
                        ("Spanning trees", 60, ["Minimum spanning tree properties", "Cut property"]),
                        ("Prim's algorithm", 75, ["Growing MST from vertex", "Min-heap implementation"]),
                        ("Kruskal's algorithm", 75, ["Edge sorting", "Cycle prevention with disjoint sets"]),
                        ("Union-find data structure", 75, ["Disjoint set union", "Find with path compression", "Union by rank"])
                    ]
                },
                {
                    "unit_number": 8,
                    "title": "Advanced Data Structures",
                    "lecture_allocation": 6,
                    "topics": [
                        ("Heaps", 75, ["Binary min-heap and max-heap", "Heapify algorithm", "Array representation"]),
                        ("Priority queues using heaps", 60, ["Insert, extract-min, decrease-key operations"]),
                        ("Hashing", 75, ["Hash functions", "Collision resolution: chaining, open addressing (linear, quadratic, double hashing)"]),
                        ("Indexing", 60, ["Dense vs sparse indexes", "B+ tree indexing principles"])
                    ]
                }
            ]
        },
        {
            "code": "CSN 3004",
            "name": "Object Oriented Programming",
            "credits": 4,
            "total_lectures": 42,
            "color": "#f59e0b",
            "priority": "NORMAL",
            "exam_date": "2026-12-01",
            "units": [
                {
                    "unit_number": 1,
                    "title": "Introduction to Object-Oriented Programming and Design",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Abstraction", 45, ["Data abstraction", "Process abstraction", "Real-world modeling"]),
                        ("Objects", 45, ["State, behavior, identity", "Object lifecycle"]),
                        ("Encapsulation", 45, ["Data binding", "Information hiding boundaries"]),
                        ("Information hiding", 45, ["Access specifiers", "Interface vs implementation"]),
                        ("Methods", 45, ["Member functions", "Message passing"]),
                        ("Method signatures", 30, ["Function name", "Parameter list", "Return type distinctions"]),
                        ("Classes and instances", 45, ["Blueprint concept", "Instantiating objects"]),
                        ("Polymorphism", 60, ["Compile-time vs run-time polymorphism", "Concept of dynamic binding"]),
                        ("Inheritance", 60, ["Code reuse", "Base and derived concepts", "Is-a relationship"])
                    ]
                },
                {
                    "unit_number": 2,
                    "title": "Programming Basics",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Variables and assignments", 30, ["L-values and R-values", "Variable scoping"]),
                        ("Input and output", 45, ["Streams in C++", "cin, cout, cerr", "Format manipulators"]),
                        ("Data types and expressions", 45, ["Primitive types", "Type casting", "Operator precedence"]),
                        ("Flow of control", 45, ["Branching (if-else, switch)", "Loops (for, while, do-while)"]),
                        ("Subprograms", 45, ["Function definitions", "Function prototypes"]),
                        ("Top-down design", 45, ["Modular decomposition", "Stepwise refinement"]),
                        ("Predefined functions", 30, ["Standard math and string library functions"]),
                        ("User-defined functions", 45, ["Defining and calling custom functions"]),
                        ("Procedural abstractions", 45, ["Separating what a function does from how it is done"]),
                        ("Local variables", 30, ["Stack frame allocation", "Scope and lifetime"]),
                        ("Parameter passing", 60, ["Pass by value", "Pass by reference", "Pass by pointer", "Const references"]),
                        ("Arrays", 60, ["One-dimensional and multidimensional arrays", "Array-pointer decay"])
                    ]
                },
                {
                    "unit_number": 3,
                    "title": "Classes",
                    "lecture_allocation": 8,
                    "topics": [
                        ("Defining classes", 60, ["Class declaration syntax", "Member variables and functions"]),
                        ("Member functions", 60, ["Inline member functions", "Outside class definition using scope resolution ::"]),
                        ("Public and private members", 45, ["Access controls", "Protected access specifier"]),
                        ("Constructors for initialization", 75, ["Default constructor", "Parameterized constructors", "Member initializer lists"]),
                        ("Destructors", 60, ["Cleanup operations", "Automatic invocation", "Resource release"]),
                        ("Copy constructors", 75, ["Shallow copy vs deep copy", "Passing objects by value"]),
                        ("Static functions", 60, ["Static member variables", "Class-level functions without this pointer"]),
                        ("Friend functions", 60, ["Friend functions and friend classes", "Breaking encapsulation safely"]),
                        ("The `this` pointer", 45, ["Self-referential pointer", "Method chaining", "Disambiguating variable names"])
                    ]
                },
                {
                    "unit_number": 4,
                    "title": "Overloading",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Overloading unary operators", 60, ["++ and -- (prefix vs postfix)", "Member function vs friend function"]),
                        ("Overloading binary operators", 75, ["+, -, *, / operators for custom classes", "Stream operators << and >>"]),
                        ("Overloading the assignment operator", 75, ["Self-assignment check", "Deep copying in operator="]),
                        ("Data conversion", 60, ["Basic to class type", "Class to basic type (conversion operators)"]),
                        ("Pitfalls of operator overloading", 45, ["Loss of natural operator semantics", "Ambiguity in conversions"]),
                        ("Operator overloading and conversion", 60, ["Explicit constructors", "Preventing accidental implicit conversions"])
                    ]
                },
                {
                    "unit_number": 5,
                    "title": "Inheritance",
                    "lecture_allocation": 7,
                    "topics": [
                        ("Concept of inheritance", 45, ["Generalization and specialization", "Code reusability"]),
                        ("Derived classes and base classes", 60, ["Inheritance syntax", "Public, protected, private inheritance modes"]),
                        ("Derived-class constructors", 75, ["Order of constructor/destructor execution", "Calling base class constructor"]),
                        ("Member functions", 60, ["Function overriding vs function overloading in inheritance"]),
                        ("Class hierarchies", 60, ["Multilevel inheritance", "Hierarchical inheritance"]),
                        ("Types of inheritance", 60, ["Single, multiple, multilevel, hierarchical, hybrid inheritance"]),
                        ("Aggregation", 60, ["Has-a relationship", "Composition vs aggregation"]),
                        ("Classes within classes", 60, ["Nested / inner classes", "Scoping and access permissions"])
                    ]
                },
                {
                    "unit_number": 6,
                    "title": "Pointers and Virtual Functions",
                    "lecture_allocation": 7,
                    "topics": [
                        ("The address-of operator", 45, ["& operator", "Pointer declaration and dereferencing *"]),
                        ("Pointers", 60, ["Pointers to structures and classes", "Arrow operator ->"]),
                        ("Dynamic memory management", 75, ["Heap allocation", "Memory leaks and fragmentation"]),
                        ("`new` and `delete`", 60, ["Dynamic single objects and arrays", "delete vs delete[]"]),
                        ("Pointers to objects", 60, ["Base class pointer pointing to derived class object"]),
                        ("Virtual functions", 90, ["Virtual keyword", "VTABLE and VPTR mechanism", "Pure virtual functions and abstract classes"]),
                        ("Assignment and copy initialization", 60, ["Object slicing problem", "Virtual destructors"])
                    ]
                }
            ]
        },
        {
            "code": "CSN 3002",
            "name": "Data Science & Machine Learning",
            "credits": 4,
            "total_lectures": 42,
            "color": "#8b5cf6",
            "priority": "HIGH",
            "exam_date": "2026-12-04",
            "units": [
                {
                    "unit_number": 1,
                    "title": "Introduction to Data Science",
                    "lecture_allocation": 6,
                    "topics": [
                        ("Basics of data science and machine learning", 45, ["Data science workflow", "AI vs ML vs DL distinction"]),
                        ("Types of data", 45, ["Quantitative vs qualitative", "Nominal, ordinal, interval, ratio"]),
                        ("Structured data", 45, ["Tabular data", "Relational databases", "Schema constraints"]),
                        ("Unstructured data", 45, ["Text, audio, images, videos", "Storage and processing challenges"]),
                        ("Other data types", 45, ["Semi-structured data (JSON, XML)", "Streaming and time-series data"]),
                        ("Data science process", 60, ["CRISP-DM methodology", "Problem formulation, data prep, modeling, deployment"]),
                        ("Exploring and visualising data", 60, ["Histograms, scatter plots, box plots", "Summary statistics"]),
                        ("Features", 45, ["Feature matrix representation", "Independent vs dependent variables"]),
                        ("Linear algebra", 75, ["Vectors, matrices, dot products, matrix multiplication, rank, determinants"]),
                        ("Correlation", 60, ["Pearson correlation coefficient", "Spearman rank correlation", "Correlation vs causation"])
                    ]
                },
                {
                    "unit_number": 2,
                    "title": "Data Acquisition and Preprocessing",
                    "lecture_allocation": 7,
                    "topics": [
                        ("Data sources and collection", 45, ["APIs, web scraping, sensors, database queries"]),
                        ("Data storage and management", 45, ["Data warehouses, data lakes, distributed storage basics"]),
                        ("Data preparation", 45, ["Pipeline setup", "Data auditing"]),
                        ("Handling missing data", 60, ["MCAR, MAR, MNAR", "Imputation (mean, median, KNN)", "Dropping rows"]),
                        ("Feature encoding", 60, ["One-hot encoding", "Label encoding", "Target encoding"]),
                        ("Feature scaling", 60, ["Min-Max normalization", "Standardization (Z-score)", "Robust scaling"]),
                        ("Data cleaning", 60, ["Duplicate removal", "Outlier detection (IQR, Z-score)", "Inconsistent data fix"]),
                        ("Dataset division", 45, ["Train-test split methodology", "Data leakage prevention"]),
                        ("Training sets", 45, ["Model fitting data", "Representative sampling"]),
                        ("Test sets", 45, ["Unseen test evaluation", "Final unbiased metric reporting"]),
                        ("Validation sets", 45, ["Hyperparameter tuning set", "Early stopping"])
                    ]
                },
                {
                    "unit_number": 3,
                    "title": "Machine Learning Fundamentals",
                    "lecture_allocation": 7,
                    "topics": [
                        ("Applications of machine learning", 45, ["Recommendation systems, NLP, vision, finance"]),
                        ("Introduction to machine learning techniques", 45, ["Inductive learning", "Parametric vs non-parametric models"]),
                        ("Supervised learning", 60, ["Regression vs classification tasks", "Ground truth labels"]),
                        ("Unsupervised learning", 60, ["Pattern discovery", "Clustering and association rules"]),
                        ("Reinforcement learning", 60, ["Agents, environments, states, actions, rewards", "Policy and value iteration"]),
                        ("Bias-variance trade-off", 75, ["Underfitting vs overfitting balance", "Model complexity curves"]),
                        ("Overfitting and underfitting", 60, ["Symptoms on train vs validation curves", "Regularization strategies"]),
                        ("Evaluation measures", 60, ["Loss functions vs evaluation metrics"]),
                        ("SSE", 45, ["Sum of squared errors", "MSE, RMSE, MAE comparison"]),
                        ("R-squared", 45, ["Coefficient of determination", "Adjusted R-squared interpretation"]),
                        ("Confusion matrix", 60, ["TP, FP, TN, FN matrix construction"]),
                        ("Precision", 45, ["Positive predictive value", "Impact on false positive sensitive tasks"]),
                        ("Recall", 45, ["Sensitivity / true positive rate", "Impact on false negative sensitive tasks"]),
                        ("F-score", 45, ["Harmonic mean of precision and recall", "F1 score vs F-beta"]),
                        ("ROC curve", 60, ["Receiver operating characteristic", "AUC score interpretation"]),
                        ("Cross-validation", 60, ["K-fold cross validation", "Stratified K-fold", "Leave-one-out CV"])
                    ]
                },
                {
                    "unit_number": 4,
                    "title": "Regression and Classification",
                    "lecture_allocation": 12,
                    "topics": [
                        ("Simple linear regression", 75, ["Slope and intercept derivation", "Least squares criterion", "Assumptions"]),
                        ("Multiple linear regression", 90, ["Matrix formulation", "Multicollinearity", "VIF"]),
                        ("Logistic regression", 90, ["Sigmoid function", "Log-odds", "Binary cross-entropy loss", "Decision boundary"]),
                        ("Gradient descent algorithm", 90, ["Batch, Stochastic, and Mini-batch gradient descent", "Learning rate scheduling"]),
                        ("K-nearest neighbours", 75, ["Euclidean/Manhattan distance metrics", "Choosing optimal K", "Curse of dimensionality"]),
                        ("Support Vector Machine", 100, ["Hyperplanes, margins, support vectors", "Hard vs soft margin", "Kernel trick"]),
                        ("Naive Bayes", 75, ["Bayes theorem application", "Conditional independence assumption", "Gaussian and Multinomial NB"]),
                        ("Decision trees", 90, ["Entropy and Information Gain", "Gini impurity", "ID3, C4.5, CART algorithms", "Pruning"])
                    ]
                },
                {
                    "unit_number": 5,
                    "title": "Dimensionality Reduction and Clustering",
                    "lecture_allocation": 10,
                    "topics": [
                        ("Feature selection", 60, ["Filter methods (Chi-square, ANOVA)", "Wrapper methods (RFE)", "Embedded methods (Lasso L1)"]),
                        ("Principal Component Analysis", 100, ["Covariance matrix", "Eigenvalues and eigenvectors", "Explained variance ratio"]),
                        ("K-means clustering", 75, ["Centroid initialization", "Lloyd's algorithm", "Elbow method", "Silhouette score"]),
                        ("Hierarchical clustering", 75, ["Agglomerative vs divisive", "Dendrograms", "Linkage criteria: single, complete, average"]),
                        ("Density-based clustering", 90, ["DBSCAN algorithm", "Epsilon and MinPts parameters", "Core, border, and noise points"])
                    ]
                }
            ]
        }
    ]

    for subj in subjects_data:
        cursor.execute("""
            INSERT INTO subjects (code, name, credits, total_lectures, color, priority, exam_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (subj["code"], subj["name"], subj["credits"], subj["total_lectures"], subj["color"], subj["priority"], subj["exam_date"]))
        subject_id = cursor.lastrowid

        for u in subj["units"]:
            cursor.execute("""
                INSERT INTO units (subject_id, unit_number, title, lecture_allocation)
                VALUES (?, ?, ?, ?)
            """, (subject_id, u["unit_number"], u["title"], u["lecture_allocation"]))
            unit_id = cursor.lastrowid

            for idx, topic_info in enumerate(u["topics"]):
                title, mins, subtopics = topic_info
                cursor.execute("""
                    INSERT INTO topics (unit_id, subject_id, title, estimated_minutes, base_minutes, order_index)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (unit_id, subject_id, title, mins, mins, idx))
                topic_id = cursor.lastrowid

                for s_idx, st in enumerate(subtopics):
                    cursor.execute("""
                        INSERT INTO subtopics (topic_id, title, order_index)
                        VALUES (?, ?, ?)
                    """, (topic_id, st, s_idx))

    # Add realistic prerequisites scoped by course code to prevent cross-course collisions
    cursor.execute("SELECT id, code FROM subjects")
    subject_map = {row["code"]: row["id"] for row in cursor.fetchall()}

    cursor.execute("SELECT id, subject_id, title FROM topics")
    topic_map = {(row["subject_id"], row["title"]): row["id"] for row in cursor.fetchall()}

    prereqs = [
        # Discrete Structures (CSN 3003)
        ("CSN 3003", "Truth tables", "Propositions"),
        ("CSN 3003", "Quantifiers", "Predicates"),
        ("CSN 3003", "Rules of inference", "Truth tables"),
        ("CSN 3003", "Methods of proofs", "Rules of inference"),
        ("CSN 3003", "Equivalence relations and partitions", "Properties of relations"),
        ("CSN 3003", "POSETs", "Partial orderings"),
        ("CSN 3003", "Inversions", "Injection"),
        ("CSN 3003", "Inversions", "Surjections"),
        ("CSN 3003", "Solving linear recurrence relations", "Recurrence relations"),
        ("CSN 3003", "Spanning trees", "Trees"),
        ("CSN 3003", "Probability theory", "Introduction to probability"),
        ("CSN 3003", "Bayes' theorem", "Probability theory"),
        ("CSN 3003", "Expected value and variance", "Discrete random variables"),

        # Data Structures (CSN 3001)
        ("CSN 3001", "Doubly linked lists", "Introduction to linked lists"),
        ("CSN 3001", "Balanced brackets", "Introduction to stacks"),
        ("CSN 3001", "Infix to postfix conversion", "Introduction to stacks"),
        ("CSN 3001", "Job scheduling in CPU", "Queue implementation using arrays"),
        ("CSN 3001", "Traversals in binary trees", "Binary trees"),
        ("CSN 3001", "BFS in binary trees", "Binary trees"),
        ("CSN 3001", "DFS in binary trees", "Binary trees"),
        ("CSN 3001", "Insertion in BST", "Binary search trees"),
        ("CSN 3001", "Deletion in BST", "Insertion in BST"),
        ("CSN 3001", "AVL trees", "Binary search trees"),
        ("CSN 3001", "B-trees", "Binary search trees"),
        ("CSN 3001", "Graph traversal", "Graph implementation"),
        ("CSN 3001", "Dijkstra's algorithm for single-source shortest paths", "Graph traversal"),
        ("CSN 3001", "Prim's algorithm", "Spanning trees"),
        ("CSN 3001", "Kruskal's algorithm", "Union-find data structure"),
        ("CSN 3001", "Priority queues using heaps", "Heaps"),

        # Object Oriented Programming (CSN 3004)
        ("CSN 3004", "Copy constructors", "Constructors for initialization"),
        ("CSN 3004", "Overloading binary operators", "Overloading unary operators"),
        ("CSN 3004", "Derived-class constructors", "Derived classes and base classes"),
        ("CSN 3004", "Types of inheritance", "Derived classes and base classes"),
        ("CSN 3004", "Virtual functions", "Pointers to objects"),
        ("CSN 3004", "Virtual functions", "Derived classes and base classes"),

        # Data Science & Machine Learning (CSN 3002)
        ("CSN 3002", "Exploring and visualising data", "Basics of data science and machine learning"),
        ("CSN 3002", "Handling missing data", "Data sources and collection"),
        ("CSN 3002", "Feature encoding", "Types of data"),
        ("CSN 3002", "Feature scaling", "Feature encoding"),
        ("CSN 3002", "Data cleaning", "Handling missing data"),
        ("CSN 3002", "Bias-variance trade-off", "Supervised learning"),
        ("CSN 3002", "Overfitting and underfitting", "Bias-variance trade-off"),
        ("CSN 3002", "Precision", "Confusion matrix"),
        ("CSN 3002", "Recall", "Confusion matrix"),
        ("CSN 3002", "F-score", "Precision"),
        ("CSN 3002", "ROC curve", "Evaluation measures"),
        ("CSN 3002", "Cross-validation", "Dataset division"),
        ("CSN 3002", "Multiple linear regression", "Simple linear regression"),
        ("CSN 3002", "Gradient descent algorithm", "Simple linear regression"),
        ("CSN 3002", "Logistic regression", "Gradient descent algorithm"),
        ("CSN 3002", "Principal Component Analysis", "Linear algebra"),
        ("CSN 3002", "Hierarchical clustering", "K-means clustering"),
        ("CSN 3002", "Density-based clustering", "K-means clustering")
    ]

    for code, topic_title, prereq_title in prereqs:
        sub_id = subject_map.get(code)
        if sub_id:
            top_id = topic_map.get((sub_id, topic_title))
            pre_id = topic_map.get((sub_id, prereq_title))
            if top_id and pre_id:
                cursor.execute("""
                    INSERT OR IGNORE INTO prerequisites (topic_id, prerequisite_topic_id)
                    VALUES (?, ?)
                """, (top_id, pre_id))

    conn.commit()

def seed_dsa_questions_if_empty(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM dsa_questions")
    if cursor.fetchone()["count"] > 0:
        return

    questions = [
        (
            "Reverse a Singly Linked List",
            "Linked Lists",
            "Easy",
            "Given the head of a singly linked list, reverse the list in-place and return its new head.",
            "Pointer manipulation, iterative 3-pointer technique (prev, curr, next) and recursive call stack.",
            json.dumps([
                "Initialize three pointers: prev = NULL, curr = head, next = NULL.",
                "In each iteration, save curr->next before modifying it.",
                "Point curr->next backwards to prev, then advance prev and curr."
            ]),
            "Time Complexity: O(N) where N is number of nodes.\nSpace Complexity: O(1) iterative in-place.\n\nIterative Solution in C++:\n```cpp\nListNode* reverseList(ListNode* head) {\n    ListNode *prev = nullptr, *curr = head;\n    while (curr != nullptr) {\n        ListNode* nextTemp = curr->next;\n        curr->next = prev;\n        prev = curr;\n        curr = nextTemp;\n    }\n    return prev;\n}\n```"
        ),
        (
            "Detect and Remove Loop in Linked List (Floyd's Cycle)",
            "Linked Lists",
            "Medium",
            "Given a linked list, detect whether a cycle exists. If a cycle exists, find the starting node of the loop and break the cycle.",
            "Fast and slow pointers (tortoise and hare algorithm), modular arithmetic on linked nodes.",
            json.dumps([
                "Advance slow by 1 step and fast by 2 steps. If they meet, a cycle exists.",
                "Reset one pointer to head while keeping the other at the meeting point.",
                "Advance both by 1 step until they meet; that meeting point is the loop start."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(1).\n\n```cpp\nListNode* detectCycle(ListNode* head) {\n    ListNode *slow = head, *fast = head;\n    while (fast && fast->next) {\n        slow = slow->next;\n        fast = fast->next->next;\n        if (slow == fast) {\n            ListNode* entry = head;\n            while (entry != slow) {\n                entry = entry->next;\n                slow = slow->next;\n            }\n            return entry; // loop start\n        }\n    }\n    return nullptr;\n}\n```"
        ),
        (
            "Valid Parentheses Matching",
            "Stacks",
            "Easy",
            "Given a string containing just '(', ')', '{', '}', '[' and ']', determine if the input string is valid by balanced bracket ordering.",
            "LIFO stack principle, matching opening and closing delimiter pairs.",
            json.dumps([
                "Push opening brackets onto stack.",
                "When encountering a closing bracket, check if stack is non-empty and top matches.",
                "At the end of string, stack must be empty."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(N).\n\n```cpp\nbool isValid(string s) {\n    stack<char> st;\n    for (char c : s) {\n        if (c == '(' || c == '{' || c == '[') st.push(c);\n        else {\n            if (st.empty()) return false;\n            char top = st.top(); st.pop();\n            if ((c == ')' && top != '(') || (c == '}' && top != '{') || (c == ']' && top != '[')) return false;\n        }\n    }\n    return st.empty();\n}\n```"
        ),
        (
            "Evaluate Reverse Polish Notation (Postfix Expression)",
            "Stacks",
            "Medium",
            "Evaluate the value of an arithmetic expression in Reverse Polish Notation. Valid operators are +, -, *, /.",
            "Operand stack, operator precedence elimination in postfix.",
            json.dumps([
                "Iterate through tokens. If token is number, push to stack.",
                "If operator, pop two operands: right operand first, left operand second.",
                "Apply operator, push result back to stack."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(N).\n\n```cpp\nint evalRPN(vector<string>& tokens) {\n    stack<int> st;\n    for (const string& t : tokens) {\n        if (t == \"+\" || t == \"-\" || t == \"*\" || t == \"/\") {\n            int b = st.top(); st.pop();\n            int a = st.top(); st.pop();\n            if (t == \"+\") st.push(a + b);\n            else if (t == \"-\") st.push(a - b);\n            else if (t == \"*\") st.push(a * b);\n            else if (t == \"/\") st.push(a / b);\n        } else {\n            st.push(stoi(t));\n        }\n    }\n    return st.top();\n}\n```"
        ),
        (
            "Implement Circular Queue with Dynamic Array",
            "Queues",
            "Medium",
            "Design a circular queue data structure supporting enQueue, deQueue, Front, Rear, isEmpty, and isFull without wasting buffer space.",
            "Modulo arithmetic `(rear + 1) % capacity`, ring buffer mechanics.",
            json.dumps([
                "Use front and rear pointers initialized to -1.",
                "When enqueueing: rear = (rear + 1) % size.",
                "When dequeueing: front = (front + 1) % size."
            ]),
            "Time Complexity: O(1) for all operations.\nSpace Complexity: O(K) where K is capacity.\n\nAll operations utilize (index + 1) % capacity to wrap around seamlessly."
        ),
        (
            "Binary Tree Level Order Traversal (BFS)",
            "Trees",
            "Medium",
            "Given the root of a binary tree, return the level order traversal of its nodes' values (from left to right, level by level).",
            "Breadth First Search using a FIFO queue.",
            json.dumps([
                "Push root to queue if not null.",
                "At each level, record `int levelSize = q.size()`.",
                "Pop exactly `levelSize` elements, collect values, and push their children."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(W) where W is max tree width.\n\n```cpp\nvector<vector<int>> levelOrder(TreeNode* root) {\n    vector<vector<int>> res;\n    if (!root) return res;\n    queue<TreeNode*> q;\n    q.push(root);\n    while (!q.empty()) {\n        int sz = q.size();\n        vector<int> level;\n        for (int i = 0; i < sz; i++) {\n            TreeNode* node = q.front(); q.pop();\n            level.push_back(node->val);\n            if (node->left) q.push(node->left);\n            if (node->right) q.push(node->right);\n        }\n        res.push_back(level);\n    }\n    return res;\n}\n```"
        ),
        (
            "Validate Binary Search Tree",
            "Binary Search Trees",
            "Medium",
            "Given the root of a binary tree, determine if it is a valid binary search tree (BST). Left subtree strictly less, right strictly greater.",
            "BST invariant property, range propagation (minVal, maxVal) or in-order sorted check.",
            json.dumps([
                "A node's value must be strictly within (minLimit, maxLimit).",
                "When going left, update maxLimit = node->val.",
                "When going right, update minLimit = node->val."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(H) call stack height.\n\n```cpp\nbool validate(TreeNode* node, long minVal, long maxVal) {\n    if (!node) return true;\n    if (node->val <= minVal || node->val >= maxVal) return false;\n    return validate(node->left, minVal, node->val) && validate(node->right, node->val, maxVal);\n}\n```"
        ),
        (
            "Lowest Common Ancestor in a Binary Search Tree",
            "Binary Search Trees",
            "Easy",
            "Given a binary search tree (BST), find the lowest common ancestor (LCA) node of two given nodes p and q.",
            "BST ordering property: split point where p and q diverge.",
            json.dumps([
                "If both p and q values are less than root, LCA lies in left subtree.",
                "If both p and q values are greater than root, LCA lies in right subtree.",
                "Otherwise, root is the split point and the LCA."
            ]),
            "Time Complexity: O(H) where H is tree height.\nSpace Complexity: O(1) iterative.\n\n```cpp\nTreeNode* lowestCommonAncestor(TreeNode* root, TreeNode* p, TreeNode* q) {\n    while (root) {\n        if (p->val < root->val && q->val < root->val) root = root->left;\n        else if (p->val > root->val && q->val > root->val) root = root->right;\n        else return root;\n    }\n    return nullptr;\n}\n```"
        ),
        (
            "Find Minimum in Rotated Sorted Array",
            "Review",
            "Medium",
            "Suppose an array of length n sorted in ascending order is rotated between 1 and n times. Find the minimum element in O(log n) time.",
            "Binary search on modified sorted partitions.",
            json.dumps([
                "Compare nums[mid] with nums[right].",
                "If nums[mid] > nums[right], minimum lies in right half: left = mid + 1.",
                "Otherwise minimum lies in left half including mid: right = mid."
            ]),
            "Time Complexity: O(log N).\nSpace Complexity: O(1).\n\n```cpp\nint findMin(vector<int>& nums) {\n    int left = 0, right = nums.size() - 1;\n    while (left < right) {\n        int mid = left + (right - left) / 2;\n        if (nums[mid] > nums[right]) left = mid + 1;\n        else right = mid;\n    }\n    return nums[left];\n}\n```"
        ),
        (
            "Implement Min Heap / Priority Queue",
            "Advanced Data Structures",
            "Medium",
            "Implement a binary Min-Heap supporting insert, extractMin, and heapify in O(log N) time using a standard 0-indexed vector.",
            "Complete binary tree array mapping: parent = (i-1)/2, left = 2i+1, right = 2i+2.",
            json.dumps([
                "Insert adds element at end and sifts up (bubble up) while smaller than parent.",
                "ExtractMin swaps root with last element, pops back, and sifts down (bubble down)."
            ]),
            "Time Complexity: Insert O(log N), ExtractMin O(log N), GetMin O(1).\nSpace: O(N)."
        ),
        (
            "Dijkstra's Shortest Path Algorithm",
            "Graphs",
            "Hard",
            "Given a weighted graph with non-negative edge weights and a source vertex, find the shortest path distances from source to all other vertices.",
            "Greedy vertex relaxation with min-priority queue (distance, vertex).",
            json.dumps([
                "Maintain dist[] array initialized to infinity, with dist[src] = 0.",
                "Use min-heap priority_queue<pair<int,int>, vector<pair<int,int>>, greater<>>.",
                "Relax edge (u, v, weight): if dist[u] + weight < dist[v], update dist[v] and push."
            ]),
            "Time Complexity: O((V + E) log V).\nSpace Complexity: O(V + E).\n\n```cpp\nvector<int> dijkstra(int V, vector<vector<pair<int,int>>>& adj, int S) {\n    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>> pq;\n    vector<int> dist(V, 1e9);\n    dist[S] = 0;\n    pq.push({0, S});\n    while (!pq.empty()) {\n        auto [d, u] = pq.top(); pq.pop();\n        if (d > dist[u]) continue;\n        for (auto& edge : adj[u]) {\n            int v = edge.first, w = edge.second;\n            if (dist[u] + w < dist[v]) {\n                dist[v] = dist[u] + w;\n                pq.push({dist[v], v});\n            }\n        }\n    }\n    return dist;\n}\n```"
        ),
        (
            "Connected Components in Undirected Graph (BFS/DFS)",
            "Graphs",
            "Easy",
            "Given n vertices and a list of undirected edges, find the total number of connected components in the graph.",
            "Graph traversal using visited boolean array.",
            json.dumps([
                "Build adjacency list.",
                "Iterate i from 0 to n-1. If vertex i is unvisited, launch BFS/DFS and increment component count."
            ]),
            "Time Complexity: O(V + E).\nSpace Complexity: O(V + E)."
        ),
        (
            "Longest Consecutive Sequence",
            "Advanced Data Structures",
            "Medium",
            "Given an unsorted array of integers, find the length of the longest consecutive elements sequence in O(N) time.",
            "Hash Set O(1) lookups, identifying sequence start points.",
            json.dumps([
                "Insert all elements into unordered_set.",
                "Only start counting sequence from `x` if `x - 1` does NOT exist in set.",
                "Count x+1, x+2... while present in set."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(N).\n\n```cpp\nint longestConsecutive(vector<int>& nums) {\n    unordered_set<int> s(nums.begin(), nums.end());\n    int maxLen = 0;\n    for (int num : s) {\n        if (!s.count(num - 1)) {\n            int curr = num, len = 1;\n            while (s.count(curr + 1)) { curr++; len++; }\n            maxLen = max(maxLen, len);\n        }\n    }\n    return maxLen;\n}\n```"
        ),
        (
            "Kth Largest Element in an Array",
            "Advanced Data Structures",
            "Medium",
            "Given an integer array nums and an integer k, return the kth largest element in the array without full sorting.",
            "Min-heap of fixed size K or Quickselect algorithm.",
            json.dumps([
                "Maintain a min-heap of size k.",
                "Push each element. If heap size exceeds k, pop the smallest element.",
                "After traversing array, heap top contains the kth largest element."
            ]),
            "Time Complexity: O(N log K).\nSpace Complexity: O(K).\n\n```cpp\nint findKthLargest(vector<int>& nums, int k) {\n    priority_queue<int, vector<int>, greater<int>> minHeap;\n    for (int num : nums) {\n        minHeap.push(num);\n        if (minHeap.size() > k) minHeap.pop();\n    }\n    return minHeap.top();\n}\n```"
        ),
        (
            "Course Schedule (Cycle Detection in Directed Graph)",
            "Graphs",
            "Medium",
            "There are a total of numCourses courses with prerequisites [a, b]. Return true if you can finish all courses without cyclical dependencies.",
            "Topological sort (Kahn's algorithm using in-degree array) or DFS coloring.",
            json.dumps([
                "Compute in-degree for every vertex.",
                "Enqueue all vertices with in-degree == 0.",
                "Pop vertex, decrement in-degree of its neighbors. If neighbor hits 0, enqueue it.",
                "If total popped vertices == numCourses, valid topological order exists."
            ]),
            "Time Complexity: O(V + E).\nSpace Complexity: O(V + E)."
        )
    ]

    for q in questions:
        hints_list = []
        try:
            hints_list = json.loads(q[5])
        except Exception:
            hints_list = []
        h1 = hints_list[0] if len(hints_list) > 0 else None
        h2 = hints_list[1] if len(hints_list) > 1 else None
        
        cursor.execute("""
            INSERT INTO dsa_questions (title, topic, difficulty, description, problem_statement, concept, hints_json, hint_1, hint_2, solution, solution_approach, solution_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (q[0], q[1], q[2], q[3], q[3], q[4], q[5], h1, h2, q[6], q[6], q[6]))
    conn.commit()

def seed_english_topics_if_empty(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM english_speaking_topics")
    if cursor.fetchone()["count"] > 0:
        return

    topics = [
        (
            "Technical Concept Explanation: How Hash Tables Handle Collisions",
            "Technical Concept",
            "Explain hash collisions, separate chaining, and open addressing in clear, structured English for 5-10 minutes.",
            json.dumps(["deterministic", "collision resolution", "chaining", "probe sequence", "load factor"]),
            json.dumps(["To begin with, a hash function maps keys to...", "The primary trade-off between chaining and open addressing is...", "In worst-case scenarios, performance degrades to..."]),
            json.dumps(["What happens when two distinct keys yield the same index?", "How would you explain the load factor to an interviewer?", "Which collision strategy is preferred in memory-constrained environments?"])
        ),
        (
            "Professional Self-Introduction for Engineering Interviews",
            "Self Introduction",
            "Deliver an articulate 2-3 minute elevator pitch covering your technical background, projects, and academic focus.",
            json.dumps(["specializing in", "proficient in", "hands-on experience", "enthusiastic about", "academic milestones"]),
            json.dumps(["Hello, my name is Aman. I am currently pursuing...", "Over the past semester, my core focus has been...", "What drives my interest in computer science is..."]),
            json.dumps(["How do your technical coursework and projects align with your goals?", "What is one technical challenge you recently overcame?"])
        ),
        (
            "Describing an Engineering Project and Problem Solved",
            "Project Discussion",
            "Explain an end-to-end software project: the problem statement, architectural choices, and technical hurdles.",
            json.dumps(["architecture", "modular design", "bottleneck", "optimization", "scalability"]),
            json.dumps(["The application was designed to solve...", "One significant bottleneck we encountered was...", "To mitigate this, we restructured the database schema..."]),
            json.dumps(["What made you select this specific technology stack?", "How did you measure the performance improvement?"])
        ),
        (
            "Expressing Opinions on AI in Software Development",
            "Opinions & Arguments",
            "Articulate balanced perspectives on how AI coding assistants affect foundational learning and developer productivity.",
            json.dumps(["augmentation", "syntactic sugar", "algorithmic thinking", "dependency", "paradigm shift"]),
            json.dumps(["From my vantage point...", "While AI accelerates boilerplate generation, it cannot substitute for...", "On the other hand, engineers must remain cautious of..."]),
            json.dumps(["Does AI reduce the need to master fundamental data structures?", "How should universities adapt examination formats?"])
        ),
        (
            "Explaining the Trade-off Between Time and Space Complexity",
            "Technical Concept",
            "Deliver an engaging monologue comparing time efficiency vs memory footprint with real-world examples.",
            json.dumps(["amortized", "memory footprint", "caching", "lookup latency", "in-place algorithm"]),
            json.dumps(["In computer science, optimal design is fundamentally about trade-offs...", "For instance, dynamic programming memoizes state to reduce...", "Conversely, in-place sorting minimizes memory at the expense of..."]),
            json.dumps(["Can you give an example where saving memory is more crucial than saving CPU cycles?"])
        ),
        (
            "Group Discussion: Building Consistency vs Burst Studying",
            "Group Discussion",
            "Practice persuasive argument structures supporting daily disciplined study over cramming before exams.",
            json.dumps(["spaced repetition", "cognitive load", "neuroplasticity", "burnout", "incremental mastery"]),
            json.dumps(["I would like to add to this point...", "Evidence clearly demonstrates that cramming results in rapid forgetting...", "Consistent daily allocation builds long-term retention..."]),
            json.dumps(["Why do students procrastinate even when aware of the risks?", "How does a daily study schedule prevent exam anxiety?"])
        ),
        (
            "Interview Question: Tell Me About a Time You Failed or Got Stuck",
            "Interview Questions",
            "Structure an authentic response using the STAR (Situation, Task, Action, Result) methodology in English.",
            json.dumps(["roadblock", "retrospective", "countermeasure", "resilience", "lessons learned"]),
            json.dumps(["A notable instance occurred when...", "The task required delivering...", "My action was to step back, profile the error logs, and...", "Ultimately, the result taught me that..."]),
            json.dumps(["What would you do differently if faced with the same roadblock today?"])
        ),
        (
            "Summarizing Today's Academic Learning in 5 Minutes",
            "Daily Reflection",
            "Summarize the key mathematical proof or data structure concept you studied today without looking at notes.",
            json.dumps(["fundamental theorem", "underlying principle", "edge case", "verification", "takeaway"]),
            json.dumps(["Today's core topic centered on...", "The most non-intuitive aspect was...", "By the end of the session, I was able to implement..."]),
            json.dumps(["What was the hardest problem you tackled today?", "How does today's concept connect to previous units?"])
        )
    ]

    for t in topics:
        cursor.execute("""
            INSERT INTO english_speaking_topics (title, category, objective, vocabulary_json, starter_phrases_json, prompt_questions_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, t)
    conn.commit()

def seed_quotes_if_empty(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM daily_quotes")
    if cursor.fetchone()["count"] > 0:
        return

    quotes = [
        ("Discipline is the bridge between goals and accomplishment.", "Consistency & Discipline", "Jim Rohn"),
        ("Honour your father and your mother: the blessing of parents is the silent foundation of every great victory.", "Parents & Gratitude", "Traditional Wisdom"),
        ("Trust in the Almighty with all your heart, and lean not on your own understanding. In all your ways acknowledge Him, and He shall direct your paths.", "Faith in God", "Spiritual Heritage"),
        ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Success & Perseverance", "Winston Churchill"),
        ("Verily, with hardship comes ease. Patience through the struggle is itself a quiet victory.", "Patience & Hope", "Timeless Reflection"),
        ("Small disciplines repeated with consistency every day lead to great achievements gained slowly over time.", "Consistency & Discipline", "John C. Maxwell"),
        ("Live as if you were to die tomorrow. Learn as if you were to live forever.", "Study & Learning", "Mahatma Gandhi"),
        ("Remember the sacrifices of those who believed in you when you had nothing to show. Work so hard that their sacrifices bear fruit.", "Parents & Gratitude", "Reflection"),
        ("When you plant seeds in the ground, you do not dig them up every day to see if they have grown. Have faith in your daily labor and trust the harvest.", "Patience & Hope", "Ancient Proverb"),
        ("An investment in knowledge pays the best interest.", "Study & Learning", "Benjamin Franklin"),
        ("The secret of your future is hidden in your daily routine.", "Consistency & Discipline", "Mike Murdock"),
        ("Do not pray for an easy life; pray for the strength to endure a difficult one and emerge with wisdom.", "Faith in God", "Spiritual Heritage"),
        ("He who moves a mountain begins by carrying away small stones.", "Success & Perseverance", "Confucius"),
        ("No legacy is so rich as honesty, humility, and gratitude toward your family.", "Parents & Gratitude", "Traditional Wisdom"),
        ("Difficulties in life do not come to destroy you, but to help you realize your hidden potential and power.", "Patience & Hope", "A.P.J. Abdul Kalam")
    ]

    for idx, q in enumerate(quotes):
        cursor.execute("""
            INSERT INTO daily_quotes (quote, quote_text, category, author, day_offset)
            VALUES (?, ?, ?, ?, ?)
        """, (q[0], q[0], q[1], q[2], idx))
    conn.commit()

# --- Wasted Time & Shortfall Accounting Helpers ---
def log_wasted_time(conn: sqlite3.Connection, log_date: str, minutes: int, reason: str = "", category: str = "Unproductive Time") -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO wasted_time_logs (log_date, minutes, reason, category)
        VALUES (?, ?, ?, ?)
    """, (log_date, minutes, reason, category))
    conn.commit()
    return cursor.lastrowid

def get_wasted_time_summary(conn: sqlite3.Connection, target_date: str) -> Dict[str, Any]:
    """Calculates confirmed wasted time, English shortfall, and missed study minutes for a given date and week."""
    cursor = conn.cursor()
    
    # 1. Confirmed wasted time for date
    cursor.execute("SELECT COALESCE(SUM(minutes), 0) as total FROM wasted_time_logs WHERE log_date = ?", (target_date,))
    confirmed_today = cursor.fetchone()["total"]

    # 2. English speaking shortfall for date (Target is 30m)
    cursor.execute("SELECT actual_minutes, shortfall_minutes, completed FROM daily_english_logs WHERE log_date = ? OR assigned_date = ?", (target_date, target_date))
    eng_row = cursor.fetchone()
    if eng_row:
        eng_actual = eng_row["actual_minutes"] or 0
        eng_shortfall = max(0, 30 - eng_actual)
    else:
        eng_actual = 0
        eng_shortfall = 30 # default shortfall if not practiced

    # 3. Missed scheduled academic study for date (Pending tasks that passed or incomplete portion)
    cursor.execute("""
        SELECT COALESCE(SUM(duration_minutes - actual_minutes), 0) as total_missed
        FROM study_schedules
        WHERE scheduled_date = ? AND status IN ('PENDING', 'MISSED', 'PARTIALLY_COMPLETED')
    """, (target_date,))
    missed_academic = cursor.fetchone()["total_missed"]

    # Calculate weekly bounds (Monday to Sunday)
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    except Exception:
        dt = date.today()
    week_start = dt - timedelta(days=dt.weekday())
    week_end = week_start + timedelta(days=6)
    w_start_str = week_start.strftime("%Y-%m-%d")
    w_end_str = week_end.strftime("%Y-%m-%d")

    # Weekly confirmed wasted
    cursor.execute("SELECT COALESCE(SUM(minutes), 0) as total FROM wasted_time_logs WHERE log_date BETWEEN ? AND ?", (w_start_str, w_end_str))
    weekly_confirmed = cursor.fetchone()["total"]

    # Weekly English shortfall
    cursor.execute("""
        SELECT log_date, COALESCE(actual_minutes, 0) as actual
        FROM daily_english_logs
        WHERE (log_date BETWEEN ? AND ?) OR (assigned_date BETWEEN ? AND ?)
    """, (w_start_str, w_end_str, w_start_str, w_end_str))
    logged_eng = {r["log_date"]: r["actual"] for r in cursor.fetchall()}
    
    weekly_eng_shortfall = 0
    cur_d = week_start
    while cur_d <= min(dt, week_end):
        d_str = cur_d.strftime("%Y-%m-%d")
        act = logged_eng.get(d_str, 0)
        weekly_eng_shortfall += max(0, 30 - act)
        cur_d += timedelta(days=1)

    # Weekly missed academic
    cursor.execute("""
        SELECT COALESCE(SUM(duration_minutes - actual_minutes), 0) as total_missed
        FROM study_schedules
        WHERE scheduled_date BETWEEN ? AND ? AND scheduled_date <= ? AND status IN ('PENDING', 'MISSED', 'PARTIALLY_COMPLETED')
    """, (w_start_str, w_end_str, target_date))
    weekly_missed_academic = cursor.fetchone()["total_missed"]

    total_today = confirmed_today + eng_shortfall + missed_academic
    total_week = weekly_confirmed + weekly_eng_shortfall + weekly_missed_academic

    return {
        "date": target_date,
        "confirmed_wasted_minutes": confirmed_today,
        "english_shortfall_minutes": eng_shortfall,
        "missed_academic_minutes": missed_academic,
        "total_unmet_minutes": total_today,
        "weekly_confirmed_wasted_minutes": weekly_confirmed,
        "weekly_english_shortfall_minutes": weekly_eng_shortfall,
        "weekly_missed_academic_minutes": weekly_missed_academic,
        "weekly_total_unmet_minutes": total_week,
        "week_range": f"{w_start_str} to {w_end_str}"
    }

def get_wasted_time_graph_data(conn: sqlite3.Connection, start_date_str: str, end_date_str: str) -> List[Dict[str, Any]]:
    """Returns day-wise time tracking for the wasted-time & shortfall graph."""
    cursor = conn.cursor()
    
    # Pre-fetch confirmed wasted logs
    cursor.execute("SELECT log_date, SUM(minutes) as total FROM wasted_time_logs WHERE log_date BETWEEN ? AND ? GROUP BY log_date", (start_date_str, end_date_str))
    confirmed_map = {r["log_date"]: r["total"] for r in cursor.fetchall()}

    # Pre-fetch English logs
    cursor.execute("SELECT COALESCE(log_date, assigned_date) as dt, actual_minutes FROM daily_english_logs WHERE (log_date BETWEEN ? AND ?) OR (assigned_date BETWEEN ? AND ?)", (start_date_str, end_date_str, start_date_str, end_date_str))
    eng_map = {r["dt"]: r["actual_minutes"] or 0 for r in cursor.fetchall()}

    # Pre-fetch academic planned, completed, missed
    cursor.execute("""
        SELECT 
            scheduled_date,
            SUM(duration_minutes) as planned,
            SUM(actual_minutes) as completed,
            SUM(CASE WHEN status IN ('PENDING', 'MISSED', 'PARTIALLY_COMPLETED') THEN (duration_minutes - actual_minutes) ELSE 0 END) as missed
        FROM study_schedules
        WHERE scheduled_date BETWEEN ? AND ?
        GROUP BY scheduled_date
    """, (start_date_str, end_date_str))
    sched_map = {r["scheduled_date"]: r for r in cursor.fetchall()}

    try:
        s_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        e_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except Exception:
        s_date = date.today() - timedelta(days=7)
        e_date = date.today() + timedelta(days=30)

    cur = s_date
    today = date.today()
    result = []
    while cur <= e_date:
        d_str = cur.strftime("%Y-%m-%d")
        is_future = cur > today
        
        conf = confirmed_map.get(d_str, 0)
        
        if is_future:
            # Future days do not have confirmed wasted or missed historical shortfall
            eng_shortfall = 0
            missed = 0
            conf = 0
        else:
            eng_act = eng_map.get(d_str, None)
            eng_shortfall = max(0, 30 - eng_act) if eng_act is not None else 30
            sched = sched_map.get(d_str)
            missed = sched["missed"] if sched else 0

        sched_info = sched_map.get(d_str)
        planned = sched_info["planned"] if sched_info else 240
        completed = sched_info["completed"] if sched_info else 0

        result.append({
            "date": d_str,
            "weekday": cur.strftime("%a"),
            "is_future": is_future,
            "confirmed_wasted_minutes": conf,
            "english_shortfall_minutes": eng_shortfall,
            "missed_academic_minutes": missed,
            "total_unmet_minutes": conf + eng_shortfall + missed,
            "planned_academic_minutes": planned,
            "completed_academic_minutes": completed
        })
        cur += timedelta(days=1)
    return result

# --- Authoritative DSA Topics Rotation (CSN 3001 Syllabus) ---
OFFICIAL_DSA_TOPICS = [
    {"topic": "Linked Lists (Singly, Doubly & Circular)", "unit": "Unit 2"},
    {"topic": "Stacks & Infix-Postfix Conversion", "unit": "Unit 3"},
    {"topic": "Queues & Job Scheduling in CPU", "unit": "Unit 4"},
    {"topic": "Binary Trees & BFS/DFS Traversals", "unit": "Unit 5"},
    {"topic": "Binary Search Trees (BST & AVL Trees)", "unit": "Unit 6"},
    {"topic": "Graphs & Graph Traversals (BFS, DFS)", "unit": "Unit 7"},
    {"topic": "Shortest Paths (Dijkstra) & Minimum Spanning Trees (Prim/Kruskal)", "unit": "Unit 7"},
    {"topic": "Heaps & Priority Queues", "unit": "Unit 8"},
    {"topic": "Hashing & Collision Resolution", "unit": "Unit 8"},
    {"topic": "Recursion & Algorithm Complexity Analysis", "unit": "Unit 1"}
]

def get_daily_dsa_topics(conn: sqlite3.Connection, target_date: str) -> Dict[str, Any]:
    """Returns exactly two syllabus-aligned DSA topic recommendations for the day."""
    cursor = conn.cursor()
    
    # Check if assignments already exist for date
    cursor.execute("""
        SELECT id, assigned_date, slot_number, status, topic_name, time_spent_minutes, mistakes_notes as notes, completed_at
        FROM daily_dsa_assignments
        WHERE assigned_date = ?
        ORDER BY slot_number ASC
    """, (target_date,))
    existing = [dict(r) for r in cursor.fetchall()]

    if len(existing) >= 2:
        return {
            "date": target_date,
            "topics": existing,
            "is_completed": all(t["status"] == "Solved" for t in existing),
            "completed_count": sum(1 for t in existing if t["status"] == "Solved")
        }

    # Deterministic rotation based on day offset
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    except Exception:
        dt = date.today()
    day_idx = (dt - date(2026, 1, 1)).days

    t1_info = OFFICIAL_DSA_TOPICS[(day_idx * 2) % len(OFFICIAL_DSA_TOPICS)]
    t2_info = OFFICIAL_DSA_TOPICS[(day_idx * 2 + 1) % len(OFFICIAL_DSA_TOPICS)]

    # Fetch dummy question IDs or create placeholder assignments
    cursor.execute("SELECT id FROM dsa_questions LIMIT 2")
    q_rows = cursor.fetchall()
    q1_id = q_rows[0]["id"] if q_rows else 1
    q2_id = q_rows[1]["id"] if len(q_rows) > 1 else 2

    # Insert or update slot 1
    cursor.execute("""
        INSERT OR IGNORE INTO daily_dsa_assignments (assigned_date, question_id, slot_number, topic_name, status)
        VALUES (?, ?, 1, ?, 'Pending')
    """, (target_date, q1_id, f"{t1_info['unit']}: {t1_info['topic']}"))
    
    # Insert or update slot 2
    cursor.execute("""
        INSERT OR IGNORE INTO daily_dsa_assignments (assigned_date, question_id, slot_number, topic_name, status)
        VALUES (?, ?, 2, ?, 'Pending')
    """, (target_date, q2_id, f"{t2_info['unit']}: {t2_info['topic']}"))
    conn.commit()

    cursor.execute("""
        SELECT id, assigned_date, slot_number, status, topic_name, time_spent_minutes, mistakes_notes as notes, completed_at
        FROM daily_dsa_assignments
        WHERE assigned_date = ?
        ORDER BY slot_number ASC
    """, (target_date,))
    items = [dict(r) for r in cursor.fetchall()]

    return {
        "date": target_date,
        "topics": items,
        "is_completed": all(t["status"] == "Solved" for t in items),
        "completed_count": sum(1 for t in items if t["status"] == "Solved")
    }

def update_daily_dsa_topic(conn: sqlite3.Connection, assignment_id: int, status: str = "Solved", time_spent_minutes: int = 0, notes: str = "", is_completed: Optional[bool] = None) -> Dict[str, Any]:
    cursor = conn.cursor()
    if is_completed is not None:
        status = "Solved" if is_completed else "Pending"
    now_str = datetime.now().isoformat() if status == "Solved" else None
    cursor.execute("""
        UPDATE daily_dsa_assignments
        SET status = ?, time_spent_minutes = ?, mistakes_notes = ?, completed_at = ?
        WHERE id = ?
    """, (status, time_spent_minutes, notes, now_str, assignment_id))
    conn.commit()
    cursor.execute("SELECT * FROM daily_dsa_assignments WHERE id = ?", (assignment_id,))
    row = cursor.fetchone()
    return dict(row) if row else {"id": assignment_id, "status": status}

# --- Simple English Practice Logging ---
def get_english_status_today(conn: sqlite3.Connection, target_date: str) -> Dict[str, Any]:
    cursor = conn.cursor()
    
    # Topic of the day for guidance
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    except Exception:
        dt = date.today()
    cursor.execute("SELECT id, title, category, objective FROM english_speaking_topics ORDER BY id ASC")
    all_topics = cursor.fetchall()
    topic = dict(all_topics[((dt - date(2026, 1, 1)).days) % len(all_topics)]) if all_topics else {
        "id": 1, "title": "Technical Concept Explanation", "category": "Technical", "objective": "Explain a concept clearly in English."
    }

    cursor.execute("""
        SELECT id, log_date, actual_minutes, shortfall_minutes, completed, is_completed, notes, completed_at
        FROM daily_english_logs
        WHERE log_date = ? OR assigned_date = ?
    """, (target_date, target_date))
    log = cursor.fetchone()

    # Calculate streak
    streak = 0
    cur_d = dt - timedelta(days=1)
    while True:
        d_str = cur_d.strftime("%Y-%m-%d")
        cursor.execute("SELECT completed, is_completed, actual_minutes FROM daily_english_logs WHERE (log_date = ? OR assigned_date = ?) AND (completed = 1 OR is_completed = 1 OR actual_minutes >= 20)", (d_str, d_str))
        r = cursor.fetchone()
        if r:
            streak += 1
            cur_d -= timedelta(days=1)
        else:
            break

    if log and (log["completed"] or log["is_completed"]):
        streak += 1

    actual_mins = log["actual_minutes"] if log and log["actual_minutes"] is not None else (30 if log and log["completed"] else 0)
    shortfall = max(0, 30 - actual_mins)
    is_done = actual_mins >= 30 or (log and bool(log["completed"]))

    return {
        "date": target_date,
        "target_minutes": 30,
        "actual_minutes": actual_mins,
        "shortfall_minutes": shortfall,
        "is_completed": is_done,
        "notes": log["notes"] if log else "",
        "streak_days": streak,
        "topic": topic
    }

def save_english_practice(conn: sqlite3.Connection, log_date: str, actual_minutes: int, notes: str = "") -> Dict[str, Any]:
    cursor = conn.cursor()
    shortfall = max(0, 30 - actual_minutes)
    is_completed = 1 if actual_minutes >= 30 else (1 if actual_minutes > 0 else 0)
    now_str = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO daily_english_logs (assigned_date, log_date, topic_id, duration_seconds, actual_minutes, shortfall_minutes, completed, is_completed, notes, completed_at)
        VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(assigned_date) DO UPDATE SET
            actual_minutes = excluded.actual_minutes,
            shortfall_minutes = excluded.shortfall_minutes,
            duration_seconds = excluded.duration_seconds,
            completed = excluded.completed,
            is_completed = excluded.is_completed,
            notes = excluded.notes,
            completed_at = excluded.completed_at
    """, (log_date, log_date, actual_minutes * 60, actual_minutes, shortfall, is_completed, is_completed, notes, now_str))
    conn.commit()

    return get_english_status_today(conn, log_date)


# =====================================================================
# --- TIMETABLE SHIFTS, RESCHEDULING & REAL-TIME STUDY MANAGEMENT ---
# =====================================================================

def get_daily_study_plan(conn: sqlite3.Connection, target_date: str) -> Dict[str, Any]:
    """
    Returns the day's study plan with 5 academic shifts + 1 wrap-up block.
    Distinguishes scheduled, completed, partially completed, overdue, and rescheduled tasks.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            s.id, s.scheduled_date, s.original_date, s.shift_number, s.duration_minutes,
            s.remaining_minutes, s.actual_minutes, s.status, s.task_type, s.priority,
            s.task_description, s.unit_name, s.notes, s.is_wrapup, s.is_interrupted,
            s.rescheduled_count, s.rescheduled_reason, s.completed_at,
            subj.id as subject_id, subj.code as subject_code, subj.name as subject_name, subj.color as subject_color,
            top.id as topic_id, top.title as topic_title, top.mastery_level, top.difficulty_level, top.needs_revision,
            u.id as unit_id, u.unit_number, u.title as unit_title
        FROM study_schedules s
        LEFT JOIN subjects subj ON s.subject_id = subj.id
        LEFT JOIN topics top ON s.topic_id = top.id
        LEFT JOIN units u ON top.unit_id = u.id
        WHERE s.scheduled_date = ?
        ORDER BY s.is_wrapup ASC, s.shift_number ASC
    """, (target_date,))
    rows = [dict(r) for r in cursor.fetchall()]

    shifts = [r for r in rows if not r.get("is_wrapup")]
    wrapups = [r for r in rows if r.get("is_wrapup")]

    # Calculate daily statistics
    acad_completed = sum(r["actual_minutes"] or 0 for r in shifts)
    acad_planned = sum(r["duration_minutes"] or 45 for r in shifts)
    acad_target = int(get_setting(conn, "daily_academic_target_minutes", 240))
    acad_remaining = max(0, acad_target - acad_completed)
    completed_shifts_count = sum(1 for r in shifts if r["status"] == "COMPLETED")
    wrapup_done = any(w["status"] == "COMPLETED" or (w["actual_minutes"] or 0) > 0 for w in wrapups)

    # Workload warning if planned > 240
    is_overloaded = acad_planned > 240

    return {
        "date": target_date,
        "academic_target_minutes": acad_target,
        "academic_completed_minutes": acad_completed,
        "academic_planned_minutes": acad_planned,
        "academic_remaining_minutes": acad_remaining,
        "academic_progress_pct": min(100.0, round((acad_completed / acad_target) * 100, 2)) if acad_target > 0 else 0,
        "extra_academic_minutes": max(0, acad_completed - acad_target),
        "shifts_total": len(shifts),
        "shifts_completed": completed_shifts_count,
        "wrapup_completed": wrapup_done,
        "is_overloaded": is_overloaded,
        "shifts": shifts,
        "wrapup": wrapups[0] if wrapups else None
    }

def complete_study_shift(conn: sqlite3.Connection, schedule_id: int, actual_minutes: int = 45, notes: Optional[str] = None) -> Dict[str, Any]:
    """Marks a study shift as completed, records session history, updates topic progress."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM study_schedules WHERE id = ?", (schedule_id,))
    shift = cursor.fetchone()
    if not shift:
        raise ValueError(f"Study schedule with ID {schedule_id} not found.")

    shift_dict = dict(shift)
    now_iso = datetime.now().isoformat()
    final_actual = actual_minutes if actual_minutes is not None else shift_dict.get("duration_minutes", 45)
    existing_notes = shift_dict.get("notes") or ""
    final_notes = f"{existing_notes} {notes}".strip() if notes else existing_notes

    cursor.execute("""
        UPDATE study_schedules SET
            status = 'COMPLETED',
            actual_minutes = ?,
            remaining_minutes = 0,
            completion_percentage = 100,
            completed_at = ?,
            notes = ?
        WHERE id = ?
    """, (final_actual, now_iso, final_notes, schedule_id))

    # Record persistent study session
    cursor.execute("""
        INSERT INTO study_sessions (
            topic_id, schedule_id, started_at, ended_at, duration_seconds,
            actual_minutes, notes, completion_percentage
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 100)
    """, (
        shift_dict.get("topic_id", 1), schedule_id, now_iso, now_iso,
        final_actual * 60, final_actual, final_notes
    ))

    # Update topic last studied
    if shift_dict.get("topic_id"):
        cursor.execute("UPDATE topics SET last_studied_at = ? WHERE id = ?", (now_iso, shift_dict["topic_id"]))

    conn.commit()

    # Varied motivational message
    import random
    messages = [
        "Great work! One more step forward.",
        "Excellent consistency. Keep going!",
        "You completed this shift. Build on that progress.",
        "Small steps every day create real progress.",
        "Discipline in action. Outstanding effort!",
        "Another milestone reached today. Keep the momentum!",
        "Quality focus session completed. Proud of your commitment."
    ]
    appreciation = random.choice(messages)

    return {
        "status": "success",
        "success": True,
        "schedule_id": schedule_id,
        "shift_status": "COMPLETED",
        "actual_minutes": final_actual,
        "appreciation": appreciation
    }

def partially_complete_study_shift(conn: sqlite3.Connection, schedule_id: int, actual_minutes: int, notes: Optional[str] = None, is_interrupted: bool = False) -> Dict[str, Any]:
    """Records partial study progress for a shift and updates remaining duration."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM study_schedules WHERE id = ?", (schedule_id,))
    shift = cursor.fetchone()
    if not shift:
        raise ValueError(f"Study schedule with ID {schedule_id} not found.")

    shift_dict = dict(shift)
    dur = shift_dict.get("duration_minutes", 45)

    if actual_minutes >= dur:
        return complete_study_shift(conn, schedule_id, actual_minutes, notes)

    remaining = max(0, dur - actual_minutes)
    pct = int((actual_minutes / dur) * 100) if dur > 0 else 0
    now_iso = datetime.now().isoformat()
    existing_notes = shift_dict.get("notes") or ""
    final_notes = f"{existing_notes} {notes}".strip() if notes else existing_notes

    cursor.execute("""
        UPDATE study_schedules SET
            status = 'PARTIALLY_COMPLETED',
            actual_minutes = ?,
            remaining_minutes = ?,
            completion_percentage = ?,
            is_interrupted = ?,
            notes = ?
        WHERE id = ?
    """, (actual_minutes, remaining, pct, 1 if is_interrupted else 0, final_notes, schedule_id))

    # Record persistent study session for the actual time spent
    cursor.execute("""
        INSERT INTO study_sessions (
            topic_id, schedule_id, started_at, ended_at, duration_seconds,
            actual_minutes, notes, completion_percentage
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        shift_dict.get("topic_id", 1), schedule_id, now_iso, now_iso,
        actual_minutes * 60, actual_minutes, final_notes, pct
    ))

    conn.commit()

    return {
        "status": "partial_success",
        "success": True,
        "schedule_id": schedule_id,
        "shift_status": "PARTIALLY_COMPLETED",
        "actual_minutes": actual_minutes,
        "remaining_minutes": remaining,
        "completion_percentage": pct,
        "is_interrupted": is_interrupted
    }

def reschedule_study_shift(conn: sqlite3.Connection, schedule_id: int, to_date: str, reason: str = "Unfinished task moved") -> Dict[str, Any]:
    """Reschedules a study shift to a future date while preserving original planned date and tracking history."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM study_schedules WHERE id = ?", (schedule_id,))
    shift = cursor.fetchone()
    if not shift:
        raise ValueError(f"Study schedule with ID {schedule_id} not found.")

    shift_dict = dict(shift)
    orig_date = shift_dict.get("original_date") or shift_dict["scheduled_date"]
    from_date = shift_dict["scheduled_date"]

    # Record in history table
    cursor.execute("""
        INSERT INTO rescheduled_history (schedule_id, original_date, from_date, to_date, reason, status)
        VALUES (?, ?, ?, ?, ?, 'ACTIVE')
    """, (schedule_id, orig_date, from_date, to_date, reason))
    history_id = cursor.lastrowid

    # Update schedule row
    new_count = (shift_dict.get("rescheduled_count") or 0) + 1
    cursor.execute("""
        UPDATE study_schedules SET
            scheduled_date = ?,
            original_date = ?,
            rescheduled_count = ?,
            rescheduled_reason = ?,
            status = 'PENDING'
        WHERE id = ?
    """, (to_date, orig_date, new_count, reason, schedule_id))

    # Check future day load
    cursor.execute("SELECT COALESCE(SUM(duration_minutes), 0) as total FROM study_schedules WHERE scheduled_date = ? AND is_wrapup = 0", (to_date,))
    future_load = cursor.fetchone()["total"]
    conn.commit()

    is_overloaded = future_load > 240
    return {
        "status": "rescheduled",
        "success": True,
        "schedule_id": schedule_id,
        "history_id": history_id,
        "original_date": orig_date,
        "from_date": from_date,
        "to_date": to_date,
        "new_date": to_date,
        "target_day_workload_minutes": future_load,
        "target_day_overloaded": is_overloaded,
        "warning": f"Target date {to_date} now has {future_load}m of planned academic study (Target: 240m)." if is_overloaded else None
    }

def undo_reschedule_shift(conn: sqlite3.Connection, history_id: int) -> Dict[str, Any]:
    """Undoes a previous rescheduling action and restores the shift to its previous date."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rescheduled_history WHERE id = ?", (history_id,))
    hist = cursor.fetchone()
    if not hist:
        raise ValueError(f"Rescheduling history record with ID {history_id} not found.")

    h_dict = dict(hist)
    if h_dict["status"] == "UNDONE":
        return {"status": "already_undone", "success": False, "message": "This rescheduling action was already undone."}

    # Restore schedule to from_date
    cursor.execute("""
        UPDATE study_schedules SET
            scheduled_date = ?
        WHERE id = ?
    """, (h_dict["from_date"], h_dict["schedule_id"]))

    cursor.execute("UPDATE rescheduled_history SET status = 'UNDONE' WHERE id = ?", (history_id,))
    conn.commit()

    return {
        "status": "undone",
        "success": True,
        "schedule_id": h_dict["schedule_id"],
        "restored_to_date": h_dict["from_date"]
    }

def get_rescheduled_tasks(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Returns all rescheduled tasks with original dates, new dates, and reasons."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            h.id as history_id, h.id as latest_history_id, h.schedule_id, h.schedule_id as id, h.original_date, h.from_date, h.to_date, h.reason,
            h.status as history_status, h.created_at as rescheduled_at,
            s.task_description, s.duration_minutes, s.actual_minutes, s.status as current_status,
            subj.code as subject_code, subj.name as subject_name, subj.color as subject_color
        FROM rescheduled_history h
        JOIN study_schedules s ON h.schedule_id = s.id
        LEFT JOIN subjects subj ON s.subject_id = subj.id
        ORDER BY h.created_at DESC
    """)
    return [dict(r) for r in cursor.fetchall()]

def auto_reschedule_overdue_tasks(conn: sqlite3.Connection, current_date_str: str) -> Dict[str, Any]:
    """
    Deterministic automatic rescheduling:
    Moves any uncompleted academic shifts from past dates (< current_date_str)
    to future slots, prioritizing Discrete Structures (CSN 3003).
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.scheduled_date, s.original_date, s.duration_minutes, s.remaining_minutes,
               s.task_description, subj.code as subject_code
        FROM study_schedules s
        JOIN subjects subj ON s.subject_id = subj.id
        WHERE s.scheduled_date < ? 
          AND s.status IN ('PENDING', 'PARTIALLY_COMPLETED')
          AND s.is_wrapup = 0
        ORDER BY 
            CASE WHEN subj.code = 'CSN 3003' THEN 1 ELSE 2 END ASC,
            s.scheduled_date ASC, s.shift_number ASC
    """, (current_date_str,))
    overdue_shifts = [dict(r) for r in cursor.fetchall()]

    if not overdue_shifts:
        return {"status": "no_overdue", "moved_count": 0, "messages": ["No overdue unfinished shifts found."]}

    # Target date: move to current_date_str backlog
    moved_count = 0
    warnings = []
    for shift in overdue_shifts:
        orig = shift.get("original_date") or shift["scheduled_date"]
        # Reschedule to current date
        cursor.execute("""
            INSERT INTO rescheduled_history (schedule_id, original_date, from_date, to_date, reason, status)
            VALUES (?, ?, ?, ?, 'Automated end-of-day backlog roll-forward', 'ACTIVE')
        """, (shift["id"], orig, shift["scheduled_date"], current_date_str))

        cursor.execute("""
            UPDATE study_schedules SET
                scheduled_date = ?,
                original_date = ?,
                rescheduled_count = rescheduled_count + 1,
                rescheduled_reason = 'Automated backlog reschedule'
            WHERE id = ?
        """, (current_date_str, orig, shift["id"]))
        moved_count += 1

    # Check workload on current date
    cursor.execute("SELECT COALESCE(SUM(duration_minutes), 0) as total FROM study_schedules WHERE scheduled_date = ? AND is_wrapup = 0", (current_date_str,))
    day_load = cursor.fetchone()["total"]
    conn.commit()

    if day_load > 240:
        warnings.append(f"Day {current_date_str} is currently overloaded with {day_load}m of study tasks. Consider spreading backlog items across subsequent days.")

    return {
        "status": "success",
        "moved_count": moved_count,
        "target_date": current_date_str,
        "day_workload_minutes": day_load,
        "warnings": warnings
    }

# =====================================================================
# --- TOTAL STUDY TIME COUNTER & SESSION AUDIT ---
# =====================================================================

def get_cumulative_study_totals(conn: sqlite3.Connection, target_date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculates cumulative study time across all categories from real saved records:
    Academic Study, DSA Practice, English Speaking, Wrap-up/Revision.
    Avoids double-counting and separates paused/wasted time.
    """
    cursor = conn.cursor()
    ref_date_str = target_date_str or datetime.now().strftime("%Y-%m-%d")

    # 1. Total Academic Study Time (study_schedules is_wrapup = 0)
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM study_schedules WHERE is_wrapup = 0")
    total_academic_mins = cursor.fetchone()["total"]

    # 2. Total DSA Practice Time (daily_dsa_assignments)
    cursor.execute("SELECT COALESCE(SUM(time_spent_minutes), 0) as total FROM daily_dsa_assignments WHERE status = 'Solved'")
    total_dsa_mins = cursor.fetchone()["total"]

    # 3. Total English Speaking Time (daily_english_logs)
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM daily_english_logs")
    total_english_mins = cursor.fetchone()["total"]

    # 4. Total Wrap-up & Revision Time
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM study_schedules WHERE is_wrapup = 1 OR task_type = 'REVISION'")
    total_wrapup_mins = cursor.fetchone()["total"]

    # Today's academic study time
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM study_schedules WHERE scheduled_date = ? AND is_wrapup = 0", (ref_date_str,))
    today_academic_mins = cursor.fetchone()["total"]

    # This week's study time (Monday to Sunday)
    try:
        dt = datetime.strptime(ref_date_str, "%Y-%m-%d").date()
    except Exception:
        dt = date.today()
    w_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
    w_end = (dt - timedelta(days=dt.weekday()) + timedelta(days=6)).strftime("%Y-%m-%d")
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM study_schedules WHERE scheduled_date BETWEEN ? AND ? AND is_wrapup = 0", (w_start, w_end))
    week_academic_mins = cursor.fetchone()["total"]

    # This month's study time
    m_prefix = ref_date_str[:7]
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM study_schedules WHERE scheduled_date LIKE ? AND is_wrapup = 0", (f"{m_prefix}%",))
    month_academic_mins = cursor.fetchone()["total"]

    # Study time since timetable start (2026-10-27)
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM study_schedules WHERE scheduled_date >= '2026-10-27' AND is_wrapup = 0")
    timetable_academic_mins = cursor.fetchone()["total"]

    # Helper formatter
    def fmt(mins: int) -> str:
        h = mins // 60
        m = mins % 60
        if h == 0:
            return f"{m} minutes"
        elif m == 0:
            return f"{h} hours"
        return f"{h} hours {m} minutes"

    # Recent session history for audit
    cursor.execute("""
        SELECT sess.id, sess.started_at, sess.duration_seconds, sess.actual_minutes, sess.notes,
               top.title as topic_title, subj.name as subject_name, subj.code as subject_code
        FROM study_sessions sess
        LEFT JOIN topics top ON sess.topic_id = top.id
        LEFT JOIN subjects subj ON top.subject_id = subj.id
        ORDER BY sess.id DESC
        LIMIT 30
    """)
    recent_sessions = [dict(r) for r in cursor.fetchall()]

    grand_total_mins = total_academic_mins + total_dsa_mins + total_english_mins + total_wrapup_mins

    return {
        "grand_total_minutes": grand_total_mins,
        "grand_total_formatted": fmt(grand_total_mins),
        "total_academic_minutes": total_academic_mins,
        "total_dsa_minutes": total_dsa_mins,
        "total_english_minutes": total_english_mins,
        "total_wrapup_minutes": total_wrapup_mins,
        "academic": {
            "total_minutes": total_academic_mins,
            "formatted": fmt(total_academic_mins),
            "today_minutes": today_academic_mins,
            "today_formatted": fmt(today_academic_mins),
            "week_minutes": week_academic_mins,
            "week_formatted": fmt(week_academic_mins),
            "month_minutes": month_academic_mins,
            "month_formatted": fmt(month_academic_mins),
            "timetable_since_oct27_minutes": timetable_academic_mins,
            "timetable_since_oct27_formatted": fmt(timetable_academic_mins)
        },
        "dsa": {
            "total_minutes": total_dsa_mins,
            "formatted": fmt(total_dsa_mins)
        },
        "english": {
            "total_minutes": total_english_mins,
            "formatted": fmt(total_english_mins)
        },
        "wrapup_revision": {
            "total_minutes": total_wrapup_mins,
            "formatted": fmt(total_wrapup_mins)
        },
        "recent_sessions": recent_sessions
    }

# =====================================================================
# --- WASTED TIME & SHORTFALL SEPARATION ---
# =====================================================================

def get_enhanced_wasted_time_summary(conn: sqlite3.Connection, target_date: str) -> Dict[str, Any]:
    """
    Clearly distinguishes:
    1. Confirmed Wasted Time (manually logged unproductive/distracted minutes)
    2. Academic Target Shortfall (max(0, 240 - actual_study))
    3. Unfinished Scheduled Work (planned tasks remaining)
    4. Unaccounted Time
    Never conflates them into a single misleading metric.
    """
    cursor = conn.cursor()

    # Confirmed Wasted Time Today
    cursor.execute("SELECT COALESCE(SUM(minutes), 0) as total FROM wasted_time_logs WHERE log_date = ?", (target_date,))
    confirmed_today = cursor.fetchone()["total"]

    # Calculate weekly bounds (Monday to Sunday)
    try:
        dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    except Exception:
        dt = date.today()
    w_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
    w_end = (dt - timedelta(days=dt.weekday()) + timedelta(days=6)).strftime("%Y-%m-%d")
    m_prefix = target_date[:7]

    # Weekly & Monthly Confirmed Wasted
    cursor.execute("SELECT COALESCE(SUM(minutes), 0) as total FROM wasted_time_logs WHERE log_date BETWEEN ? AND ?", (w_start, w_end))
    confirmed_week = cursor.fetchone()["total"]

    cursor.execute("SELECT COALESCE(SUM(minutes), 0) as total FROM wasted_time_logs WHERE log_date LIKE ?", (f"{m_prefix}%",))
    confirmed_month = cursor.fetchone()["total"]

    # Academic Target Shortfall Today
    acad_target = int(get_setting(conn, "daily_academic_target_minutes", 240))
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM study_schedules WHERE scheduled_date = ? AND is_wrapup = 0", (target_date,))
    acad_actual = cursor.fetchone()["total"]
    shortfall_today = max(0, acad_target - acad_actual)

    # Weekly academic shortfall
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM study_schedules WHERE scheduled_date BETWEEN ? AND ? AND scheduled_date <= ? AND is_wrapup = 0", (w_start, w_end, target_date))
    days_elapsed_in_week = (dt.weekday() + 1)
    week_target = acad_target * days_elapsed_in_week
    week_actual = cursor.fetchone()["total"]
    shortfall_week = max(0, week_target - week_actual)

    # Unfinished scheduled work (minutes left on today's tasks)
    cursor.execute("""
        SELECT COALESCE(SUM(remaining_minutes), 0) as total
        FROM study_schedules
        WHERE scheduled_date = ? AND status != 'COMPLETED' AND is_wrapup = 0
    """, (target_date,))
    unfinished_today = cursor.fetchone()["total"]

    # List of individual wasted logs for today
    cursor.execute("""
        SELECT id, log_date, minutes, reason, category, notes, created_at
        FROM wasted_time_logs
        WHERE log_date = ?
        ORDER BY id DESC
    """, (target_date,))
    logs_today = [dict(r) for r in cursor.fetchall()]

    today_summary = {
        "confirmed_wasted_minutes": confirmed_today,
        "academic_shortfall_minutes": shortfall_today,
        "academic_target_minutes": acad_target,
        "academic_actual_minutes": acad_actual,
        "unfinished_scheduled_minutes": unfinished_today
    }

    return {
        "date": target_date,
        "week_range": f"{w_start} to {w_end}",
        "today": today_summary,
        "recent_logs": logs_today,
        "confirmed_wasted": {
            "today_minutes": confirmed_today,
            "week_minutes": confirmed_week,
            "month_minutes": confirmed_month
        },
        "academic_shortfall": {
            "target_minutes": acad_target,
            "actual_minutes": acad_actual,
            "shortfall_today_minutes": shortfall_today,
            "week_target_minutes": week_target,
            "week_actual_minutes": week_actual,
            "shortfall_week_minutes": shortfall_week
        },
        "unfinished_scheduled_work_minutes": unfinished_today,
        "logs": logs_today,
        "explanation": "Confirmed wasted time is explicitly recorded unproductive time. Target shortfall is simply unstudied time below your 4-hour target. They are tracked separately to avoid double-counting."
    }

def delete_wasted_time_log(conn: sqlite3.Connection, log_id: int) -> bool:
    """Deletes a mistakenly logged wasted time entry."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM wasted_time_logs WHERE id = ?", (log_id,))
    conn.commit()
    return cursor.rowcount > 0

# =====================================================================
# --- HANDOUTS & SYLLABUS MANAGEMENT ---
# =====================================================================

def add_handout(conn: sqlite3.Connection, filename: str, original_filename: str, file_type: str, file_size: int, subject_id: int, unit_id: Optional[int], topic_id: Optional[int], file_path: str, notes: Optional[str] = None) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO handouts (filename, original_filename, file_type, file_size, subject_id, unit_id, topic_id, file_path, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (filename, original_filename, file_type.lower(), file_size, subject_id, unit_id, topic_id, file_path, notes))
    conn.commit()
    return cursor.lastrowid

def get_handouts(conn: sqlite3.Connection, subject_id: Optional[int] = None, unit_id: Optional[int] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    query = """
        SELECT 
            h.id, h.filename, h.original_filename, h.file_type, h.file_size, h.file_path,
            h.upload_date, h.notes,
            s.id as subject_id, s.code as subject_code, s.name as subject_name, s.color as subject_color,
            u.id as unit_id, u.unit_number, u.title as unit_title,
            t.id as topic_id, t.title as topic_title
        FROM handouts h
        LEFT JOIN subjects s ON h.subject_id = s.id
        LEFT JOIN units u ON h.unit_id = u.id
        LEFT JOIN topics t ON h.topic_id = t.id
        WHERE 1=1
    """
    params = []
    if subject_id:
        query += " AND h.subject_id = ?"
        params.append(subject_id)
    if unit_id:
        query += " AND h.unit_id = ?"
        params.append(unit_id)
    if search:
        query += " AND (h.original_filename LIKE ? OR h.notes LIKE ? OR t.title LIKE ?)"
        s_term = f"%{search}%"
        params.extend([s_term, s_term, s_term])

    query += " ORDER BY h.id DESC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]

def get_handout_by_id(conn: sqlite3.Connection, handout_id: int) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.*, s.code as subject_code, s.name as subject_name
        FROM handouts h
        LEFT JOIN subjects s ON h.subject_id = s.id
        WHERE h.id = ?
    """, (handout_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

def update_handout(conn: sqlite3.Connection, handout_id: int, original_filename: Optional[str] = None, subject_id: Optional[int] = None, unit_id: Optional[int] = None, topic_id: Optional[int] = None, notes: Optional[str] = None) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM handouts WHERE id = ?", (handout_id,))
    if not cursor.fetchone():
        return False
    
    updates = []
    params = []
    if original_filename is not None:
        updates.append("original_filename = ?")
        params.append(original_filename)
    if subject_id is not None:
        updates.append("subject_id = ?")
        params.append(subject_id)
    if unit_id is not None:
        updates.append("unit_id = ?")
        params.append(unit_id)
    if topic_id is not None:
        updates.append("topic_id = ?")
        params.append(topic_id)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)

    if updates:
        params.append(handout_id)
        cursor.execute(f"UPDATE handouts SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    return True

def delete_handout(conn: sqlite3.Connection, handout_id: int) -> Optional[str]:
    """Deletes handout record from DB and returns file path so file can be removed from disk."""
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM handouts WHERE id = ?", (handout_id,))
    row = cursor.fetchone()
    if not row:
        return None
    file_path = row["file_path"]
    cursor.execute("DELETE FROM handouts WHERE id = ?", (handout_id,))
    conn.commit()
    return file_path

def get_handouts_course_hierarchy(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Returns clean 3-level hierarchy for all 4 courses:
    Course -> Units -> Topics (with attached handouts, notes, and completion status)
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, code, color, total_lectures FROM subjects ORDER BY id ASC")
    courses = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT h.id, h.filename, h.original_filename, h.file_type, h.file_size, h.file_path,
               h.upload_date, h.notes, h.subject_id, h.unit_id, h.topic_id
        FROM handouts h
        ORDER BY h.id ASC
    """)
    all_handouts = [dict(r) for r in cursor.fetchall()]

    result = []
    for c in courses:
        c_id = c["id"]
        # Course-level materials (e.g. syllabus sheets, master timetable)
        c_materials = [h for h in all_handouts if h.get("subject_id") == c_id and not h.get("unit_id")]
        
        # Get units for this course
        cursor.execute("SELECT id, unit_number, title FROM units WHERE subject_id = ? ORDER BY unit_number ASC", (c_id,))
        units = [dict(u) for u in cursor.fetchall()]

        units_with_materials_count = 0
        total_topics_count = 0
        completed_topics_count = 0

        for u in units:
            u_id = u["id"]
            u_materials = [h for h in all_handouts if h.get("unit_id") == u_id]
            u["handouts"] = u_materials
            if u_materials:
                units_with_materials_count += 1

            # Get topics for this unit
            cursor.execute("""
                SELECT id, title, order_index, mastery_level, difficulty_level,
                       estimated_minutes, is_mandatory
                FROM topics
                WHERE unit_id = ?
                ORDER BY order_index ASC, id ASC
            """, (u_id,))
            topics = [dict(t) for t in cursor.fetchall()]

            u_completed = 0
            for t in topics:
                t_id = t["id"]
                is_comp = t.get("mastery_level") in ("CONFIDENT", "MASTERED", "COMPLETED")
                t["is_completed"] = is_comp
                if is_comp:
                    u_completed += 1
                t["handouts"] = [h for h in all_handouts if h.get("topic_id") == t_id]

            u["topics"] = topics
            u["total_topics"] = len(topics)
            u["completed_topics"] = u_completed
            u["progress_percent"] = int((u_completed / len(topics)) * 100) if topics else 0

            total_topics_count += len(topics)
            completed_topics_count += u_completed

        c["course_materials"] = c_materials
        c["units"] = units
        c["total_units"] = len(units)
        c["units_with_materials"] = units_with_materials_count
        c["total_topics"] = total_topics_count
        c["completed_topics"] = completed_topics_count
        c["progress_percent"] = int((completed_topics_count / total_topics_count) * 100) if total_topics_count else 0
        result.append(c)

    return result

# =====================================================================
# --- LIVE UNIT & SYLLABUS PROGRESS TRACKER ---
# =====================================================================

def get_syllabus_tracker_data(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Returns full syllabus hierarchy across the four courses with verified completion progress,
    actual study times, weak topic markers, and revision statuses.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, name, priority, color FROM subjects ORDER BY id ASC")
    subjects = [dict(s) for s in cursor.fetchall()]

    for s in subjects:
        s_id = s["id"]
        # Fetch units
        cursor.execute("SELECT id, unit_number, title, lecture_allocation FROM units WHERE subject_id = ? ORDER BY unit_number ASC", (s_id,))
        units = [dict(u) for u in cursor.fetchall()]

        subject_total_topics = 0
        subject_completed_topics = 0
        subject_study_mins = 0

        for u in units:
            u_id = u["id"]
            cursor.execute("""
                SELECT 
                    t.id, t.title, t.order_index, t.mastery_level, t.difficulty_level,
                    t.is_mandatory, t.needs_revision, t.last_studied_at,
                    COUNT(DISTINCT s.id) as scheduled_shifts,
                    SUM(CASE WHEN s.status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_shifts,
                    COALESCE(SUM(s.actual_minutes), 0) as total_study_minutes
                FROM topics t
                LEFT JOIN study_schedules s ON t.id = s.topic_id
                WHERE t.unit_id = ?
                GROUP BY t.id
                ORDER BY t.order_index ASC
            """, (u_id,))
            topics = [dict(t) for t in cursor.fetchall()]

            u_total = len(topics)
            u_completed = sum(1 for t in topics if t["mastery_level"] in ("COMPLETED", "MASTERED", "CONFIDENT"))
            u_in_progress = sum(1 for t in topics if t["mastery_level"] in ("STUDIED_ONCE", "PARTIALLY_UNDERSTOOD", "IN_PROGRESS"))
            u_not_started = sum(1 for t in topics if t["mastery_level"] == "NOT_STARTED")
            u_study_mins = sum(t["total_study_minutes"] for t in topics)

            u["topics"] = topics
            u["topics_count"] = u_total
            u["completed_count"] = u_completed
            u["in_progress_count"] = u_in_progress
            u["not_started_count"] = u_not_started
            u["total_study_minutes"] = u_study_mins
            u["completion_pct"] = round((u_completed / u_total * 100), 1) if u_total > 0 else 0

            subject_total_topics += u_total
            subject_completed_topics += u_completed
            subject_study_mins += u_study_mins

        s["units"] = units
        s["total_units"] = len(units)
        s["units_completed"] = sum(1 for u in units if u["completion_pct"] >= 100)
        s["units_in_progress"] = sum(1 for u in units if 0 < u["completion_pct"] < 100)
        s["units_not_started"] = sum(1 for u in units if u["completion_pct"] == 0)
        s["total_topics"] = subject_total_topics
        s["topics_completed"] = subject_completed_topics
        s["topics_remaining"] = max(0, subject_total_topics - subject_completed_topics)
        s["total_study_minutes"] = subject_study_mins
        s["completion_pct"] = round((subject_completed_topics / subject_total_topics * 100), 1) if subject_total_topics > 0 else 0

    return subjects

def update_topic_status_audit(conn: sqlite3.Connection, topic_id: int, mastery_level: Optional[str] = None, difficulty_level: Optional[str] = None, needs_revision: Optional[int] = None) -> Dict[str, Any]:
    """Updates topic mastery, difficulty tag (Easy/Moderate/Difficult), or revision flag."""
    cursor = conn.cursor()
    updates = []
    params = []
    if mastery_level is not None:
        updates.append("mastery_level = ?")
        params.append(mastery_level)
    if difficulty_level is not None:
        updates.append("difficulty_level = ?")
        params.append(difficulty_level)
    if needs_revision is not None:
        updates.append("needs_revision = ?")
        params.append(needs_revision)

    if updates:
        params.append(topic_id)
        cursor.execute(f"UPDATE topics SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    cursor.execute("SELECT * FROM topics WHERE id = ?", (topic_id,))
    row = cursor.fetchone()
    return dict(row) if row else {}

# =====================================================================
# --- DOUBTS & NOTES ATTACHMENT ---
# =====================================================================

def add_doubt(conn: sqlite3.Connection, subject_id: int, doubt_text: str, schedule_id: Optional[int] = None, topic_id: Optional[int] = None) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO doubts (schedule_id, subject_id, topic_id, doubt_text, status)
        VALUES (?, ?, ?, ?, 'UNRESOLVED')
    """, (schedule_id, subject_id, topic_id, doubt_text))
    conn.commit()
    return cursor.lastrowid

def get_doubts(conn: sqlite3.Connection, status: Optional[str] = None, subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    query = """
        SELECT d.id, d.schedule_id, d.subject_id, d.topic_id, d.doubt_text, d.answer_text, d.status, d.created_at, d.resolved_at,
               s.code as subject_code, s.name as subject_name, s.color as subject_color,
               t.title as topic_title
        FROM doubts d
        JOIN subjects s ON d.subject_id = s.id
        LEFT JOIN topics t ON d.topic_id = t.id
        WHERE 1=1
    """
    params = []
    if status:
        if status.upper() in ('OPEN', 'UNRESOLVED'):
            query += " AND UPPER(d.status) IN ('OPEN', 'UNRESOLVED')"
        else:
            query += " AND UPPER(d.status) = ?"
            params.append(status.upper())
    if subject_id:
        query += " AND d.subject_id = ?"
        params.append(subject_id)
    query += " ORDER BY d.id DESC"
    cursor.execute(query, params)
    return [dict(r) for r in cursor.fetchall()]

def resolve_doubt(conn: sqlite3.Connection, doubt_id: int, answer_text: str) -> bool:
    cursor = conn.cursor()
    now_iso = datetime.now().isoformat()
    cursor.execute("""
        UPDATE doubts SET
            answer_text = ?,
            status = 'RESOLVED',
            resolved_at = ?
        WHERE id = ?
    """, (answer_text, now_iso, doubt_id))
    conn.commit()
    return cursor.rowcount > 0

# =====================================================================
# --- QUOTE OF THE DAY & FAVORITES ---
# =====================================================================

def get_stable_quote_of_the_day(conn: sqlite3.Connection, date_str: str) -> Dict[str, Any]:
    """
    Returns exactly one quote per local calendar day.
    Deterministic: stays completely stable across all page refreshes for that date.
    New quote is provided on the next day.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, quote, quote_text, author, category, is_favorite FROM daily_quotes ORDER BY id ASC")
    quotes = [dict(q) for q in cursor.fetchall()]

    if not quotes:
        seed_quotes_if_empty(conn)
        cursor.execute("SELECT id, quote, quote_text, author, category, is_favorite FROM daily_quotes ORDER BY id ASC")
        quotes = [dict(q) for q in cursor.fetchall()]

    # Hash the calendar date string (YYYY-MM-DD) deterministically
    date_hash = sum(ord(c) for c in date_str)
    selected_idx = date_hash % len(quotes)
    selected_quote = quotes[selected_idx]

    q_text = selected_quote.get("quote_text") or selected_quote.get("quote")
    # Check if favorited in quote_favorites table
    cursor.execute("SELECT COUNT(*) as cnt FROM quote_favorites WHERE quote_text = ?", (q_text,))
    is_fav = cursor.fetchone()["cnt"] > 0 or bool(selected_quote.get("is_favorite"))

    return {
        "id": selected_quote["id"],
        "quote": q_text,
        "quote_text": q_text,
        "author": selected_quote.get("author") or "Unknown",
        "category": selected_quote.get("category") or "Consistency & Discipline",
        "is_favorite": is_fav,
        "date": date_str
    }

def toggle_quote_favorite(conn: sqlite3.Connection, quote_identifier: Any, author_or_fav: Any = None, force_fav: Optional[bool] = None, category: str = "Consistency") -> bool:
    cursor = conn.cursor()
    # Check if identifier is an integer ID
    is_id = False
    if isinstance(quote_identifier, int):
        is_id = True
    elif isinstance(quote_identifier, str) and quote_identifier.strip().isdigit():
        is_id = True
        quote_identifier = int(quote_identifier.strip())

    if is_id:
        q_id = quote_identifier
        is_fav = bool(author_or_fav) if author_or_fav is not None else True
        if force_fav is not None:
            is_fav = force_fav
        cursor.execute("UPDATE daily_quotes SET is_favorite = ? WHERE id = ?", (1 if is_fav else 0, q_id))
        cursor.execute("SELECT quote, quote_text, author, category FROM daily_quotes WHERE id = ?", (q_id,))
        q = cursor.fetchone()
        if q:
            q_text = q["quote_text"] or q["quote"]
            if is_fav:
                cursor.execute("INSERT OR IGNORE INTO quote_favorites (quote_text, author, category) VALUES (?, ?, ?)",
                               (q_text, q["author"] or "Unknown", q["category"] or category))
            else:
                cursor.execute("DELETE FROM quote_favorites WHERE quote_text = ?", (q_text,))
        conn.commit()
        return is_fav
    else:
        q_text = str(quote_identifier).strip()
        author = str(author_or_fav) if author_or_fav is not None and not isinstance(author_or_fav, bool) else "Unknown"
        # Check if already in favorites
        cursor.execute("SELECT id FROM quote_favorites WHERE quote_text = ?", (q_text,))
        existing = cursor.fetchone()
        if force_fav is True or (force_fav is None and not existing):
            cursor.execute("INSERT OR IGNORE INTO quote_favorites (quote_text, author, category) VALUES (?, ?, ?)",
                           (q_text, author, category))
            cursor.execute("UPDATE daily_quotes SET is_favorite = 1 WHERE quote = ? OR quote_text = ?", (q_text, q_text))
            conn.commit()
            return True
        else:
            cursor.execute("DELETE FROM quote_favorites WHERE quote_text = ?", (q_text,))
            cursor.execute("UPDATE daily_quotes SET is_favorite = 0 WHERE quote = ? OR quote_text = ?", (q_text, q_text))
            conn.commit()
            return False

def get_favorite_quotes(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("SELECT id, quote_text, quote_text as quote, author, category, favorited_at FROM quote_favorites ORDER BY id DESC")
    return [dict(r) for r in cursor.fetchall()]

# =====================================================================
# --- GLOBAL SEARCH ACROSS ALL ENTITIES ---
# =====================================================================

def global_search(conn: sqlite3.Connection, query_term: str) -> Dict[str, Any]:
    """Searches subjects, units, topics, handouts, study notes, and timetable shifts."""
    cursor = conn.cursor()
    q = f"%{query_term.strip()}%"

    # Subjects
    cursor.execute("SELECT id, code, name FROM subjects WHERE code LIKE ? OR name LIKE ?", (q, q))
    matched_subjects = [dict(r) for r in cursor.fetchall()]

    # Topics
    cursor.execute("""
        SELECT t.id, t.title, u.unit_number, u.title as unit_title, s.code as subject_code, s.name as subject_name
        FROM topics t
        JOIN units u ON t.unit_id = u.id
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.title LIKE ?
        LIMIT 10
    """, (q,))
    matched_topics = [dict(r) for r in cursor.fetchall()]

    # Handouts
    cursor.execute("""
        SELECT h.id, h.original_filename, h.file_type, s.code as subject_code
        FROM handouts h
        JOIN subjects s ON h.subject_id = s.id
        WHERE h.original_filename LIKE ? OR h.notes LIKE ?
        LIMIT 10
    """, (q, q))
    matched_handouts = [dict(r) for r in cursor.fetchall()]

    # Scheduled shifts
    cursor.execute("""
        SELECT s.id, s.scheduled_date, s.shift_number, s.task_description, s.status, subj.code as subject_code
        FROM study_schedules s
        JOIN subjects subj ON s.subject_id = subj.id
        WHERE s.task_description LIKE ? OR s.notes LIKE ?
        LIMIT 10
    """, (q, q))
    matched_tasks = [dict(r) for r in cursor.fetchall()]

    return {
        "query": query_term,
        "subjects": matched_subjects,
        "topics": matched_topics,
        "handouts": matched_handouts,
        "tasks": matched_tasks
    }

# =====================================================================
# --- WEEKLY REVIEW & SUGGESTIONS ---
# =====================================================================

def get_weekly_review(conn: sqlite3.Connection, target_date_str: str) -> Dict[str, Any]:
    """
    At the end of each week (Mon-Sun), displays:
    Academic hours completed, target achievement, strongest course,
    course with most unfinished work, confirmed wasted time, completed shifts,
    suggested priorities for next week based on actual data.
    """
    cursor = conn.cursor()
    try:
        dt = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except Exception:
        dt = date.today()

    w_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
    w_end = (dt - timedelta(days=dt.weekday()) + timedelta(days=6)).strftime("%Y-%m-%d")

    # Academic hours completed in week
    cursor.execute("SELECT COALESCE(SUM(actual_minutes), 0) as total FROM study_schedules WHERE scheduled_date BETWEEN ? AND ? AND is_wrapup = 0", (w_start, w_end))
    acad_mins = cursor.fetchone()["total"]
    acad_target_week = 240 * 7 # 1680 mins (28 hrs)
    achievement_rate = round((acad_mins / acad_target_week) * 100, 1)

    # Completed shifts
    cursor.execute("SELECT COUNT(*) as cnt FROM study_schedules WHERE scheduled_date BETWEEN ? AND ? AND status = 'COMPLETED' AND is_wrapup = 0", (w_start, w_end))
    completed_shifts = cursor.fetchone()["cnt"]

    # Confirmed wasted time in week
    cursor.execute("SELECT COALESCE(SUM(minutes), 0) as total FROM wasted_time_logs WHERE log_date BETWEEN ? AND ?", (w_start, w_end))
    wasted_week = cursor.fetchone()["total"]

    # Subject performance in this week
    cursor.execute("""
        SELECT subj.code, subj.name,
               SUM(CASE WHEN s.status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_shifts,
               SUM(CASE WHEN s.status != 'COMPLETED' THEN 1 ELSE 0 END) as unfinished_shifts,
               COALESCE(SUM(s.actual_minutes), 0) as study_minutes
        FROM study_schedules s
        JOIN subjects subj ON s.subject_id = subj.id
        WHERE s.scheduled_date BETWEEN ? AND ? AND s.is_wrapup = 0
        GROUP BY subj.id
        ORDER BY completed_shifts DESC
    """, (w_start, w_end))
    subj_perf = [dict(r) for r in cursor.fetchall()]

    strongest = subj_perf[0]["name"] if subj_perf else "None yet"
    unfinished_sorted = sorted(subj_perf, key=lambda x: x["unfinished_shifts"], reverse=True)
    most_unfinished = unfinished_sorted[0]["name"] if unfinished_sorted and unfinished_sorted[0]["unfinished_shifts"] > 0 else "None (all on track!)"

    # Suggested priorities for following week
    suggestions = []
    if any(s["code"] == "CSN 3003" and s["unfinished_shifts"] > 0 for s in subj_perf):
        suggestions.append("Discrete Structures has pending shifts: allocate first morning shifts to finish Unit 2-4 proofs.")
    suggestions.append("Maintain 30-min English speaking streak and solve 2 DSA questions daily before afternoon.")
    if wasted_week > 120:
        suggestions.append(f"Confirmed wasted time ({wasted_week}m) is elevated: use 45-minute focus timer with phone placed away.")

    return {
        "week_range": f"{w_start} to {w_end}",
        "academic_hours_completed": round(acad_mins / 60, 1),
        "academic_minutes_completed": acad_mins,
        "academic_target_week_minutes": acad_target_week,
        "target_achievement_percentage": achievement_rate,
        "completed_shifts_count": completed_shifts,
        "confirmed_wasted_minutes": wasted_week,
        "strongest_course": strongest,
        "course_with_most_unfinished_work": most_unfinished,
        "subject_breakdown": subj_perf,
        "suggested_priorities": suggestions
    }

# =====================================================================
# --- SAFE DATA BACKUP & RESTORE ---
# =====================================================================

def export_database_backup(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Exports all user study records, schedules, wasted logs, handouts, doubts to JSON."""
    cursor = conn.cursor()
    backup = {
        "version": "2.0.0",
        "exported_at": datetime.now().isoformat(),
        "tables": {}
    }

    tables_to_export = [
        "settings", "study_schedules", "study_sessions", "wasted_time_logs",
        "daily_dsa_assignments", "daily_english_logs", "handouts", "doubts",
        "rescheduled_history", "quote_favorites"
    ]

    for t in tables_to_export:
        try:
            cursor.execute(f"SELECT * FROM {t}")
            backup["tables"][t] = [dict(r) for r in cursor.fetchall()]
        except Exception:
            backup["tables"][t] = []

    return backup

def restore_database_backup(conn: sqlite3.Connection, backup_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates backup and restores tables safely."""
    if not isinstance(backup_data, dict) or "tables" not in backup_data:
        raise ValueError("Invalid backup format: missing 'tables' payload.")

    cursor = conn.cursor()
    tables = backup_data["tables"]
    restored_counts = {}

    for t_name, rows in tables.items():
        if not rows or not isinstance(rows, list):
            continue
        try:
            # Clear existing data for user logs only
            if t_name in ("wasted_time_logs", "doubts", "rescheduled_history", "quote_favorites"):
                cursor.execute(f"DELETE FROM {t_name}")
            
            for row in rows:
                cols = list(row.keys())
                placeholders = ", ".join(["?"] * len(cols))
                col_names = ", ".join(cols)
                cursor.execute(f"INSERT OR REPLACE INTO {t_name} ({col_names}) VALUES ({placeholders})", list(row.values()))
            
            restored_counts[t_name] = len(rows)
        except Exception as e:
            restored_counts[t_name] = f"Error: {str(e)}"

    conn.commit()
    return {"status": "restored", "counts": restored_counts}


# --- REDO / PRACTICE AGAIN FUNCTIONS ---

def add_redo_task(
    conn: sqlite3.Connection,
    topic_title: str,
    schedule_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    course_code: Optional[str] = None,
    course_name: Optional[str] = None,
    unit_number: Optional[int] = None,
    unit_title: Optional[str] = None,
    original_completion_date: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: str = "MEDIUM",
    reason: Optional[str] = None
) -> int:
    """Adds a task to the persistent Redo / Practice Again queue without inflating syllabus completion."""
    cursor = conn.cursor()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # If course_code/name missing, resolve from subject_id or topic_id
    if (not course_code or not course_name) and subject_id:
        cursor.execute("SELECT code, name FROM subjects WHERE id = ?", (subject_id,))
        s_row = cursor.fetchone()
        if s_row:
            course_code = course_code or s_row["code"]
            course_name = course_name or s_row["name"]

    cursor.execute("""
        INSERT INTO redo_tasks (
            schedule_id, topic_id, subject_id, topic_title, course_code, course_name,
            unit_number, unit_title, original_completion_date, added_to_redo_date,
            due_date, priority, reason, status, redo_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0)
    """, (
        schedule_id, topic_id, subject_id, topic_title, course_code, course_name,
        unit_number, unit_title, original_completion_date or today_str, today_str,
        due_date, priority.upper(), reason
    ))
    conn.commit()
    return cursor.lastrowid

def get_redo_tasks(conn: sqlite3.Connection, status: Optional[str] = None, course_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves redo tasks with optional filtering by status and course."""
    cursor = conn.cursor()
    query = """
        SELECT r.*, s.color as course_color
        FROM redo_tasks r
        LEFT JOIN subjects s ON (r.subject_id = s.id OR r.course_code = s.code)
        WHERE 1=1
    """
    params = []
    if status and status != 'ALL':
        query += " AND r.status = ?"
        params.append(status.upper())
    if course_code and course_code != 'ALL':
        query += " AND (r.course_code = ? OR s.code = ?)"
        params.extend([course_code, course_code])

    query += " ORDER BY CASE r.priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END, r.created_at DESC"
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]

def update_redo_task(
    conn: sqlite3.Connection,
    redo_id: int,
    status: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    reason: Optional[str] = None
) -> bool:
    """Updates redo task metadata, status, or due date."""
    cursor = conn.cursor()
    updates = []
    params = []

    if status:
        updates.append("status = ?")
        params.append(status.upper())
        if status.upper() == 'COMPLETED':
            updates.append("completed_at = datetime('now')")
            updates.append("redo_count = redo_count + 1")
            updates.append("last_practiced_at = datetime('now')")
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date)
    if priority:
        updates.append("priority = ?")
        params.append(priority.upper())
    if reason is not None:
        updates.append("reason = ?")
        params.append(reason)

    if not updates:
        return False

    params.append(redo_id)
    cursor.execute(f"UPDATE redo_tasks SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    return cursor.rowcount > 0

def complete_redo_task(conn: sqlite3.Connection, redo_id: int) -> bool:
    """Marks a redo task completed, records practice timestamp, and increments redo attempt count."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE redo_tasks
        SET status = 'COMPLETED',
            redo_count = redo_count + 1,
            last_practiced_at = datetime('now'),
            completed_at = datetime('now')
        WHERE id = ?
    """, (redo_id,))
    conn.commit()
    return cursor.rowcount > 0

def delete_redo_task(conn: sqlite3.Connection, redo_id: int) -> bool:
    """Removes a task from the redo queue."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM redo_tasks WHERE id = ?", (redo_id,))
    conn.commit()
    return cursor.rowcount > 0


# --- CALENDAR INTEGRATED EVENTS & ACTIONS ---

def get_calendar_events_combined(
    conn: sqlite3.Connection,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns unified, complete calendar events for the specified date range:
    1. Custom calendar events (calendar_events)
    2. Scheduled study shifts (study_schedules)
    3. Daily DSA assignments (daily_dsa_assignments)
    4. Daily English speaking logs (daily_english_logs)
    5. Official semester exam milestones
    """
    cursor = conn.cursor()
    events = []

    # 1. Custom calendar events
    cal_query = "SELECT * FROM calendar_events WHERE 1=1"
    cal_params = []
    if start_date:
        cal_query += " AND event_date >= ?"
        cal_params.append(start_date)
    if end_date:
        cal_query += " AND event_date <= ?"
        cal_params.append(end_date)
    cursor.execute(cal_query, cal_params)
    for r in cursor.fetchall():
        events.append({
            "id": f"custom_{r['id']}",
            "db_id": r["id"],
            "title": r["title"],
            "description": r["description"],
            "date": r["event_date"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "duration": r["duration_minutes"],
            "type": r["event_type"],
            "subject_code": r["subject_code"],
            "color": r["color"] or "#6366f1",
            "is_completed": bool(r["is_completed"])
        })

    # 2. Scheduled study shifts (from study_schedules)
    sched_query = """
        SELECT sc.*, sub.code as subject_code, sub.name as subject_name, sub.color as subject_color,
               t.title as topic_name
        FROM study_schedules sc
        JOIN subjects sub ON sc.subject_id = sub.id
        LEFT JOIN topics t ON sc.topic_id = t.id
        WHERE 1=1
    """
    sched_params = []
    if start_date:
        sched_query += " AND sc.scheduled_date >= ?"
        sched_params.append(start_date)
    if end_date:
        sched_query += " AND sc.scheduled_date <= ?"
        sched_params.append(end_date)
    sched_query += " ORDER BY sc.scheduled_date, sc.shift_number"
    cursor.execute(sched_query, sched_params)

    for r in cursor.fetchall():
        is_comp = r["status"] == "COMPLETED"
        events.append({
            "id": f"shift_{r['id']}",
            "schedule_id": r["id"],
            "title": f"Shift {r['shift_number']}: {r['subject_code']} - {r['task_description'] or r['topic_name']}",
            "description": r["learning_objectives"] or r["reasoning"],
            "date": r["scheduled_date"],
            "start_time": r["planned_start_time"],
            "duration": r["duration_minutes"],
            "actual_minutes": r["actual_minutes"],
            "type": "academic_shift",
            "shift_number": r["shift_number"],
            "is_wrapup": bool(r["is_wrapup"]),
            "subject_code": r["subject_code"],
            "subject_name": r["subject_name"],
            "color": r["subject_color"] or "#4f46e5",
            "status": r["status"],
            "is_completed": is_comp
        })

    # 3. Daily DSA assignments
    dsa_query = """
        SELECT dsa.*, dq.title as question_title, dq.difficulty, dq.topic as dsa_topic
        FROM daily_dsa_assignments dsa
        LEFT JOIN dsa_questions dq ON dsa.question_id = dq.id
        WHERE 1=1
    """
    dsa_params = []
    if start_date:
        dsa_query += " AND dsa.assigned_date >= ?"
        dsa_params.append(start_date)
    if end_date:
        dsa_query += " AND dsa.assigned_date <= ?"
        dsa_params.append(end_date)
    cursor.execute(dsa_query, dsa_params)
    for r in cursor.fetchall():
        events.append({
            "id": f"dsa_{r['id']}",
            "title": f"DSA #{r['slot_number']}: {r['question_title'] or r['topic_name'] or 'Algorithm Problem'}",
            "date": r["assigned_date"],
            "type": "dsa",
            "slot_number": r["slot_number"],
            "difficulty": r["difficulty"] or "Medium",
            "status": r["status"],
            "color": "#38bdf8",
            "is_completed": r["status"] == "Solved"
        })

    # 4. Daily English practice logs
    eng_query = """
        SELECT el.*, et.title as topic_title
        FROM daily_english_logs el
        LEFT JOIN english_speaking_topics et ON el.topic_id = et.id
        WHERE 1=1
    """
    eng_params = []
    if start_date:
        eng_query += " AND (el.log_date >= ? OR el.assigned_date >= ?)"
        eng_params.extend([start_date, start_date])
    if end_date:
        eng_query += " AND (el.log_date <= ? OR el.assigned_date <= ?)"
        eng_params.extend([end_date, end_date])
    cursor.execute(eng_query, eng_params)
    for r in cursor.fetchall():
        d_str = r["log_date"] or r["assigned_date"]
        events.append({
            "id": f"eng_{r['id']}",
            "title": f"English Practice: {r['topic_title'] or '30m Speaking Session'}",
            "date": d_str,
            "type": "english",
            "actual_minutes": r["actual_minutes"] or (r["time_spent_seconds"] // 60 if r["time_spent_seconds"] else 0),
            "status": "COMPLETED" if r["is_completed"] else "PENDING",
            "color": "#a855f7",
            "is_completed": bool(r["is_completed"])
        })

    # 5. Fixed Exam Milestones
    exam_milestones = [
        {"date": "2026-11-26", "title": "🎯 EXAM: CSN 3001 Data Structures", "code": "CSN 3001", "color": "#ef4444"},
        {"date": "2026-11-28", "title": "🎯 EXAM: CSN 3003 Discrete Structures", "code": "CSN 3003", "color": "#ef4444"},
        {"date": "2026-12-01", "title": "🎯 EXAM: CSN 3004 Object-Oriented Prog", "code": "CSN 3004", "color": "#ef4444"},
        {"date": "2026-12-04", "title": "🎯 EXAM: CSN 3002 Data Science & ML", "code": "CSN 3002", "color": "#ef4444"}
    ]
    for em in exam_milestones:
        if (not start_date or em["date"] >= start_date) and (not end_date or em["date"] <= end_date):
            events.append({
                "id": f"exam_{em['code'].replace(' ', '_')}",
                "title": em["title"],
                "date": em["date"],
                "type": "exam",
                "subject_code": em["code"],
                "color": em["color"],
                "is_completed": False
            })

    return events

def create_calendar_event(
    conn: sqlite3.Connection,
    title: str,
    event_date: str,
    description: Optional[str] = None,
    event_type: str = "study",
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    duration_minutes: int = 60,
    subject_code: Optional[str] = None,
    color: Optional[str] = None
) -> int:
    """Inserts a new custom event into calendar_events."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO calendar_events (
            title, description, event_date, start_time, end_time, duration_minutes,
            event_type, subject_code, color, is_completed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        title, description, event_date, start_time, end_time, duration_minutes,
        event_type, subject_code, color or "#6366f1"
    ))
    conn.commit()
    return cursor.lastrowid

def update_calendar_event(conn: sqlite3.Connection, event_id: int, **fields) -> bool:
    """Updates custom calendar event fields."""
    cursor = conn.cursor()
    valid_cols = {"title", "description", "event_date", "start_time", "end_time", "duration_minutes", "event_type", "subject_code", "color", "is_completed"}
    updates = []
    params = []
    for k, v in fields.items():
        if k in valid_cols and v is not None:
            updates.append(f"{k} = ?")
            params.append(v)
    if not updates:
        return False
    params.append(event_id)
    cursor.execute(f"UPDATE calendar_events SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    return cursor.rowcount > 0

def delete_calendar_event(conn: sqlite3.Connection, event_id: int) -> bool:
    """Deletes a custom calendar event."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
    conn.commit()
    return cursor.rowcount > 0


# --- USER AUTHENTICATION & PROFILE FUNCTIONS ---

def create_user(
    conn: sqlite3.Connection,
    username: str,
    password_hash: str,
    email: Optional[str] = None,
    full_name: str = "Student"
) -> int:
    """Creates a user account in the persistent database."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, full_name, is_active, theme_preference)
        VALUES (?, ?, ?, ?, 1, 'dark')
    """, (username, email, password_hash, full_name))
    conn.commit()
    return cursor.lastrowid

def get_user_by_username(conn: sqlite3.Connection, username: str) -> Optional[Dict[str, Any]]:
    """Fetches user record by username."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    return dict(row) if row else None

def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    """Fetches user record by ID."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, is_active, theme_preference, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

def update_user_profile(
    conn: sqlite3.Connection,
    user_id: int,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    theme_preference: Optional[str] = None
) -> bool:
    """Updates user profile and theme preference."""
    cursor = conn.cursor()
    updates = []
    params = []
    if full_name:
        updates.append("full_name = ?")
        params.append(full_name)
    if email:
        updates.append("email = ?")
        params.append(email)
    if theme_preference:
        updates.append("theme_preference = ?")
        params.append(theme_preference)
    if not updates:
        return False
    params.append(user_id)
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    return cursor.rowcount > 0


# --- MISSING COURSE MATERIALS CHECKLIST ---

def get_missing_materials_checklist(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Inspects all course units in the syllabus and checks which units have uploaded handouts
    vs which units currently lack student lecture photos or handouts.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id as unit_id, u.unit_number, u.title as unit_title,
               s.id as subject_id, s.code as course_code, s.name as course_name, s.color as course_color
        FROM units u
        JOIN subjects s ON u.subject_id = s.id
        ORDER BY s.id, u.unit_number
    """)
    all_units = cursor.fetchall()

    cursor.execute("SELECT id, filename, original_filename, subject_id, unit_id, file_type, file_size FROM handouts")
    handouts = cursor.fetchall()

    unit_handout_map = {}
    course_handout_map = {}
    for h in handouts:
        u_id = h["unit_id"]
        s_id = h["subject_id"]
        if u_id:
            unit_handout_map.setdefault(u_id, []).append(dict(h))
        if s_id:
            course_handout_map.setdefault(s_id, []).append(dict(h))

    uploaded_list = []
    missing_list = []

    for u in all_units:
        u_id = u["unit_id"]
        attached = unit_handout_map.get(u_id, [])
        item = {
            "unit_id": u_id,
            "unit_number": u["unit_number"],
            "unit_title": u["unit_title"],
            "course_code": u["course_code"],
            "course_name": u["course_name"],
            "course_color": u["course_color"],
            "attached_handouts": attached
        }
        if attached:
            uploaded_list.append(item)
        else:
            missing_list.append(item)

    courses_map = {}
    for u in all_units:
        c_code = u["course_code"]
        if c_code not in courses_map:
            courses_map[c_code] = {
                "course_code": c_code,
                "course_name": u["course_name"],
                "course_color": u["course_color"],
                "total_units": 0,
                "units": []
            }
        attached = unit_handout_map.get(u["unit_id"], [])
        courses_map[c_code]["total_units"] += 1
        courses_map[c_code]["units"].append({
            "unit_id": u["unit_id"],
            "unit_number": u["unit_number"],
            "unit_title": u["unit_title"],
            "has_handout": len(attached) > 0,
            "materials": attached
        })

    course_breakdown = list(courses_map.values())

    return {
        "total_units": len(all_units),
        "units_with_materials": len(uploaded_list),
        "units_missing_materials": len(missing_list),
        "uploaded_materials": uploaded_list,
        "missing_materials_checklist": missing_list,
        "course_breakdown": course_breakdown,
        "checklist": course_breakdown,
        "total_handout_files": len(handouts)
    }



