import os
import pandas as pd
from model import classify

def generate_summary(capture_file):
    print(f"Processing: {capture_file}")
    df = pd.read_csv(capture_file, sep=',', engine='python', on_bad_lines='skip')

    # merge host columns if they exist
    host_cols = [c for c in ['dns.qry.name', 'http.host', 'tls.handshake.extensions_server_name'] if c in df.columns]
    if not host_cols:
        print(f"⚠️ No host columns found in {capture_file}")
        return

    df['host'] = df[host_cols].bfill(axis=1).iloc[:, 0]
    df.dropna(subset=['host'], inplace=True)

    # classify
    df['category'] = df['host'].apply(classify)

    summary = df.groupby(['ip.src', 'category']).size().reset_index(name='count')

    summary_file = capture_file.replace("capture_", "summary_")
    summary.to_csv(summary_file, index=False)
    print(f"✅ Saved: {summary_file}")

if __name__ == "__main__":
    capture_files = [f for f in os.listdir() if f.startswith("capture_") and f.endswith(".csv")]
    if not capture_files:
        print("No capture files found.")
    else:
        for file in capture_files:
            generate_summary(file)
