#!/usr/bin/env python3
"""
OpenClaw Bridge — LifeOS Campus
Single entry point connecting OpenClaw skill execution
to the LifeOS Campus Python intelligence layer.
All existing Phase 1-5 code invoked through here.
"""

import sys
import os
import asyncio
import argparse
import json
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

_TOKEN = os.getenv("TELEGRAM_TOKEN")
_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def _send_telegram(text: str) -> None:
    if not _TOKEN or not _CHAT_ID:
        print("[Bridge] Telegram not configured — skipping send")
        return
    from telegram import Bot

    async def _send():
        async with Bot(_TOKEN) as bot:
            await bot.send_message(chat_id=_CHAT_ID, text=text)

    try:
        asyncio.run(_send())
    except Exception as exc:
        print(f"[Bridge] Telegram send failed: {exc}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='LifeOS Campus — OpenClaw Bridge'
    )
    parser.add_argument('--tick',
        action='store_true',
        help='Run HEARTBEAT tick')
    parser.add_argument('--check-commute',
        action='store_true',
        help='Check commute alerts')
    parser.add_argument('--check-digest',
        action='store_true',
        help='Check digest schedule')
    parser.add_argument('--update-twin',
        action='store_true',
        help='Update Digital Twin model')
    parser.add_argument('--generate-twin',
        action='store_true',
        help='Generate and send weekly twin report')
    parser.add_argument('--score-notification',
        action='store_true',
        help='Score an incoming notification')
    parser.add_argument('--override',
        type=str,
        help='Override current mode')
    parser.add_argument('--exam-mode',
        type=str,
        help='Set exam mode on/off')
    parser.add_argument('--sender', type=str, default='')
    parser.add_argument('--app', type=str, default='')
    parser.add_argument('--preview', type=str, default='')
    parser.add_argument('--hour', type=int,
        default=datetime.now().hour)
    parser.add_argument('--zone', type=str,
        default='unknown')
    args = parser.parse_args()

    try:
        if args.tick:
            handle_tick()

        elif args.check_commute:
            handle_commute_check(args.hour, args.zone)

        elif args.check_digest:
            handle_digest_check(args.hour)

        elif args.update_twin:
            handle_twin_update()

        elif args.generate_twin:
            handle_twin_report()

        elif args.score_notification:
            handle_notification(
                args.sender, args.app, args.preview)

        elif args.override:
            handle_override(args.override)

        elif args.exam_mode:
            handle_exam_mode(args.exam_mode)

        else:
            print("LifeOS Campus OpenClaw Bridge ready.")
            print("Run with --help for options.")

    except Exception as e:
        print(f"[Bridge Error] {e}", file=sys.stderr)
        sys.exit(1)


def handle_tick():
    from context import get_context
    from modes import get_mode
    from telegram_bot import send_mode_alert
    from memory import log_mode_switch
    from digest_scheduler import DigestScheduler
    from campus_agent import CampusAgent
    from pattern_memory import PatternMemory

    ctx = get_context()
    mode = get_mode(ctx)
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[Bridge] HEARTBEAT tick — {ts}")
    print(f"[Bridge] Mode: {mode.name} | Zone: {ctx['location_zone']} "
          f"| Hour: {ctx['hour']:02d}:xx | Day: {ctx['day']}")

    DigestScheduler().check_and_send_digest(ctx['hour'])
    CampusAgent().run_campus_check(ctx)
    PatternMemory().log_mode_event(
        mode.name, ctx['hour'], ctx['day'], ctx['location_zone'])
    print(f"[Bridge] Tick complete — mode={mode.name}")


def handle_commute_check(hour, zone):
    from campus_agent import CampusAgent
    from context import get_context
    ctx = get_context()
    agent = CampusAgent()
    result = agent.run_campus_check(ctx)
    result_str = json.dumps(result, default=str, indent=2)
    print(f"[Bridge] Campus check: {result_str}")


def handle_digest_check(hour):
    from digest_scheduler import DigestScheduler
    print(f"[Bridge] Digest check for hour {hour}")
    DigestScheduler().check_and_send_digest(hour)


def handle_twin_update():
    from pattern_memory import PatternMemory
    from context import get_context
    ctx = get_context()
    PatternMemory().log_mode_event(
        ctx.get('mode', 'unknown'),
        ctx['hour'],
        ctx['day'],
        ctx['location_zone']
    )
    print("[Bridge] Digital Twin updated with latest context")


def handle_twin_report():
    from digital_twin import DigitalTwin
    print("[Bridge] Generating Digital Twin report...")
    twin = DigitalTwin()
    report = twin.generate_weekly_report()
    _send_telegram(report)
    print("[Bridge] Report generated and sent to Telegram")


def handle_notification(sender, app, preview):
    from notification_scorer import NotificationScorer
    from notification_queue import NotificationQueue
    from context import get_context
    from modes import get_mode
    notif = {
        "sender": sender,
        "app": app,
        "message_preview": preview,
        "timestamp": datetime.now().isoformat()
    }
    ctx = get_context()
    mode = get_mode(ctx)
    scorer = NotificationScorer()
    score = scorer.score_notification(notif, mode.name)
    queue = NotificationQueue()
    result = queue.add(notif, score)
    print(f"[Bridge] Notification scored: {score}/10 "
          f"| Action: {result['action']}")
    if result['action'] == 'pass_through':
        from telegram_bot import send_urgent_alert
        send_urgent_alert(notif, score)


def handle_override(mode):
    valid = ['commute', 'class', 'focus', 'hostel', 'sleep']
    if mode.lower() not in valid:
        print(f"[Bridge] Invalid mode: {mode}. Valid: {valid}")
        return
    from memory import log_event
    log_event("override", {
        "mode": mode,
        "source": "openclaw_command",
        "timestamp": datetime.now().isoformat()
    })
    msg = (f"LifeOS — Override received\n"
           f"Switching to {mode.upper()} mode\n"
           f"Source: OpenClaw skill\n"
           f"Agent updated and learning.")
    _send_telegram(msg)
    print(f"[Bridge] Override to {mode} — logged and Telegram notified")


def handle_exam_mode(state):
    from memory import log_event
    log_event("exam_mode_manual", {
        "state": state,
        "source": "openclaw_command",
        "timestamp": datetime.now().isoformat()
    })
    if state.lower() == 'on':
        msg = ("Exam mode ON\n"
               "Cognitive Firewall at maximum\n"
               "Focus block: 8pm-11pm\n"
               "Social: blocked\n"
               "You've got this.")
    else:
        msg = ("Exam mode OFF\n"
               "Returning to normal protection\n"
               "Well done.")
    _send_telegram(msg)
    print(f"[Bridge] Exam mode {state} — logged and Telegram notified")


if __name__ == "__main__":
    main()
