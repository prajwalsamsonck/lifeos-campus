import json
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect
from flask_socketio import SocketIO
from digital_twin import DigitalTwin

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
BASE_DIR = Path(__file__).parent

_demo_lock = threading.Lock()
_demo_active = False

_DEMO_OVERLAY: dict = {
    "current_mode": "focus",
    "held_count": 7,
    "passed_count": 3,
    "top_held_app": "Instagram",
    "pattern_days": 3,
    "last_event": "Exam detected → Focus Mode activated",
    "ai_decision": "Exam detected → Focus Mode activated → 7 distractions blocked",
    "student_context": {
        "name": "Jyoti",
        "next_class": "Data Structures in 22 min",
        "location": "Library, Block B",
        "stress_level": "moderate",
    },
    "twin_prediction": "Twin predicts high stress window 2–4 PM",
    "weekly_pattern": {
        "Monday": {
            "7": "sleep", "8": "commute", "9": "class", "10": "class",
            "11": "class", "13": "focus", "14": "focus", "22": "sleep", "23": "sleep",
        },
        "Tuesday": {
            "7": "sleep", "8": "commute", "9": "class", "10": "class",
            "14": "hostel", "15": "hostel", "22": "sleep", "23": "sleep",
        },
        "Wednesday": {
            "7": "sleep", "8": "commute", "10": "class", "11": "class",
            "13": "focus", "14": "focus", "22": "sleep",
        },
    },
    "twin": {
        "productivity_score": 74,
        "shield_effectiveness": 87,
        "peak_focus": "9 AM – 11 AM",
        "stress_level": "moderate",
        "top_insight": "Twin predicts high stress window 2–4 PM",
        "introvert_score": 68,
        "data_points": 47,
        "insights": [
            "Twin predicts high stress window 2–4 PM",
            "Focus peaks 9–11 AM — exam shield is active",
            "87% of distractions blocked this session",
        ],
    },
    "demo_mode": True,
}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return None


def _safe_twin_card() -> dict:
    try:
        return DigitalTwin().get_twin_card()
    except Exception:
        return {
            "productivity_score": 0, "shield_effectiveness": 0,
            "peak_focus": "TBD", "stress_level": "low",
            "top_insight": "Building your profile...",
            "introvert_score": 50, "data_points": 0, "insights": [],
        }


def _build_status() -> dict:
    # ── lifeos_memory.json ──────────────────────────────────────────────
    memory = _read_json(BASE_DIR / "lifeos_memory.json") or []

    current_mode = "unknown"
    last_event = "No events yet"

    if memory:
        for entry in reversed(memory):
            if "mode" in entry or entry.get("event_type") == "mode_switch":
                current_mode = entry.get("mode", "unknown")
                break

        last = memory[-1]
        if "mode" in last:
            last_event = f"Mode: {last['mode']}"
        elif last.get("event") == "digest_sent":
            s = last.get("stats", {})
            last_event = (
                f"Digest sent — {s.get('total_held', 0)} held, "
                f"{s.get('total_passed', 0)} passed"
            )
        elif last.get("event_type") == "commute_alert":
            d = last.get("data", {})
            last_event = (
                f"Commute alert: {d.get('event_name', '')} "
                f"in {d.get('depart_in_minutes', '?')} min"
            )
        elif last.get("event_type") == "exam_mode":
            d = last.get("data", {})
            crunch = " (crunch week)" if d.get("is_crunch_week") else ""
            last_event = f"Exam mode: {d.get('exam_count', 0)} exams{crunch}"
        else:
            et = last.get("event_type") or last.get("event") or "event"
            last_event = str(et)

    today = datetime.now().date().isoformat()
    passed_count = sum(
        1 for e in memory
        if e.get("event_type") == "pass_through"
        and e.get("timestamp", "").startswith(today)
    )

    recent_log = list(reversed(memory[-20:]))

    # ── notif_queue.json ────────────────────────────────────────────────
    queue = _read_json(BASE_DIR / "notif_queue.json") or {}
    held = queue.get("held", [])
    held_count = len(held)

    held_by_app: dict = {}
    for n in held:
        a = n.get("app", "unknown")
        held_by_app[a] = held_by_app.get(a, 0) + 1
    top_held_app = max(held_by_app, key=held_by_app.get) if held_by_app else "none"

    # ── pattern_memory.json ─────────────────────────────────────────────
    pattern = _read_json(BASE_DIR / "pattern_memory.json") or []
    days: set = set()
    weekly_pattern: dict = {}
    for entry in pattern:
        day = entry.get("day")
        hour = entry.get("hour")
        mode = entry.get("mode")
        if day:
            days.add(day)
        if day and hour is not None and mode:
            weekly_pattern.setdefault(day, {})[str(hour)] = mode

    _status = {
        "current_mode": current_mode,
        "held_count": held_count,
        "passed_count": passed_count,
        "top_held_app": top_held_app,
        "pattern_days": len(days),
        "last_event": last_event,
        "recent_log": recent_log,
        "weekly_pattern": weekly_pattern,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "twin": _safe_twin_card(),
    }
    with _demo_lock:
        if _demo_active:
            _status.update(_DEMO_OVERLAY)
            today_pfx = datetime.now().strftime("%Y-%m-%dT")
            _status["recent_log"] = [
                {"timestamp": today_pfx + "07:15:00", "mode": "hostel"},
                {"timestamp": today_pfx + "08:20:00", "mode": "commute"},
                {"timestamp": today_pfx + "09:05:00", "mode": "focus"},
            ]
            _status["timestamp"] = datetime.now().strftime("%H:%M:%S")
    return _status


