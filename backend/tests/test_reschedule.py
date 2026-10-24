from datetime import datetime
from backend.database import set_setting
from backend.scheduler import StudyScheduler

def test_missed_task_adaptive_rescheduling(test_db):
    set_setting(test_db, "simulated_today", "2026-10-25")
    set_setting(test_db, "first_exam_date", "2026-11-26")
    set_setting(test_db, "revision_buffer_days", 7)
    set_setting(test_db, "weekday_minutes", 180)
    set_setting(test_db, "weekend_minutes", 300)

    scheduler = StudyScheduler(test_db)
    scheduler.generate_initial_schedule(preserve_completed=False)

    cursor = test_db.cursor()
    # Pick the first scheduled task on today's date
    cursor.execute("SELECT id, topic_id, duration_minutes FROM study_schedules WHERE scheduled_date = '2026-10-25' LIMIT 1")
    task = cursor.fetchone()
    assert task is not None
    task_id = task["id"]
    duration = task["duration_minutes"]

    # Mark as MISSED
    result = scheduler.reschedule_unfinished_work(
        changed_schedule_id=task_id,
        new_status="MISSED",
        actual_minutes=0,
        completion_percentage=0
    )
    assert result["success"]
    assert len(result["rescheduled_to_dates"]) > 0

    # Verify original task is MISSED
    cursor.execute("SELECT status FROM study_schedules WHERE id = ?", (task_id,))
    assert cursor.fetchone()["status"] == "MISSED"

    # Verify a new pending task exists for this topic on a future date
    cursor.execute("""
        SELECT scheduled_date, duration_minutes, reasoning 
        FROM study_schedules 
        WHERE topic_id = ? AND status = 'PENDING' AND id != ?
    """, (task["topic_id"], task_id))
    new_tasks = cursor.fetchall()
    assert len(new_tasks) > 0
    assert "Rescheduled" in new_tasks[0]["reasoning"]

def test_partial_completion_carries_only_remaining_portion(test_db):
    set_setting(test_db, "simulated_today", "2026-10-25")
    set_setting(test_db, "first_exam_date", "2026-11-26")
    set_setting(test_db, "revision_buffer_days", 7)

    scheduler = StudyScheduler(test_db)
    scheduler.generate_initial_schedule(preserve_completed=False)

    cursor = test_db.cursor()
    cursor.execute("SELECT id, topic_id, duration_minutes FROM study_schedules WHERE scheduled_date = '2026-10-25' LIMIT 1")
    task = cursor.fetchone()
    task_id = task["id"]
    original_duration = task["duration_minutes"] # e.g. 60 min

    # Mark 50% completed with 30 min spent
    result = scheduler.reschedule_unfinished_work(
        changed_schedule_id=task_id,
        new_status="PARTIALLY_COMPLETED",
        actual_minutes=original_duration // 2,
        completion_percentage=50
    )
    assert result["success"]

    # Verify rescheduled task has ~50% remaining minutes
    cursor.execute("""
        SELECT duration_minutes FROM study_schedules 
        WHERE topic_id = ? AND status = 'PENDING' AND id != ?
    """, (task["topic_id"], task_id))
    rescheduled = cursor.fetchone()
    assert rescheduled is not None
    assert rescheduled["duration_minutes"] == original_duration - (original_duration // 2)

def test_completed_tasks_preserved_across_regeneration(test_db):
    set_setting(test_db, "simulated_today", "2026-10-25")
    scheduler = StudyScheduler(test_db)
    scheduler.generate_initial_schedule(preserve_completed=False)

    cursor = test_db.cursor()
    cursor.execute("SELECT id FROM study_schedules LIMIT 2")
    task_ids = [r["id"] for r in cursor.fetchall()]

    for tid in task_ids:
        cursor.execute("UPDATE study_schedules SET status = 'COMPLETED', completion_percentage = 100 WHERE id = ?", (tid,))
    test_db.commit()

    # Regenerate with preserve_completed=True
    scheduler.generate_initial_schedule(preserve_completed=True)

    # Check that completed tasks are still intact
    for tid in task_ids:
        cursor.execute("SELECT status, completion_percentage FROM study_schedules WHERE id = ?", (tid,))
        row = cursor.fetchone()
        assert row is not None
        assert row["status"] == "COMPLETED"
        assert row["completion_percentage"] == 100
