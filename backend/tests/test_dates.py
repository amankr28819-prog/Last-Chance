from backend.database import set_setting
from backend.scheduler import StudyScheduler

def test_first_pass_deadline_calculation(test_db):
    set_setting(test_db, "simulated_today", "2026-10-25")
    set_setting(test_db, "first_exam_date", "2026-11-26")
    set_setting(test_db, "revision_buffer_days", 7)
    
    scheduler = StudyScheduler(test_db)
    dates = scheduler.calculate_dates()
    
    assert dates["first_exam_str"] == "2026-11-26"
    assert dates["first_pass_deadline_str"] == "2026-11-19"
    assert dates["buffer_days"] == 7
    assert dates["days_to_exam"] == 32
    assert dates["days_to_deadline"] == 25
    assert not dates["is_past_exam"]
    assert not dates["is_past_deadline"]

def test_exam_date_change_recalculates_deadline(test_db):
    set_setting(test_db, "simulated_today", "2026-10-25")
    # Move exam to Dec 10, 2026 with 7-day buffer -> deadline Dec 3
    set_setting(test_db, "first_exam_date", "2026-12-10")
    set_setting(test_db, "revision_buffer_days", 7)

    scheduler = StudyScheduler(test_db)
    dates = scheduler.calculate_dates()

    assert dates["first_exam_str"] == "2026-12-10"
    assert dates["first_pass_deadline_str"] == "2026-12-03"
    assert dates["days_to_exam"] == 46
    assert dates["days_to_deadline"] == 39

def test_past_deadline_detection(test_db):
    set_setting(test_db, "simulated_today", "2026-11-20")
    set_setting(test_db, "first_exam_date", "2026-11-26")
    set_setting(test_db, "revision_buffer_days", 7) # deadline 2026-11-19

    scheduler = StudyScheduler(test_db)
    dates = scheduler.calculate_dates()
    feasibility = scheduler.assess_feasibility()

    assert dates["is_past_deadline"]
    assert feasibility["status_label"] == "PAST_DEADLINE"
    assert "in the past" in feasibility["warning_message"]

def test_month_and_year_boundaries(test_db):
    set_setting(test_db, "simulated_today", "2027-12-28")
    set_setting(test_db, "first_exam_date", "2028-01-05")
    set_setting(test_db, "revision_buffer_days", 7)

    scheduler = StudyScheduler(test_db)
    dates = scheduler.calculate_dates()

    assert dates["first_pass_deadline_str"] == "2027-12-29"
    assert dates["days_to_deadline"] == 1
    assert dates["days_to_exam"] == 8
