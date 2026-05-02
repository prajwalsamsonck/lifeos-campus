from datetime import datetime, timedelta


class ExamDetector:
    EXAM_KEYWORDS = [
        "exam", "test", "quiz", "viva", "lab test",
        "mid sem", "end sem", "assessment", "evaluation",
    ]

    def analyze_week(self, events_list: list) -> dict:
        now = datetime.now()
        five_days = now + timedelta(days=5)
        exam_count = 0
        assignment_count = 0
        detected_exams = []

        for event in events_list:
            start = event.get("start_time")
            if isinstance(start, datetime):
                if not (now <= start <= five_days):
                    continue

            summary_lower = event.get("summary", "").lower()
            is_exam = any(kw in summary_lower for kw in self.EXAM_KEYWORDS)
            is_assignment = "assignment" in summary_lower or "submission" in summary_lower

            if is_exam:
                exam_count += 1
                detected_exams.append(event)
            elif is_assignment:
                assignment_count += 1

        return {
            "exam_count": exam_count,
            "assignment_count": assignment_count,
            "is_exam_week": exam_count >= 2,
            "is_crunch_week": exam_count + assignment_count >= 3,
            "detected_exams": detected_exams,
        }

    def get_exam_mode_config(self) -> dict:
        return {
            "notif_score_threshold": 9,
            "social_apps_blocked": True,
            "focus_window_hours": [20, 23],
            "sleep_protection_until": 7,
            "digest_frequency": "2x daily",
        }
