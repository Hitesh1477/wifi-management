from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = "your-secret-key"

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']
users_collection = db['users']

# ✅ Signup Route
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


# ✅ Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    roll_no = data.get('roll_no')
    password = data.get('password')

    user = users_collection.find_one({"roll_no": roll_no})

    if not user or not check_password_hash(user['password'], password):
        return jsonify({"message": "Invalid credentials"}), 401

    token = jwt.encode({
        "roll_no": roll_no,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({"message": "Login successful", "token": token})


# ✅ Root Test Route (optional)
@app.route('/')
def home():
    return jsonify({"message": "Backend is running ✅"})


if __name__ == '__main__':
    app.run(debug=True)
