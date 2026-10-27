import os
import shutil
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.database import (
    get_connection, init_db, get_setting, set_setting, DB_PATH,
    log_wasted_time, get_wasted_time_summary, get_wasted_time_graph_data,
    get_daily_dsa_topics, update_daily_dsa_topic, get_english_status_today, save_english_practice,
    get_daily_study_plan, complete_study_shift, partially_complete_study_shift,
    reschedule_study_shift, undo_reschedule_shift, get_rescheduled_tasks, auto_reschedule_overdue_tasks,
    get_cumulative_study_totals, get_enhanced_wasted_time_summary, delete_wasted_time_log,
    add_handout, get_handouts, get_handout_by_id, update_handout, delete_handout,
    get_syllabus_tracker_data, update_topic_status_audit,
    add_doubt, get_doubts, resolve_doubt,
    get_stable_quote_of_the_day, toggle_quote_favorite, get_favorite_quotes,
    global_search, get_weekly_review, export_database_backup, restore_database_backup,
    add_redo_task, get_redo_tasks, update_redo_task, complete_redo_task, delete_redo_task,
    get_calendar_events_combined, create_calendar_event, update_calendar_event, delete_calendar_event,
    create_user, get_user_by_username, get_user_by_id, update_user_profile,
    get_missing_materials_checklist, get_handouts_course_hierarchy
)
from backend.models import (
    SubjectModel, SubjectUpdateModel, TopicModel, TopicUpdateModel,
    SettingsModel, TaskCompletionRequest, StartSessionRequest, FinishSessionRequest,
    FeasibilityReport, DSAQuestionModel, DSAAssignmentModel, DSAStatusUpdateRequest,
    EnglishTopicModel, DailyEnglishLogModel, EnglishLogSaveRequest, QuoteModel,
    CalendarEventModel, CalendarEventCreate, CalendarEventUpdate,
    WastedTimeLogCreate, WastedTimeLogModel, EnglishLogSimpleRequest,
    DSATopicAssignmentUpdate, TopicStatusUpdateRequest,
    ShiftCompleteRequest, ShiftPartialRequest, ShiftRescheduleRequest, RescheduleUndoRequest,
    HandoutUpdateModel, DoubtCreate, DoubtResolve, QuoteFavoriteRequest,
    RedoTaskCreate, RedoTaskUpdate, UserRegisterRequest, UserLoginRequest,
    TokenResponse, UserProfileUpdate, DSAReplaceRequest, DSANotesUpdate,
    ThemeUpdateRequest
)
from backend.auth import (
    hash_password, verify_password, create_access_token, decode_access_token,
    get_optional_current_user, get_required_current_user
)
from backend.scheduler import StudyScheduler
from backend.syllabus_parser import SyllabusParser
from backend.timetable_data import TIMETABLE_DAYS, import_official_timetable

from backend.storage import storage_service

# Ensure DB is initialized
init_db()

app = FastAPI(
    title="Last Chance API",
    description="Last Chance — Your Personal Adaptive Academic Study & Exam Planner",
    version="2.0.0"
)

cors_origins_env = os.environ.get("CORS_ORIGINS", "*").strip()
if cors_origins_env and cors_origins_env != "*":
    origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Dependency for DB connection
def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()

# ----------------- DATE, TIME & FEASIBILITY ENDPOINTS -----------------

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Last Chance", "version": "2.0.0"}

