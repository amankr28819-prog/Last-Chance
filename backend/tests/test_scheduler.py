from datetime import datetime
from backend.database import set_setting
from backend.scheduler import StudyScheduler

def test_daily_available_capacity_weekdays_vs_weekends(test_db):
    set_setting(test_db, "weekday_minutes", 180)
    set_setting(test_db, "weekend_minutes", 300)
    set_setting(test_db, "blocked_dates", ["2026-10-31"])
    set_setting(test_db, "study_windows", [])

    scheduler = StudyScheduler(test_db)
    
    # 2026-10-26 is Monday -> 180
    monday = datetime.strptime("2026-10-26", "%Y-%m-%d").date()
    assert scheduler.get_daily_available_minutes(monday) == 180

    # 2026-10-25 is Sunday -> 300
    sunday = datetime.strptime("2026-10-25", "%Y-%m-%d").date()
    assert scheduler.get_daily_available_minutes(sunday) == 300

    # 2026-10-31 is blocked -> 0
    blocked_day = datetime.strptime("2026-10-31", "%Y-%m-%d").date()
    assert scheduler.get_daily_available_minutes(blocked_day) == 0

def test_prerequisite_ordering_strictly_respected(test_db):
    set_setting(test_db, "simulated_today", "2026-10-25")
    set_setting(test_db, "first_exam_date", "2026-11-26")
    set_setting(test_db, "revision_buffer_days", 7)
    set_setting(test_db, "weekday_minutes", 240)
    set_setting(test_db, "weekend_minutes", 360)

    scheduler = StudyScheduler(test_db)
    res = scheduler.generate_initial_schedule(preserve_completed=False)
    assert res["success"]

    cursor = test_db.cursor()
    cursor.execute("""
        SELECT topic_id, scheduled_date, id FROM study_schedules
        ORDER BY scheduled_date ASC, id ASC
    """)
    schedules = cursor.fetchall()
    
    # topic_id -> earliest scheduled date & id
    scheduled_order = {}
    for row in schedules:
        tid = row["topic_id"]
        if tid not in scheduled_order:
            scheduled_order[tid] = (row["scheduled_date"], row["id"])

    # Check all prerequisites in DB
    cursor.execute("SELECT topic_id, prerequisite_topic_id FROM prerequisites")
    prereqs = cursor.fetchall()

    for p in prereqs:
        dependent_id = p["topic_id"]
        prereq_id = p["prerequisite_topic_id"]

        if dependent_id in scheduled_order and prereq_id in scheduled_order:
            dep_date, dep_id = scheduled_order[dependent_id]
            pre_date, pre_id = scheduled_order[prereq_id]
            # Prerequisite MUST be scheduled before or on same day earlier in sequence
            assert (pre_date < dep_date) or (pre_date == dep_date and pre_id < dep_id), (
                f"Prerequisite violation: Topic {dependent_id} scheduled at ({dep_date}, {dep_id}) "
                f"before prerequisite {prereq_id} at ({pre_date}, {pre_id})"
            )

def test_daily_capacity_limit_never_exceeded(test_db):
    set_setting(test_db, "simulated_today", "2026-10-25")
    set_setting(test_db, "first_exam_date", "2026-11-26")
    set_setting(test_db, "revision_buffer_days", 7)
    set_setting(test_db, "weekday_minutes", 180)
    set_setting(test_db, "weekend_minutes", 300)

    scheduler = StudyScheduler(test_db)
    scheduler.generate_initial_schedule(preserve_completed=False)

    cursor = test_db.cursor()
    cursor.execute("""
        SELECT scheduled_date, SUM(duration_minutes) as daily_scheduled
        FROM study_schedules
        WHERE status = 'PENDING' AND task_type = 'NEW_LEARNING'
        GROUP BY scheduled_date
    """)
    daily_allocations = cursor.fetchall()

    for row in daily_allocations:
        d = datetime.strptime(row["scheduled_date"], "%Y-%m-%d").date()
        daily_cap = scheduler.get_daily_available_minutes(d)
        assert row["daily_scheduled"] <= daily_cap, (
            f"Daily capacity exceeded on {row['scheduled_date']}: {row['daily_scheduled']} > {daily_cap}"
        )

def test_mastery_reduces_remaining_effort(test_db):
    scheduler = StudyScheduler(test_db)
    
    t_not_started = {"estimated_minutes": 100, "mastery_level": "NOT_STARTED"}
    assert scheduler.calculate_topic_remaining_effort(t_not_started) == 100

    t_confident = {"estimated_minutes": 100, "mastery_level": "CONFIDENT"}
    assert scheduler.calculate_topic_remaining_effort(t_confident) == 25

    t_mastered = {"estimated_minutes": 100, "mastery_level": "MASTERED"}
    assert scheduler.calculate_topic_remaining_effort(t_mastered) == 0
