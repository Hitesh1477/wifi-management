from pymongo import MongoClient
from datetime import datetime, timedelta, UTC
import pandas as pd
from sklearn.ensemble import IsolationForest

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
detections = db["detections"]
anomalies = db["anomalies"]

WINDOW_MINUTES = 60  # Increased for testing (was 5)

def fetch_ml_data():
    since = datetime.now(UTC) - timedelta(minutes=WINDOW_MINUTES)

    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": since},
                "roll_no": {"$exists": True},
                "client_ip": {"$ne": ""},
                "category": {"$ne": "general"}
            }
        },
        {
            "$group": {
                "_id": "$roll_no",
                "total": {"$sum": 1},
                "video": {"$sum": {"$cond": [{"$eq": ["$category", "video"]}, 1, 0]}},
                "social": {"$sum": {"$cond": [{"$eq": ["$category", "social"]}, 1, 0]}},
                "messaging": {"$sum": {"$cond": [{"$eq": ["$category", "messaging"]}, 1, 0]}}
            }
        },
        {
            "$match": {
                "total": {"$gt": 0}  # Filter out zero totals
            }
        }
    ]

    data = list(detections.aggregate(pipeline))
    return pd.DataFrame(data)

def prepare_features(df):
    if df.empty:
        return None, None  # Return tuple consistently
    
    # Filter out rows where total is 0 (safety check)
    df = df[df["total"] > 0].copy()
    
    if df.empty:
        return None, None

    # Calculate ratios safely
    df["video_ratio"] = df["video"] / df["total"]
    df["social_ratio"] = df["social"] / df["total"]
    df["messaging_ratio"] = df["messaging"] / df["total"]

    features = df[
        ["total", "video", "social", "messaging",
         "video_ratio", "social_ratio", "messaging_ratio"]
    ]

    return features, df["_id"]  # roll_no

def run_isolation_forest(features):
    model = IsolationForest(
        n_estimators=100,
        contamination=0.1,
        random_state=42
    )

    preds = model.fit_predict(features)
    scores = model.decision_function(features)

    return preds, scores

def save_ml_anomalies(roll_nos, preds, scores):
    now = datetime.now(UTC)

    for roll_no, pred, score in zip(roll_nos, preds, scores):
        if pred == -1:  # anomaly
            anomalies.insert_one({
                "roll_no": roll_no,
                "type": "ML_ANOMALY",
                "ml_model": "Isolation Forest",
                "score": float(score),
                "severity": "medium",
                "detected_by": "ml",
                "timestamp": now
            })

def main():
    print("Fetching data from MongoDB...")
    df = fetch_ml_data()
    
    if df.empty:
        print("ℹ️ Not enough data for ML analysis")
        return

    print(f"Found {len(df)} students with activity")
    
    features, roll_nos = prepare_features(df)
    
    if features is None or features.empty:
        print("ℹ️ Not enough valid data after feature preparation")
        return
    
    print(f"Running Isolation Forest on {len(features)} records...")
    preds, scores = run_isolation_forest(features)
    
    anomaly_count = sum(1 for p in preds if p == -1)
    print(f"Found {anomaly_count} anomalies")
    
    save_ml_anomalies(roll_nos, preds, scores)
    print("✅ Isolation Forest ML detection completed")

if __name__ == "__main__":
    main()