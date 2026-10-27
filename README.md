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

### Option B: Cloud Architecture (Vercel + Render + Supabase)

Last Chance is engineered to run seamlessly across:
* **Frontend**: Vercel (Fast, global CDN hosting of the React/Tailwind client)
* **Backend**: Render Free (FastAPI REST service with dynamic port binding)
* **Database**: Supabase PostgreSQL (Persistent, managed multi-device database)
* **Storage**: Supabase Storage (Private bucket for lecture handouts and syllabus files)

---

## ⚡ Supabase Setup & Cloud Migration Guide

### 1. Supabase Dashboard Setup
1. **Create Project**:
   - Go to [supabase.com](https://supabase.com) and click **New Project** (e.g. `lastchance-prod`).
   - Set a strong database password and select your closest AWS region.
2. **Retrieve PostgreSQL Connection String**:
   - Go to **Project Settings** → **Database** → **Connection string**.
   - Copy the **URI** under Session Pooler (or Direct connection):
     ```
     postgresql://postgres.[PROJECT_REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```
3. **Create Private Storage Bucket**:
   - Go to **Storage** → **New Bucket**.
   - Bucket name: `handouts`
   - Keep **Public bucket** toggled **OFF** (Last Chance uses backend-authenticated streaming to protect private academic notes).
4. **Retrieve API Keys**:
   - Go to **Project Settings** → **API**.
   - Copy the **Project URL** (`https://[PROJECT_REF].supabase.co`).
   - Copy the **service_role** secret key (for secure backend file operations).

---

### 2. Database Migration (SQLite → Supabase PostgreSQL)

The migration script safely transfers all 23 tables, foreign keys, and serial sequences without modifying your original SQLite database:

**Step A: Dry Run Verification**
```powershell
python scripts/migrate_sqlite_to_supabase.py --dry-run
```
*Validates all 1,289+ records, table schemas, and foreign keys without performing any writes.*

**Step B: Live Production Migration**
```powershell
python scripts/migrate_sqlite_to_supabase.py --db-url "postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres"
```
*Applies `backend/migrations/001_supabase_schema.sql`, inserts all records using `ON CONFLICT` resolution (safe to rerun), aligns PostgreSQL serial sequences, and verifies row counts.*

---

### 3. Handout Files Migration (Local uploads/ → Supabase Storage)

**Step A: Dry Run File Inspection**
```powershell
python scripts/migrate_handouts_to_supabase.py --dry-run
```
*Checks all 6 course handouts and syllabus documents in `uploads/`.*

**Step B: Live Upload to Supabase**
```powershell
$env:SUPABASE_URL="https://[PROJECT_REF].supabase.co"
$env:SUPABASE_KEY="[YOUR_SERVICE_ROLE_KEY]"
python scripts/migrate_handouts_to_supabase.py
```
*Uploads materials to the private `handouts` bucket with mime-types and metadata while keeping local copies in `uploads/` 100% intact.*

---

### 4. Deploy Backend to Render Free
1. Sign in to [render.com](https://render.com) and click **New** → **Web Service**.
2. Connect your GitHub repository: `https://github.com/amankr28819-prog/Last-Chance.git`.
3. Configure the service:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/api/health`
4. Add **Environment Variables** under the Environment tab:
   - `DATABASE_URL`: Your Supabase connection string.
   - `SUPABASE_URL`: `https://[PROJECT_REF].supabase.co`
   - `SUPABASE_KEY`: Your Supabase `service_role` key.
   - `SUPABASE_STORAGE_BUCKET`: `handouts`
   - `JWT_SECRET_KEY`: A secure 64-character hex key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`).
   - `CORS_ORIGINS`: Your Vercel frontend URL (e.g. `https://last-chance.vercel.app`).

---

### 5. Deploy Frontend to Vercel
1. Sign in to [vercel.com](https://vercel.com) and click **Add New** → **Project**.
2. Import your GitHub repository.
3. In **Root Directory**, leave as `./` or select `frontend`.
4. If deploying static files separately or setting custom backend endpoint:
   - Update `<meta name="api-base-url" content="https://lastchance-backend.onrender.com" />` in `frontend/index.html` or set `window.__LAST_CHANCE_API_BASE__`.

---

## 🧪 Automated Testing

Run the full pytest test suite (44+ tests passing):
```powershell
python -m pytest backend/tests -v -p no:cacheprovider
```

The automated test suite verifies:
* 240-minute daily academic study targets and shift completions.
* 3-level Handout hierarchy (`/api/handouts/hierarchy`) with course, unit, and topic completion persistence.
* Dual-mode database compatibility (PostgreSQL adapter and local SQLite fallback).
* Storage service with private Supabase Storage streaming and local fallback.
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

* **Local Database**: `data/lastchance.db` (never committed to git, excluded via `.gitignore`).
* **Supabase PostgreSQL**: Encrypted at rest, SSL connections enforced, protected behind connection pooling.
* **Handouts Storage**: Hosted in private Supabase Storage bucket; accessed exclusively via authenticated signed URLs or backend streaming proxy.
* **Backup Export**: Use `GET /api/database/backup` to download your complete study history, custom events, and notes as a verified JSON bundle.
* **Environment Variables**: Configure secrets safely using `.env` (template in `.env.example`). Real credentials are never committed.
