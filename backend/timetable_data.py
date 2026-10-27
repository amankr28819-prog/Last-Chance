"""
Official Study Timetable Definition & Importer
Date range: 27 October 2026 to 20 November 2026 (25 days)
Extracted directly from the official Word study timetable.
Each day contains 5 x 45-minute academic study shifts (225m) + 1 x 15-minute wrap-up (15m) = 240m (4h academic target).
DSA practice (2 questions) and English speaking (30m) are tracked separately outside the 4h academic target.
"""

import sqlite3
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional

COURSE_MAP = {
    "Discrete Structures": "CSN 3003",
    "Data Structures": "CSN 3001",
    "OOP": "CSN 3004",
    "DSML": "CSN 3002",
    "All four": "ALL"
}

TIMETABLE_DAYS = [
    {
        "date": "2026-10-27",
        "day_label": "Tue 27 Oct",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Unit 2 — Set Theory: review set definitions and examples; identify exactly which topics remain."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Unit 2 — Inductive definition / proof by induction: understand method and solve examples."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 2, "task": "Unit 2 — Linked lists: insertion, deletion, search; trace operations on paper."},
            {"shift": 4, "course": "OOP", "code": "CSN 3004", "unit": 1, "task": "Post-quiz reset: list weak topics from Units 1–6; revise one weak topic."},
            {"shift": 5, "course": "DSML", "code": "CSN 3002", "unit": 1, "task": "Unit 1 — Data science basics, types of data, and data science process."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one linked-list question + one recursion/array question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-10-28",
        "day_label": "Wed 28 Oct",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Unit 2 — Peano postulates and relations; make concise notes."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Unit 2 — Equivalence relations and partitions; practise examples."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 2, "task": "Unit 2 — Doubly linked list and circular linked list; compare operations."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 1, "task": "Unit 1 — Explore/visualize data, features, linear algebra, correlation."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 3, "task": "Unit 3 — Constructors, initialization lists, destructors; trace output."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one linked-list question + one stack question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-10-29",
        "day_label": "Thu 29 Oct",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Unit 2 — Partial orders and POSETs; draw Hasse diagrams if covered in class notes."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Unit 2 — Mixed problems and proof practice; make an error list."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 3, "task": "Unit 3 — Stack implementation using arrays and linked lists."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 2, "task": "Unit 2 — Data sources, collection, storage, and management."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 3, "task": "Unit 3 — Copy constructors, friend functions, static functions, this pointer."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one stack question + one linked-list question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-10-30",
        "day_label": "Fri 30 Oct",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Unit 2 — Finish remaining listed topics; self-test without notes."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Unit 1 gap check — propositions, connectives, truth tables, predicates, quantifiers."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 3, "task": "Unit 3 — Balanced brackets and stack applications."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 2, "task": "Unit 2 — Missing data, feature encoding, feature scaling."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 4, "task": "Unit 4 — Unary/binary operator overloading basics."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one stack question + one array question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-10-31",
        "day_label": "Sat 31 Oct",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 3, "task": "Unit 3 — Functions, mappings, injection, surjection, composition."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 3, "task": "Unit 3 — Inverse functions, special functions, recursive function theory."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 3, "task": "Unit 3 — Infix-to-postfix conversion; practise conversions."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 2, "task": "Unit 2 — Data cleaning, train/test split, validation sets."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 4, "task": "Unit 4 — Assignment operator overloading, conversion, pitfalls."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one stack question + one recursion question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-01",
        "day_label": "Sun 1 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 3, "task": "Unit 3 — Mixed function problems; identify injective/surjective/bijective."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Unit 4 — Elementary combinatorics and pigeonhole principle."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 4, "task": "Unit 4 — Queue basics and array/linked-list implementations."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 3, "task": "Unit 3 — ML applications, supervised/unsupervised/reinforcement learning."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 5, "task": "Unit 5 — Inheritance basics, base/derived classes, constructors."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one queue question + one tree/recursion question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-02",
        "day_label": "Mon 2 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Unit 4 — Permutations and combinations; solve counting problems."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Unit 4 — Counting techniques and recurrence relations introduction."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 4, "task": "Unit 4 — Queue applications and job scheduling."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 3, "task": "Unit 3 — Bias–variance, overfitting/underfitting, evaluation overview."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 5, "task": "Unit 5 — Types of inheritance, constructor order, class hierarchies."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one queue question + one linked-list question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-03",
        "day_label": "Tue 3 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Unit 4 — Solve linear recurrence relations using the methods in your notes."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Unit 4 — Generating functions; examples and formula sheet."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 5, "task": "Unit 5 — Trees terminology, representations, binary tree traversals."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 3, "task": "Unit 3 — MSE/SSE, R², confusion matrix, precision, recall, F-score, ROC/curve."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 5, "task": "Unit 5 — Aggregation / classes within classes; compare with inheritance."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one tree traversal question + one queue question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-04",
        "day_label": "Wed 4 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Unit 4 — Mixed combinatorics and recurrence practice; correct mistakes."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 5, "task": "Unit 5 — Graph theory basics, graph terminology and isomorphism."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 5, "task": "Unit 5 — BFS and DFS in binary trees; trace traversals."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 4, "task": "Unit 4 — Simple and multiple linear regression concepts."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 6, "task": "Unit 6 — Pointers, address-of operator, dynamic memory, new/delete."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one tree question + one graph/array question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-05",
        "day_label": "Thu 5 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 5, "task": "Unit 5 — Euler graphs, Hamiltonian paths/trees; practise definitions/examples."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 5, "task": "Unit 5 — Trees and spanning trees; solve graph questions."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 6, "task": "Unit 6 — BST insertion, search, deletion."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 4, "task": "Unit 4 — Gradient descent and regression practice."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 6, "task": "Unit 6 — Pointers to objects, virtual functions; trace code outputs."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one BST question + one tree traversal question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-06",
        "day_label": "Fri 6 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 5, "task": "Unit 5 — Graph representation and graph traversals; practise problems."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 5, "task": "Unit 5 — Minimum spanning trees: Prim’s and Kruskal’s algorithms."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 6, "task": "Unit 6 — AVL tree and B-tree concepts/operations."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 4, "task": "Unit 4 — Logistic regression and K-nearest neighbors."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 6, "task": "Unit 6 — Assignment/copy initialization and copy constructor distinctions."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one BST question + one stack/queue question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-07",
        "day_label": "Sat 7 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 5, "task": "Unit 5 — Union-Find / disjoint-set data structure; revise graph algorithms."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 6, "task": "Unit 6 — Probability introduction, random variables, expected value and variance."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 7, "task": "Unit 7 — Graph representations and traversals; connect with Discrete graph theory."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 4, "task": "Unit 4 — SVM, Naïve Bayes, decision trees: compare core ideas."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 1, "task": "Units 1–3 — Review abstraction, encapsulation, classes, objects, constructors."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one graph question + one BST question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-08",
        "day_label": "Sun 8 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 6, "task": "Unit 6 — Conditional probability / Bayes’ theorem as listed; work through class examples."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 5, "task": "Unit 5 — Mixed graph theory problems and algorithm traces."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 7, "task": "Unit 7 — Dijkstra’s single-source shortest path; trace a small graph."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 5, "task": "Unit 5 — Feature selection and PCA."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 4, "task": "Units 4–6 — Review operator overloading, inheritance, pointers, virtual functions."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one graph question + one tree question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-09",
        "day_label": "Mon 9 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 6, "task": "Unit 6 — Discrete random variables, expectation and variance; practise."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Unit 1 — Mathematical reasoning, inference rules, proof methods and Prolog application listed in syllabus."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 7, "task": "Unit 7 — Prim’s and Kruskal’s MST algorithms; compare outputs."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 5, "task": "Unit 5 — K-means clustering."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 5, "task": "Unit 5 — Inheritance and aggregation: code/output practice."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one graph question + one heap/stack question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-10",
        "day_label": "Tue 10 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Unit 2 — Full revision: induction, relations, equivalence, partitions, POSETs."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 3, "task": "Unit 3 — Full revision: functions, mappings, composition, inverse, recursion."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 8, "task": "Unit 8 — Heaps and priority queue implementation."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 5, "task": "Unit 5 — Hierarchical clustering and density-based clustering."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 6, "task": "Unit 6 — Virtual functions and pointer-based output questions."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one heap question + one graph question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-11",
        "day_label": "Wed 11 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Unit 4 — Full revision: combinatorics, pigeonhole, permutations/combinations, recurrences, generating functions."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 5, "task": "Unit 5 — Full revision: Euler/Hamiltonian, trees, spanning trees, MST, Union-Find."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 8, "task": "Unit 8 — Hashing and indexing; notes plus examples."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 1, "task": "Units 1–2 — Revision and practice on preprocessing/data preparation."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 1, "task": "Units 1–3 — Practise code tracing and definitions."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one hashing/heap question + one graph question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-12",
        "day_label": "Thu 12 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Unit 1 — Truth tables, equivalences, predicates, quantifiers and inference rules."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 6, "task": "Unit 6 — Probability revision and mixed questions."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 1, "task": "Units 1–2 — Complexity, recurrence relations, linked lists."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 3, "task": "Unit 3 — Evaluation metrics and cross-validation; solve small metric examples."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 4, "task": "Units 4–6 — Code tracing: overloading, inheritance, pointers and virtual functions."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one linked-list question + one stack/queue question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-13",
        "day_label": "Fri 13 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Mixed revision test: Units 1–3; attempt closed-book questions."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Review mistakes from Units 1–3 and revise weakest two topics."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 3, "task": "Units 3–4 — Stacks, infix/postfix, queues and applications."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 4, "task": "Unit 4 — Regression/classification algorithms comparison and practice."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 5, "task": "Unit 5 — Inheritance, constructor order, aggregation, access behavior."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one stack question + one linked-list/tree question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-14",
        "day_label": "Sat 14 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Mixed revision test: Units 4–6; focus on counting, graphs and probability."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Review mistakes from Units 4–6; redo incorrect problems."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 5, "task": "Units 5–6 — Trees, traversals, BST, AVL and B-tree."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 5, "task": "Unit 5 — PCA and clustering; compare methods and assumptions."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 6, "task": "Unit 6 — Pointer/virtual function/copy initialization output practice."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one tree question + one graph question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-15",
        "day_label": "Sun 15 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Timed practice: mixed problems from all six units."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Proof practice: induction, relations, functions and graph arguments."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 7, "task": "Unit 7 — Dijkstra, Prim, Kruskal and Union-Find; algorithm traces."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 1, "task": "Units 1–5 — Make one-page summary sheets and list weak algorithms."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 1, "task": "Units 1–6 — Short revision and code tracing."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one graph question + one heap/BST question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-16",
        "day_label": "Mon 16 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Weakest unit deep work — choose based on your error log."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Second-weakest unit — timed problem set, then correct errors."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 8, "task": "Unit 8 — Heaps, priority queues, hashing and indexing practice."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 4, "task": "Unit 4 — Regression/classification: practice algorithm selection and metrics."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 1, "task": "Full-syllabus mixed quiz: definitions, code outputs and tricky concepts."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one weakest-topic question + one different-topic question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-17",
        "day_label": "Tue 17 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Past-paper/mock test under timed conditions (use actual available papers)."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Mark mock, classify errors, redo every incorrect question."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 1, "task": "Full-syllabus review: complexity, linked lists, stacks, queues, trees, graphs, heaps."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 1, "task": "Full-syllabus review: data prep, ML fundamentals, evaluation, regression, clustering."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 1, "task": "Full-syllabus review: classes, constructors, overloading, inheritance, pointers, virtual functions."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one graph/tree question + one array/linked-list question",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-18",
        "day_label": "Wed 18 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 2, "task": "Final consolidation: Unit 2–3 formula/definition sheet and problem patterns."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 4, "task": "Final consolidation: Unit 4–6 methods, algorithms, proofs and probability."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 1, "task": "Solve mixed questions; focus on implementation/complexity errors."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 1, "task": "Solve mixed conceptual/numerical questions; focus on metrics and algorithm differences."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 1, "task": "Solve mixed code-output questions; review only mistakes."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one topic you find difficult + one different topic",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-19",
        "day_label": "Thu 19 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Syllabus coverage audit: check every official topic in Units 1–6; finish any unstudied high-priority item."},
            {"shift": 2, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Build final revision checklist; redo hardest problems without notes."},
            {"shift": 3, "course": "Data Structures", "code": "CSN 3001", "unit": 1, "task": "Final gap-closing session: complete any unfinished syllabus topics."},
            {"shift": 4, "course": "DSML", "code": "CSN 3002", "unit": 1, "task": "Final gap-closing session: complete any unfinished syllabus topics."},
            {"shift": 5, "course": "OOP", "code": "CSN 3004", "unit": 1, "task": "Final gap-closing session: complete any unfinished syllabus topics."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "one gap-closing topic + one different topic",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    },
    {
        "date": "2026-11-20",
        "day_label": "Fri 20 Nov",
        "shifts": [
            {"shift": 1, "course": "Discrete Structures", "code": "CSN 3003", "unit": 1, "task": "Consolidation day: timed mixed set, error-log repair and key definitions."},
            {"shift": 2, "course": "Data Structures", "code": "CSN 3001", "unit": 1, "task": "Consolidation: core implementations, complexities and algorithm traces."},
            {"shift": 3, "course": "DSML", "code": "CSN 3002", "unit": 1, "task": "Consolidation: metrics, preprocessing, regression/classification, PCA/clustering."},
            {"shift": 4, "course": "OOP", "code": "CSN 3004", "unit": 1, "task": "Consolidation: code outputs, constructor order, inheritance, virtual functions and copy behavior."},
            {"shift": 5, "course": "All four", "code": "ALL", "unit": 1, "task": "Create an exam-ready checklist of remaining weak areas for the revision period."}
        ],
        "wrap_up": "Recall key points without notes, tick off completed work, and write the next action.",
        "dsa": "exam-ready checklist and practice",
        "english": "Speaking practice: explain a concept aloud or speak on a topic"
    }
]

def find_best_matching_topic(conn: sqlite3.Connection, subject_id: int, unit_number: int, task_text: str) -> Optional[int]:
    """Finds the best matching topic in the given subject and unit based on task keywords."""
    cursor = conn.cursor()
    # First try unit-specific topics
    cursor.execute("""
        SELECT t.id, t.title 
        FROM topics t
        JOIN units u ON t.unit_id = u.id
        WHERE t.subject_id = ? AND u.unit_number = ?
        ORDER BY t.order_index ASC
    """, (subject_id, unit_number))
    unit_topics = cursor.fetchall()

    if unit_topics:
        # Check title overlap
        lower_task = task_text.lower()
        for t in unit_topics:
            t_words = [w for w in re.split(r'\W+', t["title"].lower()) if len(w) > 3]
            if any(w in lower_task for w in t_words):
                return t["id"]
        # Default to first topic in unit
        return unit_topics[0]["id"]

    # Fallback to any topic in subject
    cursor.execute("SELECT id FROM topics WHERE subject_id = ? ORDER BY id ASC LIMIT 1", (subject_id,))
    row = cursor.fetchone()
    return row["id"] if row else None

def import_official_timetable(conn: sqlite3.Connection, force_overwrite: bool = False) -> Dict[str, Any]:
    """
    Imports the official Word study timetable (27 Oct to 20 Nov 2026).
    Preserves completed study history and prevents duplicate imports.
    """
    cursor = conn.cursor()

    # Get subject map {code: id}
    cursor.execute("SELECT id, code, name FROM subjects")
    subjects = {r["code"]: r["id"] for r in cursor.fetchall()}
    # Fallback subject for 'ALL'
    fallback_subject_id = subjects.get("CSN 3003", 1)

    # Check if timetable has already been imported
    cursor.execute("SELECT COUNT(*) as count FROM study_schedules WHERE scheduled_date >= '2026-10-27' AND scheduled_date <= '2026-11-20'")
    existing_count = cursor.fetchone()["count"]

    if existing_count > 0 and not force_overwrite:
        # Check if existing rows already have shift_number populated
        cursor.execute("SELECT COUNT(*) as count FROM study_schedules WHERE scheduled_date >= '2026-10-27' AND shift_number > 0")
        has_shifts = cursor.fetchone()["count"] > 0
        if has_shifts:
            return {
                "status": "already_imported",
                "message": f"Official timetable already imported with {existing_count} scheduled items.",
                "total_days": len(TIMETABLE_DAYS),
                "total_items": existing_count,
                "imported_count": 0,
                "shifts_created": 0,
                "wrapups_created": 0
            }

    # If force_overwrite or upgrading existing partial schedules, preserve completed sessions
    cursor.execute("SELECT id, scheduled_date, shift_number, status, actual_minutes, notes FROM study_schedules WHERE status = 'COMPLETED' OR actual_minutes > 0")
    completed_records = {(r["scheduled_date"], r["shift_number"]): r for r in cursor.fetchall()}

    # Clean existing pending/placeholder schedules in range
    cursor.execute("""
        DELETE FROM study_schedules 
        WHERE scheduled_date >= '2026-10-27' AND scheduled_date <= '2026-11-20'
        AND status != 'COMPLETED' AND actual_minutes = 0
    """)
    conn.commit()

    total_shifts_created = 0
    total_wrapup_created = 0

    for day in TIMETABLE_DAYS:
        day_date = day["date"]

        for shift_info in day["shifts"]:
            s_num = shift_info["shift"]
            c_code = shift_info["code"]
            subj_id = subjects.get(c_code, fallback_subject_id)
            u_num = shift_info["unit"]
            task_desc = shift_info["task"]

            # Check if this shift was already completed previously
            prev_comp = completed_records.get((day_date, s_num))
            status = prev_comp["status"] if prev_comp else "PENDING"
            act_mins = prev_comp["actual_minutes"] if prev_comp else 0
            notes = prev_comp["notes"] if prev_comp else None

            # Find matching topic in database
            top_id = find_best_matching_topic(conn, subj_id, u_num, task_desc)
            if not top_id:
                # If subject is ALL, pick CSN 3003 topic 1
                cursor.execute("SELECT id FROM topics LIMIT 1")
                top_id = cursor.fetchone()["id"]

            # Check if an existing row exists for this date and shift_number
            cursor.execute("SELECT id FROM study_schedules WHERE scheduled_date = ? AND shift_number = ?", (day_date, s_num))
            existing_row = cursor.fetchone()

            if existing_row:
                cursor.execute("""
                    UPDATE study_schedules SET
                        subject_id = ?, topic_id = ?, duration_minutes = 45,
                        task_description = ?, original_date = COALESCE(original_date, ?),
                        priority = 'HIGH', task_type = 'ACADEMIC_SHIFT',
                        unit_name = ?
                    WHERE id = ?
                """, (subj_id, top_id, task_desc, day_date, f"Unit {u_num}", existing_row["id"]))
            else:
                cursor.execute("""
                    INSERT INTO study_schedules (
                        scheduled_date, original_date, topic_id, subject_id, duration_minutes,
                        shift_number, status, task_type, priority, task_description,
                        unit_name, remaining_minutes, actual_minutes, notes, is_wrapup
                    ) VALUES (
                        ?, ?, ?, ?, 45,
                        ?, ?, 'ACADEMIC_SHIFT', 'HIGH', ?,
                        ?, 45, ?, ?, 0
                    )
                """, (day_date, day_date, top_id, subj_id, s_num, status, task_desc, f"Unit {u_num}", act_mins, notes))
                total_shifts_created += 1

        # 15-minute Wrap-up Block
        cursor.execute("SELECT id FROM study_schedules WHERE scheduled_date = ? AND is_wrapup = 1", (day_date,))
        existing_wrap = cursor.fetchone()
        if not existing_wrap:
            cursor.execute("SELECT id FROM topics LIMIT 1")
            dummy_topic = cursor.fetchone()["id"]
            cursor.execute("""
                INSERT INTO study_schedules (
                    scheduled_date, original_date, topic_id, subject_id, duration_minutes,
                    shift_number, status, task_type, priority, task_description,
                    unit_name, remaining_minutes, actual_minutes, is_wrapup
                ) VALUES (
                    ?, ?, ?, ?, 15,
                    6, 'PENDING', 'WRAP_UP', 'NORMAL', ?,
                    'Active Recall', 15, 0, 1
                )
            """, (day_date, day_date, dummy_topic, fallback_subject_id, day["wrap_up"]))
            total_wrapup_created += 1

        # Daily DSA assignment placeholder
        cursor.execute("SELECT COUNT(*) as count FROM daily_dsa_assignments WHERE assigned_date = ?", (day_date,))
        if cursor.fetchone()["count"] == 0:
            cursor.execute("SELECT id FROM dsa_questions ORDER BY id ASC LIMIT 2")
            q_rows = cursor.fetchall()
            q1 = q_rows[0]["id"] if len(q_rows) > 0 else 1
            q2 = q_rows[1]["id"] if len(q_rows) > 1 else q1
            cursor.execute("""
                INSERT OR IGNORE INTO daily_dsa_assignments (assigned_date, question_id, slot_number, status, approach_notes)
                VALUES (?, ?, 1, 'Pending', ?), (?, ?, 2, 'Pending', ?)
            """, (day_date, q1, day["dsa"], day_date, q2, day["dsa"]))

        # Daily English log placeholder
        cursor.execute("SELECT COUNT(*) as count FROM daily_english_logs WHERE assigned_date = ? OR log_date = ?", (day_date, day_date))
        if cursor.fetchone()["count"] == 0:
            cursor.execute("SELECT id FROM english_speaking_topics ORDER BY id ASC LIMIT 1")
            eng_topic_row = cursor.fetchone()
            eng_topic_id = eng_topic_row["id"] if eng_topic_row else 1
            cursor.execute("""
                INSERT OR IGNORE INTO daily_english_logs (assigned_date, log_date, topic_id, duration_seconds, actual_minutes, shortfall_minutes, completed, notes)
                VALUES (?, ?, ?, 0, 0, 30, 0, ?)
            """, (day_date, day_date, eng_topic_id, day["english"]))

    conn.commit()

    return {
        "status": "success",
        "message": "Official Word timetable successfully imported!",
        "total_days": len(TIMETABLE_DAYS),
        "total_items": total_shifts_created + total_wrapup_created,
        "imported_count": total_shifts_created + total_wrapup_created,
        "shifts_created": total_shifts_created,
        "wrapups_created": total_wrapup_created
    }
