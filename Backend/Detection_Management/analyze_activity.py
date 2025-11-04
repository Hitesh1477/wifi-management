import pandas as pd
import os
from datetime import datetime
from model import classify

def analyze_traffic(csv_path):
    print(f"📊 Analyzing {csv_path} ...")
    df = pd.read_csv(csv_path, sep=',', engine='python', on_bad_lines='skip')

    # Merge DNS/HTTP/TLS host fields
    host_cols = ['dns.qry.name', 'http.host', 'tls.handshake.extensions_server_name']
    for col in host_cols:
        if col not in df.columns:
            df[col] = None
    df['host'] = df[host_cols].bfill(axis=1).iloc[:, 0]
    df.dropna(subset=['host'], inplace=True)

    # Convert timestamp and bucket into 10s intervals
    df['time'] = pd.to_datetime(df['frame.time_epoch'], unit='s', errors='coerce')
    df['time_bucket'] = (df['frame.time_epoch'] // 10) * 10  # group every 10s
    df['time_bucket'] = pd.to_datetime(df['time_bucket'], unit='s')

    # Classify domains
    df['category'] = df['host'].apply(classify)

    # Group by 10s interval and IP
    summary = (
        df.groupby(['time_bucket', 'ip.src', 'category'])
        .size()
        .reset_index(name='packet_count')
    )

    # Save summarized and detailed logs
    detail_path = csv_path.replace("capture_", "detailed_")
    summary_path = csv_path.replace("capture_", "summary_")

    df[['time', 'ip.src', 'ip.dst', 'host', 'category']].to_csv(detail_path, index=False)
    summary.to_csv(summary_path, index=False)

    print(f"✅ Detailed log -> {detail_path}")
    print(f"✅ Summary (10s grouped) -> {summary_path}")
    return summary

if __name__ == "__main__":
    # Example: test manually on one file
    test_file = "capture_20251103_191137.csv"
    if os.path.exists(test_file):
        analyze_traffic(test_file)
