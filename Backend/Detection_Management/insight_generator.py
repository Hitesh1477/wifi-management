import os
import pandas as pd

def generate_insights():
    # Find all summary files
    summary_files = [f for f in os.listdir() if f.startswith("summary_") and f.endswith(".csv")]
    if not summary_files:
        print("❌ No summary_*.csv files found. Run analysis first.")
        return

    print("🔍 Reading summary files:")
    dfs = []
    for f in summary_files:
        print(f"  - {f}")
        df = pd.read_csv(f)
        dfs.append(df)

    all_data = pd.concat(dfs, ignore_index=True)

    # We expect: time_bucket, ip.src, category, packet_count
    expected_cols = {"time_bucket", "ip.src", "category", "packet_count"}
    missing = expected_cols - set(all_data.columns)
    if missing:
        print(f"⚠️ Missing columns in CSV. Found: {list(all_data.columns)}")
        print(f"   Expected at least: {expected_cols}")
        return

    # Top active IPs (by total packet_count)
    ip_activity = (
        all_data.groupby("ip.src")["packet_count"]
        .sum()
        .reset_index()
        .sort_values(by="packet_count", ascending=False)
    )

    # Category distribution
    category_dist = (
        all_data.groupby("category")["packet_count"]
        .sum()
        .reset_index()
        .sort_values(by="packet_count", ascending=False)
    )

    # Save insights as CSVs
    ip_activity.to_csv("insights_top_ips.csv", index=False)
    category_dist.to_csv("insights_categories.csv", index=False)

    print("\n✅ Insights generated:")
    print("   - insights_top_ips.csv")
    print("   - insights_categories.csv")

if __name__ == "__main__":
    generate_insights()
