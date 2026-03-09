#pip install pandas openpyxl xlrd

from flask import Blueprint, request, jsonify, current_app as app
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from pymongo import MongoClient
import jwt, datetime
from bson.objectid import ObjectId
import pandas as pd
import io
import threading
import logging
from linux_firewall_manager import update_firewall_rules
from bandwidth_manager import (
    apply_bandwidth_for_active_users,
    assign_auto_bandwidth,
    get_bandwidth_presets,
    get_user_activity_snapshot,
    refresh_auto_bandwidth_profiles,
    resolve_effective_bandwidth,
)

# [OK] MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']
admins_collection = db['admins']
users_collection = db['users']
web_filter_collection = db['web_filter']
notifications_collection = db['notifications']
logger = logging.getLogger(__name__)

DEFAULT_ADMIN_TIMEOUT_HOURS = 2
DEFAULT_STUDENT_TIMEOUT_HOURS = 2
MIN_TIMEOUT_HOURS = 1
MAX_TIMEOUT_HOURS = 24


def _parse_timeout_hours(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_session_timeout_settings():
    settings_col = db['admin_settings']
    defaults = {
        "admin_timeout_hours": DEFAULT_ADMIN_TIMEOUT_HOURS,
        "student_timeout_hours": DEFAULT_STUDENT_TIMEOUT_HOURS,
    }

    try:
        doc = settings_col.find_one({"type": "session_timeout"}) or {}
    except Exception:
        return defaults

    admin_hours = _parse_timeout_hours(doc.get("admin_timeout_hours"))
    student_hours = _parse_timeout_hours(doc.get("student_timeout_hours"))

    if admin_hours is None:
        admin_hours = defaults["admin_timeout_hours"]
    if student_hours is None:
        student_hours = defaults["student_timeout_hours"]

    admin_hours = max(MIN_TIMEOUT_HOURS, min(MAX_TIMEOUT_HOURS, admin_hours))
    student_hours = max(MIN_TIMEOUT_HOURS, min(MAX_TIMEOUT_HOURS, student_hours))

    return {
        "admin_timeout_hours": admin_hours,
        "student_timeout_hours": student_hours,
    }


def _medium_preset_mbps() -> int:
    return int(get_bandwidth_presets().get("medium", 5))

# [OK] Middleware for token check
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

def _find_user_by_mixed_id(id):
    try:
        oid = ObjectId(id)
        doc = users_collection.find_one({"_id": oid})
        if doc:
            return doc
    except Exception:
        pass
    doc = users_collection.find_one({"_id": id})
    if doc:
        return doc
    doc = users_collection.find_one({"roll_no": id})
    return doc


def _build_fallback_auto_recommendation(roll_no, reason=""):
    """Fallback recommendation when ML/activity detection is unavailable."""
    explanation = "ML/activity recommendation unavailable; applying MEDIUM baseline tier."
    if reason:
        explanation = f"{explanation} Reason: {reason}"

    recommendation = {
        "roll_no": roll_no,
        "tier": "medium",
        "confidence": 0.0,
        "recommended_mbps": _medium_preset_mbps(),
        "detected_activity": "General Browsing",
        "dominant_category": "general",
        "total_requests": 0,
        "explanation": explanation,
        "fallback": True,
    }

    try:
        users_collection.update_one(
            {"roll_no": str(roll_no)},
            {
                "$set": {
                    "bandwidth_limit": "auto",
                    "bandwidth_auto_assigned": "medium",
                    "bandwidth_auto_confidence": 0.0,
                    "bandwidth_last_updated": datetime.datetime.utcnow(),
                    "detected_activity": "General Browsing",
                    "activity_category": "general",
                    "activity_total_requests": 0,
                }
            },
        )
    except Exception as db_error:
        logger.warning("Failed to persist fallback auto bandwidth for %s: %s", roll_no, db_error)

    return recommendation

# [OK] Admin Login
@admin_routes.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    admin = admins_collection.find_one({"username": username})

    if not admin or not check_password_hash(admin["password"], password):
        return jsonify({"message": "Invalid admin credentials"}), 401

    timeout_settings = _get_session_timeout_settings()
    admin_timeout_hours = timeout_settings["admin_timeout_hours"]

    token = jwt.encode({
        "username": username,
        "role": "admin",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=admin_timeout_hours)
    }, app.config["SECRET_KEY"], algorithm="HS256")

    return jsonify({
        "message": "Admin login successful",
        "token": token,
        "session_timeout_hours": admin_timeout_hours,
    })

@admin_routes.route('/admin/change-password', methods=['POST'])
@admin_required
def admin_change_password():
    """Change the admin account password."""
    data = request.get_json() or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')

    if not current_password or not new_password:
        return jsonify({"message": "current_password and new_password are required"}), 400

    if len(new_password) < 6:
        return jsonify({"message": "New password must be at least 6 characters"}), 400

    # Decode token to get username
    token = request.headers['Authorization'].split(" ")[1]
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        username = payload.get('username')
    except Exception:
        return jsonify({"message": "Invalid token"}), 401

    admin = admins_collection.find_one({"username": username})
    if not admin:
        return jsonify({"message": "Admin not found"}), 404

    if not check_password_hash(admin['password'], current_password):
        return jsonify({"message": "Current password is incorrect"}), 403

    admins_collection.update_one(
        {"username": username},
        {"$set": {"password": generate_password_hash(new_password)}}
    )
    return jsonify({"message": "Password updated successfully"}), 200


