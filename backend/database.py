import sqlite3
import json
import os
from datetime import datetime, date
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "studypilot.db")

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
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
        color TEXT NOT NULL DEFAULT '#3b82f6',
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
    """)

    conn.commit()
    seed_initial_data_if_empty(conn)
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
    if cursor.fetchone()["count"] > 0:
        return

    # Default Settings
    default_settings = {
        "first_exam_date": "2026-11-26",
        "syllabus_deadline": "2026-11-19",
        "revision_buffer_days": 7,
        "is_buffer_mandatory": True,
        "weekday_minutes": 180,  # 3 hours/day
        "weekend_minutes": 300,  # 5 hours/day
        "college_hours": "09:00 - 16:00",
        "commute_minutes": 60,
        "sleep_hours": "23:30 - 06:30",
        "study_windows": [
            {"name": "Morning Slot", "start": "06:45", "end": "08:15", "minutes": 90, "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"name": "Evening Slot", "start": "18:00", "end": "19:30", "minutes": 90, "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"name": "Night Slot", "start": "20:30", "end": "22:00", "minutes": 90, "days": ["mon", "tue", "wed", "thu", "fri"]},
            {"name": "Weekend Morning", "start": "08:00", "end": "11:00", "minutes": 180, "days": ["sat", "sun"]},
            {"name": "Weekend Evening", "start": "16:00", "end": "18:00", "minutes": 120, "days": ["sat", "sun"]}
        ],
        "blocked_dates": [],
        "session_duration": 60,
        "max_consecutive_minutes": 90,
        "break_duration": 15,
        "subjects_per_day": 2,
        "study_style": "INTERLEAVED", # INTERLEAVED or DEEP_DIVE
        "daily_practice": True,
        "spaced_revision": True,
        "onboarding_completed": False,
        "theme": "dark",
        "time_zone": "Asia/Kolkata"
    }

    for k, v in default_settings.items():
        val_str = json.dumps(v) if not isinstance(v, str) else v
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, val_str))

    # Initial Subjects Data
    subjects_data = [
        {
            "code": "CSN 3003",
            "name": "Discrete Structures for Computer Science",
            "credits": 4,
            "total_lectures": 42,
            "color": "#6366f1", # Indigo
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
            "color": "#10b981", # Emerald
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
            "color": "#f59e0b", # Amber
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
            "color": "#8b5cf6", # Purple
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
    # Find topic ids helper
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
