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
    FeasibilityReport
)
from backend.scheduler import StudyScheduler
from backend.syllabus_parser import SyllabusParser

# Ensure DB is initialized
init_db()

app = FastAPI(
    title="StudyPilot API",
    description="Your Personal Exam Planning System — Local, Adaptive, Intelligent Semester Examination Planner",
    version="1.0.0"
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

# ----------------- DATE & FEASIBILITY ENDPOINTS -----------------

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "StudyPilot", "version": "1.0.0"}

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

    feasibility = scheduler.assess_feasibility()

    return {
        "date_info": date_info,
        "available_minutes": available_today,
        "scheduled_minutes": total_scheduled,
        "remaining_free_minutes": free_today,
        "completion_rate": completion_rate,
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

    backup_data = {
        "version": "1.0.0",
        "exported_at": datetime.now().isoformat(),
        "subjects": subjects,
        "units": units,
        "topics": topics,
        "subtopics": subtopics,
        "prerequisites": prereqs,
        "settings": settings,
        "study_schedules": schedules,
        "study_sessions": sessions
    }
    return backup_data

@app.post("/api/backup/restore")
def restore_backup(data: Dict[str, Any], conn=Depends(get_db)):
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = OFF;")
        # Clear tables
        for tbl in ["study_sessions", "study_schedules", "revision_items", "prerequisites", "subtopics", "topics", "units", "subjects", "settings"]:
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

        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        return {"success": True, "message": "Backup restored successfully."}
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
