# Last Chance — Personal Study Planner & Exam Management System

<p align="center">
  <img src="frontend/static/assets/logo.png" alt="Last Chance Logo" width="220" />
  <br>
  <strong>Small Steps • Big Results</strong>
  <br>
  <em>A focused, intentional personal study planner built to master university syllabus, daily DSA, and exam readiness.</em>
</p>

---

## 🏔️ Brand & Visual Identity

The Last Chance design system is grounded in the official brand asset:
* **Symbolism**: The mountain peak, sunrise sunburst, summit flag, and winding ascent path.
* **Color Palette**:
  - Deep Navy (`#0C1628` / `#0A111F`) & Mountain Slate (`#162544` / `#1E3A5F`)
  - Warm Ivory (`#FAF8F5`) & Clean White (`#FFFFFF`)
  - Sunrise Amber (`#F59E0B`) & Flag Red-Orange (`#EF4444` / `#E11D48`)
* **Assets**: High-resolution icons and favicons located in `frontend/static/assets/`:
  - `logo.png` (High-res brand banner)
  - `logo_badge.png` (Circular icon badge for sidebar & navbar)
  - `logo_transparent.png` (Transparent cutout)
  - `favicon.ico`, `favicon.png`, `favicon-32.png`

---

## 🌟 Key Features & Core Philosophy

### 1. Distinct, Realistic Daily Routine Allocations
The system strictly segregates and monitors your daily academic and professional commitments:
* **Academic Coursework Target**: **4 Hours (240 minutes)** per day reserved exclusively for semester subjects across 5 structured 45-minute shifts plus a 15-minute daily wrap-up:
  - Discrete Structures (`CSN 3003` — 4 Credits, prioritized from Unit 2 onwards)
  - Data Structures (`CSN 3001` — 4 Credits)
  - Object-Oriented Programming (`CSN 3004` — 4 Credits)
  - Data Science & Machine Learning (`CSN 3002` — 4 Credits)
* **Two Daily DSA Questions with Actual Topics**: Exactly 2 actionable questions assigned per day (outside the 4-hour academic target) with exact problem titles, syllabus topics, difficulty ratings, LeetCode / GeeksforGeeks URLs, solution notes, and an in-app "Replace Question" selector.
* **English Speaking Fluency**: **30 minutes** of speaking drills with rotating topics across technical explanations, elevator pitches, and project walkthroughs, complete with an interactive timer and streak tracker.
* **Redo / Practice Again Queue**: Complete tasks with "Complete & Add to Redo" to schedule spaced repetition without inflating syllabus completion metrics. Track redo attempts, notes, and priority.
* **College Commitments**: Distinctly separates college class hours (default 3.0 hrs on Mon–Fri working days, 0 hrs on holidays, configurable 5 hrs for special dates) from personal study hours.
* **Special Holiday Break**: Fully configurable break (6–11 December 2026). Flags that this range contains 6 calendar days and provides an option to extend to the 7th day (12 December).

### 2. Live Date & Time Engine
* Displays real-time local date, weekday, and seconds-accurate clock synchronized with **India Standard Time (`Asia/Kolkata`)**.
* Live countdowns to exam milestones and syllabus deadlines.
* Past-due items display clear overdue notices rather than misleading timers.

### 3. Fully Interactive Study Calendar
* **Unified Event Aggregation**: Combines scheduled shifts, daily DSA assignments, English sessions, exams, and personal study events.
* **Three Switchable Views**: Month view, Week view, and Day view.
* **Seamless Navigation**: Previous / Next month buttons, "Today" button, and date selection modal with one-click focus launch.
* **Custom Calendar Events**: Add, edit, and delete personal study commitments and milestones.

### 4. Quote of the Day Hero
* Located at the very top of the dashboard, immediately visible above the fold without scrolling.
* Date-stable in India Standard Time (`Asia/Kolkata`) across six curated themes:
  - Consistency & Discipline
  - Parents & Gratitude
  - Faith in God
  - Success & Perseverance
  - Patience & Hope
  - Study & Learning
* Verified author attribution, inspirational styling, and favorite toggling.