@app.route("/api/status")
def api_status():
    return jsonify(_build_status())


@app.route("/api/twin")
def api_twin():
    return jsonify(_safe_twin_card())


@app.route("/demo")
def set_demo():
    global _demo_active
    with _demo_lock:
        _demo_active = True
    return redirect("/")


@app.route("/live")
def set_live():
    global _demo_active
    with _demo_lock:
        _demo_active = False
    return redirect("/")


# ── Embedded single-page dashboard ─────────────────────────────────────
_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LifeOS Campus — Agent Dashboard</title>
<style>
:root {
  --bg:#F4F5F7;--surface:#FFFFFF;--border:#E4E4EC;
  --text-1:#111122;--text-2:#555568;--text-3:#9898B0;
  --shadow:0 1px 3px rgba(0,0,0,.07),0 4px 12px rgba(0,0,0,.04);
  --radius:14px;--accent:#378ADD;
}
@media(prefers-color-scheme:dark){
  :root{
    --bg:#0F0F18;--surface:#181824;--border:#252535;
    --text-1:#E8E8F2;--text-2:#9090A8;--text-3:#55556A;
    --shadow:0 1px 3px rgba(0,0,0,.3),0 4px 12px rgba(0,0,0,.2);
  }
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:var(--bg);color:var(--text-1);font-size:14px;line-height:1.5;
  -webkit-font-smoothing:antialiased}

/* ── TOP BAR ── */
.topbar{
  display:flex;align-items:center;justify-content:space-between;
  padding:13px 28px;background:var(--surface);
  border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100;
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)
}
.topbar-left{display:flex;align-items:center;gap:10px}
.brand{font-weight:800;font-size:20px;letter-spacing:-.4px;color:var(--text-1)}
.topbar-sep{color:var(--text-3);font-weight:300;font-size:18px;margin:0 2px}
.badge-preview{
  background:#0C447C;color:#E6F1FB;border-radius:12px;
  font-size:12px;padding:4px 12px;font-weight:700;letter-spacing:.02em;
  white-space:nowrap
}
.demo-chip{
  font-size:10px;font-weight:800;letter-spacing:.08em;
  padding:2px 9px;border-radius:10px;
  background:#FAEEDA;color:#92400E;
  text-transform:uppercase;display:none
}
.topbar-right{display:flex;align-items:center;gap:14px}
.clock{font-size:16px;font-weight:700;font-variant-numeric:tabular-nums;
  letter-spacing:.02em;color:var(--text-1)}
.hb-label{font-size:12px;color:var(--text-2)}
.pulse{
  width:9px;height:9px;background:#22C55E;border-radius:50%;
  flex-shrink:0;
  animation:pulse 2s ease-in-out infinite
}
@keyframes pulse{
  0%{transform:scale(.9);box-shadow:0 0 0 0 rgba(34,197,94,.6)}
  70%{transform:scale(1.1);box-shadow:0 0 0 9px rgba(34,197,94,0)}
  100%{transform:scale(.9);box-shadow:0 0 0 0 rgba(34,197,94,0)}
}

/* ── LAYOUT ── */
.main{max-width:1320px;margin:0 auto;padding:24px 28px;display:flex;flex-direction:column;gap:20px}

/* ── SECTION LABELS ── */
.section-label{
  font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
  color:var(--text-3);margin-bottom:12px
}

