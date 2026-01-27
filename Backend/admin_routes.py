# admin_routes.py
"""Flask Blueprint providing admin API endpoints.
This file was reconstructed after corruption. It defines routes used by the
frontend admin panel (admin.js) such as client management, filtering, logs,
stats, reports and bulk CSV upload.
"""

from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from functools import wraps
from db import users_collection, admins_collection, web_filter_collection, sessions_collection

# Blueprint registration
admin_routes = Blueprint("admin_routes", __name__)

# Secret key – same as used in auth_routes
SECRET_KEY = "your-secret-key"

def admin_required(f):
    """Decorator that checks for a valid JWT with role 'admin'."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        if not token:
            return jsonify({"status": "error", "msg": "Missing token"}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            if payload.get("role") != "admin":
                raise jwt.InvalidTokenError
        except Exception:
            return jsonify({"status": "error", "msg": "Invalid admin token"}), 403
        return f(*args, **kwargs)
    return decorated

# -------------------------------------------------------------------
# ADMIN CLIENT MANAGEMENT
# -------------------------------------------------------------------
@admin_routes.route("/admin/clients", methods=["GET"])
@admin_required
def get_clients():
    """Return a list of all student clients."""
    clients = list(users_collection.find({}, {"_id": 0}))
    return jsonify({"clients": clients}), 200

@admin_routes.route("/admin/clients", methods=["POST"])
@admin_required
def add_client():
    data = request.get_json()
    required = ["name", "roll_no", "device", "ip"]
    if not all(k in data for k in required):
        return jsonify({"status": "error", "msg": "Missing fields"}), 400
    # Default fields
    data.setdefault("data_usage", 0)
    data.setdefault("activity", "Idle")
    data.setdefault("blocked", False)
    users_collection.insert_one(data)
    return jsonify({"status": "success", "msg": "Client added"}), 201

@admin_routes.route("/admin/clients/<client_id>", methods=["PATCH"])
@admin_required
def update_client(client_id):
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "msg": "No data provided"}), 400
    result = users_collection.update_one({"_id": client_id}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"status": "error", "msg": "Client not found"}), 404
    return jsonify({"status": "success", "msg": "Client updated"}), 200

# -------------------------------------------------------------------
# FILTERING (manual blocks & category toggles)
# -------------------------------------------------------------------
@admin_routes.route("/admin/filtering", methods=["GET"])
@admin_required
def get_filtering():
    # Expected structure: {"manual_blocks": [], "categories": {}}
    doc = web_filter_collection.find_one({}) or {}
    manual = doc.get("manual_blocks", [])
    categories = doc.get("categories", {})
    return jsonify({"manual_blocks": manual, "categories": categories}), 200

@admin_routes.route("/admin/filtering/sites", methods=["POST"])
@admin_required
def add_manual_block():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"status": "error", "msg": "URL required"}), 400
    web_filter_collection.update_one(
        {},
        {"$addToSet": {"manual_blocks": url}},
        upsert=True,
    )
    return jsonify({"status": "success", "msg": f"Blocked {url}"}), 201

@admin_routes.route("/admin/filtering/sites", methods=["DELETE"])
@admin_required
def remove_manual_block():
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"status": "error", "msg": "URL required"}), 400
    web_filter_collection.update_one(
        {},
        {"$pull": {"manual_blocks": url}},
        upsert=True,
    )
    return jsonify({"status": "success", "msg": f"Unblocked {url}"}), 200

@admin_routes.route("/admin/filtering/categories", methods=["POST"])
@admin_required
def toggle_category():
    data = request.get_json()
    category = data.get("category")
    if not category:
        return jsonify({"status": "error", "msg": "Category required"}), 400
    # Flip the active flag for the given category
    doc = web_filter_collection.find_one({}) or {"categories": {}}
    cat_info = doc.get("categories", {}).get(category, {"active": False, "sites": []})
    cat_info["active"] = not cat_info.get("active", False)
    web_filter_collection.update_one(
        {},
        {"$set": {f"categories.{category}": cat_info}},
        upsert=True,
    )
    return jsonify({"status": "success", "category": category, "active": cat_info["active"]}), 200

# -------------------------------------------------------------------
# LOGS
# -------------------------------------------------------------------
@admin_routes.route("/admin/logs", methods=["GET"])
@admin_required
def get_logs():
    # For simplicity, logs are stored in a collection named "logs"
    from pymongo import DESCENDING
    logs_coll = current_app.config.get("LOGS_COLLECTION")
    if not logs_coll:
        return jsonify({"logs": []}), 200
    logs = list(logs_coll.find().sort("time", DESCENDING).limit(100))
    for l in logs:
        l.pop("_id", None)
    return jsonify({"logs": logs}), 200

# -------------------------------------------------------------------
# STATS (dashboard summary)
# -------------------------------------------------------------------
@admin_routes.route("/admin/stats", methods=["GET"])
@admin_required
def get_stats():
    client_count = users_collection.count_documents({})
    total_data = users_collection.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$data_usage"}}
    ])
    total_data_val = 0
    for doc in total_data:
        total_data_val = doc.get("total", 0)
    # Threats blocked – placeholder value
    threats_blocked = 0
    return jsonify({
        "client_count": client_count,
        "total_data": total_data_val,
        "threats_blocked": threats_blocked,
    }), 200

# -------------------------------------------------------------------
# REPORTS
# -------------------------------------------------------------------
@admin_routes.route("/admin/reports", methods=["POST"])
@admin_required
def generate_report():
    data = request.get_json()
    report_type = data.get("type")
    range_val = data.get("range")
    # Very simple mock implementation – return dummy headers & rows
    if report_type == "Top Bandwidth Users":
        headers = ["Rank", "Student ID", "Device", "Data Used (GB)"]
        rows = []
        for i, client in enumerate(users_collection.find().sort("data_usage", -1).limit(5), 1):
            rows.append([f"#{i}", client.get("roll_no"), client.get("device"), f"{client.get('data_usage',0)} GB"])
    elif report_type == "Blocked Site Activity":
        headers = ["Website", "Category", "Attempts (Simulated)"]
        rows = []
        doc = web_filter_collection.find_one({}) or {}
        manual = doc.get("manual_blocks", [])
        for site in manual:
            rows.append([site, "Manual", 0])
    else:
        headers = []
        rows = []
    return jsonify({"title": report_type, "headers": headers, "data": rows}), 200

# -------------------------------------------------------------------
# BULK CSV UPLOAD
# -------------------------------------------------------------------
@admin_routes.route("/admin/bulk-upload", methods=["POST"])
@admin_required
def bulk_upload():
    if "file" not in request.files:
        return jsonify({"status": "error", "msg": "No file uploaded"}), 400
    file = request.files["file"]
    # Very naive CSV handling – each line: name,roll_no,device,ip
    added = 0
    skipped = 0
    errors = []
    for line in file.stream.read().decode("utf-8").splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            skipped += 1
            continue
        name, roll_no, device, ip = parts[:4]
        try:
            users_collection.insert_one({
                "name": name,
                "roll_no": roll_no,
                "device": device,
                "ip": ip,
                "data_usage": 0,
                "activity": "Idle",
                "blocked": False,
            })
            added += 1
        except Exception as e:
            errors.append(str(e))
            skipped += 1
    return jsonify({"added": added, "skipped": skipped, "errors": errors}), 200

# -------------------------------------------------------------------
# END OF admin_routes
# -------------------------------------------------------------------