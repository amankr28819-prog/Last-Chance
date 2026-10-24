import sqlite3
import json
import os
import shutil
from datetime import datetime, date
from typing import Optional, Dict, Any, List

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DATA_DIR, "lastchance.db")
OLD_DB_PATH = os.path.join(DATA_DIR, "studypilot.db")

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Safe migration: if old studypilot.db exists and lastchance.db does not, migrate it
    if not os.path.exists(db_path) and os.path.exists(OLD_DB_PATH):
        try:
            shutil.copy2(OLD_DB_PATH, db_path)
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db(db_path: str = DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        credits INTEGER NOT NULL DEFAULT 4,
        total_lectures INTEGER NOT NULL DEFAULT 42,
        exam_date TEXT,
        priority TEXT NOT NULL DEFAULT 'NORMAL', -- 'NORMAL', 'HIGH', 'URGENT'
        color TEXT NOT NULL DEFAULT '#6366f1',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        unit_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        lecture_allocation INTEGER NOT NULL DEFAULT 6,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unit_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        estimated_minutes INTEGER NOT NULL DEFAULT 60,
        base_minutes INTEGER NOT NULL DEFAULT 60,
        mastery_level TEXT NOT NULL DEFAULT 'NOT_STARTED', -- NOT_STARTED, STUDIED_ONCE, PARTIALLY_UNDERSTOOD, NEEDS_REVISION, CONFIDENT, MASTERED
        is_mandatory INTEGER NOT NULL DEFAULT 1,
        is_official INTEGER NOT NULL DEFAULT 1,
        source_doc TEXT DEFAULT 'Official Syllabus',
        order_index INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS subtopics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        order_index INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS prerequisites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        prerequisite_topic_id INTEGER NOT NULL,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
        FOREIGN KEY (prerequisite_topic_id) REFERENCES topics(id) ON DELETE CASCADE,
        UNIQUE(topic_id, prerequisite_topic_id)
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS study_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scheduled_date TEXT NOT NULL,
        topic_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        duration_minutes INTEGER NOT NULL,
        planned_start_time TEXT,
        status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, COMPLETED, PARTIALLY_COMPLETED, MISSED
        task_type TEXT NOT NULL DEFAULT 'NEW_LEARNING', -- NEW_LEARNING, PRACTICE, REVISION, TEST
        priority TEXT NOT NULL DEFAULT 'NORMAL',
        learning_objectives TEXT,
        suggested_breakdown TEXT,
        study_method TEXT,
        actual_minutes INTEGER DEFAULT 0,
        completion_percentage INTEGER DEFAULT 0,
        confidence_rating INTEGER DEFAULT 0,
        notes TEXT,
        blockers TEXT,
        practice_attempted INTEGER DEFAULT 0,
        completed_at TEXT,
        reasoning TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
        FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        schedule_id INTEGER,
        started_at TEXT NOT NULL,
        ended_at TEXT,
        duration_seconds INTEGER DEFAULT 0,
        notes TEXT,
        confidence_rating INTEGER DEFAULT 0,
        completion_percentage INTEGER DEFAULT 0,
        actual_minutes INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
        FOREIGN KEY (schedule_id) REFERENCES study_schedules(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS schedule_change_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL DEFAULT (datetime('now')),
        reason TEXT NOT NULL,
        changes_summary TEXT NOT NULL,
        affected_dates_json TEXT
    );

    CREATE TABLE IF NOT EXISTS revision_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        scheduled_date TEXT NOT NULL,
        interval_days INTEGER NOT NULL DEFAULT 1,
        revision_type TEXT NOT NULL DEFAULT 'RECALL', -- RECALL, PROBLEM_SOLVING, CODE_PRACTICE, FORMULA, MOCK_TEST
        status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, COMPLETED, SKIPPED
        confidence_recorded INTEGER DEFAULT 0,
        completed_at TEXT,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
    );

    -- New Dedicated Tables for Personalized Routine
    CREATE TABLE IF NOT EXISTS dsa_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL DEFAULT 'Medium', -- Easy, Medium, Hard
        description TEXT NOT NULL,
        problem_statement TEXT,
        concept TEXT NOT NULL,
        hints_json TEXT,
        hint_1 TEXT,
        hint_2 TEXT,
        solution TEXT NOT NULL,
        solution_approach TEXT,
        solution_code TEXT,
        approach_notes TEXT,
        time_complexity TEXT DEFAULT 'O(N)',
        space_complexity TEXT DEFAULT 'O(1)',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS daily_dsa_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assigned_date TEXT NOT NULL,
        question_id INTEGER NOT NULL,
        slot_number INTEGER DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'Pending', -- Pending, Attempted, Solved, Needs Revision
        user_approach TEXT,
        approach_notes TEXT,
        time_spent_minutes INTEGER DEFAULT 0,
        mistakes_notes TEXT,
        mistakes TEXT,
        completed_at TEXT,
        FOREIGN KEY (question_id) REFERENCES dsa_questions(id) ON DELETE CASCADE,
        UNIQUE(assigned_date, question_id)
    );

    CREATE TABLE IF NOT EXISTS english_speaking_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        objective TEXT NOT NULL,
        vocabulary_json TEXT NOT NULL,
        starter_phrases_json TEXT,
        prompt_questions_json TEXT,
        vocabulary TEXT,
        speaking_prompts TEXT
    );

    CREATE TABLE IF NOT EXISTS daily_english_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assigned_date TEXT UNIQUE,
        log_date TEXT UNIQUE,
        topic_id INTEGER NOT NULL,
        duration_seconds INTEGER DEFAULT 0,
        time_spent_seconds INTEGER DEFAULT 0,
        notes TEXT,
        completed INTEGER NOT NULL DEFAULT 0,
        is_completed INTEGER NOT NULL DEFAULT 0,
        streak_count INTEGER NOT NULL DEFAULT 0,
        completed_at TEXT,
        FOREIGN KEY (topic_id) REFERENCES english_speaking_topics(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS daily_quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quote TEXT NOT NULL,
        quote_text TEXT,
        category TEXT NOT NULL,
        author TEXT DEFAULT 'Unknown',
        is_favorite INTEGER NOT NULL DEFAULT 0,
        day_offset INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        event_type TEXT NOT NULL DEFAULT 'study', -- study, college, holiday, exam, personal
        start_time TEXT,
        end_time TEXT,
        duration_minutes INTEGER NOT NULL DEFAULT 60,
        subject_code TEXT,
        color TEXT,
        notes TEXT,
        is_completed INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    conn.commit()
    seed_initial_data_if_empty(conn)
    seed_dsa_questions_if_empty(conn)
    seed_english_topics_if_empty(conn)
    seed_quotes_if_empty(conn)

    # Ensure standard aliases for targets are populated
    for k, v in [("daily_academic_target_minutes", 240), ("english_speaking_target_minutes", 30), ("daily_dsa_count", 2)]:
        if get_setting(conn, k) is None:
            set_setting(conn, k, v)

    conn.close()

def get_setting(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    if row:
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]
    return default

def set_setting(conn: sqlite3.Connection, key: str, value: Any):
    cursor = conn.cursor()
    val_str = json.dumps(value) if not isinstance(value, str) else value
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, val_str))
    conn.commit()

