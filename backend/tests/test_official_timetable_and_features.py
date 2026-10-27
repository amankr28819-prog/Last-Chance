# backend/tests/test_official_timetable_and_features.py
import pytest
from fastapi.testclient import TestClient
from backend.app import app
import backend.database as db
from backend.timetable_data import import_official_timetable, TIMETABLE_DAYS

client = TestClient(app)

def test_api_time_and_dates():
    res = client.get('/api/time')
    assert res.status_code == 200
    data = res.json()
    assert 'formatted_time' in data
    assert 'date_str' in data
    assert data.get('timezone') == 'Asia/Kolkata'

    res_dates = client.get('/api/dates')
    assert res_dates.status_code == 200
    d_data = res_dates.json()
    assert 'today_str' in d_data
    assert 'days_to_exam' in d_data

def test_timetable_preview_and_duplicate_prevention():
    res = client.get('/api/import/preview')
    assert res.status_code == 200
    p = res.json()
    assert p['days_count'] == 25
    assert p['total_shifts'] == 125
    assert p['total_wrapup_sessions'] == 25

    # Run import endpoint
    res_import = client.post('/api/import/timetable')
    assert res_import.status_code == 200
    data_import = res_import.json()
    assert 'imported_count' in data_import

    # Re-running import must prevent duplicates
    res_import2 = client.post('/api/import/timetable')
    assert res_import2.status_code == 200
    assert res_import2.json()['imported_count'] == 0

def test_today_schedule_and_shifts():
    res = client.get('/api/schedule/today')
    assert res.status_code == 200
    data = res.json()
    assert 'plan' in data
    assert 'shifts' in data
    assert 'quote' in data
    assert 'study_totals' in data

    # Plan target should be 240 mins
    assert data['plan']['academic_target_minutes'] == 240

def test_shift_complete_and_study_totals():
    # Pick a shift
    res = client.get('/api/schedule/day?date_str=2026-10-27')
    assert res.status_code == 200
    shifts = res.json().get('shifts', [])
    assert len(shifts) >= 1

    shift = shifts[0]
    shift_id = shift['id']

    # Complete the shift with 45 minutes
    res_comp = client.post(f'/api/schedule/{shift_id}/complete_shift', json={
        'actual_minutes': 45,
        'confidence_rating': 4,
        'notes': 'Test completed shift'
    })
    assert res_comp.status_code == 200
    assert res_comp.json()['success'] is True

    # Verify study totals updated
    res_totals = client.get('/api/study-time/totals')
    assert res_totals.status_code == 200
    totals = res_totals.json()
    assert totals['total_academic_minutes'] >= 45

def test_shift_partial_complete():
    res = client.get('/api/schedule/day?date_str=2026-10-27')
    shifts = res.json().get('shifts', [])
    assert len(shifts) >= 2

    shift = shifts[1]
    shift_id = shift['id']

    res_partial = client.post(f'/api/schedule/{shift_id}/partial', json={
        'actual_minutes': 20,
        'reason': 'Test partial completion'
    })
    assert res_partial.status_code == 200
    p_data = res_partial.json()
    assert p_data['success'] is True
    assert p_data['remaining_minutes'] == 25

def test_shift_reschedule_and_undo():
    res = client.get('/api/schedule/day?date_str=2026-10-27')
    shifts = res.json().get('shifts', [])
    assert len(shifts) >= 3

    shift = shifts[2]
    shift_id = shift['id']
    orig_date = shift['scheduled_date']
    new_date = '2026-11-15'

    # Reschedule shift
    res_resched = client.post(f'/api/schedule/{shift_id}/reschedule', json={
        'new_date': new_date,
        'reason': 'Heavy college day'
    })
    assert res_resched.status_code == 200
    r_data = res_resched.json()
    assert r_data['success'] is True
    assert r_data['new_date'] == new_date

    # Verify in rescheduled tasks list
    res_list = client.get('/api/schedule/rescheduled')
    assert res_list.status_code == 200
    res_tasks = res_list.json()['rescheduled_tasks']
    matching = [t for t in res_tasks if t['id'] == shift_id]
    assert len(matching) > 0
    history_id = matching[0]['latest_history_id']

    # Undo reschedule
    res_undo = client.post('/api/schedule/reschedule-undo', json={'history_id': history_id})
    assert res_undo.status_code == 200
    assert res_undo.json()['success'] is True
    assert res_undo.json()['restored_to_date'] == orig_date

