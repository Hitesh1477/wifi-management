from flask import Blueprint, request, jsonify, current_app as app
from werkzeug.security import check_password_hash
from functools import wraps
from pymongo import MongoClient
import jwt, datetime

# ✅ MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']
admins_collection = db['admins']
users_collection = db['users']

# ✅ Middleware for token check
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({"message": "Token missing"}), 401

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            if data.get("role") != "admin":
                return jsonify({"message": "Unauthorized"}), 403

        except Exception:
            return jsonify({"message": "Invalid or expired token"}), 401

        return f(*args, **kwargs)
    return decorated

admin_routes = Blueprint("admin_routes", __name__)

# ✅ Admin Login
@admin_routes.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    admin = admins_collection.find_one({"username": username})

    if not admin or not check_password_hash(admin["password"], password):
        return jsonify({"message": "Invalid admin credentials"}), 401

    token = jwt.encode({
        "username": username,
        "role": "admin",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({"message": "Admin login successful", "token": token})

@admin_routes.route("/admin/stats", methods=["GET"])
@admin_required
def admin_stats():
    total_users = users_collection.count_documents({})
    active_users = users_collection.count_documents({"status": "online"})  # later when tracking usage
    blocked_users = users_collection.count_documents({"blocked": True})

    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users
    }), 200

@admin_routes.route('/admin/clients', methods=['GET'])
@admin_required
def admin_clients():
    # Return list of non-admin users (do not expose passwords)
    clients_cursor = users_collection.find({"role": {"$ne": "admin"}}, {"password": 0})
    clients = []
    for c in clients_cursor:
        c['_id'] = str(c.get('_id'))
        clients.append(c)
    return jsonify({"clients": clients}), 200

@admin_routes.route('/admin/logs', methods=['GET'])
@admin_required
def admin_logs():
    # If you have a 'logs' collection, return recent logs; otherwise return empty list
    logs = []
    if 'logs' in db.list_collection_names():
        logs_cursor = db['logs'].find().sort([('_id', -1)]).limit(100)
        for l in logs_cursor:
            l['_id'] = str(l.get('_id'))
            logs.append(l)
    return jsonify({"logs": logs}), 200
