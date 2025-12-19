# capture.py
import subprocess
import csv
from datetime import datetime
import sys

def start_capture_stream(interface="Wi-Fi"):
    try:
        cmd = [
            "tshark", "-i", interface,
            "-Y", "dns.qry.name || http.host || tls.handshake.extensions_server_name",
            "-T", "fields",
            "-e", "frame.time_epoch",
            "-e", "ip.src",
            "-e", "dns.qry.name",
            "-e", "http.host",
            "-e", "tls.handshake.extensions_server_name",
            "-E", "separator=,"
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"✅ Started packet capture on interface: {interface}")

        for line in process.stdout:
            try:
                parts = line.strip().split(",")
                if len(parts) < 5:
                    continue

                domain = parts[2] or parts[3] or parts[4]
                if not domain or domain.strip() == "":
                    continue

                yield {
                    "timestamp": datetime.utcnow(),
                    "client_ip": parts[1],
                    "domain": domain
                }
            except Exception as e:
                print(f"⚠️ Error parsing packet line: {e}")
                continue

    except FileNotFoundError:
        print("❌ tshark not found. Please install Wireshark/tshark")
        print("Download from: https://www.wireshark.org/download.html")
        sys.exit(1)
    except PermissionError:
        print("❌ Permission denied. Run as Administrator to capture packets")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting packet capture: {e}")
        sys.exit(1)
