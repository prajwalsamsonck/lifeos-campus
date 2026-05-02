from context import get_context
from modes import get_mode


class NotificationScorer:
    URGENCY_TIERS = {
        "tier1": ["mom", "dad", "mother", "father", "family", "home"],
        "tier2": ["professor", "prof", "hod", "principal", "college",
                  "university", "moodle", "assignment"],
        "tier3": ["friend", "classmate", "roommate", "group"],
    }
    TIER_SCORES = {"tier1": 10, "tier2": 8, "tier3": 5, "tier4": 2}

    SOCIAL_APPS = frozenset(["instagram", "twitter", "youtube", "snapchat",
                              "reddit", "swiggy", "zomato", "netflix"])
    ACADEMIC_APPS = frozenset(["gmail", "teams", "moodle", "whatsapp", "sms", "phone"])

    def get_urgency_tier(self, sender: str) -> str:
        s = sender.lower()
        for tier, keywords in self.URGENCY_TIERS.items():
            if any(kw in s for kw in keywords):
                return tier
        return "tier4"

    def score_notification(self, notif_dict: dict, mode_name: str = None) -> int:
        if mode_name is None:
            mode_name = get_mode(get_context()).name

        sender = notif_dict.get("sender", "")
        app = notif_dict.get("app", "").lower()

        tier = self.get_urgency_tier(sender)
        urgency = self.TIER_SCORES[tier]

        if mode_name in ("class", "focus") and app in self.SOCIAL_APPS:
            relevance = 0.4
        elif app in self.ACADEMIC_APPS:
            relevance = 1.0
        else:
            relevance = 0.7

        return int(max(1, min(10, round(urgency * relevance, 0))))
