import os
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")

CAMPUS_COORDS = {"lat": 12.9716, "lng": 77.5946}
HOSTEL_COORDS = {"lat": 12.9611, "lng": 77.5765}

_COORD_STRINGS = {
    "campus": f"{CAMPUS_COORDS['lat']},{CAMPUS_COORDS['lng']}",
    "hostel": f"{HOSTEL_COORDS['lat']},{HOSTEL_COORDS['lng']}",
}


class CommuteSkill:
    def get_travel_estimate(self, origin: str = "hostel", destination: str = "campus") -> dict:
        if not _MAPS_KEY:
            logger.debug("GOOGLE_MAPS_KEY not set — using mock travel estimate")
            return {"travel_minutes": 22, "mode": "transit", "source": "mock"}

        try:
            import requests
            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                "origins": _COORD_STRINGS.get(origin, origin),
                "destinations": _COORD_STRINGS.get(destination, destination),
                "mode": "transit",
                "key": _MAPS_KEY,
            }
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            duration = (
                data["rows"][0]["elements"][0]["duration"]["value"]
            )
            return {"travel_minutes": round(duration / 60), "mode": "transit", "source": "live"}
        except Exception as exc:
            logger.debug("Maps API failed (%s) — using mock", exc)
            return {"travel_minutes": 22, "mode": "transit", "source": "mock"}

    def build_commute_alert(self, event: dict, travel_estimate: dict) -> str:
        travel_minutes = travel_estimate.get("travel_minutes", 22)
        start_time = event["start_time"]
        departure_time = start_time - timedelta(minutes=travel_minutes)
        depart_in = max(0, round((departure_time - datetime.now()).total_seconds() / 60))
        arrival_time = start_time.strftime("%H:%M")
        location = event.get("location", "Campus")

        return (
            f"Leave in {depart_in} min for {event['summary']}\n"
            f"Bus 401 -> {location}\n"
            f"Travel time: ~{travel_minutes} min\n"
            f"Arrive by: {arrival_time}"
        )
