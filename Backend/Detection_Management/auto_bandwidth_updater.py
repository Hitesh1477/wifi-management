"""
Auto Bandwidth Updater - Periodic Background Script
====================================================
This script runs periodically to update bandwidth allocation for users
who have AUTO mode enabled.

It:
1. Finds all users with bandwidth_limit='auto'
2. Re-analyzes their activity patterns
3. Updates bandwidth tier if it has changed
4. Logs all changes
"""

from pymongo import MongoClient
from datetime import datetime, UTC
import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Detection_Management.bandwidth_ml_model import auto_assign_bandwidth
except ImportError:
    print("⚠️ Could not import bandwidth_ml_model. Make sure you're running from the correct directory.")
    sys.exit(1)

# =========================
# MongoDB Setup
# =========================
client = MongoClient("mongodb://localhost:27017/")
db = client["studentapp"]
users = db["users"]

# =========================
# Configuration
# =========================
UPDATE_INTERVAL_MINUTES = 60  # Run every hour
CONFIDENCE_THRESHOLD = 0.6  # Only update if confidence is above this threshold

def update_auto_bandwidth_users():
    """Find and update all users with AUTO bandwidth mode"""
    print("=" * 60)
    print("🔄 Auto Bandwidth Updater")
    print(f"⏰ {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    # Find all users with AUTO mode
    auto_users = list(users.find({"bandwidth_limit": "auto", "role": "student"}))
    
    if not auto_users:
        print("ℹ️  No users with AUTO bandwidth mode found")
        return 0
    
    print(f"\n📊 Found {len(auto_users)} user(s) with AUTO bandwidth mode")
    
    updated_count = 0
    unchanged_count = 0
    error_count = 0
    
    for user in auto_users:
        roll_no = user.get("roll_no")
        if not roll_no:
            continue
        
        current_assigned = user.get("bandwidth_auto_assigned", "medium")
        
        try:
            # Get new recommendation
            result = auto_assign_bandwidth(roll_no)
            new_tier = result['tier']
            confidence = result['confidence']
            
            # Only update if confidence is high enough
            if confidence < CONFIDENCE_THRESHOLD:
                print(f"⚠️  {roll_no}: Low confidence ({confidence:.1%}), keeping {current_assigned.upper()}")
                unchanged_count += 1
                continue
            
            # Check if tier has changed
            if new_tier != current_assigned:
                # Update user document
                users.update_one(
                    {"roll_no": roll_no},
                    {
                        "$set": {
                            "bandwidth_auto_assigned": new_tier,
                            "bandwidth_auto_confidence": confidence,
                            "bandwidth_last_updated": datetime.utcnow()
                        }
                    }
                )
                
                print(f"✅ {roll_no}: {current_assigned.upper()} → {new_tier.upper()} ({confidence:.1%})")
                print(f"   Reason: {result.get('explanation', 'N/A')}")
                updated_count += 1
            else:
                print(f"➡️  {roll_no}: Unchanged ({new_tier.upper()}, {confidence:.1%})")
                
                # Update confidence even if tier hasn't changed
                users.update_one(
                    {"roll_no": roll_no},
                    {
                        "$set": {
                            "bandwidth_auto_confidence": confidence,
                            "bandwidth_last_updated": datetime.utcnow()
                        }
                    }
                )
                unchanged_count += 1
                
        except Exception as e:
            print(f"❌ {roll_no}: Error - {e}")
            error_count += 1
    
    print(f"\n📈 Summary:")
    print(f"   Updated: {updated_count}")
    print(f"   Unchanged: {unchanged_count}")
    print(f"   Errors: {error_count}")
    
    return updated_count


def main():
    """Main execution loop"""
    print("🚀 Auto Bandwidth Updater started")
    print(f"⏱️  Update interval: {UPDATE_INTERVAL_MINUTES} minutes\n")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            try:
                updates = update_auto_bandwidth_users()
                
                if updates > 0:
                    print(f"\n✅ Successfully updated {updates} user(s)")
                
                print(f"\n⏳ Next update in {UPDATE_INTERVAL_MINUTES} minutes...")
                print(f"   Next run at: {datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=UPDATE_INTERVAL_MINUTES)}")
                
                # Wait for next iteration
                time.sleep(UPDATE_INTERVAL_MINUTES * 60)
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"\n❌ Error in update cycle: {e}")
                import traceback
                traceback.print_exc()
                print(f"\n⏳ Retrying in {UPDATE_INTERVAL_MINUTES} minutes...")
                time.sleep(UPDATE_INTERVAL_MINUTES * 60)
                
    except KeyboardInterrupt:
        print("\n\n⛔ Auto Bandwidth Updater stopped by user")
        print("Goodbye! 👋")


if __name__ == "__main__":
    # Import datetime.timedelta
    from datetime import timedelta
    
    # Allow running once if --once argument is passed
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        print("🔄 Running single update cycle\n")
        updates = update_auto_bandwidth_users()
        print(f"\n✅ Update cycle complete. Updated {updates} user(s)")
    else:
        main()
