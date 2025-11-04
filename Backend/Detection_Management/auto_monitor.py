import time
import subprocess
from capture import start_capture
from analyze_activity import analyze_traffic
import os

def auto_monitor(interface="Wi-Fi", capture_time=60, analyze_after=3):
    """
    Automated monitoring loop:
    1. Capture network packets using tshark.
    2. Analyze captured data in batches.
    3. Generate insight summary after every batch.
    """
    captured_files = []

    while True:
        print("\n🚀 Starting new capture session...")
        try:
            # Start capture and save CSV file
            capture_file = start_capture(interface)
            captured_files.append(capture_file)
            print(f"✅ Capture completed: {capture_file}")

            # Analyze after N captures
            if len(captured_files) >= analyze_after:
                print("\n📈 Running analysis on recent captures...")
                for f in captured_files:
                    try:
                        analyze_traffic(f)
                    except Exception as e:
                        print(f"⚠️ Error analyzing {f}: {e}")
                captured_files.clear()

                print("\n🧠 Generating overall insights...")
                try:
                    subprocess.run(["python", "insight_generator.py"], check=True)
                    print("✅ Insight generation complete.")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️ Insight generator error: {e}")

        except KeyboardInterrupt:
            print("🛑 Monitoring stopped by user.")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")

        print(f"\n⏳ Waiting {capture_time} seconds before next capture...")
        time.sleep(capture_time)

if __name__ == "__main__":
    # Capture for 60 seconds each, analyze after 3 captures (3 minutes total)
    auto_monitor(interface="Wi-Fi", capture_time=60, analyze_after=3)
