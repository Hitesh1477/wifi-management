from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime

# ✅ Import admin routes
from admin_routes import admin_routes

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = "your-secret-key"

# ✅ MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']
users_collection = db['users']
admins_collection = db['admins']
sessions_collection = db['active_sessions']

# ✅ Register admin blueprint (MUST be after Flask app init)
app.register_blueprint(admin_routes)


# ✅ User Signup Route
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    roll_no = data.get('roll_no')
    password = data.get('password')

    if users_collection.find_one({"roll_no": roll_no}):
        return jsonify({"message": "Roll number already registered"}), 409

    hashed_password = generate_password_hash(password)

    user = {
        "name": name,
        "roll_no": roll_no,
        "password": hashed_password,
        "role": "student"
    }

    users_collection.insert_one(user)
    return jsonify({"message": "User registered successfully"}), 201


# ✅ User Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    roll_no = data.get('roll_no')
    password = data.get('password')

    user = users_collection.find_one({"roll_no": roll_no})

    if not user or not check_password_hash(user['password'], password):
        return jsonify({"message": "Invalid credentials"}), 401

    # ✅ Get client IP address
    client_ip = request.remote_addr
    
    # ✅ Create/update session with IP mapping
    sessions_collection = db['active_sessions']
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
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({"message": "Login successful", "token": token})


# ✅ User Logout Route
@app.route('/logout', methods=['POST'])
def logout():
    data = request.get_json()
    roll_no = data.get('roll_no')
    
    if roll_no:
        sessions_collection = db['active_sessions']
        sessions_collection.delete_one({"roll_no": roll_no})
        print(f"✅ Session deleted: {roll_no}")
        return jsonify({"message": "Logout successful"}), 200
    
    return jsonify({"message": "Roll number required"}), 400

# ✅ Root Test Route
@app.route('/')
def home():
    return jsonify({"message": "Backend is running ✅"})


if __name__ == '__main__':
    app.run(debug=True)
