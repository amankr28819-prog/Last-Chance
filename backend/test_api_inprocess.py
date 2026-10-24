from fastapi.testclient import TestClient
from backend.app import app
import json

client = TestClient(app)

def test_all():
    print("--- 1. Testing Static Assets & Frontend Shell ---")
    r = client.get('/')
    assert r.status_code == 200
    print("[OK] / -> Status 200 (HTML shell loaded)")

    r = client.get('/static/css/app.css')
    assert r.status_code == 200
    print("[OK] /static/css/app.css -> Status 200")

    r = client.get('/static/js/app.js')
    assert r.status_code == 200
    print("[OK] /static/js/app.js -> Status 200")

    r = client.get('/static/vendor/react.min.js')
    assert r.status_code == 200
    print("[OK] /static/vendor/react.min.js -> Status 200")

    print("\n--- 2. Testing Dates & Feasibility ---")
    r = client.get('/api/dates')
    assert r.status_code == 200
    dates = r.json()
    print(f"Dates: Today={dates['today_str']}, FirstPassDeadline={dates['first_pass_deadline_str']}, FirstExam={dates['first_exam_str']}, DaysToExam={dates['days_to_exam']}")

    r = client.get('/api/feasibility')
    assert r.status_code == 200
    feas = r.json()
    print(f"Feasibility: Status={feas['status_label']}, TotalRemainingHours={feas['total_remaining_hours']}, TotalAvailableHours={feas['total_available_hours']}, Gap={feas['capacity_gap_hours']}h")

    print("\n--- 3. Testing Subjects & Topics ---")
    r = client.get('/api/subjects')
    assert r.status_code == 200
    subjs = r.json()
    print(f"Loaded {len(subjs)} subjects:")
    for s in subjs:
        print(f" - {s['code']} {s['name']}: {s['topics_count']} topics, {s['units_count']} units, Exam Date: {s['exam_date']}")

    print("\n--- 4. Testing Schedule Generation ---")
    r = client.post('/api/schedule/generate', json={})
    assert r.status_code == 200
    gen = r.json()
    print(f"Scheduler: Successfully scheduled {gen['tasks_scheduled']} tasks! Buffer overrun: {gen['overrun_into_buffer']}")

    r = client.get('/api/schedule/today')
    assert r.status_code == 200
    today = r.json()
    print(f"Today's Plan: {len(today['tasks'])} tasks scheduled for today ({today['scheduled_minutes']} / {today['available_minutes']} mins).")
    assert len(today['tasks']) > 0
    t0 = today['tasks'][0]
    print(f"First Task Today: {t0['topic_title']} ({t0['duration_minutes']} mins) in {t0['subject_name']}")

    print("\n--- 5. Testing Task Partial Completion & Adaptive Rescheduling ---")
    r = client.post(f"/api/schedule/{t0['id']}/complete", json={
        'status': 'PARTIALLY_COMPLETED',
        'completion_percentage': 50,
        'actual_minutes': 30,
        'confidence_rating': 4,
        'notes': 'Completed first half; carrying forward remainder.'
    })
    assert r.status_code == 200
    comp_res = r.json()
    print(f"Adaptive Reschedule Response: {comp_res['summary']}")

    print("\n--- 6. Testing Analytics & History Audit ---")
    r = client.get('/api/analytics')
    assert r.status_code == 200
    analytics = r.json()
    print(f"Analytics: Subjects tracked={len(analytics['subjects_stats'])}, Revisions done={analytics['revisions_completed']}")

    r = client.get('/api/history')
    assert r.status_code == 200
    history = r.json()
    print(f"History: {len(history['history'])} completed records, {len(history['change_logs'])} schedule change logs recorded.")

    print("\n=== ALL IN-PROCESS FASTAPI CHECKS VERIFIED SUCCESSFULLY! ===")

if __name__ == '__main__':
    test_all()
