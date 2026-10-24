import os
import shutil
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import get_connection, init_db, get_setting, set_setting, DB_PATH
from backend.models import (
    SubjectModel, SubjectUpdateModel, TopicModel, TopicUpdateModel,
    SettingsModel, TaskCompletionRequest, StartSessionRequest, FinishSessionRequest,
    FeasibilityReport, DSAQuestionModel, DSAAssignmentModel, DSAStatusUpdateRequest,
    EnglishTopicModel, DailyEnglishLogModel, EnglishLogSaveRequest, QuoteModel,
    CalendarEventModel, CalendarEventCreate, CalendarEventUpdate
)
from backend.scheduler import StudyScheduler
from backend.syllabus_parser import SyllabusParser

# Ensure DB is initialized
init_db()

app = FastAPI(
    title="Last Chance API",
    description="Last Chance — Your Personal Adaptive Academic Study & Exam Planner",
    version="2.0.0"
)

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
    """Returns the real, dynamic local time and date for Asia/Kolkata."""
    now = datetime.now()
    scheduler = StudyScheduler(conn)
    date_info = scheduler.calculate_dates()
    today = date_info["today"]
    
    return {
        "iso": now.isoformat(),
        "date_str": today.strftime("%Y-%m-%d"),
        "time_str": now.strftime("%H:%M:%S"),
        "formatted_date": today.strftime("%A, %d %B %Y"),
        "formatted_time": now.strftime("%I:%M:%S %p"),
        "weekday": today.strftime("%A"),
        "day": today.day,
        "month": today.month,
        "month_name": today.strftime("%B"),
        "year": today.year,
        "timezone": get_setting(conn, "time_zone", "Asia/Kolkata"),
        "simulated": get_setting(conn, "simulated_today", None) is not None
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

    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            sc.*,
            t.title as topic_title, t.estimated_minutes as topic_base_mins, t.mastery_level,
            u.title as unit_title, u.unit_number,
            s.name as subject_name, s.code as subject_code, s.color as subject_color,
            (SELECT GROUP_CONCAT(title, '||') FROM subtopics st WHERE st.topic_id = t.id) as subtopics_joined
        FROM study_schedules sc
        JOIN topics t ON sc.topic_id = t.id
        JOIN units u ON t.unit_id = u.id
        JOIN subjects s ON sc.subject_id = s.id
        WHERE sc.scheduled_date = ?
        ORDER BY sc.status ASC, sc.id ASC
    """, (today_str,))
    
    tasks = []
    total_scheduled = 0
    total_completed = 0

    for r in cursor.fetchall():
        d = dict(r)
        d["subtopics"] = d["subtopics_joined"].split("||") if d.get("subtopics_joined") else []
        d.pop("subtopics_joined", None)
        tasks.append(d)
        total_scheduled += d["duration_minutes"]
        if d["status"] == "COMPLETED":
            total_completed += d["duration_minutes"]

    available_today = scheduler.get_daily_available_minutes(date_info["today"])
    free_today = max(0, available_today - total_scheduled)
    completion_rate = round((total_completed / total_scheduled * 100), 1) if total_scheduled > 0 else 0.0
    college_hours_today = scheduler.get_college_hours_for_date(date_info["today"])

    feasibility = scheduler.assess_feasibility()

    return {
        "date_info": date_info,
        "available_minutes": available_today,
        "academic_target_minutes": int(get_setting(conn, "daily_academic_target_minutes", 240)),
        "academic_completed_minutes": total_completed,
        "scheduled_minutes": total_scheduled,
        "remaining_free_minutes": free_today,
        "completion_rate": completion_rate,
        "college_hours": college_hours_today,
        "english_target_minutes": int(get_setting(conn, "english_speaking_target_minutes", 30)),
        "dsa_target_count": int(get_setting(conn, "daily_dsa_count", 2)),
        "tasks": tasks,
        "feasibility": feasibility
    }

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
    
    cursor = conn.cursor()
    # Subject breakdown
    cursor.execute("""
        SELECT 
            s.id, s.name, s.code, s.color,
            COUNT(t.id) as total_topics,
            SUM(CASE WHEN t.mastery_level IN ('CONFIDENT', 'MASTERED') THEN 1 ELSE 0 END) as mastered_topics,
            SUM(t.estimated_minutes) as total_estimated_mins,
            COALESCE((
                SELECT SUM(sc.actual_minutes) FROM study_schedules sc WHERE sc.subject_id = s.id AND sc.status = 'COMPLETED'
            ), 0) as total_actual_mins
        FROM subjects s
        LEFT JOIN topics t ON s.id = t.subject_id
        GROUP BY s.id
    """)
    subjects_stats = [dict(r) for r in cursor.fetchall()]

    # Daily study history for consistency
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

    # Revision coverage
    cursor.execute("SELECT COUNT(*) FROM revision_items WHERE status = 'COMPLETED'")
    revisions_done = cursor.fetchone()[0]

    return {
        "feasibility": feasibility,
        "subjects_stats": subjects_stats,
        "daily_history": daily_history,
        "revisions_completed": revisions_done,
        "predicted_completion_date": feasibility["first_pass_deadline"] if feasibility["is_feasible"] else "At Risk"
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
        SELECT a.*, q.title, q.topic, q.difficulty, q.problem_statement, q.concept,
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
        cursor.execute("""
            SELECT question_id FROM daily_dsa_assignments
            WHERE assigned_date >= date(?, '-7 days')
        """, (today_str,))
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
def toggle_quote_favorite(quote_id: int, conn=Depends(get_db)):
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
    for ce in cursor.fetchall():
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
    return {"success": True, "id": cursor.lastrowid}

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
    return {"success": True}

@app.delete("/api/calendar/events/{event_id}")
def delete_calendar_event(event_id: int, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
    conn.commit()
    return {"success": True}

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
