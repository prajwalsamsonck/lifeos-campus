import json
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "lifeos_memory.json"
logger = logging.getLogger(__name__)


def log_mode_switch(mode, ctx: dict) -> None:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode.name,
        "dnd": mode.dnd,
        "sound": mode.sound,
        "notif_score_threshold": mode.notif_score_threshold,
        "context": ctx,
    }

    records: list = []
    if MEMORY_FILE.exists():
        try:
            records = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("lifeos_memory.json unreadable — starting fresh")

    records.append(entry)
    MEMORY_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
    logger.info("Logged mode switch → %s  (%s)", mode.name, entry["timestamp"])


def log_event(event_type: str, data: dict) -> None:
    entry = {
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat(),
    }
    records: list = []
    if MEMORY_FILE.exists():
        try:
            records = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    records.append(entry)
    MEMORY_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
    logger.info("Event logged: %s", event_type)
