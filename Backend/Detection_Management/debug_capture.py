# debug_capture.py - See what IPs are being captured from the hotspot
from capture import start_capture_stream
from collections import Counter
import signal
import sys

def signal_handler(sig, frame):
    print("\n⚠️ Stopped by user")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print("🔍 Debug mode: Showing captured IPs...")
print("This will show what IP addresses are in the captured traffic")
print("Press Ctrl+C to stop\n")

interface = sys.argv[1] if len(sys.argv) > 1 else "Local Area Connection* 2"
print(f"📡 Capturing from: {interface}\n")

ip_counter = Counter()
count = 0

for row in start_capture_stream(interface):
    ip = row.get("client_ip", "unknown")
    domain = row.get("domain", "")
    ip_counter[ip] += 1
    count += 1
    
    # Show first 20 packets with details
    if count <= 20:
        print(f"  IP: {ip:20} Domain: {domain[:50]}")
    elif count == 21:
        print("\n... (showing IP summary every 50 packets)")
    
    # Show summary every 50 packets
    if count % 50 == 0:
        print(f"\n📊 Top 5 IPs after {count} packets:")
        for ip, cnt in ip_counter.most_common(5):
            print(f"    {ip}: {cnt} packets")
        print()
