from datetime import datetime


def get_context() -> dict:
    now = datetime.now()
    hour = now.hour
    day = now.strftime("%A")

    # Mocked location zone inferred from time of day
    if 7 <= hour < 9 or 17 <= hour < 19:
        zone = "transit"
    elif 9 <= hour < 17:
        zone = "campus"
    else:
        zone = "hostel"

    return {
        "hour": hour,
        "day": day,
        "location_zone": zone,
        "calendar_events": [],  # placeholder — wire up Google Calendar here
    }
