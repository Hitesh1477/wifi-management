from db import users_collection

def create_user(data):
    users_collection.insert_one(data)

def find_user(roll_id):
    return users_collection.find_one({"roll_id": roll_id})

def validate_user(roll_id, password):
    return users_collection.find_one({"roll_id": roll_id, "password": password})
