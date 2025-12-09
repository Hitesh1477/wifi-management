# model.py
CATEGORIES = {
    "video": ["youtube","googlevideo","ytimg","vimeo"],
    "learning": ["udemy","coursera","edx","khanacademy"],
    "search": ["google.","bing.com","duckduckgo"],
    "social": ["facebook","instagram","twitter","tiktok"]
}

def classify(domain: str) -> str:
    d = domain.lower()
    for cat, keys in CATEGORIES.items():
        for k in keys:
            if k in d:
                return cat
    return "general"
