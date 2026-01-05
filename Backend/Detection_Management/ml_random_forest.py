"""
ML Anomaly Detection using Random Forest Classifier
====================================================
This model classifies user behavior as 'normal' or 'anomaly' based on:
- Total activity count
- Video/Social/Messaging ratios
- Category usage patterns

Works with single user data (unlike Isolation Forest which needs multiple users)
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

# Thresholds for labeling (used to train the ML model)
THRESHOLDS = {
    "high_activity": 10,           # More than 10 requests = high activity
    "video_abuse_ratio": 0.4,      # More than 40% video = video abuse
    "social_abuse_ratio": 0.4,     # More than 40% social = social abuse
    "combined_abuse_ratio": 0.5,   # More than 50% video+social = abuse
}


# =========================
# Fetch Data from MongoDB
# =========================
def fetch_detection_data():
    """Fetch per-user activity data from detections collection"""
    since = datetime.now(UTC) - timedelta(minutes=WINDOW_MINUTES)

    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": since},
                "roll_no": {"$exists": True},
                "client_ip": {"$ne": ""},
                "category": {"$nin": ["general", "system", "search"]}  # Exclude non-entertainment
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
        },
        {
            "$match": {"total": {"$gt": 0}}
        }
    ]

    data = list(detections.aggregate(pipeline))
    return pd.DataFrame(data)


# =========================
# Create Training Labels
# =========================
def create_labels(df):
    """
    Create training labels based on thresholds.
    This is a supervised approach where we define what's 'anomaly'.
    """
    labels = []
    
    for _, row in df.iterrows():
        total = row["total"]
        video_ratio = row["video"] / total if total > 0 else 0
        social_ratio = row["social"] / total if total > 0 else 0
        combined_ratio = video_ratio + social_ratio
        
        # Check for anomaly conditions
        is_anomaly = (
            total >= THRESHOLDS["high_activity"] or
            video_ratio >= THRESHOLDS["video_abuse_ratio"] or
            social_ratio >= THRESHOLDS["social_abuse_ratio"] or
            combined_ratio >= THRESHOLDS["combined_abuse_ratio"]
        )
        
        labels.append(1 if is_anomaly else 0)
    
    return np.array(labels)


# =========================
# Prepare Features
# =========================
def prepare_features(df):
    """Prepare feature matrix for ML model"""
    if df.empty:
        return None, None, None
    
    df = df[df["total"] > 0].copy()
    
    if df.empty:
        return None, None, None
    
    # Ensure gaming column exists
    if "gaming" not in df.columns:
        df["gaming"] = 0
    
    # Calculate ratios
    df["video_ratio"] = df["video"] / df["total"]
    df["social_ratio"] = df["social"] / df["total"]
    df["messaging_ratio"] = df["messaging"] / df["total"]
    df["gaming_ratio"] = df["gaming"] / df["total"]
    df["entertainment_ratio"] = (df["video"] + df["social"] + df["gaming"]) / df["total"]
    
    # Feature columns (now includes gaming)
    feature_cols = [
        "total", "video", "social", "messaging", "gaming",
        "video_ratio", "social_ratio", "messaging_ratio", "gaming_ratio", "entertainment_ratio"
    ]
    
    features = df[feature_cols].values
    roll_nos = df["_id"].values
    client_ips = df["client_ip"].values if "client_ip" in df.columns else [None] * len(df)
    
    return features, roll_nos, client_ips


# =========================
# Generate Synthetic Training Data
# =========================
def generate_training_data():
    """
    Generate synthetic training data to train the model.
    Covers realistic ranges including high activity users and gaming.
    """
    np.random.seed(42)
    
    training_data = []
    labels = []
    
    # === NORMAL BEHAVIOR PATTERNS ===
    # Low activity, balanced usage (no gaming)
    for _ in range(100):
        total = np.random.randint(1, 10)
        video = np.random.randint(0, max(1, int(total * 0.2)))
        social = np.random.randint(0, max(1, int(total * 0.2)))
        messaging = np.random.randint(0, max(1, int(total * 0.3)))
        gaming = 0  # No gaming in normal behavior
        training_data.append([total, video, social, messaging, gaming])
        labels.append(0)  # Normal
    
    # Medium activity, still balanced (minimal entertainment)
    for _ in range(50):
        total = np.random.randint(10, 50)
        video = np.random.randint(0, max(1, int(total * 0.15)))
        social = np.random.randint(0, max(1, int(total * 0.15)))
        messaging = np.random.randint(0, max(1, int(total * 0.2)))
        gaming = 0  # No gaming in normal behavior
        training_data.append([total, video, social, messaging, gaming])
        labels.append(0)  # Normal
    
    # === ANOMALY PATTERNS ===
    # High activity (lots of requests regardless of category)
    for _ in range(40):
        total = np.random.randint(50, 200)
        video = np.random.randint(0, total // 3)
        social = np.random.randint(0, total // 3)
        gaming = np.random.randint(0, total // 4)
        messaging = max(0, total - video - social - gaming)
        training_data.append([total, video, social, messaging, gaming])
        labels.append(1)  # Anomaly - high activity
    
    # High video ratio (>40% video)
    for _ in range(40):
        total = np.random.randint(5, 100)
        video = np.random.randint(int(total * 0.45), total)
        social = np.random.randint(0, max(1, total - video))
        gaming = 0
        messaging = max(0, total - video - social)
        training_data.append([total, video, social, messaging, gaming])
        labels.append(1)  # Anomaly - video abuse
    
    # High social ratio (>40% social)
    for _ in range(40):
        total = np.random.randint(5, 200)
        social = np.random.randint(int(total * 0.45), total)
        video = np.random.randint(0, max(1, total - social))
        gaming = 0
        messaging = max(0, total - video - social)
        training_data.append([total, video, social, messaging, gaming])
        labels.append(1)  # Anomaly - social abuse
    
    # === GAMING PATTERNS (ALWAYS ANOMALY) ===
    # Any gaming activity is suspicious
    for _ in range(60):
        total = np.random.randint(3, 100)
        gaming = np.random.randint(1, total)  # At least 1 gaming request
        video = np.random.randint(0, max(1, total - gaming))
        social = np.random.randint(0, max(1, total - gaming - video))
        messaging = max(0, total - video - social - gaming)
        training_data.append([total, video, social, messaging, gaming])
        labels.append(1)  # Anomaly - gaming detected
    
    # High entertainment ratio (>50% video+social+gaming combined)
    for _ in range(40):
        total = np.random.randint(10, 150)
        entertainment = np.random.randint(int(total * 0.55), total)
        video = np.random.randint(0, entertainment // 2)
        social = np.random.randint(0, entertainment - video)
        gaming = entertainment - video - social
        messaging = max(0, total - video - social - gaming)
        training_data.append([total, video, social, messaging, gaming])
        labels.append(1)  # Anomaly - entertainment abuse
    
    # Create DataFrame with gaming column
    df = pd.DataFrame(training_data, columns=["total", "video", "social", "messaging", "gaming"])
    df["video_ratio"] = df["video"] / df["total"]
    df["social_ratio"] = df["social"] / df["total"]
    df["messaging_ratio"] = df["messaging"] / df["total"]
    df["gaming_ratio"] = df["gaming"] / df["total"]
    df["entertainment_ratio"] = (df["video"] + df["social"] + df["gaming"]) / df["total"]
    
    feature_cols = [
        "total", "video", "social", "messaging", "gaming",
        "video_ratio", "social_ratio", "messaging_ratio", "gaming_ratio", "entertainment_ratio"
    ]
    
    return df[feature_cols].values, np.array(labels)


# =========================
# Train Random Forest Model
# =========================
def train_model():
    """Train Random Forest on synthetic + real labeled data"""
    X_train, y_train = generate_training_data()
    
    # Normalize features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    # Train Random Forest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight="balanced"  # Handle imbalanced classes
    )
    model.fit(X_train_scaled, y_train)
    
    return model, scaler


# =========================
# Predict Anomalies
# =========================
def predict_anomalies(model, scaler, features):
    """Use trained model to predict anomalies"""
    features_scaled = scaler.transform(features)
    predictions = model.predict(features_scaled)
    probabilities = model.predict_proba(features_scaled)[:, 1]  # Probability of anomaly
    
    return predictions, probabilities


# =========================
# Generate Anomaly Reason
# =========================
def generate_reason(features):
    """Generate human-readable reason for why anomaly was detected"""
    total = features[0]
    video = features[1]
    social = features[2]
    messaging = features[3]
    gaming = features[4]
    video_ratio = features[5]
    social_ratio = features[6]
    gaming_ratio = features[8]
    entertainment_ratio = features[9]
    
    reasons = []
    
    # Check each anomaly condition
    if gaming > 0:
        reasons.append(f"Gaming activity detected ({int(gaming)} requests, {gaming_ratio:.0%} of traffic)")
    
    if total >= 50:
        reasons.append(f"High activity volume ({int(total)} requests in analysis window)")
    
    if video_ratio >= 0.4:
        reasons.append(f"Excessive video streaming ({video_ratio:.0%} of traffic)")
    
    if social_ratio >= 0.4:
        reasons.append(f"Excessive social media usage ({social_ratio:.0%} of traffic)")
    
    if entertainment_ratio >= 0.5 and gaming == 0:
        reasons.append(f"High entertainment usage ({entertainment_ratio:.0%} video+social)")
    
    if not reasons:
        reasons.append("Unusual behavior pattern detected by ML model")
    
    return "; ".join(reasons)


# =========================
# Save Anomalies to DB
# =========================
def save_ml_anomalies(roll_nos, client_ips, predictions, probabilities, features):
    """Save detected anomalies to MongoDB"""
    now = datetime.now(UTC)
    saved_count = 0
    
    for i, (roll_no, pred, prob) in enumerate(zip(roll_nos, predictions, probabilities)):
        if pred == 1:  # Anomaly detected
            # Determine severity based on probability
            if prob >= 0.8:
                severity = "high"
            elif prob >= 0.6:
                severity = "medium"
            else:
                severity = "low"
            
            # Generate human-readable reason
            reason = generate_reason(features[i])
            
            anomalies.insert_one({
                "roll_no": roll_no,
                "client_ip": client_ips[i] if client_ips[i] else "unknown",
                "type": "ML_ANOMALY",
                "ml_model": "Random Forest Classifier",
                "confidence": round(float(prob), 3),
                "severity": severity,
                "reason": reason,  # New field!
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
# Main Function
# =========================
def main():
    print("=" * 50)
    print("🤖 ML Anomaly Detection (Random Forest Classifier)")
    print("=" * 50)
    
    # Step 1: Train model
    print("\n📚 Training Random Forest model...")
    model, scaler = train_model()
    print("✅ Model trained successfully")
    
    # Step 2: Fetch real data
    print(f"\n📊 Fetching data from last {WINDOW_MINUTES} minutes...")
    df = fetch_detection_data()
    
    if df.empty:
        print("ℹ️ No activity data found in the time window")
        return
    
    print(f"✅ Found {len(df)} user(s) with activity")
    
    # Step 3: Prepare features
    features, roll_nos, client_ips = prepare_features(df)
    
    if features is None:
        print("ℹ️ No valid data after feature preparation")
        return
    
    # Step 4: Predict
    print(f"\n🔍 Analyzing {len(features)} record(s)...")
    predictions, probabilities = predict_anomalies(model, scaler, features)
    
    # Step 5: Show results
    anomaly_count = sum(predictions)
    print(f"\n📈 Results:")
    print(f"   - Total users analyzed: {len(predictions)}")
    print(f"   - Anomalies detected: {anomaly_count}")
    
    # Show details for each user
    for i, (roll_no, pred, prob) in enumerate(zip(roll_nos, predictions, probabilities)):
        status = "🔴 ANOMALY" if pred == 1 else "🟢 Normal"
        print(f"   - {roll_no}: {status} (confidence: {prob:.1%})")
        if pred == 1:
            reason = generate_reason(features[i])
            print(f"     Reason: {reason}")
    
    # Step 6: Save to DB
    if anomaly_count > 0:
        saved = save_ml_anomalies(roll_nos, client_ips, predictions, probabilities, features)
        print(f"\n💾 Saved {saved} anomaly record(s) to database")
    
    print("\n✅ Random Forest ML detection completed")


if __name__ == "__main__":
    main()
