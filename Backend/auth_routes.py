from flask import Blueprint, request, jsonify
from models.user_model import create_user, find_user, validate_user
from db import users_collection, admins_collection, sessions_collection, db
from werkzeug.security import check_password_hash
import jwt
import datetime
import socket
import os
import ipaddress

# Import firewall functions for captive portal
_allow_authenticated_user_fn = None
_block_authenticated_user_fn = None
_get_usage_for_client_ip_fn = None
FIREWALL_ENABLED = False

try:
    from linux_firewall_manager import (
        allow_authenticated_user as _allow_authenticated_user_fn,
        block_authenticated_user as _block_authenticated_user_fn,
        get_usage_for_client_ip as _get_usage_for_client_ip_fn,
    )
    FIREWALL_ENABLED = True
except ImportError:
    print("⚠️ Firewall manager not available")

_apply_bandwidth_for_active_users_fn = None
BANDWIDTH_MANAGEMENT_ENABLED = False

try:
    import bandwidth_manager

    _apply_bandwidth_for_active_users_fn = bandwidth_manager.apply_bandwidth_for_active_users
    BANDWIDTH_MANAGEMENT_ENABLED = True
except ImportError:
    print("⚠️ Bandwidth manager not available")

auth_routes = Blueprint("auth_routes", __name__)

SECRET_KEY = "your-secret-key"

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
    defaults = {
        "admin_timeout_hours": DEFAULT_ADMIN_TIMEOUT_HOURS,
        "student_timeout_hours": DEFAULT_STUDENT_TIMEOUT_HOURS,
    }

    try:
        settings_doc = db["admin_settings"].find_one({"type": "session_timeout"}) or {}
    except Exception:
        return defaults

    admin_hours = _parse_timeout_hours(settings_doc.get("admin_timeout_hours"))
    student_hours = _parse_timeout_hours(settings_doc.get("student_timeout_hours"))

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


def _get_hotspot_network():
    subnet = os.environ.get("HOTSPOT_SUBNET", "192.168.50.0/24")
    try:
        return ipaddress.ip_network(subnet, strict=False)
    except Exception:
        return ipaddress.ip_network("192.168.50.0/24", strict=False)


def _is_hotspot_client_ip(client_ip: str) -> bool:
    if not isinstance(client_ip, str):
        return False
    try:
        return ipaddress.ip_address(client_ip) in _get_hotspot_network()
    except ValueError:
        return False


def _normalize_utc_naive(value):
    if not isinstance(value, datetime.datetime):
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)


def _safe_non_negative_int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _sync_session_usage_totals(roll_no: str, session_doc=None):
    """Persist latest per-session byte counters into cumulative user totals."""
    if not roll_no:
        return {"delta_total_bytes": 0, "client_ip": None}

    if session_doc is None:
        session_doc = sessions_collection.find_one({"roll_no": roll_no})

    if not session_doc:
        return {"delta_total_bytes": 0, "client_ip": None}

    client_ip = session_doc.get("client_ip")
    if not client_ip or not (_get_usage_for_client_ip_fn and FIREWALL_ENABLED and _is_hotspot_client_ip(client_ip)):
        return {"delta_total_bytes": 0, "client_ip": client_ip}

    try:
        usage = _get_usage_for_client_ip_fn(client_ip) or {}
    except Exception as error:
        print(f"⚠️ Failed to read usage counters for {client_ip}: {error}")
        return {"delta_total_bytes": 0, "client_ip": client_ip}

    current_upload = _safe_non_negative_int(usage.get("upload_bytes"))
    current_download = _safe_non_negative_int(usage.get("download_bytes"))

    accounted_upload = _safe_non_negative_int(session_doc.get("usage_accounted_upload_bytes"))
    accounted_download = _safe_non_negative_int(session_doc.get("usage_accounted_download_bytes"))

    delta_upload = current_upload - accounted_upload if current_upload >= accounted_upload else current_upload
    delta_download = current_download - accounted_download if current_download >= accounted_download else current_download
    delta_total = max(0, delta_upload + delta_download)

    now_utc = datetime.datetime.utcnow()

    if delta_total > 0:
        users_collection.update_one(
            {"roll_no": roll_no},
            {
                "$inc": {
                    "total_data_bytes": delta_total,
                    "total_upload_bytes": max(0, delta_upload),
                    "total_download_bytes": max(0, delta_download),
                },
                "$set": {
                    "data_usage_updated_at": now_utc,
                },
            },
        )

    session_selector = {"_id": session_doc.get("_id")} if session_doc.get("_id") else {"roll_no": roll_no}
    sessions_collection.update_one(
        session_selector,
        {
            "$set": {
                "usage_upload_bytes": current_upload,
                "usage_download_bytes": current_download,
                "usage_total_bytes": current_upload + current_download,
                "usage_accounted_upload_bytes": current_upload,
                "usage_accounted_download_bytes": current_download,
                "usage_last_sync": now_utc,
            }
        },
    )

    return {
        "client_ip": client_ip,
        "delta_total_bytes": delta_total,
        "delta_upload_bytes": max(0, delta_upload),
        "delta_download_bytes": max(0, delta_download),
    }


