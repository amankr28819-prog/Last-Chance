#!/usr/bin/env python3
"""
Last Chance — SQLite to PostgreSQL Migration Tool
Transfers all existing user records, timetable schedules, topic progress,
DSA assignments, quotes, handouts metadata, and redo queue into durable PostgreSQL.

Usage:
    python scripts/migrate_to_postgres.py --sqlite data/lastchance.db --postgres postgresql://user:pass@host:5432/dbname
Or set DATABASE_URL environment variable:
    export DATABASE_URL=postgresql://user:pass@host:5432/dbname
    python scripts/migrate_to_postgres.py
"""

import os
import sys
import sqlite3
import argparse
from typing import List, Dict, Any

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None

TABLE_ORDER = [
    "subjects",
    "units",
    "topics",
    "subtopics",
    "topic_prerequisites",
    "study_schedules",
    "schedule_change_logs",
    "focus_sessions",
    "dsa_questions",
    "daily_dsa_assignments",
    "english_speaking_topics",
    "daily_english_logs",
    "quotes",
    "quote_favorites",
    "calendar_events",
    "wasted_time_logs",
    "doubts",
    "system_settings",
    "handouts",
    "redo_tasks",
    "users"
]

def migrate(sqlite_path: str, pg_url: str):
    if not os.path.exists(sqlite_path):
        print(f"Error: Source SQLite database not found at '{sqlite_path}'.")
        sys.exit(1)

    if not psycopg2:
        print("Error: psycopg2 is required for PostgreSQL migration. Run: pip install psycopg2-binary")
        sys.exit(1)

    print(f"[*] Reading source SQLite database: {sqlite_path}")
    s_conn = sqlite3.connect(sqlite_path)
    s_conn.row_factory = sqlite3.Row
    s_cursor = s_conn.cursor()

    print(f"[*] Connecting to destination PostgreSQL database...")
    p_conn = psycopg2.connect(pg_url)
    p_cursor = p_conn.cursor()

    total_records = 0

    for table in TABLE_ORDER:
        # Check if table exists in SQLite
        s_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not s_cursor.fetchone():
            print(f"[-] Skipping table '{table}' (not found in SQLite).")
            continue

        s_cursor.execute(f"SELECT * FROM {table}")
        rows = s_cursor.fetchall()
        if not rows:
            print(f"[.] Table '{table}': 0 records.")
            continue

        columns = rows[0].keys()
        col_names = ", ".join([f'"{col}"' for col in columns])
        placeholders = ", ".join(["%s"] * len(columns))

        data = [[r[col] for col in columns] for r in rows]

        # Insert into PostgreSQL using ON CONFLICT DO NOTHING
        insert_sql = f"""
            INSERT INTO {table} ({col_names})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        """
        try:
            p_cursor.executemany(insert_sql, data)
            p_conn.commit()
            print(f"[✓] Migrated {len(data)} records into '{table}'.")
            total_records += len(data)

            # Reset sequence if table has integer id
            if "id" in columns:
                try:
                    p_cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table};")
                    p_conn.commit()
                except Exception:
                    p_conn.rollback()
        except Exception as e:
            p_conn.rollback()
            print(f"[!] Warning migrating table '{table}': {e}")

    s_conn.close()
    p_conn.close()
    print(f"\n[✓] Migration completed successfully! Total records transferred: {total_records}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Last Chance SQLite to PostgreSQL")
    parser.add_argument("--sqlite", default=os.getenv("SQLITE_PATH", "data/lastchance.db"), help="Path to SQLite database")
    parser.add_argument("--postgres", default=os.getenv("DATABASE_URL"), help="PostgreSQL connection string")
    args = parser.parse_args()

    if not args.postgres:
        print("Error: Must provide PostgreSQL connection string via --postgres or DATABASE_URL environment variable.")
        print("Example: python scripts/migrate_to_postgres.py --postgres postgresql://user:pass@host:5432/lastchance")
        sys.exit(1)

    migrate(args.sqlite, args.postgres)
