# StudyPilot — Your Personal Exam Planning System

**StudyPilot** is an intelligent, workload-aware, adaptive semester examination planning web application designed to run 100% locally on your Windows laptop.

The core purpose of the system is to ensure you **complete your entire university syllabus before examinations**, achieve your **first full syllabus pass at least seven calendar days before your first examination (19 November 2026)**, and protect the remaining buffer period for **spaced revision, weak-concept recall, and timed mock practice**.

---

## 🌟 Key Features & Core Philosophy

1. **Realistic, Capacity-Bounded Planning**:
   - Never assigns more study hours than your configured available daily capacity.
   - Calculates study windows accounting for college hours, commute, sleep schedule, and weekend versus weekday differences.
   - Splits oversized topics across multiple days rather than scheduling impossible sessions.

2. **Deterministic Prerequisite Graph**:
   - 57 prerequisite relationships pre-seeded across your computer science curriculum.
   - Advanced concepts (e.g., AVL trees, Dijkstra's algorithm, inheritance, Bayes' theorem, multiple regression) are **strictly scheduled after** their foundational prerequisites.

3. **Mastery-Aware Effort Recalculation**:
   - Adjusts required first-pass minutes based on your current confidence level:
     - `Not Started`: 100% effort
     - `Studied Once`: 90% effort
     - `Partially Understood`: 80% effort
     - `Needs Revision`: 60% effort
     - `Confident`: 25% effort
     - `Mastered`: 0% first-pass effort (reserved for revision)

4. **Adaptive Schedule Recovery & Stability**:
   - If a task is missed or partially completed (e.g. 50%), StudyPilot **preserves all completed work** and automatically carries forward the exact remaining portion into upcoming free slots.
   - Adheres to **schedule stability**: shifts only what is necessary, preserving unaffected future plans.
   - Explains every schedule adjustment in a human-readable audit log.

5. **Protected 7-Day Pre-Exam Revision Buffer**:
   - Given a first examination date of **26 November 2026**, StudyPilot targets complete first-pass syllabus completion by **19 November 2026**.
   - The buffer from **19 November through 25 November** is dedicated to timed problem-solving, formula review, and weak-area drills.

6. **Local-First & Zero AI API Dependency**:
   - All data is saved in a local SQLite database (`data/studypilot.db`).
   - Frontend libraries (React 18, Babel standalone, Tailwind CSS, Chart.js, Lucide) are vendored locally in `frontend/static/vendor/`—meaning StudyPilot works **completely offline** without external internet access or commercial AI subscriptions.

---

## 📚 Initial Pre-Loaded Subjects

The application comes pre-loaded with the official university syllabus for all four semester courses:

1. **Discrete Structures for Computer Science** (`CSN 3003` - 4 Credits, 42 Lectures)
   - Unit 1: Mathematical Reasoning
   - Unit 2: Set Theory
   - Unit 3: Functions
   - Unit 4: Combinatorics
   - Unit 5: Graph Theory, Groups, Rings and Fields
   - Unit 6: Discrete Probability
2. **Data Structures** (`CSN 3001` - 4 Credits, 42 Lectures)
   - Unit 1: Review
   - Unit 2: Linked Lists (including Sparse Matrix & Polynomial operations)
   - Unit 3: Stacks (Balanced brackets, Infix-to-postfix, Evaluation)
   - Unit 4: Queues (Job scheduling)
   - Unit 5: Trees (Traversals, BFS, DFS)
   - Unit 6: Binary Search Trees (AVL trees, B-trees)
   - Unit 7: Graphs (Dijkstra, MST, Prim, Kruskal, Union-Find)
   - Unit 8: Advanced Data Structures (Heaps, Hashing, Indexing)
3. **Object Oriented Programming** (`CSN 3004` - 4 Credits, 42 Lectures)
   - Unit 1: Introduction to OOP and Design
   - Unit 2: Programming Basics
   - Unit 3: Classes (Constructors, Copy constructors, Destructors, Friend functions)
   - Unit 4: Overloading (Unary, Binary, Assignment operator)
   - Unit 5: Inheritance (Hierarchies, Constructor order, Aggregation)
   - Unit 6: Pointers and Virtual Functions (Dynamic memory, VTABLE, Abstract classes)
4. **Data Science & Machine Learning** (`CSN 3002` - 4 Credits, 42 Lectures)
   - Unit 1: Introduction to Data Science & Linear Algebra
   - Unit 2: Data Acquisition & Preprocessing (Missing data, Scaling, Encoding)
   - Unit 3: Machine Learning Fundamentals (Bias-Variance, ROC, F1, Cross-Validation)
   - Unit 4: Regression and Classification (Linear, Logistic, Gradient Descent, KNN, SVM, Trees)
   - Unit 5: Dimensionality Reduction and Clustering (PCA, K-Means, DBSCAN)

---

## 🚀 Quick Start (Windows)

### Prerequisites
* **Operating System**: Windows 10 or Windows 11.
* **Python**: Python 3.10 through 3.14+ (tested and verified with Python 3.14.0).

### Method 1: One-Click Startup (Recommended)
Simply double-click:
```cmd
run.bat
```
or run in PowerShell / Command Prompt:
```powershell
.\run.bat
```

The script automatically:
1. Anchors to the project directory (`cd /d "%~dp0"`).
2. Verifies Python availability and version.
3. Performs a fast dependency check and installs packages only if missing (avoiding slow pip reinstalls on every launch).
4. Safely initializes or verifies the local SQLite database without overwriting your saved data.
5. Launches the server and automatically opens `http://127.0.0.1:8000` in your default browser.

### Method 2: Manual Terminal Execution
```powershell
# 1. Install dependencies (first time only)
python -m pip install -r requirements.txt

# 2. Run the application
python main.py
```

Then navigate to:
👉 **`http://127.0.0.1:8000`**

To stop the server at any time, press `Ctrl + C` in the console window.

---

## 🔧 Port Configuration & Conflict Resolution

If port `8000` is occupied by another process:
1. **Auto-Fallback**: By default, `main.py` detects when port 8000 is occupied, identifies the occupying process, and automatically switches to the next free port (e.g. `8001`, `8002`), displaying the exact URL and opening your browser.
2. **Custom Port Selection**: You can specify an explicit port:
   ```powershell
   python main.py --port 8080
   ```
   Or set the environment variable:
   ```powershell
   $env:STUDYPILOT_PORT = 8080
   python main.py
   ```
3. **Checking and Freeing Port 8000**:
   To inspect which process is using port 8000:
   ```powershell
   Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress, LocalPort, OwningProcess
   ```
   To stop a specific process by its PID:
   ```powershell
   Stop-Process -Id <PID>
   ```

---

## 🧪 Running the Test Suite

StudyPilot includes a test suite covering date calculations, capacity bounds, prerequisite graph integrity, adaptive rescheduling, and data persistence:

```powershell
python -m pytest backend/tests -v -p no:cacheprovider
```

All 14 tests pass with zero warnings or errors.

To run the in-process API verification module:
```powershell
python -m backend.test_api_inprocess
```

---

## 💾 Local Data Storage & Backup Preservation

- **Location**: All study plans, topic ratings, and custom configurations are stored locally in:
  `data/studypilot.db`
- **Git Protection**: `data/*.db` is excluded from version control in `.gitignore`. Your study progress is kept strictly private and will never be overwritten by Git operations.
- **JSON Export / Restore**:
  - Open **Settings** inside the application.
  - Click **Export JSON Backup** to save a snapshot of your curriculum and schedule history.
  - Click **Restore from JSON** to reload or migrate your database on any machine.