### 5. Handouts & Missing Materials Checklist
* Course syllabus documents and lecture notes organized under course and unit.
* Built-in **Missing Materials Checklist** (`/api/handouts/missing-checklist`) identifying units needing lecture notes and providing direct upload shortcuts.
* Accessible previews for PDFs, text files, and images.

### 6. Analytics, Graphs & Study Insights
* Responsive Chart.js visualizations with automatic label rotation and skipping to prevent overlap on mobile (320px–430px) and desktop (1024px–1920px).
* Tracks academic study hours, daily target compliance, DSA completion, English streak, and recorded distraction/wasted time.

### 7. Complete Dark & Light Theme System
* Built on semantic CSS variables with WCAG AA compliant contrast.
* Prevents dark-on-dark or light-on-light text artifacts.
* Theme preference is saved locally and synchronized to the user account in PostgreSQL / SQLite.

### 8. Cross-Device Persistence & Authentication
* Multi-device sync enabled with secure PBKDF2 password hashing and JWT token authentication.
* Cloud-ready PostgreSQL migration script (`scripts/migrate_to_postgres.py`) preserves all existing task history, custom events, settings, and notes.

---

## 📚 Pre-Loaded Semester Courses

1. **Discrete Structures for Computer Science** (`CSN 3003` — 4 Credits, 42 Lectures)
2. **Data Structures** (`CSN 3001` — 4 Credits, 42 Lectures)
3. **Object Oriented Programming** (`CSN 3004` — 4 Credits, 42 Lectures)
4. **Data Science & Machine Learning** (`CSN 3002` — 4 Credits, 42 Lectures)

---

## 🚀 Local Execution (Windows)

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
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
# or
python main.py
```

### Port Conflict Handling
If port 8000 is occupied, `main.py` detects the process and automatically switches to the next available port (e.g. 8001). You can also specify a custom port:
```powershell
python main.py --port 8080
```

---

## 🌐 Cloud Deployment (Render / Docker)

### Option A: Render Blueprint (Recommended for Web + Managed PostgreSQL)
The repository includes a ready-to-deploy `render.yaml` blueprint:
1. Fork or push this repository to GitHub.
2. Log in to [Render](https://render.com) and click **New +** → **Blueprint**.
3. Select your repository. Render will automatically provision:
   - **Web Service** (FastAPI backend + static frontend).
   - **PostgreSQL Database** (`lastchance-db`).
   - **Persistent Disk** (`lastchance-data` mounted at `/var/data` for local uploads/backups).
4. Fill in `SECRET_KEY` in Render environment settings.

### Option B: Docker Container
Build and run using Docker:
```bash
docker build -t last-chance:latest .
docker run -p 8000:8000 -v $(pwd)/data:/app/data -v $(pwd)/uploads:/app/uploads last-chance:latest
```
Or with docker-compose:
```bash
docker-compose up -d
```

### Database Migration: SQLite to PostgreSQL
To transfer your local study progress to your deployed PostgreSQL database:
```bash
export DATABASE_URL="postgresql://user:password@hostname:5432/dbname"
python scripts/migrate_to_postgres.py --sqlite data/lastchance.db --postgres "$DATABASE_URL"
```

---

## 🧪 Automated Testing

Run the full pytest test suite (all 43 tests passing):
```powershell
python -m pytest backend/tests -v -p no:cacheprovider
```

The automated test suite verifies:
* 240-minute daily academic study targets and shift completions.
* Redo queue workflows: creation, completion without syllabus inflation, notes, and deletion.
* Compulsory 2 Daily DSA questions with status updates, syllabus topics, and in-app replacement.
* English speaking logs, topic rotation, and streak counting.
* Full calendar event aggregation (shifts, DSA, English, exams, custom events).
* User authentication: registration, PBKDF2 password hashing, JWT token validation, and theme persistence.
* Missing materials checklist across all 4 courses and units.
* College working-day hours, holiday calculations, and 6-day December break.
* Data export and backup restoration.

---

## 🔒 Data Security & Backups

* **Local Database**: `data/lastchance.db` (never committed to git).
* **Backup Export**: Go to Settings → Click **Export JSON Backup** to download your complete study history, custom events, and notes.
* **Backup Restore**: Upload your JSON backup in Settings to restore all records.
* **Environment Variables**: Configure secrets safely using `.env` (template in `.env.example`).
