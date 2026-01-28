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
# ADJUSTED FOR COLLEGE USE - More strict to detect non-academic activity
THRESHOLDS = {
    "high_activity": 5,           # Lowered from 10 - even moderate activity is flagged
    "video_abuse_ratio": 0.15,    # Lowered from 0.4 - any significant video is flagged
    "social_abuse_ratio": 0.15,   # Lowered from 0.4 - any significant social media is flagged
    "gaming_threshold": 1,        # Even 1 gaming request is an anomaly
    "combined_abuse_ratio": 0.25, # Lowered from 0.5 - stricter entertainment threshold
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
        gaming = row["gaming"]
        combined = video_ratio + social_ratio

        # STRICTER RULES FOR COLLEGE USE:
        # Gaming = immediate anomaly (non-academic)
        # High video/social = anomaly
        # Even moderate entertainment = anomaly
        anomaly = (
            gaming >= THRESHOLDS["gaming_threshold"] or          # Any gaming
            total >= THRESHOLDS["high_activity"] or              # High activity
            video_ratio >= THRESHOLDS["video_abuse_ratio"] or    # Video streaming
            social_ratio >= THRESHOLDS["social_abuse_ratio"] or  # Social media
            combined >= THRESHOLDS["combined_abuse_ratio"]       # Combined entertainment
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

    # Normal behavior - STRICT ACADEMIC USE ONLY (200 examples)
    # Only messaging and minimal general browsing
    for _ in range(200):
        total = np.random.randint(1, 8)  # Very low activity
        video = 0  # No video
        social = 0  # No social media
        messaging = np.random.randint(0, max(1, int(total * 0.8)))  # Mostly messaging
        gaming = 0  # No gaming
        data.append([total, video, social, messaging, gaming])
        labels.append(0)  # NORMAL

    # High activity anomalies - NON-ACADEMIC (200 examples)
    # Any significant entertainment = anomaly
    for _ in range(200):
        total = np.random.randint(5, 200)
        
        # Random mix of entertainment activities
        video = np.random.randint(0, max(1, int(total * 0.4)))
        social = np.random.randint(0, max(1, int(total * 0.4)))
        gaming = np.random.randint(0, max(1, int(total * 0.3)))
        messaging = np.random.randint(0, max(1, int(total * 0.3)))
        
        data.append([total, video, social, messaging, gaming])
        labels.append(1)  # ANOMALY
    
    # GAMING SPECIFIC ANOMALIES (150 examples)
    # Gaming should ALWAYS be detected with HIGH confidence
    for _ in range(150):
        total = np.random.randint(3, 150)
        gaming = np.random.randint(1, max(2, int(total * 0.6)))  # Significant gaming
        video = np.random.randint(0, max(1, int(total * 0.2)))
        social = np.random.randint(0, max(1, int(total * 0.2)))
        messaging = np.random.randint(0, max(1, int(total * 0.2)))
        
        data.append([total, video, social, messaging, gaming])
        labels.append(1)  # ANOMALY - GAMING

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

    # Adjusted for COLLEGE USE - Higher confidence in predictions
    model = RandomForestClassifier(
        n_estimators=150,      # Increased from 100 for better confidence
        max_depth=20,          # Increased from 12 for better separation
        min_samples_split=2,   # More specific splits
        min_samples_leaf=1,    # Allow very specific patterns
        random_state=42,
        class_weight={0: 1, 1: 3}  # Weight anomalies 3x more (gaming is important)
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
    
    # PRIORITY: Gaming is the most important for college monitoring
    if gaming > 0:
        reasons.append(f"🎮 GAMING DETECTED ({int(gaming)} requests, {gaming_ratio:.0%} of activity) - Non-academic use")
    
    if total >= 50:
        reasons.append(f"High activity ({int(total)} requests)")
    
    if video_ratio >= 0.15:
        reasons.append(f"Video streaming ({video_ratio:.0%})")
    
    if social_ratio >= 0.15:
        reasons.append(f"Social media usage ({social_ratio:.0%})")
    
    if entertainment_ratio >= 0.25 and gaming == 0:
        reasons.append(f"Entertainment focused ({entertainment_ratio:.0%})")
    
    if not reasons:
        reasons.append("Unusual behavior pattern detected")
    
    return "; ".join(reasons)


# =========================
# Save Anomalies to Database
# =========================
def save_ml_anomalies(roll_nos, client_ips, predictions, probabilities, features):
    """Save detected anomalies to MongoDB and auto-block high confidence violations"""
    from block_user import block_user  # Import blocking function
    
    now = datetime.now(UTC)
    saved_count = 0
    blocked_count = 0
    
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
            
            # AUTO-BLOCK: If confidence is high enough, block the user
            # - confidence >= 95% => PERMANENT BAN
            # - confidence >= 75% => 24-HOUR TEMPORARY BAN
            if prob >= 0.75:
                if block_user(roll_no, prob, reason):
                    blocked_count += 1
                    print(f"   🚫 AUTO-BLOCKED: {roll_no} (confidence: {prob:.1%})")
    
    if blocked_count > 0:
        print(f"\n⚠️  AUTO-BLOCKED {blocked_count} user(s) for policy violations")
    
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
