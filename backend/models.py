from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SubtopicModel(BaseModel):
    id: Optional[int] = None
    topic_id: Optional[int] = None
    title: str
    order_index: int = 0

class PrerequisiteModel(BaseModel):
    id: Optional[int] = None
    topic_id: int
    prerequisite_topic_id: int
    prerequisite_title: Optional[str] = None

class TopicModel(BaseModel):
    id: Optional[int] = None
    unit_id: int
    subject_id: int
    title: str
    estimated_minutes: int = 60
    base_minutes: int = 60
    mastery_level: str = "NOT_STARTED" # NOT_STARTED, STUDIED_ONCE, PARTIALLY_UNDERSTOOD, NEEDS_REVISION, CONFIDENT, MASTERED
    is_mandatory: bool = True
    is_official: bool = True
    source_doc: Optional[str] = "Official Syllabus"
    order_index: int = 0
    subtopics: List[str] = []
    prerequisites: List[int] = []

class TopicUpdateModel(BaseModel):
    title: Optional[str] = None
    estimated_minutes: Optional[int] = None
    mastery_level: Optional[str] = None
    is_mandatory: Optional[bool] = None
    order_index: Optional[int] = None
    subtopics: Optional[List[str]] = None
    prerequisites: Optional[List[int]] = None

class UnitModel(BaseModel):
    id: Optional[int] = None
    subject_id: int
    unit_number: int
    title: str
    lecture_allocation: int = 6
    topics: List[TopicModel] = []

class SubjectModel(BaseModel):
    id: Optional[int] = None
    code: str
    name: str
    credits: int = 4
    total_lectures: int = 42
    exam_date: Optional[str] = None
    priority: str = "NORMAL" # NORMAL, HIGH, URGENT
    color: str = "#3b82f6"

