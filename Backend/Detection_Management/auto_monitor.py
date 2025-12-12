import time
from capture import start_capture_stream
from analyze_activity import process_stream_line

def auto_monitor(interface="Wi-Fi"):
    print("🚀 Real-time monitoring started...")

    try:
        for line in start_capture_stream(interface):
            process_stream_line(line)

    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user.")

if __name__ == "__main__":
    auto_monitor("Wi-Fi")
