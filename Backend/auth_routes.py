from flask import Blueprint, request, jsonify
from models.user_model import create_user, find_user, validate_user
from db import users_collection
from werkzeug.security import check_password_hash
import jwt

auth_routes = Blueprint("auth_routes", __name__)

# ---------------- STUDENT SIGNUP ----------------
@auth_routes.route("/signup", methods=["POST"])
def signup():
    data = request.json
    if find_user(data["roll_no"]):  # ✅ use roll_no
        return jsonify({"status": "error", "msg": "User already exists"})
    
    create_user(data)
    return jsonify({"status": "success", "msg": "Account created"})

# ---------------- STUDENT LOGIN ----------------
@auth_routes.route("/login", methods=["POST"])
def login():
    data = request.json
    user = validate_user(data["roll_no"], data["password"])  # ✅ roll_no
    if user:
        token = jwt.encode({"roll_no": data["roll_no"], "role": "student"}, "secret", algorithm="HS256")
        return jsonify({"status": "success", "token": token, "msg": "Login successful"})
    
    return jsonify({"status": "error", "msg": "Invalid credentials"})

# ---------------- ADMIN LOGIN ----------------
@auth_routes.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    admin = users_collection.find_one({"roll_no": username, "role": "admin"})

    if not admin or not check_password_hash(admin["password"], password):
        return jsonify({"message": "Invalid admin credentials"}), 401

    token = jwt.encode({"roll_no": username, "role": "admin"}, "secret", algorithm="HS256")
    return jsonify({"token": token, "role": "admin"}), 200
