import logging

from calendar_skill import CalendarSkill
from exam_detector import ExamDetector
from pattern_memory import PatternMemory
from commute_skill import CommuteSkill
from modes import get_mode
import telegram_bot
import memory

logger = logging.getLogger(__name__)


class CampusAgent:
    def __init__(self):
        self.calendar = CalendarSkill()
        self.exam_detector = ExamDetector()
        self.pattern_memory = PatternMemory()
        self.commute = CommuteSkill()
        self._exam_week_alerted = False

    def run_campus_check(self, ctx: dict) -> dict:
        results = {}

        # Step 1: upcoming events
        try:
            events = self.calendar.get_upcoming_events()
            results["events"] = events
        except Exception as exc:
            logger.debug("Calendar fetch failed: %s", exc)
            events = []
            results["events"] = []

        # Step 2: departure alert
        try:
            next_event = self.calendar.get_next_event()
            if next_event:
                departure = self.calendar.compute_departure_alert(next_event)
                results["departure_alert"] = departure
                if departure.get("should_alert"):
                    travel_est = self.commute.get_travel_estimate()
                    alert_str = self.commute.build_commute_alert(next_event, travel_est)
                    telegram_bot.send_commute_alert(alert_str)
                    memory.log_event("commute_alert", departure)
            else:
                results["departure_alert"] = {"should_alert": False}
        except Exception as exc:
            logger.debug("Departure check failed: %s", exc)
            results["departure_alert"] = {"should_alert": False}

        # Step 3: exam week detection (fire once per session)
        try:
            exam_data = self.exam_detector.analyze_week(events)
            results["exam_data"] = exam_data
            if exam_data["is_exam_week"] and not self._exam_week_alerted:
                telegram_bot.send_exam_mode_alert(exam_data)
                memory.log_event("exam_mode", {
                    "exam_count": exam_data["exam_count"],
                    "is_crunch_week": exam_data["is_crunch_week"],
                })
                self._exam_week_alerted = True
        except Exception as exc:
            logger.debug("Exam detection failed: %s", exc)
            results["exam_data"] = {}

        # Step 4: log mode event to pattern memory
        try:
            mode_name = get_mode(ctx).name
            self.pattern_memory.log_mode_event(
                mode_name, ctx["hour"], ctx["day"], ctx["location_zone"]
            )
        except Exception as exc:
            logger.debug("Pattern log failed: %s", exc)

        # Step 5: predict next mode
        try:
            prediction = self.pattern_memory.predict_next_mode(ctx["hour"], ctx["day"])
            results["prediction"] = prediction
            if prediction:
                logger.info("[PATTERN] Next mode predicted: %s", prediction)
        except Exception as exc:
            logger.debug("Prediction failed: %s", exc)
            results["prediction"] = None

        return results
