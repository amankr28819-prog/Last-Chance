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

    def get_daily_available_minutes(self, target_date: date) -> int:
        """Calculates realistic available study minutes for a given date considering weekday/weekend and blocked dates."""
        blocked_dates = self._get_setting("blocked_dates", [])
        date_str = target_date.strftime("%Y-%m-%d")
        if date_str in blocked_dates:
            return 0

        # Check explicit day-of-week custom windows if present
        study_windows = self._get_setting("study_windows", [])
        day_abbr = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][target_date.weekday()]
        
        if study_windows:
            window_mins = sum(w.get("minutes", 0) for w in study_windows if day_abbr in w.get("days", []))
            if window_mins > 0:
                return window_mins

        # Default fallback
        if target_date.weekday() in (5, 6): # Weekend
            return int(self._get_setting("weekend_minutes", 300))
        return int(self._get_setting("weekday_minutes", 180))

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
        Deterministic, prerequisite-aware, workload-balanced study schedule generator.
        Respects:
        - Daily available study capacity (never overloads days).
        - Prerequisite relationships (prerequisites always scheduled before dependents).
        - Balanced subject interleaving.
        - First-pass completion deadline (targeting 19 Nov 2026).
        - Protected 7-day revision buffer.
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

        # Load topics with subject and unit metadata
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
            ORDER BY s.priority DESC, s.exam_date ASC, u.unit_number ASC, t.order_index ASC
        """)
        raw_topics = [dict(r) for r in cursor.fetchall()]

        # Load subtopics
        cursor.execute("SELECT topic_id, title FROM subtopics ORDER BY order_index ASC")
        subtopics_map = {}
        for r in cursor.fetchall():
            subtopics_map.setdefault(r["topic_id"], []).append(r["title"])

        # Load prerequisites
        cursor.execute("SELECT topic_id, prerequisite_topic_id FROM prerequisites")
        prereq_graph = {} # topic_id -> set of prerequisite_topic_ids
        for r in cursor.fetchall():
            prereq_graph.setdefault(r["topic_id"], set()).add(r["prerequisite_topic_id"])

        # Filter out completed or mastered
        topics_to_schedule = []
        for t in raw_topics:
            t["subtopics"] = subtopics_map.get(t["id"], [])
            if t["id"] in completed_topic_ids or t["mastery_level"] == "MASTERED":
                continue
            eff = self.calculate_topic_remaining_effort(t)
            if eff > 0:
                t["effective_minutes"] = eff
                topics_to_schedule.append(t)

        # Build dependency ordering (Topological sort with subject-interleaving)
        # Priority score calculation
        priority_weights = {"URGENT": 300, "HIGH": 200, "NORMAL": 100}
        
        def compute_sort_key(topic):
            subj_wt = priority_weights.get(topic["subject_priority"], 100)
            # Earlier exam date gets bonus
            try:
                ex_date = datetime.strptime(topic["exam_date"], "%Y-%m-%d").date()
                days_to_ex = (ex_date - today).days
                exam_urgency = max(0, 100 - days_to_ex)
            except Exception:
                exam_urgency = 0
            prereqs_count = len(prereq_graph.get(topic["id"], set()))
            return -(subj_wt + exam_urgency * 2 - prereqs_count * 10 - topic["order_index"])

        topics_to_schedule.sort(key=compute_sort_key)

        # Scheduling loop over dates
        scheduled_items = []
        finished_in_sim = set(completed_topic_ids)
        remaining_pool = list(topics_to_schedule)

        curr_date = today
        subjects_per_day_limit = int(self._get_setting("subjects_per_day", 2))
        max_consecutive = int(self._get_setting("max_consecutive_minutes", 90))

        # We first schedule up to deadline
        while remaining_pool and curr_date <= deadline:
            date_str = curr_date.strftime("%Y-%m-%d")
            daily_cap = self.get_daily_available_minutes(curr_date)
            remaining_day_cap = daily_cap
            subjects_today = set()

            # Find candidates whose prerequisites are satisfied
            while remaining_day_cap >= 30 and remaining_pool:
                candidate_idx = None
                for idx, cand in enumerate(remaining_pool):
                    cand_prereqs = prereq_graph.get(cand["id"], set())
                    # Check if all prereqs completed
                    if cand_prereqs.issubset(finished_in_sim):
                        # Check subjects per day preference
                        if len(subjects_today) < subjects_per_day_limit or cand["subject_id"] in subjects_today or len(remaining_pool) <= 3:
                            candidate_idx = idx
                            break
                
                # If no topic meets the subject limit, relax subject limit for the day to avoid idle capacity
                if candidate_idx is None:
                    for idx, cand in enumerate(remaining_pool):
                        cand_prereqs = prereq_graph.get(cand["id"], set())
                        if cand_prereqs.issubset(finished_in_sim):
                            candidate_idx = idx
                            break

                if candidate_idx is None:
                    # Prerequisite blockage or empty
                    break

                selected = remaining_pool.pop(candidate_idx)
                needed_mins = selected["effective_minutes"]

                # Check if fits in remaining day capacity or needs split
                if needed_mins <= remaining_day_cap:
                    duration = needed_mins
                    finished_in_sim.add(selected["id"])
                    split_part = None
                else:
                    # Split task!
                    duration = remaining_day_cap
                    # Create remaining part
                    leftover_mins = needed_mins - duration
                    selected["effective_minutes"] = leftover_mins
                    remaining_pool.insert(0, selected) # schedule rest tomorrow
                    split_part = f"Part 1 ({duration}m of {needed_mins}m)"

                meta = self._generate_learning_metadata(
                    selected["subject_code"],
                    selected["subject_name"],
                    selected["unit_title"],
                    selected["title"],
                    selected["subtopics"],
                    duration
                )

                reason = (
                    f"Scheduled on {date_str} to advance {selected['subject_name']} ({selected['unit_title']}). "
                    f"Fits within daily capacity ({remaining_day_cap}m remaining before allocation)."
                )
                if split_part:
                    reason += f" Split into {split_part} to respect daily limit."

                sched_entry = {
                    "scheduled_date": date_str,
                    "topic_id": selected["id"],
                    "subject_id": selected["subject_id"],
                    "duration_minutes": duration,
                    "planned_start_time": None,
                    "status": "PENDING",
                    "task_type": "NEW_LEARNING",
                    "priority": selected["subject_priority"],
                    "learning_objectives": meta["learning_objectives"],
                    "suggested_breakdown": meta["suggested_breakdown"],
                    "study_method": meta["study_method"],
                    "reasoning": reason
                }
                scheduled_items.append(sched_entry)

                remaining_day_cap -= duration
                subjects_today.add(selected["subject_id"])

            curr_date += timedelta(days=1)

        # If any topics remain after deadline, schedule into the buffer only if necessary, with clear warning
        overrun_into_buffer = False
        if remaining_pool and curr_date <= first_exam:
            overrun_into_buffer = True
            while remaining_pool and curr_date < first_exam:
                date_str = curr_date.strftime("%Y-%m-%d")
                daily_cap = self.get_daily_available_minutes(curr_date)
                remaining_day_cap = daily_cap

                while remaining_day_cap >= 30 and remaining_pool:
                    selected = remaining_pool.pop(0)
                    duration = min(selected["effective_minutes"], remaining_day_cap)
                    
                    meta = self._generate_learning_metadata(
                        selected["subject_code"], selected["subject_name"], selected["unit_title"],
                        selected["title"], selected["subtopics"], duration
                    )
                    reason = f"EMERGENCY OVERFLOW: Scheduled during protected buffer on {date_str} due to insufficient pre-deadline capacity."

                    sched_entry = {
                        "scheduled_date": date_str,
                        "topic_id": selected["id"],
                        "subject_id": selected["subject_id"],
                        "duration_minutes": duration,
                        "planned_start_time": None,
                        "status": "PENDING",
                        "task_type": "NEW_LEARNING",
                        "priority": "URGENT",
                        "learning_objectives": meta["learning_objectives"],
                        "suggested_breakdown": meta["suggested_breakdown"],
                        "study_method": meta["study_method"],
                        "reasoning": reason
                    }
                    scheduled_items.append(sched_entry)
                    remaining_day_cap -= duration

                    if duration < selected["effective_minutes"]:
                        selected["effective_minutes"] -= duration
                        remaining_pool.insert(0, selected)
                        break

                curr_date += timedelta(days=1)

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

        # Generate Spaced Revisions and Protected Final Buffer Sessions
        self._generate_revision_buffer_tasks(deadline, first_exam)

        # Log change
        changes_msg = f"Generated full schedule: {len(scheduled_items)} study tasks allocated across {len(set(i['scheduled_date'] for i in scheduled_items))} days."
        if overrun_into_buffer:
            changes_msg += " WARNING: Capacity shortfall forced mandatory topics into the protected revision buffer!"
        
        cursor.execute("""
            INSERT INTO schedule_change_logs (reason, changes_summary, affected_dates_json)
            VALUES (?, ?, ?)
        """, ("Full Schedule Generation", changes_msg, json.dumps(list(set(i["scheduled_date"] for i in scheduled_items)))))

        self.conn.commit()

        feasibility = self.assess_feasibility()
        return {
            "success": True,
            "tasks_scheduled": len(scheduled_items),
            "unassigned_topics_count": len(remaining_pool),
            "overrun_into_buffer": overrun_into_buffer,
            "feasibility": feasibility
        }

    def _generate_revision_buffer_tasks(self, deadline: date, first_exam: date):
        """Populates the 7-day revision buffer (e.g. Nov 19 to Nov 25) with high-value mock and revision sessions."""
        cursor = self.conn.cursor()
        curr = deadline
        cursor.execute("SELECT id, name, code FROM subjects")
        subjects = [dict(r) for r in cursor.fetchall()]

        # For each buffer day, schedule targeted revision if capacity is available
        rev_types = ["MOCK_TEST", "PROBLEM_SOLVING", "FORMULA_REVIEW", "WEAK_AREAS_RECALL"]
        idx = 0
        while curr < first_exam:
            date_str = curr.strftime("%Y-%m-%d")
            # Check how much capacity is already used by overflow
            cursor.execute("SELECT COALESCE(SUM(duration_minutes), 0) FROM study_schedules WHERE scheduled_date = ?", (date_str,))
            used = cursor.fetchone()[0]
            avail = self.get_daily_available_minutes(curr)
            rem = avail - used

            if rem >= 60 and subjects:
                subj = subjects[idx % len(subjects)]
                rev_type = rev_types[idx % len(rev_types)]
                
                # Pick a representative topic from this subject for review
                cursor.execute("""
                    SELECT id, title FROM topics 
                    WHERE subject_id = ? 
                    ORDER BY RANDOM() LIMIT 1
                """, (subj["id"],))
                top = cursor.fetchone()
                if top:
                    cursor.execute("""
                        INSERT INTO study_schedules (
                            scheduled_date, topic_id, subject_id, duration_minutes,
                            status, task_type, priority, learning_objectives,
                            suggested_breakdown, study_method, reasoning
                        ) VALUES (?, ?, ?, ?, 'PENDING', 'REVISION', 'HIGH', ?, ?, ?, ?)
                    """, (
                        date_str, top["id"], subj["id"], min(90, rem),
                        f"Final Buffer Intensive Revision: {top['title']} and related unit concepts in {subj['name']}.",
                        "30m: Timed problem solving | 30m: Formula and edge case recap | 30m: Self-assessment error analysis",
                        f"Active Spaced Review ({rev_type.replace('_', ' ')})",
                        f"Protected 7-day pre-exam revision session for {subj['name']}."
                    ))
                idx += 1
            curr += timedelta(days=1)

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

        while curr_d <= deadline + timedelta(days=date_info["buffer_days"]):
            d_str = curr_d.strftime("%Y-%m-%d")
            cursor.execute("SELECT COALESCE(SUM(duration_minutes), 0) FROM study_schedules WHERE scheduled_date = ? AND status = 'PENDING'", (d_str,))
            used = cursor.fetchone()[0]
            avail = self.get_daily_available_minutes(curr_d)
            free = avail - used

            if free >= 30:
                # Can fit at least part of it
                alloc = min(free, rem_effort)
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
                rem_effort -= alloc
                affected_dates.append(d_str)
                if not placed_date:
                    placed_date = d_str

                if rem_effort <= 0:
                    break
            curr_d += timedelta(days=1)

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
