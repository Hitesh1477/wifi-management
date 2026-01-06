# domain_map.py

DOMAIN_APP_MAP = {
    # Video
    "youtube": "YouTube",
    "googlevideo": "YouTube Streaming",
    "ytimg": "YouTube",
    "netflix": "Netflix",
    "hotstar": "Hotstar",
    "primevideo": "Prime Video",
    
    # Social
    "instagram": "Instagram",
    "facebook": "Facebook",
    "twitter": "Twitter",
    "linkedin": "LinkedIn",
    "pinterest": "Pinterest",
    "reddit": "Reddit",
    "snapchat": "Snapchat",
    "tiktok": "TikTok",
    
    # Messaging
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "discord": "Discord",
    
    # Gaming
    "battlegrounds": "BGMI",
    "pubg": "PUBG",
    "bgmi": "BGMI",
    "freefire": "Free Fire",
    "garena": "Free Fire",
    "callofduty": "Call of Duty",
    "activision": "Call of Duty",
    "minecraft": "Minecraft",
    "roblox": "Roblox",
    "supercell": "Supercell Game",
    "clashofclans": "Clash of Clans",
    "clashroyale": "Clash Royale",
    "mobilelegends": "Mobile Legends",
    "genshin": "Genshin Impact",
    "mihoyo": "Genshin Impact",
    "valorant": "Valorant",
    "fortnite": "Fortnite",
    "steam": "Steam",
    
    # Search
    "google.": "Google Search",
    "bing.com": "Bing Search",
    "duckduckgo": "DuckDuckGo",
    
    # System
    "play.googleapis.com": "Google Play Store"
}

def get_app_name(domain: str) -> str:
    d = domain.lower()
    for key, app in DOMAIN_APP_MAP.items():
        if key in d:
            return app
    return "Unknown"
