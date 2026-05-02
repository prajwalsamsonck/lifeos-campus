import os
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_CALENDAR_KEY = os.getenv("GOOGLE_CALENDAR_KEY")


def _mock_events() -> list:
    today = datetime.now().replace(second=0, microsecond=0)
    return [
        {"summary": "DBMS Lab",           "start_time": today.replace(hour=9,  minute=0), "location": "Room 304"},
        {"summary": "DSA Lecture",         "start_time": today.replace(hour=11, minute=0), "location": "Room 101"},
        {"summary": "Mini Project Review", "start_time": today.replace(hour=14, minute=0), "location": "Seminar Hall"},
    ]


class CalendarSkill:
    def get_upcoming_events(self, max_results: int = 3) -> list:
        if not _CALENDAR_KEY:
            logger.debug("GOOGLE_CALENDAR_KEY not set — using mock events")
            return _mock_events()

        try:
            import requests
            url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
            params = {
                "key": _CALENDAR_KEY,
                "maxResults": max_results,
                "orderBy": "startTime",
                "singleEvents": True,
                "timeMin": datetime.utcnow().isoformat() + "Z",
            }
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            events = []
            for item in items:
                start_raw = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                try:
                    start_time = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
                except Exception:
                    start_time = datetime.now()
                events.append({
                    "summary": item.get("summary", "Untitled"),
                    "start_time": start_time.replace(tzinfo=None),
                    "location": item.get("location"),
                })
            return events or _mock_events()
        except Exception as exc:
            logger.debug("Calendar API failed (%s) — using mock events", exc)
            return _mock_events()

    def get_next_event(self) -> dict | None:
        events = self.get_upcoming_events(max_results=1)
        return events[0] if events else None

    def compute_departure_alert(self, event: dict, travel_minutes: int = 25) -> dict:
        try:
            departure_time = event["start_time"] - timedelta(minutes=travel_minutes)
            minutes_until_departure = (departure_time - datetime.now()).total_seconds() / 60
            if 8 <= minutes_until_departure <= 12:
                return {
                    "should_alert": True,
                    "event_name": event["summary"],
                    "depart_in_minutes": round(minutes_until_departure),
                    "travel_minutes": travel_minutes,
                    "location": event.get("location"),
                    "bus_suggestion": "Bus 401",
                }
        except Exception:
            pass
        return {"should_alert": False}
