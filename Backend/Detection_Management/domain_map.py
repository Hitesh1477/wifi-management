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
    "fbcdn": "Facebook",
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
    
    # Gaming - BGMI/PUBG
    "battlegrounds": "BGMI",
    "pubg": "PUBG",
    "bgmi": "BGMI",
    "globh.com": "BGMI",  # Krafton/BGMI servers
    "krafton": "BGMI",
    "proximabeta": "BGMI",
    
    # Gaming - Other
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
    
    # Google Services
    "play.googleapis.com": "Google Play Store",
    "play-fe.googleapis.com": "Google Play Services",
    "googleapis.com": "Google Services",
    "android.googleapis.com": "Google Services",
    "gstatic.com": "Google Services",
    "doubleclick.net": "Google Ads",
    "app-measurement.com": "Google Analytics",
    
    # Music
    "spotify": "Spotify",
    "apresolve.spotify": "Spotify",
    "gaana": "Gaana",
    "jiosaavn": "JioSaavn",
    "wynk": "Wynk Music",
    
    # Other Apps
    "adjust.net": "App Analytics",
    "quizizz": "Quizizz",
    "listdl.com": "File Sharing",
    "memex-pa": "Google Services",
    "scorecardresearch": "Analytics",
    
    # System/OEM
    "heytapmobile.com": "Oppo Services",
    "allawnos.com": "Oppo Services",
    "coloros.com": "Oppo Services"
}

def get_app_name(domain: str) -> str:
    d = domain.lower()
    for key, app in DOMAIN_APP_MAP.items():
        if key in d:
            return app
    return "Unknown"