def test_wasted_time_and_shortfall_separation():
    today_str = '2026-10-27'
    # Log 17 mins of confirmed wasted time
    res_log = client.post('/api/wasted-time/log', json={
        'wasted_date': today_str,
        'minutes': 17,
        'category': 'Social Media Scrolling',
        'notes': 'Test wasted entry'
    })
    assert res_log.status_code == 200

    # Retrieve summary
    res_sum = client.get(f'/api/wasted-time/summary?date_str={today_str}')
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    today_w = sum_data['today']

    assert today_w['confirmed_wasted_minutes'] >= 17
    # Shortfall is separate
    assert 'academic_shortfall_minutes' in today_w
    assert today_w['confirmed_wasted_minutes'] != today_w['academic_shortfall_minutes']

    # Clean up all test logs
    recent_logs = sum_data.get('recent_logs', [])
    for l in recent_logs:
        if l.get('notes') == 'Test wasted entry':
            client.delete(f'/api/wasted-time/log/{l["id"]}')

def test_handout_upload_preview_and_delete():
    # Upload test text file
    file_content = b"Unit 2 Inductive proof notes and examples."
    res_upload = client.post(
        '/api/handouts',
        data={
            'title': 'Test Inductive Proof Handout',
            'course_id': '1',
            'unit_number': '2',
            'topic_name': 'Inductive definition'
        },
        files={'file': ('test_handout.txt', file_content, 'text/plain')}
    )
    assert res_upload.status_code == 200
    h_data = res_upload.json()['data']
    handout_id = h_data['id']

    # Retrieve handouts
    res_get = client.get('/api/handouts?course_id=1')
    assert res_get.status_code == 200
    handouts = res_get.json()['handouts']
    assert any(h['id'] == handout_id for h in handouts)

    # Preview
    res_prev = client.get(f'/api/handouts/{handout_id}/preview')
    assert res_prev.status_code == 200
    assert b"Inductive proof notes" in res_prev.content

    # Delete
    res_del = client.delete(f'/api/handouts/{handout_id}')
    assert res_del.status_code == 200

def test_quotes_stability_and_favorites():
    res1 = client.get('/api/quotes/today')
    assert res1.status_code == 200
    q1 = res1.json()['quote']

    # Refreshing or re-requesting returns the exact same quote for the calendar day
    res2 = client.get('/api/quotes/today')
    assert res2.status_code == 200
    q2 = res2.json()['quote']
    assert q1['quote_text'] == q2['quote_text']

    # Favorite toggle
    res_fav = client.post('/api/quotes/favorites', json={
        'quote_text': q1['quote_text'],
        'author': q1.get('author', 'Unknown')
    })
    assert res_fav.status_code == 200

    # Get favorites list
    res_fav_list = client.get('/api/quotes/favorites')
    assert res_fav_list.status_code == 200
    favs = res_fav_list.json()['favorites']
    assert any(f['quote_text'] == q1['quote_text'] for f in favs)

def test_doubts_workflow():
    res_add = client.post('/api/doubts', json={
        'doubt_text': 'How to apply the pigeonhole principle in generalised form?',
        'subject_name': 'Discrete Structures'
    })
    assert res_add.status_code == 200
    doubt_id = res_add.json()['doubt_id']

    # Fetch open doubts
    res_open = client.get('/api/doubts?status=OPEN')
    assert res_open.status_code == 200
    doubts = res_open.json()['doubts']
    assert any(d['id'] == doubt_id for d in doubts)

    # Resolve doubt
    res_res = client.put(f'/api/doubts/{doubt_id}/resolve', json={'notes': 'Reviewed theorem 3.2 in notes'})
    assert res_res.status_code == 200

def test_global_search_and_weekly_review():
    res_search = client.get('/api/search?q=Discrete')
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert 'topics' in data_search or 'tasks' in data_search

    res_review = client.get('/api/weekly-review')
    assert res_review.status_code == 200
    data_review = res_review.json()
    assert 'academic_hours_completed' in data_review or 'total_academic_hours' in data_review
    assert 'suggested_priorities' in data_review

def test_database_backup_export():
    res_backup = client.get('/api/backup/export')
    assert res_backup.status_code == 200
    b_data = res_backup.json()
    assert 'subjects' in b_data or 'tables' in b_data
    assert 'exported_at' in b_data
