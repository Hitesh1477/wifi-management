# model.py

CATEGORIES = {
    "video": ["youtube", "googlevideo", "netflix", "hotstar", "primevideo", "voot", "zee5", "sonyliv"],
    "social": ["instagram", "facebook", "tiktok", "snapchat", "twitter", "linkedin", "pinterest", "reddit"],
    "messaging": ["whatsapp", "telegram", "signal"],  # Removed discord (used for gaming)
    "gaming": [
        # BGMI / PUBG specific domains
        "battlegrounds", "pubg", "bgmi", "krafton", "pubgmobile",
        "tdm.globh.com", "in-voice.globh.com", "globh",  # BGMI voice & infrastructure
        "intl.garena.com", "dlied1.cdntips.net",         # Gaming CDN
        
        # Gaming services & APIs (when used during gaming)
        "gameanalytics", "playgames", "play.googleapis.com",  # Google Play Games
        "appcenter.ms", "mobilecenter.ms",                # Gaming analytics
        "ap.indusappstore.com", "api.indusappstore.com",  # Gaming app store
        
        # Other popular mobile games
        "freefire", "garena",                       # Free Fire
        "callofduty", "activision",                 # Call of Duty
        "minecraft", "roblox",                      # Minecraft, Roblox
        "supercell", "clashofclans", "clashroyale", # Supercell games
        "candycrush", "king.com",                   # Candy Crush
        "mobilelegends", "mlbb",                    # Mobile Legends
        "genshin", "mihoyo",                        # Genshin Impact
        "valorant", "riotgames", "leagueoflegends", # Riot Games
        "epicgames", "fortnite",                    # Epic Games
        "steam", "steampowered",                    # Steam
        "discord",                                  # Discord (primarily gaming)
    ],
    "search": ["google.", "bing.com", "duckduckgo"],
    "system": ["msftconnecttest", "firebase", "xiaomi", "miui", "connectivity-check"]
}

def classify(domain: str) -> str:
    d = domain.lower()
    for cat, keys in CATEGORIES.items():
        if any(k in d for k in keys):
            return cat
    return "general"