@admin_routes.route('/admin/settings/timeout', methods=['GET', 'POST'])
@admin_required
def admin_session_timeout():
    """Get or update session timeout settings."""
    settings_col = db['admin_settings']

    if request.method == 'GET':
        return jsonify(_get_session_timeout_settings()), 200

    data = request.get_json() or {}
    admin_hours = _parse_timeout_hours(data.get("admin_timeout_hours"))
    student_hours = _parse_timeout_hours(data.get("student_timeout_hours"))

    if admin_hours is None or student_hours is None:
        return jsonify({"message": "admin_timeout_hours and student_timeout_hours must be numbers"}), 400

    if not (MIN_TIMEOUT_HOURS <= admin_hours <= MAX_TIMEOUT_HOURS) or not (MIN_TIMEOUT_HOURS <= student_hours <= MAX_TIMEOUT_HOURS):
        return jsonify({"message": "Timeout must be between 1 and 24 hours"}), 400

    settings_col.update_one(
        {"type": "session_timeout"},
        {"$set": {
            "type": "session_timeout",
            "admin_timeout_hours": admin_hours,
            "student_timeout_hours": student_hours
        }},
        upsert=True
    )
    return jsonify({"message": "Timeout settings saved"}), 200


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

@admin_routes.route("/admin/dashboard/stats", methods=["GET"])
@admin_required
def dashboard_stats():
    """Get real-time dashboard statistics"""
    try:
        # Get active sessions collection
        active_sessions_col = db['active_sessions'] if 'active_sessions' in db.list_collection_names() else None
        detections_col = db['detections'] if 'detections' in db.list_collection_names() else None
        blocked_users_col = db['blocked_users'] if 'blocked_users' in db.list_collection_names() else None
        
        # 1. Count active students (from active_sessions with status "active")
        active_students = 0
        if active_sessions_col is not None:
            active_students = active_sessions_col.count_documents({"status": "active"})
        
        # 2. Calculate total data usage in last 24 hours (from detections)
        # We'll use detection count as a proxy for data usage (each detection ≈ 0.01 GB)
        now = datetime.datetime.utcnow()
        last_24h = now - datetime.timedelta(hours=24)
        
        total_data_gb = 0
        if detections_col is not None:
            detection_count_24h = detections_col.count_documents({"timestamp": {"$gte": last_24h}})
            total_data_gb = round(detection_count_24h * 0.01, 1)  # Approximate data usage
        
        # 3. Count threats blocked in last 24 hours
        threats_blocked = 0
        if blocked_users_col is not None:
            # Count blocks created in last 24h
            threats_blocked += blocked_users_col.count_documents({
                "blocked_at": {"$gte": last_24h}
            })
        
        # Also count high-risk detections (proxy, vpn, adult, malware)
        if detections_col is not None:
            high_risk_categories = ['proxy', 'vpn', 'adult', 'malware']
            threats_blocked += detections_col.count_documents({
                "timestamp": {"$gte": last_24h},
                "category": {"$in": high_risk_categories}
            })
        
        # 4. Get recent traffic data for chart (last 10 data points, grouped by 2-minute intervals)
        traffic_data = {
            "labels": [],
            "download": [],
            "upload": []
        }
        
        if detections_col is not None:
            # Get detections from last 20 minutes, grouped by 2-minute intervals
            last_20min = now - datetime.timedelta(minutes=20)
            pipeline = [
                {"$match": {"timestamp": {"$gte": last_20min}}},
                {"$group": {
                    "_id": {
                        "$subtract": [
                            {"$toLong": "$timestamp"},
                            {"$mod": [{"$toLong": "$timestamp"}, 120000]}  # 2 minutes in ms
                        ]
                    },
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}},
                {"$limit": 10}
            ]
            
            try:
                results = list(detections_col.aggregate(pipeline))
                for r in results:
                    # Convert timestamp to IST time string
                    ts = datetime.datetime.fromtimestamp(r["_id"] / 1000.0)
                    time_str = ts.strftime('%H:%M:%S')
                    traffic_data["labels"].append(time_str)
                    # Simulate download/upload based on detection count
                    download_kb = r["count"] * 50  # Approx 50 KB per detection
                    upload_kb = r["count"] * 15    # Upload is typically less
                    traffic_data["download"].append(download_kb)
                    traffic_data["upload"].append(upload_kb)
            except Exception as e:
                print(f"Error aggregating traffic data: {e}")
                # Fallback to empty data
                pass
        
        # If no traffic data, provide at least one point to avoid empty chart
        if len(traffic_data["labels"]) == 0:
            current_time = datetime.datetime.now().strftime('%H:%M:%S')
            traffic_data["labels"] = [current_time]
            traffic_data["download"] = [0]
            traffic_data["upload"] = [0]
        
        return jsonify({
            "active_students": active_students,
            "total_data_gb": total_data_gb,
            "threats_blocked": threats_blocked,
            "traffic_data": traffic_data
        }), 200
        
    except Exception as e:
        print(f"Error in dashboard_stats: {e}")
        return jsonify({
            "error": str(e),
            "active_students": 0,
            "total_data_gb": 0,
            "threats_blocked": 0,
            "traffic_data": {"labels": [], "download": [], "upload": []}
        }), 500

# ========================================
# NOTIFICATIONS SYSTEM
# ========================================

def create_notification(level, notification_type, user, message):
    """
    Helper function to create a notification
    
    Args:
        level: 'info', 'warn', or 'error'
        notification_type: 'bandwidth', 'security', 'login', 'system'
        user: username or 'SYSTEM' or 'ADMIN'
        message: notification message text
    """
    try:
        notification = {
            "level": level,
            "type": notification_type,
            "user": user,
            "message": message,
            "timestamp": datetime.datetime.utcnow(),
            "read": False
        }
        notifications_collection.insert_one(notification)
        print(f"✅ Notification created: [{level.upper()}] {message}")
    except Exception as e:
        print(f"❌ Failed to create notification: {e}")