def seed_initial_data_if_empty(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM subjects")
    has_subjects = cursor.fetchone()["count"] > 0

    # Default Settings
    default_settings = {
        "app_name": "Last Chance",
        "first_exam_date": "2026-11-26",
        "syllabus_deadline": "2026-11-19",
        "revision_buffer_days": 7,
        "is_buffer_mandatory": True,
        # Daily study targets strictly separated
        "academic_daily_target_minutes": 240, # 4 Hours main academic study
        "daily_academic_target_minutes": 240,
        "english_daily_target_minutes": 30,    # 30 Minutes English speaking
        "english_speaking_target_minutes": 30,
        "dsa_daily_question_count": 2,         # 2 DSA questions daily
        "daily_dsa_count": 2,
        # College schedule
        "college_working_day_hours": 3.0,     # 3 hours on working days
        "college_holiday_hours": 5.0,         # 5 hours on holidays if marked
        "working_days": ["mon", "tue", "wed", "thu", "fri"],
        "weekly_holidays": ["sat", "sun"],
        # Special 7-day holiday (6-11 Dec inclusive = 6 days, option for 7th)
        "special_break_start": "2026-12-06",
        "special_break_end": "2026-12-11",
        "special_break_include_7th_day": False,
        "special_break_notice": "Note: Dec 6 to Dec 11 inclusive contains 6 calendar days. You can optionally include Dec 12 as the 7th day in Settings.",
        "weekday_minutes": 240,  # 4 hours academic study
        "weekend_minutes": 300,  # 5 hours academic study on holidays
        "college_hours": "09:00 - 12:00",
        "commute_minutes": 30,
        "sleep_hours": "23:30 - 06:30",
        "study_windows": [
            {"name": "Morning Slot", "start": "06:45", "end": "08:15", "minutes": 90, "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"name": "Evening Slot", "start": "18:00", "end": "19:30", "minutes": 90, "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"name": "Night Slot", "start": "20:30", "end": "21:30", "minutes": 60, "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"name": "Weekend Morning", "start": "08:00", "end": "11:00", "minutes": 180, "days": ["sat", "sun"]},
            {"name": "Weekend Evening", "start": "16:00", "end": "18:00", "minutes": 120, "days": ["sat", "sun"]}
        ],
        "blocked_dates": [],
        "session_duration": 60,
        "max_consecutive_minutes": 90,
        "break_duration": 15,
        "subjects_per_day": 2,
        "study_style": "INTERLEAVED",
        "daily_practice": True,
        "spaced_revision": True,
        "onboarding_completed": True,
        "theme": "dark",
        "time_zone": "Asia/Kolkata"
    }

    for k, v in default_settings.items():
        cursor.execute("SELECT value FROM settings WHERE key = ?", (k,))
        if not cursor.fetchone():
            val_str = json.dumps(v) if not isinstance(v, str) else v
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, val_str))

    if has_subjects:
        return

    # Seed the 4 official subjects
    subjects_data = [
        {
            "code": "CSN 3003",
            "name": "Discrete Structures for Computer Science",
            "credits": 4,
            "total_lectures": 42,
            "color": "#6366f1",
            "priority": "HIGH",
            "exam_date": "2026-11-26",
            "units": [
                {
                    "unit_number": 1,
                    "title": "Mathematical Reasoning",
                    "lecture_allocation": 8,
                    "topics": [
                        ("Mathematical reasoning", 60, ["Logic structures", "Deductive vs inductive reasoning"]),
                        ("Propositions", 45, ["Declarative statements", "Truth values"]),
                        ("Negation", 30, ["Truth inversion", "Logical NOT operator"]),
                        ("Disjunction and conjunction", 45, ["Logical OR, AND", "Truth conditions"]),
                        ("Implication and equivalence", 60, ["Conditional statements", "Biconditional", "Converse, inverse, contrapositive"]),
                        ("Truth tables", 60, ["Table construction", "Tautologies", "Contradictions", "Contingencies"]),
                        ("Predicates", 45, ["Propositional functions", "Domain of discourse"]),
                        ("Quantifiers", 60, ["Universal quantifier", "Existential quantifier", "Negating quantified expressions"]),
                        ("Natural deduction", 90, ["Inference rules", "Derivation trees", "Hypothetical reasoning"]),
                        ("Rules of inference", 75, ["Modus Ponens", "Modus Tollens", "Hypothetical Syllogism", "Disjunctive Syllogism"]),
                        ("Methods of proofs", 90, ["Direct proof", "Proof by contraposition", "Proof by contradiction", "Exhaustive proof"]),
                        ("Resolution principle", 75, ["Clausal form", "Unification", "Resolution refutation"]),
                        ("Application to PROLOG", 60, ["Facts and rules", "Query evaluation", "Prolog horn clauses"])
                    ]
                },
                {
                    "unit_number": 2,
                    "title": "Set Theory",
                    "lecture_allocation": 8,
                    "topics": [
                        ("Paradoxes in set theory", 45, ["Russell's paradox", "Naive set theory limitations"]),
                        ("Inductive definition of sets", 60, ["Base case", "Inductive step", "Closure"]),
                        ("Proof by induction", 75, ["Mathematical induction", "Strong induction", "Well-ordering principle"]),
                        ("Peano postulates", 60, ["Axioms for natural numbers", "Successor function"]),
                        ("Relations", 45, ["Binary relations", "Domain and range", "Matrix and digraph representation"]),
                        ("Properties of relations", 60, ["Reflexive", "Symmetric", "Transitive", "Antisymmetric"]),
                        ("Equivalence relations and partitions", 75, ["Equivalence classes", "Quotient sets", "Fundamental partition theorem"]),
                        ("Partial orderings", 60, ["Reflexive, antisymmetric, transitive relations", "Comparability"]),
                        ("POSETs", 60, ["Partially ordered sets", "Hasse diagrams", "Maximal/minimal elements"]),
                        ("Linear and well-ordered sets", 60, ["Total order", "Well-ordered sets", "Lexicographic ordering"])
                    ]
                },
                {
                    "unit_number": 3,
                    "title": "Functions",
                    "lecture_allocation": 6,
                    "topics": [
                        ("Functions", 45, ["Definition", "Domain, codomain, range"]),
                        ("Mappings", 45, ["Total vs partial mappings", "Image and preimage"]),
                        ("Injection", 45, ["One-to-one functions", "Horizontal line test"]),
                        ("Surjections", 45, ["Onto functions", "Codomain coverage"]),
                        ("Composition of functions", 60, ["Associativity of composition", "Identity mapping"]),
                        ("Inversions", 60, ["Bijections", "Inverse function properties"]),
                        ("Special functions", 60, ["Floor and ceiling", "Mod function", "Characteristic function"]),
                        ("Recursive function theory", 75, ["Primitive recursive functions", "Ackermann function", "Computability"])
                    ]
                },
                {
                    "unit_number": 4,
                    "title": "Combinatorics",
                    "lecture_allocation": 9,
                    "topics": [
                        ("Elementary combinatorics", 45, ["Sum rule", "Product rule", "Inclusion-exclusion principle"]),
                        ("Pigeonhole principle", 60, ["Standard form", "Generalized pigeonhole principle", "Applications"]),
                        ("Permutations and combinations", 75, ["Formulas", "Combinations with repetitions", "Binomial coefficients"]),
                        ("Counting techniques", 60, ["Circular permutations", "Derangements", "Partitions of integers"]),
                        ("Recurrence relations", 60, ["Formulating recurrences", "Initial conditions"]),
                        ("Solving linear recurrence relations", 90, ["Homogeneous linear recurrences", "Particular solutions", "Characteristic roots"]),
                        ("Generating functions", 90, ["Ordinary generating functions", "Solving recurrences using generating functions"])
                    ]
                },
                {
                    "unit_number": 5,
                    "title": "Graph Theory, Groups, Rings and Fields",
                    "lecture_allocation": 8,
                    "topics": [
                        ("Elements of graph theory", 60, ["Vertices, edges, degrees", "Handshaking lemma", "Subgraphs"]),
                        ("Graph isomorphism", 60, ["Adjacency matrix equivalence", "Invariants of isomorphism"]),
                        ("Euler graph", 60, ["Eulerian path and circuit", "Euler's theorem", "Fleury's algorithm"]),
                        ("Hamiltonian paths", 60, ["Hamiltonian circuits", "Dirac's theorem", "Ore's theorem"]),
                        ("Trees", 60, ["Tree definitions", "Properties of trees", "Rooted trees"]),
                        ("Tree traversals", 60, ["Inorder, preorder, postorder traversals in graph contexts"]),
                        ("Spanning trees", 60, ["Cut property", "Cycle property", "Fundamental cycles"]),
                        ("Representation of relations by graphs", 45, ["Directed graph of a relation", "Transitive closure and Warshall's algorithm"]),
                        ("Definition and elementary properties of groups", 75, ["Closure, associativity, identity, inverse", "Abelian groups"]),
                        ("Semigroups", 45, ["Associative binary operation", "Subsemigroups"]),
                        ("Monoids", 45, ["Semigroup with identity element", "Submonoids"]),
                        ("Rings", 60, ["Ring definition", "Distributive laws", "Zero divisors", "Integral domains"]),
                        ("Fields", 60, ["Field definition", "Finite fields / Galois fields", "Inverses in fields"]),
                        ("Vector spaces", 60, ["Axioms", "Subspaces", "Linear independence", "Basis and dimension"]),
                        ("Lattices", 60, ["POSET as lattice", "Meet and join operations", "Distributive and modular lattices"])
                    ]
                },
                {
                    "unit_number": 6,
                    "title": "Discrete Probability",
                    "lecture_allocation": 3,
                    "topics": [
                        ("Introduction to probability", 45, ["Sample spaces", "Events", "Axioms of probability"]),
                        ("Probability theory", 60, ["Conditional probability", "Independence of events"]),
                        ("Bayes' theorem", 75, ["Law of total probability", "Posterior probability calculation"]),
                        ("Expected value and variance", 60, ["Expectation of random variables", "Properties of variance"]),
                        ("Discrete random variables", 60, ["Bernoulli, Binomial, and Geometric distributions"])
                    ]
                }
            ]
        },
        {
            "code": "CSN 3001",
            "name": "Data Structures",
            "credits": 4,
            "total_lectures": 42,
            "color": "#10b981",
            "priority": "HIGH",
            "exam_date": "2026-11-28",
            "units": [
                {
                    "unit_number": 1,
                    "title": "Review",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Classes", 45, ["Class structure", "Data encapsulation", "Constructors in C++"]),
                        ("Pointers", 60, ["Pointer arithmetic", "Dynamic memory", "Dangling pointers"]),
                        ("Recursion", 60, ["Base cases", "Recursive call stacks", "Tail recursion"]),
                        ("Time and space complexity of algorithms", 75, ["Big-O, Omega, Theta notations", "Worst, average, best case analysis"]),
                        ("Recurrence relations", 60, ["Formulating recursive equations for algorithms"]),
                        ("Solving recurrence relations using the substitution method", 75, ["Mathematical induction verification", "Master theorem intro"])
                    ]
                },
                {
                    "unit_number": 2,
                    "title": "Linked Lists",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Introduction to linked lists", 45, ["Node structure", "Singly linked list representation"]),
                        ("Insertion", 60, ["Insert at beginning, end, and given position", "Edge cases"]),
                        ("Deletion", 60, ["Delete by value, delete at position", "Memory deallocation"]),
                        ("Searching in linked lists", 45, ["Linear search", "Traversal efficiency"]),
                        ("Doubly linked lists", 60, ["Forward and backward pointers", "Insertion and deletion in DLL"]),
                        ("Circular linked lists", 60, ["Circular singly and doubly linked lists", "Split and traversal"]),
                        ("Sparse matrix storage", 60, ["Sparse matrix representation using linked lists", "Memory comparison"]),
                        ("Polynomial operations", 75, ["Polynomial addition and multiplication using linked lists"])
                    ]
                },
                {
                    "unit_number": 3,
                    "title": "Stacks",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Introduction to stacks", 45, ["LIFO principle", "Push, pop, peek operations"]),
                        ("Stack implementation using arrays", 60, ["Fixed and dynamic arrays", "Stack overflow and underflow"]),
                        ("Stack implementation using linked lists", 60, ["Top pointer management", "Dynamic size"]),
                        ("Balanced brackets", 60, ["Parentheses matching algorithm", "Multi-bracket verification"]),
                        ("Infix to postfix conversion", 75, ["Operator precedence and associativity", "Shunting-yard stack algorithm"]),
                        ("Postfix evaluation", 60, ["Operand evaluation using stack", "Handling multiple operators"])
                    ]
                },
                {
                    "unit_number": 4,
                    "title": "Queues",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Introduction to queues", 45, ["FIFO principle", "Enqueue and dequeue operations"]),
                        ("Queue implementation using arrays", 60, ["Linear queue and circular queue to prevent waste of space"]),
                        ("Queue implementation using linked lists", 60, ["Front and rear pointer operations"]),
                        ("Job scheduling in CPU", 75, ["Round robin queue implementation", "Ready queue management"])
                    ]
                },
                {
                    "unit_number": 5,
                    "title": "Trees",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Introduction to trees", 45, ["Root, leaves, internal nodes", "Subtrees and parent-child relations"]),
                        ("Tree terminology", 45, ["Height, depth, level, degree of node"]),
                        ("Tree representations", 60, ["Array representation", "First-child next-sibling representation"]),
                        ("Tree implementation", 60, ["Node structures in C++", "Memory layout"]),
                        ("Binary trees", 60, ["Full, complete, and degenerate binary trees", "Properties"]),
                        ("Traversals in binary trees", 75, ["Preorder, Inorder, Postorder recursive traversals"]),
                        ("BFS in binary trees", 75, ["Level order traversal using queue", "Spiral level order"]),
                        ("DFS in binary trees", 75, ["Iterative traversal using explicit stack"])
                    ]
                },
                {
                    "unit_number": 6,
                    "title": "Binary Search Trees",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Binary search trees", 60, ["BST property", "Search operation", "Min and max elements"]),
                        ("Insertion in BST", 60, ["Recursive and iterative insertion", "Maintaining BST property"]),
                        ("Deletion in BST", 90, ["Node with 0, 1, or 2 children", "Inorder predecessor/successor replacement"]),
                        ("AVL trees", 100, ["Balance factor", "LL, RR, LR, RL rotations", "AVL insertion and deletion"]),
                        ("B-trees", 90, ["Multiway search tree", "Order of B-tree", "Search, insert, and split operations"])
                    ]
                },
                {
                    "unit_number": 7,
                    "title": "Graphs",
                    "lecture_allocation": 6,
                    "topics": [
                        ("Introduction to graphs", 45, ["Directed vs undirected", "Weighted vs unweighted"]),
                        ("Graph terminology", 45, ["Degree, path, cycle, connectivity, components"]),
                        ("Graph representations", 60, ["Adjacency matrix", "Adjacency list", "Space-time comparison"]),
                        ("Graph implementation", 60, ["C++ representation with vectors and lists"]),
                        ("Graph traversal", 75, ["Breadth First Search (BFS)", "Depth First Search (DFS)", "Cycle detection"]),
                        ("Dijkstra's algorithm for single-source shortest paths", 90, ["Greedy approach", "Priority queue implementation", "Relaxation"]),
                        ("Spanning trees", 60, ["Minimum spanning tree properties", "Cut property"]),
                        ("Prim's algorithm", 75, ["Growing MST from vertex", "Min-heap implementation"]),
                        ("Kruskal's algorithm", 75, ["Edge sorting", "Cycle prevention with disjoint sets"]),
                        ("Union-find data structure", 75, ["Disjoint set union", "Find with path compression", "Union by rank"])
                    ]
                },
                {
                    "unit_number": 8,
                    "title": "Advanced Data Structures",
                    "lecture_allocation": 6,
                    "topics": [
                        ("Heaps", 75, ["Binary min-heap and max-heap", "Heapify algorithm", "Array representation"]),
                        ("Priority queues using heaps", 60, ["Insert, extract-min, decrease-key operations"]),
                        ("Hashing", 75, ["Hash functions", "Collision resolution: chaining, open addressing (linear, quadratic, double hashing)"]),
                        ("Indexing", 60, ["Dense vs sparse indexes", "B+ tree indexing principles"])
                    ]
                }
            ]
        },
        {
            "code": "CSN 3004",
            "name": "Object Oriented Programming",
            "credits": 4,
            "total_lectures": 42,
            "color": "#f59e0b",
            "priority": "NORMAL",
            "exam_date": "2026-12-01",
            "units": [
                {
                    "unit_number": 1,
                    "title": "Introduction to Object-Oriented Programming and Design",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Abstraction", 45, ["Data abstraction", "Process abstraction", "Real-world modeling"]),
                        ("Objects", 45, ["State, behavior, identity", "Object lifecycle"]),
                        ("Encapsulation", 45, ["Data binding", "Information hiding boundaries"]),
                        ("Information hiding", 45, ["Access specifiers", "Interface vs implementation"]),
                        ("Methods", 45, ["Member functions", "Message passing"]),
                        ("Method signatures", 30, ["Function name", "Parameter list", "Return type distinctions"]),
                        ("Classes and instances", 45, ["Blueprint concept", "Instantiating objects"]),
                        ("Polymorphism", 60, ["Compile-time vs run-time polymorphism", "Concept of dynamic binding"]),
                        ("Inheritance", 60, ["Code reuse", "Base and derived concepts", "Is-a relationship"])
                    ]
                },
                {
                    "unit_number": 2,
                    "title": "Programming Basics",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Variables and assignments", 30, ["L-values and R-values", "Variable scoping"]),
                        ("Input and output", 45, ["Streams in C++", "cin, cout, cerr", "Format manipulators"]),
                        ("Data types and expressions", 45, ["Primitive types", "Type casting", "Operator precedence"]),
                        ("Flow of control", 45, ["Branching (if-else, switch)", "Loops (for, while, do-while)"]),
                        ("Subprograms", 45, ["Function definitions", "Function prototypes"]),
                        ("Top-down design", 45, ["Modular decomposition", "Stepwise refinement"]),
                        ("Predefined functions", 30, ["Standard math and string library functions"]),
                        ("User-defined functions", 45, ["Defining and calling custom functions"]),
                        ("Procedural abstractions", 45, ["Separating what a function does from how it is done"]),
                        ("Local variables", 30, ["Stack frame allocation", "Scope and lifetime"]),
                        ("Parameter passing", 60, ["Pass by value", "Pass by reference", "Pass by pointer", "Const references"]),
                        ("Arrays", 60, ["One-dimensional and multidimensional arrays", "Array-pointer decay"])
                    ]
                },
                {
                    "unit_number": 3,
                    "title": "Classes",
                    "lecture_allocation": 8,
                    "topics": [
                        ("Defining classes", 60, ["Class declaration syntax", "Member variables and functions"]),
                        ("Member functions", 60, ["Inline member functions", "Outside class definition using scope resolution ::"]),
                        ("Public and private members", 45, ["Access controls", "Protected access specifier"]),
                        ("Constructors for initialization", 75, ["Default constructor", "Parameterized constructors", "Member initializer lists"]),
                        ("Destructors", 60, ["Cleanup operations", "Automatic invocation", "Resource release"]),
                        ("Copy constructors", 75, ["Shallow copy vs deep copy", "Passing objects by value"]),
                        ("Static functions", 60, ["Static member variables", "Class-level functions without this pointer"]),
                        ("Friend functions", 60, ["Friend functions and friend classes", "Breaking encapsulation safely"]),
                        ("The `this` pointer", 45, ["Self-referential pointer", "Method chaining", "Disambiguating variable names"])
                    ]
                },
                {
                    "unit_number": 4,
                    "title": "Overloading",
                    "lecture_allocation": 5,
                    "topics": [
                        ("Overloading unary operators", 60, ["++ and -- (prefix vs postfix)", "Member function vs friend function"]),
                        ("Overloading binary operators", 75, ["+, -, *, / operators for custom classes", "Stream operators << and >>"]),
                        ("Overloading the assignment operator", 75, ["Self-assignment check", "Deep copying in operator="]),
                        ("Data conversion", 60, ["Basic to class type", "Class to basic type (conversion operators)"]),
                        ("Pitfalls of operator overloading", 45, ["Loss of natural operator semantics", "Ambiguity in conversions"]),
                        ("Operator overloading and conversion", 60, ["Explicit constructors", "Preventing accidental implicit conversions"])
                    ]
                },
                {
                    "unit_number": 5,
                    "title": "Inheritance",
                    "lecture_allocation": 7,
                    "topics": [
                        ("Concept of inheritance", 45, ["Generalization and specialization", "Code reusability"]),
                        ("Derived classes and base classes", 60, ["Inheritance syntax", "Public, protected, private inheritance modes"]),
                        ("Derived-class constructors", 75, ["Order of constructor/destructor execution", "Calling base class constructor"]),
                        ("Member functions", 60, ["Function overriding vs function overloading in inheritance"]),
                        ("Class hierarchies", 60, ["Multilevel inheritance", "Hierarchical inheritance"]),
                        ("Types of inheritance", 60, ["Single, multiple, multilevel, hierarchical, hybrid inheritance"]),
                        ("Aggregation", 60, ["Has-a relationship", "Composition vs aggregation"]),
                        ("Classes within classes", 60, ["Nested / inner classes", "Scoping and access permissions"])
                    ]
                },
                {
                    "unit_number": 6,
                    "title": "Pointers and Virtual Functions",
                    "lecture_allocation": 7,
                    "topics": [
                        ("The address-of operator", 45, ["& operator", "Pointer declaration and dereferencing *"]),
                        ("Pointers", 60, ["Pointers to structures and classes", "Arrow operator ->"]),
                        ("Dynamic memory management", 75, ["Heap allocation", "Memory leaks and fragmentation"]),
                        ("`new` and `delete`", 60, ["Dynamic single objects and arrays", "delete vs delete[]"]),
                        ("Pointers to objects", 60, ["Base class pointer pointing to derived class object"]),
                        ("Virtual functions", 90, ["Virtual keyword", "VTABLE and VPTR mechanism", "Pure virtual functions and abstract classes"]),
                        ("Assignment and copy initialization", 60, ["Object slicing problem", "Virtual destructors"])
                    ]
                }
            ]
        },
        {
            "code": "CSN 3002",
            "name": "Data Science & Machine Learning",
            "credits": 4,
            "total_lectures": 42,
            "color": "#8b5cf6",
            "priority": "HIGH",
            "exam_date": "2026-12-04",
            "units": [
                {
                    "unit_number": 1,
                    "title": "Introduction to Data Science",
                    "lecture_allocation": 6,
                    "topics": [
                        ("Basics of data science and machine learning", 45, ["Data science workflow", "AI vs ML vs DL distinction"]),
                        ("Types of data", 45, ["Quantitative vs qualitative", "Nominal, ordinal, interval, ratio"]),
                        ("Structured data", 45, ["Tabular data", "Relational databases", "Schema constraints"]),
                        ("Unstructured data", 45, ["Text, audio, images, videos", "Storage and processing challenges"]),
                        ("Other data types", 45, ["Semi-structured data (JSON, XML)", "Streaming and time-series data"]),
                        ("Data science process", 60, ["CRISP-DM methodology", "Problem formulation, data prep, modeling, deployment"]),
                        ("Exploring and visualising data", 60, ["Histograms, scatter plots, box plots", "Summary statistics"]),
                        ("Features", 45, ["Feature matrix representation", "Independent vs dependent variables"]),
                        ("Linear algebra", 75, ["Vectors, matrices, dot products, matrix multiplication, rank, determinants"]),
                        ("Correlation", 60, ["Pearson correlation coefficient", "Spearman rank correlation", "Correlation vs causation"])
                    ]
                },
                {
                    "unit_number": 2,
                    "title": "Data Acquisition and Preprocessing",
                    "lecture_allocation": 7,
                    "topics": [
                        ("Data sources and collection", 45, ["APIs, web scraping, sensors, database queries"]),
                        ("Data storage and management", 45, ["Data warehouses, data lakes, distributed storage basics"]),
                        ("Data preparation", 45, ["Pipeline setup", "Data auditing"]),
                        ("Handling missing data", 60, ["MCAR, MAR, MNAR", "Imputation (mean, median, KNN)", "Dropping rows"]),
                        ("Feature encoding", 60, ["One-hot encoding", "Label encoding", "Target encoding"]),
                        ("Feature scaling", 60, ["Min-Max normalization", "Standardization (Z-score)", "Robust scaling"]),
                        ("Data cleaning", 60, ["Duplicate removal", "Outlier detection (IQR, Z-score)", "Inconsistent data fix"]),
                        ("Dataset division", 45, ["Train-test split methodology", "Data leakage prevention"]),
                        ("Training sets", 45, ["Model fitting data", "Representative sampling"]),
                        ("Test sets", 45, ["Unseen test evaluation", "Final unbiased metric reporting"]),
                        ("Validation sets", 45, ["Hyperparameter tuning set", "Early stopping"])
                    ]
                },
                {
                    "unit_number": 3,
                    "title": "Machine Learning Fundamentals",
                    "lecture_allocation": 7,
                    "topics": [
                        ("Applications of machine learning", 45, ["Recommendation systems, NLP, vision, finance"]),
                        ("Introduction to machine learning techniques", 45, ["Inductive learning", "Parametric vs non-parametric models"]),
                        ("Supervised learning", 60, ["Regression vs classification tasks", "Ground truth labels"]),
                        ("Unsupervised learning", 60, ["Pattern discovery", "Clustering and association rules"]),
                        ("Reinforcement learning", 60, ["Agents, environments, states, actions, rewards", "Policy and value iteration"]),
                        ("Bias-variance trade-off", 75, ["Underfitting vs overfitting balance", "Model complexity curves"]),
                        ("Overfitting and underfitting", 60, ["Symptoms on train vs validation curves", "Regularization strategies"]),
                        ("Evaluation measures", 60, ["Loss functions vs evaluation metrics"]),
                        ("SSE", 45, ["Sum of squared errors", "MSE, RMSE, MAE comparison"]),
                        ("R-squared", 45, ["Coefficient of determination", "Adjusted R-squared interpretation"]),
                        ("Confusion matrix", 60, ["TP, FP, TN, FN matrix construction"]),
                        ("Precision", 45, ["Positive predictive value", "Impact on false positive sensitive tasks"]),
                        ("Recall", 45, ["Sensitivity / true positive rate", "Impact on false negative sensitive tasks"]),
                        ("F-score", 45, ["Harmonic mean of precision and recall", "F1 score vs F-beta"]),
                        ("ROC curve", 60, ["Receiver operating characteristic", "AUC score interpretation"]),
                        ("Cross-validation", 60, ["K-fold cross validation", "Stratified K-fold", "Leave-one-out CV"])
                    ]
                },
                {
                    "unit_number": 4,
                    "title": "Regression and Classification",
                    "lecture_allocation": 12,
                    "topics": [
                        ("Simple linear regression", 75, ["Slope and intercept derivation", "Least squares criterion", "Assumptions"]),
                        ("Multiple linear regression", 90, ["Matrix formulation", "Multicollinearity", "VIF"]),
                        ("Logistic regression", 90, ["Sigmoid function", "Log-odds", "Binary cross-entropy loss", "Decision boundary"]),
                        ("Gradient descent algorithm", 90, ["Batch, Stochastic, and Mini-batch gradient descent", "Learning rate scheduling"]),
                        ("K-nearest neighbours", 75, ["Euclidean/Manhattan distance metrics", "Choosing optimal K", "Curse of dimensionality"]),
                        ("Support Vector Machine", 100, ["Hyperplanes, margins, support vectors", "Hard vs soft margin", "Kernel trick"]),
                        ("Naive Bayes", 75, ["Bayes theorem application", "Conditional independence assumption", "Gaussian and Multinomial NB"]),
                        ("Decision trees", 90, ["Entropy and Information Gain", "Gini impurity", "ID3, C4.5, CART algorithms", "Pruning"])
                    ]
                },
                {
                    "unit_number": 5,
                    "title": "Dimensionality Reduction and Clustering",
                    "lecture_allocation": 10,
                    "topics": [
                        ("Feature selection", 60, ["Filter methods (Chi-square, ANOVA)", "Wrapper methods (RFE)", "Embedded methods (Lasso L1)"]),
                        ("Principal Component Analysis", 100, ["Covariance matrix", "Eigenvalues and eigenvectors", "Explained variance ratio"]),
                        ("K-means clustering", 75, ["Centroid initialization", "Lloyd's algorithm", "Elbow method", "Silhouette score"]),
                        ("Hierarchical clustering", 75, ["Agglomerative vs divisive", "Dendrograms", "Linkage criteria: single, complete, average"]),
                        ("Density-based clustering", 90, ["DBSCAN algorithm", "Epsilon and MinPts parameters", "Core, border, and noise points"])
                    ]
                }
            ]
        }
    ]

    for subj in subjects_data:
        cursor.execute("""
            INSERT INTO subjects (code, name, credits, total_lectures, color, priority, exam_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (subj["code"], subj["name"], subj["credits"], subj["total_lectures"], subj["color"], subj["priority"], subj["exam_date"]))
        subject_id = cursor.lastrowid

        for u in subj["units"]:
            cursor.execute("""
                INSERT INTO units (subject_id, unit_number, title, lecture_allocation)
                VALUES (?, ?, ?, ?)
            """, (subject_id, u["unit_number"], u["title"], u["lecture_allocation"]))
            unit_id = cursor.lastrowid

            for idx, topic_info in enumerate(u["topics"]):
                title, mins, subtopics = topic_info
                cursor.execute("""
                    INSERT INTO topics (unit_id, subject_id, title, estimated_minutes, base_minutes, order_index)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (unit_id, subject_id, title, mins, mins, idx))
                topic_id = cursor.lastrowid

                for s_idx, st in enumerate(subtopics):
                    cursor.execute("""
                        INSERT INTO subtopics (topic_id, title, order_index)
                        VALUES (?, ?, ?)
                    """, (topic_id, st, s_idx))

    # Add realistic prerequisites
    cursor.execute("SELECT id, title FROM topics")
    topic_map = {row["title"]: row["id"] for row in cursor.fetchall()}

    prereqs = [
        # Discrete
        ("Truth tables", "Propositions"),
        ("Quantifiers", "Predicates"),
        ("Rules of inference", "Truth tables"),
        ("Methods of proofs", "Rules of inference"),
        ("Equivalence relations and partitions", "Properties of relations"),
        ("POSETs", "Partial orderings"),
        ("Inversions", "Injection"),
        ("Inversions", "Surjections"),
        ("Solving linear recurrence relations", "Recurrence relations"),
        ("Spanning trees", "Trees"),
        ("Probability theory", "Introduction to probability"),
        ("Bayes' theorem", "Probability theory"),
        ("Expected value and variance", "Discrete random variables"),

        # Data Structures
        ("Doubly linked lists", "Introduction to linked lists"),
        ("Balanced brackets", "Introduction to stacks"),
        ("Infix to postfix conversion", "Introduction to stacks"),
        ("Job scheduling in CPU", "Queue implementation using arrays"),
        ("Traversals in binary trees", "Binary trees"),
        ("BFS in binary trees", "Binary trees"),
        ("DFS in binary trees", "Binary trees"),
        ("Insertion in BST", "Binary search trees"),
        ("Deletion in BST", "Insertion in BST"),
        ("AVL trees", "Binary search trees"),
        ("B-trees", "Binary search trees"),
        ("Graph traversal", "Graph implementation"),
        ("Dijkstra's algorithm for single-source shortest paths", "Graph traversal"),
        ("Prim's algorithm", "Spanning trees"),
        ("Kruskal's algorithm", "Union-find data structure"),
        ("Priority queues using heaps", "Heaps"),

        # OOP
        ("Classes and instances", "Defining classes"),
        ("Copy constructors", "Constructors for initialization"),
        ("Static functions", "Defining classes"),
        ("Friend functions", "Defining classes"),
        ("Overloading binary operators", "Overloading unary operators"),
        ("Overloading the assignment operator", "Copy constructors"),
        ("Derived classes and base classes", "Defining classes"),
        ("Derived-class constructors", "Derived classes and base classes"),
        ("Types of inheritance", "Derived classes and base classes"),
        ("Virtual functions", "Pointers to objects"),
        ("Virtual functions", "Derived classes and base classes"),

        # DS & ML
        ("Exploring and visualising data", "Basics of data science and machine learning"),
        ("Handling missing data", "Data sources and collection"),
        ("Feature encoding", "Types of data"),
        ("Feature scaling", "Data cleaning"),
        ("Bias-variance trade-off", "Supervised learning"),
        ("Overfitting and underfitting", "Bias-variance trade-off"),
        ("Precision", "Confusion matrix"),
        ("Recall", "Confusion matrix"),
        ("F-score", "Precision"),
        ("ROC curve", "Evaluation measures"),
        ("Cross-validation", "Dataset division"),
        ("Multiple linear regression", "Simple linear regression"),
        ("Gradient descent algorithm", "Simple linear regression"),
        ("Logistic regression", "Gradient descent algorithm"),
        ("Principal Component Analysis", "Linear algebra"),
        ("Hierarchical clustering", "K-means clustering"),
        ("Density-based clustering", "K-means clustering")
    ]

    for topic_title, prereq_title in prereqs:
        if topic_title in topic_map and prereq_title in topic_map:
            cursor.execute("""
                INSERT OR IGNORE INTO prerequisites (topic_id, prerequisite_topic_id)
                VALUES (?, ?)
            """, (topic_map[topic_title], topic_map[prereq_title]))

    conn.commit()

