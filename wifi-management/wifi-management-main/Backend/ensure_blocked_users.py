from pymongo import MongoClient

def ensure_blocked_users():
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client["studentapp"]
        
        collection_name = "blocked_users"
        
        if collection_name in db.list_collection_names():
            print(f"Collection '{collection_name}' already exists.")
        else:
            db.create_collection(collection_name)
            print(f"Collection '{collection_name}' created successfully.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    ensure_blocked_users()
