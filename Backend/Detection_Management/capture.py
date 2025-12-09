import subprocess
import os
from datetime import datetime

def start_capture(interface="Wi-Fi"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"capture_{timestamp}.csv"
    output_path = os.path.join(os.path.dirname(__file__), output_file)

    tshark_cmd = [
        "tshark", "-i", interface,
        "-Y", "dns.qry.name || http.host || tls.handshake.extensions_server_name",
        "-T", "fields",
        "-e", "frame.time_epoch", "-e", "ip.src", "-e", "ip.dst",
        "-e", "dns.qry.name", "-e", "http.host", "-e", "tls.handshake.extensions_server_name",
        "-E", "header=y", "-E", "separator=,"
    ]

    print(f"📡 Capturing packets... (Press Ctrl+C to stop)\nFile: {output_path}")
    with open(output_path, "w") as f:
        subprocess.run(tshark_cmd, stdout=f)
    return output_path
