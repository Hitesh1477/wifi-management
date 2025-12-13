# capture.py
import subprocess
import csv

def start_capture_stream(interface="Wi-Fi"):
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

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)

    for line in process.stdout:
        parts = line.strip().split(",")
        if len(parts) < 5:
            continue

        yield {
            "timestamp": datetime.utcnow(),
            "client_ip": parts[1],
            "domain": parts[2] or parts[3] or parts[4]
        }
