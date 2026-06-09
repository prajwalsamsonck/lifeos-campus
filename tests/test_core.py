from __future__ import annotations

import json
from datetime import datetime, timedelta

import notification_queue
import pattern_memory
from dashboard import app
from exam_detector import ExamDetector
from modes import get_mode
from notification_queue import NotificationQueue
from notification_scorer import NotificationScorer
from pattern_memory import PatternMemory


def test_dashboard_routes():
    client = app.test_client()

    assert client.get("/").status_code == 200
    assert client.get("/demo").status_code == 302
    assert client.get("/live").status_code == 302
    assert client.get("/api/status").is_json
    assert client.get("/api/twin").is_json


def test_context_modes():
    assert get_mode({"hour": 23, "day": "Monday", "location_zone": "hostel"}).name == "sleep"
    assert get_mode({"hour": 8, "day": "Monday", "location_zone": "transit"}).name == "commute"
    assert get_mode({"hour": 10, "day": "Monday", "location_zone": "campus"}).name == "class"
    assert get_mode({"hour": 15, "day": "Monday", "location_zone": "campus"}).name == "focus"
    assert get_mode({"hour": 15, "day": "Sunday", "location_zone": "campus"}).name == "hostel"


def test_notification_scoring_prefers_family_and_academic_messages():
    scorer = NotificationScorer()

    family = scorer.score_notification({"sender": "Mom", "app": "sms"}, "focus")
    academic = scorer.score_notification({"sender": "Professor", "app": "gmail"}, "focus")
    social = scorer.score_notification({"sender": "Instagram", "app": "instagram"}, "focus")

    assert family == 10
    assert academic == 8
    assert social < academic


def test_notification_queue_routes_and_clears_digest(tmp_path, monkeypatch):
    queue_file = tmp_path / "queue.json"
    monkeypatch.setattr(notification_queue, "QUEUE_FILE", queue_file)
    queue = NotificationQueue()

    urgent = {"sender": "Mom", "app": "sms", "message_preview": "Call me"}
    social = {"sender": "Instagram", "app": "instagram", "message_preview": "New like"}

    assert queue.add(urgent, 10)["action"] == "pass_through"
    assert queue.add(social, 2)["action"] == "held"

    digest = queue.get_digest()
    assert digest["total_held"] == 1
    assert digest["total_passed"] == 1
    assert json.loads(queue_file.read_text(encoding="utf-8")) == {
        "held": [],
        "passed_through": [],
    }


def test_exam_detector_identifies_exam_week():
    now = datetime.now()
    events = [
        {"summary": "DBMS Exam", "start_time": now + timedelta(days=1)},
        {"summary": "DSA Quiz", "start_time": now + timedelta(days=2)},
        {"summary": "Project submission", "start_time": now + timedelta(days=3)},
    ]

    result = ExamDetector().analyze_week(events)

    assert result["exam_count"] == 2
    assert result["assignment_count"] == 1
    assert result["is_exam_week"] is True
    assert result["is_crunch_week"] is True


def test_pattern_memory_learns_next_mode(tmp_path, monkeypatch):
    pattern_file = tmp_path / "patterns.json"
    monkeypatch.setattr(pattern_memory, "PATTERN_FILE", pattern_file)
    memory = PatternMemory()

    for _ in range(3):
        memory.log_mode_event("focus", 10, "Monday", "campus")

    assert memory.predict_next_mode(9, "Monday") == "focus"