@admin_routes.route("/admin/notifications", methods=["GET"])
@admin_required
def get_notifications():
    """Get notifications for admin panel"""
    try:
        import pytz
        
        # Optional filter for unread only
        unread_only = request.args.get('unread', 'false').lower() == 'true'
        
        # Build query
        query = {}
        if unread_only:
            query['read'] = False
        
        # Fetch notifications (last 50, sorted by newest first)
        notifications_cursor = notifications_collection.find(query).sort([('timestamp', -1)]).limit(50)
        
        notifications = []
        ist = pytz.timezone('Asia/Kolkata')
        
        for notif in notifications_cursor:
            # Convert timestamp to IST
            ts = notif.get('timestamp')
            if ts:
                if hasattr(ts, 'replace'):
                    if ts.tzinfo is None:
                        ts_utc = pytz.utc.localize(ts)
                    else:
                        ts_utc = ts
                    ts_ist = ts_utc.astimezone(ist)
                    time_str = ts_ist.strftime('%I:%M %p, %d %b')
                else:
                    time_str = str(ts)
            else:
                time_str = 'N/A'
            
            notifications.append({
                '_id': str(notif.get('_id')),
                'level': notif.get('level', 'info'),
                'type': notif.get('type', 'system'),
                'user': notif.get('user', 'SYSTEM'),
                'message': notif.get('message', ''),
                'timestamp': time_str,
                'read': notif.get('read', False)
            })
        
        return jsonify({"notifications": notifications}), 200
        
    except Exception as e:
        print(f"Error fetching notifications: {e}")
        return jsonify({"error": str(e), "notifications": []}), 500

@admin_routes.route("/admin/notifications/count", methods=["GET"])
@admin_required
def get_notifications_count():
    """Get count of unread notifications"""
    try:
        unread_count = notifications_collection.count_documents({"read": False})
        return jsonify({"count": unread_count}), 200
    except Exception as e:
        print(f"Error counting notifications: {e}")
        return jsonify({"error": str(e), "count": 0}), 500

@admin_routes.route("/admin/notifications/mark-read", methods=["POST"])
@admin_required
def mark_notifications_read():
    """Mark notification(s) as read"""
    try:
        data = request.get_json() or {}
        notification_id = data.get('id')
        mark_all = data.get('all', False)
        
        if mark_all:
            # Mark all notifications as read
            result = notifications_collection.update_many(
                {"read": False},
                {"$set": {"read": True}}
            )
            return jsonify({
                "message": f"Marked {result.modified_count} notifications as read",
                "count": result.modified_count
            }), 200
        elif notification_id:
            # Mark specific notification as read
            try:
                oid = ObjectId(notification_id)
                result = notifications_collection.update_one(
                    {"_id": oid},
                    {"$set": {"read": True}}
                )
                if result.modified_count > 0:
                    return jsonify({"message": "Notification marked as read"}), 200
                else:
                    return jsonify({"message": "Notification not found or already read"}), 404
            except Exception:
                return jsonify({"message": "Invalid notification ID"}), 400
        else:
            return jsonify({"message": "Please provide 'id' or set 'all' to true"}), 400
            
    except Exception as e:
        print(f"Error marking notifications as read: {e}")
        return jsonify({"error": str(e)}), 500


@admin_routes.route('/admin/clients', methods=['GET'])
@admin_required
def admin_clients():
    """Return list of non-admin users with their latest activity from detections"""
    try:
        clients_cursor = users_collection.find({"role": {"$ne": "admin"}}, {"password": 0})
        clients = []
        
        # Get collections
        detections_col = db['detections'] if 'detections' in db.list_collection_names() else None
        blocked_users_col = db['blocked_users'] if 'blocked_users' in db.list_collection_names() else None
        active_sessions_col = db['active_sessions'] if 'active_sessions' in db.list_collection_names() else None
        
        for c in clients_cursor:
            c['_id'] = str(c.get('_id'))
            roll_no = c.get('roll_no')
            
            # Check if user is blocked in blocked_users collection
            is_blocked = False
            block_status = None
            block_details = None
            
            if blocked_users_col is not None and roll_no:
                block_doc = blocked_users_col.find_one({"roll_no": roll_no, "status": "blocked"})
                if block_doc:
                    is_blocked = True
                    ban_type = block_doc.get("ban_type", "temporary")
                    expires_at = block_doc.get("expires_at")
                    
                    if ban_type == "permanent":
                        block_status = "Blocked (permanent)"
                    elif expires_at:
                        # Show expiry time for temporary bans
                        import pytz
                        ist = pytz.timezone('Asia/Kolkata')
                        # Convert UTC to IST
                        if hasattr(expires_at, 'replace'):
                            expires_at_utc = expires_at.replace(tzinfo=pytz.utc)
                            expires_at_ist = expires_at_utc.astimezone(ist)
                            expiry_str = expires_at_ist.strftime('%I:%M %p, %d %b')
                            block_status = f"Blocked until {expiry_str}"
                        else:
                            block_status = f"Blocked (temporary)"
                    else:
                        block_status = f"Blocked (temporary)"
                    
                    block_details = {
                        "reason": block_doc.get("reason", "No reason provided"),
                        "confidence": block_doc.get("confidence", 0),
                        "blocked_at": block_doc.get("blocked_at")
                    }
            
            # Determine status
            if is_blocked:
                # User is blocked
                c['status'] = block_status
                c['blocked'] = True
                if block_details:
                    c['block_details'] = block_details
            else:
                # Check if user has active session
                has_active_session = False
                if active_sessions_col is not None and roll_no:
                    session = active_sessions_col.find_one({"roll_no": roll_no, "status": "active"})
                    if session:
                        has_active_session = True
                        c['ip_address'] = session.get('client_ip', 'N/A')
                
                if has_active_session:
                    c['status'] = "Online"
                else:
                    c['status'] = "Offline"
                
                c['blocked'] = False
            
            # Get IP from active session if not already set
            if not c.get('ip_address'):
                if active_sessions_col is not None and roll_no:
                    session = active_sessions_col.find_one({"roll_no": roll_no, "status": "active"})
                    if session:
                        c['ip_address'] = session.get('client_ip', 'N/A')
                    else:
                        c['ip_address'] = c.get('ip_address', 'N/A')
                else:
                    c['ip_address'] = c.get('ip_address', 'N/A')
            
            # Get latest activity from detections
            if detections_col is not None and roll_no:
                try:
                    # Get most recent detection for this user
                    latest = detections_col.find_one(
                        {"roll_no": roll_no}, 
                        sort=[("timestamp", -1)]
                    )
                    if latest:
                        c['activity'] = f"{latest.get('app_name', 'Unknown')} ({latest.get('domain', 'N/A')})"
                    else:
                        c['activity'] = c.get('activity', 'Idle')
                    
                    # Count detections as rough "data usage" (number of requests)
                    detection_count = detections_col.count_documents({"roll_no": roll_no})
                    c['data_usage'] = round(detection_count * 0.01, 2)
                except Exception:
                    c['activity'] = c.get('activity', 'Idle')
                    c['data_usage'] = 0
            else:
                c['activity'] = c.get('activity', 'Idle')
                c['data_usage'] = 0

            # Activity-aware enrichment for bandwidth page
            try:
                if roll_no:
                    snapshot = get_user_activity_snapshot(roll_no, window_minutes=120)
                    if snapshot.get('total_requests', 0) > 0:
                        c['detected_activity'] = snapshot.get('detected_activity')
                        c['activity_category'] = snapshot.get('dominant_category', 'general')
                        c['activity'] = snapshot.get('detected_activity', c.get('activity', 'Idle'))
                    else:
                        c['detected_activity'] = c.get('activity', 'Idle')
                else:
                    c['detected_activity'] = c.get('activity', 'Idle')
            except Exception:
                c['detected_activity'] = c.get('activity', 'Idle')

            # Resolve effective bandwidth (preset/manual/auto)
            policy = resolve_effective_bandwidth(c)
            c['bandwidth_mode'] = policy.get('mode', 'preset')
            c['bandwidth_effective_tier'] = policy.get('tier', 'medium')
            c['bandwidth_effective_mbps'] = policy.get('effective_mbps', _medium_preset_mbps())
            
            clients.append(c)
        
        return jsonify({
            "clients": clients,
            "bandwidth_presets": get_bandwidth_presets(),
        }), 200
    except Exception as e:
        print(f"Error in admin_clients: {e}")
        return jsonify({"error": str(e), "clients": []}), 500

