import sys
import logging
from datetime import datetime

# Force UTF-8 output so box-drawing characters render correctly on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from notification_scorer import NotificationScorer
from notification_queue import NotificationQueue
from digest_scheduler import DigestScheduler
from telegram_bot import send_urgent_alert

logging.basicConfig(
    level=logging.WARNING,  # suppress info noise during demo table print
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)

_now = datetime.now().isoformat()

MOCK_NOTIFICATIONS = [
    {"sender": "mom",          "app": "whatsapp",  "message_preview": "Beta kha liya?",           "timestamp": _now},
    {"sender": "Instagram",    "app": "instagram",  "message_preview": "3 people liked your post",  "timestamp": _now},
    {"sender": "Prof. Sharma", "app": "gmail",      "message_preview": "DBMS assignment due tmrw",  "timestamp": _now},
    {"sender": "Swiggy",       "app": "swiggy",     "message_preview": "Your order is on the way",  "timestamp": _now},
    {"sender": "Rahul",        "app": "whatsapp",   "message_preview": "bro coming to canteen?",    "timestamp": _now},
    {"sender": "YouTube",      "app": "youtube",    "message_preview": "New video from Fireship",   "timestamp": _now},
    {"sender": "Moodle",       "app": "moodle",     "message_preview": "Quiz opens in 1 hour",      "timestamp": _now},
    {"sender": "Instagram",    "app": "instagram",  "message_preview": "Someone mentioned you",     "timestamp": _now},
    {"sender": "Zomato",       "app": "zomato",     "message_preview": "50% off on your fav rest",  "timestamp": _now},
    {"sender": "dad",          "app": "sms",        "message_preview": "Call me when free",         "timestamp": _now},
    {"sender": "Priya",        "app": "whatsapp",   "message_preview": "notes share kar na",        "timestamp": _now},
    {"sender": "Netflix",      "app": "netflix",    "message_preview": "Continue watching?",        "timestamp": _now},
    {"sender": "HOD Office",   "app": "gmail",      "message_preview": "Attendance shortage notice","timestamp": _now},
    {"sender": "YouTube",      "app": "youtube",    "message_preview": "Top 10 DSA problems",       "timestamp": _now},
    {"sender": "Snapchat",     "app": "snapchat",   "message_preview": "Ananya sent you a snap",    "timestamp": _now},
    {"sender": "Paytm",        "app": "paytm",      "message_preview": "Cashback credited Rs.50",   "timestamp": _now},
    {"sender": "Arjun",        "app": "whatsapp",   "message_preview": "exam postponed bro!!",      "timestamp": _now},
    {"sender": "Instagram",    "app": "instagram",  "message_preview": "5 new followers today",     "timestamp": _now},
    {"sender": "College ERP",  "app": "gmail",      "message_preview": "Timetable updated",         "timestamp": _now},
    {"sender": "mom",          "app": "sms",        "message_preview": "Call karo jaldi",           "timestamp": _now},
]


def run_mock_flood() -> None:
    scorer = NotificationScorer()
    queue = NotificationQueue()
    scheduler = DigestScheduler()

    MODE = "class"
    COL = {"sender": 15, "app": 10, "score": 5}

    header = (f"{'Sender':<{COL['sender']}} | {'App':<{COL['app']}} | "
              f"{'Score':^{COL['score']}} | Action")
    divider = "─" * (len(header) + 2)

    print(f"\n  Simulating notification flood — mode locked to: {MODE.upper()}\n")
    print(f"  {header}")
    print(f"  {divider}")

    passed_count = 0
    held_count = 0

    for notif in MOCK_NOTIFICATIONS:
        score = scorer.score_notification(notif, mode_name=MODE)
        tier = scorer.get_urgency_tier(notif["sender"])
        result = queue.add(notif, score)
        action = result["action"]

        if action == "pass_through":
            send_urgent_alert(notif, score)
            passed_count += 1
            label = f"PASS THROUGH{' (tier1)' if tier == 'tier1' else ''}"
        else:
            held_count += 1
            label = "HELD"

        row = (f"  {notif['sender']:<{COL['sender']}} | "
               f"{notif['app']:<{COL['app']}} | "
               f"{score:^{COL['score']}} | {label}")
        print(row)

    print(f"  {divider}\n")
    print("  Sending digest to Telegram...\n")
    scheduler.force_send_digest()

    print("  " + "═" * 38)
    print("  PHASE 2 DEMO COMPLETE")
    print("  " + "═" * 38)
    print(f"  Total notifications : {len(MOCK_NOTIFICATIONS)}")
    print(f"  Passed through      : {passed_count}  (urgent/high score)")
    print(f"  Held for digest     : {held_count}")
    print(f"  Digest sent to      : Telegram")
    print(f"  notif_queue.json    : cleared")
    print("  " + "═" * 38 + "\n")


if __name__ == "__main__":
    run_mock_flood()
