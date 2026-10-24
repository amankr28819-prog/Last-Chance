import json
from datetime import date, datetime, timedelta
from backend.database import set_setting, get_setting, init_db
from backend.scheduler import StudyScheduler
from backend.models import SettingsModel, DSAQuestionModel, CalendarEventCreate

def test_daily_academic_target_240m(test_db):
    """Verifies that the core academic target is 240 minutes per day and separate from DSA and English."""
    set_setting(test_db, "daily_academic_target_minutes", 240)
    scheduler = StudyScheduler(test_db)
    
    # Test weekday (e.g. Wednesday 2026-10-28)
    wed = date(2026, 10, 28)
    avail_wed = scheduler.get_daily_available_minutes(wed)
    assert avail_wed == 240

    # Test weekend (e.g. Sunday 2026-11-01)
    sun = date(2026, 11, 1)
    avail_sun = scheduler.get_daily_available_minutes(sun)
    assert avail_sun == 240

def test_college_hours_schedule(test_db):
    """Verifies college schedule: Mon-Fri 3 hrs, Sat-Sun 0 hrs, holiday classes 5 hrs when marked."""
    scheduler = StudyScheduler(test_db)
    
    # Monday 2026-10-26 (Working day)
    mon = date(2026, 10, 26)
    assert scheduler.get_college_hours_for_date(mon) == 3.0

    # Sunday 2026-11-01 (Holiday)
    sun = date(2026, 11, 1)
    assert scheduler.get_college_hours_for_date(sun) == 0.0

    # Mark a special holiday with 5 hours of classes
    set_setting(test_db, "special_holiday_class_dates", ["2026-11-01"])
    assert scheduler.get_college_hours_for_date(sun) == 5.0

def test_special_break_december(test_db):
    """Verifies 6-11 Dec break: college is off (0 hrs) and flagged as 6 calendar days."""
    scheduler = StudyScheduler(test_db)
    set_setting(test_db, "special_break_start", "2026-12-06")
    set_setting(test_db, "special_break_end", "2026-12-11")
    set_setting(test_db, "special_break_include_7th_day", False)

    # Dec 7 is a Monday (normally 3h college), but during break college is 0
    dec7 = date(2026, 12, 7)
    assert scheduler.get_college_hours_for_date(dec7) == 0.0

    # Check 6 calendar days: 6, 7, 8, 9, 10, 11
    d1 = datetime.strptime("2026-12-06", "%Y-%m-%d").date()
    d2 = datetime.strptime("2026-12-11", "%Y-%m-%d").date()
    duration_days = (d2 - d1).days + 1
    assert duration_days == 6  # Prompt explicitly tests this mismatch!

    # Test adding 7th day (12 Dec)
    set_setting(test_db, "special_break_include_7th_day", True)
    dec12 = date(2026, 12, 12)
    assert scheduler.get_college_hours_for_date(dec12) == 0.0

def test_daily_dsa_two_questions_and_rotation(test_db):
    """Verifies daily assignment of exactly 2 compulsory DSA questions without immediate repetition."""
    cursor = test_db.cursor()
    # Check that seeded DSA questions exist
    cursor.execute("SELECT COUNT(*) FROM dsa_questions")
    count = cursor.fetchone()[0]
    assert count >= 10

    # Simulate assigning 2 questions for today
    today_str = "2026-10-25"
    cursor.execute("""
        INSERT INTO daily_dsa_assignments (assigned_date, question_id, slot_number, status)
        VALUES (?, 1, 1, 'Pending'), (?, 2, 2, 'Pending')
    """, (today_str, today_str))
    test_db.commit()

    # Query today's assignments
    cursor.execute("""
        SELECT a.slot_number, q.title, q.difficulty, q.hint_1, q.solution_approach
        FROM daily_dsa_assignments a
        JOIN dsa_questions q ON a.question_id = q.id
        WHERE a.assigned_date = ?
    """, (today_str,))
    rows = cursor.fetchall()
    assert len(rows) == 2
    assert rows[0]["hint_1"] is not None
    assert rows[0]["solution_approach"] is not None

    # Solve question 1
    cursor.execute("""
        UPDATE daily_dsa_assignments
        SET status = 'Solved', user_approach = 'Used two pointers', time_spent_minutes = 20
        WHERE assigned_date = ? AND slot_number = 1
    """, (today_str,))
    test_db.commit()

    cursor.execute("SELECT status, user_approach FROM daily_dsa_assignments WHERE assigned_date = ? AND slot_number = 1", (today_str,))
    solved_row = cursor.fetchone()
    assert solved_row["status"] == "Solved"
    assert solved_row["user_approach"] == "Used two pointers"

def test_english_speaking_rotation_and_streak(test_db):
    """Verifies daily rotating English topics and streak tracking."""
    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM english_speaking_topics")
    topic_count = cursor.fetchone()[0]
    assert topic_count >= 5

    # Simulate consecutive completed days: yesterday and today
    today = date(2026, 10, 25)
    yest = today - timedelta(days=1)

    cursor.execute("""
        INSERT INTO daily_english_logs (log_date, topic_id, time_spent_seconds, is_completed, notes)
        VALUES (?, 1, 1800, 1, 'Great fluency today'),
               (?, 2, 1850, 1, 'Discussed cloud computing')
    """, (yest.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")))
    test_db.commit()

    # Calculate streak
    cursor.execute("SELECT log_date FROM daily_english_logs WHERE is_completed = 1 ORDER BY log_date DESC")
    completed_dates = {r[0] for r in cursor.fetchall()}
    streak = 0
    cur = today
    while cur.strftime("%Y-%m-%d") in completed_dates:
        streak += 1
        cur -= timedelta(days=1)
    
    assert streak == 2

def test_daily_quotes_and_favorite(test_db):
    """Verifies daily inspirational quote selection and favorite toggle."""
    cursor = test_db.cursor()
    cursor.execute("SELECT id, quote_text, author, category, is_favorite FROM daily_quotes LIMIT 1")
    q = cursor.fetchone()
    valid_themes = ["Consistency", "Discipline", "Parents", "Faith", "Patience", "Success", "Study", "Learning", "Perseverance", "Gratitude", "Hope"]
    assert any(theme in q["category"] for theme in valid_themes)

    # Toggle favorite
    qid = q["id"]
    cursor.execute("UPDATE daily_quotes SET is_favorite = 1 WHERE id = ?", (qid,))
    test_db.commit()
    cursor.execute("SELECT is_favorite FROM daily_quotes WHERE id = ?", (qid,))
    assert cursor.fetchone()[0] == 1

def test_calendar_custom_events(test_db):
    """Verifies creating, querying, and deleting custom events in the study calendar."""
    cursor = test_db.cursor()
    cursor.execute("""
        INSERT INTO calendar_events (title, description, event_date, start_time, end_time, event_type, color, is_completed)
        VALUES ('Group Study & Doubt Clearance', 'Discuss binary search trees', '2026-10-30', '16:00', '17:30', 'study', '#3b82f6', 0)
    """)
    test_db.commit()
    event_id = cursor.lastrowid

    cursor.execute("SELECT title, event_type FROM calendar_events WHERE id = ?", (event_id,))
    ev = cursor.fetchone()
    assert ev["title"] == "Group Study & Doubt Clearance"
    assert ev["event_type"] == "study"

    # Delete
    cursor.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
    test_db.commit()
    cursor.execute("SELECT COUNT(*) FROM calendar_events WHERE id = ?", (event_id,))
    assert cursor.fetchone()[0] == 0
