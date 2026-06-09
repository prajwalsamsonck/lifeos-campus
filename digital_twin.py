import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
MEMORY_FILE = BASE_DIR / "lifeos_memory.json"
PATTERN_FILE = BASE_DIR / "pattern_memory.json"
QUEUE_FILE = BASE_DIR / "notif_queue.json"


class DigitalTwin:

    def _read_memory(self) -> list:
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8")) if MEMORY_FILE.exists() else []
        except Exception:
            return []

    def _read_pattern(self) -> list:
        try:
            return json.loads(PATTERN_FILE.read_text(encoding="utf-8")) if PATTERN_FILE.exists() else []
        except Exception:
            return []

    # ── build_profile ────────────────────────────────────────────────────

    def build_profile(self) -> dict:
        memory  = self._read_memory()
        pattern = self._read_pattern()
        total   = len(pattern)

        # ── peak focus hours ──────────────────────────────────────────────
        focus_h = Counter(e["hour"] for e in pattern if e.get("mode") == "focus")
        focus_d = Counter(e["day"]  for e in pattern if e.get("mode") == "focus")
        peak_focus_hours = [h for h, _ in focus_h.most_common(2)]
        peak_focus_days  = [d for d, _ in focus_d.most_common(2)]

        # ── stress signals ────────────────────────────────────────────────
        # Restless switching: (day, hour) pairs where multiple modes appear
        dh_modes: dict = defaultdict(set)
        for e in pattern:
            day  = e.get("day")
            hour = e.get("hour")
            mode = e.get("mode")
            if day and hour is not None and mode:
                dh_modes[(day, hour)].add(mode)

        multi_hour_by_day: Counter = Counter()
        for (day, _), modes in dh_modes.items():
            if len(modes) > 1:
                multi_hour_by_day[day] += 1

        stress_days = [d for d, _ in multi_hour_by_day.most_common()]
        high_stress_hours = [
            h for h, _ in Counter(
                hour for (day, hour), modes in dh_modes.items() if len(modes) > 1
            ).most_common(3)
        ]

        # Trend: focus ratio first-half vs second-half
        stress_trend = "stable"
        if len(pattern) >= 10:
            mid = len(pattern) // 2
            def focus_ratio(entries):
                return Counter(e.get("mode") for e in entries).get("focus", 0) / max(1, len(entries))
            fr_early = focus_ratio(pattern[:mid])
            fr_late  = focus_ratio(pattern[mid:])
            if fr_late > fr_early + 0.05:
                stress_trend = "decreasing"
            elif fr_late < fr_early - 0.05:
                stress_trend = "increasing"

        stress_signals = {
            "high_stress_hours": high_stress_hours,
            "stress_days": stress_days,
            "stress_trend": stress_trend,
        }

        # ── social energy ─────────────────────────────────────────────────
        hostel_h = Counter(e["hour"] for e in pattern if e.get("mode") == "hostel")
        peak_social_hours = [h for h, _ in hostel_h.most_common(3)]

        social_energy_drops_after = 21
        if hostel_h:
            for h in sorted(hostel_h.keys(), reverse=True):
                if hostel_h[h] >= 2:
                    social_energy_drops_after = h
                    break

        social_count  = sum(1 for e in pattern if e.get("mode") in ("hostel",))
        introvert_score = round((total - social_count) / max(1, total) * 100)

        social_energy = {
            "peak_social_hours": peak_social_hours,
            "social_energy_drops_after": social_energy_drops_after,
            "introvert_score": introvert_score,
        }

        # ── productivity ──────────────────────────────────────────────────
        productive_count = sum(1 for e in pattern if e.get("mode") in ("focus", "class"))
        productivity_score = round(productive_count / max(1, total) * 100)

        best_hour = focus_h.most_common(1)[0][0] if focus_h else 9
        best_day  = focus_d.most_common(1)[0][0] if focus_d else "Monday"

        # Focus streak record: longest consecutive focus hours per day
        dh_mode_map = {}
        for e in pattern:
            key = (e.get("day"), e.get("hour"))
            if key[0] and key[1] is not None:
                dh_mode_map[key] = e.get("mode")

        focus_streak_record = 0
        for day in set(e.get("day") for e in pattern if e.get("day")):
            streak = best = 0
            for h in range(24):
                if dh_mode_map.get((day, h)) == "focus":
                    streak += 1
                    best = max(best, streak)
                else:
                    streak = 0
            focus_streak_record = max(focus_streak_record, best)

        productivity = {
            "productivity_score": productivity_score,
            "best_hour": best_hour,
            "best_day": best_day,
            "focus_streak_record": focus_streak_record,
        }

        # ── notification health ───────────────────────────────────────────
        digest_entries = [e for e in memory if e.get("event") == "digest_sent"]
        total_held   = sum(e.get("stats", {}).get("total_held",   0) for e in digest_entries)
        total_passed = sum(e.get("stats", {}).get("total_passed", 0) for e in digest_entries)
        num_days = max(1, len(digest_entries))

        app_counts: Counter = Counter()
        for e in digest_entries:
            for app, cnt in e.get("stats", {}).get("held_by_app", {}).items():
                app_counts[app] += cnt

        most_disruptive_app = app_counts.most_common(1)[0][0] if app_counts else "none"
        total_notifs = total_held + total_passed
        shield_effectiveness = round(total_held / max(1, total_notifs) * 100)

        notification_health = {
            "avg_held_per_day":   round(total_held   / num_days, 1),
            "avg_passed_per_day": round(total_passed / num_days, 1),
            "most_disruptive_app": most_disruptive_app,
            "shield_effectiveness": shield_effectiveness,
        }

        # ── metadata ──────────────────────────────────────────────────────
        timestamps = []
        for e in pattern:
            try:
                timestamps.append(datetime.fromisoformat(e["timestamp"]))
            except Exception:
                pass
        profile_age_days = (max(timestamps) - min(timestamps)).days + 1 if len(timestamps) >= 2 else 1

        return {
            "peak_focus_hours": peak_focus_hours,
            "peak_focus_days":  peak_focus_days,
            "stress_signals":   stress_signals,
            "social_energy":    social_energy,
            "productivity":     productivity,
            "notification_health": notification_health,
            "profile_age_days": profile_age_days,
            "data_points":      total,
            "last_updated":     datetime.now().isoformat(),
        }

    # ── generate_insights ────────────────────────────────────────────────

    def generate_insights(self) -> list:
        p = self.build_profile()
        insights = []

        # 1. Peak focus time
        phours = p["peak_focus_hours"]
        pdays  = p["peak_focus_days"]
        if phours and pdays:
            lo, hi = min(phours), max(phours)
            hour_str = f"{lo}:00-{hi+1}:00" if lo != hi else f"{lo}:00"
            days_str = " and ".join(pdays[:2])
            insights.append(
                f"Your peak focus window is {days_str} at {hour_str}. "
                f"Protect this time at all costs."
            )

        # 2. Most disruptive app
        nh  = p["notification_health"]
        app = nh["most_disruptive_app"]
        if app and app != "none":
            blocked = round(nh["avg_held_per_day"] * p["profile_age_days"])
            insights.append(
                f"{app.capitalize()} is your most disruptive app — "
                f"LifeOS blocked it {blocked} times this period."
            )

        # 3. Social energy drop
        se = p["social_energy"]
        drop = se["social_energy_drops_after"]
        insights.append(
            f"Your social energy drops after {drop}:00. "
            f"LifeOS has been scheduling social digests before this window automatically."
        )

        # 4. Stress signals
        ss = p["stress_signals"]
        if ss["stress_days"]:
            hs = ss["high_stress_hours"]
            hour_hint = f"around {hs[0]}:00" if hs else "late night"
            insights.append(
                f"You showed stress signals on {len(ss['stress_days'])} day(s) {hour_hint}. "
                f"Pattern consistent with exam period behaviour."
            )
        else:
            insights.append(
                f"No unusual stress signals detected. "
                f"Your routine looks stable this week."
            )

        # 5. Shield effectiveness
        eff = nh["shield_effectiveness"]
        dp  = p["data_points"]
        insights.append(
            f"Your attention shield is {eff}% effective with {dp} data points. "
            f"LifeOS gets smarter with every tick."
        )

        return insights[:5]

    # ── generate_weekly_report ───────────────────────────────────────────

    def generate_weekly_report(self) -> str:
        p        = self.build_profile()
        insights = self.generate_insights()

        phours = p["peak_focus_hours"]
        pdays  = p["peak_focus_days"]
        hour_str = (f"{min(phours)}-{max(phours)+1}:00" if len(phours) >= 2
                    else (f"{phours[0]}:00" if phours else "TBD"))
        days_str = "/".join(d[:3] for d in pdays[:2]) if pdays else "TBD"

        prod = p["productivity"]
        ss   = p["stress_signals"]
        nh   = p["notification_health"]
        counterfactual = (
            "Counterfactual: without your attention shield, you would have seen "
            f"about {nh['avg_held_per_day']} extra low-priority notifications per day."
        )

        lines = [
            "LifeOS — Your Digital Twin Report",
            f"Week of {datetime.now().strftime('%d %b %Y')}",
            "━" * 20,
            "",
            "Your week in numbers:",
            f"· Peak focus    : {days_str} {hour_str}",
            f"· Productivity  : {prod['productivity_score']}/100",
            f"· Stress signals: {len(ss['stress_days'])} days detected",
            f"· Shield        : {nh['shield_effectiveness']}% effective",
            f"· Most disruptive app: {nh['most_disruptive_app']}",
            "",
            "Top insights this week:",
        ]
        for i, ins in enumerate(insights[:3], 1):
            lines.append(f"{i}. {ins}")

        lines += [
            "",
            counterfactual,
            "",
            "━" * 20,
            f"Your Digital Twin has {p['data_points']} observations.",
            "It knows you better every day.",
        ]
        return "\n".join(lines)

    # ── get_twin_card ────────────────────────────────────────────────────

    def get_twin_card(self) -> dict:
        try:
            p        = self.build_profile()
            insights = self.generate_insights()

            phours = p["peak_focus_hours"]
            pdays  = p["peak_focus_days"]
            hour_str = (f"{min(phours)}-{max(phours)+1}pm" if len(phours) >= 2
                        else (f"{phours[0]}:00" if phours else "TBD"))
            days_str  = "/".join(d[:3] for d in pdays[:2]) if pdays else "TBD"
            peak_focus = f"{days_str} {hour_str}"

            n_stress   = len(p["stress_signals"]["stress_days"])
            stress_level = "high" if n_stress >= 3 else ("moderate" if n_stress >= 1 else "low")

            return {
                "productivity_score":    p["productivity"]["productivity_score"],
                "shield_effectiveness":  p["notification_health"]["shield_effectiveness"],
                "peak_focus":            peak_focus,
                "stress_level":          stress_level,
                "top_insight":           insights[0] if insights else "Building your profile...",
                "introvert_score":       p["social_energy"]["introvert_score"],
                "data_points":           p["data_points"],
                "insights":              insights[:3],
            }
        except Exception as exc:
            logger.error("get_twin_card failed: %s", exc)
            return {
                "productivity_score": 0,
                "shield_effectiveness": 0,
                "peak_focus": "TBD",
                "stress_level": "low",
                "top_insight": "Building your profile...",
                "introvert_score": 50,
                "data_points": 0,
                "insights": [],
            }