@admin_routes.route('/admin/clients', methods=['POST'])
@admin_required
def admin_add_client():
    data = request.get_json() or {}
    roll_no = (data.get('roll_no') or '').strip()
    password = (data.get('password') or '').strip()
    activity = (data.get('activity') or '').strip() or 'Idle'

    if not roll_no:
        return jsonify({"message": "roll_no required"}), 400
    if users_collection.find_one({"roll_no": roll_no}):
        return jsonify({"message": "User already exists"}), 409

    doc = {
        "roll_no": roll_no,
        "role": "student",
        "blocked": False,
        "activity": activity,
        "bandwidth_limit": "medium",
        "bandwidth_effective_tier": "medium",
        "bandwidth_effective_mbps": _medium_preset_mbps(),
    }
    if password:
        doc["password"] = generate_password_hash(password)

    inserted = users_collection.insert_one(doc)
    return jsonify({"message": "Client added", "id": str(inserted.inserted_id)}), 201

@admin_routes.route('/admin/clients/<id>', methods=['GET'])
@admin_required
def admin_get_client(id):
    c = _find_user_by_mixed_id(id)
    if not c:
        return jsonify({"message": "Not found"}), 404
    c['_id'] = str(c['_id'])
    return jsonify({"client": c}), 200

@admin_routes.route('/admin/clients/<id>', methods=['PATCH'])
@admin_required
def admin_update_client(id):
    doc = _find_user_by_mixed_id(id)
    if not doc:
        return jsonify({"message": "Not found"}), 404
    oid = doc.get('_id')
    roll_no = doc.get('roll_no')
    data = request.get_json() or {}

    updates = {}
    unset_fields = {}
    bandwidth_updated = False
    if 'roll_no' in data and isinstance(data['roll_no'], str) and data['roll_no'].strip():
        new_roll = data['roll_no'].strip()
        # prevent duplicate roll_no
        existing = users_collection.find_one({"roll_no": new_roll, "_id": {"$ne": oid}})
        if existing:
            return jsonify({"message": "roll_no already in use"}), 409
        updates['roll_no'] = new_roll

    if 'password' in data and isinstance(data['password'], str) and data['password'].strip():
        updates['password'] = generate_password_hash(data['password'].strip())

    # Handle blocking/unblocking - write to blocked_users collection
    if 'blocked' in data:
        should_block = bool(data['blocked'])
        updates['blocked'] = should_block
        
        blocked_users_col = db['blocked_users']
        
        if should_block:
            # Block the user - add to blocked_users collection
            blocked_users_col.update_one(
                {"roll_no": roll_no},
                {
                    "$set": {
                        "roll_no": roll_no,
                        "ban_type": "permanent",  # Admin blocks are permanent by default
                        "confidence": 1.0,
                        "reason": "Manually blocked by admin",
                        "blocked_at": datetime.datetime.utcnow(),
                        "expires_at": None,
                        "status": "blocked"
                    }
                },
                upsert=True
            )
        else:
            # Unblock the user - remove from blocked_users collection
            blocked_users_col.delete_one({"roll_no": roll_no})

    if 'activity' in data and isinstance(data['activity'], str):
        updates['activity'] = data['activity']

    # Handle bandwidth_limit modes: low/medium/high/manual/auto
    if 'bandwidth_limit' in data:
        raw_limit = data['bandwidth_limit']

        if isinstance(raw_limit, (int, float)):
            updates['bandwidth_limit'] = 'manual'
            updates['bandwidth_custom_value'] = min(500, max(1, int(float(raw_limit))))
            unset_fields['bandwidth_auto_assigned'] = ''
            unset_fields['bandwidth_auto_confidence'] = ''
            bandwidth_updated = True
        elif isinstance(raw_limit, str):
            normalized_limit = raw_limit.strip().lower()
            if normalized_limit not in ('low', 'medium', 'high', 'manual', 'auto'):
                return jsonify({"message": "Invalid bandwidth_limit value"}), 400

            updates['bandwidth_limit'] = normalized_limit
            bandwidth_updated = True

            if normalized_limit == 'manual':
                custom_value = data.get('bandwidth_custom_value', doc.get('bandwidth_custom_value', 50))
                try:
                    updates['bandwidth_custom_value'] = min(500, max(1, int(float(custom_value))))
                except (TypeError, ValueError):
                    return jsonify({"message": "Invalid bandwidth_custom_value"}), 400
                unset_fields['bandwidth_auto_assigned'] = ''
                unset_fields['bandwidth_auto_confidence'] = ''
            elif normalized_limit == 'auto':
                unset_fields['bandwidth_custom_value'] = ''
            else:
                unset_fields['bandwidth_custom_value'] = ''
                unset_fields['bandwidth_auto_assigned'] = ''
                unset_fields['bandwidth_auto_confidence'] = ''
        else:
            return jsonify({"message": "Invalid bandwidth_limit payload"}), 400

    if 'bandwidth_custom_value' in data:
        if ('bandwidth_limit' not in data) or (updates.get('bandwidth_limit') == 'manual') or (doc.get('bandwidth_limit') == 'manual'):
            raw_custom_value = data.get('bandwidth_custom_value')
            if raw_custom_value is None:
                return jsonify({"message": "Invalid bandwidth_custom_value"}), 400
            try:
                custom_value = min(500, max(1, int(float(str(raw_custom_value)))))
            except (TypeError, ValueError):
                return jsonify({"message": "Invalid bandwidth_custom_value"}), 400
            updates['bandwidth_limit'] = updates.get('bandwidth_limit', 'manual')
            updates['bandwidth_custom_value'] = custom_value
            unset_fields['bandwidth_auto_assigned'] = ''
            unset_fields['bandwidth_auto_confidence'] = ''
            bandwidth_updated = True

    if not updates and not unset_fields:
        return jsonify({"message": "No changes"}), 400

    update_doc = {}
    if updates:
        update_doc['$set'] = updates
    if unset_fields:
        update_doc['$unset'] = unset_fields

    res = users_collection.update_one({"_id": oid}, update_doc)
    if res.matched_count == 0:
        return jsonify({"message": "Not found"}), 404

    roll_no_for_update = updates.get('roll_no', roll_no)
    auto_recommendation = None
    auto_warning = None

    # AUTO mode: detect activity and assign tier immediately
    if updates.get('bandwidth_limit') == 'auto' and roll_no_for_update:
        try:
            auto_recommendation = assign_auto_bandwidth(roll_no_for_update)
        except Exception as error:
            auto_warning = str(error)
            logger.warning("Auto bandwidth assignment failed for %s: %s", roll_no_for_update, error)
            auto_recommendation = _build_fallback_auto_recommendation(roll_no_for_update, auto_warning)
        bandwidth_updated = True

    apply_status = None
    if bandwidth_updated:
        latest_doc = users_collection.find_one({"_id": oid}) or {}
        resolved_policy = resolve_effective_bandwidth(latest_doc)
        users_collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "bandwidth_effective_mode": resolved_policy.get("mode", "preset"),
                    "bandwidth_effective_tier": resolved_policy.get("tier", "medium"),
                    "bandwidth_effective_mbps": resolved_policy.get("effective_mbps", _medium_preset_mbps()),
                    "bandwidth_last_applied": datetime.datetime.utcnow(),
                }
            },
        )

        try:
            apply_status = apply_bandwidth_for_active_users()
        except Exception as error:
            logger.warning("Applying bandwidth policies failed after update for %s: %s", roll_no_for_update, error)
            apply_status = {
                "success": False,
                "error": str(error),
            }

    return jsonify({
        "message": "Client updated",
        "auto_recommendation": auto_recommendation,
        "apply_status": apply_status,
        "warning": auto_warning,
    }), 200


