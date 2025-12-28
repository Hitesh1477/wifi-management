from pymongo import MongoClient
from werkzeug.security import generate_password_hash

client = MongoClient("mongodb://localhost:27017/")
db = client['studentapp']

admin = {
    "username": "admin",
    "password": generate_password_hash("Admin@123"),
    "role": "admin"
}

db['admins'].insert_one(admin)
print("Admin created ✅")