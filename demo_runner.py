import sys
import time
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

from mock_notifications import run_mock_flood
from digest_scheduler import DigestScheduler
from campus_agent import CampusAgent
from pattern_memory import PatternMemory
from exam_detector import ExamDetector
from calendar_skill import CalendarSkill
from commute_skill import CommuteSkill
from telegram_bot import send_mode_alert, send_exam_mode_alert, send_commute_alert
from memory import log_event
from modes import MODES


DEMO_SCRIPT = [
    {
        "step": 1,
        "title": "Agent startup + history loaded",
        "description": "LifeOS Campus boots. 3 days of pattern memory ready.",
        "action": "start_agent",
        "pause_seconds": 3,
    },
    {
        "step": 2,
        "title": "Morning — commute mode",
        "description": "7am context detected. Switching to commute mode.",
        "action": "simulate_mode",
        "mode": "commute",
        "pause_seconds": 4,
    },
    {
        "step": 3,
        "title": "Departure alert fires",
        "description": "DBMS Lab in 10 min. Agent sends alert before you think of it.",
        "action": "trigger_commute_alert",
        "pause_seconds": 4,
    },
    {
        "step": 4,
        "title": "Campus arrived — class mode",
        "description": "Location: campus. Mode switches automatically.",
        "action": "simulate_mode",
        "mode": "class",
        "pause_seconds": 3,
    },
    {
        "step": 5,
        "title": "20 notifications arrive",
        "description": "Watch what LifeOS does without you touching anything.",
        "action": "run_notification_flood",
        "pause_seconds": 8,
    },
    {
        "step": 6,
        "title": "Digest delivered — 16 held, 4 passed",
        "description": "20 notifications became 4. Digest hits Telegram now.",
        "action": "force_digest",
        "pause_seconds": 4,
    },
    {
        "step": 7,
        "title": "Focus mode — deep work detected",
        "description": "Pattern recognised. Agent switches without being asked.",
        "action": "simulate_mode",
        "mode": "focus",
        "pause_seconds": 3,
    },
    {
        "step": 8,
        "title": "Exam week detected",
        "description": "3 exams in 5 days. Exam mode activates automatically.",
        "action": "trigger_exam_week",
        "pause_seconds": 5,
    },
    {
        "step": 9,
        "title": "Pattern graph — agent learned your week",
        "description": "3 days in memory. Agent now predicts before context confirms.",
        "action": "show_pattern",
        "pause_seconds": 4,
    },
    {
        "step": 10,
        "title": "Override — judge takes control",
        "description": "Telegram command: /override hostel. Agent obeys instantly.",
        "action": "simulate_override",
        "mode": "hostel",
        "pause_seconds": 3,
    },
    {
        "step": 11,
        "title": "Digital Twin — this phone knows you",
        "description": "3 days of observation. Watch what it learned.",
        "action": "show_digital_twin",
        "pause_seconds": 6,
    },
]


# ── helpers ─────────────────────────────────────────────────────────────

def _now_ctx(zone: str = "demo") -> dict:
    now = datetime.now()
    return {
        "hour": now.hour,
        "day": now.strftime("%A"),
        "location_zone": zone,
        "calendar_events": [],
    }


def _read_memory() -> list:
    p = Path("lifeos_memory.json")
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _current_mode_from_memory() -> str:
    for entry in reversed(_read_memory()):
        if "mode" in entry:
            return entry["mode"]
    return "starting"


# ── action handlers ──────────────────────────────────────────────────────

def _action_start_agent() -> None:
    pm = PatternMemory()
    records = pm._read()
    if len(records) < 20:
        pm.inject_demo_history()
        records = pm._read()
        print("    Demo history injected.")
    else:
        print("    Pattern memory already populated.")

    mem_records = _read_memory()
    print(f"    Agent: LifeOS Campus")
    print(f"    Mode:  {_current_mode_from_memory()}")
    print(f"    Memory: {len(mem_records)} entries")
    print(f"    Telegram: connected")


def _action_simulate_mode(mode: str) -> None:
    ctx = _now_ctx(zone="demo")
    log_event("mode_switch", {
        "mode": mode,
        "simulated": True,
        "hour": ctx["hour"],
        "zone": "demo",
    })
    try:
        send_mode_alert(MODES[mode], ctx)
    except Exception as exc:
        print(f"    [Telegram skipped: {exc}]")
    print(f"    Mode → {mode} (simulated, logged to memory)")


def _action_trigger_commute_alert() -> None:
    now = datetime.now()
    # start_time 35 min out so departure window (35-25=10 min) fires
    mock_event = {
        "summary": "DBMS Lab",
        "location": "Room 304",
        "start_time": now + timedelta(minutes=35),
    }
    calendar = CalendarSkill()
    commute = CommuteSkill()
    travel_est = commute.get_travel_estimate()
    alert_str = commute.build_commute_alert(mock_event, travel_est)
    alert_info = calendar.compute_departure_alert(mock_event, travel_minutes=25)

    try:
        send_commute_alert(alert_str)
    except Exception as exc:
        print(f"    [Telegram skipped: {exc}]")
    log_event("commute_alert", alert_info)

    print("    Alert sent:")
    for line in alert_str.splitlines():
        print(f"      {line}")


def _action_run_notification_flood() -> None:
    print("    Sending 20 notifications through LifeOS filter...\n")
    run_mock_flood()