@admin_routes.route('/admin/bandwidth/auto-assign/<id>', methods=['POST'])
@admin_required
def admin_auto_assign_bandwidth(id):
    """Detect activity and auto-assign bandwidth for one user."""
    user_doc = _find_user_by_mixed_id(id)
    if not user_doc:
        return jsonify({"message": "User not found"}), 404

    roll_no = user_doc.get('roll_no')
    if not roll_no:
        return jsonify({"message": "roll_no missing for user"}), 400

    warning = None

    try:
        recommendation = assign_auto_bandwidth(roll_no)
    except Exception as error:
        warning = str(error)
        logger.warning("Auto bandwidth endpoint failed for %s: %s", roll_no, error)
        recommendation = _build_fallback_auto_recommendation(roll_no, warning)

    try:
        apply_status = apply_bandwidth_for_active_users()
    except Exception as error:
        logger.warning("Failed applying tc policies after auto-assign for %s: %s", roll_no, error)
        apply_status = {
            "success": False,
            "error": str(error),
        }

    return jsonify({
        "roll_no": roll_no,
        "tier": recommendation.get('tier', 'medium'),
        "confidence": recommendation.get('confidence', 0),
        "recommended_mbps": recommendation.get('recommended_mbps', _medium_preset_mbps()),
        "detected_activity": recommendation.get('detected_activity', 'General Browsing'),
        "dominant_category": recommendation.get('dominant_category', 'general'),
        "total_requests": recommendation.get('total_requests', 0),
        "explanation": recommendation.get('explanation', ''),
        "fallback": recommendation.get('fallback', False),
        "warning": warning,
        "apply_status": apply_status,
    }), 200


@admin_routes.route('/admin/bandwidth/refresh-auto', methods=['POST'])
@admin_required
def admin_refresh_auto_bandwidth():
    """Refresh all AUTO users based on latest activity patterns."""
    result = refresh_auto_bandwidth_profiles()
    return jsonify(result), 200


