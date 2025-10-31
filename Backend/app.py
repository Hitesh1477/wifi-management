from flask import Flask, request, jsonify
from pymongo import MongoClient

app = Flask(__name__)

# ✅ Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["flask-db"]  # your database name
users_collection = db["users"]  # collection name

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask Working ✅"})

# ✅ POST API to save user to DB
@app.route("/users", methods=["POST"])
def add_user():
    data = request.get_json()
    result = users_collection.insert_one(data)
    return jsonify({"status": "success", "inserted_id": str(result.inserted_id)})

if __name__ == "__main__":
    app.run(debug=True)