/* ── CARDS ── */
.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.card{
  background:var(--surface);border-radius:var(--radius);
  padding:22px 20px 18px;box-shadow:var(--shadow);
  border:1px solid var(--border);transition:box-shadow .2s
}
.card:hover{box-shadow:0 2px 8px rgba(0,0,0,.1),0 8px 24px rgba(0,0,0,.07)}
.card-label{
  font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:.07em;color:var(--text-2);margin-bottom:12px
}
.card-value{font-size:38px;font-weight:800;line-height:1;letter-spacing:-.5px;margin-bottom:6px}
.card-sub{font-size:12px;color:var(--text-2)}

/* mode card gets bg from JS */
.mode-card{}
.mode-big{font-size:26px;font-weight:800;margin-bottom:10px}

/* ── MODE PILLS ── */
.pill{
  display:inline-block;font-size:11px;font-weight:700;
  padding:3px 11px;border-radius:20px;text-transform:uppercase;letter-spacing:.05em
}
.pm-commute{background:#E6F1FB;color:#0C447C}
.pm-class  {background:#EEEDFE;color:#3730A3}
.pm-focus  {background:#FAEEDA;color:#92400E}
.pm-hostel {background:#EAF3DE;color:#2D5A0E}
.pm-sleep  {background:#F1EFE8;color:#5A5A5A}
.pm-unknown{background:#F1EFE8;color:#5A5A5A}

/* ── EVENT TYPE PILLS ── */
.et-mode_switch  {background:#E6F1FB;color:#0C447C}
.et-digest_sent  {background:#EDE9FE;color:#4C1D95}
.et-digest       {background:#EDE9FE;color:#4C1D95}
.et-commute_alert{background:#EAF3DE;color:#2D5A0E}
.et-exam_mode    {background:#FEF3C7;color:#92400E}
.et-campus_check {background:#F1EFE8;color:#5A5A5A}
.et-default      {background:#F1F1F5;color:#555568}

/* ── TWO-PANEL ROW ── */
.panel-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.panel{
  background:var(--surface);border-radius:var(--radius);padding:22px;
  box-shadow:var(--shadow);border:1px solid var(--border)
}
.panel-title{
  font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;
  color:var(--text-2);padding-bottom:14px;margin-bottom:14px;
  border-bottom:1px solid var(--border)
}
.empty{color:var(--text-3);font-size:13px}

/* ── TIMELINE ── */
.tl-item{
  display:flex;align-items:center;gap:10px;
  padding:9px 0;border-bottom:1px solid var(--border)
}
.tl-item:last-child{border-bottom:none}
.tl-time{font-size:12px;font-variant-numeric:tabular-nums;color:var(--text-2);min-width:42px}
.tl-arrow{color:var(--text-3);font-size:13px}

/* ── NOTIF BREAKDOWN ── */
.breakdown-num{font-size:52px;font-weight:800;line-height:1;letter-spacing:-1px}
.breakdown-top{font-size:13px;color:var(--text-2);margin-top:8px}
strong{font-weight:700}

/* ── WEEKLY PATTERN GRID ── */
.pattern-wrap{
  background:var(--surface);border-radius:var(--radius);padding:22px;
  box-shadow:var(--shadow);border:1px solid var(--border)
}
.pattern-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.pattern-grid{
  display:grid;
  grid-template-columns:28px repeat(7,1fr);
  gap:2px;min-width:480px
}
.pg-corner{}
.pg-day{
  font-size:11px;font-weight:700;color:var(--text-2);
  text-align:center;padding:0 0 8px;text-transform:uppercase;letter-spacing:.05em
}
.pg-hour{
  font-size:10px;color:var(--text-3);text-align:right;
  padding-right:6px;line-height:18px
}
.pg-cell{
  height:18px;border-radius:3px;background:#EDEDED;
  cursor:default;transition:opacity .15s
}
@media(prefers-color-scheme:dark){.pg-cell{background:#272733}}
.pg-cell:hover{opacity:.75}
.mc-commute{background:#378ADD}.mc-class{background:#7F77DD}
.mc-focus{background:#BA7517}.mc-hostel{background:#639922}
.mc-sleep{background:#888780}

.pattern-legend{display:flex;gap:16px;margin-top:14px;flex-wrap:wrap;align-items:center}
.lg-item{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text-2)}
.lg-dot{width:13px;height:13px;border-radius:3px;flex-shrink:0}
.pattern-note{font-size:12px;color:var(--text-3);margin-top:10px;text-align:center}

/* ── LOG TABLE ── */
.log-wrap{
  background:var(--surface);border-radius:var(--radius);padding:22px;
  box-shadow:var(--shadow);border:1px solid var(--border)
}
.log-table{width:100%;border-collapse:collapse}
.log-table th{
  font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;
  color:var(--text-2);text-align:left;padding:0 14px 12px 0;
  border-bottom:1px solid var(--border)
}
.log-table td{
  padding:10px 14px 10px 0;border-bottom:1px solid var(--border);
  font-size:13px;vertical-align:middle
}
.log-table tr:last-child td{border-bottom:none}
.log-ts{font-variant-numeric:tabular-nums;color:var(--text-2);white-space:nowrap;font-size:12px}
.log-summary{color:var(--text-1);line-height:1.4}
.log-table tr{transition:background .15s}
.log-table tbody tr:hover{background:rgba(0,0,0,.02)}
@media(prefers-color-scheme:dark){.log-table tbody tr:hover{background:rgba(255,255,255,.03)}}

/* ── FOOTER ── */
.footer{text-align:right;font-size:11px;color:var(--text-3);padding-top:4px}

/* ── RESPONSIVE ── */
@media(max-width:960px){.stat-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:680px){
  .stat-grid{grid-template-columns:1fr}
  .panel-row{grid-template-columns:1fr}
  .main{padding:16px}
  .topbar{padding:12px 16px}
}

/* ── FADE IN ── */
@keyframes fadein{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.main>*{animation:fadein .35s ease both}
.main>*:nth-child(1){animation-delay:.05s}
.main>*:nth-child(2){animation-delay:.1s}
.main>*:nth-child(3){animation-delay:.15s}
.main>*:nth-child(4){animation-delay:.2s}
.main>*:nth-child(5){animation-delay:.25s}
.main>*:nth-child(6){animation-delay:.3s}
.main>*:nth-child(7){animation-delay:.35s}

/* ── DIGITAL TWIN ── */
.twin-wrap{
  background:var(--surface);border-radius:var(--radius);padding:22px;
  box-shadow:var(--shadow);border:1px solid var(--border)
}
.twin-header{
  display:flex;align-items:center;justify-content:space-between;
  padding-bottom:14px;margin-bottom:16px;border-bottom:1px solid var(--border)
}
.twin-layout{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:start}
.twin-metrics{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.twin-metric{
  background:var(--bg);border-radius:10px;padding:14px 10px;
  border:1px solid var(--border);text-align:center
}
.twin-metric-val{
  font-size:30px;font-weight:800;line-height:1;letter-spacing:-.5px;margin-bottom:4px;
  color:var(--text-1)
}
.twin-metric-lbl{
  font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em;color:var(--text-2)
}
.twin-insights{display:flex;flex-direction:column;gap:8px}
.twin-insight{
  display:flex;align-items:flex-start;gap:10px;
  font-size:12px;color:var(--text-1);line-height:1.45;
  padding:10px 12px;background:var(--bg);
  border-radius:8px;border:1px solid var(--border)
}
.tw-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:3px}
.tw-blue  {background:#378ADD}
.tw-green {background:#639922}
.tw-amber {background:#BA7517}
.tw-purple{background:#7F77DD}
.tw-gray  {background:#888780}
.tw-stress-badge{
  font-size:11px;font-weight:700;padding:3px 10px;border-radius:12px;
  letter-spacing:.02em
}
.stress-low     {background:#EAF3DE;color:#2D5A0E}
.stress-moderate{background:#FAEEDA;color:#92400E}
.stress-high    {background:#FEE2E2;color:#991B1B}
.twin-footer{margin-top:10px;font-size:11px;color:var(--text-3)}
@media(max-width:680px){.twin-layout{grid-template-columns:1fr}}

/* ── AI DECISION BANNER ── */
.ai-banner{
  background:linear-gradient(135deg,#0B1622 0%,#162032 100%);
  border-radius:var(--radius);padding:24px 28px;
  border:1px solid #1E3A52;
  box-shadow:0 4px 28px rgba(0,0,0,.28);
  display:none
}
.ai-banner-hdr{display:flex;align-items:center;gap:12px;margin-bottom:18px}
.ai-tag{
  font-size:11px;font-weight:800;letter-spacing:.14em;
  text-transform:uppercase;color:#60A5FA
}
.ai-live{display:flex;align-items:center;gap:5px;font-size:11px;font-weight:700;color:#4ADE80}
.ai-live-dot{
  width:7px;height:7px;background:#4ADE80;border-radius:50%;
  animation:pulse 1.6s ease-in-out infinite
}
.ai-chain{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:18px}
.ai-step{
  padding:10px 20px;border-radius:10px;
  font-size:15px;font-weight:700;letter-spacing:-.1px;
  background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.1);
  color:#CBD5E1
}
.ai-step.final{
  background:rgba(74,222,128,.1);
  border-color:rgba(74,222,128,.3);
  color:#4ADE80
}
.ai-sep{color:#334155;font-size:20px;user-select:none;padding:0 2px}
.ai-pred{
  border-top:1px solid rgba(255,255,255,.07);
  padding-top:14px;
  display:flex;align-items:center;gap:9px;
  font-size:13px;color:#94A3B8
}
.ai-pred-icon{font-size:16px}

/* ── STUDENT CONTEXT CARD ── */
.ctx-items{display:flex;flex-direction:column;gap:11px;padding-top:4px}
.ctx-row{display:flex;flex-direction:column;gap:2px}
.ctx-lbl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text-3)}
.ctx-val{font-size:13px;font-weight:600;color:var(--text-1);line-height:1.3}
.ctx-stress-moderate{color:#D97706}
.ctx-stress-high{color:#DC2626}
.ctx-stress-low{color:#16A34A}

/* ── 5-COL STAT GRID (demo mode) ── */
.stat-grid.has-ctx{grid-template-columns:repeat(5,1fr)}
@media(max-width:1100px){.stat-grid.has-ctx{grid-template-columns:repeat(3,1fr)}}
@media(max-width:960px){.stat-grid.has-ctx{grid-template-columns:repeat(2,1fr)}}
@media(max-width:680px){.stat-grid.has-ctx{grid-template-columns:1fr}}
</style>
</head>
<body>

<!-- TOP BAR -->
<header class="topbar">
  <div class="topbar-left">
    <span class="brand">LifeOS Campus</span>
    <span class="topbar-sep">&mdash;</span>
    <span class="badge-preview">Galaxy AI Preview</span>
    <span class="demo-chip" id="demo-chip">Demo</span>
  </div>
  <div class="topbar-right">
    <span class="clock" id="js-clock">--:--:--</span>
    <span class="hb-label">Heartbeat agent running</span>
    <span class="pulse"></span>
  </div>
</header>

<div class="main">

  <!-- AI DECISION BANNER (demo mode only) -->
  <div class="ai-banner" id="ai-banner">
    <div class="ai-banner-hdr">
      <span class="ai-tag">AI Decision</span>
      <span class="ai-live"><span class="ai-live-dot"></span>&nbsp;LIVE</span>
    </div>
    <div class="ai-chain" id="ai-chain"></div>
    <div class="ai-pred">
      <span class="ai-pred-icon">&#x1F916;</span>
      <span id="ai-pred-text">Loading prediction&hellip;</span>
    </div>
  </div>

  <!-- ROW 1 — Stat cards -->
  <div>
    <div class="section-label">System Status</div>
    <div class="stat-grid" id="stat-grid">

      <!-- Mode card -->
      <div class="card mode-card" id="mode-card">
        <div class="card-label">Current Mode</div>
        <div class="mode-big" id="mode-value">&mdash;</div>
        <div><span class="pill pm-unknown" id="mode-pill">loading</span></div>
      </div>

      <!-- Student Context (demo only) -->
      <div class="card" id="ctx-card" style="display:none">
        <div class="card-label">Student Context</div>
        <div class="ctx-items">
          <div class="ctx-row">
            <span class="ctx-lbl">Next Class</span>
            <span class="ctx-val" id="ctx-class">&mdash;</span>
          </div>
          <div class="ctx-row">
            <span class="ctx-lbl">Location</span>
            <span class="ctx-val" id="ctx-loc">&mdash;</span>
          </div>
          <div class="ctx-row">
            <span class="ctx-lbl">Stress Level</span>
            <span class="ctx-val" id="ctx-stress">&mdash;</span>
          </div>
        </div>
      </div>

      <!-- Held -->
      <div class="card">
        <div class="card-label">Notifications Held</div>
        <div class="card-value" id="held-count">&mdash;</div>
        <div class="card-sub">queued for digest</div>
      </div>

      <!-- Passed -->
      <div class="card">
        <div class="card-label">Notifications Passed</div>
        <div class="card-value" id="passed-count">&mdash;</div>
        <div class="card-sub">urgent delivered</div>
      </div>

      <!-- Pattern -->
      <div class="card">
        <div class="card-label">Pattern Days Learned</div>
        <div class="card-value" id="pattern-days">&mdash;</div>
        <div class="card-sub">days of behavior data</div>
      </div>

    </div>
  </div>

  <!-- ROW 2 — Two panels -->
  <div class="panel-row">
    <div class="panel">
      <div class="panel-title">Today&rsquo;s Mode Timeline</div>
      <div id="timeline-body"><span class="empty">Loading&hellip;</span></div>
    </div>
    <div class="panel">
      <div class="panel-title">Notification Breakdown</div>
      <div id="notif-body"><span class="empty">Loading&hellip;</span></div>
    </div>
  </div>

  <!-- ROW 3 — Weekly pattern -->
  <div class="pattern-wrap">
    <div class="panel-title">Weekly Pattern Learned</div>
    <div class="pattern-scroll">
      <div class="pattern-grid" id="pg"></div>
    </div>
    <div class="pattern-legend">
      <div class="lg-item"><div class="lg-dot" style="background:#378ADD"></div>Commute</div>
      <div class="lg-item"><div class="lg-dot" style="background:#7F77DD"></div>Class</div>
      <div class="lg-item"><div class="lg-dot" style="background:#BA7517"></div>Focus</div>
      <div class="lg-item"><div class="lg-dot" style="background:#639922"></div>Hostel</div>
      <div class="lg-item"><div class="lg-dot" style="background:#888780"></div>Sleep</div>
      <div class="lg-item"><div class="lg-dot" style="background:#EDEDED;border:1px solid #ccc"></div>No data</div>
    </div>
    <div class="pattern-note" id="pg-note"></div>
  </div>

  <!-- ROW 4 — Live log -->
  <div class="log-wrap">
    <div class="panel-title">Live Agent Log</div>
    <div id="log-body"><span class="empty">Loading&hellip;</span></div>
  </div>

  <!-- ROW 5 — Digital Twin -->
  <div class="twin-wrap">
    <div class="twin-header">
      <div class="panel-title" style="padding:0;margin:0;border:0">Your Digital Twin</div>
      <span class="tw-stress-badge stress-low" id="tw-badge">low stress</span>
    </div>
    <div class="twin-layout">
      <div class="twin-metrics">
        <div class="twin-metric">
          <div class="twin-metric-val" id="tw-prod">&mdash;</div>
          <div class="twin-metric-lbl">Productivity /100</div>
        </div>
        <div class="twin-metric">
          <div class="twin-metric-val" id="tw-shield">&mdash;</div>
          <div class="twin-metric-lbl">Shield %</div>
        </div>
        <div class="twin-metric">
          <div class="twin-metric-val" id="tw-intro">&mdash;</div>
          <div class="twin-metric-lbl">Introvert /100</div>
        </div>
        <div class="twin-metric">
          <div class="twin-metric-val" id="tw-dp">&mdash;</div>
          <div class="twin-metric-lbl">Data Points</div>
        </div>
      </div>
      <div class="twin-insights" id="tw-insights">
        <span class="empty">Loading twin profile&hellip;</span>
      </div>
    </div>
    <div class="twin-footer">Peak focus window: <strong id="tw-peak">TBD</strong></div>
  </div>

  <div class="footer">Updated&nbsp;<span id="updated-at">&mdash;</span></div>

</div><!-- /main -->

<script>
const DAYS_FULL = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
const DAYS_ABR  = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
const HOURS     = Array.from({length:24},(_,i)=>i);

const MODE_BG = {
  commute:'#E6F1FB',class:'#EEEDFE',focus:'#FAEEDA',
  hostel:'#EAF3DE',sleep:'#F1EFE8',unknown:'#F1EFE8'
};
const MODE_FG = {
  commute:'#0C447C',class:'#3730A3',focus:'#92400E',
  hostel:'#2D5A0E',sleep:'#5A5A5A',unknown:'#5A5A5A'
};

/* clock */
function tickClock(){
  document.getElementById('js-clock').textContent =
    new Date().toTimeString().slice(0,8);
}
setInterval(tickClock,1000); tickClock();

/* helpers */
function modePillHTML(m){
  const k=m||'unknown';
  return `<span class="pill pm-${k}" style="background:${MODE_BG[k]||'#F1EFE8'};color:${MODE_FG[k]||'#5A5A5A'}">${k.toUpperCase()}</span>`;
}

function etPillHTML(et){
  const raw = et || 'event';
  const label = raw.replace(/_/g,' ');
  const cls = 'et-'+raw;
  return `<span class="pill ${cls}" style="text-transform:capitalize;letter-spacing:.02em">${label}</span>`;
}

function fmtTs(ts){
  if(!ts) return '—';
  const p = ts.split('T');
  return p.length>1 ? p[1].slice(0,5) : ts.slice(0,16);
}

function entryType(e){
  if(e.mode && !e.event_type) return 'mode_switch';
  if(e.event==='digest_sent') return 'digest_sent';
  return e.event_type || e.event || 'event';
}

function entryText(e){
  if(e.mode && !e.event_type) return `Mode switched → ${e.mode}`;
  if(e.event==='digest_sent'){
    const s=e.stats||{};
    return `Digest sent — ${s.total_held||0} held, ${s.total_passed||0} passed`;
  }
  if(e.event_type==='commute_alert'){
    const d=e.data||{};
    return `Commute alert: ${d.event_name||''} in ${d.depart_in_minutes||'?'} min`;
  }
  if(e.event_type==='exam_mode'){
    const d=e.data||{};
    const cr=d.is_crunch_week?' (crunch week)':'';
    return `Exam mode: ${d.exam_count||0} exams${cr}`;
  }
  return JSON.stringify(e).slice(0,100);
}

/* Timeline */
function renderTimeline(log){
  const el = document.getElementById('timeline-body');
  const today = new Date().toISOString().slice(0,10);
  const items = (log||[]).filter(e=>e.mode && !e.event_type && (e.timestamp||'').startsWith(today));
  if(!items.length){el.innerHTML='<span class="empty">No mode switches logged yet</span>';return;}
  el.innerHTML = items.map(e=>`
    <div class="tl-item">
      <span class="tl-time">${fmtTs(e.timestamp)}</span>
      <span class="tl-arrow">→</span>
      ${modePillHTML(e.mode)}
    </div>`).join('');
}

/* Notif breakdown */
function renderBreakdown(data){
  const el = document.getElementById('notif-body');
  const n = data.held_count||0;
  const top = data.top_held_app||'none';
  if(n===0){
    el.innerHTML=`<div style="text-align:center;padding:24px 0">
      <div class="breakdown-num" style="color:var(--text-1)">0</div>
      <div class="empty" style="margin-top:8px">Queue is clear ✔</div>
    </div>`;
    return;
  }
  el.innerHTML=`
    <div style="display:flex;align-items:baseline;gap:8px">
      <div class="breakdown-num">${n}</div>
      <div class="card-sub">held</div>
    </div>
    <div class="breakdown-top">Top app: <strong>${top}</strong></div>
    <div style="margin-top:14px;font-size:12px;color:var(--text-2)">
      ${n} notification${n===1?'':'s'} queued for next digest
    </div>`;
}

/* Pattern grid */
function renderPatternGrid(wp){
  const grid = document.getElementById('pg');
  const note = document.getElementById('pg-note');
  const hasData = wp && Object.keys(wp).length>0;

  grid.innerHTML='';

  /* corner */
  grid.appendChild(Object.assign(document.createElement('div'),{className:'pg-corner'}));

  /* day headers */
  DAYS_ABR.forEach(d=>{
    const h=document.createElement('div');
    h.className='pg-day'; h.textContent=d;
    grid.appendChild(h);
  });

  /* hour rows */
  HOURS.forEach(h=>{
    const lbl=document.createElement('div');
    lbl.className='pg-hour'; lbl.textContent=h;
    grid.appendChild(lbl);

    DAYS_FULL.forEach(day=>{
      const cell=document.createElement('div');
      cell.className='pg-cell';
      const mode = hasData && wp[day] && wp[day][String(h)];
      if(mode) cell.classList.add('mc-'+mode);
      cell.title = mode ? `${day} ${h}:00 — ${mode}` : `${day} ${h}:00 — no data yet`;
      grid.appendChild(cell);
    });
  });

  if(hasData){
    const daysLearned = Object.keys(wp).length;
    const remaining = 7 - daysLearned;
    note.textContent = remaining > 0
      ? `${daysLearned} day${daysLearned>1?'s':''} learned — ${remaining} day${remaining>1?'s':''} still collecting…`
      : '';
  } else {
    note.textContent = 'Run demo history injection to populate — python phase3_demo.py';
  }
}

/* Log */
function renderLog(log){
  const el = document.getElementById('log-body');
  if(!log||!log.length){el.innerHTML='<span class="empty">No events logged yet</span>';return;}
  const rows = log.map(e=>{
    const ts=fmtTs(e.timestamp);
    const et=entryType(e);
    const txt=entryText(e);
    return `<tr>
      <td class="log-ts">${ts}</td>
      <td style="padding-right:14px;white-space:nowrap">${etPillHTML(et)}</td>
      <td class="log-summary">${txt}</td>
    </tr>`;
  }).join('');
  el.innerHTML=`<table class="log-table">
    <thead><tr><th>Time</th><th>Type</th><th>Summary</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

/* Digital Twin */
const TW_DOT_CLS = ['tw-blue','tw-green','tw-amber','tw-purple','tw-gray'];
function renderTwin(twin){
  if(!twin) return;
  document.getElementById('tw-prod').textContent   = twin.productivity_score??'—';
  document.getElementById('tw-shield').textContent = (twin.shield_effectiveness??'—')+'%';
  document.getElementById('tw-intro').textContent  = twin.introvert_score??'—';
  document.getElementById('tw-dp').textContent     = twin.data_points??'—';
  document.getElementById('tw-peak').textContent   = twin.peak_focus||'TBD';

  const badge = document.getElementById('tw-badge');
  const sl    = twin.stress_level||'low';
  badge.textContent = sl+' stress';
  badge.className   = `tw-stress-badge stress-${sl}`;

  const el  = document.getElementById('tw-insights');
  const arr = (twin.insights && twin.insights.length)
    ? twin.insights
    : (twin.top_insight ? [twin.top_insight] : []);
  if(!arr.length){el.innerHTML='<span class="empty">Building twin profile…</span>';return;}
  el.innerHTML = arr.slice(0,3).map((ins,i)=>
    `<div class="twin-insight">
      <div class="tw-dot ${TW_DOT_CLS[i]||'tw-gray'}"></div>
      <span>${ins}</span>
    </div>`
  ).join('');
}

/* Demo overlay renderer */
function renderDemo(data){
  const isDemo = !!data.demo_mode;

  /* header chip */
  const chip = document.getElementById('demo-chip');
  if(chip) chip.style.display = isDemo ? 'inline-block' : 'none';

  /* AI Decision Banner */
  const banner = document.getElementById('ai-banner');
  if(isDemo && data.ai_decision){
    banner.style.display = '';
    const steps = data.ai_decision.split('→').map(s=>s.trim());
    document.getElementById('ai-chain').innerHTML = steps.map((s,i)=>{
      const last = i===steps.length-1;
      const sep  = i<steps.length-1 ? '<span class="ai-sep">→</span>' : '';
      return `<span class="ai-step${last?' final':''}">${s}</span>${sep}`;
    }).join('');
    const predEl = document.getElementById('ai-pred-text');
    if(predEl && data.twin_prediction) predEl.textContent = data.twin_prediction;
  } else {
    if(banner) banner.style.display = 'none';
  }

  /* Student Context card */
  const ctxCard = document.getElementById('ctx-card');
  const grid    = document.getElementById('stat-grid');
  if(isDemo && data.student_context){
    ctxCard.style.display = '';
    grid.classList.add('has-ctx');
    const ctx = data.student_context;
    document.getElementById('ctx-class').textContent = ctx.next_class || '—';
    document.getElementById('ctx-loc').textContent   = ctx.location  || '—';
    const stEl = document.getElementById('ctx-stress');
    const sl   = ctx.stress_level || '';
    stEl.textContent = sl.charAt(0).toUpperCase()+sl.slice(1);
    stEl.className   = `ctx-val ctx-stress-${sl}`;
  } else {
    if(ctxCard) ctxCard.style.display = 'none';
    if(grid)    grid.classList.remove('has-ctx');
  }
}

/* Main refresh */
async function refresh(){
  let data;
  try{
    const r = await fetch('/api/status');
    data = await r.json();
  }catch(err){
    console.error('Dashboard fetch error:',err);
    return;
  }

  /* mode card */
  const m = data.current_mode||'unknown';
  const card = document.getElementById('mode-card');
  card.style.background = MODE_BG[m]||'#F1EFE8';
  const mv = document.getElementById('mode-value');
  mv.textContent = m.charAt(0).toUpperCase()+m.slice(1);
  mv.style.color = MODE_FG[m]||'#5A5A5A';
  const mp = document.getElementById('mode-pill');
  mp.className=`pill pm-${m}`;
  mp.style.background=MODE_BG[m]||'#F1EFE8';
  mp.style.color=MODE_FG[m]||'#5A5A5A';
  mp.textContent=m.toUpperCase();

  /* stat numbers */
  document.getElementById('held-count').textContent   = data.held_count??0;
  document.getElementById('passed-count').textContent = data.passed_count??0;
  document.getElementById('pattern-days').textContent = data.pattern_days??0;

  renderTimeline(data.recent_log);
  renderBreakdown(data);
  renderPatternGrid(data.weekly_pattern);
  renderLog(data.recent_log);
  renderTwin(data.twin);
  renderDemo(data);

  document.getElementById('updated-at').textContent = data.timestamp||'--:--:--';
}

refresh();
setInterval(refresh, 3000);
</script>
<script src="/socket.io/socket.io.js"></script>
<script>
try{const _sock=io();_sock.on('refresh',refresh);}catch(e){}
</script>
</body>
</html>"""


def _push_loop():
    import time as _t
    while True:
        _t.sleep(3)
        socketio.emit("refresh")


@app.route("/")
def index():
    return _HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


if __name__ == "__main__":
    socketio.start_background_task(_push_loop)
    socketio.run(app, host="127.0.0.1", port=5000, debug=False, allow_unsafe_werkzeug=True)
