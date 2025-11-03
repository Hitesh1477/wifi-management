from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from pymongo import MongoClient
import jwt, datetime
from flask import current_app as app

admin_routes = Blueprint("admin_routes", __name__)

client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']
admins_collection = db['admins']   # ✅ Correct collection

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
