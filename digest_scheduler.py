import os
import json
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from notification_queue import NotificationQueue

load_dotenv()
logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
DIGEST_HOURS = [9, 13, 18]
BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "lifeos_memory.json"


class DigestScheduler:
    def __init__(self):
        self.queue = NotificationQueue()
        self.last_digest_hour: int | None = None

    def check_and_send_digest(self, current_hour: int) -> None:
        if DEMO_MODE:
            return
        if current_hour in DIGEST_HOURS and current_hour != self.last_digest_hour:
            self.force_send_digest()
            self.last_digest_hour = current_hour

    def force_send_digest(self) -> None:
        from telegram_bot import send_digest

        digest = self.queue.get_digest()
        send_digest(digest)
        self._log(digest)

    def _log(self, digest: dict) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "digest_sent",
            "stats": {
                "total_held": digest["total_held"],
                "total_passed": digest["total_passed"],
                "held_by_app": digest["held_by_app"],
            },
        }
        records: list = []
        if MEMORY_FILE.exists():
            try:
                records = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        records.append(entry)
        MEMORY_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
        logger.info("Digest logged to lifeos_memory.json")
