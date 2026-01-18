from db import users_collection
from werkzeug.security import generate_password_hash, check_password_hash

def create_user(name, roll_no, password):
    hashed_password = generate_password_hash(password)
    users_collection.insert_one({
        "name": name,
        "roll_no": roll_no,
        "password": hashed_password,
        "role": "student"
    })

def find_user(roll_no):
    return users_collection.find_one({"roll_no": roll_no})

def validate_user(roll_no, password):
    user = users_collection.find_one({"roll_no": roll_no})
    if user and check_password_hash(user["password"], password):
        return user
    return None
