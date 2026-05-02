from dataclasses import dataclass
from typing import Dict


@dataclass
class Mode:
    name: str
    dnd: bool
    sound: str  # "silent" | "low" | "normal"
    notif_score_threshold: int  # 0–10; higher = only urgent notifications get through


MODES: Dict[str, Mode] = {
    "sleep":   Mode("sleep",   dnd=True,  sound="silent", notif_score_threshold=9),
    "commute": Mode("commute", dnd=False, sound="low",    notif_score_threshold=5),
    "class":   Mode("class",   dnd=True,  sound="silent", notif_score_threshold=8),
    "focus":   Mode("focus",   dnd=True,  sound="low",    notif_score_threshold=7),
    "hostel":  Mode("hostel",  dnd=False, sound="normal", notif_score_threshold=3),
}


def get_mode(ctx: dict) -> Mode:
    hour = ctx["hour"]
    zone = ctx["location_zone"]
    is_weekday = ctx["day"] not in ("Saturday", "Sunday")

    if hour >= 22 or hour < 6:
        return MODES["sleep"]

    if zone == "transit":
        return MODES["commute"]

    if zone == "campus" and is_weekday:
        if 8 <= hour < 13:
            return MODES["class"]
        return MODES["focus"]

    return MODES["hostel"]
