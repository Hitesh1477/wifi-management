# auto_monitor.py
from capture import start_capture_stream
from analyze_activity import analyze_rows
from ml_random_forest import main as run_ml_analysis
import signal
import sys
import time
from datetime import datetime, timedelta

# Graceful shutdown handler
def signal_handler(sig, frame):
    print("\n⚠️ Monitoring stopped by user")
    sys.exit(0)

def auto_monitor(interface="wlan0", interval_minutes=1, ml_interval_minutes=5):
    signal.signal(signal.SIGINT, signal_handler)
    print("🚀 Real-time monitoring started...")
    print(f"💾 Saving detections every {interval_minutes} minute(s)")
    print(f"🤖 Running ML analysis every {ml_interval_minutes} minute(s)")
    print("Press Ctrl+C to stop\n")

    buffer = []
    next_save_time = datetime.now() + timedelta(minutes=interval_minutes)
    next_ml_time = datetime.now() + timedelta(minutes=ml_interval_minutes)

    try:
        for row in start_capture_stream(interface):
            buffer.append(row)

            # ✅ Check if it's time to save (every 1 minute)
            if datetime.now() >= next_save_time:
                if buffer:
                    print(f"⏰ {interval_minutes} minute(s) elapsed. Saving {len(buffer)} detections...")
                    analyze_rows(buffer)
                    buffer.clear()
                else:
                    print(f"⏰ {interval_minutes} minute(s) elapsed. No activity detected.")
                
                # Set next save time
                next_save_time = datetime.now() + timedelta(minutes=interval_minutes)
            
            # 🤖 Check if it's time to run ML analysis (every 5 minutes)
            if datetime.now() >= next_ml_time:
                print(f"\n{'='*50}")
                print(f"🤖 Running ML Analysis (every {ml_interval_minutes} minutes)...")
                print(f"{'='*50}")
                try:
                    run_ml_analysis()  # This also auto-blocks violators
                    print(f"✅ ML Analysis completed\n")
                except Exception as ml_error:
                    print(f"❌ ML Analysis error: {ml_error}\n")
                
                # Set next ML time
                next_ml_time = datetime.now() + timedelta(minutes=ml_interval_minutes)

    except KeyboardInterrupt:
        print("\n⚠️ Monitoring stopped by user")
        if buffer:
            print("Saving remaining buffer...")
            analyze_rows(buffer)
    except Exception as e:
        print(f"❌ Error in auto_monitor: {e}")
        if buffer:
            print("Attempting to save buffered data...")
            analyze_rows(buffer)
        sys.exit(1)

if __name__ == "__main__":
    # Default to wlan0 (Linux WiFi interface)
    # Usage: python auto_monitor.py [interface]
    # Examples:
    #   python auto_monitor.py              -> Uses wlan0
    #   python auto_monitor.py eth0         -> Uses ethernet interface
    #   python auto_monitor.py list         -> Lists available interfaces
    
    import argparse
    import subprocess
    
    parser = argparse.ArgumentParser(description="Monitor network traffic")
    parser.add_argument("interface", nargs="?", default="wlan0", 
                        help="Network interface (default: wlan0, use 'list' to show all)")
    args = parser.parse_args()
    
    interface = args.interface
    
    # List interfaces if requested
    if interface.lower() == "list":
        print("📋 Available network interfaces:")
        result = subprocess.run(["tshark", "-D"], capture_output=True, text=True)
        print(result.stdout)
        sys.exit(0)
    
    print(f"📡 Using interface: {interface}")
    auto_monitor(interface)
