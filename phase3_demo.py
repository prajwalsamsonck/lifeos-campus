import sys
import logging
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

from calendar_skill import CalendarSkill
from exam_detector import ExamDetector
from pattern_memory import PatternMemory
from commute_skill import CommuteSkill
import telegram_bot
import memory


def run_phase3_demo() -> None:
    SEP = "=" * 38

    print(f"\n  {SEP}")
    print("  PHASE 3 DEMO — Campus Intelligence")
    print(f"  {SEP}\n")

    pm = PatternMemory()
    calendar = CalendarSkill()
    detector = ExamDetector()
    commute = CommuteSkill()

    # ── Step 1: inject demo history ──────────────────────────────────────
    print("  [Step 1] Injecting demo history...")
    pm.inject_demo_history()

    # ── Step 2: show pattern learned ─────────────────────────────────────
    print("\n  [Step 2] Pattern summary:")
    summary = pm.get_pattern_summary()
    for line in summary.splitlines():
        print(f"    {line}")

    # ── Step 3: commute alert ─────────────────────────────────────────────
    print("\n  [Step 3] Simulating commute alert...")
    mock_event = {
        "summary": "DBMS Lab",
        "start_time": datetime.now() + timedelta(minutes=35),
        "location": "Room 304",
    }
    alert_info = calendar.compute_departure_alert(mock_event, travel_minutes=25)
    travel_est = commute.get_travel_estimate()
    alert_str = commute.build_commute_alert(mock_event, travel_est)
    print(f"    Alert dict: {alert_info}")
    print(f"    Message preview:\n      " + "\n      ".join(alert_str.splitlines()))
    telegram_bot.send_commute_alert(alert_str)
    memory.log_event("commute_alert", alert_info)
    print("  Commute alert sent to Telegram")

    # ── Step 4: exam week detection ───────────────────────────────────────
    print("\n  [Step 4] Simulating exam week detection...")
    now = datetime.now()
    mock_exams = [
        {"summary": "DBMS End Sem Exam",    "start_time": now + timedelta(days=2)},
        {"summary": "DSA Quiz",             "start_time": now + timedelta(days=3)},
        {"summary": "Mini Project Viva",    "start_time": now + timedelta(days=4)},
        {"summary": "Assignment submission","start_time": now + timedelta(days=5)},
    ]
    exam_data = detector.analyze_week(mock_exams)
    print(f"    Detector result: {{"
          f"exam_count: {exam_data['exam_count']}, "
          f"assignment_count: {exam_data['assignment_count']}, "
          f"is_exam_week: {exam_data['is_exam_week']}, "
          f"is_crunch_week: {exam_data['is_crunch_week']}}}")
    print(f"    Detected: {[e['summary'] for e in exam_data['detected_exams']]}")
    telegram_bot.send_exam_mode_alert(exam_data)
    memory.log_event("exam_mode", {
        "exam_count": exam_data["exam_count"],
        "is_crunch_week": exam_data["is_crunch_week"],
        "detected": [e["summary"] for e in exam_data["detected_exams"]],
    })
    print("  Exam week alert sent to Telegram")

    # ── Step 5: pattern prediction ────────────────────────────────────────
    print("\n  [Step 5] Pattern prediction...")
    current_hour = datetime.now().hour
    current_day = datetime.now().strftime("%A")
    prediction = pm.predict_next_mode(current_hour, current_day)
    if prediction:
        print(f"    [PATTERN] Next mode predicted: {prediction}")
    else:
        print("    Not enough data yet (inject more history for predictions)")

    # ── Step 6: final summary ─────────────────────────────────────────────
    all_entries = len(PatternMemory()._read())
    cal_source = "mock" if not __import__("os").getenv("GOOGLE_CALENDAR_KEY") else "live"
    pred_status = f"predicted: {prediction}" if prediction else "needs more data"

    print(f"\n  {SEP}")
    print("  PHASE 3 COMPLETE")
    print(f"  {SEP}")
    print(f"  Calendar skill     : working ({cal_source})")
    print(f"  Commute alert      : sent to Telegram")
    print(f"  Exam week detector : working")
    print(f"  Pattern memory     : {all_entries} entries logged")
    print(f"  Mode prediction    : {pred_status}")
    print(f"  {SEP}\n")


if __name__ == "__main__":
    run_phase3_demo()