@admin_routes.route('/admin/logs', methods=['GET'])
@admin_required
def admin_logs():
    """Return network activity logs from the detections collection"""
    import pytz
    
    logs = []
    
    # Get detections from the detections collection
    if 'detections' in db.list_collection_names():
        detections_cursor = db['detections'].find().sort([('timestamp', -1)]).limit(100)
        
        # Setup IST timezone
        ist = pytz.timezone('Asia/Kolkata')
        
        for d in detections_cursor:
            # Format timestamp with timezone conversion
            ts = d.get('timestamp')
            if ts:
                if hasattr(ts, 'strftime'):
                    # Convert UTC to IST
                    if ts.tzinfo is None:
                        # Assume UTC if naive datetime
                        ts_utc = pytz.utc.localize(ts)
                    else:
                        ts_utc = ts
                    
                    # Convert to IST
                    ts_ist = ts_utc.astimezone(ist)
                    time_str = ts_ist.strftime('%I:%M:%S %p')
                else:
                    time_str = str(ts)
            else:
                time_str = 'N/A'
            
            # Determine log level based on category
            category = d.get('category', 'general').lower()
            if category in ('proxy', 'vpn', 'adult', 'malware'):
                level = 'error'
            elif category in ('gaming', 'streaming', 'social'):
                level = 'warn'
            else:
                level = 'info'
            
            logs.append({
                '_id': str(d.get('_id')),
                'time': time_str,
                'level': level,
                'user': d.get('roll_no', 'Unknown'),
                'ip': d.get('client_ip', 'N/A'),
                'action': d.get('app_name', 'Unknown'),  # Show just the app name
                'domain': d.get('domain'),
                'category': d.get('category', 'general'),
                'app_name': d.get('app_name', 'Unknown')
            })
    
    return jsonify({"logs": logs}), 200


