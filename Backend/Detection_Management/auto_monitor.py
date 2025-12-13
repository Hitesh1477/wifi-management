# auto_monitor.py
from capture import start_capture_stream
from analyze_activity import analyze_rows

def auto_monitor(interface="Wi-Fi"):
    print("🚀 Real-time monitoring started...")

    buffer = []

    for row in start_capture_stream(interface):
        buffer.append(row)

        if len(buffer) >= 10:  # batch every 10 events
            analyze_rows(buffer)
            buffer.clear()

if __name__ == "__main__":
    auto_monitor("Wi-Fi")
