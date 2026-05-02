import sys
import os
import json
import logging
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

from dotenv import load_dotenv
load_dotenv()

from pattern_memory import PatternMemory
from telegram_bot import send_commute_alert

SEP = "=" * 40

_ENV_CHECKS = [
    ("TELEGRAM_TOKEN",      True,  "TELEGRAM_TOKEN"),
    ("TELEGRAM_CHAT_ID",    True,  "TELEGRAM_CHAT_ID"),
    ("GOOGLE_CALENDAR_KEY", False, "GOOGLE_CALENDAR_KEY"),
    ("GOOGLE_MAPS_KEY",     False, "GOOGLE_MAPS_KEY"),
    ("DEMO_MODE",           False, "DEMO_MODE"),
]

_JSON_CHECKS = [
    ("lifeos_memory.json",  "lifeos_memory.json",  "list"),
    ("notif_queue.json",    "notif_queue.json",    "dict"),
    ("pattern_memory.json", "pattern_memory.json", "list"),
]


def _check_env() -> list:
    missing = []
    print(f"\n  ENV KEYS")
    print(f"  {'-'*36}")
    for key, critical, label in _ENV_CHECKS:
        val = os.getenv(key)
        if val:
            display = val if key == "DEMO_MODE" else "found"
            suffix = ""
            print(f"  {label:<26} → {display}{suffix}")
        else:
            if critical:
                print(f"  {label:<26} → MISSING  (demo will fail)")
                missing.append(label)
            elif key in ("GOOGLE_CALENDAR_KEY", "GOOGLE_MAPS_KEY"):
                print(f"  {label:<26} → running in mock mode")
            else:
                print(f"  {label:<26} → false")
    return missing


def _check_files() -> None:
    print(f"\n  JSON FILES")
    print(f"  {'-'*36}")
    for label, fname, kind in _JSON_CHECKS:
        p = Path(fname)
        if not p.exists():
            print(f"  {label:<26} → missing (will be created)")
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if kind == "list":
                n = len(data) if isinstance(data, list) else 0
                status = f"{n} entries" if n > 0 else "empty"
            else:
                held = len(data.get("held", [])) if isinstance(data, dict) else 0
                status = f"{held} items queued" if held > 0 else "empty"
            print(f"  {label:<26} → {status}")
        except Exception:
            print(f"  {label:<26} → unreadable")


def _inject_pattern_if_needed() -> None:
    pm = PatternMemory()
    records = pm._read()
    if len(records) < 20:
        pm.inject_demo_history()
        print("\n  Demo history injected automatically.")


def _clear_notif_queue() -> None:
    p = Path("notif_queue.json")
    p.write_text(
        json.dumps({"held": [], "passed_through": []}, indent=2),
        encoding="utf-8",
    )
    print("  Notification queue cleared for fresh demo.")


def run_setup() -> None:
    print(f"\n{SEP}")
    print("  LifeOS Campus — Pre-Demo Setup Check")
    print(f"{SEP}")

    missing = _check_env()
    _check_files()
    _inject_pattern_if_needed()
    _clear_notif_queue()

    # Telegram setup confirmation
    setup_msg = (
        "LifeOS Campus — Demo Setup Complete\n"
        + "━" * 20 + "\n"
        "All systems checked.\n"
        "Dashboard  : http://localhost:5000\n"
        "Demo runner: python demo_runner.py\n"
        "\n"
        "Checklist:\n"
        "· Telegram open on your phone\n"
        "· Dashboard open on second screen\n"
        "· Screen timeout set to Never\n"
        "· Device name: Galaxy LifeOS Preview\n"
        "\n"
        "Ready when you are."
    )
    try:
        send_commute_alert(setup_msg)
        print("  Telegram: setup confirmation sent.")
    except Exception as exc:
        print(f"  Telegram: skipped ({exc})")

    # Device checklist
    print(f"\n{SEP}")
    print("  DEVICE SETUP CHECKLIST")
    print(f"{SEP}")
    print("  1. Rename device to: Galaxy LifeOS Preview")
    print("     Settings > About Phone > Device Name")
    print("  2. Open Telegram on your phone — keep it visible")
    print("  3. Open http://localhost:5000 on a second screen")
    print("  4. Set screen timeout to Never")
    print("  5. Run: python demo_runner.py")
    print("")
    print("  If anything is MISSING above, fix it before")
    print("  running the demo.")
    print(f"{SEP}\n")

    if missing:
        print(f"  WARNING: Fix MISSING items in .env before demo.")
        print(f"  Missing: {', '.join(missing)}")
        sys.exit(1)
    else:
        print("  All systems green. You are demo-ready.")


if __name__ == "__main__":
    run_setup()