@admin_routes.route('/admin/reports', methods=['POST'])
@admin_required
def admin_reports():
    """Generate reports from real detection data"""
    data = request.get_json() or {}
    report_type = data.get('type', 'Top Bandwidth Users')
    time_range = data.get('range', 'weekly')
    
    try:
        detections_col = db['detections'] if 'detections' in db.list_collection_names() else None
        
        # Calculate time filter based on range
        now = datetime.datetime.utcnow()
        if time_range == 'daily':
            start_date = now - datetime.timedelta(days=1)
        elif time_range == 'weekly':
            start_date = now - datetime.timedelta(weeks=1)
        else:  # monthly
            start_date = now - datetime.timedelta(days=30)
        
        headers = []
        rows = []
        
        if report_type == 'Top Bandwidth Users':
            headers = ['Rank', 'Student ID', 'Requests Count', 'Top Domain']
            
            if detections_col is not None:
                # Aggregate detections by roll_no
                pipeline = [
                    {"$match": {"timestamp": {"$gte": start_date}}},
                    {"$group": {
                        "_id": "$roll_no",
                        "count": {"$sum": 1},
                        "domains": {"$push": "$domain"}
                    }},
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ]
                results = list(detections_col.aggregate(pipeline))
                
                for i, r in enumerate(results):
                    # Find most common domain
                    domains = r.get('domains', [])
                    top_domain = max(set(domains), key=domains.count) if domains else 'N/A'
                    rows.append([
                        f"#{i+1}",
                        r.get('_id', 'Unknown'),
                        str(r.get('count', 0)),
                        top_domain
                    ])
        
        elif report_type == 'Blocked Site Activity':
            headers = ['Domain', 'Category', 'Access Count', 'Users']
            
            if detections_col is not None:
                # Aggregate by domain and category
                pipeline = [
                    {"$match": {"timestamp": {"$gte": start_date}}},
                    {"$group": {
                        "_id": {"domain": "$domain", "category": "$category"},
                        "count": {"$sum": 1},
                        "users": {"$addToSet": "$roll_no"}
                    }},
                    {"$sort": {"count": -1}},
                    {"$limit": 20}
                ]
                results = list(detections_col.aggregate(pipeline))
                
                for r in results:
                    domain = r.get('_id', {}).get('domain', 'Unknown')
                    category = r.get('_id', {}).get('category', 'general')
                    users = r.get('users', [])
                    rows.append([
                        domain,
                        category,
                        str(r.get('count', 0)),
                        ', '.join(users[:3]) + ('...' if len(users) > 3 else '')
                    ])
        
        elif report_type == 'Full Network Audit':
            headers = ['Time', 'Student', 'IP', 'Domain', 'Category']
            
            if detections_col is not None:
                # Get recent detections
                detections = list(detections_col.find(
                    {"timestamp": {"$gte": start_date}}
                ).sort([("timestamp", -1)]).limit(50))
                
                for d in detections:
                    ts = d.get('timestamp')
                    time_str = ts.strftime('%Y-%m-%d %H:%M') if hasattr(ts, 'strftime') else str(ts)[:16]
                    rows.append([
                        time_str,
                        d.get('roll_no', 'Unknown'),
                        d.get('client_ip', 'N/A'),
                        d.get('domain', 'N/A'),
                        d.get('category', 'general')
                    ])
        
        return jsonify({
            "headers": headers,
            "data": rows,
            "title": f"{time_range.capitalize()} {report_type}",
            "generated_at": now.isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({"error": str(e), "headers": [], "data": []}), 500

@admin_routes.route('/admin/bulk-upload', methods=['POST'])
@admin_required
def bulk_upload_clients():
    """Bulk upload students via CSV/Excel file"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        filename = file.filename or ''
        
        if filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file extension
        if not filename.endswith(('.csv', '.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file format. Please upload CSV or Excel file'}), 400
        
        # Read file
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(file.stream.read().decode('utf-8')))
            else:
                df = pd.read_excel(file)
        except Exception as e:
            return jsonify({'error': f'Failed to read file: {str(e)}'}), 400
        
        # Validate columns
        required_columns = ['roll_number', 'password']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': f'CSV must contain columns: {", ".join(required_columns)}'}), 400
        
        # Remove NaN values
        df = df.dropna(subset=required_columns)
        
        added_count = 0
        skipped_count = 0
        errors = []
        
        # Process each row
        for row_num, (_, row) in enumerate(df.iterrows(), start=2):
            roll_no = str(row['roll_number']).strip()
            password = str(row['password']).strip()
            
            if not roll_no or not password:
                skipped_count += 1
                errors.append(f'Row {row_num}: Missing data')
                continue
            
            # Check if student exists
            if users_collection.find_one({'roll_no': roll_no}):
                skipped_count += 1
                errors.append(f'Student {roll_no} already exists')
                continue
            
            # Insert new student (using same structure as existing add_client route)
            doc = {
                'roll_no': roll_no,
                'password': generate_password_hash(password),
                'role': 'student',
                'blocked': False,
                'activity': 'Idle',
                'bandwidth_limit': 'medium',
                'bandwidth_effective_tier': 'medium',
                'bandwidth_effective_mbps': _medium_preset_mbps(),
            }
            
            users_collection.insert_one(doc)
            added_count += 1
        
        return jsonify({
            'message': 'Bulk upload completed',
            'added': added_count,
            'skipped': skipped_count,
            'errors': errors[:10]
        }), 200
        
    except Exception as e:
        print(f"Bulk upload error: {e}")
        return jsonify({'error': str(e)}), 500

# S&  Web Filtering

DEFAULT_CATEGORIES = {

    "Gaming": {

        "active": True,

        "sites": ["steampowered.com", "twitch.tv", "roblox.com", "discord.gg", "epicgames.com", "ea.com", "playvalorant.com", "minecraft.net", "battle.net", "ubisoft.com"]

    },

    "Social Media": {

        "active": False,

        "sites": ["tiktok.com", "instagram.com", "facebook.com", "twitter.com", "reddit.com", "snapchat.com", "pinterest.com"]

    },

    "Streaming": {
        "active": False,
        "sites": [
            "netflix.com", "nflxvideo.net", "hulu.com", "disneyplus.com", "hbomax.com", "primevideo.com", 
            "spotify.com", "peacocktv.com", "sonyliv.com", "sonylivauth.com", 
            "hotstar.com", "api.hotstar.com", "zee5.com", "voot.com" 
            # Note: youtube.com is explicitly EXCLUDED
        ]
    },

    "File Sharing": {

        "active": True,

        "sites": ["thepiratebay.org", "1337x.to", "megaupload.com", "wetransfer.com", "mediafire.com", "rarbg.to"]

    },

    "Proxy/VPN": {
        "active": True,
        "sites": ["nordvpn.com", "expressvpn.com", "hidemyass.com", "proxysite.com", "cyberghostvpn.com", "surfshark.com", "privateinternetaccess.com", "protonvpn.me", "tunnelbear.com"]
    },
    "Messaging": {
         "active": False,
         "sites": ["whatsapp.com", "telegram.org", "discord.gg", "signal.org"]
    },

}



def normalize_filter_domain(value: str) -> str:
    """Normalize a URL/domain into a lowercase host suitable for filtering."""
    host = str(value or "").strip().lower()
    if not host:
        return ""

    if "://" in host:
        host = host.split("://", 1)[1]
    if host.startswith("//"):
        host = host[2:]

    host = host.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]

    if "@" in host:
        host = host.rsplit("@", 1)[-1]

    if ":" in host:
        maybe_host, maybe_port = host.rsplit(":", 1)
        if maybe_port.isdigit():
            host = maybe_host

    if host.startswith("www."):
        host = host[4:]

    return host.strip(".")


def _refresh_web_filter_defaults():
    """Ensure filtering config exists and normalize legacy manual blocks."""
    config = web_filter_collection.find_one({"type": "config"})

    if not config:
        legacy = web_filter_collection.find_one({
            "$or": [
                {"categories": {"$exists": True}},
                {"manual_blocks": {"$exists": True}},
            ]
        })

        if legacy:
            web_filter_collection.update_one(
                {"_id": legacy["_id"]},
                {
                    "$set": {
                        "type": "config",
                        "categories": legacy.get("categories", DEFAULT_CATEGORIES),
                        "manual_blocks": legacy.get("manual_blocks", ["specific-cheating-site.com", "unblock-proxy.net"]),
                    }
                },
            )
            config = web_filter_collection.find_one({"_id": legacy["_id"]})
        else:
            doc = {
                "type": "config",
                "categories": DEFAULT_CATEGORIES,
                "manual_blocks": ["specific-cheating-site.com", "unblock-proxy.net"],
            }
            inserted = web_filter_collection.insert_one(doc)
            config = {"_id": inserted.inserted_id, **doc}

    if not config:
        return

    updates = {}

    if not isinstance(config.get("categories"), dict):
        updates["categories"] = DEFAULT_CATEGORIES

    manual_blocks = config.get("manual_blocks")
    if not isinstance(manual_blocks, list):
        manual_blocks = []
        updates["manual_blocks"] = []

    legacy_manual_map = {
        "specific-cheating-site": "specific-cheating-site.com",
        "unblock-proxy": "unblock-proxy.net",
    }

    normalized_manual_blocks = []
    seen = set()
    for entry in manual_blocks:
        normalized = normalize_filter_domain(entry)
        if not normalized:
            continue
        normalized = legacy_manual_map.get(normalized, normalized)
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_manual_blocks.append(normalized)

    if normalized_manual_blocks != manual_blocks:
        updates["manual_blocks"] = normalized_manual_blocks

    if updates:
        config_id = config.get("_id")
        if config_id is not None:
            web_filter_collection.update_one({"_id": config_id}, {"$set": updates})



@admin_routes.route('/admin/filtering', methods=['GET'])

@admin_required

def get_filtering():

    _refresh_web_filter_defaults()

    config = web_filter_collection.find_one({"type": "config"})

    if not config:

        return jsonify({"message": "Error loading config"}), 500

    

    return jsonify({

        "categories": config.get("categories", {}),

        "manual_blocks": config.get("manual_blocks", [])

    }), 200



@admin_routes.route('/admin/filtering/categories', methods=['POST'])
@admin_required
def toggle_category():
    data = request.get_json() or {}
    category = data.get("category")
    
    if not category:
        return jsonify({"message": "Category required"}), 400
        
    _refresh_web_filter_defaults()
    config = web_filter_collection.find_one({"type": "config"}) or {}
    
    categories = config.get("categories", {})
    if category not in categories:
        return jsonify({"message": "Category not found"}), 404
        
    # Toggle
    current_status = categories[category]["active"]
    new_status = not current_status
    
    web_filter_collection.update_one(
        {"type": "config"},
        {"$set": {f"categories.{category}.active": new_status}}
    )
    
    # Update DNS blocklist immediately
    try:
        from dns_filtering_manager import update_dnsmasq_blocklist
        print(f"\n🔄 {'Enabling' if new_status else 'Disabling'} {category} category via DNS...")
        dns_updated = update_dnsmasq_blocklist()
        if dns_updated:
            print("✅ DNS blocklist updated")
        else:
            print("⚠️ DNS blocklist update failed")
        
        # Update Firewall rules (IP Blocking)
        print(f"🔄 Updating Firewall rules...")
        firewall_updated = update_firewall_rules()
        if firewall_updated:
            print("✅ Firewall rules updated")
        else:
            print("⚠️ Firewall rules update failed")

        if not dns_updated or not firewall_updated:
            web_filter_collection.update_one(
                {"type": "config"},
                {"$set": {f"categories.{category}.active": current_status}}
            )
            return jsonify({
                "message": "Category updated, but failed to apply filtering rules",
                "active": new_status,
                "dns_updated": dns_updated,
                "firewall_updated": firewall_updated,
            }), 500
        
    except Exception as e:
        print(f"⚠️ Update failed: {e}")
        web_filter_collection.update_one(
            {"type": "config"},
            {"$set": {f"categories.{category}.active": current_status}}
        )
        return jsonify({"message": "Category updated, but applying filtering rules failed"}), 500
    
    return jsonify({"message": "Updated", "active": new_status}), 200



@admin_routes.route('/admin/filtering/sites', methods=['POST'])
@admin_required
def add_blocked_site():
    data = request.get_json() or {}
    url = data.get("url")

    if not url:
        return jsonify({"message": "URL required"}), 400

    domain = normalize_filter_domain(url)
    if not domain or "." not in domain:
        return jsonify({"message": "Please enter a valid domain (example.com)"}), 400

    _refresh_web_filter_defaults()

    # Duplicate check after normalization
    config = web_filter_collection.find_one({"type": "config"}) or {}
    existing_domains = {
        normalized
        for item in config.get("manual_blocks", [])
        for normalized in [normalize_filter_domain(item)]
        if normalized
    }
    if domain in existing_domains:
        return jsonify({"message": f"'{domain}' is already in the block list"}), 409

    # Store normalized domain
    web_filter_collection.update_one(
        {"type": "config"},
        {"$addToSet": {"manual_blocks": domain}}
    )

    # Update DNS blocklist immediately
    try:
        from dns_filtering_manager import update_dnsmasq_blocklist
        from linux_firewall_manager import update_firewall_rules

        print(f"\n🔄 Blocking {domain} via DNS...")
        dns_updated = update_dnsmasq_blocklist()
        if dns_updated:
            print("✅ DNS blocklist updated")
        else:
            print("⚠️ DNS blocklist update failed")

        print(f"🔄 Blocking {domain} via Firewall (IPs)...")
        firewall_updated = update_firewall_rules()
        if firewall_updated:
            print("✅ Firewall rules updated")
        else:
            print("⚠️ Firewall rules update failed")

        if not dns_updated or not firewall_updated:
            web_filter_collection.update_one(
                {"type": "config"},
                {"$pull": {"manual_blocks": domain}}
            )
            return jsonify({
                "message": "Site saved, but failed to apply filtering rules",
                "dns_updated": dns_updated,
                "firewall_updated": firewall_updated,
            }), 500

        return jsonify({"message": f"Site blocked: {domain}"}), 201
    except Exception as e:
        print(f"⚠️ Update failed: {e}")
        web_filter_collection.update_one(
            {"type": "config"},
            {"$pull": {"manual_blocks": domain}}
        )
        return jsonify({"message": "Site added to database, but applying filtering rules failed"}), 500



@admin_routes.route('/admin/filtering/sites', methods=['DELETE'])
@admin_required
def remove_blocked_site():
    data = request.get_json() or {}
    url = data.get("url")

    if not url:
        return jsonify({"message": "URL required"}), 400

    target = normalize_filter_domain(url)
    if not target:
        return jsonify({"message": "Invalid URL/domain"}), 400

    _refresh_web_filter_defaults()

    config = web_filter_collection.find_one({"type": "config"}) or {}
    existing_blocks = config.get("manual_blocks", [])
    raw_value = str(url).strip().lower()

    values_to_remove = {
        entry
        for entry in existing_blocks
        if normalize_filter_domain(entry) == target
        or str(entry).strip().lower() == raw_value
    }

    if not values_to_remove:
        return jsonify({"message": "Site not found in manual block list"}), 404

    # Remove all equivalent representations
    web_filter_collection.update_one(
        {"type": "config"},
        {"$pull": {"manual_blocks": {"$in": list(values_to_remove)}}}
    )

    # Update DNS blocklist immediately
    try:
        from dns_filtering_manager import update_dnsmasq_blocklist
        from linux_firewall_manager import update_firewall_rules

        print(f"\n🔄 Unblocking {target} via DNS...")
        dns_updated = update_dnsmasq_blocklist()
        if dns_updated:
            print("✅ DNS blocklist updated")
        else:
            print("⚠️ DNS blocklist update failed")

        print(f"🔄 Unblocking {target} via Firewall...")
        firewall_updated = update_firewall_rules()
        if firewall_updated:
            print("✅ Firewall rules updated")
        else:
            print("⚠️ Firewall rules update failed")

        if not dns_updated or not firewall_updated:
            web_filter_collection.update_one(
                {"type": "config"},
                {"$addToSet": {"manual_blocks": {"$each": list(values_to_remove)}}}
            )
            return jsonify({
                "message": "Site removed, but failed to apply filtering rules",
                "dns_updated": dns_updated,
                "firewall_updated": firewall_updated,
            }), 500

        return jsonify({"message": f"Site unblocked: {target}"}), 200
    except Exception as e:
        print(f"⚠️ Update failed: {e}")
        if values_to_remove:
            web_filter_collection.update_one(
                {"type": "config"},
                {"$addToSet": {"manual_blocks": {"$each": list(values_to_remove)}}}
            )
        return jsonify({"message": "Site removed from database, but applying filtering rules failed"}), 500
