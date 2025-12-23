from flask import Blueprint, request, jsonify
from models.user_model import create_user, find_user, validate_user
from db import users_collection, admins_collection, sessions_collection
from werkzeug.security import check_password_hash
import jwt
import datetime
import socket

auth_routes = Blueprint("auth_routes", __name__)

SECRET_KEY = "your-secret-key"

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
    data = request.get_json()

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
    data = request.get_json()

    roll_no = data.get("roll_no")
    password = data.get("password")

    user = validate_user(roll_no, password)

    if not user:
        return jsonify({"status": "error", "msg": "Invalid credentials"}), 401

    # ✅ Get client IP (use actual network IP if localhost)
    remote_ip = request.remote_addr
    if remote_ip in ("127.0.0.1", "::1", "localhost"):
        client_ip = get_local_network_ip()
    else:
        client_ip = remote_ip
    
    # ✅ Create/update session for detection tracking
    sessions_collection.update_one(
        {"roll_no": roll_no},
        {"$set": {
            "roll_no": roll_no,
            "client_ip": client_ip,
            "login_time": datetime.datetime.utcnow(),
            "status": "active"
        }},
        upsert=True
    )
    print(f"✅ Session created: {roll_no} -> {client_ip}")

    token = jwt.encode({
        "roll_no": roll_no,
        "role": "student",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, SECRET_KEY, algorithm="HS256")

    return jsonify({
        "status": "success",
        "token": token,
        "role": "student",
        "msg": "Login successful"
    }), 200


# ---------------- STUDENT LOGOUT ----------------
@auth_routes.route("/logout", methods=["POST"])
def logout():
    data = request.get_json()
    roll_no = data.get("roll_no")
    
    if roll_no:
        sessions_collection.delete_one({"roll_no": roll_no})
        print(f"✅ Session deleted: {roll_no}")
        return jsonify({"status": "success", "msg": "Logout successful"}), 200
    
    return jsonify({"status": "error", "msg": "Roll number required"}), 400


# ---------------- ADMIN LOGIN ----------------
@auth_routes.route("/admin/login", methods=["POST"])
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
    }, SECRET_KEY, algorithm="HS256")

    return jsonify({
        "token": token,
        "role": "admin"
    }), 200
