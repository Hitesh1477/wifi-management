from domain_map import identify_app
from model import classify
from save_detections_batch import save_detection

def process_stream_line(line):
    try:
        parts = line.split(",")

        timestamp = parts[0]
        src_ip = parts[1]
        dst_ip = parts[2]
        dns = parts[3] if len(parts) > 3 else ""
        http = parts[4] if len(parts) > 4 else ""
        tls = parts[5] if len(parts) > 5 else ""

        domain = dns or http or tls
        if not domain:
            return

        app_name = identify_app(domain)
        category = classify(domain)

        save_detection({
            "timestamp": timestamp,
            "client_ip": src_ip,
            "domain": domain,
            "app_name": app_name,
            "category": category
        })

    except Exception as e:
        print("Error parsing line:", e)
