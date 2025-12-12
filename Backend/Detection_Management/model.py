CATEGORIES = {
    "video": ["youtube", "googlevideo", "netflix"],
    "social": ["instagram", "facebook", "tiktok", "snapchat"],
    "messaging": ["whatsapp"],
    "search": ["google.", "bing.com", "duckduckgo"],
    "system": ["msftconnecttest", "firebase", "xiaomi", "miui"]
}

def classify(domain: str) -> str:
    d = domain.lower()
    for cat, keys in CATEGORIES.items():
        if any(k in d for k in keys):
            return cat
    return "general"