class SubjectUpdateModel(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    exam_date: Optional[str] = None
    priority: Optional[str] = None
    color: Optional[str] = None

class StudyWindowModel(BaseModel):
    name: str
    start: str
    end: str
    minutes: int
    days: List[str]

class SettingsModel(BaseModel):
    first_exam_date: str = "2026-11-26"
    syllabus_deadline: str = "2026-11-19"
    revision_buffer_days: int = 7
    is_buffer_mandatory: bool = True
    daily_academic_target_minutes: int = 240  # 4 hours
    english_speaking_target_minutes: int = 30  # 30 minutes
    daily_dsa_count: int = 2  # 2 questions
    working_days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    weekly_holidays: List[str] = ["Saturday", "Sunday"]
    college_working_day_hours: float = 3.0
    college_holiday_hours: float = 5.0
    special_break_start: str = "2026-12-06"
    special_break_end: str = "2026-12-11"
    special_break_warning: str = "Note: 6 Dec to 11 Dec contains 6 calendar days, not 7."
    special_break_include_7th_day: bool = False
    weekday_minutes: int = 240
    weekend_minutes: int = 240
    college_hours: str = "09:00 - 12:00"
    commute_minutes: int = 30
    sleep_hours: str = "23:30 - 06:30"
    study_windows: List[StudyWindowModel] = []
    blocked_dates: List[str] = []
    session_duration: int = 60
    max_consecutive_minutes: int = 90
    break_duration: int = 15
    subjects_per_day: int = 2
    study_style: str = "INTERLEAVED"  # INTERLEAVED or DEEP_DIVE
    daily_practice: bool = True
    spaced_revision: bool = True
    onboarding_completed: bool = False
    theme: str = "dark"
    time_zone: str = "Asia/Kolkata"

class DSAQuestionModel(BaseModel):
    id: Optional[int] = None
    title: str
    topic: str
    difficulty: str = "Medium"
    problem_statement: str
    concept: Optional[str] = None
    hint_1: Optional[str] = None
    hint_2: Optional[str] = None
    solution_approach: Optional[str] = None
    solution_code: Optional[str] = None
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None

class DSAAssignmentModel(BaseModel):
    id: Optional[int] = None
    assigned_date: str
    question_id: int
    slot_number: int = 1
    status: str = "Pending"  # Pending, Attempted, Solved, Needs Revision
    user_approach: Optional[str] = None
    time_spent_minutes: int = 0
    mistakes_notes: Optional[str] = None
    completed_at: Optional[str] = None
    question: Optional[DSAQuestionModel] = None

class DSAStatusUpdateRequest(BaseModel):
    status: str  # Attempted, Solved, Needs Revision, Pending
    user_approach: Optional[str] = None
    mistakes_notes: Optional[str] = None
    time_spent_minutes: int = 0

class EnglishTopicModel(BaseModel):
    id: Optional[int] = None
    category: str
    title: str
    objective: str
    vocabulary: List[str] = []
    speaking_prompts: List[str] = []

class DailyEnglishLogModel(BaseModel):
    id: Optional[int] = None
    log_date: str
    topic_id: Optional[int] = None
    time_spent_seconds: int = 0
    is_completed: bool = False
    notes: Optional[str] = None
    completed_at: Optional[str] = None
    topic: Optional[EnglishTopicModel] = None

class EnglishLogSaveRequest(BaseModel):
    log_date: str
    topic_id: Optional[int] = None
    time_spent_seconds: int
    is_completed: bool
    notes: Optional[str] = None

class QuoteModel(BaseModel):
    id: Optional[int] = None
    quote_text: str
    author: Optional[str] = "Unknown"
    category: str
    is_favorite: bool = False

class CalendarEventModel(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    event_date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    event_type: str = "study"  # study, college, holiday, exam, personal
    subject_code: Optional[str] = None
    color: Optional[str] = None
    is_completed: bool = False

class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    event_type: str = "study"
    subject_code: Optional[str] = None
    color: Optional[str] = None
    is_completed: bool = False

class CalendarEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    event_type: Optional[str] = None
    subject_code: Optional[str] = None
    color: Optional[str] = None
    is_completed: Optional[bool] = None

class WastedTimeLogCreate(BaseModel):
    log_date: Optional[str] = None
    wasted_date: Optional[str] = None
    minutes: int
    reason: Optional[str] = ""
    notes: Optional[str] = None
    category: str = "Unproductive Time"

class WastedTimeLogModel(BaseModel):
    id: Optional[int] = None
    log_date: str
    minutes: int
    reason: Optional[str] = None
    category: str = "Unproductive Time"
    created_at: Optional[str] = None

class EnglishLogSimpleRequest(BaseModel):
    log_date: str
    actual_minutes: int
    notes: Optional[str] = ""

class DSATopicAssignmentUpdate(BaseModel):
    status: str # Pending, Attempted, Solved, Needs Revision
    time_spent_minutes: int = 0
    notes: Optional[str] = ""

class TopicStatusUpdateRequest(BaseModel):
    mastery_level: str # NOT_STARTED, IN_PROGRESS, COMPLETED, NEEDS_REVISION, CONFIDENT, MASTERED
    notes: Optional[str] = None

class TaskCompletionRequest(BaseModel):
    status: str # COMPLETED, PARTIALLY_COMPLETED, MISSED, PENDING
    completion_percentage: int = 100
    actual_minutes: int = 0
    remaining_minutes: Optional[int] = None
    confidence_rating: int = 3 # 1 to 5
    notes: Optional[str] = ""
    blockers: Optional[str] = ""
    practice_attempted: bool = False

class StartSessionRequest(BaseModel):
    schedule_id: Optional[int] = None
    topic_id: int

class FinishSessionRequest(BaseModel):
    session_id: int
    duration_seconds: int
    actual_minutes: int
    completion_percentage: int
    confidence_rating: int
    notes: Optional[str] = ""
    mark_task_status: Optional[str] = "COMPLETED"

class ScheduleItemModel(BaseModel):
    id: Optional[int] = None
    scheduled_date: str
    topic_id: int
    subject_id: int
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    subject_color: Optional[str] = None
    unit_title: Optional[str] = None
    topic_title: Optional[str] = None
    subtopics: List[str] = []
    duration_minutes: int
    planned_start_time: Optional[str] = None
    status: str = "PENDING"
    task_type: str = "NEW_LEARNING"
    priority: str = "NORMAL"
    learning_objectives: Optional[str] = None
    suggested_breakdown: Optional[str] = None
    study_method: Optional[str] = None
    actual_minutes: int = 0
    completion_percentage: int = 0
    confidence_rating: int = 0
    notes: Optional[str] = None
    blockers: Optional[str] = None
    practice_attempted: bool = False
    completed_at: Optional[str] = None
    reasoning: Optional[str] = None

class FeasibilityReport(BaseModel):
    is_feasible: bool
    current_date: str
    first_exam_date: str
    first_pass_deadline: str
    days_to_deadline: int
    days_to_exam: int
    revision_buffer_days: int
    total_topics_count: int
    completed_topics_count: int
    remaining_topics_count: int
    total_remaining_minutes: int
    total_remaining_hours: float
    total_available_minutes: int
    total_available_hours: float
    capacity_gap_minutes: int
    capacity_gap_hours: float
    capacity_utilization_percent: float
    daily_average_needed_minutes: float
    daily_average_available_minutes: float
    status_label: str # ON_TRACK, TIGHT, OVERLOADED, PAST_DEADLINE
    warning_message: Optional[str] = None
    actionable_recommendations: List[str] = []

class SyllabusExtractionReviewItem(BaseModel):
    course_name: str
    course_code: str
    credits: int = 4
    total_lectures: int = 42
    units: List[Dict[str, Any]]
    detected_duplicates: List[str] = []
    potential_missing_sections: List[str] = []
    source_filename: str

class ShiftCompleteRequest(BaseModel):
    actual_minutes: Optional[int] = 45
    notes: Optional[str] = None
    add_to_redo: bool = False
    redo_reason: Optional[str] = None

class ShiftPartialRequest(BaseModel):
    actual_minutes: int
    notes: Optional[str] = None
    is_interrupted: bool = False

class ShiftRescheduleRequest(BaseModel):
    to_date: Optional[str] = None
    new_date: Optional[str] = None
    reason: str = "Unfinished task moved"

class RescheduleUndoRequest(BaseModel):
    history_id: int

class HandoutUpdateModel(BaseModel):
    original_filename: Optional[str] = None
    subject_id: Optional[int] = None
    unit_id: Optional[int] = None
    topic_id: Optional[int] = None
    notes: Optional[str] = None

class DoubtCreate(BaseModel):
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    doubt_text: str
    schedule_id: Optional[int] = None
    topic_id: Optional[int] = None

class DoubtResolve(BaseModel):
    answer_text: Optional[str] = ""
    notes: Optional[str] = ""

class QuoteFavoriteRequest(BaseModel):
    quote_text: Optional[str] = None
    author: Optional[str] = None
    is_favorite: Optional[bool] = True

# --- Redo / Practice Again Models ---
class RedoTaskCreate(BaseModel):
    topic_id: Optional[int] = None
    subject_id: Optional[int] = None
    schedule_id: Optional[int] = None
    topic_title: Optional[str] = None
    topic_name: Optional[str] = None
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    unit_number: Optional[int] = None
    unit_title: Optional[str] = None
    original_completion_date: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "MEDIUM" # LOW, MEDIUM, HIGH, URGENT
    reason: Optional[str] = None

class RedoTaskUpdate(BaseModel):
    status: Optional[str] = None # PENDING, IN_PROGRESS, COMPLETED, POSTPONED
    due_date: Optional[str] = None
    priority: Optional[str] = None
    reason: Optional[str] = None

class RedoTaskModel(BaseModel):
    id: int
    schedule_id: Optional[int] = None
    topic_id: Optional[int] = None
    subject_id: Optional[int] = None
    topic_title: str
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    unit_number: Optional[int] = None
    unit_title: Optional[str] = None
    original_completion_date: Optional[str] = None
    added_to_redo_date: str
    due_date: Optional[str] = None
    priority: str = "MEDIUM"
    reason: Optional[str] = None
    status: str = "PENDING"
    redo_count: int = 0
    last_practiced_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None

# --- User Authentication & Profile Models ---
class UserRegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = "Student"

class UserLoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    theme_preference: str = "dark"

class ThemeUpdateRequest(BaseModel):
    theme: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    theme_preference: Optional[str] = None

# --- DSA Enhancement Models ---
class DSAReplaceRequest(BaseModel):
    new_question_id: Optional[int] = None
    target_topic: Optional[str] = None

class DSANotesUpdate(BaseModel):
    notes: Optional[str] = None
    user_approach: Optional[str] = None
    approach_notes: Optional[str] = None
    mistakes_notes: Optional[str] = None
    time_spent_minutes: Optional[int] = None


