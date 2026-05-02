import os
import asyncio
import logging
from datetime import datetime

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
logger = logging.getLogger(__name__)

_TOKEN = os.getenv("TELEGRAM_TOKEN")
_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

_SOUND_EMOJI = {"silent": "🔇", "low": "🔉", "normal": "🔊"}


def send_mode_alert(mode, ctx: dict) -> None:
    if not _TOKEN or not _CHAT_ID:
        logger.warning("TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not configured — skipping alert")
        return

    sound_icon = _SOUND_EMOJI.get(mode.sound, "🔊")
    text = (
        f"*LifeOS — Mode Switch*\n"
        f"Mode: *{mode.name.upper()}*\n"
        f"DND: {'ON' if mode.dnd else 'OFF'}  |  Sound: {sound_icon} {mode.sound}\n"
        f"Notif threshold: {mode.notif_score_threshold}/10\n"
        f"Time: {ctx['hour']:02d}:xx  |  Zone: {ctx['location_zone']}  |  {ctx['day']}"
    )

    async def _send() -> None:
        async with Bot(_TOKEN) as bot:
            await bot.send_message(chat_id=_CHAT_ID, text=text, parse_mode="Markdown")

    try:
        asyncio.run(_send())
    except Exception as exc:
        logger.error("Telegram send failed: %s", exc)


def send_urgent_alert(notif: dict, score: int) -> None:
    if not _TOKEN or not _CHAT_ID:
        return

    text = (
        f"URGENT — {notif['sender']} via {notif['app']}\n"
        f"Score: {score}/10\n"
        f"Preview: {notif['message_preview']}"
    )

    async def _send() -> None:
        async with Bot(_TOKEN) as bot:
            await bot.send_message(chat_id=_CHAT_ID, text=text)

    try:
        asyncio.run(_send())
    except Exception as exc:
        logger.error("Urgent alert send failed: %s", exc)


def send_digest(digest_data: dict) -> None:
    if not _TOKEN or not _CHAT_ID:
        logger.warning("TELEGRAM credentials not configured — skipping digest")
        return

    total_held = digest_data["total_held"]
    total_passed = digest_data["total_passed"]
    held_by_app = digest_data.get("held_by_app", {})
    passed_through = digest_data.get("passed_through", [])

    lines = [
        "LifeOS — Notification Digest",
        "━" * 20,
        f"Held: {total_held} notifications",
        f"Passed through: {total_passed} (urgent)",
        "",
        "Held breakdown:",
    ]
    for app, count in held_by_app.items():
        lines.append(f"· {app.capitalize()} — {count}")

    lines += ["", "Urgent delivered instantly:"]
    for n in passed_through:
        try:
            ts = datetime.fromisoformat(n.get("queued_at", ""))
            time_str = ts.strftime("%H:%M")
        except Exception:
            time_str = "--:--"
        lines.append(f"· {n['sender']} via {n['app']} — score {n['score']}/10 at {time_str}")

    lines += ["", "━" * 20, "Next digest in: demo mode (instant)"]

    text = "\n".join(lines)

    async def _send() -> None:
        async with Bot(_TOKEN) as bot:
            await bot.send_message(chat_id=_CHAT_ID, text=text)

    try:
        asyncio.run(_send())
        logger.info("Digest sent to Telegram")
    except Exception as exc:
        logger.error("Digest send failed: %s", exc)


def send_phase2_status(stats: dict) -> None:
    if not _TOKEN or not _CHAT_ID:
        return

    text = (f"LifeOS shield active — "
            f"{stats['held_count']} held, {stats['passed_count']} delivered")

    async def _send() -> None:
        async with Bot(_TOKEN) as bot:
            await bot.send_message(chat_id=_CHAT_ID, text=text)

    try:
        asyncio.run(_send())
    except Exception as exc:
        logger.error("Phase2 status send failed: %s", exc)


def send_commute_alert(alert_str: str) -> None:
    if not _TOKEN or not _CHAT_ID:
        logger.warning("TELEGRAM credentials not configured — skipping commute alert")
        return

    async def _send() -> None:
        async with Bot(_TOKEN) as bot:
            await bot.send_message(chat_id=_CHAT_ID, text=alert_str)

    try:
        asyncio.run(_send())
        logger.info("Commute alert sent to Telegram")
    except Exception as exc:
        logger.error("Commute alert send failed: %s", exc)


def send_exam_mode_alert(exam_data: dict) -> None:
    if not _TOKEN or not _CHAT_ID:
        logger.warning("TELEGRAM credentials not configured — skipping exam alert")
        return

    exam_count = exam_data.get("exam_count", 0)
    detected_exams = exam_data.get("detected_exams", [])

    lines = [
        "LifeOS — Exam Week Detected",
        "━" * 20,
        f"{exam_count} exams detected in next 5 days:",
    ]
    for event in detected_exams:
        if isinstance(event, dict):
            summary = event.get("summary", "Unknown")
            start = event.get("start_time")
            day_str = start.strftime("%a") if hasattr(start, "strftime") else "?"
        else:
            summary = str(event)
            day_str = "?"
        lines.append(f"· {summary} — {day_str}")

    lines += [
        "",
        "Exam mode activated:",
        "· Only urgent notifications pass through",
        "· Focus block: 8pm-11pm daily",
        "· Social apps blocked",
        "· Sleep protection until 7am",
        "━" * 20,
        "You've got this.",
    ]

    text = "\n".join(lines)

    async def _send() -> None:
        async with Bot(_TOKEN) as bot:
            await bot.send_message(chat_id=_CHAT_ID, text=text)

    try:
        asyncio.run(_send())
        logger.info("Exam mode alert sent to Telegram")
    except Exception as exc:
        logger.error("Exam mode alert send failed: %s", exc)
