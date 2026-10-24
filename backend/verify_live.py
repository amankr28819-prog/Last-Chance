import urllib.request
import json

base = 'http://127.0.0.1:8000'

def test_endpoint(ep):
    req = urllib.request.Request(base + ep)
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        content = resp.read()
        print(f"[OK] {ep} -> Status 200 ({len(content)} bytes)")
        return content

def main():
    print("--- 1. Testing Static Assets & Frontend Shell ---")
    test_endpoint('/')
    test_endpoint('/static/css/app.css')
    test_endpoint('/static/js/app.js')
    test_endpoint('/static/js/api.js')
    test_endpoint('/static/vendor/react.min.js')
    test_endpoint('/static/vendor/tailwind.js')

    print("\n--- 2. Testing Dates & Feasibility ---")
    dates = json.loads(test_endpoint('/api/dates'))
    print(f"Dates: Today={dates['today_str']}, FirstPassDeadline={dates['first_pass_deadline_str']}, FirstExam={dates['first_exam_str']}")

    feas = json.loads(test_endpoint('/api/feasibility'))
    print(f"Feasibility: Status={feas['status_label']}, TotalRemainingHours={feas['total_remaining_hours']}, TotalAvailableHours={feas['total_available_hours']}")

    print("\n--- 3. Testing Subjects & Topics ---")
    subjs = json.loads(test_endpoint('/api/subjects'))
    print(f"Loaded {len(subjs)} subjects:")
    for s in subjs:
        print(f" - {s['code']} {s['name']}: {s['topics_count']} topics, {s['units_count']} units, Exam Date: {s['exam_date']}")

    print("\n--- 4. Testing Schedule Generation ---")
    post_req = urllib.request.Request(base + '/api/schedule/generate', data=b'{}', headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(post_req) as resp:
        res = json.loads(resp.read())
        print(f"Scheduler: Successfully scheduled {res['tasks_scheduled']} tasks! Buffer overrun: {res['overrun_into_buffer']}")

    today = json.loads(test_endpoint('/api/schedule/today'))
    print(f"Today's Plan: {len(today['tasks'])} tasks scheduled for today ({today['scheduled_minutes']} / {today['available_minutes']} mins).")
    if today['tasks']:
        t0 = today['tasks'][0]
        print(f"First Task Today: {t0['topic_title']} ({t0['duration_minutes']} mins) in {t0['subject_name']}")
        print(f"Objectives: {t0['learning_objectives'].splitlines()[0]}")

        print("\n--- 5. Testing Task Partial Completion & Adaptive Rescheduling ---")
        comp_data = json.dumps({
            'status': 'PARTIALLY_COMPLETED',
            'completion_percentage': 50,
            'actual_minutes': 30,
            'confidence_rating': 4,
            'notes': 'Completed first half; carrying forward remainder.'
        }).encode('utf-8')
        comp_req = urllib.request.Request(f"{base}/api/schedule/{t0['id']}/complete", data=comp_data, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(comp_req) as resp:
            c_res = json.loads(resp.read())
            print(f"Reschedule Response: {c_res['summary']}")

    print("\n--- 6. Testing Analytics & History Audit ---")
    analytics = json.loads(test_endpoint('/api/analytics'))
    print(f"Analytics: Subjects tracked={len(analytics['subjects_stats'])}, Revisions done={analytics['revisions_completed']}")

    history = json.loads(test_endpoint('/api/history'))
    print(f"History: {len(history['history'])} completed records, {len(history['change_logs'])} schedule change logs recorded.")

    print("\n=== ALL LIVE INTEGRATION CHECKS COMPLETED SUCCESSFULLY! ===")

if __name__ == '__main__':
    main()
