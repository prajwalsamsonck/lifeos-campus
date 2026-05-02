import json
import logging
from datetime import datetime
from pathlib import Path

from notification_scorer import NotificationScorer

QUEUE_FILE = Path("notif_queue.json")
logger = logging.getLogger(__name__)
_scorer = NotificationScorer()


class NotificationQueue:
    def _read(self) -> dict:
        if not QUEUE_FILE.exists():
            return {"held": [], "passed_through": []}
        try:
            raw = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return {"held": raw, "passed_through": []}
            return raw
        except (json.JSONDecodeError, OSError):
            return {"held": [], "passed_through": []}

    def _write(self, data: dict) -> None:
        QUEUE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add(self, notification: dict, score: int) -> dict:
        tier = _scorer.get_urgency_tier(notification.get("sender", ""))
        entry = {
            **notification,
            "score": score,
            "tier": tier,
            "queued_at": datetime.now().isoformat(),
        }

        data = self._read()
        if tier == "tier1" or score >= 7:
            action = "pass_through"
            data["passed_through"].append(entry)
        else:
            action = "held"
            data["held"].append(entry)
        self._write(data)
        return {"action": action, "score": score}

    def get_digest(self) -> dict:
        data = self._read()
        held = data.get("held", [])
        passed = data.get("passed_through", [])

        held_by_app: dict = {}
        for n in held:
            app = n.get("app", "unknown")
            held_by_app[app] = held_by_app.get(app, 0) + 1

        self._write({"held": [], "passed_through": []})
        return {
            "held": held,
            "held_by_app": held_by_app,
            "passed_through": passed,
            "total_held": len(held),
            "total_passed": len(passed),
        }

    def get_stats(self) -> dict:
        data = self._read()
        held = data.get("held", [])
        passed = data.get("passed_through", [])

        held_by_app: dict = {}
        for n in held:
            app = n.get("app", "unknown")
            held_by_app[app] = held_by_app.get(app, 0) + 1

        top_app = max(held_by_app, key=held_by_app.get) if held_by_app else "none"
        return {
            "held_count": len(held),
            "passed_count": len(passed),
            "top_held_app": top_app,
        }
