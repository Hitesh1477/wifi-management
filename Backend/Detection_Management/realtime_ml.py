# realtime_ml.py
from datetime import datetime, timedelta, UTC
from pymongo import MongoClient
from sklearn.ensemble import IsolationForest
import numpy as np

client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
detections = db["detections"]

WINDOW_MINUTES = 2

# Train-once simple model (baseline normal behavior)
model = IsolationForest(
    n_estimators=100,
    contamination=0.05,
    random_state=42
)

def extract_features(roll_no):
    since = datetime.now(UTC) - timedelta(minutes=WINDOW_MINUTES)

    docs = list(detections.find({
        "roll_no": roll_no,
        "timestamp": {"$gte": since},
        "category": {"$ne": "general"}
    }))

    if len(docs) < 5:
        return None

    total = len(docs)
    apps = [d["app_name"] for d in docs]
    dominant = max(apps.count(a) for a in set(apps))
    dominant_ratio = dominant / total

    return np.array([[total, dominant_ratio]])

def ml_anomaly_check(roll_no):
    features = extract_features(roll_no)
    if features is None:
        return False

    model.fit(features)
    score = model.decision_function(features)[0]

    return score < -0.15  # strict threshold
