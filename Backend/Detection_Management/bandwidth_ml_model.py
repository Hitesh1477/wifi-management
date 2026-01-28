"""
Bandwidth Allocation ML Model using Random Forest Classifier
=============================================================
This model classifies user behavior into bandwidth tiers based on:
- Total activity count
- Video/Social/Messaging/Gaming ratios
- Category usage patterns

Provides:
1. Bandwidth tier prediction (LOW, MEDIUM, HIGH)
2. Real-time bandwidth recommendation via auto_assign_bandwidth(roll_no)
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
users = db["users"]

# =========================
# Configuration
# =========================
WINDOW_MINUTES = 60 * 24  # Analyze last 24 hours for bandwidth decisions

# Bandwidth tier definitions
BANDWIDTH_TIERS = {
    0: "low",      # 10 Mbps
    1: "medium",   # 25 Mbps
    2: "high"      # 100 Mbps
}

# =========================
# Fetch User Activity Data
# =========================
def get_user_features(roll_no, window_minutes=WINDOW_MINUTES):
    """Extract features for a specific user from detections collection"""
    since = datetime.now(UTC) - timedelta(minutes=window_minutes)
    
    pipeline = [
        {
            "$match": {
                "timestamp": {"$gte": since},
                "roll_no": roll_no
            }
        },
        {
            "$group": {
                "_id": "$roll_no",
                "total": {"$sum": 1},
                "video": {"$sum": {"$cond": [{"$eq": ["$category", "video"]}, 1, 0]}},
                "streaming": {"$sum": {"$cond": [{"$eq": ["$category", "streaming"]}, 1, 0]}},
                "social": {"$sum": {"$cond": [{"$eq": ["$category", "social"]}, 1, 0]}},
                "messaging": {"$sum": {"$cond": [{"$eq": ["$category", "messaging"]}, 1, 0]}},
                "gaming": {"$sum": {"$cond": [{"$eq": ["$category", "gaming"]}, 1, 0]}},
                "general": {"$sum": {"$cond": [{"$eq": ["$category", "general"]}, 1, 0]}},
            }
        }
    ]
    
    data = list(detections.aggregate(pipeline))
    
    if not data or len(data) == 0:
        # No activity data - return default features for low bandwidth
        return create_feature_vector(0, 0, 0, 0, 0, 0, 0)
    
    user_data = data[0]
    total = user_data.get("total", 0)
    video = user_data.get("video", 0)
    streaming = user_data.get("streaming", 0)
    social = user_data.get("social", 0)
    messaging = user_data.get("messaging", 0)
    gaming = user_data.get("gaming", 0)
    general = user_data.get("general", 0)
    
    return create_feature_vector(total, video, streaming, social, messaging, gaming, general)


def create_feature_vector(total, video, streaming, social, messaging, gaming, general):
    """Create feature vector from activity counts - returns exactly 13 features"""
    if total == 0:
        return [0] * 13
    
    video_ratio = video / total
    streaming_ratio = streaming / total
    social_ratio = social / total
    messaging_ratio = messaging / total
    gaming_ratio = gaming / total
    general_ratio = general / total
    
    # Combined entertainment ratio
    entertainment_ratio = (video + streaming + social + gaming) / total
    
    # Return exactly 13 features
    return [
        float(total),           # 0
        float(video),           # 1
        float(streaming),       # 2
        float(social),          # 3
        float(messaging),       # 4
        float(gaming),          # 5
        float(video_ratio),     # 6
        float(streaming_ratio), # 7
        float(social_ratio),    # 8
        float(messaging_ratio), # 9
        float(gaming_ratio),    # 10
        float(general_ratio),   # 11
        float(entertainment_ratio)  # 12
    ]


# =========================
# Generate Training Data
# =========================
def generate_training_data():
    """Generate synthetic training data for bandwidth classification"""
    np.random.seed(42)
    data = []
    labels = []
    
    # LOW tier (10 Mbps) - Light users: mostly messaging, general browsing, minimal video
    for _ in range(150):
        total = np.random.randint(5, 30)
        messaging = np.random.randint(1, max(2, int(total * 0.5)))
        general = np.random.randint(1, max(2, int(total * 0.4)))
        video = np.random.randint(0, max(1, int(total * 0.15)))
        streaming = 0
        social = np.random.randint(0, max(1, int(total * 0.15)))
        gaming = 0
        
        features = create_feature_vector(total, video, streaming, social, messaging, gaming, general)
        data.append(features)
        labels.append(0)  # LOW
    
    # MEDIUM tier (25 Mbps) - Moderate users: balanced usage, some video/social
    for _ in range(150):
        total = np.random.randint(30, 120)
        video = np.random.randint(1, max(2, int(total * 0.3)))
        streaming = np.random.randint(0, max(1, int(total * 0.25)))
        social = np.random.randint(1, max(2, int(total * 0.3)))
        messaging = np.random.randint(1, max(2, int(total * 0.25)))
        gaming = np.random.randint(0, max(1, int(total * 0.1)))
        general = max(1, total - (video + streaming + social + messaging + gaming))
        
        features = create_feature_vector(total, video, streaming, social, messaging, gaming, general)
        data.append(features)
        labels.append(1)  # MEDIUM
    
    # HIGH tier (100 Mbps) - Heavy users: lots of video, streaming, gaming
    for _ in range(150):
        total = np.random.randint(120, 500)
        video = np.random.randint(max(1, int(total * 0.15)), max(2, int(total * 0.35)))
        streaming = np.random.randint(max(1, int(total * 0.15)), max(2, int(total * 0.35)))
        gaming = np.random.randint(1, max(2, int(total * 0.25)))
        social = np.random.randint(1, max(2, int(total * 0.25)))
        messaging = np.random.randint(0, max(1, int(total * 0.15)))
        general = max(0, total - (video + streaming + social + messaging + gaming))
        
        features = create_feature_vector(total, video, streaming, social, messaging, gaming, general)
        data.append(features)
        labels.append(2)  # HIGH
    
    return np.array(data), np.array(labels)


# =========================
# Train Model
# =========================
_cached_model = None
_cached_scaler = None

def train_bandwidth_model():
    """Train the Random Forest classifier for bandwidth allocation"""
    X_train, y_train = generate_training_data()
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        random_state=42,
        class_weight="balanced"
    )
    model.fit(X_train_scaled, y_train)
    
    return model, scaler


def get_or_train_model():
    """Get cached model or train a new one"""
    global _cached_model, _cached_scaler
    
    if _cached_model is None or _cached_scaler is None:
        print("🔄 Training bandwidth allocation model...")
        _cached_model, _cached_scaler = train_bandwidth_model()
        print("✅ Model trained successfully")
    
    return _cached_model, _cached_scaler


# =========================
# Predict Bandwidth Tier
# =========================
def predict_bandwidth_tier(features):
    """
    Predict bandwidth tier from feature vector
    
    Args:
        features: List of 13 feature values
    
    Returns:
        tuple: (tier_name, confidence)
               tier_name: "low", "medium", or "high"
               confidence: probability score (0-1)
    """
    model, scaler = get_or_train_model()
    
    features_scaled = scaler.transform([features])
    prediction = model.predict(features_scaled)[0]
    probabilities = model.predict_proba(features_scaled)[0]
    confidence = float(probabilities[prediction])
    
    tier_name = BANDWIDTH_TIERS[prediction]
    
    return tier_name, confidence


# =========================
# Auto-Assign Bandwidth
# =========================
def auto_assign_bandwidth(roll_no):
    """
    Automatically assign bandwidth tier for a user based on their activity
    
    Args:
        roll_no: User's roll number
    
    Returns:
        dict: {
            "tier": "low" | "medium" | "high",
            "confidence": float (0-1),
            "features": {...},
            "explanation": str
        }
    """
    # Get user features
    features = get_user_features(roll_no)
    
    # Predict tier
    tier, confidence = predict_bandwidth_tier(features)
    
    # Generate explanation
    total_activity = int(features[0])
    
    if total_activity == 0:
        explanation = "No recent activity detected - assigned LOW tier"
    elif tier == "low":
        explanation = f"Light usage detected ({total_activity} requests in 24h) - primarily messaging/browsing"
    elif tier == "medium":
        explanation = f"Moderate usage detected ({total_activity} requests in 24h) - balanced activity"
    else:  # high
        explanation = f"Heavy usage detected ({total_activity} requests in 24h) - streaming/gaming/video"
    
    return {
        "tier": tier,
        "confidence": confidence,
        "total_activity": total_activity,
        "explanation": explanation,
        "features": {
            "total_requests": int(features[0]),
            "video_count": int(features[1]),
            "streaming_count": int(features[2]),
            "social_count": int(features[3]),
            "messaging_count": int(features[4]),
            "gaming_count": int(features[5]),
            "video_ratio": round(features[6], 3),
            "streaming_ratio": round(features[7], 3),
            "social_ratio": round(features[8], 3),
            "entertainment_ratio": round(features[12], 3)
        }
    }


# =========================
# Main Execution (for testing)
# =========================
def main():
    """Test the bandwidth allocation model"""
    print("=" * 60)
    print("🤖 Bandwidth Allocation ML Model (Random Forest)")
    print("=" * 60)
    
    # Train model
    print("\n📚 Training model...")
    model, scaler = train_bandwidth_model()
    print("✅ Model trained successfully")
    
    # Test with sample users
    print("\n🧪 Testing with sample data...")
    
    # Find some real users from database
    sample_users = list(users.find({"role": "student"}).limit(5))
    
    if sample_users:
        print(f"\n📊 Analyzing {len(sample_users)} users from database:")
        for user in sample_users:
            roll_no = user.get("roll_no")
            if not roll_no:
                continue
            
            result = auto_assign_bandwidth(roll_no)
            print(f"\n👤 User: {roll_no}")
            print(f"   Recommended Tier: {result['tier'].upper()}")
            print(f"   Confidence: {result['confidence']:.1%}")
            print(f"   {result['explanation']}")
            print(f"   Total Activity: {result['total_activity']} requests")
    else:
        print("ℹ️  No users found in database for testing")
        
        # Test with synthetic examples
        print("\n🧪 Testing with synthetic examples:")
        
        # Light user
        light_features = create_feature_vector(15, 1, 0, 2, 10, 0, 2)
        tier, conf = predict_bandwidth_tier(light_features)
        print(f"\n📱 Light User (15 requests, mostly messaging): {tier.upper()} ({conf:.1%})")
        
        # Medium user
        medium_features = create_feature_vector(60, 15, 10, 20, 10, 5, 0)
        tier, conf = predict_bandwidth_tier(medium_features)
        print(f"💻 Medium User (60 requests, balanced): {tier.upper()} ({conf:.1%})")
        
        # Heavy user
        heavy_features = create_feature_vector(250, 80, 60, 40, 20, 50, 0)
        tier, conf = predict_bandwidth_tier(heavy_features)
        print(f"🎮 Heavy User (250 requests, gaming/streaming): {tier.upper()} ({conf:.1%})")
    
    print("\n✅ Bandwidth allocation model testing completed")


if __name__ == "__main__":
    main()