@app.get("/api/time")
def get_current_time(conn=Depends(get_db)):
    """Returns the real, dynamic local time, countdown to midnight, and daily commitment tracking for Asia/Kolkata."""
    now = datetime.now()
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    today = date_info["today"]
    today_str = today.strftime("%Y-%m-%d")

    # Time left until midnight
    midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
    diff = midnight - now
    sec_to_midnight = max(0, int(diff.total_seconds()))
    hours_left = sec_to_midnight // 3600
    minutes_left = (sec_to_midnight % 3600) // 60
    seconds_left = sec_to_midnight % 60

    # Today's academic study minutes completed
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(SUM(actual_minutes), 0) as completed,
               COALESCE(SUM(duration_minutes), 0) as planned
        FROM study_schedules
        WHERE scheduled_date = ?
    """, (today_str,))
    study_r = cursor.fetchone()
    acad_completed = study_r["completed"] if study_r else 0
    acad_planned = study_r["planned"] if study_r else 240
    acad_target = int(get_setting(conn, "daily_academic_target_minutes", 240))
    acad_remaining = max(0, acad_target - acad_completed)

    # English speaking status
    eng_status = get_english_status_today(conn, today_str)

    # DSA topics status
    dsa_status = get_daily_dsa_topics(conn, today_str)

    return {
        "iso": now.isoformat(),
        "date_str": today_str,
        "time_str": now.strftime("%H:%M:%S"),
        "formatted_date": today.strftime("%A, %d %B %Y"),
        "formatted_time": now.strftime("%I:%M:%S %p"),
        "weekday": today.strftime("%A"),
        "day": today.day,
        "month": today.month,
        "month_name": today.strftime("%B"),
        "year": today.year,
        "timezone": get_setting(conn, "time_zone", "Asia/Kolkata"),
        "simulated": get_setting(conn, "simulated_today", None) is not None,
        "time_left_today": {
            "seconds_to_midnight": sec_to_midnight,
            "hours": hours_left,
            "minutes": minutes_left,
            "seconds": seconds_left,
            "formatted": f"{hours_left}h {minutes_left}m {seconds_left}s left today",
            "academic_target_minutes": acad_target,
            "academic_planned_minutes": acad_planned,
            "academic_completed_minutes": acad_completed,
            "academic_remaining_minutes": acad_remaining,
            "english_target_minutes": 30,
            "english_actual_minutes": eng_status["actual_minutes"],
            "english_shortfall_minutes": eng_status["shortfall_minutes"],
            "english_completed": eng_status["is_completed"],
            "dsa_completed_count": dsa_status["completed_count"],
            "dsa_target_count": 2,
            "dsa_is_completed": dsa_status["is_completed"]
        }
    }

@app.get("/api/dates")
def get_date_info(conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    return scheduler.calculate_dates()

@app.get("/api/feasibility")
def get_feasibility(conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    return scheduler.assess_feasibility()

# ----------------- SETTINGS & ONBOARDING -----------------

@app.get("/api/settings")
def get_all_settings(conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {}
    for row in cursor.fetchall():
        try:
            settings[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            settings[row["key"]] = row["value"]

    # Normalize aliases
    if "academic_daily_target_minutes" in settings and "daily_academic_target_minutes" not in settings:
        settings["daily_academic_target_minutes"] = settings["academic_daily_target_minutes"]
    if "daily_academic_target_minutes" in settings and "academic_daily_target_minutes" not in settings:
        settings["academic_daily_target_minutes"] = settings["daily_academic_target_minutes"]

    if "english_daily_target_minutes" in settings and "english_speaking_target_minutes" not in settings:
        settings["english_speaking_target_minutes"] = settings["english_daily_target_minutes"]
    if "english_speaking_target_minutes" in settings and "english_daily_target_minutes" not in settings:
        settings["english_daily_target_minutes"] = settings["english_speaking_target_minutes"]

    if "dsa_daily_question_count" in settings and "daily_dsa_count" not in settings:
        settings["daily_dsa_count"] = settings["dsa_daily_question_count"]
    if "daily_dsa_count" in settings and "dsa_daily_question_count" not in settings:
        settings["dsa_daily_question_count"] = settings["daily_dsa_count"]

    return settings

@app.put("/api/settings")
def update_settings(settings: Dict[str, Any], conn=Depends(get_db)):
    for k, v in settings.items():
        set_setting(conn, k, v)
    
    # If first_exam_date or revision_buffer_days changed, update syllabus_deadline automatically
    if "first_exam_date" in settings or "revision_buffer_days" in settings:
        exam_str = get_setting(conn, "first_exam_date", "2026-11-26")
        buf_days = int(get_setting(conn, "revision_buffer_days", 7))
        try:
            ex_date = datetime.strptime(exam_str, "%Y-%m-%d").date()
            dl_date = ex_date - timedelta(days=buf_days)
            set_setting(conn, "syllabus_deadline", dl_date.strftime("%Y-%m-%d"))
        except ValueError:
            pass

    return {"success": True, "settings": get_all_settings(conn)}

# ----------------- SUBJECTS ENDPOINTS -----------------

@app.get("/api/subjects")
def list_subjects(conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            s.*,
            (SELECT COUNT(*) FROM units u WHERE u.subject_id = s.id) as units_count,
            (SELECT COUNT(*) FROM topics t WHERE t.subject_id = s.id) as topics_count,
            (SELECT COUNT(*) FROM topics t WHERE t.subject_id = s.id AND t.mastery_level IN ('CONFIDENT', 'MASTERED')) as mastered_count,
            (SELECT COALESCE(SUM(estimated_minutes), 0) FROM topics t WHERE t.subject_id = s.id) as total_estimated_minutes,
            (SELECT COALESCE(SUM(actual_minutes), 0) FROM study_schedules sc WHERE sc.subject_id = s.id AND sc.status = 'COMPLETED') as total_studied_minutes
        FROM subjects s
        ORDER BY s.priority DESC, s.exam_date ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    return rows

@app.get("/api/subjects/{subject_id}")
def get_subject_detail(subject_id: int, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    subj = cursor.fetchone()
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    subj_dict = dict(subj)

    cursor.execute("""
        SELECT u.*, 
            (SELECT COUNT(*) FROM topics t WHERE t.unit_id = u.id) as topics_count,
            (SELECT COUNT(*) FROM topics t WHERE t.unit_id = u.id AND t.mastery_level IN ('CONFIDENT', 'MASTERED')) as completed_count
        FROM units u 
        WHERE u.subject_id = ? 
        ORDER BY u.unit_number ASC
    """, (subject_id,))
    units = [dict(u) for u in cursor.fetchall()]

    for u in units:
        cursor.execute("""
            SELECT t.*,
                (SELECT GROUP_CONCAT(title, '||') FROM subtopics st WHERE st.topic_id = t.id) as subtopics_joined
            FROM topics t
            WHERE t.unit_id = ?
            ORDER BY t.order_index ASC
        """, (u["id"],))
        t_rows = []
        for tr in cursor.fetchall():
            td = dict(tr)
            td["subtopics"] = td["subtopics_joined"].split("||") if td.get("subtopics_joined") else []
            td.pop("subtopics_joined", None)
            t_rows.append(td)
        u["topics"] = t_rows

    subj_dict["units"] = units
    return subj_dict

@app.put("/api/subjects/{subject_id}")
def update_subject(subject_id: int, update: SubjectUpdateModel, conn=Depends(get_db)):
    cursor = conn.cursor()
    fields = []
    values = []
    for k, v in update.model_dump(exclude_unset=True).items():
        fields.append(f"{k} = ?")
        values.append(v)
    if not fields:
        return {"success": True}
    values.append(subject_id)
    cursor.execute(f"UPDATE subjects SET {', '.join(fields)} WHERE id = ?", tuple(values))
    conn.commit()
    return {"success": True}

@app.post("/api/subjects")
def create_subject(subj: SubjectModel, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO subjects (code, name, credits, total_lectures, exam_date, priority, color)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (subj.code, subj.name, subj.credits, subj.total_lectures, subj.exam_date, subj.priority, subj.color))
    new_id = cursor.lastrowid
    conn.commit()
    return {"success": True, "id": new_id}

# ----------------- SYLLABUS & TOPICS -----------------

@app.get("/api/syllabus")
def get_full_syllabus(subject_id: Optional[int] = None, mastery: Optional[str] = None, conn=Depends(get_db)):
    cursor = conn.cursor()
    query = """
        SELECT 
            t.id, t.title, t.estimated_minutes, t.base_minutes, t.mastery_level,
            t.is_mandatory, t.is_official, t.source_doc, t.order_index,
            u.id as unit_id, u.unit_number, u.title as unit_title,
            s.id as subject_id, s.code as subject_code, s.name as subject_name, s.color as subject_color,
            (SELECT GROUP_CONCAT(title, '||') FROM subtopics st WHERE st.topic_id = t.id) as subtopics_joined,
            (SELECT MAX(scheduled_date) FROM study_schedules sc WHERE sc.topic_id = t.id) as next_scheduled_date,
            (SELECT COUNT(*) FROM revision_items ri WHERE ri.topic_id = t.id AND ri.status = 'COMPLETED') as revisions_completed
        FROM topics t
        JOIN units u ON t.unit_id = u.id
        JOIN subjects s ON t.subject_id = s.id
        WHERE 1=1
    """
    params = []
    if subject_id:
        query += " AND s.id = ?"
        params.append(subject_id)
    if mastery:
        query += " AND t.mastery_level = ?"
        params.append(mastery)
    
    query += " ORDER BY s.id ASC, u.unit_number ASC, t.order_index ASC"
    cursor.execute(query, tuple(params))
    
    topics = []
    for r in cursor.fetchall():
        d = dict(r)
        d["subtopics"] = d["subtopics_joined"].split("||") if d.get("subtopics_joined") else []
        d.pop("subtopics_joined", None)
        topics.append(d)
    return topics

@app.put("/api/topics/{topic_id}")
def update_topic(topic_id: int, update: TopicUpdateModel, conn=Depends(get_db)):
    cursor = conn.cursor()
    fields = []
    values = []
    dump = update.model_dump(exclude_unset=True)
    subtopics = dump.pop("subtopics", None)
    prereqs = dump.pop("prerequisites", None)

    for k, v in dump.items():
        fields.append(f"{k} = ?")
        values.append(v)

    if fields:
        values.append(topic_id)
        cursor.execute(f"UPDATE topics SET {', '.join(fields)} WHERE id = ?", tuple(values))

    if subtopics is not None:
        cursor.execute("DELETE FROM subtopics WHERE topic_id = ?", (topic_id,))
        for idx, st in enumerate(subtopics):
            cursor.execute("INSERT INTO subtopics (topic_id, title, order_index) VALUES (?, ?, ?)", (topic_id, st, idx))

    if prereqs is not None:
        cursor.execute("DELETE FROM prerequisites WHERE topic_id = ?", (topic_id,))
        for pid in prereqs:
            cursor.execute("INSERT INTO prerequisites (topic_id, prerequisite_topic_id) VALUES (?, ?)", (topic_id, pid))

    conn.commit()
    return {"success": True}

@app.post("/api/topics")
def create_topic(topic: TopicModel, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO topics (unit_id, subject_id, title, estimated_minutes, base_minutes, mastery_level, is_mandatory, is_official, source_doc, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (topic.unit_id, topic.subject_id, topic.title, topic.estimated_minutes, topic.estimated_minutes, topic.mastery_level, int(topic.is_mandatory), int(topic.is_official), topic.source_doc, topic.order_index))
    topic_id = cursor.lastrowid

    for idx, st in enumerate(topic.subtopics):
        cursor.execute("INSERT INTO subtopics (topic_id, title, order_index) VALUES (?, ?, ?)", (topic_id, st, idx))

    for pid in topic.prerequisites:
        cursor.execute("INSERT INTO prerequisites (topic_id, prerequisite_topic_id) VALUES (?, ?)", (topic_id, pid))

    conn.commit()
    return {"success": True, "id": topic_id}

@app.delete("/api/topics/{topic_id}")
def delete_topic(topic_id: int, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
    conn.commit()
    return {"success": True}

# ----------------- STUDY SCHEDULE & COMPLETION -----------------

@app.get("/api/schedule/today")
def get_today_schedule(conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    today_str = date_info["today_str"]

    plan = get_daily_study_plan(conn, today_str)
    quote = get_stable_quote_of_the_day(conn, today_str)
    study_totals = get_cumulative_study_totals(conn, today_str)
    wasted_summary = get_enhanced_wasted_time_summary(conn, today_str)
    feasibility = scheduler.assess_feasibility()
    college_hours_today = scheduler.get_college_hours_for_date(date_info["today"])

    return {
        "date_info": date_info,
        "college_hours": college_hours_today,
        "plan": plan,
        "shifts": plan["shifts"],
        "wrapup": plan["wrapup"],
        "tasks": plan["shifts"], # Backwards compatibility
        "academic_target_minutes": plan["academic_target_minutes"],
        "academic_completed_minutes": plan["academic_completed_minutes"],
        "academic_planned_minutes": plan["academic_planned_minutes"],
        "academic_remaining_minutes": plan["academic_remaining_minutes"],
        "academic_progress_pct": plan["academic_progress_pct"],
        "completion_rate": plan["academic_progress_pct"],
        "extra_academic_minutes": plan["extra_academic_minutes"],
        "shifts_total": plan["shifts_total"],
        "shifts_completed": plan["shifts_completed"],
        "wrapup_completed": plan["wrapup_completed"],
        "is_overloaded": plan["is_overloaded"],
        "today_quote": quote,
        "quote": quote,
        "study_totals": study_totals,
        "wasted_summary": wasted_summary,
        "english_target_minutes": int(get_setting(conn, "english_speaking_target_minutes", 30)),
        "dsa_target_count": int(get_setting(conn, "daily_dsa_count", 2)),
        "feasibility": feasibility
    }

@app.get("/api/schedule/day")
def get_schedule_day(date: Optional[str] = None, date_str: Optional[str] = None, conn=Depends(get_db)):
    """Returns the full 5-shift + wrapup plan for any specific date."""
    target_date = date or date_str
    if not target_date:
        scheduler = StudyScheduler(conn)
        target_date = scheduler.calculate_dates()["today_str"]
    return get_daily_study_plan(conn, target_date)

@app.post("/api/schedule/{schedule_id}/complete_shift")
def complete_shift_endpoint(schedule_id: int, req: Optional[ShiftCompleteRequest] = None, conn=Depends(get_db)):
    actual_mins = req.actual_minutes if req and req.actual_minutes is not None else 45
    notes = req.notes if req else None
    result = complete_study_shift(conn, schedule_id, actual_mins, notes)
    
    # Check if user requested to add this task to the Redo / Practice Again queue
    if req and req.add_to_redo:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sc.topic_id, sc.subject_id, sc.task_description, sc.scheduled_date,
                   sub.code as course_code, sub.name as course_name
            FROM study_schedules sc
            LEFT JOIN subjects sub ON sc.subject_id = sub.id
            WHERE sc.id = ?
        """, (schedule_id,))
        sch = cursor.fetchone()
        if sch:
            redo_id = add_redo_task(
                conn,
                topic_title=sch["task_description"] or "Study Shift",
                schedule_id=schedule_id,
                topic_id=sch["topic_id"],
                subject_id=sch["subject_id"],
                course_code=sch["course_code"],
                course_name=sch["course_name"],
                original_completion_date=sch["scheduled_date"],
                reason=req.redo_reason or "Added to Redo upon completion"
            )
            result["added_to_redo"] = True
            result["redo_task_id"] = redo_id

    return result

@app.post("/api/schedule/{schedule_id}/partial")
def partial_shift_endpoint(schedule_id: int, req: ShiftPartialRequest, conn=Depends(get_db)):
    return partially_complete_study_shift(conn, schedule_id, req.actual_minutes, req.notes, req.is_interrupted)

@app.post("/api/schedule/{schedule_id}/reschedule")
def reschedule_shift_endpoint(schedule_id: int, req: ShiftRescheduleRequest, conn=Depends(get_db)):
    target_d = req.new_date or req.to_date
    return reschedule_study_shift(conn, schedule_id, target_d, req.reason)

@app.post("/api/schedule/reschedule-undo")
def undo_reschedule_endpoint(req: RescheduleUndoRequest, conn=Depends(get_db)):
    return undo_reschedule_shift(conn, req.history_id)

@app.get("/api/schedule/rescheduled")
def get_rescheduled_endpoint(conn=Depends(get_db)):
    return {"rescheduled_tasks": get_rescheduled_tasks(conn)}

