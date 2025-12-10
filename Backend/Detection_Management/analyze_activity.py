import pandas as pd
from datetime import datetime
from model import classify
from detection_store import save_detections_batch


def map_ip_to_roll(ip: str) -> str:
    """
    For now, we just use IP as roll_no.
    Later you can map IP -> student roll number using a CSV or DB.
    """
    return ip or "unknown"


def analyze_traffic(csv_path):
    print(f"\n📊 Analyzing {csv_path} ...")

    # 1) Load capture CSV
    df = pd.read_csv(csv_path, sep=",", engine="python", on_bad_lines="skip")

    # 2) Merge host columns
    host_cols = ["dns.qry.name", "http.host", "tls.handshake.extensions_server_name"]
    for col in host_cols:
        if col not in df.columns:
            df[col] = None

    df["host"] = df[host_cols].bfill(axis=1).iloc[:, 0]
    df = df.dropna(subset=["host"])

    # 3) Time + 10 second bucket
    df["time"] = pd.to_datetime(df["frame.time_epoch"], unit="s", errors="coerce")
    df["time_bucket_epoch"] = (df["frame.time_epoch"] // 10) * 10
    df["time_bucket"] = pd.to_datetime(df["time_bucket_epoch"], unit="s", errors="coerce")

    # 4) Category
    df["category"] = df["host"].apply(classify)

    # 5) Summary per (bucket, ip, category)
    summary = (
        df.groupby(["time_bucket", "ip.src", "category"])
        .size()
        .reset_index(name="packet_count")
    )

    summary_path = csv_path.replace("capture_", "summary_")
    summary.to_csv(summary_path, index=False)
    print(f"✅ Summary -> {summary_path}")

    # 6) Build detection docs for MongoDB
    items = []
    for _, row in summary.iterrows():
        ts = row["time_bucket"]
        if pd.isna(ts):
            ts_dt = None
        else:
            ts_dt = ts.to_pydatetime()

        roll_no = map_ip_to_roll(row["ip.src"])
        cat = row["category"]
        count = float(row["packet_count"])

        reason = f"{cat} activity"
        details = f"time_bucket={ts_dt}, ip={row['ip.src']}, packets={int(count)}"

        items.append(
            {
                "roll_no": roll_no,
                "timestamp": ts_dt,
                "reason": reason,
                "score": count,
                "details": details,
            }
        )

    # 7) Save to MongoDB
    if items:
        save_detections_batch(items)
        print(f"📥 Inserted {len(items)} detections into MongoDB")
    else:
        print("ℹ️ No detections to insert.")

    return summary
