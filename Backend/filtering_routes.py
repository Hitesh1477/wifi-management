from flask import Blueprint, request, jsonify
from db import web_filter_collection
try:
    from linux_firewall_manager import update_firewall_rules
except ImportError:
    # Graceful fallback if running in non-admin/limited env
    def update_firewall_rules(): pass


filtering_blueprint = Blueprint('filtering', __name__)

DEFAULT_CATEGORIES = {
    "Gaming": {
        "active": True,
        "sites": ["steampowered.com", "twitch.tv", "roblox.com", "epicgames.com", "ea.com", "playvalorant.com", "minecraft.net", "battle.net", "ubisoft.com"]
    },
    "Social Media": {
        "active": False,
        "sites": ["tiktok.com", "instagram.com", "facebook.com", "twitter.com", "reddit.com", "snapchat.com", "pinterest.com", "linkedin.com"]
    },
    "Streaming": {
        "active": False,
        "sites": ["youtube.com", "netflix.com", "hulu.com", "disneyplus.com", "hbomax.com", "primevideo.com", "spotify.com", "peacocktv.com", "hotstar.com", "voot.com", "zee5.com", "sonyliv.com"]
    },
    "Messaging": {
        "active": False,
        "sites": ["whatsapp.com", "telegram.org", "discord.gg", "signal.org"]
    },
    "File Sharing": {
        "active": True,
        "sites": ["thepiratebay.org", "1337x.to", "megaupload.com", "wetransfer.com", "mediafire.com", "rarbg.to"]
    },
    "Proxy/VPN": {
        "active": True,
        "sites": ["nordvpn.com", "expressvpn.com", "hidemyass.com", "proxysite.com", "cyberghostvpn.com", "surfshark.com", "privateinternetaccess.com", "protonvpn.me", "tunnelbear.com"]
    }
}

def get_config():
    config = web_filter_collection.find_one({"type": "config"})
    if not config:
        config = {
            "type": "config",
            "manual_blocks": [],
            "categories": DEFAULT_CATEGORIES
        }
        web_filter_collection.insert_one(config)
    else:
        # Synch categories structure
        changed = False
        if "categories" not in config:
             config["categories"] = DEFAULT_CATEGORIES
             changed = True
        else:
            for cat, details in DEFAULT_CATEGORIES.items():
                if cat not in config["categories"]:
                    config["categories"][cat] = details
                    changed = True
        
        if changed:
            web_filter_collection.update_one({"type": "config"}, {"$set": {"categories": config["categories"]}})
            
    if "_id" in config:
        config["_id"] = str(config["_id"])
    return config

@filtering_blueprint.route('/filtering', methods=['GET'])
def get_filtering_status():
    config = get_config()
    return jsonify(config)

@filtering_blueprint.route('/filtering/sites', methods=['POST'])
def block_site():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"message": "URL is required"}), 400
    
    config = get_config()
    if url in config["manual_blocks"]:
         return jsonify({"message": "Site already blocked"}), 409
         
    web_filter_collection.update_one(
        {"type": "config"},
        {"$addToSet": {"manual_blocks": url}}
    )
    # Trigger firewall update
    try:
        update_firewall_rules()
    except Exception as e:
        print(f"Firewall update failed: {e}")
        
    return jsonify({"message": f"Blocked {url}"}), 200

@filtering_blueprint.route('/filtering/sites', methods=['DELETE'])
def unblock_site():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"message": "URL is required"}), 400
        
    web_filter_collection.update_one(
        {"type": "config"},
        {"$pull": {"manual_blocks": url}}
    )
    # Trigger firewall update
    try:
        update_firewall_rules()
    except Exception as e:
        print(f"Firewall update failed: {e}")

    return jsonify({"message": f"Unblocked {url}"}), 200

@filtering_blueprint.route('/filtering/categories', methods=['POST'])
def toggle_category():
    data = request.json
    category = data.get('category')
    if not category:
        return jsonify({"message": "Category is required"}), 400
        
    config = get_config()
    if category not in config["categories"]:
        return jsonify({"message": "Category not found"}), 404
        
    new_state = not config["categories"][category]["active"]
    web_filter_collection.update_one(
        {"type": "config"},
        {"$set": {f"categories.{category}.active": new_state}}
    )

    # Trigger firewall update
    try:
        update_firewall_rules()
    except Exception as e:
        print(f"Firewall update failed: {e}")
    
    return jsonify({"message": f"Toggled {category}", "active": new_state}), 200
