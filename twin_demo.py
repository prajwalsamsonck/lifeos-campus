import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

from digital_twin import DigitalTwin
from pattern_memory import PatternMemory
from telegram_bot import send_commute_alert

SEP  = "=" * 36
THIN = "-" * 26

MEMORY_FILE = Path("lifeos_memory.json")


def _inject_synthetic_history() -> None:
    records = []
    if MEMORY_FILE.exists():
        try:
            records = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Only inject if we don't already have enough synthetic digest data
    if sum(1 for e in records if e.get("event") == "digest_sent") >= 3:
        return

    base = datetime.now() - timedelta(days=3)

    # 3 digest entries (Mon / Tue / Wed)
    digest_data = [
        {
            "day": "Monday",
            "held": 14, "passed": 4,
            "held_by_app": {"instagram": 4, "youtube": 3, "snapchat": 2, "swiggy": 2, "netflix": 2, "paytm": 1},
        },
        {
            "day": "Tuesday",
            "held": 11, "passed": 6,
            "held_by_app": {"youtube": 4, "instagram": 3, "snapchat": 2, "zomato": 2},
        },
        {
            "day": "Wednesday",
            "held": 16, "passed": 3,
            "held_by_app": {"snapchat": 5, "instagram": 4, "youtube": 3, "swiggy": 2, "netflix": 2},
        },
    ]
    for i, d in enumerate(digest_data):
        ts = (base + timedelta(days=i)).replace(hour=13, minute=0, second=0, microsecond=0).isoformat()
        records.append({
            "timestamp": ts,
            "event": "digest_sent",
            "stats": {
                "total_held":   d["held"],
                "total_passed": d["passed"],
                "held_by_app":  d["held_by_app"],
            },
        })

    # 3 stress signal entries — mode switches at 11pm on Mon/Tue/Wed
    for i in range(3):
        ts = (base + timedelta(days=i)).replace(hour=23, minute=0, second=0, microsecond=0).isoformat()
        records.append({
            "timestamp": ts,
            "mode": "focus",
            "dnd": True,
            "sound": "low",
            "notif_score_threshold": 7,
            "context": {
                "hour": 23,
                "day": ["Monday", "Tuesday", "Wednesday"][i],
                "location_zone": "hostel",
                "calendar_events": [],
            },
        })

    # 2 exam_mode entries
    for i in range(2):
        ts = (base + timedelta(days=i)).replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
        records.append({
            "event_type": "exam_mode",
            "data": {
                "exam_count": 3,
                "is_crunch_week": True,
                "detected": ["DBMS End Sem Exam", "DSA Quiz", "Mini Project Viva"],
            },
            "timestamp": ts,
        })

    MEMORY_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print("    Synthetic history injected for demo.")


def run_twin_demo() -> None:
    print(f"\n{SEP}")
    print("  DIGITAL TWIN — LifeOS Campus")
    print("  Building your personal model...")
    print(f"{SEP}\n")

    # ── Step 1: Ensure demo data ──────────────────────────────────────────
    print("  [Step 1] Checking demo data...")
    pm = PatternMemory()
    pattern_records = pm._read()
    if len(pattern_records) < 20:
        pm.inject_demo_history()
        print("    Pattern history injected.")
    else:
        print(f"    Pattern memory OK — {len(pattern_records)} entries.")
    _inject_synthetic_history()

    # ── Step 2: Build profile ─────────────────────────────────────────────
    print("\n  [Step 2] Building Digital Twin profile...")
    twin    = DigitalTwin()
    profile = twin.build_profile()
    prod    = profile["productivity"]
    nh      = profile["notification_health"]
    se      = profile["social_energy"]
    ss      = profile["stress_signals"]

    pfh      = profile["peak_focus_hours"]
    pfd      = profile["peak_focus_days"]
    hour_str = f"{pfh[0]}-{pfh[-1]+1}:00" if len(pfh) >= 2 else (f"{pfh[0]}:00" if pfh else "TBD")

    print(f"\n  {THIN}")
    print(f"  DIGITAL TWIN PROFILE")
    print(f"  {THIN}")
    print(f"  Peak focus    : {pfd} at {hour_str}")
    print(f"  Productivity  : {prod['productivity_score']}/100")
    print(f"  Social energy : drops after {se['social_energy_drops_after']}:00")
    print(f"  Introvert score: {se['introvert_score']}/100")
    print(f"  Stress signals: {ss['stress_days']}")
    print(f"  Shield effect : {nh['shield_effectiveness']}%")
    print(f"  Most disruptive: {nh['most_disruptive_app']}")
    print(f"  Data points   : {profile['data_points']}")
    print(f"  {THIN}")

    # ── Step 3: Insights ─────────────────────────────────────────────────
    print("\n  [Step 3] Generating insights...")
    insights = twin.generate_insights()
    for i, ins in enumerate(insights, 1):
        print(f"    {i}. {ins}")

    # ── Step 4: Weekly report to Telegram ────────────────────────────────
    print("\n  [Step 4] Sending weekly report to Telegram...")
    report = twin.generate_weekly_report()
    try:
        send_commute_alert(report)
        print("    Weekly report sent to Telegram.")
    except Exception as exc:
        print(f"    [Telegram skipped: {exc}]")

    # ── Step 5: Twin card ─────────────────────────────────────────────────
    print("\n  [Step 5] Twin card (dashboard snapshot)...")
    card = twin.get_twin_card()
    print(f"    Productivity    : {card['productivity_score']}/100")
    print(f"    Shield effect   : {card['shield_effectiveness']}%")
    print(f"    Peak focus      : {card['peak_focus']}")
    print(f"    Stress level    : {card['stress_level']}")
    print(f"    Introvert score : {card['introvert_score']}/100")
    print(f"    Data points     : {card['data_points']}")
    print(f"    Top insight     :")
    for line in card['top_insight'].splitlines():
        print(f"      {line}")

    # ── Footer ────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  DIGITAL TWIN COMPLETE")
    print("  This model grows more accurate every day.")
    print("  Every heartbeat tick adds a data point.")
    print("  Every notification decision teaches it.")
    print("  Every mode switch refines it.")
    print("  This is the real product.")
    print(f"{SEP}\n")


if __name__ == "__main__":
    run_twin_demo()