def _get_active_block_doc(roll_no: str):
    blocked_users_col = db["blocked_users"]
    block_doc = blocked_users_col.find_one({"roll_no": roll_no, "status": "blocked"})
    if not block_doc:
        return None

    if block_doc.get("ban_type") == "temporary":
        expires_at = _normalize_utc_naive(block_doc.get("expires_at"))
        if expires_at and datetime.datetime.utcnow() >= expires_at:
            blocked_users_col.update_one(
                {"_id": block_doc.get("_id")},
                {
                    "$set": {
                        "status": "expired",
                        "expired_at": datetime.datetime.utcnow(),
                    }
                },
            )
            return None

    return block_doc


def _force_logout_session(roll_no: str, reason: str) -> bool:
    active_session = sessions_collection.find_one({"roll_no": roll_no, "status": "active"})
    if not active_session:
        return False

    client_ip = active_session.get("client_ip")

    try:
        _sync_session_usage_totals(roll_no, session_doc=active_session)
    except Exception as e:
        print(f"⚠️ Failed to sync usage for {roll_no} before forced logout: {e}")

    if FIREWALL_ENABLED and _block_authenticated_user_fn and _is_hotspot_client_ip(client_ip):
        try:
            _block_authenticated_user_fn(client_ip)
            print(f"✅ Internet access revoked for {client_ip} (security block)")
        except Exception as e:
            print(f"⚠️ Failed to revoke firewall access for {client_ip}: {e}")

    sessions_collection.update_many(
        {"roll_no": roll_no, "status": "active"},
        {
            "$set": {
                "status": "terminated",
                "logout_reason": "security_block",
                "logout_message": reason,
                "logout_at": datetime.datetime.utcnow(),
            }
        },
    )

    if BANDWIDTH_MANAGEMENT_ENABLED and _apply_bandwidth_for_active_users_fn:
        try:
            _apply_bandwidth_for_active_users_fn()
        except Exception as e:
            print(f"⚠️ Failed to refresh bandwidth policy after forced logout: {e}")

    return True

