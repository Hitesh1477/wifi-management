from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")  # local DB URL
db = client["flask_db"]  # Database name
