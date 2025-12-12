import subprocess
import shlex

def start_capture_stream(interface="Wi-Fi"):
    cmd = (
        f'tshark -i "{interface}" '
        f'-Y "dns.qry.name || http.host || tls.handshake.extensions_server_name" '
        f'-T fields '
        f'-e frame.time_epoch -e ip.src -e ip.dst '
        f'-e dns.qry.name -e http.host -e tls.handshake.extensions_server_name '
        f'-E header=n -E separator=,' 
    )

    print(f"📡 Starting live capture on {interface} ...")
    print("Press CTRL + C to stop.\n")

    process = subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    for line in process.stdout:
        if line.strip():
            yield line.strip()

    process.terminate()
