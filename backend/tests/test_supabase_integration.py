import os
import pytest
from backend.storage import StorageService
from backend.database import translate_query_for_postgres, is_postgres, get_connection
from scripts.migrate_sqlite_to_supabase import MIGRATION_ORDER, get_sqlite_conn, migrate_table

def test_query_translator_postgres():
    # 1. Placeholders
    q1, ret1 = translate_query_for_postgres("SELECT * FROM subjects WHERE code = ? AND id = ?")
    assert "%s" in q1
    assert "?" not in q1
    assert ret1 is False

    # 2. Datetime translation
    q2, ret2 = translate_query_for_postgres("UPDATE study_schedules SET completed_at = datetime('now') WHERE id = ?")
    assert "CURRENT_TIMESTAMP" in q2
    assert "datetime('now')" not in q2
    assert ret2 is False

    # 3. INSERT with RETURNING id for lastrowid
    q3, ret3 = translate_query_for_postgres("INSERT INTO topics (unit_id, title) VALUES (?, ?)")
    assert "RETURNING id" in q3
    assert ret3 is True

    # 4. INSERT into table without ID (settings)
    q4, ret4 = translate_query_for_postgres("INSERT INTO settings (key, value) VALUES (?, ?)")
    assert "RETURNING id" not in q4
    assert ret4 is False

    # 5. Question mark inside string literal preserved
    q5, ret5 = translate_query_for_postgres("SELECT * FROM doubts WHERE doubt_text = 'What is recursion?' AND status = ?")
    assert "'What is recursion?'" in q5
    assert ret5 is False

def test_storage_service_local_fallback():
    service = StorageService(url="", key="", bucket="test-bucket")
    assert service.is_cloud is False

    test_content = b"Mock handout binary data for testing"
    test_fname = "test_handout_sample.txt"

    # Upload (writes to local uploads/)
    res = service.upload_file(test_content, test_fname, "text/plain")
    assert res["is_remote"] is False
    assert res["file_size"] == len(test_content)

    # Retrieve
    content, mime = service.get_file_bytes(test_fname)
    assert content == test_content
    assert "text" in mime

    # Signed URL returns None when offline
    assert service.create_signed_url(test_fname) is None

    # Delete
    deleted = service.delete_file(test_fname)
    assert deleted is True

def test_sqlite_migration_dry_run_integrity():
    conn = get_sqlite_conn("data/lastchance.db")
    assert conn is not None

    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    actual_tables = {r[0] for r in cur.fetchall()}

    # Ensure every single table in the SQLite database is covered by MIGRATION_ORDER
    for t in actual_tables:
        assert t in MIGRATION_ORDER, f"Table {t} missing from migration order list!"

    # Test dry run execution on all tables
    for t in MIGRATION_ORDER:
        res = migrate_table(conn, None, t, dry_run=True)
        assert res["status"] in ("DRY_RUN_OK", "EMPTY")
        assert res["source_count"] >= 0

    conn.close()

def test_sqlite_fallback_active_when_database_url_empty():
    # In standard testing environment without DATABASE_URL, is_postgres should be False
    if not os.environ.get("DATABASE_URL"):
        assert is_postgres() is False
        conn = get_connection()
        # Should be an SQLite connection
        assert hasattr(conn, "row_factory")
        conn.close()
