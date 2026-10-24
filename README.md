# Last Chance — Personal Study Planner & Exam Management System

**Last Chance** is a comprehensive, local-first academic planning and student productivity application built to ensure total university syllabus mastery, consistent daily discipline, and top examination readiness.

Running 100% locally on Windows, it requires zero external subscriptions and no paid AI APIs.

---

## 🌟 Key Features & Core Philosophy

### 1. Distinct, Realistic Daily Routine Allocations
The system strictly segregates and monitors your daily academic and professional commitments:
* **Academic Coursework Target**: **4 Hours (240 minutes)** per day reserved exclusively for semester subjects:
  - Discrete Structures (`CSN 3003`)
  - Data Structures (`CSN 3001`)
  - Object-Oriented Programming (`CSN 3004`)
  - Data Science & Machine Learning (`CSN 3002`)
* **Daily DSA Practice**: Exactly **2 compulsory practice problems** assigned daily from the Data Structures curriculum with hints, detailed solutions, complexity analysis, and approach/mistake tracking.
* **English Speaking Fluency**: **30 minutes** of speaking drills with rotating topics across technical explanations, elevator pitches, and project walkthroughs, complete with an interactive timer and streak tracker.
* **College Commitments**: Distinctly separates college class hours (default 3.0 hrs on Mon–Fri working days, 0 hrs on holidays, configurable 5 hrs for special dates) from personal study hours.
* **Special Holiday Break**: Fully configurable break (6–11 December 2026). Flags that this range contains 6 calendar days and provides an option to extend to the 7th day (12 December).

### 2. Live Date & Time Engine
* Displays real-time local date, weekday, and seconds-accurate clock synchronized with **India Standard Time (`Asia/Kolkata`)**.
* Live countdowns to exam milestones and syllabus deadlines.
* Past-due items display clear overdue notices rather than misleading timers.

### 3. Fully Repaired Study Calendar
* **Three Switchable Views**: Month view, Week view, and Day view.
* **Seamless Navigation**: Previous / Next month buttons, "Today" button, and date picker.
* **Holistic Day Overview**: Displays academic sessions, college classes, university exams, and holidays.
* **Custom Calendar Events**: Add, edit, and delete personal study commitments and milestones.

### 4. "Have Extra Time? Do This Next"
* An intelligent productivity card that recommends optional high-impact activities when you have surplus time:
  - Catch up on overdue tasks.
  - Revisit weak or low-confidence topics.
  - Solve a bonus DSA question.
  - Complete daily English speaking practice.
  - Review recorded mistake notes.

### 5. Daily Motivational Quotes
* One inspirational quote per calendar day (offline, consistent all day) across six curated categories:
  - Consistency & Discipline
  - Parents & Gratitude
  - Faith in God
  - Success & Perseverance
  - Patience & Hope
  - Study & Learning
* Save favorite quotes to build a personal library.

### 6. Course & Unit Syllabus Explorer
* Navigable hierarchy: **Course → Unit → Topic**.
* Real-time search, status filtering (Not Started, Confident, Needs Revision, Mastered).
* Topic confidence ratings, time estimates, notes, and subtopics.

### 7. Protected 7-Day Pre-Exam Revision Buffer
* Targets complete first-pass syllabus completion at least **7 calendar days before your first examination**.
* Locks the final 7 days for spaced revision, formula recall, and mock tests.

### 8. Focus Mode & Time Tracking
* Full-screen distraction-free timer with pause/resume and real elapsed-time tracking.
* Browser refresh resilience and note taking.

### 9. Handout & Syllabus Ingestion
* Import PDF, TXT, or Markdown syllabus documents locally.
* Previews extracted units and detects duplicates before committing.

### 10. Complete Dark & Light Theme System
* Built on semantic CSS variables with WCAG AA compliant contrast.
* Prevents dark-on-dark or light-on-light text artifacts.
* Theme preference is saved locally and preserved across reloads.

---

## 📚 Pre-Loaded Semester Courses

1. **Discrete Structures for Computer Science** (`CSN 3003` — 4 Credits, 42 Lectures)
2. **Data Structures** (`CSN 3001` — 4 Credits, 42 Lectures)
3. **Object Oriented Programming** (`CSN 3004` — 4 Credits, 42 Lectures)
4. **Data Science & Machine Learning** (`CSN 3002` — 4 Credits, 42 Lectures)

---

## 🚀 Windows Local Execution

### Prerequisites
* Windows 10 or Windows 11.
* Python 3.10+ (tested and verified with Python 3.14.0).

### Method 1: One-Click Startup (Recommended)
Double-click `run.bat` or run in PowerShell:
```powershell
cd "Z:\Last Chance\Last-Chance"
.\run.bat
```

The script will:
1. Verify Python and environment dependencies.
2. Initialize or safely migrate the SQLite database at `data\lastchance.db`.
3. Launch the web server on `http://127.0.0.1:8000`.
4. Automatically open your default web browser.

### Method 2: Manual Python Startup
```powershell
python main.py
```

### Port Conflict Handling
If port 8000 is occupied, `main.py` detects the process and automatically switches to the next available port (e.g. 8001). You can also specify a custom port:
```powershell
python main.py --port 8080
```

To stop the server: Press `Ctrl+C` in the command window.

---

## 🧪 Automated Testing

Run the full pytest test suite:
```powershell
python -m pytest backend/tests -v -p no:cacheprovider
```

All 21 backend unit tests cover:
* 240-minute daily academic study targets.
* College working-day hours and holiday class calculations.
* Special 6-day holiday break in December (with optional 7th day toggle).
* Compulsory 2 Daily DSA questions with status updates and hints.
* English speaking logs, topic rotation, and streak counting.
* Daily inspirational quotes and favorite toggling.
* Calendar event creation, query, and deletion.
* Prerequisite topological ordering and dependency enforcement.
* Adaptive rescheduling and task progress persistence.
* Backup export and restore.

---

## 🔒 Data Persistence & Backups

* **Database File**: `data/lastchance.db` (automatically migrated from legacy `data/studypilot.db` with zero data loss).
* **Backup Export**: Go to Settings → Click **Export JSON Backup** to download your complete study history, custom events, and notes.
* **Backup Restore**: Upload your JSON backup in Settings to restore all records.
