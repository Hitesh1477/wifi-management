# domain_map.py

DOMAIN_APP_MAP = {
    "youtube": "YouTube",
    "googlevideo": "YouTube Streaming",
    "ytimg": "YouTube",
    "instagram": "Instagram",
    "facebook": "Facebook",
    "whatsapp": "WhatsApp",
    "netflix": "Netflix",
    "google.": "Google Search",
    "bing.com": "Bing Search",
    "duckduckgo": "DuckDuckGo",
    "play.googleapis.com": "Google Play Store"
}

def get_app_name(domain: str) -> str:
    d = domain.lower()
    for key, app in DOMAIN_APP_MAP.items():
        if key in d:
            return app
    return "Unknown"
