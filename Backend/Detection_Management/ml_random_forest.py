"""
ML Anomaly Detection using Random Forest Classifier
====================================================
This model classifies user behavior as 'normal' or 'anomaly' based on:
- Total activity count
- Video/Social/Messaging/Gaming ratios
- Category usage patterns

Provides:
1. Offline anomaly detection (batch)
2. Real-time anomaly scoring via rf_anomaly_check(features)
"""

from pymongo import MongoClient
from datetime import datetime, timedelta, UTC
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# =========================
# MongoDB Setup
# =========================
client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
detections = db["detections"]
anomalies = db["anomalies"]

# =========================
# Configuration
# =========================
WINDOW_MINUTES = 60  # Analyze last 60 minutes

# Thresholds for labeling (used for supervised training)
THRESHOLDS = {
    "high_activity": 10,
    "video_abuse_ratio": 0.4,
    "social_abuse_ratio": 0.4,
    "combined_abuse_ratio": 0.5,
}


# =========================
# Fetch Detection Data
# =========================
def fetch_detection_data():
    since = datetime.now(UTC) - timedelta(minutes=WINDOW_MINUTES)

    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": since},
                "roll_no": {"$exists": True},
                "category": {"$ne": "general"}
            }
        },
        {
            "$group": {
                "_id": "$roll_no",
                "total": {"$sum": 1},
                "video": {"$sum": {"$cond": [{"$eq": ["$category", "video"]}, 1, 0]}},
                "social": {"$sum": {"$cond": [{"$eq": ["$category", "social"]}, 1, 0]}},
                "messaging": {"$sum": {"$cond": [{"$eq": ["$category", "messaging"]}, 1, 0]}},
                "gaming": {"$sum": {"$cond": [{"$eq": ["$category", "gaming"]}, 1, 0]}},
                "client_ip": {"$first": "$client_ip"}
            }
        }
    ]

    data = list(detections.aggregate(pipeline))
    return pd.DataFrame(data)


# =========================
# Create Training Labels
# =========================
def create_labels(df):
    labels = []

    for _, row in df.iterrows():
        total = row["total"]
        video_ratio = row["video"] / total if total > 0 else 0
        social_ratio = row["social"] / total if total > 0 else 0
        combined = video_ratio + social_ratio

        anomaly = (
            total >= THRESHOLDS["high_activity"] or
            video_ratio >= THRESHOLDS["video_abuse_ratio"] or
            social_ratio >= THRESHOLDS["social_abuse_ratio"] or
            combined >= THRESHOLDS["combined_abuse_ratio"]
        )
        labels.append(1 if anomaly else 0)

    return np.array(labels)


# =========================
# Prepare Features
# =========================
def prepare_features(df):
    if df.empty:
        return None, None, None

    df = df[df["total"] > 0].copy()
    if df.empty:
        return None, None, None

    df["video_ratio"] = df["video"] / df["total"]
    df["social_ratio"] = df["social"] / df["total"]
    df["messaging_ratio"] = df["messaging"] / df["total"]
    df["gaming_ratio"] = df["gaming"] / df["total"]
    df["entertainment_ratio"] = (df["video"] + df["social"] + df["gaming"]) / df["total"]

    feature_cols = [
        "total", "video", "social", "messaging", "gaming",
        "video_ratio", "social_ratio", "messaging_ratio",
        "gaming_ratio", "entertainment_ratio"
    ]

    return (
        df[feature_cols].values,
        df["_id"].values,
        df["client_ip"].values
    )


