from flask import Blueprint, request, jsonify
from models.user_model import create_user, find_user, validate_user

auth_routes = Blueprint("auth_routes", __name__)

@auth_routes.route("/signup", methods=["POST"])
def signup():
    data = request.json
    if find_user(data["roll_id"]):
        return jsonify({"status": "error", "msg": "User already exists"})
    
    create_user(data)
    return jsonify({"status": "success", "msg": "Account created"})

@auth_routes.route("/login", methods=["POST"])
def login():
    data = request.json
    user = validate_user(data["roll_id"], data["password"])
    if user:
        return jsonify({"status": "success", "msg": "Login successful"})
    return jsonify({"status": "error", "msg": "Invalid credentials"})
