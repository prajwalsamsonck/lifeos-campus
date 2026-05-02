import time
import logging

from context import get_context
from modes import get_mode
from telegram_bot import send_mode_alert
from memory import log_mode_switch
from digest_scheduler import DigestScheduler
from notification_queue import NotificationQueue
from campus_agent import CampusAgent
from pattern_memory import PatternMemory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

INTERVAL = 10  # seconds — fast for demo; set to 60 for production


def run():
    current_mode_name: str | None = None
    scheduler = DigestScheduler()
    queue = NotificationQueue()
    campus_agent = CampusAgent()
    tick = 0
    logger.info("LifeOS Campus heartbeat started (interval=%ds)", INTERVAL)

    while True:
        ctx = get_context()
        mode = get_mode(ctx)

        scheduler.check_and_send_digest(ctx["hour"])

        if mode.name != current_mode_name:
            logger.info("Mode switch: %s → %s  (zone=%s, hour=%02d:xx, day=%s)",
                        current_mode_name or "none", mode.name,
                        ctx["location_zone"], ctx["hour"], ctx["day"])
            current_mode_name = mode.name
            send_mode_alert(mode, ctx)
            log_mode_switch(mode, ctx)
            PatternMemory().log_mode_event(mode.name, ctx["hour"], ctx["day"], ctx["location_zone"])
        else:
            logger.debug("Mode stable: %s", mode.name)

        campus_agent.run_campus_check(ctx)

        tick += 1
        if tick % 5 == 0:
            stats = queue.get_stats()
            logger.info("Shield stats — held: %d | passed: %d | top held: %s",
                        stats["held_count"], stats["passed_count"], stats["top_held_app"])

        time.sleep(INTERVAL)