# =========================
# Generate Synthetic Training Data
# =========================
def generate_training_data():
    np.random.seed(42)
    data = []
    labels = []

    # Normal behavior
    for _ in range(100):
        total = np.random.randint(1, 10)
        video = np.random.randint(0, 2)
        social = np.random.randint(0, 2)
        messaging = np.random.randint(0, 3)
        gaming = 0
        data.append([total, video, social, messaging, gaming])
        labels.append(0)

    # High activity anomalies
    for _ in range(100):
        total = np.random.randint(20, 200)
        video = np.random.randint(0, total//2)
        social = np.random.randint(0, total//2)
        gaming = np.random.randint(0, total//3)
        messaging = total - video - social - gaming
        data.append([total, video, social, messaging, gaming])
        labels.append(1)

    df = pd.DataFrame(data, columns=["total", "video", "social", "messaging", "gaming"])
    df["video_ratio"] = df["video"] / df["total"]
    df["social_ratio"] = df["social"] / df["total"]
    df["messaging_ratio"] = df["messaging"] / df["total"]
    df["gaming_ratio"] = df["gaming"] / df["total"]
    df["entertainment_ratio"] = (df["video"] + df["social"] + df["gaming"]) / df["total"]

    return df.values, np.array(labels)


# =========================
# Train Model
# =========================
def train_model():
    X_synth, y_synth = generate_training_data()

    scaler = StandardScaler()
    X_synth = scaler.fit_transform(X_synth)

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        random_state=42,
        class_weight="balanced"
    )
    model.fit(X_synth, y_synth)

    return model, scaler


# =========================
# Real-Time Random Forest Check
# =========================
_cached_model = None
_cached_scaler = None

def rf_anomaly_check(features):
    """
    Input: feature list (length 10)
    Output: (is_anomaly: bool, confidence: float)
    """
    global _cached_model, _cached_scaler

    if _cached_model is None or _cached_scaler is None:
        _cached_model, _cached_scaler = train_model()

    scaled = _cached_scaler.transform([features])
    pred = _cached_model.predict(scaled)[0]
    prob = _cached_model.predict_proba(scaled)[0][1]

    return pred == 1, float(prob)


# =========================
# Generate Reason for Anomaly
# =========================
def generate_reason(features):
    """Generate human-readable reason for why anomaly was detected"""
    total = features[0]
    gaming = features[4]
    video_ratio = features[5]
    social_ratio = features[6]
    gaming_ratio = features[8]
    entertainment_ratio = features[9]
    
    reasons = []
    
    if gaming > 0:
        reasons.append(f"Gaming detected ({int(gaming)} requests, {gaming_ratio:.0%})")
    
    if total >= 50:
        reasons.append(f"High activity ({int(total)} requests)")
    
    if video_ratio >= 0.4:
        reasons.append(f"Excessive video ({video_ratio:.0%})")
    
    if social_ratio >= 0.4:
        reasons.append(f"Excessive social media ({social_ratio:.0%})")
    
    if entertainment_ratio >= 0.5 and gaming == 0:
        reasons.append(f"High entertainment ({entertainment_ratio:.0%})")
    
    if not reasons:
        reasons.append("Unusual behavior pattern")
    
    return "; ".join(reasons)


# =========================
# Save Anomalies to Database
# =========================
def save_ml_anomalies(roll_nos, client_ips, predictions, probabilities, features):
    """Save detected anomalies to MongoDB"""
    now = datetime.now(UTC)
    saved_count = 0
    
    for i, (roll_no, pred, prob) in enumerate(zip(roll_nos, predictions, probabilities)):
        if pred == 1:  # Anomaly detected
            if prob >= 0.8:
                severity = "high"
            elif prob >= 0.6:
                severity = "medium"
            else:
                severity = "low"
            
            reason = generate_reason(features[i])
            
            anomalies.insert_one({
                "roll_no": roll_no,
                "client_ip": client_ips[i] if client_ips[i] else "unknown",
                "type": "ML_ANOMALY",
                "ml_model": "Random Forest Classifier",
                "confidence": round(float(prob), 3),
                "severity": severity,
                "reason": reason,
                "detected_by": "ml",
                "features": {
                    "total_requests": int(features[i][0]),
                    "video_count": int(features[i][1]),
                    "social_count": int(features[i][2]),
                    "messaging_count": int(features[i][3]),
                    "gaming_count": int(features[i][4]),
                    "video_ratio": round(float(features[i][5]), 3),
                    "social_ratio": round(float(features[i][6]), 3),
                    "gaming_ratio": round(float(features[i][8]), 3),
                    "entertainment_ratio": round(float(features[i][9]), 3)
                },
                "timestamp": now
            })
            saved_count += 1
    
    return saved_count


# =========================
# Main Execution
# =========================
def main():
    print("=" * 50)
    print("🤖 ML Anomaly Detection (Random Forest)")
    print("=" * 50)
    
    # Train model
    print("\n📚 Training Random Forest model...")
    model, scaler = train_model()
    print("✅ Model trained successfully")
    
    # Fetch data
    print(f"\n📊 Fetching data from last {WINDOW_MINUTES} minutes...")
    df = fetch_detection_data()
    
    if df.empty:
        print("ℹ️  No activity data found in the time window")
        return
    
    print(f"✅ Found {len(df)} user(s) with activity")
    
    # Prepare features
    features, roll_nos, client_ips = prepare_features(df)
    
    if features is None:
        print("ℹ️  No valid data after feature preparation")
        return
    
    # Predict
    print(f"\n🔍 Analyzing {len(features)} record(s)...")
    features_scaled = scaler.transform(features)
    predictions = model.predict(features_scaled)
    probabilities = model.predict_proba(features_scaled)[:, 1]
    
    # Show results
    anomaly_count = sum(predictions)
    print(f"\n📈 Results:")
    print(f"   - Total users analyzed: {len(predictions)}")
    print(f"   - Anomalies detected: {anomaly_count}")
    
    for i, (roll_no, pred, prob) in enumerate(zip(roll_nos, predictions, probabilities)):
        status = "🔴 ANOMALY" if pred == 1 else "🟢 Normal"
        print(f"   - {roll_no}: {status} (confidence: {prob:.1%})")
        if pred == 1:
            reason = generate_reason(features[i])
            print(f"     Reason: {reason}")
    
    # Save to DB
    if anomaly_count > 0:
        saved = save_ml_anomalies(roll_nos, client_ips, predictions, probabilities, features)
        print(f"\n💾 Saved {saved} anomaly record(s) to database")
    
    print("\n✅ Random Forest ML detection completed")


if __name__ == "__main__":
    main()