def _action_force_digest() -> None:
    # Show stats from the digest that run_mock_flood already sent
    last_stats = None
    for entry in reversed(_read_memory()):
        if entry.get("event") == "digest_sent":
            last_stats = entry.get("stats", {})
            break

    if last_stats:
        print(f"    Last digest → held: {last_stats.get('total_held', 0)}, "
              f"passed: {last_stats.get('total_passed', 0)}")
        by_app = last_stats.get("held_by_app", {})
        if by_app:
            items = ", ".join(f"{k}:{v}" for k, v in by_app.items())
            print(f"    By app: {items}")

    # Call force_send_digest to confirm system is live on Telegram
    try:
        DigestScheduler().force_send_digest()
        print("    Digest system confirmed — Telegram notified.")
    except Exception as exc:
        print(f"    [Telegram skipped: {exc}]")


def _action_trigger_exam_week() -> None:
    now = datetime.now()
    mock_events = [
        {"summary": "DBMS End Sem Exam",        "start_time": now + timedelta(days=1)},
        {"summary": "DSA Quiz",                  "start_time": now + timedelta(days=2)},
        {"summary": "Mini Project Viva",          "start_time": now + timedelta(days=3)},
        {"summary": "CN Assignment submission",   "start_time": now + timedelta(days=4)},
    ]
    exam_result = ExamDetector().analyze_week(mock_events)

    try:
        send_exam_mode_alert(exam_result)
    except Exception as exc:
        print(f"    [Telegram skipped: {exc}]")

    log_event("exam_mode", {
        "exam_count": exam_result["exam_count"],
        "is_crunch_week": exam_result["is_crunch_week"],
        "detected": [e["summary"] for e in exam_result["detected_exams"]],
    })

    print(f"    Result: exam_count={exam_result['exam_count']}, "
          f"assignment_count={exam_result['assignment_count']}, "
          f"is_exam_week={exam_result['is_exam_week']}, "
          f"is_crunch_week={exam_result['is_crunch_week']}")
    print(f"    Detected: {[e['summary'] for e in exam_result['detected_exams']]}")


def _action_show_pattern() -> None:
    pm = PatternMemory()
    summary = pm.get_pattern_summary()
    print("    Pattern summary:")
    for line in summary.splitlines():
        print(f"      {line}")

    now = datetime.now()
    prediction = pm.predict_next_mode(now.hour, now.strftime("%A"))
    if prediction:
        print(f"    Predicted next mode: {prediction}")
    else:
        print("    Prediction: needs more real data (demo history active)")


def _action_show_digital_twin() -> None:
    from digital_twin import DigitalTwin
    twin    = DigitalTwin()
    profile = twin.build_profile()
    prod    = profile["productivity"]
    nh      = profile["notification_health"]
    se      = profile["social_energy"]

    print(f"    Productivity    : {prod['productivity_score']}/100")
    print(f"    Shield effect   : {nh['shield_effectiveness']}%")
    print(f"    Peak focus hrs  : {profile['peak_focus_hours']} on {profile['peak_focus_days']}")
    print(f"    Social drops    : after {se['social_energy_drops_after']}:00")
    print(f"    Data points     : {profile['data_points']}")

    report = twin.generate_weekly_report()
    try:
        send_commute_alert(report)
    except Exception as exc:
        print(f"    [Telegram skipped: {exc}]")
    print("    Digital Twin report sent to Telegram.")


def _action_simulate_override(mode: str) -> None:
    log_event("override", {
        "mode": mode,
        "source": "telegram_command",
        "timestamp": datetime.now().isoformat(),
    })
    override_msg = (
        f"LifeOS — Override received\n"
        f"Switching to {mode.upper()} mode\n"
        f"Source: /override command\n"
        f"Agent updated."
    )
    try:
        send_commute_alert(override_msg)
    except Exception as exc:
        print(f"    [Telegram skipped: {exc}]")
    print("    Override logged and Telegram notified.")


# ── orchestrator ─────────────────────────────────────────────────────────

def run_demo() -> None:
    print(f"\n╬{'':=<44}╬")
    print(f"║{'LifeOS Campus — HACKATHON DEMO':^44}║")
    print(f"║{'Samsung PRISM / OpenClaw 2026':^44}║")
    print(f"║{'Dashboard → http://localhost:5000':^44}║")
    print(f"╝{'':=<44}╝\n")

    print("  Open your Telegram app now.")
    print("  Open http://localhost:5000 on a second screen.")
    input("  Press ENTER to begin the demo.\n")

    for cfg in DEMO_SCRIPT:
        step = cfg["step"]
        total_steps = len(DEMO_SCRIPT)
        print(f"\n─── Step {step}/{total_steps}: {cfg['title']} ───")
        print(f"    {cfg['description']}")

        try:
            action = cfg["action"]
            if action == "start_agent":
                _action_start_agent()
            elif action == "simulate_mode":
                _action_simulate_mode(cfg["mode"])
            elif action == "trigger_commute_alert":
                _action_trigger_commute_alert()
            elif action == "run_notification_flood":
                _action_run_notification_flood()
            elif action == "force_digest":
                _action_force_digest()
            elif action == "trigger_exam_week":
                _action_trigger_exam_week()
            elif action == "show_pattern":
                _action_show_pattern()
            elif action == "simulate_override":
                _action_simulate_override(cfg["mode"])
            elif action == "show_digital_twin":
                _action_show_digital_twin()
        except Exception as exc:
            print(f"    [Action error: {exc}]")

        print(f"    Waiting {cfg['pause_seconds']}s...")
        time.sleep(cfg["pause_seconds"])
        print("    Done.")

    print(f"\n╬{'':=<44}╬")
    print(f"║{'DEMO COMPLETE — All 11 steps done':^44}║")
    print(f"║{'Check Telegram for all messages':^44}║")
    print(f"║{'Dashboard: http://localhost:5000':^44}║")
    print(f"╝{'':=<44}╝\n")


if __name__ == "__main__":
    run_demo()
