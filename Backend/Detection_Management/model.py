CATEGORIES = {
    "video": ["youtube", "googlevideo", "ytimg", "vimeo"],
    "learning": ["udemy", "coursera", "edx", "khanacademy"],
    "search": ["google.", "bing.com", "duckduckgo"],
    "social": ["facebook", "instagram", "twitter", "tiktok", "snapchat", "whatsapp"]
}

def classify(domain: str) -> str:
    d = domain.lower()

    for category, keywords in CATEGORIES.items():
        for key in keywords:
            if key in d:
                return category

    return "general"
