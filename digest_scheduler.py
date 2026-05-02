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
MEMORY_FILE = Path("lifeos_memory.json")


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
        from telegram_bot import send_digest, _TOKEN, _CHAT_ID

        digest = self.queue.get_digest()

        if digest["total_held"] == 0 and digest["total_passed"] == 0:
            import asyncio
            from telegram import Bot

            async def _empty():
                async with Bot(_TOKEN) as bot:
                    await bot.send_message(
                        chat_id=_CHAT_ID,
                        text="No notifications held since last digest."
                    )
            try:
                asyncio.run(_empty())
            except Exception as exc:
                logger.error("Empty digest send failed: %s", exc)
        else:
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
