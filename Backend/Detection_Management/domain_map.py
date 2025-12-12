DOMAIN_APP_MAP = {
    "youtube.com": "YouTube",
    "googlevideo.com": "YouTube Streaming",
    "ytimg.com": "YouTube",
    "youtubei.googleapis.com": "YouTube",

    "google.com": "Google Search",
    "google.co.in": "Google Search",

    "whatsapp.net": "WhatsApp",
    "g.whatsapp.net": "WhatsApp",

    "instagram.com": "Instagram",
    "cdninstagram.com": "Instagram",
    "fbcdn.net": "Facebook/Instagram CDN",

    "facebook.com": "Facebook",

    "msftconnecttest.com": "Microsoft Connectivity Test",

    "pubsub.googleapis.com": "Google Services",
    "play.googleapis.com": "Google Play Store",
    "android.clients.google.com": "Google Android Services",
}

def identify_app(domain: str):
    domain = domain.lower()
    for key, app in DOMAIN_APP_MAP.items():
        if key in domain:
            return app

    if "googlevideo.com" in domain:
        return "YouTube Streaming"

    return "Unknown"
