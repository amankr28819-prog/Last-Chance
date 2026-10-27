# Tests for audit improvements: Redo queue, Calendar events, DSA replace/notes, Handouts checklist, and Auth
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend import database as db

client = TestClient(app)

def test_calendar_endpoints_full():
    # 1. Fetch calendar events
    res = client.get("/api/calendar/events?start=2026-10-27&end=2026-11-20")
    assert res.status_code == 200
    data = res.json()
    assert "events" in data
    assert len(data["events"]) > 0

    # 2. Create custom event
    ev_payload = {
        "event_date": "2026-11-15",
        "title": "Group Revision Session",
        "event_type": "STUDY_SESSION",
        "duration_minutes": 60,
        "notes": "Testing calendar custom event"
    }
    create_res = client.post("/api/calendar/events", json=ev_payload)
    assert create_res.status_code == 200
    created = create_res.json()
    event_id = created["id"]
    assert created["title"] == "Group Revision Session"

    # 3. Update custom event
    update_res = client.put(f"/api/calendar/events/{event_id}", json={"title": "Updated Revision Session"})
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Revision Session"

    # 4. Delete custom event
    del_res = client.delete(f"/api/calendar/events/{event_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True

def test_redo_queue_workflow():
    # 1. Add a redo task
    payload = {
        "topic_name": "Peano Postulates & Inductive Sets",
        "course_name": "Discrete Structures",
        "unit_number": 2,
        "priority": "HIGH",
        "reason": "Needs formal proof practice before exam"
    }
    res = client.post("/api/redo", json=payload)
    assert res.status_code == 200
    task = res.json()
    task_id = task["id"]
    assert task["topic_name"] == payload["topic_name"]
    assert task["status"] == "PENDING"

    # 2. List redo tasks
    list_res = client.get("/api/redo?status=PENDING")
    assert list_res.status_code == 200
    tasks = list_res.json()["redo_tasks"]
    assert any(t["id"] == task_id for t in tasks)

    # 3. Mark redo complete
    comp_res = client.post(f"/api/redo/{task_id}/complete")
    assert comp_res.status_code == 200
    completed_task = comp_res.json()
    assert completed_task["status"] == "COMPLETED"

    # 4. Clean up / delete
    del_res = client.delete(f"/api/redo/{task_id}")
    assert del_res.status_code == 200

def test_dsa_extended_endpoints():
    # 1. Fetch all DSA questions repository
    all_res = client.get("/api/dsa/all-questions")
    assert all_res.status_code == 200
    questions = all_res.json()["questions"]
    assert len(questions) >= 40

    # 2. Fetch today's assignment
    today_res = client.get("/api/dsa/today")
    assert today_res.status_code == 200
    assignments = today_res.json()["assignments"]
    assert len(assignments) == 2
    first_assignment = assignments[0]
    assert first_assignment["question_title"] is not None
    assert first_assignment["syllabus_topic"] is not None

    # 3. Replace question
    alt_question = next(q for q in questions if q["id"] != first_assignment["question_id"])
    replace_res = client.post(
        f"/api/dsa/{first_assignment['id']}/replace",
        json={"new_question_id": alt_question["id"]}
    )
    assert replace_res.status_code == 200
    replaced = replace_res.json()
    assert replaced["question_id"] == alt_question["id"]
    assert replaced["question_title"] == alt_question["question_title"]

    # 4. Update notes
    notes_res = client.put(
        f"/api/dsa/{first_assignment['id']}/notes",
        json={"notes": "Solved using two-pointer approach O(n)"}
    )
    assert notes_res.status_code == 200
    assert notes_res.json()["notes"] == "Solved using two-pointer approach O(n)"

def test_missing_materials_checklist():
    res = client.get("/api/handouts/missing-checklist")
    assert res.status_code == 200
    data = res.json()
    assert "checklist" in data
    assert len(data["checklist"]) == 4  # 4 courses

    # Verify courses
    codes = [c["course_code"] for c in data["checklist"]]
    assert "CSN 3003" in codes
    assert "CSN 3001" in codes
    assert "CSN 3004" in codes
    assert "CSN 3002" in codes

def test_auth_workflow():
    import uuid
    uname = f"testuser_{uuid.uuid4().hex[:6]}"
    pwd = "SecretPassword123!"

    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "username": uname,
        "password": pwd,
        "full_name": "Test User"
    })
    assert reg_res.status_code == 200
    token_data = reg_res.json()
    token = token_data["access_token"]
    assert token is not None
    assert token_data["user"]["username"] == uname

    # 2. Login
    login_res = client.post("/api/auth/login", json={
        "username": uname,
        "password": pwd
    })
    assert login_res.status_code == 200
    assert login_res.json()["access_token"] is not None

    # 3. Get Me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == uname

    # 4. Update Theme
    theme_res = client.put("/api/auth/theme", json={"theme": "light"}, headers={"Authorization": f"Bearer {token}"})
    assert theme_res.status_code == 200
    assert theme_res.json()["theme_preference"] == "light"

def test_shift_completion_with_redo():
    # Fetch today's shifts
    today_res = client.get("/api/schedule/today")
    shifts = today_res.json()["shifts"]
    if shifts:
        s = shifts[0]
        comp_res = client.post(
            f"/api/schedule/{s['id']}/complete_shift",
            json={
                "actual_minutes": 45,
                "confidence_rating": 3,
                "notes": "Testing shift complete with redo flag",
                "add_to_redo": True,
                "redo_reason": "Flagged from test"
            }
        )
        assert comp_res.status_code == 200
        # Check that redo task was registered
        redo_res = client.get("/api/redo")
        redo_tasks = redo_res.json()["redo_tasks"]
        assert any("Flagged from test" in (t.get("reason") or "") for t in redo_tasks)