def get_local_network_ip():
    """Get actual network IP for session tracking"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# ---------------- STUDENT SIGNUP ----------------
@auth_routes.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}

    name = data.get("name")
    roll_no = data.get("roll_no")
    password = data.get("password")

    if not name or not roll_no or not password:
        return jsonify({"status": "error", "msg": "All fields required"}), 400

    if find_user(roll_no):
        return jsonify({"status": "error", "msg": "User already exists"}), 409

    create_user(name, roll_no, password)

    return jsonify({"status": "success", "msg": "Account created"}), 201


# ---------------- STUDENT LOGIN ----------------
@auth_routes.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    roll_no = (data.get("roll_no") or "").strip()
    password = data.get("password")

    user = validate_user(roll_no, password)

    if not user:
        return jsonify({"status": "error", "msg": "Invalid credentials"}), 401

    # ✅ Check if user is blocked
    block_doc = _get_active_block_doc(roll_no)
    
    if block_doc:
        ban_type = block_doc.get("ban_type", "temporary")
        reason = block_doc.get("reason", "Violation of network policy")
        
        if ban_type == "permanent":
            return jsonify({
                "status": "error", 
                "msg": f"Account permanently blocked. Reason: {reason}",
                "blocked": True,
                "ban_type": "permanent"
            }), 403
        else:
            # Temporary ban - show expiry time
            expires_at = block_doc.get("expires_at")
            if expires_at:
                import pytz
                ist = pytz.timezone('Asia/Kolkata')
                if hasattr(expires_at, 'replace'):
                    expires_at_utc = expires_at.replace(tzinfo=pytz.utc)
                    expires_at_ist = expires_at_utc.astimezone(ist)
                    expiry_str = expires_at_ist.strftime('%I:%M %p, %d %b %Y')
                    return jsonify({
                        "status": "error",
                        "msg": f"Account temporarily blocked until {expiry_str}. Reason: {reason}",
                        "blocked": True,
                        "ban_type": "temporary",
                        "expires_at": expiry_str
                    }), 403
            
            return jsonify({
                "status": "error",
                "msg": f"Account temporarily blocked. Reason: {reason}",
                "blocked": True,
                "ban_type": "temporary"
            }), 403

    # ✅ Get client IP (use actual network IP if localhost)
    remote_ip = request.remote_addr
    if remote_ip in ("127.0.0.1", "::1", "localhost"):
        client_ip = get_local_network_ip()
    else:
        client_ip = remote_ip or "unknown"
    
    # ✅ Create/update session for detection tracking
    sessions_collection.update_one(
        {"roll_no": roll_no},
        {"$set": {
            "roll_no": roll_no,
            "client_ip": client_ip,
            "login_time": datetime.datetime.utcnow(),
            "status": "active",
            "logout_reason": None,
            "logout_message": None,
            "logout_at": None,
            "usage_upload_bytes": 0,
            "usage_download_bytes": 0,
            "usage_total_bytes": 0,
            "usage_accounted_upload_bytes": 0,
            "usage_accounted_download_bytes": 0,
            "usage_last_sync": None,
        }},
        upsert=True
    )
    print(f"✅ Session created: {roll_no} -> {client_ip}")
    
    # ✅ Enable internet access for this user (captive portal)
    if FIREWALL_ENABLED and _allow_authenticated_user_fn and _is_hotspot_client_ip(client_ip):
        try:
            _allow_authenticated_user_fn(client_ip)
            print(f"✅ Internet access enabled for {client_ip}")
        except Exception as e:
            print(f"⚠️ Failed to enable firewall access: {e}")

    # ✅ Apply bandwidth policy for active users (including this new login)
    if BANDWIDTH_MANAGEMENT_ENABLED and _apply_bandwidth_for_active_users_fn:
        try:
            _apply_bandwidth_for_active_users_fn()
        except Exception as e:
            print(f"⚠️ Failed to apply bandwidth policy: {e}")

    timeout_settings = _get_session_timeout_settings()
    student_timeout_hours = timeout_settings["student_timeout_hours"]

    token = jwt.encode({
        "roll_no": roll_no,
        "role": "student",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=student_timeout_hours)
    }, SECRET_KEY, algorithm="HS256")

    return jsonify({
        "status": "success",
        "token": token,
        "role": "student",
        "session_timeout_hours": student_timeout_hours,
        "msg": "Login successful"
    }), 200


@auth_routes.route("/session-status", methods=["GET"])
def session_status():
    roll_no = (request.args.get("roll_no") or "").strip()
    if not roll_no:
        return jsonify({"status": "error", "msg": "Roll number required"}), 400

    block_doc = _get_active_block_doc(roll_no)
    if block_doc:
        reason = block_doc.get("reason", "Malicious activity detected")
        _force_logout_session(roll_no, reason)

        payload = {
            "status": "success",
            "session_status": "blocked",
            "auto_logout": True,
            "msg": "You have been logged out due to malicious activity.",
            "reason": reason,
            "ban_type": block_doc.get("ban_type", "temporary"),
        }

        expires_at = _normalize_utc_naive(block_doc.get("expires_at"))
        if block_doc.get("ban_type") == "temporary" and expires_at:
            payload["expires_at_utc"] = f"{expires_at.isoformat()}Z"

        return jsonify(payload), 200

    active_session = sessions_collection.find_one({"roll_no": roll_no, "status": "active"})
    if not active_session:
        return jsonify({
            "status": "success",
            "session_status": "logged_out",
            "auto_logout": True,
            "msg": "Session ended. Please login again.",
        }), 200

    return jsonify({
        "status": "success",
        "session_status": "active",
        "auto_logout": False,
    }), 200


# ---------------- STUDENT LOGOUT ----------------
@auth_routes.route("/logout", methods=["POST"])
def logout():
    data = request.get_json() or {}
    roll_no = (data.get("roll_no") or "").strip()
    
    if roll_no:
        # Get the session to find client IP
        session = sessions_collection.find_one({"roll_no": roll_no})
        
        if session:
            client_ip = session.get("client_ip")

            try:
                _sync_session_usage_totals(roll_no, session_doc=session)
            except Exception as e:
                print(f"⚠️ Failed to sync usage for {roll_no} before logout: {e}")
            
            # ✅ Revoke internet access (captive portal)
            if FIREWALL_ENABLED and _block_authenticated_user_fn and _is_hotspot_client_ip(client_ip):
                try:
                    _block_authenticated_user_fn(client_ip)
                    print(f"✅ Internet access revoked for {client_ip}")
                except Exception as e:
                    print(f"⚠️ Failed to revoke firewall access: {e}")
        
        # Delete session
        sessions_collection.delete_one({"roll_no": roll_no})
        print(f"✅ Session deleted: {roll_no}")

        # ✅ Refresh bandwidth policies after session removal
        if BANDWIDTH_MANAGEMENT_ENABLED and _apply_bandwidth_for_active_users_fn:
            try:
                _apply_bandwidth_for_active_users_fn()
            except Exception as e:
                print(f"⚠️ Failed to refresh bandwidth policy: {e}")

        return jsonify({"status": "success", "msg": "Logout successful"}), 200
    
    return jsonify({"status": "error", "msg": "Roll number required"}), 400


# ---------------- ADMIN LOGIN ----------------
@auth_routes.route("/admin/login", methods=["POST"])
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
    }, SECRET_KEY, algorithm="HS256")

    return jsonify({
        "token": token,
        "role": "admin",
        "session_timeout_hours": admin_timeout_hours,
    }), 200
