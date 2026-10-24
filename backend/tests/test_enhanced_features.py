import pytest
import sqlite3
from datetime import date, datetime
from backend.database import (
    log_wasted_time, get_wasted_time_summary, get_wasted_time_graph_data,
    get_daily_dsa_topics, update_daily_dsa_topic,
    get_english_status_today, save_english_practice, set_setting
)
from backend.scheduler import StudyScheduler

def test_wasted_time_tracking_and_shortfall(test_db):
    """Verifies that English shortfall, confirmed wasted time, and missed tasks are tracked without double counting."""
    set_setting(test_db, "simulated_today", "2026-10-25")
    
    # 1. Log manual confirmed wasted time (e.g. 45 min unnecessary social media)
    log_wasted_time(test_db, "2026-10-25", 45, "Distraction and scrolling", "Unproductive Time")
    
    # 2. Log English speaking with partial completion (20 min actual vs 30 min target -> 10 min shortfall)
    save_english_practice(test_db, "2026-10-25", actual_minutes=20, notes="Speaking practice")
    
    summary = get_wasted_time_summary(test_db, "2026-10-25")
    assert summary["confirmed_wasted_minutes"] == 45
    assert summary["english_shortfall_minutes"] == 10
    assert summary["total_unmet_minutes"] >= 55
    
    # 3. Test graph data retrieval
    graph_data = get_wasted_time_graph_data(test_db, "2026-10-25", "2026-10-31")
    today_point = next((p for p in graph_data if p["date"] == "2026-10-25"), None)
    assert today_point is not None
    assert today_point["confirmed_wasted_minutes"] == 45
    assert today_point["english_shortfall_minutes"] == 10

def test_daily_dsa_two_topic_names_only(test_db):
    """Verifies that daily DSA returns exactly two syllabus topic names (not code questions) and tracks completion."""
    dsa_res = get_daily_dsa_topics(test_db, "2026-10-25")
    topics = dsa_res["topics"]
    assert len(topics) == 2
    for t in topics:
        assert "topic_name" in t
        assert len(t["topic_name"]) > 0
        assert t["status"] == "Pending"

    # Mark first topic as completed with 25 minutes
    topic_id = topics[0]["id"]
    updated = update_daily_dsa_topic(test_db, topic_id, is_completed=True, time_spent_minutes=25, notes="Practiced linked lists")
    assert updated["status"] == "Solved"
    assert updated["time_spent_minutes"] == 25

def test_english_speaking_simple_workflow(test_db):
    """Verifies simple English workflow: target 30m, actual entered, shortfall computed and updated."""
    # Day 1: 30 minutes practiced -> 0 shortfall
    res1 = save_english_practice(test_db, "2026-10-25", actual_minutes=30)
    assert res1["actual_minutes"] == 30
    assert res1["shortfall_minutes"] == 0
    assert res1["is_completed"] == 1

    # Update Day 1: corrected to 20 minutes -> 10 shortfall
    res2 = save_english_practice(test_db, "2026-10-25", actual_minutes=20)
    assert res2["actual_minutes"] == 20
    assert res2["shortfall_minutes"] == 10

    status = get_english_status_today(test_db, "2026-10-25")
    assert status["actual_minutes"] == 20
    assert status["shortfall_minutes"] == 10

def test_full_schedule_horizon_multi_subject(test_db):
    """Verifies that scheduler builds a day-by-day plan through exam horizon with all 4 subjects interleaved."""
    set_setting(test_db, "simulated_today", "2026-10-25")
    set_setting(test_db, "first_exam_date", "2026-11-26")
    set_setting(test_db, "revision_buffer_days", 7)
    
    scheduler = StudyScheduler(test_db)
    res = scheduler.generate_initial_schedule(preserve_completed=False)
    assert res["success"]
    assert res["tasks_scheduled"] > 100
    assert res["dates_covered_count"] >= 40

    cursor = test_db.cursor()
    # Check 2026-10-28 (Phase 2 normal multi-subject day)
    cursor.execute("""
        SELECT s.code, ss.duration_minutes
        FROM study_schedules ss
        JOIN subjects s ON ss.subject_id = s.id
        WHERE ss.scheduled_date = '2026-10-28'
    """)
    rows = cursor.fetchall()
    codes = {r["code"] for r in rows}
    total_mins = sum(r["duration_minutes"] for r in rows)
    
    # Must contain all 4 subjects
    assert "CSN 3003" in codes
    assert "CSN 3001" in codes
    assert "CSN 3004" in codes
    assert "CSN 3002" in codes
    # Total academic study exactly matches 240m target
    assert total_mins == 240
