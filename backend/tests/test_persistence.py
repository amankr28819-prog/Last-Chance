import json
from backend.database import set_setting, get_setting
from backend.syllabus_parser import SyllabusParser

def test_settings_persistence(test_db):
    set_setting(test_db, "custom_target", "Score A+ in CSN 3001")
    val = get_setting(test_db, "custom_target")
    assert val == "Score A+ in CSN 3001"

def test_syllabus_parser_text_extraction_and_duplicates():
    raw_text = """
    Course Code: CSN 4001
    Course Title: Computer Networks
    Unit 1: Physical Layer
    * Introduction to Networks: OSI Model, TCP/IP Model
    * Transmission Media: Twisted pair, Coaxial cable, Fiber optics
    * Introduction to Networks: OSI Model
    Unit 2: Data Link Layer
    * Framing techniques
    * Error detection and correction: CRC, Checksum
    """
    parsed = SyllabusParser.parse_syllabus_text(raw_text, "test_syllabus.txt")
    assert parsed["course_code"] == "CSN 4001"
    assert "Computer Networks" in parsed["course_name"]
    assert len(parsed["units"]) == 2
    assert "Introduction to Networks" in parsed["detected_duplicates"]

def test_backup_and_restore(test_db):
    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM subjects")
    orig_subjs = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM topics")
    orig_topics = cursor.fetchone()[0]

    assert orig_subjs == 4
    assert orig_topics == 210

    # Read all tables as backup
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

    backup = {
        "subjects": subjects,
        "units": units,
        "topics": topics,
        "subtopics": subtopics,
        "prerequisites": prereqs,
        "settings": settings,
        "study_schedules": [],
        "study_sessions": []
    }

    # Delete all
    cursor.execute("DELETE FROM prerequisites")
    cursor.execute("DELETE FROM subtopics")
    cursor.execute("DELETE FROM topics")
    cursor.execute("DELETE FROM units")
    cursor.execute("DELETE FROM subjects")
    test_db.commit()

    cursor.execute("SELECT COUNT(*) FROM subjects")
    assert cursor.fetchone()[0] == 0

    # Restore from backup
    for s in backup["subjects"]:
        cursor.execute("INSERT INTO subjects (id, code, name, credits, total_lectures, exam_date, priority, color) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (s["id"], s["code"], s["name"], s["credits"], s["total_lectures"], s["exam_date"], s["priority"], s["color"]))
    for u in backup["units"]:
        cursor.execute("INSERT INTO units (id, subject_id, unit_number, title, lecture_allocation) VALUES (?, ?, ?, ?, ?)",
                       (u["id"], u["subject_id"], u["unit_number"], u["title"], u["lecture_allocation"]))
    for t in backup["topics"]:
        cursor.execute("INSERT INTO topics (id, unit_id, subject_id, title, estimated_minutes, base_minutes, mastery_level, is_mandatory, is_official, source_doc, order_index) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (t["id"], t["unit_id"], t["subject_id"], t["title"], t["estimated_minutes"], t["base_minutes"], t["mastery_level"], t["is_mandatory"], t["is_official"], t.get("source_doc", "Backup"), t["order_index"]))
    test_db.commit()

    cursor.execute("SELECT COUNT(*) FROM subjects")
    assert cursor.fetchone()[0] == 4
    cursor.execute("SELECT COUNT(*) FROM topics")
    assert cursor.fetchone()[0] == 210
