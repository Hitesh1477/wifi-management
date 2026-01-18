# model.py

CATEGORIES = {
    "video": ["youtube", "googlevideo", "netflix", "hotstar", "primevideo", "voot", "zee5", "sonyliv"],
    "social": ["instagram", "facebook", "tiktok", "snapchat", "twitter", "linkedin", "pinterest", "reddit"],
    "messaging": ["whatsapp", "telegram", "signal", "discord"],
    "gaming": [
        "battlegrounds", "pubg", "bgmi",           # BGMI / PUBG
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
        "playgames", "gameanalytics"                # Generic game services
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
