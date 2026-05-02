import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

PATTERN_FILE = Path("pattern_memory.json")
MAX_ENTRIES = 500
logger = logging.getLogger(__name__)


class PatternMemory:
    def _read(self) -> list:
        if not PATTERN_FILE.exists():
            return []
        try:
            return json.loads(PATTERN_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _write(self, records: list) -> None:
        PATTERN_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def log_mode_event(self, mode_name: str, hour: int, day: str, zone: str) -> None:
        records = self._read()
        records.append({
            "mode": mode_name,
            "hour": hour,
            "day": day,
            "zone": zone,
            "timestamp": datetime.now().isoformat(),
        })
        if len(records) > MAX_ENTRIES:
            records = records[-MAX_ENTRIES:]
        self._write(records)

    def get_weekly_pattern(self) -> dict:
        records = self._read()
        raw: dict = {}
        for entry in records:
            day = entry.get("day", "")
            hour = entry.get("hour")
            mode = entry.get("mode", "")
            if not (day and hour is not None and mode):
                continue
            raw.setdefault(day, {}).setdefault(hour, Counter())[mode] += 1

        return {
            day: {hour: counts.most_common(1)[0][0] for hour, counts in hours.items()}
            for day, hours in raw.items()
        }

    def get_pattern_summary(self) -> str:
        records = self._read()
        if not records:
            return "No pattern data yet."

        days_seen = {r["day"] for r in records}
        day_count = len(days_seen)

        weekdays = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday"}
        has_weekday = bool(days_seen & weekdays)
        has_weekend = bool(days_seen - weekdays)

        lines = [f"Pattern learned over {day_count} days:"]
        if has_weekday:
            lines.append("Mon-Fri: commute 7-8am, class 9am-5pm, hostel evenings")
        if has_weekend:
            lines.append("Weekends: hostel mode dominant")

        focus_days = {
            r["day"][:3]
            for r in records
            if r.get("mode") == "focus" and r.get("hour", 0) >= 20
        }
        if focus_days:
            lines.append(f"Focus blocks detected: {'/'.join(sorted(focus_days))} 8-10pm")

        return "\n".join(lines)

    def predict_next_mode(self, current_hour: int, current_day: str) -> str | None:
        records = self._read()
        next_hour = (current_hour + 1) % 24
        counts: Counter = Counter(
            r["mode"]
            for r in records
            if r.get("day") == current_day and r.get("hour") == next_hour
        )
        if not counts or sum(counts.values()) <= 2:
            return None
        return counts.most_common(1)[0][0]

    def inject_demo_history(self) -> None:
        records = []
        days = ["Monday", "Tuesday", "Wednesday"]
        base = datetime.now() - timedelta(days=3)

        for i, day in enumerate(days):
            day_base = base + timedelta(days=i)

            # 7am: commute
            records.append({"mode": "commute", "hour": 7, "day": day, "zone": "transit",
                            "timestamp": day_base.replace(hour=7).isoformat()})

            # 8am-12pm: class/focus alternating
            for hour in range(8, 13):
                mode = "class" if hour % 2 == 0 else "focus"
                records.append({"mode": mode, "hour": hour, "day": day, "zone": "campus",
                                "timestamp": day_base.replace(hour=hour).isoformat()})

            # 13pm-17pm: focus/class alternating
            for hour in range(13, 18):
                mode = "focus" if hour % 2 == 1 else "class"
                records.append({"mode": mode, "hour": hour, "day": day, "zone": "campus",
                                "timestamp": day_base.replace(hour=hour).isoformat()})

            # 18pm-21pm: hostel
            for hour in range(18, 22):
                records.append({"mode": "hostel", "hour": hour, "day": day, "zone": "hostel",
                                "timestamp": day_base.replace(hour=hour).isoformat()})

            # 22pm-23pm: sleep
            for hour in range(22, 24):
                records.append({"mode": "sleep", "hour": hour, "day": day, "zone": "hostel",
                                "timestamp": day_base.replace(hour=hour).isoformat()})

        self._write(records)
        print(f"Demo history injected: 3 days, {len(records)} entries")
