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
    weekday_minutes: int = 180
    weekend_minutes: int = 300
    college_hours: str = "09:00 - 16:00"
    commute_minutes: int = 60
    sleep_hours: str = "23:30 - 06:30"
    study_windows: List[StudyWindowModel] = []
    blocked_dates: List[str] = []
    session_duration: int = 60
    max_consecutive_minutes: int = 90
    break_duration: int = 15
    subjects_per_day: int = 2
    study_style: str = "INTERLEAVED" # INTERLEAVED or DEEP_DIVE
    daily_practice: bool = True
    spaced_revision: bool = True
    onboarding_completed: bool = False
    theme: str = "dark"
    time_zone: str = "Asia/Kolkata"

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
