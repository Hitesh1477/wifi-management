import time
import subprocess
from capture import start_capture
from analyze_activity import analyze_traffic


def auto_monitor(interface="Wi-Fi", capture_time=60):
    """
    Loop:
    1. Capture network packets for `capture_time` seconds.
    2. Analyze captured CSV (classify domains, write summary, send to MongoDB if configured).
    3. Generate insights from summaries.
    4. Wait and repeat.
    """
    while True:
        print("\n🚀 Starting new capture session...")

        try:
            # 1) Capture traffic
            capture_file = start_capture(interface, capture_time)
            print(f"✅ Capture completed: {capture_file}")

            # 2) Analyze traffic
            print("\n📊 Analyzing traffic...")
            analyze_traffic(capture_file)

            # 3) Generate insights
            print("\n🧠 Generating insights...")
            subprocess.run(["python", "insight_generator.py"], check=True)

        except KeyboardInterrupt:
            print("🛑 Monitoring stopped by user.")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")

        # 4) Wait before next capture
        print(f"\n⏳ Waiting {capture_time} seconds before next capture...")
        time.sleep(capture_time)


if __name__ == "__main__":
    auto_monitor(interface="Wi-Fi", capture_time=60)
