# capture.py
import subprocess
import threading
from datetime import datetime
import sys
import time

def _read_stderr(process, label="tshark"):
    """Read and print stderr from tshark in a background thread."""
    for line in process.stderr:
        line = line.strip()
        if line:
            print(f"[{label} stderr] {line}")

def start_capture_stream(interface="wlan0", retry=True, retry_delay=3):
    """
    Stream packets from tshark. Automatically retries if tshark exits.
    Shows tshark errors via stderr so issues are visible.
    """
    while True:
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

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print(f"✅ Started packet capture on interface: {interface}")

            # Read stderr in background thread so we can see tshark errors
            stderr_thread = threading.Thread(
                target=_read_stderr,
                args=(process, "tshark"),
                daemon=True
            )
            stderr_thread.start()

            packet_count = 0
            for line in process.stdout:
                try:
                    parts = line.strip().split(",")
                    if len(parts) < 5:
                        continue

                    domain = parts[2] or parts[3] or parts[4]
                    if not domain or domain.strip() == "":
                        continue

                    packet_count += 1
                    yield {
                        "timestamp": datetime.utcnow(),
                        "client_ip": parts[1],
                        "domain": domain
                    }
                except Exception as e:
                    print(f"⚠️ Error parsing packet line: {e}")
                    continue

            # tshark exited - check return code
            process.wait()
            rc = process.returncode
            print(f"⚠️ tshark exited (return code: {rc}, packets captured: {packet_count})")

            if not retry:
                break

            print(f"🔄 Restarting capture in {retry_delay}s... (Ctrl+C to stop)")
            time.sleep(retry_delay)

        except FileNotFoundError:
            print("❌ tshark not found. Install with: sudo apt install tshark")
            sys.exit(1)
        except PermissionError:
            print("❌ Permission denied. Run with: sudo python3 auto_monitor.py")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error starting packet capture: {e}")
            if not retry:
                sys.exit(1)
            print(f"🔄 Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