@app.post("/api/schedule/auto-reschedule")
def auto_reschedule_endpoint(as_of_date: Optional[str] = None, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    cur_d = as_of_date or scheduler.calculate_dates()["today_str"]
    return auto_reschedule_overdue_tasks(conn, cur_d)

@app.get("/api/import/preview")
def preview_timetable():
    """Returns a full review of the official 25-day study plan before committing import."""
    return {
        "status": "ready",
        "days_count": len(TIMETABLE_DAYS),
        "total_days": len(TIMETABLE_DAYS),
        "total_shifts": len(TIMETABLE_DAYS) * 5,
        "total_wrapup_sessions": len(TIMETABLE_DAYS),
        "total_wrapups": len(TIMETABLE_DAYS),
        "start_date": "2026-10-27",
        "end_date": "2026-11-20",
        "days": TIMETABLE_DAYS
    }

@app.post("/api/import/timetable")
def commit_official_timetable(force_overwrite: bool = False, conn=Depends(get_db)):
    """Imports the official Word timetable safely without duplicating tasks."""
    return import_official_timetable(conn, force_overwrite=force_overwrite)

@app.get("/api/study-time/totals")
def get_study_time_totals(date_str: Optional[str] = None, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    ref_d = date_str or scheduler.calculate_dates()["today_str"]
    return get_cumulative_study_totals(conn, ref_d)

@app.get("/api/schedule")
def get_schedules_range(start_date: Optional[str] = None, end_date: Optional[str] = None, conn=Depends(get_db)):
    cursor = conn.cursor()
    query = """
        SELECT 
            sc.*,
            t.title as topic_title,
            u.title as unit_title,
            s.name as subject_name, s.code as subject_code, s.color as subject_color
        FROM study_schedules sc
        JOIN topics t ON sc.topic_id = t.id
        JOIN units u ON t.unit_id = u.id
        JOIN subjects s ON sc.subject_id = s.id
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND sc.scheduled_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND sc.scheduled_date <= ?"
        params.append(end_date)
    
    query += " ORDER BY sc.scheduled_date ASC, sc.id ASC"
    cursor.execute(query, tuple(params))
    return [dict(r) for r in cursor.fetchall()]

@app.get("/api/schedule/full")
def get_full_horizon_schedule(conn=Depends(get_db)):
    """Returns the complete day-by-day study schedule through the final examination date (4 Dec 2026)."""
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            sc.*,
            t.title as topic_title,
            u.title as unit_title, u.unit_number,
            s.name as subject_name, s.code as subject_code, s.color as subject_color
        FROM study_schedules sc
        JOIN topics t ON sc.topic_id = t.id
        JOIN units u ON t.unit_id = u.id
        JOIN subjects s ON sc.subject_id = s.id
        ORDER BY sc.scheduled_date ASC, sc.id ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]

    # Group by date
    days_map = {}
    for r in rows:
        d = r["scheduled_date"]
        days_map.setdefault(d, []).append(r)

    timeline = []
    for d, items in sorted(days_map.items()):
        total_mins = sum(i["duration_minutes"] for i in items)
        comp_mins = sum(i["actual_minutes"] for i in items if i["status"] == "COMPLETED")
        timeline.append({
            "date": d,
            "tasks_count": len(items),
            "planned_minutes": total_mins,
            "completed_minutes": comp_mins,
            "tasks": items
        })

    return {
        "date_info": date_info,
        "total_sessions": len(rows),
        "days_count": len(timeline),
        "timeline": timeline
    }

@app.put("/api/topics/{topic_id}/status")
def update_topic_status(topic_id: int, req: TopicStatusUpdateRequest, conn=Depends(get_db)):
    """Explicit topic-level checklist completion control."""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE topics
        SET mastery_level = ?, notes = COALESCE(?, notes)
        WHERE id = ?
    """, (req.mastery_level, req.notes, topic_id))
    conn.commit()

    # If marked MASTERED or COMPLETED, update any pending schedule item for this topic
    if req.mastery_level in ("COMPLETED", "MASTERED"):
        cursor.execute("UPDATE study_schedules SET status = 'COMPLETED', actual_minutes = duration_minutes, completed_at = datetime('now') WHERE topic_id = ? AND status = 'PENDING'", (topic_id,))
        conn.commit()

    return {"success": True, "topic_id": topic_id, "mastery_level": req.mastery_level}

# ----------------- WASTED TIME & SHORTFALL ACCOUNTING -----------------

@app.get("/api/wasted-time/summary")
def get_wasted_time_report(date_str: Optional[str] = None, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    target_date = date_str or scheduler.calculate_dates()["today_str"]
    return get_enhanced_wasted_time_summary(conn, target_date)

@app.post("/api/wasted-time/log")
def log_wasted_time_entry(req: WastedTimeLogCreate, conn=Depends(get_db)):
    t_date = req.log_date or req.wasted_date
    if not t_date:
        scheduler = StudyScheduler(conn)
        t_date = scheduler.calculate_dates()["today_str"]
    r_text = req.notes or req.reason or ""
    new_id = log_wasted_time(conn, t_date, req.minutes, r_text, req.category)
    return {"success": True, "id": new_id, "summary": get_enhanced_wasted_time_summary(conn, t_date)}

@app.delete("/api/wasted-time/log/{log_id}")
def delete_wasted_time_entry(log_id: int, date_str: Optional[str] = None, conn=Depends(get_db)):
    success = delete_wasted_time_log(conn, log_id)
    scheduler = StudyScheduler(conn)
    ref_d = date_str or scheduler.calculate_dates()["today_str"]
    return {"success": success, "summary": get_enhanced_wasted_time_summary(conn, ref_d)}

@app.get("/api/wasted-time/graph")
def get_wasted_time_graph(start_date: Optional[str] = None, end_date: Optional[str] = None, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    s_date = start_date or (date_info["today"] - timedelta(days=7)).strftime("%Y-%m-%d")
    e_date = end_date or "2026-11-20"
    data = get_wasted_time_graph_data(conn, s_date, e_date)
    return {"data": data}

# ----------------- DAILY DSA TOPIC RECOMMENDATIONS -----------------

@app.get("/api/dsa/topics")
def get_daily_dsa_topic_recommendations(date_str: Optional[str] = None, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    target_date = date_str or scheduler.calculate_dates()["today_str"]
    return get_daily_dsa_topics(conn, target_date)

@app.put("/api/dsa/topic/{assignment_id}")
def update_dsa_topic_progress(assignment_id: int, req: DSATopicAssignmentUpdate, conn=Depends(get_db)):
    update_daily_dsa_topic(conn, assignment_id, req.status, req.time_spent_minutes, req.notes or "")
    return {"success": True}

# ----------------- SIMPLE ENGLISH PRACTICE LOGGING -----------------

@app.get("/api/english/status")
def get_english_practice_status(date_str: Optional[str] = None, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    target_date = date_str or scheduler.calculate_dates()["today_str"]
    return get_english_status_today(conn, target_date)

@app.post("/api/english/simple-log")
def log_english_practice_simple(req: EnglishLogSimpleRequest, conn=Depends(get_db)):
    result = save_english_practice(conn, req.log_date, req.actual_minutes, req.notes or "")
    return {"success": True, "data": result}

# ----------------- COURSES & UNITS CHECKLIST EXPLORER -----------------

@app.get("/api/courses")
def get_courses_hierarchy(conn=Depends(get_db)):
    """Returns Course -> Unit -> Topic complete hierarchy with completion indicators."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, name, credits, total_lectures, priority, color, exam_date FROM subjects ORDER BY id ASC")
    courses = [dict(r) for r in cursor.fetchall()]

    for c in courses:
        cursor.execute("SELECT id, unit_number, title, lecture_allocation FROM units WHERE subject_id = ? ORDER BY unit_number ASC", (c["id"],))
        units = [dict(u) for u in cursor.fetchall()]

        total_course_topics = 0
        completed_course_topics = 0
        total_course_minutes = 0

        for u in units:
            cursor.execute("""
                SELECT 
                    t.id, t.title, t.estimated_minutes, t.mastery_level, t.order_index, t.notes,
                    (SELECT GROUP_CONCAT(title, '||') FROM subtopics st WHERE st.topic_id = t.id) as subtopics_str
                FROM topics t
                WHERE t.unit_id = ?
                ORDER BY t.order_index ASC
            """, (u["id"],))
            topics = []
            u_completed = 0
            u_mins = 0
            for tr in cursor.fetchall():
                td = dict(tr)
                td["subtopics"] = td["subtopics_str"].split("||") if td.get("subtopics_str") else []
                td.pop("subtopics_str", None)
                if td["mastery_level"] in ("COMPLETED", "MASTERED"):
                    u_completed += 1
                u_mins += td["estimated_minutes"]
                topics.append(td)

            u["topics"] = topics
            u["topics_count"] = len(topics)
            u["completed_count"] = u_completed
            u["progress_percent"] = round((u_completed / len(topics) * 100), 1) if topics else 0.0
            u["total_minutes"] = u_mins

            total_course_topics += len(topics)
            completed_course_topics += u_completed
            total_course_minutes += u_mins

        c["units"] = units
        c["topics_count"] = total_course_topics
        c["completed_count"] = completed_course_topics
        c["progress_percent"] = round((completed_course_topics / total_course_topics * 100), 1) if total_course_topics else 0.0
        c["total_minutes"] = total_course_minutes
        c["total_hours"] = round(total_course_minutes / 60.0, 1)

    return courses

@app.post("/api/schedule/generate")
def generate_schedule(preserve_completed: bool = True, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    result = scheduler.generate_initial_schedule(preserve_completed=preserve_completed)
    return result

@app.post("/api/schedule/{schedule_id}/complete")
def update_task_completion(schedule_id: int, req: TaskCompletionRequest, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    result = scheduler.reschedule_unfinished_work(
        changed_schedule_id=schedule_id,
        new_status=req.status,
        actual_minutes=req.actual_minutes,
        completion_percentage=req.completion_percentage,
        remaining_minutes_override=req.remaining_minutes
    )
    
    # Update notes, confidence, practice
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE study_schedules 
        SET notes = ?, blockers = ?, confidence_rating = ?, practice_attempted = ?
        WHERE id = ?
    """, (req.notes, req.blockers, req.confidence_rating, int(req.practice_attempted), schedule_id))
    conn.commit()

    return result

# ----------------- STUDY SESSION (FOCUS MODE) -----------------

@app.post("/api/sessions/start")
def start_session(req: StartSessionRequest, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO study_sessions (topic_id, schedule_id, started_at)
        VALUES (?, ?, datetime('now'))
    """, (req.topic_id, req.schedule_id))
    session_id = cursor.lastrowid
    conn.commit()
    return {"success": True, "session_id": session_id}

@app.post("/api/sessions/finish")
def finish_session(req: FinishSessionRequest, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE study_sessions
        SET ended_at = datetime('now'), duration_seconds = ?, actual_minutes = ?,
            completion_percentage = ?, confidence_rating = ?, notes = ?
        WHERE id = ?
    """, (req.duration_seconds, req.actual_minutes, req.completion_percentage, req.confidence_rating, req.notes, req.session_id))
    
    # Also find associated schedule if any and update
    cursor.execute("SELECT schedule_id, topic_id FROM study_sessions WHERE id = ?", (req.session_id,))
    row = cursor.fetchone()
    if row and row["schedule_id"]:
        sched_id = row["schedule_id"]
        status = req.mark_task_status or ("COMPLETED" if req.completion_percentage >= 100 else "PARTIALLY_COMPLETED")
        scheduler = StudyScheduler(conn)
        scheduler.reschedule_unfinished_work(
            changed_schedule_id=sched_id,
            new_status=status,
            actual_minutes=req.actual_minutes,
            completion_percentage=req.completion_percentage
        )
    conn.commit()
    return {"success": True}

# ----------------- ANALYTICS & HISTORY -----------------

@app.get("/api/analytics")
def get_analytics(conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    feasibility = scheduler.assess_feasibility()
    date_info = scheduler.calculate_dates()
    today = date_info["today"]
    cursor = conn.cursor()

    # Graph A & B: Daily study time and target completion
    cursor.execute("""
        SELECT 
            scheduled_date as dt,
            COALESCE(SUM(actual_minutes), 0) as actual_mins,
            COALESCE(SUM(duration_minutes), 0) as planned_mins,
            COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_shifts_count,
            COUNT(CASE WHEN status != 'COMPLETED' THEN 1 END) as unfinished_shifts_count
        FROM study_schedules
        WHERE is_wrapup = 0
        GROUP BY scheduled_date
        ORDER BY scheduled_date ASC
    """)
    sched_by_date = {r["dt"]: dict(r) for r in cursor.fetchall()}

    # Confirmed wasted logs by date
    cursor.execute("SELECT log_date, SUM(minutes) as total FROM wasted_time_logs GROUP BY log_date")
    wasted_by_date = {r["log_date"]: r["total"] for r in cursor.fetchall()}

    graph_a_daily_study = []
    graph_b_daily_progress = []
    graph_c_wasted_time = []

    # Span from 2026-10-27 through 2026-11-20 (or dates with schedules)
    start_dt = date(2026, 10, 27)
    end_dt = max(today + timedelta(days=7), date(2026, 11, 20))
    cur = start_dt

    active_days_count = 0
    full_target_days_count = 0

    while cur <= end_dt:
        cur_str = cur.strftime("%Y-%m-%d")
        s_data = sched_by_date.get(cur_str, {"actual_mins": 0, "planned_mins": 240, "completed_shifts_count": 0, "unfinished_shifts_count": 5})
        act = s_data["actual_mins"]
        pln = s_data["planned_mins"] or 240
        wasted_val = wasted_by_date.get(cur_str, 0)
        shortfall_val = max(0, 240 - act) if cur <= today else 0

        h = act // 60
        m = act % 60
        act_formatted = f"{h}h {m}m" if h > 0 else f"{m}m"

        pct = min(100.0, round((act / 240.0) * 100, 1))
        extra_m = max(0, act - 240)

        if act > 0:
            active_days_count += 1
        if act >= 240:
            full_target_days_count += 1

        graph_a_daily_study.append({
            "date": cur_str,
            "day_label": cur.strftime("%d %b"),
            "actual_minutes": act,
            "planned_minutes": pln,
            "target_minutes": 240,
            "actual_formatted": act_formatted
        })

        graph_b_daily_progress.append({
            "date": cur_str,
            "day_label": cur.strftime("%d %b"),
            "progress_percent": pct,
            "extra_minutes": extra_m
        })

        graph_c_wasted_time.append({
            "date": cur_str,
            "day_label": cur.strftime("%d %b"),
            "confirmed_wasted_minutes": wasted_val,
            "academic_shortfall_minutes": shortfall_val
        })

        cur += timedelta(days=1)

    # Graph D: Weekly study summary (Monday-Sunday weeks)
    graph_d_weekly = []
    w_cur = date(2026, 10, 26) # Monday
    while w_cur <= end_dt:
        w_end = w_cur + timedelta(days=6)
        ws_str = w_cur.strftime("%Y-%m-%d")
        we_str = w_end.strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT 
                COALESCE(SUM(actual_minutes), 0) as act_sum,
                COALESCE(SUM(duration_minutes), 0) as pln_sum,
                COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as comp_cnt,
                COUNT(CASE WHEN status != 'COMPLETED' THEN 1 END) as unfin_cnt
            FROM study_schedules
            WHERE scheduled_date BETWEEN ? AND ? AND is_wrapup = 0
        """, (ws_str, we_str))
        w_row = cursor.fetchone()

        cursor.execute("SELECT COALESCE(SUM(minutes), 0) FROM wasted_time_logs WHERE log_date BETWEEN ? AND ?", (ws_str, we_str))
        w_wasted = cursor.fetchone()[0]

        w_act = w_row["act_sum"]
        w_pln = w_row["pln_sum"] or (240 * 7)
        achievement = round((w_act / w_pln * 100), 1) if w_pln > 0 else 0.0

        graph_d_weekly.append({
            "week_label": f"{w_cur.strftime('%d %b')} – {w_end.strftime('%d %b')}",
            "start_date": ws_str,
            "end_date": we_str,
            "total_academic_hours": round(w_act / 60, 1),
            "total_academic_minutes": w_act,
            "total_planned_hours": round(w_pln / 60, 1),
            "completed_shifts": w_row["comp_cnt"],
            "unfinished_shifts": w_row["unfin_cnt"],
            "daily_average_minutes": round(w_act / 7, 1),
            "target_achievement_percent": achievement,
            "confirmed_wasted_minutes": w_wasted
        })
        w_cur += timedelta(days=7)

    # Graph E: Course-wise progress
    cursor.execute("""
        SELECT 
            s.id, s.name, s.code, s.color,
            COUNT(DISTINCT t.id) as total_topics,
            COUNT(DISTINCT CASE WHEN t.mastery_level IN ('CONFIDENT', 'MASTERED', 'COMPLETED') THEN t.id END) as mastered_topics,
            COALESCE(SUM(sc.actual_minutes), 0) as total_actual_mins
        FROM subjects s
        LEFT JOIN topics t ON s.id = t.subject_id
        LEFT JOIN study_schedules sc ON sc.subject_id = s.id AND sc.is_wrapup = 0
        GROUP BY s.id
        ORDER BY s.id ASC
    """)
    course_progress = []
    for r in cursor.fetchall():
        t_tot = r["total_topics"]
        t_mast = r["mastered_topics"]
        pct = round((t_mast / t_tot * 100), 1) if t_tot > 0 else 0.0
        course_progress.append({
            "id": r["id"],
            "code": r["code"],
            "name": r["name"],
            "color": r["color"],
            "total_topics": t_tot,
            "mastered_topics": t_mast,
            "progress_percent": pct,
            "total_actual_hours": round(r["total_actual_mins"] / 60, 1),
            "total_actual_minutes": r["total_actual_mins"]
        })

    # Consistency & Streak
    consistency_data = {
        "active_study_days": active_days_count,
        "target_achieved_days": full_target_days_count,
        "total_tracked_days": len(graph_a_daily_study)
    }

    # Backward compatibility
    cursor.execute("""
        SELECT scheduled_date, 
            SUM(actual_minutes) as total_actual_minutes,
            SUM(duration_minutes) as total_planned_minutes,
            COUNT(*) as tasks_count
        FROM study_schedules
        WHERE status IN ('COMPLETED', 'PARTIALLY_COMPLETED')
        GROUP BY scheduled_date
        ORDER BY scheduled_date DESC
        LIMIT 14
    """)
    daily_history = [dict(r) for r in cursor.fetchall()]

    return {
        "feasibility": feasibility,
        "graph_a_daily_study": graph_a_daily_study,
        "graph_b_daily_progress": graph_b_daily_progress,
        "graph_c_wasted_time": graph_c_wasted_time,
        "graph_d_weekly_summary": graph_d_weekly,
        "graph_e_course_progress": course_progress,
        "graph_f_consistency": consistency_data,
        "subjects_stats": course_progress,
        "daily_history": daily_history
    }

@app.get("/api/history")
def get_study_history(conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            sc.id, sc.scheduled_date, sc.duration_minutes, sc.actual_minutes,
            sc.status, sc.task_type, sc.completion_percentage, sc.confidence_rating,
            sc.notes, sc.blockers, sc.completed_at,
            t.title as topic_title, s.name as subject_name, s.color as subject_color
        FROM study_schedules sc
        JOIN topics t ON sc.topic_id = t.id
        JOIN subjects s ON sc.subject_id = s.id
        WHERE sc.status IN ('COMPLETED', 'PARTIALLY_COMPLETED', 'MISSED')
        ORDER BY sc.scheduled_date DESC, sc.id DESC
        LIMIT 100
    """)
    history_items = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM schedule_change_logs ORDER BY timestamp DESC LIMIT 50")
    change_logs = [dict(r) for r in cursor.fetchall()]

    return {
        "history": history_items,
        "change_logs": change_logs
    }

# ----------------- REVISION SYSTEM -----------------

@app.get("/api/revision")
def get_revision_data(conn=Depends(get_db)):
    cursor = conn.cursor()
    # Weak topics
    cursor.execute("""
        SELECT t.id, t.title, t.mastery_level, s.name as subject_name, s.color as subject_color,
            COALESCE((SELECT MIN(confidence_rating) FROM study_schedules sc WHERE sc.topic_id = t.id AND sc.confidence_rating > 0), 2) as lowest_confidence
        FROM topics t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.mastery_level IN ('NEEDS_REVISION', 'PARTIALLY_UNDERSTOOD', 'STUDIED_ONCE')
        ORDER BY lowest_confidence ASC, s.id ASC
    """)
    weak_topics = [dict(r) for r in cursor.fetchall()]

    # Protected 7-day buffer sessions
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    cursor.execute("""
        SELECT sc.*, t.title as topic_title, s.name as subject_name, s.color as subject_color
        FROM study_schedules sc
        JOIN topics t ON sc.topic_id = t.id
        JOIN subjects s ON sc.subject_id = s.id
        WHERE sc.task_type = 'REVISION' AND sc.scheduled_date >= ?
        ORDER BY sc.scheduled_date ASC
    """, (date_info["first_pass_deadline_str"],))
    buffer_sessions = [dict(r) for r in cursor.fetchall()]

    return {
        "weak_topics": weak_topics,
        "buffer_sessions": buffer_sessions,
        "revision_buffer_days": date_info["buffer_days"],
        "buffer_start": date_info["first_pass_deadline_str"],
        "buffer_end": date_info["first_exam_str"]
    }

# ----------------- SYLLABUS INGESTION / IMPORT -----------------

@app.post("/api/import/upload")
async def upload_syllabus_document(file: UploadFile = File(...)):
    filename = file.filename or "uploaded_syllabus.txt"
    dest_path = os.path.join(UPLOADS_DIR, filename)
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        raw_text = SyllabusParser.extract_text_from_file(dest_path)
        extracted = SyllabusParser.parse_syllabus_text(raw_text, source_filename=filename)
        return {"success": True, "data": extracted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse document: {str(e)}")

@app.post("/api/import/commit")
def commit_imported_syllabus(data: Dict[str, Any], conn=Depends(get_db)):
    cursor = conn.cursor()
    code = data.get("course_code", "CSN 9999")
    name = data.get("course_name", "Imported Course")
    credits = data.get("credits", 4)
    lectures = data.get("total_lectures", 42)
    units = data.get("units", [])
    source_filename = data.get("source_filename", "Uploaded Document")

    # Check if subject code already exists
    cursor.execute("SELECT id FROM subjects WHERE code = ?", (code,))
    existing = cursor.fetchone()
    if existing:
        subject_id = existing["id"]
    else:
        cursor.execute("""
            INSERT INTO subjects (code, name, credits, total_lectures, priority, color)
            VALUES (?, ?, ?, ?, 'NORMAL', '#06b6d4')
        """, (code, name, credits, lectures))
        subject_id = cursor.lastrowid

    # Add units and topics
    added_topics = 0
    for u in units:
        cursor.execute("""
            INSERT INTO units (subject_id, unit_number, title, lecture_allocation)
            VALUES (?, ?, ?, ?)
        """, (subject_id, u.get("unit_number", 1), u.get("title", "Unit"), u.get("lecture_allocation", 6)))
        unit_id = cursor.lastrowid

        for idx, t in enumerate(u.get("topics", [])):
            cursor.execute("""
                INSERT INTO topics (unit_id, subject_id, title, estimated_minutes, base_minutes, source_doc, order_index)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (unit_id, subject_id, t.get("title", "Topic"), t.get("estimated_minutes", 60), t.get("estimated_minutes", 60), source_filename, idx))
            topic_id = cursor.lastrowid
            added_topics += 1

            for s_idx, st in enumerate(t.get("subtopics", [])):
                cursor.execute("INSERT INTO subtopics (topic_id, title, order_index) VALUES (?, ?, ?)", (topic_id, st, s_idx))

    conn.commit()
    return {"success": True, "subject_id": subject_id, "topics_added": added_topics}

# ----------------- DAILY DSA (2 COMPULSORY QUESTIONS) -----------------

@app.get("/api/dsa/today")
def get_daily_dsa(conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    today_str = date_info["today_str"]
    cursor = conn.cursor()

    # Check existing assignments for today
    cursor.execute("""
        SELECT a.*, q.title as question_title, q.title, q.topic as syllabus_topic, q.topic, q.difficulty, q.problem_statement, q.concept,
               q.hint_1, q.hint_2, q.solution_approach, q.solution_code,
               q.time_complexity, q.space_complexity
        FROM daily_dsa_assignments a
        JOIN dsa_questions q ON a.question_id = q.id
        WHERE a.assigned_date = ?
        ORDER BY a.slot_number ASC
    """, (today_str,))
    rows = cursor.fetchall()

    assignments = [dict(r) for r in rows]

    # If fewer than 2 assigned, assign new questions automatically
    if len(assignments) < 2:
        needed = 2 - len(assignments)
        assigned_ids = [a["question_id"] for a in assignments]
        # Avoid questions assigned in the past 7 days if possible
        seven_days_ago = (datetime.strptime(today_str, "%Y-%m-%d").date() - timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT question_id FROM daily_dsa_assignments
            WHERE assigned_date >= ?
        """, (seven_days_ago,))
        recent_ids = {r[0] for r in cursor.fetchall()}
        recent_ids.update(assigned_ids)

        # Candidate questions
        placeholders = ",".join("?" for _ in recent_ids) if recent_ids else "0"
        query = f"SELECT id FROM dsa_questions WHERE id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT ?"
        params = list(recent_ids) + [needed] if recent_ids else [needed]
        cursor.execute(query, params)
        new_q_ids = [r[0] for r in cursor.fetchall()]

        # If not enough unassigned, fall back to any questions not already assigned today
        if len(new_q_ids) < needed:
            fallbacks_needed = needed - len(new_q_ids)
            today_ids = assigned_ids + new_q_ids
            tb_placeholders = ",".join("?" for _ in today_ids) if today_ids else "0"
            fb_query = f"SELECT id FROM dsa_questions WHERE id NOT IN ({tb_placeholders}) ORDER BY RANDOM() LIMIT ?"
            fb_params = list(today_ids) + [fallbacks_needed] if today_ids else [fallbacks_needed]
            cursor.execute(fb_query, fb_params)
            new_q_ids.extend([r[0] for r in cursor.fetchall()])

        slot_start = len(assignments) + 1
        for idx, qid in enumerate(new_q_ids):
            cursor.execute("""
                INSERT INTO daily_dsa_assignments (assigned_date, question_id, slot_number, status)
                VALUES (?, ?, ?, 'Pending')
            """, (today_str, qid, slot_start + idx))

        conn.commit()

        # Re-fetch assignments
        cursor.execute("""
            SELECT a.*, q.title, q.topic, q.difficulty, q.problem_statement, q.concept,
                   q.hint_1, q.hint_2, q.solution_approach, q.solution_code,
                   q.time_complexity, q.space_complexity
            FROM daily_dsa_assignments a
            JOIN dsa_questions q ON a.question_id = q.id
            WHERE a.assigned_date = ?
            ORDER BY a.slot_number ASC
        """, (today_str,))
        assignments = [dict(r) for r in cursor.fetchall()]

    solved_count = sum(1 for a in assignments if a["status"] == "Solved")
    attempted_count = sum(1 for a in assignments if a["status"] in ("Attempted", "Solved"))

    return {
        "date": today_str,
        "target_count": 2,
        "solved_count": solved_count,
        "attempted_count": attempted_count,
        "is_completed": solved_count >= 2,
        "assignments": assignments
    }

@app.put("/api/dsa/assignment/{assignment_id}")
def update_dsa_assignment(assignment_id: int, req: DSAStatusUpdateRequest, conn=Depends(get_db)):
    cursor = conn.cursor()
    completed_at = datetime.now().isoformat() if req.status == "Solved" else None
    cursor.execute("""
        UPDATE daily_dsa_assignments
        SET status = ?, user_approach = ?, mistakes_notes = ?, time_spent_minutes = ?,
            completed_at = COALESCE(?, completed_at)
        WHERE id = ?
    """, (req.status, req.user_approach, req.mistakes_notes, req.time_spent_minutes, completed_at, assignment_id))
    conn.commit()
    return {"success": True}

@app.get("/api/dsa/all")
def get_all_dsa_questions(conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.*,
               (SELECT status FROM daily_dsa_assignments a WHERE a.question_id = q.id ORDER BY a.assigned_date DESC LIMIT 1) as latest_status,
               (SELECT COUNT(*) FROM daily_dsa_assignments a WHERE a.question_id = q.id AND a.status = 'Solved') as solve_count
        FROM dsa_questions q
        ORDER BY q.topic ASC, q.id ASC
    """)
    questions = [dict(r) for r in cursor.fetchall()]

    # Stats
    cursor.execute("SELECT COUNT(*) FROM dsa_questions")
    total_q = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT question_id) FROM daily_dsa_assignments WHERE status = 'Solved'")
    solved_q = cursor.fetchone()[0]

    return {
        "total_questions": total_q,
        "unique_solved": solved_q,
        "questions": questions
    }

# ----------------- ENGLISH SPEAKING IMPROVEMENT (30 MIN TARGET) -----------------

@app.get("/api/english/today")
def get_today_english_practice(conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    today = date_info["today"]
    today_str = date_info["today_str"]
    cursor = conn.cursor()

    # Get all topics
    cursor.execute("SELECT * FROM english_speaking_topics ORDER BY id ASC")
    all_topics = [dict(r) for r in cursor.fetchall()]

    if not all_topics:
        selected_topic = None
    else:
        # Deterministic rotation based on day of year
        day_of_year = today.timetuple().tm_yday
        topic_idx = (day_of_year - 1) % len(all_topics)
        selected_topic = all_topics[topic_idx]
        try:
            selected_topic["vocabulary"] = json.loads(selected_topic.get("vocabulary") or "[]")
        except Exception:
            selected_topic["vocabulary"] = []
        try:
            selected_topic["speaking_prompts"] = json.loads(selected_topic.get("speaking_prompts") or "[]")
        except Exception:
            selected_topic["speaking_prompts"] = []

    # Get today's log if any
    cursor.execute("SELECT * FROM daily_english_logs WHERE log_date = ?", (today_str,))
    log_row = cursor.fetchone()
    log_data = dict(log_row) if log_row else {
        "log_date": today_str,
        "topic_id": selected_topic["id"] if selected_topic else None,
        "time_spent_seconds": 0,
        "is_completed": False,
        "notes": "",
        "completed_at": None
    }

    # Calculate streak (consecutive days completed up to today or yesterday)
    cursor.execute("""
        SELECT log_date FROM daily_english_logs
        WHERE is_completed = 1
        ORDER BY log_date DESC
    """)
    completed_dates = {r[0] for r in cursor.fetchall()}
    streak = 0
    check_date = today
    if today_str not in completed_dates:
        check_date = today - timedelta(days=1)
    
    while check_date.strftime("%Y-%m-%d") in completed_dates:
        streak += 1
        check_date -= timedelta(days=1)

    return {
        "date": today_str,
        "target_minutes": int(get_setting(conn, "english_speaking_target_minutes", 30)),
        "streak_days": streak,
        "topic": selected_topic,
        "log": log_data,
        "all_topics_count": len(all_topics)
    }

@app.post("/api/english/log")
def save_english_log(req: EnglishLogSaveRequest, conn=Depends(get_db)):
    cursor = conn.cursor()
    completed_at = datetime.now().isoformat() if req.is_completed else None
    
    cursor.execute("SELECT id FROM daily_english_logs WHERE log_date = ?", (req.log_date,))
    existing = cursor.fetchone()
    if existing:
        cursor.execute("""
            UPDATE daily_english_logs
            SET topic_id = ?, time_spent_seconds = ?, is_completed = ?, notes = ?,
                completed_at = COALESCE(?, completed_at)
            WHERE log_date = ?
        """, (req.topic_id, req.time_spent_seconds, int(req.is_completed), req.notes, completed_at, req.log_date))
    else:
        cursor.execute("""
            INSERT INTO daily_english_logs (log_date, topic_id, time_spent_seconds, is_completed, notes, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (req.log_date, req.topic_id, req.time_spent_seconds, int(req.is_completed), req.notes, completed_at))

    conn.commit()
    return {"success": True}

@app.get("/api/english/history")
def get_english_history(conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, t.title as topic_title, t.category as topic_category
        FROM daily_english_logs l
        LEFT JOIN english_speaking_topics t ON l.topic_id = t.id
        ORDER BY l.log_date DESC
        LIMIT 30
    """)
    logs = [dict(r) for r in cursor.fetchall()]
    return {"history": logs}

# ----------------- DAILY MOTIVATIONAL QUOTE -----------------

@app.get("/api/quotes/today")
def get_today_quote(conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    today = date_info["today"]
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM daily_quotes ORDER BY id ASC")
    quotes = [dict(r) for r in cursor.fetchall()]
    if not quotes:
        return {"quote": {"id": 1, "quote_text": "Consistency turns average effort into excellence.", "author": "Anonymous", "category": "Consistency", "is_favorite": 0}}

    day_of_year = today.timetuple().tm_yday
    idx = (day_of_year - 1) % len(quotes)
    selected = quotes[idx]

    return {
        "date": date_info["today_str"],
        "quote": selected
    }

@app.post("/api/quotes/{quote_id}/favorite")
def toggle_quote_favorite_by_id(quote_id: int, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("UPDATE daily_quotes SET is_favorite = 1 - is_favorite WHERE id = ?", (quote_id,))
    conn.commit()
    cursor.execute("SELECT is_favorite FROM daily_quotes WHERE id = ?", (quote_id,))
    row = cursor.fetchone()
    return {"success": True, "is_favorite": bool(row[0]) if row else False}

@app.get("/api/quotes/all")
def get_all_quotes(conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_quotes ORDER BY category ASC, id ASC")
    return {"quotes": [dict(r) for r in cursor.fetchall()]}

# ----------------- HAVE EXTRA TIME? DO THIS NEXT -----------------

@app.get("/api/extra-time")
def get_extra_time_recommendations(conn=Depends(get_db)):
    """Generates intelligent, workload-aware optional recommendations.
    Never marks optional tasks as compulsory.
    Explains the rationale for each recommendation.
    """
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    today_str = date_info["today_str"]
    cursor = conn.cursor()

    recommendations = []

    # 1. Check for overdue / missed tasks from previous days
    cursor.execute("""
        SELECT sc.id, sc.scheduled_date, sc.duration_minutes, t.title as topic_title,
               s.name as subject_name, s.color as subject_color
        FROM study_schedules sc
        JOIN topics t ON sc.topic_id = t.id
        JOIN subjects s ON sc.subject_id = s.id
        WHERE sc.scheduled_date < ? AND sc.status IN ('PENDING', 'MISSED', 'PARTIALLY_COMPLETED')
        ORDER BY sc.scheduled_date ASC
        LIMIT 2
    """, (today_str,))
    for r in cursor.fetchall():
        recommendations.append({
            "title": f"Complete Overdue: {r['topic_title']} ({r['subject_name']})",
            "category": "Overdue Catch-up",
            "estimated_minutes": min(45, r["duration_minutes"]),
            "reason": f"Scheduled on {r['scheduled_date']} but was not fully completed. Catching up prevents syllabus backlog.",
            "action_type": "STUDY_TASK",
            "target_id": r["id"],
            "color": r["subject_color"]
        })

    # 2. Check weak topics needing revision
    cursor.execute("""
        SELECT t.id, t.title, t.mastery_level, s.name as subject_name, s.color as subject_color
        FROM topics t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.mastery_level IN ('NEEDS_REVISION', 'PARTIALLY_UNDERSTOOD')
        ORDER BY RANDOM()
        LIMIT 2
    """, ())
    for r in cursor.fetchall():
        recommendations.append({
            "title": f"Revisit Weak Topic: {r['title']} ({r['subject_name']})",
            "category": "Revision & Mastery",
            "estimated_minutes": 30,
            "reason": f"Marked as '{r['mastery_level']}'. A 30-minute focused review solidifies understanding before exam crunch.",
            "action_type": "TOPIC_REVIEW",
            "target_id": r["id"],
            "color": r["subject_color"]
        })

    # 3. Check DSA daily completion
    cursor.execute("""
        SELECT COUNT(*) FROM daily_dsa_assignments
        WHERE assigned_date = ? AND status = 'Solved'
    """, (today_str,))
    dsa_solved = cursor.fetchone()[0]
    if dsa_solved < 2:
        recommendations.append({
            "title": "Solve Today's Compulsory DSA Questions",
            "category": "Daily DSA",
            "estimated_minutes": 30,
            "reason": f"You have solved {dsa_solved} of 2 required questions for today. Completing these builds algorithmic consistency.",
            "action_type": "DSA_NAV",
            "target_id": None,
            "color": "#10b981"
        })
    else:
        # Suggest bonus DSA problem
        recommendations.append({
            "title": "Bonus DSA Practice: Solve an Extra Problem",
            "category": "Bonus DSA",
            "estimated_minutes": 25,
            "reason": "You've finished your daily 2 questions! Doing one extra question from Trees or Graphs strengthens interview readiness.",
            "action_type": "DSA_BONUS",
            "target_id": None,
            "color": "#10b981"
        })

    # 4. Check English speaking completion
    cursor.execute("""
        SELECT is_completed FROM daily_english_logs WHERE log_date = ?
    """, (today_str,))
    eng_row = cursor.fetchone()
    if not eng_row or not eng_row[0]:
        recommendations.append({
            "title": "Complete 30-Minute English Speaking Drill",
            "category": "English Fluency",
            "estimated_minutes": 30,
            "reason": "English practice target has not been completed today. Practice builds confidence in technical interviews and presentations.",
            "action_type": "ENGLISH_NAV",
            "target_id": None,
            "color": "#f59e0b"
        })

    # 5. Review mistake notes
    cursor.execute("""
        SELECT mistakes_notes FROM daily_dsa_assignments
        WHERE mistakes_notes IS NOT NULL AND mistakes_notes != ''
        ORDER BY assigned_date DESC LIMIT 1
    """)
    mistake_row = cursor.fetchone()
    if mistake_row:
        recommendations.append({
            "title": "Review Previous DSA Mistakes & Edge Cases",
            "category": "Mistake Analysis",
            "estimated_minutes": 15,
            "reason": "Reviewing past errors prevents making the same missteps in actual exams or coding rounds.",
            "action_type": "MISTAKE_REVIEW",
            "target_id": None,
            "color": "#8b5cf6"
        })

    return {
        "date": today_str,
        "recommendations": recommendations[:5]
    }

# ----------------- STUDY CALENDAR & CUSTOM EVENTS -----------------

@app.get("/api/calendar/events")
def get_calendar_events(start: Optional[str] = None, end: Optional[str] = None, conn=Depends(get_db)):
    """Comprehensive calendar feed:
    - Study sessions from study_schedules
    - College class commitments
    - Subject exam dates
    - Special breaks
    - Custom user events
    """
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    today = date_info["today"]

    if not start:
        start_date = today - timedelta(days=30)
    else:
        try:
            start_date = datetime.strptime(start, "%Y-%m-%d").date()
        except ValueError:
            start_date = today - timedelta(days=30)

    if not end:
        end_date = today + timedelta(days=60)
    else:
        try:
            end_date = datetime.strptime(end, "%Y-%m-%d").date()
        except ValueError:
            end_date = today + timedelta(days=60)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    cursor = conn.cursor()

    events = []

    # 1. Scheduled study sessions
    cursor.execute("""
        SELECT sc.id, sc.scheduled_date, sc.duration_minutes, sc.planned_start_time,
               sc.status, sc.task_type, t.title as topic_title,
               s.name as subject_name, s.code as subject_code, s.color as subject_color
        FROM study_schedules sc
        JOIN topics t ON sc.topic_id = t.id
        JOIN subjects s ON sc.subject_id = s.id
        WHERE sc.scheduled_date >= ? AND sc.scheduled_date <= ?
        ORDER BY sc.scheduled_date ASC, sc.id ASC
    """, (start_str, end_str))
    
    for r in cursor.fetchall():
        events.append({
            "id": f"study_{r['id']}",
            "source_id": r["id"],
            "title": f"[{r['subject_code']}] {r['topic_title']}",
            "description": f"{r['task_type']} • {r['duration_minutes']} mins • Status: {r['status']}",
            "event_date": r["scheduled_date"],
            "start_time": r["planned_start_time"] or "18:00",
            "duration_minutes": r["duration_minutes"],
            "event_type": "study",
            "subject_code": r["subject_code"],
            "color": r["subject_color"],
            "status": r["status"],
            "is_completed": r["status"] == "COMPLETED"
        })

    # 2. Subject exam milestones
    cursor.execute("SELECT id, code, name, exam_date, color FROM subjects WHERE exam_date IS NOT NULL")
    for s in cursor.fetchall():
        if s["exam_date"] and start_str <= s["exam_date"] <= end_str:
            events.append({
                "id": f"exam_{s['id']}",
                "source_id": s["id"],
                "title": f"EXAM: {s['code']} — {s['name']}",
                "description": f"End-Semester Examination for {s['name']}",
                "event_date": s["exam_date"],
                "start_time": "09:30",
                "duration_minutes": 180,
                "event_type": "exam",
                "subject_code": s["code"],
                "color": "#ef4444",
                "status": "UPCOMING",
                "is_completed": False
            })

    # 3. Special Holiday Break (6-11 Dec / 12 Dec)
    break_start_str = get_setting(conn, "special_break_start", "2026-12-06")
    break_end_str = get_setting(conn, "special_break_end", "2026-12-11")
    include_7th = get_setting(conn, "special_break_include_7th_day", False)
    if include_7th and break_end_str == "2026-12-11":
        break_end_str = "2026-12-12"

    try:
        b_curr = datetime.strptime(break_start_str, "%Y-%m-%d").date()
        b_end = datetime.strptime(break_end_str, "%Y-%m-%d").date()
        while b_curr <= b_end:
            b_str = b_curr.strftime("%Y-%m-%d")
            if start_str <= b_str <= end_str:
                events.append({
                    "id": f"break_{b_str}",
                    "source_id": None,
                    "title": "Special Holiday Break (College Off)",
                    "description": "Configured holiday period: college classes are suspended.",
                    "event_date": b_str,
                    "start_time": "00:00",
                    "duration_minutes": 0,
                    "event_type": "holiday",
                    "subject_code": None,
                    "color": "#8b5cf6",
                    "status": "BREAK",
                    "is_completed": True
                })
            b_curr += timedelta(days=1)
    except Exception:
        pass

    # 4. Custom calendar events from calendar_events table
    cursor.execute("""
        SELECT * FROM calendar_events
        WHERE event_date >= ? AND event_date <= ?
        ORDER BY event_date ASC, start_time ASC
    """, (start_str, end_str))
    for row in cursor.fetchall():
        ce = dict(row)
        events.append({
            "id": f"custom_{ce['id']}",
            "source_id": ce["id"],
            "title": ce["title"],
            "description": ce.get("description", ""),
            "event_date": ce["event_date"],
            "start_time": ce.get("start_time") or "10:00",
            "end_time": ce.get("end_time"),
            "duration_minutes": 60,
            "event_type": ce.get("event_type", "personal"),
            "subject_code": ce.get("subject_code"),
            "color": ce.get("color") or "#3b82f6",
            "status": "COMPLETED" if ce.get("is_completed") else "PENDING",
            "is_completed": bool(ce.get("is_completed"))
        })

    # 5. College commitments for dates in range (unless break or blocked)
    # Generate college class indicators for Mon-Fri
    working_days = get_setting(conn, "working_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    college_wh = float(get_setting(conn, "college_working_day_hours", 3.0))
    d_curr = start_date
    while d_curr <= end_date:
        d_str = d_curr.strftime("%Y-%m-%d")
        w_name = d_curr.strftime("%A")
        # If in special break, skip college classes
        if not (break_start_str <= d_str <= break_end_str):
            if w_name in working_days and college_wh > 0:
                events.append({
                    "id": f"college_{d_str}",
                    "source_id": None,
                    "title": f"College Classes ({college_wh:.0f} hrs)",
                    "description": f"Scheduled college classes: {college_wh:.1f} hours",
                    "event_date": d_str,
                    "start_time": "09:00",
                    "duration_minutes": int(college_wh * 60),
                    "event_type": "college",
                    "subject_code": None,
                    "color": "#64748b",
                    "status": "SCHEDULED",
                    "is_completed": d_curr < today
                })
        d_curr += timedelta(days=1)

    return {"events": events}

@app.post("/api/calendar/events")
def create_calendar_event(event: CalendarEventCreate, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO calendar_events (title, description, event_date, start_time, end_time, event_type, subject_code, color, is_completed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (event.title, event.description, event.event_date, event.start_time, event.end_time, event.event_type, event.subject_code, event.color, int(event.is_completed)))
    conn.commit()
    return {"success": True, "id": cursor.lastrowid, "title": event.title, "event_date": event.event_date}

@app.put("/api/calendar/events/{event_id}")
def update_calendar_event(event_id: int, event: CalendarEventUpdate, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,))
    existing = cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")
    
    title = event.title if event.title is not None else existing["title"]
    description = event.description if event.description is not None else existing["description"]
    event_date = event.event_date if event.event_date is not None else existing["event_date"]
    start_time = event.start_time if event.start_time is not None else existing["start_time"]
    end_time = event.end_time if event.end_time is not None else existing["end_time"]
    event_type = event.event_type if event.event_type is not None else existing["event_type"]
    subject_code = event.subject_code if event.subject_code is not None else existing["subject_code"]
    color = event.color if event.color is not None else existing["color"]
    is_completed = int(event.is_completed) if event.is_completed is not None else existing["is_completed"]

    cursor.execute("""
        UPDATE calendar_events
        SET title = ?, description = ?, event_date = ?, start_time = ?, end_time = ?,
            event_type = ?, subject_code = ?, color = ?, is_completed = ?
        WHERE id = ?
    """, (title, description, event_date, start_time, end_time, event_type, subject_code, color, is_completed, event_id))
    conn.commit()
    return {"success": True, "id": event_id, "title": title}

@app.delete("/api/calendar/events/{event_id}")
def delete_calendar_event(event_id: int, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
    conn.commit()
    return {"success": True, "deleted": True}

# ----------------- LIVE UNIT & SYLLABUS TRACKER -----------------
@app.get("/api/syllabus/tracker")
def get_syllabus_tracker_endpoint(conn=Depends(get_db)):
    """Returns comprehensive course-unit-topic progress with verified topic completion percentages."""
    return get_syllabus_tracker_data(conn)

@app.put("/api/topics/{topic_id}/status-enhanced")
def update_topic_status_enhanced(topic_id: int, mastery_level: Optional[str] = None, difficulty_level: Optional[str] = None, needs_revision: Optional[int] = None, conn=Depends(get_db)):
    return update_topic_status_audit(conn, topic_id, mastery_level, difficulty_level, needs_revision)

# ----------------- HANDOUTS & SYLLABUS FILES -----------------
@app.get("/api/handouts")
def list_handouts_endpoint(subject_id: Optional[int] = None, course_id: Optional[int] = None, unit_id: Optional[int] = None, search: Optional[str] = None, conn=Depends(get_db)):
    actual_subj_id = subject_id or course_id
    items = get_handouts(conn, actual_subj_id, unit_id, search)
    return {"handouts": items, "items": items}

@app.get("/api/handouts/hierarchy")
def get_handouts_hierarchy_endpoint(conn=Depends(get_db)):
    """
    Returns verified 3-level academic hierarchy:
    Course -> Unit -> Topics with attached materials, notes, and completion statuses.
    """
    courses = get_handouts_course_hierarchy(conn)
    return {"courses": courses}

@app.post("/api/handouts")
@app.post("/api/handouts/upload")
async def upload_handout_endpoint(
    file: UploadFile = File(...),
    subject_id: Optional[int] = Form(None),
    course_id: Optional[int] = Form(None),
    unit_id: Optional[int] = Form(None),
    unit_number: Optional[int] = Form(None),
    topic_id: Optional[int] = Form(None),
    title: Optional[str] = Form(None),
    topic_name: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    conn=Depends(get_db)
):
    actual_subj_id = subject_id or course_id or 1
    actual_unit_id = unit_id or unit_number
    original_name = file.filename or "uploaded_file"
    ext = os.path.splitext(original_name)[1].lower()
    allowed_exts = {".pdf", ".ppt", ".pptx", ".doc", ".docx", ".txt", ".md"}
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file format '{ext}'. Allowed: PDF, PPT, PPTX, DOC, DOCX, TXT, MD.")

    import uuid
    import re
    safe_name = f"{uuid.uuid4().hex[:10]}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', original_name)}"
    dest_path = os.path.join(UPLOADS_DIR, safe_name)

    content = await file.read()
    file_size = len(content)
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds maximum 50MB limit.")

    with open(dest_path, "wb") as f:
        f.write(content)

    doc_title = title or original_name
    h_notes = f"Topic: {topic_name}. {notes or ''}" if topic_name else notes
    h_id = add_handout(conn, safe_name, doc_title, ext.replace(".", "").upper(), file_size, actual_subj_id, actual_unit_id, topic_id, dest_path, h_notes)
    handout_obj = get_handout_by_id(conn, h_id)
    return {"success": True, "id": h_id, "data": handout_obj, "handout": handout_obj}

@app.get("/api/handouts/{handout_id}/download")
def download_handout_endpoint(handout_id: int, conn=Depends(get_db)):
    handout = get_handout_by_id(conn, handout_id)
    if not handout:
        raise HTTPException(status_code=404, detail="Handout not found.")
    
    target_path = handout.get("storage_path") or handout["file_path"]
    content, media_type = storage_service.get_file_bytes(target_path)
    if content is None:
        raise HTTPException(status_code=404, detail="Handout file not found in storage.")
    
    from fastapi.responses import Response
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{handout["original_filename"]}"'}
    )

@app.get("/api/handouts/{handout_id}/preview")
def preview_handout_endpoint(handout_id: int, conn=Depends(get_db)):
    handout = get_handout_by_id(conn, handout_id)
    if not handout:
        raise HTTPException(status_code=404, detail="Handout not found.")

    target_path = handout.get("storage_path") or handout["file_path"]
    content, media_type = storage_service.get_file_bytes(target_path)
    if content is None:
        raise HTTPException(status_code=404, detail="Handout file not found in storage.")

    f_type = handout["file_type"].lower()
    if f_type in ("txt", "md"):
        return Response(content=content, media_type="text/plain; charset=utf-8")
    elif f_type == "pdf":
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{handout["original_filename"]}"'}
        )
    elif f_type in ("png", "jpg", "jpeg", "webp"):
        return Response(content=content, media_type=media_type)
    else:
        return {
            "type": "unsupported",
            "message": f"In-browser preview not available for {f_type.upper()}. Please use download to open in your system viewer.",
            "filename": handout["original_filename"]
        }

@app.put("/api/handouts/{handout_id}")
def update_handout_endpoint(handout_id: int, req: HandoutUpdateModel, conn=Depends(get_db)):
    success = update_handout(conn, handout_id, req.original_filename, req.subject_id, req.unit_id, req.topic_id, req.notes)
    if not success:
        raise HTTPException(status_code=404, detail="Handout not found.")
    return {"success": True, "handout": get_handout_by_id(conn, handout_id)}

@app.delete("/api/handouts/{handout_id}")
def delete_handout_endpoint(handout_id: int, conn=Depends(get_db)):
    handout = get_handout_by_id(conn, handout_id)
    if not handout:
        raise HTTPException(status_code=404, detail="Handout not found.")
    file_path = delete_handout(conn, handout_id)
    storage_service.delete_file(handout.get("storage_path") or file_path or handout["filename"])
    return {"success": True}

# ----------------- DOUBTS & NOTES ATTACHMENT -----------------
@app.get("/api/doubts")
def list_doubts(status: Optional[str] = None, subject_id: Optional[int] = None, conn=Depends(get_db)):
    return {"doubts": get_doubts(conn, status, subject_id)}

@app.post("/api/doubts")
def create_doubt(req: DoubtCreate, conn=Depends(get_db)):
    subj_id = req.subject_id
    if subj_id is None and req.subject_name:
        cur = conn.cursor()
        cur.execute("SELECT id FROM subjects WHERE name LIKE ? OR code LIKE ? LIMIT 1", (f"%{req.subject_name}%", f"%{req.subject_name}%"))
        r = cur.fetchone()
        subj_id = r["id"] if r else 1
    elif subj_id is None:
        subj_id = 1
    d_id = add_doubt(conn, subj_id, req.doubt_text, req.schedule_id, req.topic_id)
    return {"success": True, "id": d_id, "doubt_id": d_id}

@app.put("/api/doubts/{doubt_id}/resolve")
def resolve_doubt_endpoint(doubt_id: int, req: DoubtResolve, conn=Depends(get_db)):
    ans_text = req.answer_text or req.notes or "Resolved in study session"
    success = resolve_doubt(conn, doubt_id, ans_text)
    return {"success": success}

# ----------------- QUOTE OF THE DAY & FAVORITES -----------------
@app.get("/api/quotes/today")
@app.get("/api/quote/today")
def get_quote_today(date_str: Optional[str] = None, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    today_s = date_str or scheduler.calculate_dates()["today_str"]
    q = get_stable_quote_of_the_day(conn, today_s)
    return {"success": True, "quote": q}

@app.get("/api/quotes/favorites")
def list_favorite_quotes(conn=Depends(get_db)):
    return {"favorites": get_favorite_quotes(conn)}

@app.post("/api/quotes/favorites")
def save_favorite_quote(req: QuoteFavoriteRequest, conn=Depends(get_db)):
    q_text = req.quote_text or ""
    author = req.author or "Unknown"
    is_fav = toggle_quote_favorite(conn, q_text, author, req.is_favorite)
    return {"success": True, "is_favorite": is_fav}

# ----------------- WEEKLY REVIEW & GLOBAL SEARCH -----------------
@app.get("/api/weekly-review")
def weekly_review_endpoint(date_str: Optional[str] = None, conn=Depends(get_db)):
    scheduler = StudyScheduler(conn)
    ref_d = date_str or scheduler.calculate_dates()["today_str"]
    return get_weekly_review(conn, ref_d)

@app.get("/api/search")
def search_endpoint(q: str, conn=Depends(get_db)):
    if not q or len(q.strip()) < 2:
        return {"query": q, "subjects": [], "topics": [], "handouts": [], "tasks": []}
    return global_search(conn, q.strip())

# ----------------- BACKUP & RESTORE -----------------

@app.get("/api/backup/export")
def export_backup(conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects")
    subjects = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM units")
    units = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM topics")
    topics = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM subtopics")
    subtopics = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM prerequisites")
    prereqs = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM settings")
    settings = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM study_schedules")
    schedules = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM study_sessions")
    sessions = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM dsa_questions")
    dsa_questions = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM daily_dsa_assignments")
    dsa_assignments = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM english_speaking_topics")
    english_topics = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM daily_english_logs")
    english_logs = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM daily_quotes")
    quotes = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM calendar_events")
    calendar_events = [dict(r) for r in cursor.fetchall()]

    backup_data = {
        "version": "2.0.0",
        "app": "Last Chance",
        "exported_at": datetime.now().isoformat(),
        "subjects": subjects,
        "units": units,
        "topics": topics,
        "subtopics": subtopics,
        "prerequisites": prereqs,
        "settings": settings,
        "study_schedules": schedules,
        "study_sessions": sessions,
        "dsa_questions": dsa_questions,
        "daily_dsa_assignments": dsa_assignments,
        "english_speaking_topics": english_topics,
        "daily_english_logs": english_logs,
        "daily_quotes": quotes,
        "calendar_events": calendar_events
    }
    return backup_data

@app.post("/api/backup/restore")
def restore_backup(data: Dict[str, Any], conn=Depends(get_db)):
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = OFF;")
        # Clear tables
        tables_to_clear = [
            "calendar_events", "daily_english_logs", "daily_dsa_assignments",
            "study_sessions", "study_schedules", "revision_items", "prerequisites",
            "subtopics", "topics", "units", "subjects", "settings"
        ]
        for tbl in tables_to_clear:
            cursor.execute(f"DELETE FROM {tbl}")
        
        for s in data.get("subjects", []):
            cursor.execute("INSERT INTO subjects (id, code, name, credits, total_lectures, exam_date, priority, color) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (s["id"], s["code"], s["name"], s["credits"], s["total_lectures"], s["exam_date"], s["priority"], s["color"]))
        for u in data.get("units", []):
            cursor.execute("INSERT INTO units (id, subject_id, unit_number, title, lecture_allocation) VALUES (?, ?, ?, ?, ?)",
                           (u["id"], u["subject_id"], u["unit_number"], u["title"], u["lecture_allocation"]))
        for t in data.get("topics", []):
            cursor.execute("INSERT INTO topics (id, unit_id, subject_id, title, estimated_minutes, base_minutes, mastery_level, is_mandatory, is_official, source_doc, order_index) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (t["id"], t["unit_id"], t["subject_id"], t["title"], t["estimated_minutes"], t["base_minutes"], t["mastery_level"], t["is_mandatory"], t["is_official"], t.get("source_doc", "Backup"), t["order_index"]))
        for st in data.get("subtopics", []):
            cursor.execute("INSERT INTO subtopics (id, topic_id, title, order_index) VALUES (?, ?, ?, ?)",
                           (st["id"], st["topic_id"], st["title"], st["order_index"]))
        for pr in data.get("prerequisites", []):
            cursor.execute("INSERT INTO prerequisites (id, topic_id, prerequisite_topic_id) VALUES (?, ?, ?)",
                           (pr["id"], pr["topic_id"], pr["prerequisite_topic_id"]))
        for stg in data.get("settings", []):
            cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (stg["key"], stg["value"]))
        for sc in data.get("study_schedules", []):
            cursor.execute("""
                INSERT INTO study_schedules (id, scheduled_date, topic_id, subject_id, duration_minutes, planned_start_time, status, task_type, priority, learning_objectives, suggested_breakdown, study_method, actual_minutes, completion_percentage, confidence_rating, notes, blockers, practice_attempted, completed_at, reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sc["id"], sc["scheduled_date"], sc["topic_id"], sc["subject_id"], sc["duration_minutes"], sc.get("planned_start_time"), sc["status"], sc["task_type"], sc["priority"], sc.get("learning_objectives"), sc.get("suggested_breakdown"), sc.get("study_method"), sc.get("actual_minutes", 0), sc.get("completion_percentage", 0), sc.get("confidence_rating", 0), sc.get("notes"), sc.get("blockers"), sc.get("practice_attempted", 0), sc.get("completed_at"), sc.get("reasoning")))

        for dsa in data.get("daily_dsa_assignments", []):
            cursor.execute("""
                INSERT INTO daily_dsa_assignments (id, assigned_date, question_id, slot_number, status, user_approach, time_spent_minutes, mistakes_notes, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (dsa["id"], dsa["assigned_date"], dsa["question_id"], dsa["slot_number"], dsa["status"], dsa.get("user_approach"), dsa.get("time_spent_minutes", 0), dsa.get("mistakes_notes"), dsa.get("completed_at")))

        for eng in data.get("daily_english_logs", []):
            cursor.execute("""
                INSERT INTO daily_english_logs (id, log_date, topic_id, time_spent_seconds, is_completed, notes, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (eng["id"], eng["log_date"], eng.get("topic_id"), eng.get("time_spent_seconds", 0), eng.get("is_completed", 0), eng.get("notes"), eng.get("completed_at")))

        for ce in data.get("calendar_events", []):
            cursor.execute("""
                INSERT INTO calendar_events (id, title, description, event_date, start_time, end_time, event_type, subject_code, color, is_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ce["id"], ce["title"], ce.get("description"), ce["event_date"], ce.get("start_time"), ce.get("end_time"), ce.get("event_type", "personal"), ce.get("subject_code"), ce.get("color"), ce.get("is_completed", 0)))

        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        return {"success": True, "message": "Last Chance backup restored successfully."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {str(e)}")

# ----------------- CALENDAR INTEGRATED EVENTS & ACTIONS -----------------

@app.get("/api/calendar/events")
def get_calendar_events_endpoint(start: Optional[str] = None, end: Optional[str] = None, conn=Depends(get_db)):
    """Returns combined scheduled study shifts, DSA assignments, English logs, exams, and custom calendar events."""
    events = get_calendar_events_combined(conn, start, end)
    return {"events": events, "count": len(events)}

# ----------------- REDO / PRACTICE AGAIN WORKFLOW -----------------

@app.get("/api/redo")
def get_redo_queue_endpoint(status: Optional[str] = None, course_code: Optional[str] = None, conn=Depends(get_db)):
    """Returns persistent tasks in the Redo / Practice Again queue."""
    tasks = get_redo_tasks(conn, status, course_code)
    pending_count = len([t for t in tasks if t["status"] == "PENDING"])
    return {"tasks": tasks, "redo_tasks": tasks, "total": len(tasks), "pending_count": pending_count}

@app.post("/api/redo")
def add_redo_task_endpoint(req: RedoTaskCreate, conn=Depends(get_db)):
    t_title = req.topic_title or req.topic_name or "Revision Task"
    task_id = add_redo_task(
        conn,
        topic_title=t_title,
        schedule_id=req.schedule_id,
        topic_id=req.topic_id,
        subject_id=req.subject_id,
        course_code=req.course_code,
        course_name=req.course_name,
        unit_number=req.unit_number,
        unit_title=req.unit_title,
        original_completion_date=req.original_completion_date,
        due_date=req.due_date,
        priority=req.priority,
        reason=req.reason
    )
    return {"success": True, "id": task_id, "topic_name": t_title, "topic_title": t_title, "status": "PENDING"}

@app.put("/api/redo/{redo_id}")
def update_redo_task_endpoint(redo_id: int, req: RedoTaskUpdate, conn=Depends(get_db)):
    success = update_redo_task(conn, redo_id, status=req.status, due_date=req.due_date, priority=req.priority, reason=req.reason)
    return {"success": success}

@app.post("/api/redo/{redo_id}/complete")
def complete_redo_task_endpoint(redo_id: int, conn=Depends(get_db)):
    success = complete_redo_task(conn, redo_id)
    return {"success": success, "status": "COMPLETED"}

@app.delete("/api/redo/{redo_id}")
def delete_redo_task_endpoint(redo_id: int, conn=Depends(get_db)):
    success = delete_redo_task(conn, redo_id)
    return {"success": success, "deleted": success}

# ----------------- USER AUTHENTICATION & CROSS-DEVICE PROFILE -----------------

@app.post("/api/auth/register")
def register_user_endpoint(req: UserRegisterRequest, conn=Depends(get_db)):
    existing = get_user_by_username(conn, req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists.")
    pwd_hash = hash_password(req.password)
    user_id = create_user(conn, req.username, pwd_hash, req.email, req.full_name or "Student")
    token = create_access_token({"user_id": user_id, "username": req.username})
    user_obj = {
        "id": user_id,
        "username": req.username,
        "full_name": req.full_name or "Student",
        "email": req.email,
        "theme_preference": "dark"
    }
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": req.username,
        "full_name": req.full_name or "Student",
        "theme_preference": "dark",
        "user": user_obj
    }

@app.post("/api/auth/login")
def login_user_endpoint(req: UserLoginRequest, conn=Depends(get_db)):
    user = get_user_by_username(conn, req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = create_access_token({"user_id": user["id"], "username": user["username"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "full_name": user["full_name"],
        "theme_preference": user["theme_preference"] or "dark",
        "user": user
    }

@app.get("/api/auth/me")
def get_current_user_profile_endpoint(user_dict=Depends(get_optional_current_user), conn=Depends(get_db)):
    if not user_dict:
        return {"authenticated": False, "username": "Guest Student", "theme_preference": "dark"}
    user = get_user_by_id(conn, user_dict["user_id"])
    if not user:
        return {"authenticated": False, "username": "Guest Student", "theme_preference": "dark"}
    return {"authenticated": True, "user": user, "username": user["username"], "theme_preference": user.get("theme_preference", "dark")}

@app.put("/api/auth/theme")
def update_user_theme_endpoint(req: ThemeUpdateRequest, user_dict=Depends(get_optional_current_user), conn=Depends(get_db)):
    theme_val = req.theme
    if user_dict and user_dict.get("user_id"):
        update_user_profile(conn, user_dict["user_id"], theme_preference=theme_val)
    set_setting(conn, "default_theme", theme_val)
    return {"success": True, "theme": theme_val, "theme_preference": theme_val}

# ----------------- ENHANCED DSA ROTATION & NOTES -----------------

@app.get("/api/dsa/all-questions")
def get_all_dsa_questions_endpoint(conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, title as question_title, topic, topic as syllabus_topic, difficulty, concept, description, solution, time_complexity, space_complexity FROM dsa_questions ORDER BY topic, difficulty")
    questions = [dict(r) for r in cursor.fetchall()]
    return {"questions": questions, "count": len(questions)}

@app.post("/api/dsa/{assignment_id}/replace")
def replace_dsa_assignment_endpoint(assignment_id: int, req: Optional[DSAReplaceRequest] = None, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_dsa_assignments WHERE id = ?", (assignment_id,))
    cur_assign = cursor.fetchone()
    if not cur_assign:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    
    if req and req.new_question_id:
        target_qid = req.new_question_id
    else:
        cursor.execute("SELECT id, title, topic FROM dsa_questions WHERE id != ? ORDER BY RANDOM() LIMIT 1", (cur_assign["question_id"],))
        alt = cursor.fetchone()
        target_qid = alt["id"] if alt else cur_assign["question_id"]
    
    cursor.execute("SELECT title, topic FROM dsa_questions WHERE id = ?", (target_qid,))
    q_info = cursor.fetchone()
    new_topic_name = f"{q_info['topic']}: {q_info['title']}" if q_info else cur_assign["topic_name"]
    q_title = q_info["title"] if q_info else cur_assign["topic_name"]

    cursor.execute("UPDATE daily_dsa_assignments SET question_id = ?, topic_name = ?, status = 'Pending' WHERE id = ?", (target_qid, new_topic_name, assignment_id))
    conn.commit()
    return {"success": True, "question_id": target_qid, "topic_name": new_topic_name, "question_title": q_title}

@app.put("/api/dsa/{assignment_id}/notes")
def update_dsa_notes_endpoint(assignment_id: int, req: DSANotesUpdate, conn=Depends(get_db)):
    cursor = conn.cursor()
    updates = []
    params = []
    note_val = req.notes or req.approach_notes or req.user_approach
    if note_val is not None:
        updates.append("approach_notes = ?")
        params.append(note_val)
    if req.mistakes_notes is not None:
        updates.append("mistakes_notes = ?")
        params.append(req.mistakes_notes)
    if req.time_spent_minutes is not None:
        updates.append("time_spent_minutes = ?")
        params.append(req.time_spent_minutes)
    if not updates:
        return {"success": True, "notes": ""}
    params.append(assignment_id)
    cursor.execute(f"UPDATE daily_dsa_assignments SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    return {"success": True, "notes": note_val or ""}

# ----------------- MISSING MATERIALS CHECKLIST -----------------

@app.get("/api/handouts/missing-checklist")
def get_missing_handouts_checklist_endpoint(conn=Depends(get_db)):
    """Returns syllabus units with uploaded materials vs units that need lecture notes/photos."""
    data = get_missing_materials_checklist(conn)
    data["checklist"] = data.get("course_breakdown", [])
    return data

# ----------------- STATIC FILES & FRONTEND -----------------

app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    # If file exists in frontend, serve it
    file_path = os.path.join(FRONTEND_DIR, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    # Default SPA fallback
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