def seed_dsa_questions_if_empty(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM dsa_questions")
    if cursor.fetchone()["count"] > 0:
        return

    questions = [
        (
            "Reverse a Singly Linked List",
            "Linked Lists",
            "Easy",
            "Given the head of a singly linked list, reverse the list in-place and return its new head.",
            "Pointer manipulation, iterative 3-pointer technique (prev, curr, next) and recursive call stack.",
            json.dumps([
                "Initialize three pointers: prev = NULL, curr = head, next = NULL.",
                "In each iteration, save curr->next before modifying it.",
                "Point curr->next backwards to prev, then advance prev and curr."
            ]),
            "Time Complexity: O(N) where N is number of nodes.\nSpace Complexity: O(1) iterative in-place.\n\nIterative Solution in C++:\n```cpp\nListNode* reverseList(ListNode* head) {\n    ListNode *prev = nullptr, *curr = head;\n    while (curr != nullptr) {\n        ListNode* nextTemp = curr->next;\n        curr->next = prev;\n        prev = curr;\n        curr = nextTemp;\n    }\n    return prev;\n}\n```"
        ),
        (
            "Detect and Remove Loop in Linked List (Floyd's Cycle)",
            "Linked Lists",
            "Medium",
            "Given a linked list, detect whether a cycle exists. If a cycle exists, find the starting node of the loop and break the cycle.",
            "Fast and slow pointers (tortoise and hare algorithm), modular arithmetic on linked nodes.",
            json.dumps([
                "Advance slow by 1 step and fast by 2 steps. If they meet, a cycle exists.",
                "Reset one pointer to head while keeping the other at the meeting point.",
                "Advance both by 1 step until they meet; that meeting point is the loop start."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(1).\n\n```cpp\nListNode* detectCycle(ListNode* head) {\n    ListNode *slow = head, *fast = head;\n    while (fast && fast->next) {\n        slow = slow->next;\n        fast = fast->next->next;\n        if (slow == fast) {\n            ListNode* entry = head;\n            while (entry != slow) {\n                entry = entry->next;\n                slow = slow->next;\n            }\n            return entry; // loop start\n        }\n    }\n    return nullptr;\n}\n```"
        ),
        (
            "Valid Parentheses Matching",
            "Stacks",
            "Easy",
            "Given a string containing just '(', ')', '{', '}', '[' and ']', determine if the input string is valid by balanced bracket ordering.",
            "LIFO stack principle, matching opening and closing delimiter pairs.",
            json.dumps([
                "Push opening brackets onto stack.",
                "When encountering a closing bracket, check if stack is non-empty and top matches.",
                "At the end of string, stack must be empty."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(N).\n\n```cpp\nbool isValid(string s) {\n    stack<char> st;\n    for (char c : s) {\n        if (c == '(' || c == '{' || c == '[') st.push(c);\n        else {\n            if (st.empty()) return false;\n            char top = st.top(); st.pop();\n            if ((c == ')' && top != '(') || (c == '}' && top != '{') || (c == ']' && top != '[')) return false;\n        }\n    }\n    return st.empty();\n}\n```"
        ),
        (
            "Evaluate Reverse Polish Notation (Postfix Expression)",
            "Stacks",
            "Medium",
            "Evaluate the value of an arithmetic expression in Reverse Polish Notation. Valid operators are +, -, *, /.",
            "Operand stack, operator precedence elimination in postfix.",
            json.dumps([
                "Iterate through tokens. If token is number, push to stack.",
                "If operator, pop two operands: right operand first, left operand second.",
                "Apply operator, push result back to stack."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(N).\n\n```cpp\nint evalRPN(vector<string>& tokens) {\n    stack<int> st;\n    for (const string& t : tokens) {\n        if (t == \"+\" || t == \"-\" || t == \"*\" || t == \"/\") {\n            int b = st.top(); st.pop();\n            int a = st.top(); st.pop();\n            if (t == \"+\") st.push(a + b);\n            else if (t == \"-\") st.push(a - b);\n            else if (t == \"*\") st.push(a * b);\n            else if (t == \"/\") st.push(a / b);\n        } else {\n            st.push(stoi(t));\n        }\n    }\n    return st.top();\n}\n```"
        ),
        (
            "Implement Circular Queue with Dynamic Array",
            "Queues",
            "Medium",
            "Design a circular queue data structure supporting enQueue, deQueue, Front, Rear, isEmpty, and isFull without wasting buffer space.",
            "Modulo arithmetic `(rear + 1) % capacity`, ring buffer mechanics.",
            json.dumps([
                "Use front and rear pointers initialized to -1.",
                "When enqueueing: rear = (rear + 1) % size.",
                "When dequeueing: front = (front + 1) % size."
            ]),
            "Time Complexity: O(1) for all operations.\nSpace Complexity: O(K) where K is capacity.\n\nAll operations utilize (index + 1) % capacity to wrap around seamlessly."
        ),
        (
            "Binary Tree Level Order Traversal (BFS)",
            "Trees",
            "Medium",
            "Given the root of a binary tree, return the level order traversal of its nodes' values (from left to right, level by level).",
            "Breadth First Search using a FIFO queue.",
            json.dumps([
                "Push root to queue if not null.",
                "At each level, record `int levelSize = q.size()`.",
                "Pop exactly `levelSize` elements, collect values, and push their children."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(W) where W is max tree width.\n\n```cpp\nvector<vector<int>> levelOrder(TreeNode* root) {\n    vector<vector<int>> res;\n    if (!root) return res;\n    queue<TreeNode*> q;\n    q.push(root);\n    while (!q.empty()) {\n        int sz = q.size();\n        vector<int> level;\n        for (int i = 0; i < sz; i++) {\n            TreeNode* node = q.front(); q.pop();\n            level.push_back(node->val);\n            if (node->left) q.push(node->left);\n            if (node->right) q.push(node->right);\n        }\n        res.push_back(level);\n    }\n    return res;\n}\n```"
        ),
        (
            "Validate Binary Search Tree",
            "Binary Search Trees",
            "Medium",
            "Given the root of a binary tree, determine if it is a valid binary search tree (BST). Left subtree strictly less, right strictly greater.",
            "BST invariant property, range propagation (minVal, maxVal) or in-order sorted check.",
            json.dumps([
                "A node's value must be strictly within (minLimit, maxLimit).",
                "When going left, update maxLimit = node->val.",
                "When going right, update minLimit = node->val."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(H) call stack height.\n\n```cpp\nbool validate(TreeNode* node, long minVal, long maxVal) {\n    if (!node) return true;\n    if (node->val <= minVal || node->val >= maxVal) return false;\n    return validate(node->left, minVal, node->val) && validate(node->right, node->val, maxVal);\n}\n```"
        ),
        (
            "Lowest Common Ancestor in a Binary Search Tree",
            "Binary Search Trees",
            "Easy",
            "Given a binary search tree (BST), find the lowest common ancestor (LCA) node of two given nodes p and q.",
            "BST ordering property: split point where p and q diverge.",
            json.dumps([
                "If both p and q values are less than root, LCA lies in left subtree.",
                "If both p and q values are greater than root, LCA lies in right subtree.",
                "Otherwise, root is the split point and the LCA."
            ]),
            "Time Complexity: O(H) where H is tree height.\nSpace Complexity: O(1) iterative.\n\n```cpp\nTreeNode* lowestCommonAncestor(TreeNode* root, TreeNode* p, TreeNode* q) {\n    while (root) {\n        if (p->val < root->val && q->val < root->val) root = root->left;\n        else if (p->val > root->val && q->val > root->val) root = root->right;\n        else return root;\n    }\n    return nullptr;\n}\n```"
        ),
        (
            "Find Minimum in Rotated Sorted Array",
            "Review",
            "Medium",
            "Suppose an array of length n sorted in ascending order is rotated between 1 and n times. Find the minimum element in O(log n) time.",
            "Binary search on modified sorted partitions.",
            json.dumps([
                "Compare nums[mid] with nums[right].",
                "If nums[mid] > nums[right], minimum lies in right half: left = mid + 1.",
                "Otherwise minimum lies in left half including mid: right = mid."
            ]),
            "Time Complexity: O(log N).\nSpace Complexity: O(1).\n\n```cpp\nint findMin(vector<int>& nums) {\n    int left = 0, right = nums.size() - 1;\n    while (left < right) {\n        int mid = left + (right - left) / 2;\n        if (nums[mid] > nums[right]) left = mid + 1;\n        else right = mid;\n    }\n    return nums[left];\n}\n```"
        ),
        (
            "Implement Min Heap / Priority Queue",
            "Advanced Data Structures",
            "Medium",
            "Implement a binary Min-Heap supporting insert, extractMin, and heapify in O(log N) time using a standard 0-indexed vector.",
            "Complete binary tree array mapping: parent = (i-1)/2, left = 2i+1, right = 2i+2.",
            json.dumps([
                "Insert adds element at end and sifts up (bubble up) while smaller than parent.",
                "ExtractMin swaps root with last element, pops back, and sifts down (bubble down)."
            ]),
            "Time Complexity: Insert O(log N), ExtractMin O(log N), GetMin O(1).\nSpace: O(N)."
        ),
        (
            "Dijkstra's Shortest Path Algorithm",
            "Graphs",
            "Hard",
            "Given a weighted graph with non-negative edge weights and a source vertex, find the shortest path distances from source to all other vertices.",
            "Greedy vertex relaxation with min-priority queue (distance, vertex).",
            json.dumps([
                "Maintain dist[] array initialized to infinity, with dist[src] = 0.",
                "Use min-heap priority_queue<pair<int,int>, vector<pair<int,int>>, greater<>>.",
                "Relax edge (u, v, weight): if dist[u] + weight < dist[v], update dist[v] and push."
            ]),
            "Time Complexity: O((V + E) log V).\nSpace Complexity: O(V + E).\n\n```cpp\nvector<int> dijkstra(int V, vector<vector<pair<int,int>>>& adj, int S) {\n    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>> pq;\n    vector<int> dist(V, 1e9);\n    dist[S] = 0;\n    pq.push({0, S});\n    while (!pq.empty()) {\n        auto [d, u] = pq.top(); pq.pop();\n        if (d > dist[u]) continue;\n        for (auto& edge : adj[u]) {\n            int v = edge.first, w = edge.second;\n            if (dist[u] + w < dist[v]) {\n                dist[v] = dist[u] + w;\n                pq.push({dist[v], v});\n            }\n        }\n    }\n    return dist;\n}\n```"
        ),
        (
            "Connected Components in Undirected Graph (BFS/DFS)",
            "Graphs",
            "Easy",
            "Given n vertices and a list of undirected edges, find the total number of connected components in the graph.",
            "Graph traversal using visited boolean array.",
            json.dumps([
                "Build adjacency list.",
                "Iterate i from 0 to n-1. If vertex i is unvisited, launch BFS/DFS and increment component count."
            ]),
            "Time Complexity: O(V + E).\nSpace Complexity: O(V + E)."
        ),
        (
            "Longest Consecutive Sequence",
            "Advanced Data Structures",
            "Medium",
            "Given an unsorted array of integers, find the length of the longest consecutive elements sequence in O(N) time.",
            "Hash Set O(1) lookups, identifying sequence start points.",
            json.dumps([
                "Insert all elements into unordered_set.",
                "Only start counting sequence from `x` if `x - 1` does NOT exist in set.",
                "Count x+1, x+2... while present in set."
            ]),
            "Time Complexity: O(N).\nSpace Complexity: O(N).\n\n```cpp\nint longestConsecutive(vector<int>& nums) {\n    unordered_set<int> s(nums.begin(), nums.end());\n    int maxLen = 0;\n    for (int num : s) {\n        if (!s.count(num - 1)) {\n            int curr = num, len = 1;\n            while (s.count(curr + 1)) { curr++; len++; }\n            maxLen = max(maxLen, len);\n        }\n    }\n    return maxLen;\n}\n```"
        ),
        (
            "Kth Largest Element in an Array",
            "Advanced Data Structures",
            "Medium",
            "Given an integer array nums and an integer k, return the kth largest element in the array without full sorting.",
            "Min-heap of fixed size K or Quickselect algorithm.",
            json.dumps([
                "Maintain a min-heap of size k.",
                "Push each element. If heap size exceeds k, pop the smallest element.",
                "After traversing array, heap top contains the kth largest element."
            ]),
            "Time Complexity: O(N log K).\nSpace Complexity: O(K).\n\n```cpp\nint findKthLargest(vector<int>& nums, int k) {\n    priority_queue<int, vector<int>, greater<int>> minHeap;\n    for (int num : nums) {\n        minHeap.push(num);\n        if (minHeap.size() > k) minHeap.pop();\n    }\n    return minHeap.top();\n}\n```"
        ),
        (
            "Course Schedule (Cycle Detection in Directed Graph)",
            "Graphs",
            "Medium",
            "There are a total of numCourses courses with prerequisites [a, b]. Return true if you can finish all courses without cyclical dependencies.",
            "Topological sort (Kahn's algorithm using in-degree array) or DFS coloring.",
            json.dumps([
                "Compute in-degree for every vertex.",
                "Enqueue all vertices with in-degree == 0.",
                "Pop vertex, decrement in-degree of its neighbors. If neighbor hits 0, enqueue it.",
                "If total popped vertices == numCourses, valid topological order exists."
            ]),
            "Time Complexity: O(V + E).\nSpace Complexity: O(V + E)."
        )
    ]

    for q in questions:
        hints_list = []
        try:
            hints_list = json.loads(q[5])
        except Exception:
            hints_list = []
        h1 = hints_list[0] if len(hints_list) > 0 else None
        h2 = hints_list[1] if len(hints_list) > 1 else None
        
        cursor.execute("""
            INSERT INTO dsa_questions (title, topic, difficulty, description, problem_statement, concept, hints_json, hint_1, hint_2, solution, solution_approach, solution_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (q[0], q[1], q[2], q[3], q[3], q[4], q[5], h1, h2, q[6], q[6], q[6]))
    conn.commit()

def seed_english_topics_if_empty(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM english_speaking_topics")
    if cursor.fetchone()["count"] > 0:
        return

    topics = [
        (
            "Technical Concept Explanation: How Hash Tables Handle Collisions",
            "Technical Concept",
            "Explain hash collisions, separate chaining, and open addressing in clear, structured English for 5-10 minutes.",
            json.dumps(["deterministic", "collision resolution", "chaining", "probe sequence", "load factor"]),
            json.dumps(["To begin with, a hash function maps keys to...", "The primary trade-off between chaining and open addressing is...", "In worst-case scenarios, performance degrades to..."]),
            json.dumps(["What happens when two distinct keys yield the same index?", "How would you explain the load factor to an interviewer?", "Which collision strategy is preferred in memory-constrained environments?"])
        ),
        (
            "Professional Self-Introduction for Engineering Interviews",
            "Self Introduction",
            "Deliver an articulate 2-3 minute elevator pitch covering your technical background, projects, and academic focus.",
            json.dumps(["specializing in", "proficient in", "hands-on experience", "enthusiastic about", "academic milestones"]),
            json.dumps(["Hello, my name is Aman. I am currently pursuing...", "Over the past semester, my core focus has been...", "What drives my interest in computer science is..."]),
            json.dumps(["How do your technical coursework and projects align with your goals?", "What is one technical challenge you recently overcame?"])
        ),
        (
            "Describing an Engineering Project and Problem Solved",
            "Project Discussion",
            "Explain an end-to-end software project: the problem statement, architectural choices, and technical hurdles.",
            json.dumps(["architecture", "modular design", "bottleneck", "optimization", "scalability"]),
            json.dumps(["The application was designed to solve...", "One significant bottleneck we encountered was...", "To mitigate this, we restructured the database schema..."]),
            json.dumps(["What made you select this specific technology stack?", "How did you measure the performance improvement?"])
        ),
        (
            "Expressing Opinions on AI in Software Development",
            "Opinions & Arguments",
            "Articulate balanced perspectives on how AI coding assistants affect foundational learning and developer productivity.",
            json.dumps(["augmentation", "syntactic sugar", "algorithmic thinking", "dependency", "paradigm shift"]),
            json.dumps(["From my vantage point...", "While AI accelerates boilerplate generation, it cannot substitute for...", "On the other hand, engineers must remain cautious of..."]),
            json.dumps(["Does AI reduce the need to master fundamental data structures?", "How should universities adapt examination formats?"])
        ),
        (
            "Explaining the Trade-off Between Time and Space Complexity",
            "Technical Concept",
            "Deliver an engaging monologue comparing time efficiency vs memory footprint with real-world examples.",
            json.dumps(["amortized", "memory footprint", "caching", "lookup latency", "in-place algorithm"]),
            json.dumps(["In computer science, optimal design is fundamentally about trade-offs...", "For instance, dynamic programming memoizes state to reduce...", "Conversely, in-place sorting minimizes memory at the expense of..."]),
            json.dumps(["Can you give an example where saving memory is more crucial than saving CPU cycles?"])
        ),
        (
            "Group Discussion: Building Consistency vs Burst Studying",
            "Group Discussion",
            "Practice persuasive argument structures supporting daily disciplined study over cramming before exams.",
            json.dumps(["spaced repetition", "cognitive load", "neuroplasticity", "burnout", "incremental mastery"]),
            json.dumps(["I would like to add to this point...", "Evidence clearly demonstrates that cramming results in rapid forgetting...", "Consistent daily allocation builds long-term retention..."]),
            json.dumps(["Why do students procrastinate even when aware of the risks?", "How does a daily study schedule prevent exam anxiety?"])
        ),
        (
            "Interview Question: Tell Me About a Time You Failed or Got Stuck",
            "Interview Questions",
            "Structure an authentic response using the STAR (Situation, Task, Action, Result) methodology in English.",
            json.dumps(["roadblock", "retrospective", "countermeasure", "resilience", "lessons learned"]),
            json.dumps(["A notable instance occurred when...", "The task required delivering...", "My action was to step back, profile the error logs, and...", "Ultimately, the result taught me that..."]),
            json.dumps(["What would you do differently if faced with the same roadblock today?"])
        ),
        (
            "Summarizing Today's Academic Learning in 5 Minutes",
            "Daily Reflection",
            "Summarize the key mathematical proof or data structure concept you studied today without looking at notes.",
            json.dumps(["fundamental theorem", "underlying principle", "edge case", "verification", "takeaway"]),
            json.dumps(["Today's core topic centered on...", "The most non-intuitive aspect was...", "By the end of the session, I was able to implement..."]),
            json.dumps(["What was the hardest problem you tackled today?", "How does today's concept connect to previous units?"])
        )
    ]

    for t in topics:
        cursor.execute("""
            INSERT INTO english_speaking_topics (title, category, objective, vocabulary_json, starter_phrases_json, prompt_questions_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, t)
    conn.commit()

def seed_quotes_if_empty(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM daily_quotes")
    if cursor.fetchone()["count"] > 0:
        return

    quotes = [
        ("Discipline is the bridge between goals and accomplishment.", "Consistency & Discipline", "Jim Rohn"),
        ("Honour your father and your mother: the blessing of parents is the silent foundation of every great victory.", "Parents & Gratitude", "Traditional Wisdom"),
        ("Trust in the Almighty with all your heart, and lean not on your own understanding. In all your ways acknowledge Him, and He shall direct your paths.", "Faith in God", "Spiritual Heritage"),
        ("Success is not final, failure is not fatal: it is the courage to continue that counts.", "Success & Perseverance", "Winston Churchill"),
        ("Verily, with hardship comes ease. Patience through the struggle is itself a quiet victory.", "Patience & Hope", "Timeless Reflection"),
        ("Small disciplines repeated with consistency every day lead to great achievements gained slowly over time.", "Consistency & Discipline", "John C. Maxwell"),
        ("Live as if you were to die tomorrow. Learn as if you were to live forever.", "Study & Learning", "Mahatma Gandhi"),
        ("Remember the sacrifices of those who believed in you when you had nothing to show. Work so hard that their sacrifices bear fruit.", "Parents & Gratitude", "Reflection"),
        ("When you plant seeds in the ground, you do not dig them up every day to see if they have grown. Have faith in your daily labor and trust the harvest.", "Patience & Hope", "Ancient Proverb"),
        ("An investment in knowledge pays the best interest.", "Study & Learning", "Benjamin Franklin"),
        ("The secret of your future is hidden in your daily routine.", "Consistency & Discipline", "Mike Murdock"),
        ("Do not pray for an easy life; pray for the strength to endure a difficult one and emerge with wisdom.", "Faith in God", "Spiritual Heritage"),
        ("He who moves a mountain begins by carrying away small stones.", "Success & Perseverance", "Confucius"),
        ("No legacy is so rich as honesty, humility, and gratitude toward your family.", "Parents & Gratitude", "Traditional Wisdom"),
        ("Difficulties in life do not come to destroy you, but to help you realize your hidden potential and power.", "Patience & Hope", "A.P.J. Abdul Kalam")
    ]

    for idx, q in enumerate(quotes):
        cursor.execute("""
            INSERT INTO daily_quotes (quote, quote_text, category, author, day_offset)
            VALUES (?, ?, ?, ?, ?)
        """, (q[0], q[0], q[1], q[2], idx))
    conn.commit()
