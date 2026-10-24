import sqlite3
import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

class StudyScheduler:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_current_date(self) -> date:
        """Determines the current local system date, or user-configured simulation date if set."""
        override = self._get_setting("simulated_today", None)
        if override:
            try:
                return datetime.strptime(override, "%Y-%m-%d").date()
            except ValueError:
                pass
        return date.today()

    def _get_setting(self, key: str, default: Any = None) -> Any:
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                return row["value"]
        return default

    def calculate_dates(self) -> Dict[str, Any]:
        """Calculates today, first exam date, first-pass deadline, and buffers."""
        today = self.get_current_date()
        first_exam_str = self._get_setting("first_exam_date", "2026-11-26")
        buffer_days = int(self._get_setting("revision_buffer_days", 7))
        
        try:
            first_exam = datetime.strptime(first_exam_str, "%Y-%m-%d").date()
        except ValueError:
            first_exam = today + timedelta(days=32)

        deadline = first_exam - timedelta(days=buffer_days)

        is_past_exam = today > first_exam
        is_past_deadline = today > deadline
        days_to_exam = (first_exam - today).days
        days_to_deadline = (deadline - today).days

        return {
            "today": today,
            "today_str": today.strftime("%Y-%m-%d"),
            "first_exam": first_exam,
            "first_exam_str": first_exam.strftime("%Y-%m-%d"),
            "first_pass_deadline": deadline,
            "first_pass_deadline_str": deadline.strftime("%Y-%m-%d"),
            "buffer_days": buffer_days,
            "days_to_exam": days_to_exam,
            "days_to_deadline": days_to_deadline,
            "is_past_exam": is_past_exam,
            "is_past_deadline": is_past_deadline
        }

    def get_college_hours_for_date(self, target_date: date) -> float:
        """Calculates college class hours for a given date.
        Mon-Fri default: 3.0 hrs
        Sat-Sun default: 0.0 hrs
        Special holiday classes: 5.0 hrs when explicitly marked
        Special break (Dec 6-11): 0.0 hrs
        """
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Check special break range
        break_start = self._get_setting("special_break_start", "2026-12-06")
        break_end = self._get_setting("special_break_end", "2026-12-11")
        include_7th = self._get_setting("special_break_include_7th_day", False)
        if include_7th and break_end == "2026-12-11":
            break_end = "2026-12-12"
            
        if break_start <= date_str <= break_end:
            # College is off during special break
            return 0.0

        # Check explicitly marked special holiday dates with classes
        special_holiday_dates = self._get_setting("special_holiday_class_dates", [])
        if date_str in special_holiday_dates:
            return float(self._get_setting("college_holiday_hours", 5.0))

        # Check day of week (match either full name like 'Monday' or abbreviation like 'mon')
        weekday_name = target_date.strftime("%A").lower()
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][target_date.weekday()]
        working_days = self._get_setting("working_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        working_set = {str(d).lower() for d in working_days}
        if weekday_name in working_set or day_abbr in working_set:
            return float(self._get_setting("college_working_day_hours", 3.0))
        return 0.0

    def get_daily_available_minutes(self, target_date: date) -> int:
        """Calculates realistic available main academic study minutes for a given date.
        Core daily academic target is 240 minutes (4 hours) reserved for semester subjects.
        DSA (2 questions) and English Speaking (30 min) are tracked separately.
        """
        blocked_dates = self._get_setting("blocked_dates", [])
        date_str = target_date.strftime("%Y-%m-%d")
        if date_str in blocked_dates:
            return 0

        # Check special break range
        break_start = self._get_setting("special_break_start", "2026-12-06")
        break_end = self._get_setting("special_break_end", "2026-12-11")
        include_7th = self._get_setting("special_break_include_7th_day", False)
        if include_7th and break_end == "2026-12-11":
            break_end = "2026-12-12"

        if break_start <= date_str <= break_end:
            # User can configure lighter break target or default target
            break_target = self._get_setting("special_break_study_minutes", None)
            if break_target is not None:
                return int(break_target)

        # 1. Check custom weekday/weekend overrides if set
        if target_date.weekday() in (5, 6):
            weekend_custom = self._get_setting("weekend_minutes", None)
            if weekend_custom is not None:
                return int(weekend_custom)
        else:
            weekday_custom = self._get_setting("weekday_minutes", None)
            if weekday_custom is not None:
                return int(weekday_custom)

        # 2. Check explicit day-of-week custom windows if configured
        study_windows = self._get_setting("study_windows", [])
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][target_date.weekday()]
        if study_windows:
            window_mins = sum(w.get("minutes", 0) for w in study_windows if day_abbr in [str(d).lower() for d in w.get("days", [])])
            if window_mins > 0:
                return window_mins

        # 3. Primary Academic Target (240 minutes per day = 4 hours)
        target = self._get_setting("daily_academic_target_minutes", 240)
        return int(target)

    def calculate_topic_remaining_effort(self, topic: Dict[str, Any]) -> int:
        """Mastery-aware remaining effort calculation."""
        base = topic["estimated_minutes"]
        mastery = topic.get("mastery_level", "NOT_STARTED")
        
        mastery_multipliers = {
            "MASTERED": 0.0,
            "CONFIDENT": 0.25,
            "NEEDS_REVISION": 0.60,
            "PARTIALLY_UNDERSTOOD": 0.80,
            "STUDIED_ONCE": 0.90,
            "NOT_STARTED": 1.0
        }
        mult = mastery_multipliers.get(mastery, 1.0)
        remaining = int(base * mult)
        return remaining

    def assess_feasibility(self) -> Dict[str, Any]:
        """Calculates remaining workload vs available study capacity up to first-pass deadline."""
        date_info = self.calculate_dates()
        today = date_info["today"]
        deadline = date_info["first_pass_deadline"]
        first_exam = date_info["first_exam"]

        cursor = self.conn.cursor()
        # Find all mandatory topics
        cursor.execute("""
            SELECT t.id, t.title, t.estimated_minutes, t.mastery_level, t.subject_id, s.name as subject_name
            FROM topics t
            JOIN subjects s ON t.subject_id = s.id
            WHERE t.is_mandatory = 1
        """)
        all_topics = cursor.fetchall()
        total_topics_count = len(all_topics)

        # Check existing completion status
        cursor.execute("""
            SELECT DISTINCT topic_id FROM study_schedules
            WHERE status = 'COMPLETED'
        """)
        completed_topic_ids = {row["topic_id"] for row in cursor.fetchall()}

        remaining_topics = []
        total_remaining_minutes = 0
        subject_workloads = {}

        for t in all_topics:
            t_dict = dict(t)
            s_name = t_dict["subject_name"]
            if s_name not in subject_workloads:
                subject_workloads[s_name] = {"total_mins": 0, "topics_count": 0}

            if t_dict["id"] in completed_topic_ids or t_dict["mastery_level"] == "MASTERED":
                continue
            
            # Check for partial completion in schedules
            cursor.execute("""
                SELECT actual_minutes, completion_percentage, duration_minutes 
                FROM study_schedules 
                WHERE topic_id = ? AND status = 'PARTIALLY_COMPLETED'
                ORDER BY id DESC LIMIT 1
            """, (t_dict["id"],))
            partial = cursor.fetchone()

            eff = self.calculate_topic_remaining_effort(t_dict)
            if partial and partial["completion_percentage"] > 0:
                pct = min(100, max(0, partial["completion_percentage"]))
                eff = int(eff * (100 - pct) / 100.0)

            if eff > 0:
                t_dict["effective_remaining_minutes"] = eff
                remaining_topics.append(t_dict)
                total_remaining_minutes += eff
                subject_workloads[s_name]["total_mins"] += eff
                subject_workloads[s_name]["topics_count"] += 1

        completed_topics_count = total_topics_count - len(remaining_topics)

        # Calculate available minutes up to deadline
        total_available_minutes = 0
        daily_capacities = {}
        curr = today
        while curr <= deadline:
            cap = self.get_daily_available_minutes(curr)
            daily_capacities[curr.strftime("%Y-%m-%d")] = cap
            total_available_minutes += cap
            curr += timedelta(days=1)

        capacity_gap_minutes = total_available_minutes - total_remaining_minutes
        days_to_deadline = max(1, date_info["days_to_deadline"])
        daily_needed = total_remaining_minutes / days_to_deadline if days_to_deadline > 0 else total_remaining_minutes
        daily_avg_available = total_available_minutes / days_to_deadline if days_to_deadline > 0 else 0

        utilization = (total_remaining_minutes / total_available_minutes * 100.0) if total_available_minutes > 0 else 999.0

        is_feasible = (capacity_gap_minutes >= 0) and not date_info["is_past_deadline"]
        
        # Recommendations & status labels
        recommendations = []
        warning_message = None

        if date_info["is_past_deadline"]:
            status_label = "PAST_DEADLINE"
            warning_message = f"Configured deadline ({date_info['first_pass_deadline_str']}) is in the past! Update your examination dates."
            recommendations.append("Update examination or target dates in Settings.")
        elif utilization > 100.0:
            status_label = "OVERLOADED"
            shortfall_hrs = round(abs(capacity_gap_minutes) / 60.0, 1)
            extra_per_day = round(abs(capacity_gap_minutes) / days_to_deadline, 0)
            warning_message = (
                f"Schedule Overload: Remaining syllabus requires {round(total_remaining_minutes/60.0, 1)} hours, "
                f"but only {round(total_available_minutes/60.0, 1)} hours are available before {date_info['first_pass_deadline_str']}. "
                f"Shortfall is {shortfall_hrs} hours (~{int(extra_per_day)} extra mins/day needed)."
            )
            recommendations.append(f"Increase daily study time by ~{int(extra_per_day)} minutes on weekdays/weekends.")
            recommendations.append(f"Reduce the revision buffer from {date_info['buffer_days']} to 4 or 5 days to gain extra study days.")
            recommendations.append("Mark topics you already know as 'Confident' or 'Mastered' to lower remaining workload.")
            recommendations.append("Adjust individual topic effort estimates if initial estimates were overly conservative.")
        elif utilization > 85.0:
            status_label = "TIGHT"
            warning_message = f"Schedule is achievable but tight ({round(utilization, 1)}% capacity utilized). Minor delays could risk the revision buffer."
            recommendations.append("Stay consistent with daily study targets.")
            recommendations.append("Protect study windows from unexpected distractions.")
        else:
            status_label = "ON_TRACK"
            surplus_hrs = round(capacity_gap_minutes / 60.0, 1)
            warning_message = f"Schedule is comfortable! You have a buffer surplus of {surplus_hrs} hours before the {date_info['first_pass_deadline_str']} deadline."
            recommendations.append("Maintain steady pace and engage in active recall.")

        return {
            "is_feasible": is_feasible,
            "current_date": date_info["today_str"],
            "first_exam_date": date_info["first_exam_str"],
            "first_pass_deadline": date_info["first_pass_deadline_str"],
            "days_to_deadline": date_info["days_to_deadline"],
            "days_to_exam": date_info["days_to_exam"],
            "revision_buffer_days": date_info["buffer_days"],
            "total_topics_count": total_topics_count,
            "completed_topics_count": completed_topics_count,
            "remaining_topics_count": len(remaining_topics),
            "total_remaining_minutes": total_remaining_minutes,
            "total_remaining_hours": round(total_remaining_minutes / 60.0, 2),
            "total_available_minutes": total_available_minutes,
            "total_available_hours": round(total_available_minutes / 60.0, 2),
            "capacity_gap_minutes": capacity_gap_minutes,
            "capacity_gap_hours": round(capacity_gap_minutes / 60.0, 2),
            "capacity_utilization_percent": round(utilization, 1),
            "daily_average_needed_minutes": round(daily_needed, 1),
            "daily_average_available_minutes": round(daily_avg_available, 1),
            "status_label": status_label,
            "warning_message": warning_message,
            "actionable_recommendations": recommendations,
            "subject_workloads": subject_workloads
        }

    def _generate_learning_metadata(self, subject_code: str, subject_name: str, unit_title: str, topic_title: str, subtopics: List[str], duration_mins: int) -> Dict[str, str]:
        """Subject-aware dynamic pedagogical metadata generator."""
        s_code = subject_code.upper()
        
        if "CSN 3003" in s_code or "DISCRETE" in subject_name.upper():
            method = "Worked Examples & Proof Rigor"
            objectives = (
                f"• Master the theoretical definitions and theorems for {topic_title}.\n"
                f"• Trace proof structures and solve 3-5 typical examination problems on {unit_title}.\n"
                f"• Verify concepts: {', '.join(subtopics[:3]) if subtopics else topic_title}."
            )
            part1 = int(duration_mins * 0.3)
            part2 = int(duration_mins * 0.45)
            part3 = duration_mins - part1 - part2
            breakdown = f"{part1}m: Theory & theorem study | {part2}m: Step-by-step problem solving | {part3}m: Independent recall & formula verification"
        elif "CSN 3001" in s_code or "DATA STRUCTURES" in subject_name.upper():
            method = "Code Implementation & Complexity Analysis"
            objectives = (
                f"• Understand memory layout and algorithmic invariants for {topic_title}.\n"
                f"• Implement operations and analyze worst/average case time and space complexity.\n"
                f"• Trace edge cases for: {', '.join(subtopics[:3]) if subtopics else topic_title}."
            )
            part1 = int(duration_mins * 0.25)
            part2 = int(duration_mins * 0.5)
            part3 = duration_mins - part1 - part2
            breakdown = f"{part1}m: Conceptual trace & pointer mechanics | {part2}m: Hands-on code/dry run | {part3}m: Complexity & edge-case quiz"
        elif "CSN 3004" in s_code or "OBJECT ORIENTED" in subject_name.upper():
            method = "Object Modeling & OOP Principles"
            objectives = (
                f"• Grasp OOP paradigms, class contracts, and design implications of {topic_title}.\n"
                f"• Write concise, working C++ code exemplifying: {', '.join(subtopics[:3]) if subtopics else topic_title}.\n"
                f"• Identify common pitfalls, compilation errors, and memory ownership details."
            )
            part1 = int(duration_mins * 0.3)
            part2 = int(duration_mins * 0.45)
            part3 = duration_mins - part1 - part2
            breakdown = f"{part1}m: Syntax & concept review | {part2}m: Implementation & operator/class tests | {part3}m: Self-explanation of mechanics"
        else: # Data Science & ML
            method = "Mathematical Intuition & Practical Workflow"
            objectives = (
                f"• Build solid geometric and statistical intuition for {topic_title}.\n"
                f"• Understand mathematical formulations, loss/evaluation functions, and parameter roles.\n"
                f"• Review real-world application & assumptions for: {', '.join(subtopics[:3]) if subtopics else topic_title}."
            )
            part1 = int(duration_mins * 0.35)
            part2 = int(duration_mins * 0.4)
            part3 = duration_mins - part1 - part2
            breakdown = f"{part1}m: Intuition & mathematical formulation | {part2}m: Algorithmic workflow & metrics | {part3}m: Active recall & review"

        return {
            "study_method": method,
            "learning_objectives": objectives,
            "suggested_breakdown": breakdown
        }

    def generate_initial_schedule(self, preserve_completed: bool = True) -> Dict[str, Any]:
        """
        Personalized, multi-subject, deterministic study schedule generator for Last Chance.
        Respects:
        - Strict 240-minute daily academic study capacity (separated from 30m English & 2 DSA topics).
        - Multi-subject allocation every single day (all 4 courses progress without starvation).
        - Dedicated OOP Test Preparation on 25, 26, 27 October 2026 (Units 5 and 6 priority).
        - Discrete Structures highest priority after 27 October:
          First remaining Unit 2 topics -> Unit 3 -> Unit 4 -> Unit 5 -> Unit 6 -> Unit 1 & early Unit 2 review.
        - Prerequisite relationships and pedagogical progression.
        - 19 Nov syllabus completion deadline.
        - 7-day protected revision buffer (19-25 Nov).
        - Full planning horizon through the final exam date (4 Dec 2026).
        """
        date_info = self.calculate_dates()
        today = date_info["today"]
        deadline = date_info["first_pass_deadline"]
        first_exam = date_info["first_exam"]

        cursor = self.conn.cursor()

        # Load completed tasks if preserving
        completed_topic_ids = set()
        if preserve_completed:
            cursor.execute("SELECT DISTINCT topic_id FROM study_schedules WHERE status = 'COMPLETED'")
            completed_topic_ids = {row["topic_id"] for row in cursor.fetchall()}
            # Remove pending future schedules
            cursor.execute("DELETE FROM study_schedules WHERE status = 'PENDING' AND scheduled_date >= ?", (today.strftime("%Y-%m-%d"),))
        else:
            cursor.execute("DELETE FROM study_schedules")

        # Load subjects
        cursor.execute("SELECT id, code, name, priority, color, exam_date FROM subjects ORDER BY id ASC")
        subjects_list = [dict(r) for r in cursor.fetchall()]
        subj_by_code = {s["code"]: s for s in subjects_list}
        subj_by_id = {s["id"]: s for s in subjects_list}

        # Load all topics with unit and subject info
        cursor.execute("""
            SELECT 
                t.id, t.title, t.estimated_minutes, t.base_minutes, t.mastery_level,
                t.is_mandatory, t.order_index, t.unit_id,
                u.title as unit_title, u.unit_number,
                s.id as subject_id, s.code as subject_code, s.name as subject_name,
                s.priority as subject_priority, s.color as subject_color, s.exam_date
            FROM topics t
            JOIN units u ON t.unit_id = u.id
            JOIN subjects s ON t.subject_id = s.id
            WHERE t.is_mandatory = 1
            ORDER BY u.unit_number ASC, t.order_index ASC
        """)
        all_topics = [dict(r) for r in cursor.fetchall()]

        # Load subtopics map
        cursor.execute("SELECT topic_id, title FROM subtopics ORDER BY order_index ASC")
        subtopics_map = {}
        for r in cursor.fetchall():
            subtopics_map.setdefault(r["topic_id"], []).append(r["title"])
        for t in all_topics:
            t["subtopics"] = subtopics_map.get(t["id"], [])

        # Categorize topics by subject
        discrete_topics = [t for t in all_topics if "3003" in t["subject_code"]]
        dsa_topics = [t for t in all_topics if "3001" in t["subject_code"]]
        oop_topics = [t for t in all_topics if "3004" in t["subject_code"]]
        dsml_topics = [t for t in all_topics if "3002" in t["subject_code"]]

        # 1. Sort Discrete Structures (CSN 3003) according to user priority:
        # First: Remaining topics in Unit 2 (Unit 2, topics with order_index >= 6 or remaining)
        # Then: Unit 3, Unit 4, Unit 5, Unit 6
        # Then: Unit 1 and early Unit 2 topics for full mastery
        def discrete_sort_key(t):
            u_num = t["unit_number"]
            if u_num == 2 and t["order_index"] >= 6:
                return (1, t["order_index"])
            elif u_num in (3, 4, 5, 6):
                return (2, u_num, t["order_index"])
            else:
                return (3, u_num, t["order_index"])

        discrete_pool = [t for t in discrete_topics if t["id"] not in completed_topic_ids and t["mastery_level"] != "MASTERED"]
        discrete_pool.sort(key=discrete_sort_key)

        # 2. Sort OOP (CSN 3004):
        oop_units_5_6 = [t for t in oop_topics if t["unit_number"] in (5, 6) and t["id"] not in completed_topic_ids]
        oop_other_pool = [t for t in oop_topics if t["unit_number"] not in (5, 6) and t["id"] not in completed_topic_ids and t["mastery_level"] != "MASTERED"]

        # 3. Data Structures & DS & ML pools
        dsa_pool = [t for t in dsa_topics if t["id"] not in completed_topic_ids and t["mastery_level"] != "MASTERED"]
        dsml_pool = [t for t in dsml_topics if t["id"] not in completed_topic_ids and t["mastery_level"] != "MASTERED"]

        scheduled_items = []
        finished_topics = set(completed_topic_ids)

        # --- Phase 1: Dedicated OOP Test Preparation (25 Oct to 27 Oct 2026) ---
        test_prep_days = [
            ("2026-10-25", [
                ("CSN 3004", 135, "OOP Test Prep: Unit 5 Inheritance Concepts, Base & Derived Constructors, Class Hierarchies, Aggregation"),
                ("CSN 3003", 45, "Discrete Structures: Unit 2 Equivalence Relations and Partitions (High Priority)"),
                ("CSN 3001", 60, "Data Structures: Unit 2 Doubly and Circular Linked Lists")
            ]),
            ("2026-10-26", [
                ("CSN 3004", 135, "OOP Test Prep: Unit 6 Pointers to Objects, Dynamic Memory (new/delete), Virtual Functions, VPTR & VTABLE Mechanics"),
                ("CSN 3003", 60, "Discrete Structures: Unit 2 Partial Orderings, POSETs & Hasse Diagrams"),
                ("CSN 3002", 45, "Data Science & ML: Unit 1 Data Science Workflow & Linear Algebra Foundations")
            ]),
            ("2026-10-27", [
                ("CSN 3004", 120, "OOP Exam Day Final Sprint: Units 5 & 6 Pitfalls, Object Slicing, Virtual Destructors & Mock Test Review"),
                ("CSN 3003", 60, "Discrete Structures: Unit 2 Linear and Well-Ordered Sets"),
                ("CSN 3001", 60, "Data Structures: Unit 3 Stacks, Array/Linked List Implementations & Balanced Brackets")
            ])
        ]

        # Allocate Phase 1 days if currently on or before those dates
        for day_str, allocs in test_prep_days:
            day_date = datetime.strptime(day_str, "%Y-%m-%d").date()
            if day_date >= today:
                day_cap = self.get_daily_available_minutes(day_date)
                if day_cap <= 0:
                    continue

                if day_cap != 240:
                    scale = day_cap / 240.0
                    scaled_allocs = []
                    sum_mins = 0
                    for i, (sc, dur, desc) in enumerate(allocs):
                        if i == len(allocs) - 1:
                            s_dur = day_cap - sum_mins
                        else:
                            s_dur = max(20, int(dur * scale))
                            sum_mins += s_dur
                        scaled_allocs.append((sc, s_dur, desc))
                    current_allocs = scaled_allocs
                else:
                    current_allocs = allocs

                for subj_code, dur, desc in current_allocs:
                    s_info = subj_by_code[subj_code]
                    matching_topic = None
                    if subj_code == "CSN 3004":
                        if oop_units_5_6:
                            matching_topic = oop_units_5_6.pop(0)
                        elif oop_other_pool:
                            matching_topic = oop_other_pool.pop(0)
                    elif subj_code == "CSN 3003" and discrete_pool:
                        matching_topic = discrete_pool.pop(0)
                    elif subj_code == "CSN 3001" and dsa_pool:
                        matching_topic = dsa_pool.pop(0)
                    elif subj_code == "CSN 3002" and dsml_pool:
                        matching_topic = dsml_pool.pop(0)

                    if not matching_topic:
                        cursor.execute("SELECT id, title, unit_id FROM topics WHERE subject_id = ? LIMIT 1", (s_info["id"],))
                        t_row = cursor.fetchone()
                        matching_topic = {"id": t_row["id"], "title": t_row["title"], "unit_title": "Core Unit", "subtopics": []}

                    meta = self._generate_learning_metadata(
                        s_info["code"], s_info["name"], matching_topic.get("unit_title", "Unit"),
                        matching_topic["title"], matching_topic.get("subtopics", []), dur
                    )
                    task_type = "OOP_TEST_PREP" if subj_code == "CSN 3004" else "NEW_LEARNING"

                    scheduled_items.append({
                        "scheduled_date": day_str,
                        "topic_id": matching_topic["id"],
                        "subject_id": s_info["id"],
                        "duration_minutes": dur,
                        "planned_start_time": None,
                        "status": "PENDING",
                        "task_type": task_type,
                        "priority": "URGENT" if subj_code == "CSN 3004" else "HIGH",
                        "learning_objectives": f"• {desc}\n" + meta["learning_objectives"],
                        "suggested_breakdown": meta["suggested_breakdown"],
                        "study_method": meta["study_method"],
                        "reasoning": f"Phase 1 priority allocation: {desc}. Exactly aligns with 27 Oct OOP test and ongoing semester progression."
                    })
                    finished_topics.add(matching_topic["id"])

        # --- Phase 2: Post-Test Multi-Subject Daily Schedule (28 Oct to 18 Nov 2026) ---
        p2_start = max(today, date(2026, 10, 28))
        cur_date = p2_start

        while cur_date <= deadline:
            d_str = cur_date.strftime("%Y-%m-%d")
            daily_cap = self.get_daily_available_minutes(cur_date)
            if daily_cap <= 0:
                cur_date += timedelta(days=1)
                continue

            if daily_cap != 240:
                scale = daily_cap / 240.0
                d_discrete = max(25, int(90 * scale))
                d_dsa = max(20, int(50 * scale))
                d_oop = max(20, int(45 * scale))
                d_dsml = daily_cap - d_discrete - d_dsa - d_oop
                daily_allocations = [
                    ("CSN 3003", d_discrete, discrete_pool, "Discrete Structures: Priority units advancement (Functions, Combinatorics, Graph Theory, Probability, Review)"),
                    ("CSN 3001", d_dsa, dsa_pool, "Data Structures: Core linear and non-linear data structures, trees, graphs, heaps, and complexity analysis"),
                    ("CSN 3004", d_oop, oop_other_pool, "Object Oriented Programming: Programming basics, classes, member functions, operator overloading, data conversions"),
                    ("CSN 3002", d_dsml, dsml_pool, "Data Science & ML: Data preprocessing, regression, classification, clustering, dimensionality reduction")
                ]
            else:
                daily_allocations = [
                    ("CSN 3003", 90, discrete_pool, "Discrete Structures: Priority units advancement (Functions, Combinatorics, Graph Theory, Probability, Review)"),
                    ("CSN 3001", 50, dsa_pool, "Data Structures: Core linear and non-linear data structures, trees, graphs, heaps, and complexity analysis"),
                    ("CSN 3004", 45, oop_other_pool, "Object Oriented Programming: Programming basics, classes, member functions, operator overloading, data conversions"),
                    ("CSN 3002", 55, dsml_pool, "Data Science & ML: Data preprocessing, regression, classification, clustering, dimensionality reduction")
                ]

            for s_code, dur, pool, reason_text in daily_allocations:
                s_info = subj_by_code[s_code]
                if pool:
                    topic = pool.pop(0)
                else:
                    cursor.execute("""
                        SELECT t.id, t.title, u.title as unit_title 
                        FROM topics t JOIN units u ON t.unit_id = u.id 
                        WHERE t.subject_id = ? ORDER BY RANDOM() LIMIT 1
                    """, (s_info["id"],))
                    r_top = cursor.fetchone()
                    topic = {"id": r_top["id"], "title": r_top["title"], "unit_title": r_top["unit_title"], "subtopics": []}

                meta = self._generate_learning_metadata(
                    s_info["code"], s_info["name"], topic.get("unit_title", "Unit"),
                    topic["title"], topic.get("subtopics", []), dur
                )

                scheduled_items.append({
                    "scheduled_date": d_str,
                    "topic_id": topic["id"],
                    "subject_id": s_info["id"],
                    "duration_minutes": dur,
                    "planned_start_time": None,
                    "status": "PENDING",
                    "task_type": "NEW_LEARNING" if topic["id"] not in finished_topics else "REVISION",
                    "priority": "HIGH" if "3003" in s_code else "NORMAL",
                    "learning_objectives": meta["learning_objectives"],
                    "suggested_breakdown": meta["suggested_breakdown"],
                    "study_method": meta["study_method"],
                    "reasoning": f"Multi-subject daily interleaving: {reason_text}. Dedicated 240m academic budget maintained."
                })
                finished_topics.add(topic["id"])

            cur_date += timedelta(days=1)

        # --- Phase 3: 7-Day Revision Buffer (19 Nov to 25 Nov 2026) ---
        rev_start = date(2026, 11, 19)
        rev_end = date(2026, 11, 25)
        rev_cur = max(today, rev_start)

        while rev_cur <= rev_end:
            d_str = rev_cur.strftime("%Y-%m-%d")
            if rev_cur >= date(2026, 11, 23):
                buf_alloc = [
                    ("CSN 3003", 120, "Discrete Structures Exam Prep: Full syllabus formula sheet, proofs, logic, graphs & probability drill"),
                    ("CSN 3001", 45, "Data Structures Buffer Revision: Trees & Graph algorithms review"),
                    ("CSN 3004", 35, "OOP Buffer Revision: Inheritance, pointers, and virtual function trace"),
                    ("CSN 3002", 40, "Data Science & ML Buffer Revision: Core ML algorithms & evaluation metrics")
                ]
            else:
                buf_alloc = [
                    ("CSN 3003", 80, "Discrete Structures Buffer Revision: Worked examples & recurrence relations"),
                    ("CSN 3001", 60, "Data Structures Buffer Revision: Stacks, queues, and tree traversal algorithms"),
                    ("CSN 3004", 50, "OOP Buffer Revision: Class design, operator overloading, and copy constructors"),
                    ("CSN 3002", 50, "Data Science & ML Buffer Revision: Regression and classification algorithms review")
                ]

            for s_code, dur, rev_desc in buf_alloc:
                s_info = subj_by_code[s_code]
                scheduled_for_subj = [it["topic_id"] for it in scheduled_items if it["subject_id"] == s_info["id"]]
                if scheduled_for_subj:
                    top_id = scheduled_for_subj[len(scheduled_items) % len(scheduled_for_subj)]
                    cursor.execute("SELECT title FROM topics WHERE id = ?", (top_id,))
                    r_top = cursor.fetchone()
                    top_title = r_top["title"] if r_top else "Core Topic"
                else:
                    cursor.execute("SELECT t.id, t.title FROM topics t JOIN units u ON t.unit_id = u.id WHERE t.subject_id = ? ORDER BY u.unit_number ASC, t.order_index ASC LIMIT 1", (s_info["id"],))
                    r_top = cursor.fetchone()
                    top_id = r_top["id"] if r_top else 1
                    top_title = r_top["title"] if r_top else "Syllabus Review"

                meta = self._generate_learning_metadata(
                    s_info["code"], s_info["name"], "Revision Buffer", top_title, [], dur
                )

                scheduled_items.append({
                    "scheduled_date": d_str,
                    "topic_id": top_id,
                    "subject_id": s_info["id"],
                    "duration_minutes": dur,
                    "planned_start_time": None,
                    "status": "PENDING",
                    "task_type": "REVISION",
                    "priority": "HIGH",
                    "learning_objectives": f"• {rev_desc}\n• Active recall and past paper mock questions.",
                    "suggested_breakdown": meta["suggested_breakdown"],
                    "study_method": "Active Recall & Timed Mock Questions",
                    "reasoning": f"Protected 7-day revision buffer: {rev_desc}."
                })
            rev_cur += timedelta(days=1)

        # --- Phase 4: Exam Execution Horizon (26 Nov to 4 Dec 2026) ---
        exam_schedule_days = [
            ("2026-11-26", [
                ("CSN 3003", 120, "Discrete Structures: Final morning review and formula memory lock before examination"),
                ("CSN 3001", 120, "Data Structures: Immediate post-exam sprint: Review Units 1-4 for 28 Nov exam")
            ]),
            ("2026-11-27", [
                ("CSN 3001", 240, "Data Structures Intensive Pre-Exam Day: Trees, BST, Graphs, Dijkstra, Heaps, and Sorting algorithm dry runs")
            ]),
            ("2026-11-28", [
                ("CSN 3001", 120, "Data Structures Exam Day: Final review before exam paper"),
                ("CSN 3004", 120, "Object Oriented Programming: Kickoff sprint for 1 Dec exam: Classes, Overloading, Inheritance")
            ]),
            ("2026-11-29", [
                ("CSN 3004", 240, "OOP Intensive Revision: Inheritance hierarchies, pointers to objects, virtual functions, dynamic memory management")
            ]),
            ("2026-11-30", [
                ("CSN 3004", 240, "OOP Pre-Exam Sprint: Mock papers, operator overloading assignment deep dive, and VTABLE/VPTR tracing")
            ]),
            ("2026-12-01", [
                ("CSN 3004", 120, "OOP Exam Day: Final formula and syntax recall before exam"),
                ("CSN 3002", 120, "Data Science & ML: Kickoff sprint for 4 Dec exam: Data preprocessing & Linear Algebra")
            ]),
            ("2026-12-02", [
                ("CSN 3002", 240, "Data Science & ML Intensive: Supervised Learning, Regression, Classification (SVM, Decision Trees, Naive Bayes)")
            ]),
            ("2026-12-03", [
                ("CSN 3002", 240, "Data Science & ML Pre-Exam Sprint: Clustering (K-Means, Hierarchical), PCA, ROC-curves, and evaluation metrics")
            ]),
            ("2026-12-04", [
                ("CSN 3002", 240, "Data Science & ML Exam Day: Final review, matrix intuition, and exam execution. Semester Complete!")
            ])
        ]

        for day_str, allocs in exam_schedule_days:
            day_date = datetime.strptime(day_str, "%Y-%m-%d").date()
            if day_date >= today:
                for s_code, dur, desc in allocs:
                    s_info = subj_by_code[s_code]
                    scheduled_for_subj = [it["topic_id"] for it in scheduled_items if it["subject_id"] == s_info["id"]]
                    if scheduled_for_subj:
                        t_id = scheduled_for_subj[len(scheduled_items) % len(scheduled_for_subj)]
                        cursor.execute("SELECT title FROM topics WHERE id = ?", (t_id,))
                        top_r = cursor.fetchone()
                        t_name = top_r["title"] if top_r else "Exam Review"
                    else:
                        cursor.execute("SELECT t.id, t.title FROM topics t JOIN units u ON t.unit_id = u.id WHERE t.subject_id = ? ORDER BY u.unit_number ASC, t.order_index ASC LIMIT 1", (s_info["id"],))
                        top_r = cursor.fetchone()
                        t_id = top_r["id"] if top_r else 1
                        t_name = top_r["title"] if top_r else "Exam Review"

                    meta = self._generate_learning_metadata(s_info["code"], s_info["name"], "Exam Phase", t_name, [], dur)
                    scheduled_items.append({
                        "scheduled_date": day_str,
                        "topic_id": t_id,
                        "subject_id": s_info["id"],
                        "duration_minutes": dur,
                        "planned_start_time": None,
                        "status": "PENDING",
                        "task_type": "EXAM_PREP",
                        "priority": "URGENT",
                        "learning_objectives": f"• {desc}\n• High-yield examination focus.",
                        "suggested_breakdown": meta["suggested_breakdown"],
                        "study_method": "Intensive Targeted Exam Sprint",
                        "reasoning": f"Exam Phase Allocation: {desc}."
                    })

        # Insert scheduled items into SQLite
        for item in scheduled_items:
            cursor.execute("""
                INSERT INTO study_schedules (
                    scheduled_date, topic_id, subject_id, duration_minutes, planned_start_time,
                    status, task_type, priority, learning_objectives, suggested_breakdown,
                    study_method, reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["scheduled_date"], item["topic_id"], item["subject_id"], item["duration_minutes"],
                item["planned_start_time"], item["status"], item["task_type"], item["priority"],
                item["learning_objectives"], item["suggested_breakdown"], item["study_method"], item["reasoning"]
            ))

        # Log change
        dates_covered = sorted(list(set(i["scheduled_date"] for i in scheduled_items)))
        changes_msg = f"Generated complete personalized study schedule: {len(scheduled_items)} sessions covering {len(dates_covered)} days from {dates_covered[0] if dates_covered else 'N/A'} through {dates_covered[-1] if dates_covered else 'N/A'}."
        cursor.execute("""
            INSERT INTO schedule_change_logs (reason, changes_summary, affected_dates_json)
            VALUES (?, ?, ?)
        """, ("Full Horizon Multi-Subject Schedule Generation", changes_msg, json.dumps(dates_covered)))

        self.conn.commit()

        feasibility = self.assess_feasibility()
        return {
            "success": True,
            "tasks_scheduled": len(scheduled_items),
            "dates_covered_count": len(dates_covered),
            "date_range": f"{dates_covered[0] if dates_covered else ''} to {dates_covered[-1] if dates_covered else ''}",
            "feasibility": feasibility
        }

    def reschedule_unfinished_work(self, changed_schedule_id: int, new_status: str, actual_minutes: int = 0, completion_percentage: int = 0, remaining_minutes_override: Optional[int] = None) -> Dict[str, Any]:
        """
        Adaptive schedule recovery:
        - When a task is marked MISSED or PARTIALLY_COMPLETED,
        - Preserves all completed work,
        - Computes remaining effort,
        - Shifts unfinished work to future available slots,
        - Re-checks prerequisites and first-pass deadline,
        - Logs explainable reasoning for every moved task.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.*, t.title as topic_title, t.estimated_minutes, sub.name as subject_name
            FROM study_schedules s
            JOIN topics t ON s.topic_id = t.id
            JOIN subjects sub ON s.subject_id = sub.id
            WHERE s.id = ?
        """, (changed_schedule_id,))
        task = cursor.fetchone()
        if not task:
            return {"success": False, "error": "Schedule not found"}

        task_dict = dict(task)
        task_date_str = task_dict["scheduled_date"]
        task_date = datetime.strptime(task_date_str, "%Y-%m-%d").date()
        today = self.get_current_date()

        # Update current task status
        cursor.execute("""
            UPDATE study_schedules 
            SET status = ?, actual_minutes = ?, completion_percentage = ?, completed_at = datetime('now')
            WHERE id = ?
        """, (new_status, actual_minutes, completion_percentage, changed_schedule_id))

        if new_status == "COMPLETED" and completion_percentage == 100:
            # Also update topic mastery
            cursor.execute("UPDATE topics SET mastery_level = 'CONFIDENT' WHERE id = ? AND mastery_level = 'NOT_STARTED'", (task_dict["topic_id"],))
            self.conn.commit()
            return {"success": True, "message": "Task marked 100% completed. No rescheduling needed."}

        # Calculate remaining effort to reschedule
        if remaining_minutes_override is not None and remaining_minutes_override > 0:
            rem_effort = remaining_minutes_override
        elif actual_minutes > 0:
            rem_effort = max(0, task_dict["duration_minutes"] - actual_minutes)
        elif new_status == "PARTIALLY_COMPLETED" and completion_percentage > 0:
            pct_left = max(0, 100 - completion_percentage)
            rem_effort = int(task_dict["duration_minutes"] * pct_left / 100.0)
        else: # MISSED or 0%
            rem_effort = task_dict["duration_minutes"]

        if rem_effort <= 0:
            self.conn.commit()
            return {"success": True, "message": "No remaining minutes left to reschedule."}

        # Find future days starting from tomorrow (or today if capacity remains)
        date_info = self.calculate_dates()
        deadline = date_info["first_pass_deadline"]
        start_date = max(today, task_date)
        if start_date == today:
            # Check today's remaining capacity
            cursor.execute("SELECT COALESCE(SUM(duration_minutes), 0) FROM study_schedules WHERE scheduled_date = ? AND status != 'MISSED'", (today.strftime("%Y-%m-%d"),))
            used_today = cursor.fetchone()[0]
            avail_today = self.get_daily_available_minutes(today)
            if avail_today - used_today < 30:
                start_date = today + timedelta(days=1)
        else:
            start_date = start_date + timedelta(days=1)

        # Find best slot for remaining work
        curr_d = start_date
        placed_date = None
        allocated_minutes = 0
        affected_dates = []

        placed = False
        while curr_d <= deadline + timedelta(days=date_info["buffer_days"]):
            d_str = curr_d.strftime("%Y-%m-%d")
            cursor.execute("SELECT COALESCE(SUM(duration_minutes), 0) FROM study_schedules WHERE scheduled_date = ? AND status = 'PENDING'", (d_str,))
            used = cursor.fetchone()[0]
            avail = self.get_daily_available_minutes(curr_d)
            free = avail - used

            if free >= rem_effort:
                alloc = rem_effort
                meta = self._generate_learning_metadata(
                    task_dict.get("subject_code", ""),
                    task_dict["subject_name"],
                    "",
                    task_dict["topic_title"],
                    [],
                    alloc
                )
                reason = (
                    f"Rescheduled {alloc}m from uncompleted session on {task_date_str}. "
                    f"Placed on {d_str} where {free}m free capacity was available."
                )
                cursor.execute("""
                    INSERT INTO study_schedules (
                        scheduled_date, topic_id, subject_id, duration_minutes, status,
                        task_type, priority, learning_objectives, suggested_breakdown,
                        study_method, reasoning
                    ) VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, ?)
                """, (
                    d_str, task_dict["topic_id"], task_dict["subject_id"], alloc,
                    task_dict["task_type"], task_dict["priority"], meta["learning_objectives"],
                    meta["suggested_breakdown"], meta["study_method"], reason
                ))
                rem_effort = 0
                affected_dates.append(d_str)
                placed = True
                break
            curr_d += timedelta(days=1)

        # If capacity was tightly packed, place any remaining unfinished work on start_date
        if rem_effort > 0:
            fallback_date = start_date.strftime("%Y-%m-%d")
            meta = self._generate_learning_metadata(
                task_dict.get("subject_code", ""),
                task_dict["subject_name"],
                "",
                task_dict["topic_title"],
                [],
                rem_effort
            )
            reason = f"Rescheduled {rem_effort}m from uncompleted session on {task_date_str}. Placed on {fallback_date} for catch-up."
            cursor.execute("""
                INSERT INTO study_schedules (
                    scheduled_date, topic_id, subject_id, duration_minutes, status,
                    task_type, priority, learning_objectives, suggested_breakdown,
                    study_method, reasoning
                ) VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?, ?)
            """, (
                fallback_date, task_dict["topic_id"], task_dict["subject_id"], rem_effort,
                task_dict["task_type"], task_dict["priority"], meta["learning_objectives"],
                meta["suggested_breakdown"], meta["study_method"], reason
            ))
            affected_dates.append(fallback_date)
            rem_effort = 0

        # Log change
        log_msg = (
            f"Rescheduled unfinished task '{task_dict['topic_title']}' ({task_dict['subject_name']}). "
            f"Moved remaining workload to {', '.join(affected_dates)}. "
            f"Capacity recalculation completed."
        )
        cursor.execute("""
            INSERT INTO schedule_change_logs (reason, changes_summary, affected_dates_json)
            VALUES (?, ?, ?)
        """, (f"Adaptive Reschedule: Task {task_dict['topic_title']}", log_msg, json.dumps(affected_dates)))

        self.conn.commit()

        feasibility = self.assess_feasibility()
        return {
            "success": True,
            "rescheduled_to_dates": affected_dates,
            "summary": log_msg,
            "feasibility": feasibility
        }
